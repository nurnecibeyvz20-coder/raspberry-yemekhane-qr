from datetime import date
from decimal import Decimal

def login(client, sicil="1001", password="dogru123"):
    return client.post("/login", data={"sicil_no": sicil,
                       "password": password}, follow_redirects=False)

def test_manifest_served(client):
    r = client.get("/static/manifest.json")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Karatay Yemekhane"
    assert data["start_url"] == "/qr"

def test_sw_served_from_root(client):
    # Kök kapsam için sw.js /sw.js'den servis edilmeli (/static değil)
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]

def test_gecmis_requires_login(client, seeded_db):
    r = client.get("/gecmis", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

def test_gecmis_shows_summary_and_history(client, seeded_db):
    from app.db import get_db
    from app.main import app
    from app.models import MealEntry, Transaction
    db = next(app.dependency_overrides[get_db]())
    db.add(Transaction(user_id=seeded_db, type="yukleme",
                       amount=Decimal("500.00"),
                       balance_after=Decimal("500.00")))
    db.add(MealEntry(user_id=seeded_db, entry_date=date.today()))
    db.commit()
    login(client)
    r = client.get("/gecmis")
    assert r.status_code == 200
    assert "Bu ay" in r.text
    assert "+500.00" in r.text

def test_profil_requires_login(client, seeded_db):
    r = client.get("/profil", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

def test_profil_page_shows_user(client, seeded_db):
    login(client)
    r = client.get("/profil")
    assert r.status_code == 200
    assert "Test Personel" in r.text
    assert "1001" in r.text

def test_kurtarma_wrong_password(client, seeded_db):
    login(client)
    r = client.post("/profil/kurtarma", data={
        "telefon": "05551234567", "eposta": "", "gizli_soru": "",
        "gizli_cevap": "", "mevcut_sifre": "yanlis999"})
    assert "Mevcut şifre hatalı" in r.text

def test_kurtarma_saves_fields_normalized(client, seeded_db):
    from app.db import get_db
    from app.main import app
    from app.models import User
    from app.services import reset
    login(client)
    r = client.post("/profil/kurtarma", data={
        "telefon": "05551234567",
        "eposta": "a@b.com",
        "gizli_soru": "İlk okulun?",
        "gizli_cevap": "CEVAP",
        "mevcut_sifre": "dogru123"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/profil"
    db = next(app.dependency_overrides[get_db]())
    user = db.get(User, seeded_db)
    assert user.telefon == "05551234567"
    assert user.eposta == "a@b.com"
    assert user.gizli_soru == "İlk okulun?"
    assert user.gizli_cevap_hash != "CEVAP"  # düz metin değil
    assert reset.gizli_dogrula(user, "  CEVAP ")  # normalize edilmiş

def test_kurtarma_empty_clears_fields(client, seeded_db):
    from app.db import get_db
    from app.main import app
    from app.models import User
    login(client)
    client.post("/profil/kurtarma", data={
        "telefon": "05551234567", "eposta": "a@b.com", "gizli_soru": "",
        "gizli_cevap": "", "mevcut_sifre": "dogru123"},
        follow_redirects=False)
    client.post("/profil/kurtarma", data={
        "telefon": "", "eposta": "", "gizli_soru": "",
        "gizli_cevap": "", "mevcut_sifre": "dogru123"},
        follow_redirects=False)
    db = next(app.dependency_overrides[get_db]())
    user = db.get(User, seeded_db)
    assert user.telefon is None
    assert user.eposta is None

def test_qr_page_no_longer_has_history(client, seeded_db):
    login(client)
    r = client.get("/qr")
    assert r.status_code == 200
    assert "Geçmişim" not in r.text
    assert 'id="qrcode"' in r.text  # QR alanı yerinde
