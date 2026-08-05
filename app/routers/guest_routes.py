from datetime import date, time

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user_unlocked
from app.db import get_db
from app.deps import templates
from app.guest_qr_token import generate_guest_token
from app.models import GuestRequest, User
from app.services.checkin import get_service_hours
from app.services.guest_requests import event

router = APIRouter()


@router.get("/misafir", response_class=HTMLResponse)
def guest_page(request: Request, user: User = Depends(current_user_unlocked),
               db: Session = Depends(get_db)):
    bas, bit = get_service_hours(db)
    requests = db.query(GuestRequest).filter_by(owner_id=user.id).order_by(GuestRequest.created_at.desc()).all()
    return templates.TemplateResponse(request, "app/misafir.html", {"user": user, "requests": requests,
        "today": date.today().isoformat(), "bas": bas.strftime("%H:%M"), "bit": bit.strftime("%H:%M"), "error": None, "aktif_sekme": "misafir"})


@router.post("/misafir")
def create_guest(request: Request, ad: str = Form(...), soyad: str = Form(...), tc_kimlik_no: str = Form(""),
                 telefon: str = Form(...), ziyaret_nedeni: str = Form(...), ziyaret_tarihi: date = Form(...),
                 yemek_adedi: int = Form(...), user: User = Depends(current_user_unlocked), db: Session = Depends(get_db)):
    if ziyaret_tarihi < date.today() or yemek_adedi < 1:
        raise HTTPException(400, "Geçersiz misafir talebi")
    bas, bit = get_service_hours(db)
    guest = GuestRequest(owner_id=user.id, ad=ad.strip(), soyad=soyad.strip(), tc_kimlik_no=tc_kimlik_no.strip() or None,
        telefon=telefon.strip(), ziyaret_nedeni=ziyaret_nedeni.strip(), ziyaret_tarihi=ziyaret_tarihi,
        yemek_adedi=yemek_adedi, baslangic_saati=bas, bitis_saati=bit)
    db.add(guest); db.flush(); event(db, guest, "created", "Misafir talebi oluşturuldu", user.id); db.commit()
    return RedirectResponse("/misafir", status_code=303)


@router.get("/misafir/{request_id}", response_class=HTMLResponse)
def guest_detail(request_id: int, request: Request, user: User = Depends(current_user_unlocked), db: Session = Depends(get_db)):
    guest = db.get(GuestRequest, request_id)
    if guest is None or guest.owner_id != user.id:
        raise HTTPException(404, "Misafir talebi bulunamadı")
    token = generate_guest_token(guest.id, guest.qr_secret) if guest.durum == "approved" and guest.qr_secret else None
    return templates.TemplateResponse(request, "app/misafir_detay.html", {"user": user, "guest": guest, "token": token, "aktif_sekme": "misafir"})
