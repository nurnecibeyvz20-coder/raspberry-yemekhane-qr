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

def test_qr_page_shows_history_and_meals(client, seeded_db):
    from app.db import get_db
    from app.main import app
    from app.models import Transaction
    # seeded_db overrides get_db; use the same engine the app sees
    db = next(app.dependency_overrides[get_db]())
    db.add(Transaction(user_id=seeded_db, type="yukleme",
                       amount=Decimal("500.00"),
                       balance_after=Decimal("500.00")))
    db.commit()
    login(client)
    r = client.get("/qr")
    assert "Geçmişim" in r.text
    assert "+500.00" in r.text
    assert "4 öğün" in r.text   # 500 // 125

def test_qr_token_api_reports_ate_today(client, seeded_db):
    from datetime import date
    from app.db import get_db
    from app.main import app
    from app.models import MealEntry
    login(client)
    r = client.get("/api/qr-token")
    assert r.json()["ate_today"] is False
    db = next(app.dependency_overrides[get_db]())
    db.add(MealEntry(user_id=seeded_db, entry_date=date.today()))
    db.commit()
    r = client.get("/api/qr-token")
    assert r.json()["ate_today"] is True

def test_change_password_rejects_short(client, seeded_db):
    login(client)
    r = client.post("/change-password",
                    data={"old_password": "dogru123",
                          "new_password": "kisa5"},
                    follow_redirects=False)
    assert r.status_code == 200
    assert "Şifre en az 8 karakter olmalı" in r.text
    client.post("/logout")
    assert login(client).status_code == 303  # şifre değişmedi

def test_change_password(client, seeded_db):
    login(client)
    r = client.post("/change-password",
                    data={"old_password": "dogru123",
                          "new_password": "yeni12345"},
                    follow_redirects=False)
    assert r.status_code == 303
    client.post("/logout")
    assert login(client, password="yeni12345").status_code == 303
