from itsdangerous import (URLSafeTimedSerializer, BadSignature,
                          SignatureExpired)
from app.config import settings

class InvalidToken(Exception):
    pass

class ExpiredToken(Exception):
    pass

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="qr-token")

def generate_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})

def verify_token(token: str) -> int:
    try:
        data = _serializer.loads(token, max_age=settings.qr_token_ttl)
    except SignatureExpired as e:
        raise ExpiredToken() from e
    except (BadSignature, Exception) as e:
        raise InvalidToken() from e
    return int(data["uid"])
