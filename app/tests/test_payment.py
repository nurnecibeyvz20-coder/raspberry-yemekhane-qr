from decimal import Decimal

import pytest

from app.auth import hash_password
from app.models import Payment, Transaction, User
from app.services import payment_flow


def login(client, sicil="1001", password="dogru123"):
    return client.post("/login", data={"sicil_no": sicil,
                       "password": password}, follow_redirects=False)


def make_user(db, sicil="2001", balance="100.00", **kw):
    u = User(sicil_no=sicil, ad_soyad=f"Kisi {sicil}", role="personel",
             password_hash=hash_password("dogru123"),
             balance=Decimal(balance), **kw)
    db.add(u)
    db.commit()
    return u


def app_db():
    from app.db import get_db
    from app.main import app
    return next(app.dependency_overrides[get_db]())


# --- baslat sınırları ---

def test_baslat_sinirlari(db_session):
    user = make_user(db_session)
    with pytest.raises(ValueError):
        payment_flow.baslat(db_session, user, Decimal("49.99"))
    with pytest.raises(ValueError):
        payment_flow.baslat(db_session, user, Decimal("5000.01"))
    p1 = payment_flow.baslat(db_session, user, Decimal("50"))
    p2 = payment_flow.baslat(db_session, user, Decimal("5000"))
    assert p1.durum == "baslatildi" and p2.durum == "baslatildi"
    assert p1.saglayici == "demo"
    assert len(p1.saglayici_ref) == 16


def test_baslat_sonlu_olmayan_tutar(db_session):
    user = make_user(db_session)
    for kotu in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(ValueError):
            payment_flow.baslat(db_session, user, kotu)


# --- mutlu yol (rotalar üzerinden) ---

def test_yukleme_mutlu_yol(client, seeded_db):
    login(client)
    r = client.post("/yukle", data={"tutar": "500"}, follow_redirects=False)
    assert r.status_code == 303
    pos_url = r.headers["location"]
    assert pos_url.endswith("/pos")

    r = client.get(pos_url)
    assert r.status_code == 200
    assert "TEST MODU" in r.text
    assert "4242" in r.text  # test kartı ipucu

    r = client.post(pos_url, data={"kart_no": "4242 4242 4242 4242",
                                   "skt": "12/30", "cvv": "123",
                                   "isim": "Test"},
                    follow_redirects=False)
    assert r.status_code == 303
    sonuc_url = r.headers["location"]
    assert sonuc_url.endswith("/sonuc")

    r = client.get(sonuc_url)
    assert r.status_code == 200
    assert "1000.00" in r.text  # 500 + 500 yeni bakiye
    assert "öğün" in r.text

    db = app_db()
    payment = db.query(Payment).one()
    assert payment.durum == "basarili"
    assert payment.transaction_id is not None
    tx = db.get(Transaction, payment.transaction_id)
    assert tx.type == "yukleme"
    assert tx.created_by is None
    assert tx.amount == Decimal("500.00")
    assert tx.balance_after == Decimal("1000.00")
    assert db.get(User, seeded_db).balance == Decimal("1000.00")


# --- idempotens ---

def test_tamamla_idempotent(db_session):
    user = make_user(db_session, balance="100.00")
    p = payment_flow.baslat(db_session, user, Decimal("200"))
    payment_flow.tamamla(db_session, p.id, "4242424242424242")
    payment_flow.tamamla(db_session, p.id, "4242424242424242")
    db_session.refresh(user)
    assert user.balance == Decimal("300.00")
    assert db_session.query(Transaction).count() == 1


def _db_durum(db, payment_id):
    """Identity map'i atlayarak DB'deki güncel durumu okur."""
    return (db.query(Payment.durum)
              .filter(Payment.id == payment_id).scalar())


def test_tamamla_claim_alinir(db_session, monkeypatch):
    # Sağlayıcı çağrıldığı ANDA claim commit edilmiş olmalı ('isleniyor'):
    # yarışan ikinci istek koşullu UPDATE'te 0 satır görür.
    gorulen = []

    class GozetleyenPos:
        def dogrula(self, kart_no, tutar, ref):
            gorulen.append(_db_durum(db_session, p.id))
            from app.providers.payment import OdemeSonucu
            return OdemeSonucu(True, ref, "Onaylandı")

    monkeypatch.setattr("app.services.payment_flow.get_payment_provider",
                        lambda: GozetleyenPos())
    user = make_user(db_session, balance="100.00")
    p = payment_flow.baslat(db_session, user, Decimal("200"))
    payment_flow.tamamla(db_session, p.id, "4242424242424242")
    assert gorulen == ["isleniyor"]
    assert _db_durum(db_session, p.id) == "basarili"
    db_session.refresh(user)
    assert user.balance == Decimal("300.00")


