from decimal import Decimal
from app.qr_token import generate_token

def test_checkin_rejected_from_remote_ip(client_remote, seeded_db):
    r = client_remote.post("/api/checkin", json={"token": "x"})
    assert r.status_code == 403

def test_kiosk_page_rejected_from_remote_ip(client_remote, seeded_db):
    assert client_remote.get("/kiosk").status_code == 403

def test_checkin_success(client, seeded_db):
    uid = seeded_db  # fixture user id döndürür
    r = client.post("/api/checkin",
                    json={"token": generate_token(uid)})
    body = r.json()
    assert body["ok"] is True and body["status"] == "onay"
    assert body["balance"] == "375.00"

def test_checkin_invalid_token(client, seeded_db):
    r = client.post("/api/checkin", json={"token": "sahte"})
    body = r.json()
    assert body["ok"] is False and body["status"] == "gecersiz"
