import secrets

from app.models import User


def is_approved(user: User) -> bool:
    return user.registration_status == "approved" and user.is_active


def regenerate_qr_secret(user: User) -> str:
    user.qr_secret = secrets.token_urlsafe(32)
    return user.qr_secret


def approve_user(user: User) -> None:
    user.registration_status = "approved"
    user.is_active = True
    regenerate_qr_secret(user)
