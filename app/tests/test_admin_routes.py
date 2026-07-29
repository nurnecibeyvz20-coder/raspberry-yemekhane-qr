from decimal import Decimal
import pytest
from app.models import User, Transaction, Setting
from app.auth import hash_password, login_limiter

@pytest.fixture(autouse=True)
def _reset_limiter():
    login_limiter.hits.clear()
    yield
    login_limiter.hits.clear()

def login_admin(client, db):
    a = User(sicil_no="9001", ad_soyad="Admin", role="admin",
             password_hash=hash_password("admin123"))
    db.add(a); db.commit()
    client.post("/login", data={"sicil_no": "9001",
                "password": "admin123"})
    return a

def test_admin_requires_admin_role(client, seeded_db):
    client.post("/login", data={"sicil_no": "1001",
                "password": "dogru123"})
    assert client.get("/admin").status_code == 403

def test_create_user(client, admin_db):
    login_admin(client, admin_db)
    r = client.post("/admin/users/new",
                    data={"sicil_no": "3001", "ad_soyad": "Yeni Kişi",
                          "password": "sifre123", "role": "personel"},
                    follow_redirects=False)
    assert r.status_code == 303
    u = admin_db.query(User).filter_by(sicil_no="3001").one()
    assert u.ad_soyad == "Yeni Kişi"

def test_load_balance(client, admin_db):
    admin = login_admin(client, admin_db)
    u = User(sicil_no="3002", ad_soyad="B", role="personel",
             password_hash="x")
    admin_db.add(u); admin_db.commit()
    client.post(f"/admin/users/{u.id}/load-balance",
                data={"amount": "500.00"})
    admin_db.refresh(u)
    assert u.balance == Decimal("500.00")
    tx = admin_db.query(Transaction).one()
    assert tx.type == "yukleme" and tx.created_by == admin.id

def test_negative_amount_is_duzeltme(client, admin_db):
    login_admin(client, admin_db)
    u = User(sicil_no="3003", ad_soyad="C", role="personel",
             password_hash="x", balance=Decimal("200.00"))
    admin_db.add(u); admin_db.commit()
    client.post(f"/admin/users/{u.id}/load-balance",
                data={"amount": "-50.00"})
    admin_db.refresh(u)
    assert u.balance == Decimal("150.00")
    assert admin_db.query(Transaction).one().type == "duzeltme"

def test_toggle_active(client, admin_db):
    login_admin(client, admin_db)
    u = User(sicil_no="3004", ad_soyad="D", role="personel",
             password_hash="x")
    admin_db.add(u); admin_db.commit()
    client.post(f"/admin/users/{u.id}/toggle-active")
    admin_db.refresh(u)
    assert u.is_active is False

def test_update_meal_price(client, admin_db):
    login_admin(client, admin_db)
    client.post("/admin/settings", data={"meal_price": "150.00"})
    assert admin_db.get(Setting, "meal_price").value == "150.00"

def test_search_users(client, admin_db):
    login_admin(client, admin_db)
    admin_db.add(User(sicil_no="4001", ad_soyad="Mehmet Öz",
                      role="personel", password_hash="x"))
    admin_db.commit()
    r = client.get("/admin?q=Mehmet")
    assert "Mehmet Öz" in r.text
