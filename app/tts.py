import hashlib
import hmac
import os
import threading
import wave
from datetime import time
from pathlib import Path

from itsdangerous import Signer

from app.config import settings
from app.services.checkin import CheckinResult

CACHE_DIR = Path("/tmp/tts-cache")
MODEL_PATH = os.environ.get("PIPER_MODEL", "/opt/piper/tr_TR-dfki-medium.onnx")

_signer = Signer(settings.secret_key, salt="tts")

# Model bir kez yüklenir ve bellekte tutulur (yükleme RPi'de ~12 sn;
# subprocess her çağrıda yeniden yüklüyordu -> 20 sn'lik anons gecikmesi).
_voice = None
_voice_lock = threading.Lock()


def _get_voice():
    global _voice
    if _voice is None:
        with _voice_lock:
            if _voice is None:
                from piper import PiperVoice
                _voice = PiperVoice.load(MODEL_PATH)
    return _voice


def preload_voice() -> None:
    """Uygulama açılışında arka planda çağrılır; ilk anons gecikmesin."""
    try:
        _get_voice()
    except Exception:
        pass  # model yoksa (test ortamı) sessizce geç; uret hata verir


_BIRLER = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_ONLAR = ["", "on", "yirmi", "otuz", "kırk", "elli"]


def _sayi_okunusu(n: int) -> str:
    return " ".join(p for p in (_ONLAR[n // 10], _BIRLER[n % 10]) if p)


def saat_okunusu(t: time) -> str:
    saat = _sayi_okunusu(t.hour) if t.hour else "sıfır"
    if t.minute == 0:
        return saat
    return f"{saat} {_sayi_okunusu(t.minute)}"


def anons_metni(result: CheckinResult,
                saatler: "tuple[time, time] | None" = None) -> str:
    if result.status == "saat_disi":
        if saatler is None:
            return "Yemekhane şu an kapalı."
        bas, bit = saatler
        return (f"Yemekhane şu an kapalı. Servis saatleri "
                f"{saat_okunusu(bas)}, {saat_okunusu(bit)} arasıdır.")
    if result.status == "onay":
        return (f"Afiyet olsun {result.ad_soyad}. "
                f"Kalan bakiyeniz {int(result.balance)} lira.")
    if result.status == "misafir_onay":
        return f"Afiyet olsun {result.ad_soyad}."
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
    return hmac.compare_digest(imzala(text), sig)


def uret(text: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / (hashlib.sha256(text.encode()).hexdigest() + ".wav")
    if path.exists():
        return path
    tmp = path.with_suffix(".tmp")
    try:
        voice = _get_voice()
        with _voice_lock:  # onnx oturumu tek is parcaciginda kullanilsin
            with wave.open(str(tmp), "wb") as wf:
                voice.synthesize_wav(text, wf)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, path)
    return path
