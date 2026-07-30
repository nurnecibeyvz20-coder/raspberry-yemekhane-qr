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

def test_checkin_response_includes_signed_announcement(client, seeded_db):
    from app.qr_token import generate_token
    from app.tts import dogrula
    r = client.post("/api/checkin", json={"token": generate_token(seeded_db)})
    body = r.json()
    assert "anons" in body
    assert "Afiyet olsun" in body["anons"]["text"]
    assert dogrula(body["anons"]["text"], body["anons"]["sig"])

def test_tts_rejects_bad_signature(client, seeded_db):
    r = client.get("/api/tts", params={"text": "istedigim metni okut", "sig": "sahte"})
    assert r.status_code == 400

def test_tts_rejects_non_ascii_signature(client, seeded_db):
    r = client.get("/api/tts", params={"text": "x", "sig": "türkçe-imza-ğ"})
    assert r.status_code == 400

def test_tts_rejected_from_remote(client_remote, seeded_db):
    r = client_remote.get("/api/tts", params={"text": "x", "sig": "y"})
    assert r.status_code == 403

def test_tts_serves_wav(client, seeded_db, monkeypatch, tmp_path):
    from app import tts
    wav = tmp_path / "a.wav"; wav.write_bytes(b"RIFFtest")
    monkeypatch.setattr("app.routers.kiosk_routes.uret", lambda t: wav)
    metin = "deneme anonsu"
    r = client.get("/api/tts", params={"text": metin, "sig": tts.imzala(metin)})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content == b"RIFFtest"
