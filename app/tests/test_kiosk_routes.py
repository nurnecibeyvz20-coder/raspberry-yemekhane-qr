from decimal import Decimal
from fastapi.testclient import TestClient
from app.qr_token import generate_token
from app.routers import kiosk_routes

def test_kiosk_allowed_from_docker_gateway(monkeypatch, seeded_db):
    from app.main import app
    monkeypatch.setattr(kiosk_routes, "_cached_gateway", "172.18.0.1")
    c = TestClient(app, client=("172.18.0.1", 50000))
    assert c.get("/kiosk").status_code == 200

def test_kiosk_lan_still_rejected_when_gateway_known(monkeypatch, seeded_db):
    from app.main import app
    monkeypatch.setattr(kiosk_routes, "_cached_gateway", "172.18.0.1")
    c = TestClient(app, client=("192.168.1.50", 50000))
    assert c.get("/kiosk").status_code == 403

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
