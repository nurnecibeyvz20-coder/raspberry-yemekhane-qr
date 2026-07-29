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

def create_session_cookie(user_id: int) -> str:
    return _signer.sign(str(user_id)).decode()

def read_session_cookie(value: str) -> int | None:
    try:
        raw = _signer.unsign(value, max_age=settings.session_max_age)
        return int(raw)
    except (BadSignature, SignatureExpired, ValueError):
        return None

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
    user_id = read_session_cookie(cookie) if cookie else None
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkisiz")
    return user
