from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (RateLimiter, current_user, create_session_cookie,
                      hash_password, login_limiter, session_age_for,
                      verify_password)
from app.config import settings
from app.db import get_db
from app.deps import templates
from app.flash import get_flash, set_flash
from app.models import User
from app.services import reset

router = APIRouter()

# --- Şifremi unuttum akış durumu (imzalı kısa ömürlü çerez) ---
RESET_STATE_OMRU = 900  # 15 dk
_reset_signer = TimestampSigner(settings.secret_key, salt="reset-state")
unuttum_limiter = RateLimiter(limit=10, window=60)

def _reset_state_yaz(response: Response, user: User,
                     asama: str, kanal: str = "") -> None:
    # session_version bağlanır: sifre_sifirla sürümü artırdığından
    # başarılı sıfırlama tüm açık state çerezlerini geçersiz kılar.
    value = _reset_signer.sign(
        f"{user.id}:{asama}:{kanal}:{user.session_version}").decode()
    response.set_cookie("reset_state", value, max_age=RESET_STATE_OMRU,
                        httponly=True, samesite="lax")

def _reset_state_oku(request: Request) -> tuple[int, str, str, int] | None:
    raw = request.cookies.get("reset_state")
    if not raw:
        return None
    try:
        data = _reset_signer.unsign(raw, max_age=RESET_STATE_OMRU).decode()
        uid, asama, kanal, surum = data.split(":", 3)
        return int(uid), asama, kanal, int(surum)
    except (BadSignature, SignatureExpired, ValueError):
        return None

def _reset_user(db: Session,
                durum: tuple[int, str, str, int]) -> User | None:
    user = db.get(User, durum[0])
    if user is None or not user.is_active:
        return None
    if user.session_version != durum[3]:  # sürüm eski → state geçersiz
        return None
    return user

def _basa_don() -> RedirectResponse:
    return RedirectResponse("/sifremi-unuttum", status_code=303)

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    flash_data = get_flash(request)
    resp = templates.TemplateResponse(request, "login.html",
                                      {"error": None, "flash": flash_data})
    if flash_data:
        resp.delete_cookie("flash")
    return resp


@router.get("/kayit", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/kayit")
def register(request: Request,
             sicil_no: str = Form(...),
             ad_soyad: str = Form(...),
             password: str = Form(...),
             db: Session = Depends(get_db)):
    if len(password) < 8:
        return templates.TemplateResponse(
            request, "register.html", {"error": "Şifre en az 8 karakter olmalı"})
    user = User(sicil_no=sicil_no.strip(), ad_soyad=ad_soyad.strip(),
                role="personel", password_hash=hash_password(password),
                is_active=False, registration_status="pending")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "register.html", {"error": "Bu sicil no zaten kayıtlı"})
    response = RedirectResponse("/login", status_code=303)
    set_flash(response, "Başvurunuz alındı, yönetici onayı bekleniyor")
    return response

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

    if user is not None and verify_password(password, user.password_hash):
        if user.registration_status == "pending":
            return templates.TemplateResponse(
                request, "login.html", {"error": "Hesabınız yönetici onayı bekliyor"})
        if user.registration_status == "rejected":
            return templates.TemplateResponse(
                request, "login.html", {"error": "Başvurunuz reddedildi"})
        if not user.is_active:
            return templates.TemplateResponse(
                request, "login.html", {"error": "Hesabınız pasif durumda"})
    if (user is None or not user.is_active
            or user.registration_status != "approved"
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
        create_session_cookie(user.id, user.session_version, user.role),
        max_age=session_age_for(user.role),
        httponly=True,
        samesite="lax",
    )
    set_flash(response, "Şifreniz başarıyla değiştirildi.")
    return response

@router.get("/sifre-degistir-zorunlu", response_class=HTMLResponse)
def forced_password_page(request: Request,
                         user: User = Depends(current_user)):
    if not user.must_change_password:
        return RedirectResponse("/qr", status_code=303)
    return templates.TemplateResponse(request, "zorunlu_sifre.html",
                                      {"user": user, "error": None})

@router.post("/sifre-degistir-zorunlu")
def forced_password_change(request: Request,
                           new_password: str = Form(...),
                           user: User = Depends(current_user),
                           db: Session = Depends(get_db)):
    if not user.must_change_password:
        return RedirectResponse("/qr", status_code=303)
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
        create_session_cookie(user.id, user.session_version, user.role),
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

# --- Şifremi unuttum akışı ---

@router.get("/sifremi-unuttum", response_class=HTMLResponse)
def unuttum_sicil(request: Request):
    return templates.TemplateResponse(request, "app/unuttum_sicil.html", {})

