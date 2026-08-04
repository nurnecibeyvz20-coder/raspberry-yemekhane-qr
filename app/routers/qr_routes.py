from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import (create_session_cookie, current_user,
                      current_user_unlocked, hash_password,
                      session_age_for, verify_password)
from app.config import settings
from app.db import get_db
from app.deps import templates
from app.flash import get_flash, set_flash
from app.models import MealEntry, Transaction, User
from app.qr_token import generate_token
from app.services.checkin import get_meal_price
from app.services.reset import normalize as reset_normalize
from app.services.user_qr import regenerate_qr_secret

def _ate_today(db: Session, user_id: int) -> bool:
    return (db.query(MealEntry)
              .filter_by(user_id=user_id, entry_date=date.today())
              .first() is not None)

router = APIRouter()

@router.get("/qr", response_class=HTMLResponse)
def qr_page(request: Request,
            user: User = Depends(current_user_unlocked),
            db: Session = Depends(get_db)):
    price = get_meal_price(db)
    return templates.TemplateResponse(request, "qr.html", {
        "user": user,
        "meal_price": price,
        "low_balance": user.balance < price,
        "ogun_sayisi": int(user.balance // price),
        "ate_today": _ate_today(db, user.id),
        "aktif_sekme": "qr",
    })

@router.get("/gecmis", response_class=HTMLResponse)
def gecmis_page(request: Request,
                user: User = Depends(current_user_unlocked),
                db: Session = Depends(get_db)):
    ay_basi = date.today().replace(day=1)
    gecmis = (db.query(Transaction)
                .filter_by(user_id=user.id)
                .order_by(Transaction.created_at.desc(),
                          Transaction.id.desc())
                .limit(20).all())
    ay_ogun = (db.query(MealEntry)
                 .filter(MealEntry.user_id == user.id,
                         MealEntry.entry_date >= ay_basi)
                 .count())
    ay_yukleme = (db.query(func.coalesce(func.sum(Transaction.amount), 0))
                    .filter(Transaction.user_id == user.id,
                            Transaction.type == "yukleme",
                            Transaction.created_at >= ay_basi)
                    .scalar()) or Decimal("0")
    return templates.TemplateResponse(request, "app/gecmis.html", {
        "user": user,
        "gecmis": gecmis,
        "ay_ogun": ay_ogun,
        "ay_yukleme": ay_yukleme,
        "aktif_sekme": "gecmis",
    })

@router.get("/profil", response_class=HTMLResponse)
def profil_page(request: Request,
                user: User = Depends(current_user_unlocked)):
    flash_data = get_flash(request)
    resp = templates.TemplateResponse(request, "app/profil.html", {
        "user": user,
        "error": None,
        "flash": flash_data,
        "aktif_sekme": "profil",
    })
    if flash_data:
        resp.delete_cookie("flash")
    return resp

@router.post("/profil/kurtarma")
def profil_kurtarma(request: Request,
                    telefon: str = Form(""),
                    eposta: str = Form(""),
                    gizli_soru: str = Form(""),
                    gizli_cevap: str = Form(""),
                    mevcut_sifre: str = Form(""),
                    user: User = Depends(current_user_unlocked),
                    db: Session = Depends(get_db)):
    if not verify_password(mevcut_sifre, user.password_hash):
        return templates.TemplateResponse(request, "app/profil.html", {
            "user": user,
            "error": "Mevcut şifre hatalı",
            "flash": None,
            "aktif_sekme": "profil",
        })
    user.telefon = telefon.strip() or None
    user.eposta = eposta.strip() or None
    user.gizli_soru = gizli_soru.strip() or None
    if gizli_cevap.strip():
        user.gizli_cevap_hash = hash_password(reset_normalize(gizli_cevap))
    db.commit()
    resp = RedirectResponse("/profil", status_code=303)
    set_flash(resp, "Bilgileriniz güncellendi")
    return resp

@router.get("/api/qr-token")
def qr_token(user: User = Depends(current_user_unlocked),
              db: Session = Depends(get_db)):
    if not user.qr_secret:
        regenerate_qr_secret(user)
        db.commit()
    price = get_meal_price(db)
    return {
        "token": generate_token(user.id, user.qr_secret),
        "balance": str(user.balance),
        "low_balance": user.balance < price,
        "ate_today": _ate_today(db, user.id),
        "ttl": settings.qr_token_ttl,
    }

@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request,
                         user: User = Depends(current_user)):
    return templates.TemplateResponse(request, "change_password.html",
                                      {"user": user, "error": None})

@router.post("/change-password")
def change_password(request: Request,
                    old_password: str = Form(...),
                    new_password: str = Form(...),
                    user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(old_password, user.password_hash):
        return templates.TemplateResponse(
            request, "change_password.html",
            {"user": user, "error": "Eski şifre hatalı"})
    if len(new_password) < 8:
        return templates.TemplateResponse(
            request, "change_password.html",
            {"user": user, "error": "Şifre en az 8 karakter olmalı"})
    user.password_hash = hash_password(new_password)
    user.session_version += 1
    db.commit()
    response = RedirectResponse("/qr", status_code=303)
    response.set_cookie(
        "session",
        create_session_cookie(user.id, user.session_version, user.role),
        max_age=session_age_for(user.role),
        httponly=True,
        samesite="lax",
    )
    return response
