from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import login_limiter, verify_password, create_session_cookie
from app.config import settings
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
        create_session_cookie(user.id),
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
    )
    return response

@router.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response