@router.post("/sifremi-unuttum", response_class=HTMLResponse)
def unuttum_sicil_post(request: Request,
                       sicil_no: str = Form(...),
                       db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not unuttum_limiter.allow(client_ip):
        return templates.TemplateResponse(
            request, "app/unuttum_sicil.html",
            {"error": "Çok fazla deneme"},
            status_code=429,
        )
    user = db.execute(
        select(User).where(User.sicil_no == sicil_no,
                           User.is_active.is_(True))
    ).scalar_one_or_none()
    yontemler = reset.kanallar(user) if user else []
    # Kullanıcı yoksa VEYA yöntemi yoksa AYNI yanıt (varlık sızdırılmaz)
    if not yontemler:
        return templates.TemplateResponse(
            request, "app/unuttum_yontem.html", {"yontemler": []})
    resp = templates.TemplateResponse(
        request, "app/unuttum_yontem.html", {"yontemler": yontemler})
    _reset_state_yaz(resp, user, "yontem")
    return resp

@router.post("/sifremi-unuttum/yontem")
def unuttum_yontem_post(request: Request,
                        kanal: str = Form(...),
                        db: Session = Depends(get_db)):
    durum = _reset_state_oku(request)
    if durum is None or durum[1] not in ("yontem", "dogrulama"):
        return _basa_don()
    user = _reset_user(db, durum)
    if user is None:
        return _basa_don()

    yontemler = reset.kanallar(user)
    secili = next((y for y in yontemler if y["kanal"] == kanal), None)
    if kanal not in ("sms", "eposta", "gizli_soru") or secili is None:
        return _basa_don()

    if kanal == "gizli_soru":
        resp = templates.TemplateResponse(
            request, "app/unuttum_soru.html",
            {"soru": secili["soru"], "error": None})
        _reset_state_yaz(resp, user, "dogrulama", "gizli_soru")
        return resp

    kod = reset.kod_talep(db, user, kanal)
    if kod is None:
        resp = templates.TemplateResponse(
            request, "app/unuttum_yontem.html",
            {"yontemler": yontemler,
             "error": "Çok fazla deneme, daha sonra tekrar deneyin"})
        _reset_state_yaz(resp, user, "yontem")
        return resp

    resp = templates.TemplateResponse(
        request, "app/unuttum_kod.html",
        {"maske": secili["maske"], "kanal": kanal, "error": None,
         "demo_kod": kod if (
             kanal == "sms" and settings.sms_provider == "demo"
         ) or (
             kanal == "eposta" and settings.mail_provider == "demo"
         ) else None})
    _reset_state_yaz(resp, user, "dogrulama", kanal)
    return resp

@router.post("/sifremi-unuttum/kod")
def unuttum_kod_post(request: Request,
                     kod: str = Form(...),
                     db: Session = Depends(get_db)):
    durum = _reset_state_oku(request)
    if durum is None or durum[1] != "dogrulama" \
            or durum[2] not in ("sms", "eposta"):
        return _basa_don()
    user = _reset_user(db, durum)
    if user is None:
        return _basa_don()

    if not reset.kod_dogrula(db, user, kod):
        secili = next((y for y in reset.kanallar(user)
                       if y["kanal"] == durum[2]), None)
        maske = secili["maske"] if secili else ""
        return templates.TemplateResponse(
            request, "app/unuttum_kod.html",
            {"maske": maske, "kanal": durum[2],
             "error": "Kod hatalı veya süresi dolmuş"})

    resp = templates.TemplateResponse(
        request, "app/unuttum_yeni.html", {"error": None})
    _reset_state_yaz(resp, user, "yeni")
    return resp

@router.post("/sifremi-unuttum/soru")
def unuttum_soru_post(request: Request,
                      cevap: str = Form(...),
                      db: Session = Depends(get_db)):
    durum = _reset_state_oku(request)
    if durum is None or durum[1] != "dogrulama" or durum[2] != "gizli_soru":
        return _basa_don()
    user = _reset_user(db, durum)
    if user is None:
        return _basa_don()

    if not reset.gizli_dogrula(user, cevap):
        return templates.TemplateResponse(
            request, "app/unuttum_soru.html",
            {"soru": user.gizli_soru, "error": "Cevap hatalı"})

    resp = templates.TemplateResponse(
        request, "app/unuttum_yeni.html", {"error": None})
    _reset_state_yaz(resp, user, "yeni")
    return resp

@router.post("/sifremi-unuttum/yeni")
def unuttum_yeni_post(request: Request,
                      new_password: str = Form(...),
                      db: Session = Depends(get_db)):
    durum = _reset_state_oku(request)
    if durum is None or durum[1] != "yeni":
        return _basa_don()
    user = _reset_user(db, durum)
    if user is None:
        return _basa_don()

    if len(new_password) < 8:
        return templates.TemplateResponse(
            request, "app/unuttum_yeni.html",
            {"error": "Şifre en az 8 karakter olmalı"})

    reset.sifre_sifirla(db, user, new_password)
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("reset_state")
    set_flash(resp, "Şifreniz değişti, giriş yapın")
    return resp
