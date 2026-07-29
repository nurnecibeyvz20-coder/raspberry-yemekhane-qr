from decimal import Decimal
from app.models import User, MealEntry
from app.services.checkin import process_checkin
from app.qr_token import generate_token
from app.auth import hash_password

def test_integrity_error_path_returns_mukerrer(db_session):
    u = User(sicil_no="5001", ad_soyad="R", role="personel",
             password_hash=hash_password("x"),
             balance=Decimal("500.00"))
    db_session.add(u); db_session.commit()
    # SQLite'ta gercek eszamanlilik test edilemez; iki ardisik cagrinin
    # ikincisinin mukerrer dondugunu ve bakiyenin tek dustugunu dogrula
    r1 = process_checkin(db_session, generate_token(u.id))
    r2 = process_checkin(db_session, generate_token(u.id))
    assert r1.ok and r2.status == "mukerrer"
    db_session.refresh(u)
    assert u.balance == Decimal("375.00")
    assert db_session.query(MealEntry).count() == 1
