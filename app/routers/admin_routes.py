from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import hash_password, require_admin
from app.db import get_db
from app.deps import templates
from app.models import MealEntry, Setting, Transaction, User
from app.services.checkin import get_meal_price

router = APIRouter(dependencies=[Depends(require_admin)])

ROLES = ("personel", "admin")

def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return user

@router.get("/admin", response_class=HTMLResponse)
def user_list(request: Request, q: str = "",
              db: Session = Depends(get_db)):
    query = db.query(User)
    if q:
        query = query.filter(or_(User.sicil_no.ilike(f"%{q}%"),
                                 User.ad_soyad.ilike(f"%{q}%")))
    users = query.order_by(User.ad_soyad).all()
    return templates.TemplateResponse(
        request, "admin/list.html", {"users": users, "q": q})

@router.get("/admin/users/new", response_class=HTMLResponse)
def new_user_page(request: Request):
    return templates.TemplateResponse(
        request, "admin/form.html", {"error": None, "form": {}})

@router.post("/admin/users/new")
def create_user(request: Request,
                sicil_no: str = Form(...),
                ad_soyad: str = Form(...),
                password: str = Form(...),
                role: str = Form(...),
                db: Session = Depends(get_db)):
    if role not in ROLES:
        raise HTTPException(400, "Geçersiz rol")
    user = User(sicil_no=sicil_no.strip(), ad_soyad=ad_soyad.strip(),
                role=role, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "admin/form.html",
            {"error": "Bu sicil no zaten kayıtlı",
             "form": {"sicil_no": sicil_no, "ad_soyad": ad_soyad,
                      "role": role}},
            status_code=200)
    return RedirectResponse("/admin", status_code=303)

@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
def user_detail(request: Request, user_id: int,
                db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    transactions = (db.query(Transaction)
                      .filter_by(user_id=user.id)
                      .order_by(Transaction.created_at.desc(),
                                Transaction.id.desc())
                      .limit(50).all())
    meal_entries = (db.query(MealEntry)
                      .filter_by(user_id=user.id)
                      .order_by(MealEntry.entry_date.desc(),
                                MealEntry.id.desc())
                      .limit(50).all())
    return templates.TemplateResponse(
        request, "admin/detail.html",
        {"user": user, "transactions": transactions,
         "meal_entries": meal_entries})

@router.post("/admin/users/{user_id}/edit")
def edit_user(user_id: int,
              ad_soyad: str = Form(...),
              role: str = Form(...),
              db: Session = Depends(get_db)):
    if role not in ROLES:
        raise HTTPException(400, "Geçersiz rol")
    user = _get_user_or_404(db, user_id)
    user.ad_soyad = ad_soyad.strip()
    user.role = role
    db.commit()
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)

@router.post("/admin/users/{user_id}/password")
def set_password(user_id: int,
                 new_password: str = Form(...),
                 db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)

@router.post("/admin/users/{user_id}/toggle-active")
def toggle_active(user_id: int, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    user.is_active = not user.is_active
    db.commit()
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)

@router.post("/admin/users/{user_id}/load-balance")
def load_balance(user_id: int, amount: str = Form(...),
                 admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    try:
        amt = Decimal(amount)
    except InvalidOperation:
        raise HTTPException(400, "Geçersiz tutar")
    if not amt.is_finite():
        raise HTTPException(400, "Geçersiz tutar")
    if amt == 0:
        raise HTTPException(400, "Tutar sıfır olamaz")
    user = _get_user_or_404(db, user_id)
    new_balance = user.balance + amt
    db.add(Transaction(
        user_id=user.id,
        type="yukleme" if amt > 0 else "duzeltme",
        amount=amt, balance_after=new_balance, created_by=admin.id))
    user.balance = new_balance
    db.commit()
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)

@router.get("/admin/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "admin/settings.html",
        {"meal_price": get_meal_price(db), "error": None,
         "saved": False})

@router.post("/admin/settings")
def update_settings(request: Request,
                    meal_price: str = Form(...),
                    db: Session = Depends(get_db)):
    try:
        price = Decimal(meal_price)
        if not price.is_finite():
            raise InvalidOperation
    except InvalidOperation:
        return templates.TemplateResponse(
            request, "admin/settings.html",
            {"meal_price": get_meal_price(db),
             "error": "Geçersiz fiyat", "saved": False},
            status_code=200)
    row = db.get(Setting, "meal_price")
    if row is None:
        row = Setting(key="meal_price", value=str(price))
        db.add(row)
    else:
        row.value = str(price)
    db.commit()
    return templates.TemplateResponse(
        request, "admin/settings.html",
        {"meal_price": price, "error": None, "saved": True})
