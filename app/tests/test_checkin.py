from decimal import Decimal
from datetime import date
from app.qr_token import generate_token
from app.models import User, MealEntry, Transaction, FailedAttempt
from app.services.checkin import process_checkin, get_meal_price
from app.auth import hash_password

def make_user(db, sicil="2001", balance="500.00", active=True):
    u = User(sicil_no=sicil, ad_soyad="Test Kişi", role="personel",
             password_hash=hash_password("x"), balance=Decimal(balance),
             is_active=active)
    db.add(u); db.commit()
    return u

def test_meal_price_defaults_to_125(db_session):
    assert get_meal_price(db_session) == Decimal("125.00")

def test_successful_checkin(db_session):
    u = make_user(db_session)
    r = process_checkin(db_session, generate_token(u.id))
    assert r.ok and r.status == "onay"
    assert r.balance == Decimal("375.00")
    db_session.refresh(u)
    assert u.balance == Decimal("375.00")
    assert db_session.query(MealEntry).count() == 1
    tx = db_session.query(Transaction).one()
    assert tx.type == "yemek" and tx.amount == Decimal("-125.00")
    assert tx.balance_after == Decimal("375.00")

def test_invalid_token(db_session):
    r = process_checkin(db_session, "sahte-token")
    assert not r.ok and r.status == "gecersiz"
    assert db_session.query(FailedAttempt).one().reason == "gecersiz"

def test_inactive_user(db_session):
    u = make_user(db_session, active=False)
    r = process_checkin(db_session, generate_token(u.id))
    assert r.status == "hesap_pasif"

def test_duplicate_entry_same_day(db_session):
    u = make_user(db_session)
    process_checkin(db_session, generate_token(u.id))
    r = process_checkin(db_session, generate_token(u.id))
    assert r.status == "mukerrer"
    db_session.refresh(u)
    assert u.balance == Decimal("375.00")  # ikinci kez düşmedi

def test_insufficient_balance(db_session):
    u = make_user(db_session, balance="100.00")
    r = process_checkin(db_session, generate_token(u.id))
    assert r.status == "yetersiz_bakiye"
    db_session.refresh(u)
    assert u.balance == Decimal("100.00")
