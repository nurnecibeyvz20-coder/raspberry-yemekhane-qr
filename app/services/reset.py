import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.models import ResetCode, User
from app.providers.messaging import (DemoMessageProvider, get_mail_provider,
                                     get_sms_provider)

SAATLIK_LIMIT = 3
KOD_OMRU = timedelta(minutes=10)
MAX_DENEME = 5

_TR_KUCUK = str.maketrans({"İ": "i", "I": "ı"})


def normalize(cevap: str) -> str:
    return cevap.strip().translate(_TR_KUCUK).lower()


def _telefon_maske(telefon: str) -> str:
    hane = "".join(c for c in telefon if c.isdigit())
    return f"{hane[:2]}** *** **{hane[-2:]}"


def _eposta_maske(eposta: str) -> str:
    yerel, _, alan = eposta.partition("@")
    govde, nokta, tld = alan.rpartition(".")
    if not nokta:  # TLD yok
        return f"{yerel[:1]}***@{alan[:1]}**"
    return f"{yerel[:1]}***@{govde[:1]}**.{tld}"


def _kod_hash(user_id: int, kod: str) -> str:
    return hashlib.sha256(f"{user_id}:{kod}".encode()).hexdigest()


def kanallar(user: User) -> list[dict]:
    liste: list[dict] = []
    if user.telefon:
        liste.append({"kanal": "sms", "maske": _telefon_maske(user.telefon)})
    if user.eposta:
        liste.append({"kanal": "eposta", "maske": _eposta_maske(user.eposta)})
    if user.gizli_soru and user.gizli_cevap_hash:
        liste.append({"kanal": "gizli_soru", "soru": user.gizli_soru})
    return liste


def kod_talep(db: Session, user: User, kanal: str) -> str | None:
    esik = datetime.now() - timedelta(hours=1)
    sayi = (db.query(ResetCode)
              .filter(ResetCode.user_id == user.id,
                      ResetCode.created_at >= esik)
              .count())
    if sayi >= SAATLIK_LIMIT:
        return None

    kod = f"{secrets.randbelow(1000000):06d}"
    if kanal == "sms":
        provider, hedef = get_sms_provider(), user.telefon
    else:
        provider, hedef = get_mail_provider(), user.eposta

    db.add(ResetCode(
        user_id=user.id,
        kanal=kanal,
        kod_hash=_kod_hash(user.id, kod),
        expires_at=datetime.now() + KOD_OMRU,
        demo_gosterim=(kod if isinstance(provider, DemoMessageProvider)
                       else None),
        created_at=datetime.now(),
    ))
    provider.gonder(hedef, kod)
    db.commit()
    return kod


def kod_dogrula(db: Session, user: User, girilen: str) -> bool:
    satir = (db.query(ResetCode)
               .filter(ResetCode.user_id == user.id,
                       ResetCode.used.is_(False),
                       ResetCode.expires_at > datetime.now())
               .order_by(ResetCode.id.desc())
               .first())
    if satir is None:
        return False
    if satir.kod_hash != _kod_hash(user.id, girilen):
        satir.attempts += 1
        if satir.attempts >= MAX_DENEME:
            satir.used = True  # kod iptal
        db.commit()
        return False
    satir.used = True
    db.commit()
    return True


def gizli_dogrula(user: User, cevap: str) -> bool:
    if not user.gizli_cevap_hash:
        return False
    return verify_password(normalize(cevap), user.gizli_cevap_hash)


def sifre_sifirla(db: Session, user: User, yeni: str) -> None:
    user.password_hash = hash_password(yeni)
    user.must_change_password = False
    user.session_version += 1
    db.commit()
