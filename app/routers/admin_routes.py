from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import hash_password, require_admin
from app.db import get_db
from app.deps import templates
from app.flash import get_flash, set_flash
from app.models import MealEntry, Setting, Transaction, User
from app.services.checkin import get_meal_price
from app.services.stats import dashboard_stats, paginate

router = APIRouter(dependencies=[Depends(require_admin)])

ROLES = ("personel", "admin")

SORT_COLS = {"sicil_no": User.sicil_no, "ad_soyad": User.ad_soyad,
             "balance": User.balance}

def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return user

def _detail_or_list_redirect(user_id: int, next: str) -> RedirectResponse:
    target = "/admin/personel" if next == "personel" \
        else f"/admin/users/{user_id}"
    return RedirectResponse(target, status_code=303)

def _render_with_flash(request: Request, template: str, context: dict):
    flash_data = get_flash(request)
    context["flash"] = flash_data
    resp = templates.TemplateResponse(request, template, context)
    if flash_data:
        resp.delete_cookie("flash")
    return resp

@router.get("/admin", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = dashboard_stats(db)
    # Son islemlerdeki kisi adlari icin id -> ad_soyad haritasi
    # (Transaction modelinde user iliskisi yok).
    ids = {t.user_id for t in stats["son_islemler"]}
    isim_map = dict(db.query(User.id, User.ad_soyad)
                      .filter(User.id.in_(ids)).all()) if ids else {}
    return _render_with_flash(
        request, "admin/dashboard.html",
        {"stats": stats,
         "isim_map": isim_map,
         "meal_price": get_meal_price(db),
         "aktif_sayfa": "genel"})

@router.get("/admin/personel", response_class=HTMLResponse)
def personel_list(request: Request, q: str = "", page: int = 1,
                  sort: str = "ad_soyad", dir: str = "asc",
                  db: Session = Depends(get_db)):
    col = SORT_COLS.get(sort, User.ad_soyad)
    if sort not in SORT_COLS:
        sort = "ad_soyad"
    if dir not in ("asc", "desc"):
        dir = "asc"
    query = db.query(User)
    if q:
        query = query.filter(or_(User.sicil_no.ilike(f"%{q}%"),
                                 User.ad_soyad.ilike(f"%{q}%")))
    query = query.order_by(col.desc() if dir == "desc" else col.asc())
    page_obj = paginate(query, page)
    return _render_with_flash(
        request, "admin/list.html",
        {"page_obj": page_obj, "q": q, "sort": sort, "dir": dir,
         "aktif_sayfa": "personel"})

@router.get("/admin/islemler", response_class=HTMLResponse)
def islemler_list(request: Request, page: int = 1, tur: str = "",
                  db: Session = Depends(get_db)):
    # Transaction modelinde `user` iliskisi yok; kullanici adini
    # gostermek icin User ile join edip (Transaction, User) ciftleri
    # olarak sablona geciyoruz.
    query = (db.query(Transaction, User)
               .join(User, Transaction.user_id == User.id))
    if tur:
        query = query.filter(Transaction.type == tur)
    query = query.order_by(Transaction.created_at.desc(),
                           Transaction.id.desc())
    page_obj = paginate(query, page)
    return _render_with_flash(
        request, "admin/islemler.html",
        {"page_obj": page_obj, "tur": tur, "aktif_sayfa": "islemler"})

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
    resp = RedirectResponse("/admin/personel", status_code=303)
    set_flash(resp, "Personel eklendi")
    return resp

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
    return _render_with_flash(
        request, "admin/detail.html",
        {"user": user, "transactions": transactions,
         "meal_entries": meal_entries})

@router.post("/admin/users/{user_id}/edit")
def edit_user(user_id: int,
              ad_soyad: str = Form(...),
              role: str = Form(...),
              next: str = Form(""),
              db: Session = Depends(get_db)):
    if role not in ROLES:
        raise HTTPException(400, "Geçersiz rol")
    user = _get_user_or_404(db, user_id)
    user.ad_soyad = ad_soyad.strip()
    user.role = role
    db.commit()
    resp = _detail_or_list_redirect(user_id, next)
    set_flash(resp, f"{user.ad_soyad} bilgileri güncellendi")
    return resp

@router.post("/admin/users/{user_id}/password")
def set_password(user_id: int,
                 new_password: str = Form(...),
                 next: str = Form(""),
                 db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    user.password_hash = hash_password(new_password)
    db.commit()
    resp = _detail_or_list_redirect(user_id, next)
    set_flash(resp, "Şifre sıfırlandı")
    return resp

@router.post("/admin/users/{user_id}/toggle-active")
def toggle_active(user_id: int, next: str = Form(""),
                  db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    user.is_active = not user.is_active
    db.commit()
    resp = _detail_or_list_redirect(user_id, next)
    mesaj = (f"{user.ad_soyad} aktifleştirildi" if user.is_active
             else f"{user.ad_soyad} pasife alındı")
    set_flash(resp, mesaj)
    return resp

@router.post("/admin/users/{user_id}/load-balance")
def load_balance(user_id: int, amount: str = Form(...),
                 next: str = Form(""),
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
    resp = _detail_or_list_redirect(user_id, next)
    if amt > 0:
        set_flash(resp, f"{user.ad_soyad} kişisine {amt} TL yüklendi")
    else:
        set_flash(resp, f"{user.ad_soyad} bakiyesi {amt} TL düzeltildi")
    return resp

@router.get("/admin/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    return _render_with_flash(
        request, "admin/settings.html",
        {"meal_price": get_meal_price(db), "error": None,
         "aktif_sayfa": "ayarlar"})

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
             "error": "Geçersiz fiyat", "aktif_sayfa": "ayarlar"},
            status_code=200)
    row = db.get(Setting, "meal_price")
    if row is None:
        row = Setting(key="meal_price", value=str(price))
        db.add(row)
    else:
        row.value = str(price)
    db.commit()
    resp = RedirectResponse("/admin/settings", status_code=303)
    set_flash(resp, "Yemek ücreti güncellendi")
    return resp
