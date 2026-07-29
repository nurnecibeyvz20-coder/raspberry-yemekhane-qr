from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user, hash_password, verify_password
from app.config import settings
from app.db import get_db
from app.deps import templates
from app.models import User
from app.qr_token import generate_token
from app.services.checkin import get_meal_price

router = APIRouter()

@router.get("/qr", response_class=HTMLResponse)
def qr_page(request: Request,
            user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    price = get_meal_price(db)
    return templates.TemplateResponse(request, "qr.html", {
        "user": user,
        "meal_price": price,
        "low_balance": user.balance < price,
    })

@router.get("/api/qr-token")
def qr_token(user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    price = get_meal_price(db)
    return {
        "token": generate_token(user.id),
        "balance": str(user.balance),
        "low_balance": user.balance < price,
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
    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse("/qr", status_code=303)
