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
    assert r.headers["location"] == "/admin/personel"
    u = admin_db.query(User).filter_by(sicil_no="3001").one()
    assert u.ad_soyad == "Yeni Kişi"

def test_create_user_duplicate(client, admin_db):
    login_admin(client, admin_db)
    client.post("/admin/users/new",
                data={"sicil_no": "3001", "ad_soyad": "İlk Kişi",
                      "password": "sifre123", "role": "personel"})
    r = client.post("/admin/users/new",
                    data={"sicil_no": "3001", "ad_soyad": "İkinci Kişi",
                          "password": "sifre456", "role": "personel"},
                    follow_redirects=True)
    # Hata flash ile listeye redirect edilir; toast metni sayfada gorunur
    assert r.history and r.history[0].status_code == 303
    assert r.history[0].headers["location"] == "/admin/personel"
    assert "Bu sicil no zaten kayıtlı" in r.text
    users = admin_db.query(User).filter_by(sicil_no="3001").all()
    assert len(users) == 1
    assert users[0].ad_soyad == "İlk Kişi"

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
    r = client.post("/admin/settings", data={"meal_price": "150.00"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert admin_db.get(Setting, "meal_price").value == "150.00"

def test_load_balance_rejects_nan(client, admin_db):
    login_admin(client, admin_db)
    u = User(sicil_no="3005", ad_soyad="E", role="personel",
             password_hash="x", balance=Decimal("100.00"))
    admin_db.add(u); admin_db.commit()
    r = client.post(f"/admin/users/{u.id}/load-balance",
                    data={"amount": "NaN"})
    assert r.status_code == 400
    admin_db.refresh(u)
    assert u.balance == Decimal("100.00")
    assert admin_db.query(Transaction).count() == 0

def test_settings_rejects_nan(client, admin_db):
    login_admin(client, admin_db)
    r = client.post("/admin/settings", data={"meal_price": "NaN"})
    assert r.status_code < 500
    row = admin_db.get(Setting, "meal_price")
    assert row is None or row.value != "NaN"

def test_search_users(client, admin_db):
    login_admin(client, admin_db)
    admin_db.add(User(sicil_no="4001", ad_soyad="Mehmet Öz",
                      role="personel", password_hash="x"))
    admin_db.commit()
    r = client.get("/admin/personel?q=Mehmet")
    assert "Mehmet Öz" in r.text

def test_dashboard_renders_stats(client, admin_db):
    login_admin(client, admin_db)
    r = client.get("/admin")
    assert r.status_code == 200
    assert "Bugün Yiyen" in r.text

def test_personel_pagination(client, admin_db):
    login_admin(client, admin_db)
    for i in range(60):
        admin_db.add(User(sicil_no=f"pg{i:03d}", ad_soyad=f"Kisi {i:03d}",
                          role="personel", password_hash="x"))
    admin_db.commit()
    r1 = client.get("/admin/personel?page=1")
    r2 = client.get("/admin/personel?page=2")
    assert "Kisi 000" in r1.text and "Kisi 000" not in r2.text

def test_personel_sort_by_balance(client, admin_db):
    login_admin(client, admin_db)
    admin_db.add(User(sicil_no="z1", ad_soyad="Zengin", role="personel",
                      password_hash="x", balance=Decimal("900.00")))
    admin_db.add(User(sicil_no="f1", ad_soyad="Fakir", role="personel",
                      password_hash="x", balance=Decimal("10.00")))
    admin_db.commit()
    r = client.get("/admin/personel?sort=balance&dir=desc")
    assert r.text.index("Zengin") < r.text.index("Fakir")

def test_islemler_page_filters_by_type(client, admin_db):
    admin = login_admin(client, admin_db)
    u = User(sicil_no="i1", ad_soyad="Islemci", role="personel",
             password_hash="x")
    admin_db.add(u); admin_db.commit()
    admin_db.add(Transaction(user_id=u.id, type="yukleme",
                             amount=Decimal("100.00"),
                             balance_after=Decimal("100.00"),
                             created_by=admin.id))
    admin_db.add(Transaction(user_id=u.id, type="yemek",
                             amount=Decimal("-125.00"),
                             balance_after=Decimal("-25.00")))
    admin_db.commit()
    r = client.get("/admin/islemler?tur=yukleme")
    assert "yukleme" in r.text.lower() or "Yükleme" in r.text
    assert "-125" not in r.text

def test_load_balance_sets_flash_cookie(client, admin_db):
    login_admin(client, admin_db)
    u = User(sicil_no="f2", ad_soyad="Flaslı", role="personel",
             password_hash="x")
    admin_db.add(u); admin_db.commit()
    r = client.post(f"/admin/users/{u.id}/load-balance",
                    data={"amount": "250.00"}, follow_redirects=False)
    assert r.status_code == 303
    assert "flash=" in r.headers.get("set-cookie", "")
