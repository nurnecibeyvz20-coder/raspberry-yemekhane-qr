import base64

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from app.config import settings

_signer = TimestampSigner(settings.secret_key, salt="flash")

def set_flash(response: Response, mesaj: str, tur: str = "basari") -> None:
    # Cookie basliklari latin-1 ile kodlanir; Turkce karakterler icin
    # payload'i base64url ile sarmalayip oyle imzaliyoruz.
    payload = base64.urlsafe_b64encode(f"{tur}|{mesaj}".encode()).decode()
    value = _signer.sign(payload).decode()
    response.set_cookie("flash", value, max_age=60, httponly=True,
                        samesite="lax")

def get_flash(request: Request) -> dict | None:
    raw = request.cookies.get("flash")
    if not raw:
        return None
    try:
        payload = _signer.unsign(raw, max_age=60)
        data = base64.urlsafe_b64decode(payload).decode()
    except (BadSignature, SignatureExpired, ValueError):
        return None
    tur, _, mesaj = data.partition("|")
    return {"mesaj": mesaj, "tur": tur}
