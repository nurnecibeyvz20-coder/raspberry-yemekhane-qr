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
