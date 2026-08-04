from app.models import User
from app.services.user_qr import approve_user, regenerate_qr_secret


def test_approve_user_generates_unique_qr_secret(db_session):
    user = User(sicil_no="9003", ad_soyad="Onay", role="personel",
                password_hash="x")

    approve_user(user)
    first = user.qr_secret

    assert user.registration_status == "approved"
    assert user.is_active is True
    assert first and len(first) >= 32
    assert regenerate_qr_secret(user) != first
