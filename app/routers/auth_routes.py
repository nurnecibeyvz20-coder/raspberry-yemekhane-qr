from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (current_user, create_session_cookie, hash_password,
                      login_limiter, session_age_for, verify_password)
from app.db import get_db
from app.deps import templates
from app.models import User

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})

@router.post("/login")
def login(request: Request,
          sicil_no: str = Form(...),
          password: str = Form(...),
          db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not login_limiter.allow(client_ip):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Çok fazla deneme"},
            status_code=429,
        )

    user = db.execute(
        select(User).where(User.sicil_no == sicil_no)
    ).scalar_one_or_none()

    if (user is None or not user.is_active
            or not verify_password(password, user.password_hash)):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Hatalı sicil no veya şifre"},
            status_code=200,
        )

    target = "/admin" if user.role == "admin" else "/qr"
    response = RedirectResponse(url=target, status_code=303)
    response.set_cookie(
        "session",
        create_session_cookie(user.id, user.session_version),
        max_age=session_age_for(user.role),
        httponly=True,
        samesite="lax",
    )
    return response

@router.get("/sifre-degistir-zorunlu", response_class=HTMLResponse)
def forced_password_page(request: Request,
                         user: User = Depends(current_user)):
    return templates.TemplateResponse(request, "zorunlu_sifre.html",
                                      {"user": user, "error": None})

@router.post("/sifre-degistir-zorunlu")
def forced_password_change(request: Request,
                           new_password: str = Form(...),
                           user: User = Depends(current_user),
                           db: Session = Depends(get_db)):
    if len(new_password) < 8:
        return templates.TemplateResponse(
            request, "zorunlu_sifre.html",
            {"user": user, "error": "Şifre en az 8 karakter olmalı"})
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.session_version += 1
    db.commit()
    response = RedirectResponse("/qr", status_code=303)
    response.set_cookie(
        "session",
        create_session_cookie(user.id, user.session_version),
        max_age=session_age_for(user.role),
        httponly=True,
        samesite="lax",
    )
    return response

@router.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response
