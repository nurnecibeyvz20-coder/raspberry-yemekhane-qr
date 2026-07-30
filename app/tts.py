import hashlib
import os
import subprocess
from pathlib import Path

from itsdangerous import BadSignature, Signer

from app.config import settings
from app.services.checkin import CheckinResult

CACHE_DIR = Path("/tmp/tts-cache")
MODEL_PATH = os.environ.get("PIPER_MODEL", "/opt/piper/tr_TR-dfki-medium.onnx")

_signer = Signer(settings.secret_key, salt="tts")


def anons_metni(result: CheckinResult) -> str:
    if result.status == "onay":
        return (f"Afiyet olsun {result.ad_soyad}. "
                f"Kalan bakiyeniz {int(result.balance)} lira.")
    if result.status == "yetersiz_bakiye":
        return (f"{result.ad_soyad}, bakiyeniz yetersiz."
                if result.ad_soyad else "Bakiyeniz yetersiz.")
    if result.status == "mukerrer":
        return (f"{result.ad_soyad}, bugün zaten giriş yaptınız."
                if result.ad_soyad else "Bugün zaten giriş yaptınız.")
    if result.status == "suresi_dolmus":
        return "QR kodun süresi dolmuş, lütfen yenileyin."
    if result.status == "hesap_pasif":
        return "Hesabınız pasif durumda."
    return "Geçersiz QR kodu."


def imzala(text: str) -> str:
    return _signer.sign(text.encode()).decode().rsplit(".", 1)[1]


def dogrula(text: str, sig: str) -> bool:
    try:
        _signer.unsign(f"{text}.{sig}".encode())
        return True
    except (BadSignature, UnicodeError):
        return False


def uret(text: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / (hashlib.sha256(text.encode()).hexdigest() + ".wav")
    if path.exists():
        return path
    subprocess.run(
        ["piper", "--model", MODEL_PATH, "--output_file", str(path)],
        input=text.encode(), check=True, timeout=15)
    return path
