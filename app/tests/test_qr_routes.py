from decimal import Decimal

def login(client, sicil="1001", password="dogru123"):
    return client.post("/login", data={"sicil_no": sicil,
                       "password": password}, follow_redirects=False)

def test_qr_page_requires_login(client, seeded_db):
    r = client.get("/qr", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

def test_qr_token_api(client, seeded_db):
    login(client)
    r = client.get("/api/qr-token")
    assert r.status_code == 200
    body = r.json()
    assert body["ttl"] == 60
    assert "token" in body and "balance" in body

def test_low_balance_flag(client, seeded_db_low_balance):
    login(client, sicil="1003")
    r = client.get("/api/qr-token")
    assert r.json()["low_balance"] is True

def test_change_password(client, seeded_db):
    login(client)
    r = client.post("/change-password",
                    data={"old_password": "dogru123",
                          "new_password": "yeni12345"},
                    follow_redirects=False)
    assert r.status_code == 303
    client.post("/logout")
    assert login(client, password="yeni12345").status_code == 303