def test_tamamla_claim_yarisi(db_session):
    # Yarış simülasyonu: başka bir istek claim'i almış gibi durum='isleniyor'
    from sqlalchemy import update
    user = make_user(db_session, balance="100.00")
    p = payment_flow.baslat(db_session, user, Decimal("200"))
    db_session.execute(update(Payment).where(Payment.id == p.id)
                       .values(durum="isleniyor"))
    db_session.commit()
    sonuc = payment_flow.tamamla(db_session, p.id, "4242424242424242")
    assert sonuc.durum == "isleniyor"
    db_session.refresh(user)
    assert user.balance == Decimal("100.00")
    assert db_session.query(Transaction).count() == 0


def test_tamamla_provider_hatasi_geri_alir(db_session, monkeypatch):
    gorulen = []

    class PatlayanPos:
        def dogrula(self, kart_no, tutar, ref):
            gorulen.append(_db_durum(db_session, p.id))
            raise RuntimeError("saglayici koptu")

    monkeypatch.setattr("app.services.payment_flow.get_payment_provider",
                        lambda: PatlayanPos())
    user = make_user(db_session, balance="100.00")
    p = payment_flow.baslat(db_session, user, Decimal("200"))
    with pytest.raises(RuntimeError):
        payment_flow.tamamla(db_session, p.id, "4242424242424242")
    assert gorulen == ["isleniyor"]  # hata anında claim alınmıştı
    assert _db_durum(db_session, p.id) == "baslatildi"  # geri alındı
    db_session.refresh(user)
    assert user.balance == Decimal("100.00")
    assert db_session.query(Transaction).count() == 0


# --- red kartı ---

def test_yukleme_red_karti(client, seeded_db):
    login(client)
    r = client.post("/yukle", data={"tutar": "500"}, follow_redirects=False)
    pos_url = r.headers["location"]
    r = client.post(pos_url, data={"kart_no": "4000 0000 0000 0002"},
                    follow_redirects=False)
    assert r.status_code == 303
    r = client.get(r.headers["location"])
    assert r.status_code == 200
    assert "Tekrar Dene" in r.text

    db = app_db()
    payment = db.query(Payment).one()
    assert payment.durum == "basarisiz"
    assert payment.transaction_id is None
    assert db.get(User, seeded_db).balance == Decimal("500.00")
    assert db.query(Transaction).count() == 0


# --- geçersiz tutar girişi ---

def test_yukleme_gecersiz_tutar(client, seeded_db):
    login(client)
    for tutar in ("abc", "49", "5001", ""):
        r = client.post("/yukle", data={"tutar": tutar},
                        follow_redirects=False)
        assert r.status_code == 200
        assert "50-5000" in r.text
    assert app_db().query(Payment).count() == 0


# --- sahiplik ---

def test_baskasinin_odemesine_erisim(client, seeded_db):
    login(client)
    r = client.post("/yukle", data={"tutar": "500"}, follow_redirects=False)
    pos_url = r.headers["location"]

    db = app_db()
    make_user(db, sicil="9002")
    client.post("/logout")
    login(client, sicil="9002")
    r = client.get(pos_url, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/yukle"
    r = client.post(pos_url, data={"kart_no": "4242424242424242"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/yukle"


# --- dashboard bugun_yuklenen ---

def test_dashboard_bugun_yuklenen(db_session):
    from app.services.stats import dashboard_stats
    user = make_user(db_session)
    p = payment_flow.baslat(db_session, user, Decimal("250"))
    payment_flow.tamamla(db_session, p.id, "4242424242424242")
    s = dashboard_stats(db_session)
    assert s["bugun_yuklenen"] == Decimal("250.00")


def test_dashboard_bugun_yuklenen_sifir(db_session):
    from app.services.stats import dashboard_stats
    assert dashboard_stats(db_session)["bugun_yuklenen"] == Decimal("0")


# --- kilitli kullanıcı ---

def test_kilitli_kullanici_yukleyemez(client, seeded_db):
    db = app_db()
    user = db.get(User, seeded_db)
    user.must_change_password = True
    db.commit()
    login(client)
    r = client.get("/yukle", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/sifre-degistir-zorunlu"
