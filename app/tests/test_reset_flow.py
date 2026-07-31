import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password, verify_password
from app.db import Base, get_db
from app.main import app
from app.models import ResetCode, User
from app.services.reset import normalize


@pytest.fixture
def flow_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    session = TestingSession()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.pop(get_db, None)
    session.close()


def _kullanici(db, **kwargs):
    defaults = dict(sicil_no="7001", ad_soyad="Akış Test", role="personel",
                    password_hash=hash_password("eski1234"))
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    db.commit()
    return user


def test_bilinmeyen_sicil_ve_yontemsiz_ayni_cevap(client, flow_db):
    """Bilinmeyen sicil ile yöntemsiz kullanıcı aynı yanıtı almalı
    (kullanıcı varlığı sızdırılmaz)."""
    _kullanici(flow_db, sicil_no="7002")  # yöntemsiz kullanıcı
    r1 = client.post("/sifremi-unuttum", data={"sicil_no": "yok999"})
    r2 = client.post("/sifremi-unuttum", data={"sicil_no": "7002"})
    for r in (r1, r2):
        assert r.status_code == 200
        assert "Yöneticinize başvurun" in r.text
        assert 'name="kanal"' not in r.text  # kanal seçim butonu yok
    assert "reset_state" not in r1.cookies
    assert "reset_state" not in r2.cookies


def test_sms_akisi_uctan_uca(client, flow_db):
    user = _kullanici(flow_db, telefon="05321234512")

    r = client.post("/sifremi-unuttum", data={"sicil_no": "7001"})
    assert r.status_code == 200
    assert "05** *** **12" in r.text  # yöntem listesinde maske

    r = client.post("/sifremi-unuttum/yontem", data={"kanal": "sms"})
    assert r.status_code == 200
    assert "05** *** **12" in r.text  # kod ekranında maskeli hedef

    satir = (flow_db.query(ResetCode).filter_by(user_id=user.id)
             .order_by(ResetCode.id.desc()).first())
    assert satir is not None
    assert satir.demo_gosterim  # demo sağlayıcı kodu sakladı
    assert satir.demo_gosterim not in r.text  # kod ASLA sayfada gösterilmez

    r = client.post("/sifremi-unuttum/kod", data={"kod": satir.demo_gosterim})
    assert r.status_code == 200
    assert "new_password" in r.text  # yeni şifre ekranı

    r = client.post("/sifremi-unuttum/yeni",
                    data={"new_password": "yepyeni123"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

    r = client.get("/login")
    assert "Şifreniz değişti" in r.text  # flash görünür

    r = client.post("/login",
                    data={"sicil_no": "7001", "password": "eski1234"},
                    follow_redirects=False)
    assert r.status_code == 200
    assert "Hatalı" in r.text  # eski şifre artık geçmez

    r = client.post("/login",
                    data={"sicil_no": "7001", "password": "yepyeni123"},
                    follow_redirects=False)
    assert r.status_code == 303  # yeni şifre çalışır


def test_yanlis_kod_hata_mesaji(client, flow_db):
    user = _kullanici(flow_db, telefon="05321234512")
    client.post("/sifremi-unuttum", data={"sicil_no": "7001"})
    client.post("/sifremi-unuttum/yontem", data={"kanal": "sms"})
    satir = (flow_db.query(ResetCode).filter_by(user_id=user.id)
             .order_by(ResetCode.id.desc()).first())
    yanlis = "000000" if satir.demo_gosterim != "000000" else "111111"
    r = client.post("/sifremi-unuttum/kod", data={"kod": yanlis})
    assert r.status_code == 200
    assert "Kod hatalı veya süresi dolmuş" in r.text


def test_gizli_soru_akisi(client, flow_db):
    _kullanici(flow_db, gizli_soru="Doğduğunuz şehir?",
               gizli_cevap_hash=hash_password(normalize("Ankara")))

    r = client.post("/sifremi-unuttum", data={"sicil_no": "7001"})
    assert r.status_code == 200

    r = client.post("/sifremi-unuttum/yontem", data={"kanal": "gizli_soru"})
    assert r.status_code == 200
    assert "Doğduğunuz şehir?" in r.text  # soru gösterilir

    # dağınık büyük/küçük harf ve boşlukla cevap kabul edilmeli
    r = client.post("/sifremi-unuttum/soru", data={"cevap": "  ANKARA "})
    assert r.status_code == 200
    assert "new_password" in r.text

    r = client.post("/sifremi-unuttum/yeni",
                    data={"new_password": "sorulu1234"},
                    follow_redirects=False)
    assert r.status_code == 303

    flow_db.expire_all()
    user = flow_db.query(User).filter_by(sicil_no="7001").one()
    assert verify_password("sorulu1234", user.password_hash)


def test_statesiz_yeni_post_basa_doner(client, flow_db):
    _kullanici(flow_db)
    r = client.post("/sifremi-unuttum/yeni",
                    data={"new_password": "hacker1234"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/sifremi-unuttum"

    flow_db.expire_all()
    user = flow_db.query(User).filter_by(sicil_no="7001").one()
    assert verify_password("eski1234", user.password_hash)  # şifre değişmedi


def test_yeni_state_tekrar_kullanilamaz(client, flow_db):
    """Başarılı sıfırlama sonrası yakalanan asama=yeni çerezi ikinci bir
    şifre sıfırlamaya izin vermemeli (session_version bağlaması)."""
    user = _kullanici(flow_db, telefon="05321234512")
    client.post("/sifremi-unuttum", data={"sicil_no": "7001"})
    client.post("/sifremi-unuttum/yontem", data={"kanal": "sms"})
    satir = (flow_db.query(ResetCode).filter_by(user_id=user.id)
             .order_by(ResetCode.id.desc()).first())
    client.post("/sifremi-unuttum/kod", data={"kod": satir.demo_gosterim})

    # /yeni POST'undan ÖNCE state çerezini yakala
    yakalanan = client.cookies.get("reset_state")
    assert yakalanan

    r = client.post("/sifremi-unuttum/yeni",
                    data={"new_password": "birinci123"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

    # Yakalanan çerezle tekrar dene → başa dönmeli
    client.cookies.set("reset_state", yakalanan)
    r = client.post("/sifremi-unuttum/yeni",
                    data={"new_password": "ikinci1234"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/sifremi-unuttum"

    flow_db.expire_all()
    user = flow_db.query(User).filter_by(sicil_no="7001").one()
    assert verify_password("birinci123", user.password_hash)
    assert not verify_password("ikinci1234", user.password_hash)


def test_sicil_post_hiz_siniri(client, flow_db):
    """POST /sifremi-unuttum IP başına sınırlı: 11. istek 429."""
    for _ in range(10):
        r = client.post("/sifremi-unuttum", data={"sicil_no": "yok"})
        assert r.status_code == 200
    r = client.post("/sifremi-unuttum", data={"sicil_no": "yok"})
    assert r.status_code == 429
    assert "Çok fazla deneme" in r.text


def test_gecersiz_kanal_kod_uretmez(client, flow_db):
    """Sadece telefonu olan kullanıcı için kanal=eposta enjekte edilirse
    kod üretilmemeli (Task 4 taşıması: servis doğrulama yapmıyor)."""
    _kullanici(flow_db, telefon="05321234512")
    client.post("/sifremi-unuttum", data={"sicil_no": "7001"})
    r = client.post("/sifremi-unuttum/yontem", data={"kanal": "eposta"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    if r.status_code == 200:
        assert 'name="kod"' not in r.text  # kod ekranına geçilmedi
    assert flow_db.query(ResetCode).count() == 0
