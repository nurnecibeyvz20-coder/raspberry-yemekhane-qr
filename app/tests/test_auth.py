from app.auth import (hash_password, verify_password,
                      create_session_cookie, read_session_cookie)

def test_password_hash_roundtrip():
    h = hash_password("gizli123")
    assert h != "gizli123"
    assert verify_password("gizli123", h)
    assert not verify_password("yanlis", h)

def test_session_cookie_roundtrip():
    c = create_session_cookie(42, 0)
    assert read_session_cookie(c) == (42, 0)

def test_session_cookie_tampered():
    c = create_session_cookie(42, 0) + "x"
    assert read_session_cookie(c) is None

def test_session_cookie_old_format_rejected():
    from app.auth import _signer
    old = _signer.sign("42").decode()  # eski format: sürümsüz
    assert read_session_cookie(old) is None

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
