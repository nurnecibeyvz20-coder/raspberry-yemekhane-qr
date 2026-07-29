from app.models import User
from app.startup import ensure_initial_admin

def test_creates_admin_when_none(db_session):
    ensure_initial_admin(db_session)
    a = db_session.query(User).filter_by(role="admin").one()
    assert a.sicil_no == "admin"

def test_skips_when_admin_exists(db_session):
    ensure_initial_admin(db_session)
    ensure_initial_admin(db_session)
    assert db_session.query(User).filter_by(role="admin").count() == 1
