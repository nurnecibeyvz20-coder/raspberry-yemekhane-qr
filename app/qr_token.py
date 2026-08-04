from itsdangerous import (URLSafeTimedSerializer, BadSignature,
                          SignatureExpired)
from app.config import settings

class InvalidToken(Exception):
    pass

class ExpiredToken(Exception):
    pass

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="qr-token")

def generate_token(user_id: int, qr_secret: str) -> str:
    if not qr_secret:
        raise ValueError("QR secret gerekli")
    return _serializer.dumps({"uid": user_id, "qr": qr_secret})

def verify_token(token: str) -> tuple[int, str]:
    try:
        data = _serializer.loads(token, max_age=settings.qr_token_ttl)
    except SignatureExpired as e:
        raise ExpiredToken() from e
    except (BadSignature, Exception) as e:
        raise InvalidToken() from e
    qr_secret = data.get("qr")
    if not isinstance(qr_secret, str) or not qr_secret:
        raise InvalidToken()
    return int(data["uid"]), qr_secret
