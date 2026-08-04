from decimal import Decimal
from datetime import date, time as dtime
from app.qr_token import generate_token
from app.models import User, MealEntry, Transaction, FailedAttempt
from app.services.checkin import process_checkin, get_meal_price
from app.auth import hash_password
from app.services.user_qr import regenerate_qr_secret

def make_user(db, sicil="2001", balance="500.00", active=True):
    u = User(sicil_no=sicil, ad_soyad="Test Kişi", role="personel",
             password_hash=hash_password("x"), balance=Decimal(balance),
             is_active=active)
    db.add(u); db.commit()
    regenerate_qr_secret(u); db.commit()
    return u

def test_meal_price_defaults_to_125(db_session):
    assert get_meal_price(db_session) == Decimal("125.00")

def test_successful_checkin(db_session):
    u = make_user(db_session)
    r = process_checkin(db_session, generate_token(u.id, u.qr_secret))
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
    r = process_checkin(db_session, generate_token(u.id, u.qr_secret))
    assert r.status == "hesap_pasif"

def test_duplicate_entry_same_day(db_session):
    u = make_user(db_session)
    process_checkin(db_session, generate_token(u.id, u.qr_secret))
    r = process_checkin(db_session, generate_token(u.id, u.qr_secret))
    assert r.status == "mukerrer"
    db_session.refresh(u)
    assert u.balance == Decimal("375.00")  # ikinci kez düşmedi

def test_insufficient_balance(db_session):
    u = make_user(db_session, balance="100.00")
    r = process_checkin(db_session, generate_token(u.id, u.qr_secret))
    assert r.status == "yetersiz_bakiye"
    db_session.refresh(u)
    assert u.balance == Decimal("100.00")

class SabitDatetime:
    """checkin.datetime yerine monkeypatch edilir."""
    sabit = None
    @classmethod
    def now(cls):
        class N:
            @staticmethod
            def time():
                return SabitDatetime.sabit
        return N()

def _saat_sabitle(monkeypatch, hh, mm):
    SabitDatetime.sabit = dtime(hh, mm)
    monkeypatch.setattr("app.services.checkin.datetime", SabitDatetime)

def test_service_hours_defaults(db_session):
    from app.services.checkin import get_service_hours
    bas, bit = get_service_hours(db_session)
    assert bas == dtime(12, 0) and bit == dtime(13, 30)

def test_checkin_outside_hours_rejected(db_session, monkeypatch):
    u = make_user(db_session, sicil="7001")
    _saat_sabitle(monkeypatch, 15, 0)
    r = process_checkin(db_session, generate_token(u.id, u.qr_secret))
    assert r.status == "saat_disi"
    db_session.refresh(u)
    assert u.balance == Decimal("500.00")          # bakiye düşmedi
    assert db_session.query(MealEntry).count() == 0
    assert db_session.query(FailedAttempt).one().reason == "saat_disi"

def test_checkin_boundary_times_accepted(db_session, monkeypatch):
    u1 = make_user(db_session, sicil="7002")
    _saat_sabitle(monkeypatch, 12, 0)              # tam açılış
    assert process_checkin(db_session, generate_token(u1.id, u1.qr_secret)).ok
    u2 = make_user(db_session, sicil="7003")
    _saat_sabitle(monkeypatch, 13, 30)             # tam kapanış
    assert process_checkin(db_session, generate_token(u2.id, u2.qr_secret)).ok

def test_checkin_just_after_close_rejected(db_session, monkeypatch):
    u = make_user(db_session, sicil="7004")
    _saat_sabitle(monkeypatch, 13, 31)
    assert process_checkin(db_session, generate_token(u.id, u.qr_secret)).status == "saat_disi"
