import secrets
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.guest_qr_token import InvalidGuestToken, verify_guest_token
from app.models import GuestRequest, GuestRequestEvent


class GuestCheckinResult:
    def __init__(self, ok: bool, status: str, message: str, ad_soyad: str = ""):
        self.ok, self.status, self.message, self.ad_soyad = ok, status, message, ad_soyad
        self.balance = None


def event(db: Session, request: GuestRequest, event_type: str, description: str, actor_id: int | None = None) -> None:
    db.add(GuestRequestEvent(request_id=request.id, actor_id=actor_id,
                             event_type=event_type, description=description))


def approve_request(db: Session, request: GuestRequest, actor_id: int) -> None:
    request.durum = "approved"
    request.kalan_hak = request.yemek_adedi
    request.qr_secret = secrets.token_urlsafe(32)
    event(db, request, "approved", "Talep onaylandı", actor_id)


def reject_request(db: Session, request: GuestRequest, actor_id: int, reason: str = "") -> None:
    request.durum = "rejected"
    request.red_nedeni = reason.strip() or None
    event(db, request, "rejected", "Talep reddedildi", actor_id)


def use_guest_qr(db: Session, token: str) -> GuestCheckinResult:
    try:
        request_id, secret = verify_guest_token(token)
    except InvalidGuestToken:
        return GuestCheckinResult(False, "gecersiz", "Geçersiz misafir QR kodu")
    request = db.get(GuestRequest, request_id)
    if request is None or request.qr_secret != secret:
        return GuestCheckinResult(False, "gecersiz", "Geçersiz misafir QR kodu")
    if request.ziyaret_tarihi < date.today() and request.durum == "approved":
        request.durum = "expired"; event(db, request, "expired", "Talep süresi doldu"); db.commit()
    if request.durum != "approved":
        return GuestCheckinResult(False, "misafir_gecersiz", "Misafir QR kodu aktif değil")
    now = datetime.now().time()
    if request.ziyaret_tarihi != date.today() or not request.baslangic_saati <= now <= request.bitis_saati:
        return GuestCheckinResult(False, "misafir_saat_disi", "Misafir QR kodu bu saatte geçerli değil")
    if request.kalan_hak <= 0:
        return GuestCheckinResult(False, "misafir_hakki_bitti", "Misafir yemek hakkı tükendi")
    request.kalan_hak -= 1
    if request.kalan_hak == 0:
        request.durum = "exhausted"
    event(db, request, "used", "Misafir QR kodu kullanıldı")
    db.commit()
    return GuestCheckinResult(True, "misafir_onay", f"Afiyet olsun, {request.ad}", f"{request.ad} {request.soyad}")
