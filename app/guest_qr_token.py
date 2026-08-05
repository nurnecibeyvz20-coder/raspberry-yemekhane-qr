from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="guest-qr-token")


class InvalidGuestToken(Exception):
    pass


def generate_guest_token(request_id: int, secret: str) -> str:
    return _serializer.dumps({"rid": request_id, "secret": secret})


def verify_guest_token(token: str) -> tuple[int, str]:
    try:
        data = _serializer.loads(token, max_age=86400)
        return int(data["rid"]), str(data["secret"])
    except (BadSignature, SignatureExpired, KeyError, ValueError, TypeError) as exc:
        raise InvalidGuestToken() from exc
