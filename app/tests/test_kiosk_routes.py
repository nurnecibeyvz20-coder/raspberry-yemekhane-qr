from decimal import Decimal
from fastapi.testclient import TestClient
from app.qr_token import generate_token
from app.routers import kiosk_routes
from app.models import User


def _token_for_user(db, user_id):
    from app.services.user_qr import regenerate_qr_secret
    user = db.get(User, user_id)
    secret = user.qr_secret or regenerate_qr_secret(user)
    db.commit()
    return generate_token(user.id, secret)

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


def test_kiosk_uses_horizontal_municipality_logo(client, seeded_db):
    r = client.get("/kiosk")
    assert 'src="/static/imagebelediye.png"' in r.text
    assert 'class="kiosk-doku"' in r.text

def test_checkin_success(client, seeded_db):
    from app.db import get_db
    from app.main import app
    db = next(app.dependency_overrides[get_db]())
    r = client.post("/api/checkin", json={"token": _token_for_user(db, seeded_db)})
    body = r.json()
    assert body["ok"] is True and body["status"] == "onay"
    assert body["balance"] == "375.00"

def test_checkin_invalid_token(client, seeded_db):
    r = client.post("/api/checkin", json={"token": "sahte"})
    body = r.json()
    assert body["ok"] is False and body["status"] == "gecersiz"


def test_kiosk_accepts_approved_guest_qr(client, seeded_db):
    from datetime import date, time
    from app.db import get_db
    from app.guest_qr_token import generate_guest_token
    from app.main import app
    from app.models import GuestRequest
    from app.services.guest_requests import approve_request
    db = next(app.dependency_overrides[get_db]())
    guest = GuestRequest(owner_id=seeded_db, ad="Misafir", soyad="Kişi", telefon="0555",
        ziyaret_nedeni="Ziyaret", ziyaret_tarihi=date.today(), yemek_adedi=1,
        baslangic_saati=time(0), bitis_saati=time(23, 59))
    db.add(guest); db.flush(); approve_request(db, guest, seeded_db); db.commit()
    r = client.post("/api/checkin", json={"token": generate_guest_token(guest.id, guest.qr_secret)})
    assert r.json()["status"] == "misafir_onay"

def test_checkin_response_includes_signed_announcement(client, seeded_db):
    from app.qr_token import generate_token
    from app.tts import dogrula
    from app.db import get_db
    from app.main import app
    db = next(app.dependency_overrides[get_db]())
    r = client.post("/api/checkin", json={"token": _token_for_user(db, seeded_db)})
    body = r.json()
    assert "anons" in body
    assert "Afiyet olsun" in body["anons"]["text"]
    assert dogrula(body["anons"]["text"], body["anons"]["sig"])

def test_checkin_outside_hours_response(client, seeded_db, monkeypatch):
    from datetime import time as t
    monkeypatch.setattr(
        "app.services.checkin.get_service_hours",
        lambda db: (t(0, 0), t(0, 1)))   # hep kapali
    from app.qr_token import generate_token
    from app.db import get_db
    from app.main import app
    db = next(app.dependency_overrides[get_db]())
    r = client.post("/api/checkin", json={"token": _token_for_user(db, seeded_db)})
    body = r.json()
    assert body["status"] == "saat_disi"
    assert body["saatler"] == "00:00 - 00:01"
    assert "kapalı" in body["anons"]["text"]

def test_kiosk_durum_endpoint(client, seeded_db, monkeypatch):
    from datetime import time as t
    monkeypatch.setattr(
        "app.routers.kiosk_routes.get_service_hours",
        lambda db: (t(0, 0), t(23, 59)))
    r = client.get("/api/kiosk-durum")
    assert r.json()["acik"] is True

def test_kiosk_durum_remote_403(client_remote, seeded_db):
    assert client_remote.get("/api/kiosk-durum").status_code == 403

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
