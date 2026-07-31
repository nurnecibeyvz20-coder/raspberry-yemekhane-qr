from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user_unlocked
from app.db import get_db
from app.deps import templates
from app.models import Payment, User
from app.services import payment_flow
from app.services.checkin import get_meal_price

router = APIRouter()

HIZLI_TUTARLAR = [125, 250, 500, 1000]


def _yukle_sayfasi(request: Request, user: User, error: str | None = None,
                   status_code: int = 200):
    return templates.TemplateResponse(
        request, "app/odeme_tutar.html",
        {"user": user, "hizli_tutarlar": HIZLI_TUTARLAR, "error": error,
         "aktif_sekme": "yukle"},
        status_code=status_code)


def _payment_getir(db: Session, payment_id: int, user: User) -> Payment | None:
    payment = db.get(Payment, payment_id)
    if payment is None or payment.user_id != user.id:
        return None
    return payment


@router.get("/yukle", response_class=HTMLResponse)
def yukle_sayfa(request: Request,
                user: User = Depends(current_user_unlocked)):
    return _yukle_sayfasi(request, user)


@router.post("/yukle")
def yukle_baslat(request: Request,
                 tutar: str = Form(""),
                 user: User = Depends(current_user_unlocked),
                 db: Session = Depends(get_db)):
    try:
        miktar = Decimal(tutar.strip().replace(",", "."))
        payment = payment_flow.baslat(db, user, miktar)
    except (InvalidOperation, ValueError):
        return _yukle_sayfasi(request, user,
                              error="Tutar 50-5000 TL arasında olmalı")
    return RedirectResponse(f"/yukle/{payment.id}/pos", status_code=303)


@router.get("/yukle/{payment_id}/pos", response_class=HTMLResponse)
def pos_sayfa(request: Request, payment_id: int,
              user: User = Depends(current_user_unlocked),
              db: Session = Depends(get_db)):
    payment = _payment_getir(db, payment_id, user)
    if payment is None or payment.durum != "baslatildi":
        return RedirectResponse("/yukle", status_code=303)
    return templates.TemplateResponse(request, "app/odeme_pos.html",
                                      {"user": user, "payment": payment,
                                       "aktif_sekme": "yukle"})


@router.post("/yukle/{payment_id}/pos")
def pos_tamamla(request: Request, payment_id: int,
                kart_no: str = Form(""),
                user: User = Depends(current_user_unlocked),
                db: Session = Depends(get_db)):
    payment = _payment_getir(db, payment_id, user)
    if payment is None or payment.durum != "baslatildi":
        return RedirectResponse("/yukle", status_code=303)
    payment_flow.tamamla(db, payment.id, kart_no)
    return RedirectResponse(f"/yukle/{payment_id}/sonuc", status_code=303)


@router.get("/yukle/{payment_id}/sonuc", response_class=HTMLResponse)
def sonuc_sayfa(request: Request, payment_id: int,
                user: User = Depends(current_user_unlocked),
                db: Session = Depends(get_db)):
    payment = _payment_getir(db, payment_id, user)
    if payment is None:
        return RedirectResponse("/yukle", status_code=303)
    if payment.durum in ("baslatildi", "isleniyor"):  # yarım kalmış ödeme
        return RedirectResponse(f"/yukle/{payment_id}/pos", status_code=303)
    price = get_meal_price(db)
    return templates.TemplateResponse(request, "app/odeme_sonuc.html", {
        "user": user,
        "payment": payment,
        "ogun_sayisi": int(user.balance // price),
        "aktif_sekme": "yukle",
    })
