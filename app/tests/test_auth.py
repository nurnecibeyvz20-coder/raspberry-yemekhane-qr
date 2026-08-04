from app.auth import (hash_password, verify_password,
                       create_session_cookie, read_session_cookie)
from app.models import User

def test_password_hash_roundtrip():
    h = hash_password("gizli123")
    assert h != "gizli123"
    assert verify_password("gizli123", h)
    assert not verify_password("yanlis", h)

def test_session_cookie_roundtrip():
    c = create_session_cookie(42, 0, "personel")
    assert read_session_cookie(c) == (42, 0)

def test_session_cookie_roundtrip_admin():
    c = create_session_cookie(42, 0, "admin")
    assert read_session_cookie(c) == (42, 0)

def test_session_cookie_tampered():
    c = create_session_cookie(42, 0, "personel") + "x"
    assert read_session_cookie(c) is None

def test_session_cookie_old_format_rejected():
    from app.auth import _signer
    old = _signer.sign("42").decode()  # eski format: sürümsüz
    assert read_session_cookie(old) is None
    eski_iki = _signer.sign("42:0").decode()  # rol işaretsiz eski format
    assert read_session_cookie(eski_iki) is None

def test_admin_cookie_expires_before_personel(monkeypatch):
    # Admin çerezi 12 saatlik tazelik denetimine tabidir; süresi geçmiş
    # sayılırsa (max_age=-1) okunamaz. Aynı yaştaki personel çerezi okunur.
    from app.config import settings
    monkeypatch.setattr(settings, "admin_session_age", -1)
    admin_c = create_session_cookie(7, 0, "admin")
    personel_c = create_session_cookie(7, 0, "personel")
    assert read_session_cookie(admin_c) is None
    assert read_session_cookie(personel_c) == (7, 0)

def test_login_wrong_password(client, seeded_db):
    r = client.post("/login",
                    data={"sicil_no": "1001", "password": "yanlis"},
                    follow_redirects=False)
    assert r.status_code == 200  # login sayfası hata mesajıyla döner
    assert "Hatalı" in r.text

def test_login_success_sets_cookie(client, seeded_db):
    r = client.post("/login",
                    data={"sicil_no": "1001", "password": "dogru123"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert "session" in r.cookies


def test_registration_creates_pending_user(client, admin_db):
    r = client.post("/kayit", data={"sicil_no": "8010", "ad_soyad": "Yeni",
                                     "password": "guvenli123"},
                    follow_redirects=False)
    assert r.status_code == 303
    user = admin_db.query(User).filter_by(sicil_no="8010").one()
    assert user.registration_status == "pending"
    assert user.is_active is False


def test_pending_user_cannot_login_until_approved(client, admin_db):
    user = User(sicil_no="8011", ad_soyad="Bekleyen", role="personel",
                password_hash=hash_password("guvenli123"), is_active=False,
                registration_status="pending")
    admin_db.add(user); admin_db.commit()
    r = client.post("/login", data={"sicil_no": "8011", "password": "guvenli123"})
    assert "bekliyor" in r.text.lower()

def login(client, sicil="1001", password="dogru123"):
    return client.post("/login", data={"sicil_no": sicil,
                       "password": password}, follow_redirects=False)

def test_session_version_invalidates_old_cookie(client, seeded_db):
    from app.db import get_db
    from app.main import app
    from app.models import User
    login(client)
    db = next(app.dependency_overrides[get_db]())
    u = db.get(User, seeded_db); u.session_version += 1; db.commit()
    r = client.get("/qr", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

def test_password_change_keeps_current_session(client, seeded_db):
    login(client)
    r = client.post("/change-password",
                    data={"old_password": "dogru123",
                          "new_password": "yeni12345"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert client.get("/qr").status_code == 200   # yeni çerez verildi

def test_must_change_password_locks_pages(client, seeded_db):
    from app.db import get_db
    from app.main import app
    from app.models import User
    db = next(app.dependency_overrides[get_db]())
    u = db.get(User, seeded_db); u.must_change_password = True; db.commit()
    login(client)
    r = client.get("/qr", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/sifre-degistir-zorunlu"

def test_forced_change_rejected_when_not_locked(client, seeded_db):
    login(client)  # must_change_password=False
    r = client.post("/sifre-degistir-zorunlu",
                    data={"new_password": "korsan123"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/qr"
    client.post("/logout")
    # şifre DEĞİŞMEDİ: eski şifreyle giriş hâlâ çalışır
    assert login(client).status_code == 303

def test_forced_change_unlocks(client, seeded_db):
    from app.db import get_db
    from app.main import app
    from app.models import User
    db = next(app.dependency_overrides[get_db]())
    u = db.get(User, seeded_db); u.must_change_password = True; db.commit()
    login(client)
    r = client.post("/sifre-degistir-zorunlu",
                    data={"new_password": "taze12345"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert client.get("/qr").status_code == 200
