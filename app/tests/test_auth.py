from app.auth import (hash_password, verify_password,
                      create_session_cookie, read_session_cookie)

def test_password_hash_roundtrip():
    h = hash_password("gizli123")
    assert h != "gizli123"
    assert verify_password("gizli123", h)
    assert not verify_password("yanlis", h)

def test_session_cookie_roundtrip():
    c = create_session_cookie(42)
    assert read_session_cookie(c) == 42

def test_session_cookie_tampered():
    c = create_session_cookie(42) + "x"
    assert read_session_cookie(c) is None

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
