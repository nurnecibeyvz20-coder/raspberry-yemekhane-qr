import time
from collections import defaultdict
from fastapi import Depends, HTTPException, Request
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_signer = TimestampSigner(settings.secret_key, salt="session")

def hash_password(plain: str) -> str:
    return pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)

def create_session_cookie(user_id: int, session_version: int,
                          role: str) -> str:
    # Rol işareti ('p'/'a') imzalı değere gömülür: admin çerezinin 12
    # saatlik ömrü sunucu tarafında da denetlenebilsin diye.
    return _signer.sign(
        f"{user_id}:{session_version}:{role[0]}").decode()

def read_session_cookie(value: str) -> tuple[int, int] | None:
    try:
        raw = _signer.unsign(
            value, max_age=settings.personel_session_age).decode()
        parcalar = raw.split(":")
        if len(parcalar) != 3:  # eski format (rol işaretsiz) geçersiz
            return None
        uid, ver, rol = parcalar
        if rol == "a":
            # Admin çerezi ek tazelik denetiminden geçer (12 saat).
            _signer.unsign(value, max_age=settings.admin_session_age)
        return int(uid), int(ver)
    except (BadSignature, SignatureExpired, ValueError):
        return None

def session_age_for(role: str) -> int:
    return (settings.admin_session_age if role == "admin"
            else settings.personel_session_age)

class RateLimiter:
    def __init__(self, limit: int = 10, window: int = 60):
        self.limit, self.window = limit, window
        self.hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        self.hits[key] = [t for t in self.hits[key] if now - t < self.window]
        if len(self.hits[key]) >= self.limit:
            return False
        self.hits[key].append(now)
        return True

login_limiter = RateLimiter()

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    cookie = request.cookies.get("session")
    parsed = read_session_cookie(cookie) if cookie else None
    user = db.get(User, parsed[0]) if parsed else None
    if (user is None or not user.is_active
            or user.registration_status != "approved"
            or user.session_version != parsed[1]):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user

def current_user_unlocked(user: User = Depends(current_user)) -> User:
    if user.must_change_password:
        raise HTTPException(status_code=303,
                            headers={"Location": "/sifre-degistir-zorunlu"})
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkisiz")
    return user
