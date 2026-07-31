from decimal import Decimal
from datetime import date
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import User, MealEntry

def test_user_defaults(db_session):
    u = User(sicil_no="1001", ad_soyad="Ali Veli",
             role="personel", password_hash="x")
    db_session.add(u)
    db_session.commit()
    assert u.balance == Decimal("0.00")
    assert u.is_active is True

def test_user_pwa_defaults(db_session):
    u = User(sicil_no="m1", ad_soyad="M", role="personel", password_hash="x")
    db_session.add(u)
    db_session.commit()
    assert u.must_change_password is False
    assert u.session_version == 0
    assert u.telefon is None and u.gizli_soru is None

def test_reset_code_and_payment_models(db_session):
    from datetime import datetime, timedelta
    from app.models import ResetCode, Payment
    u = User(sicil_no="m2", ad_soyad="N", role="personel", password_hash="x")
    db_session.add(u)
    db_session.commit()
    rc = ResetCode(user_id=u.id, kanal="sms", kod_hash="h",
                   expires_at=datetime.now() + timedelta(minutes=10))
    p = Payment(user_id=u.id, tutar=Decimal("250.00"),
                durum="baslatildi", saglayici="demo", saglayici_ref="ref1")
    db_session.add_all([rc, p])
    db_session.commit()
    assert rc.used is False and rc.demo_gosterim is None
    assert rc.attempts == 0
    assert p.transaction_id is None

def test_one_meal_per_day_constraint(db_session):
    u = User(sicil_no="1002", ad_soyad="Ayşe Can",
             role="personel", password_hash="x")
    db_session.add(u)
    db_session.commit()
    db_session.add(MealEntry(user_id=u.id, entry_date=date(2026, 7, 29)))
    db_session.commit()
    db_session.add(MealEntry(user_id=u.id, entry_date=date(2026, 7, 29)))
    with pytest.raises(IntegrityError):
        db_session.commit()
