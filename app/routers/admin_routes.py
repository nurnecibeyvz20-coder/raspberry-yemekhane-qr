from datetime import time
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
from app.services.checkin import get_meal_price, get_service_hours
from app.services.reset import normalize as reset_normalize
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

@router.post("/admin/users/new")
def create_user(sicil_no: str = Form(...),
                ad_soyad: str = Form(...),
                password: str = Form(...),
                role: str = Form(...),
                telefon: str = Form(""),
                eposta: str = Form(""),
                gizli_soru: str = Form(""),
                gizli_cevap: str = Form(""),
                db: Session = Depends(get_db)):
    if role not in ROLES:
        raise HTTPException(400, "Geçersiz rol")
    # Gizli soru yalnız cevabıyla birlikte anlamlı: ikisi de doluysa
    # kaydedilir, aksi halde ikisi de boş bırakılır (hata verilmez).
    soru = gizli_soru.strip()
    cevap = gizli_cevap.strip()
    if soru and cevap:
        soru_kayit = soru
        cevap_hash = hash_password(reset_normalize(cevap))
    else:
        soru_kayit = cevap_hash = None
    user = User(sicil_no=sicil_no.strip(), ad_soyad=ad_soyad.strip(),
                role=role, password_hash=hash_password(password),
                telefon=telefon.strip() or None,
                eposta=eposta.strip() or None,
                gizli_soru=soru_kayit,
                gizli_cevap_hash=cevap_hash)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        resp = RedirectResponse("/admin/personel", status_code=303)
        set_flash(resp, "Bu sicil no zaten kayıtlı", "hata")
        return resp
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
         "meal_entries": meal_entries, "aktif_sayfa": "personel"})

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
    user.must_change_password = True
    user.session_version += 1
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

def _current_hours(db: Session) -> tuple[time, time]:
    """Kayıtlı servis saatlerini OKUR; kayıt yoksa varsayılanı döndürür
    ama yazmaz (hatalı POST'ta yan etki olmasın diye get_service_hours
    yerine bu kullanılır)."""
    bas = db.get(Setting, "saat_baslangic")
    bit = db.get(Setting, "saat_bitis")
    return (time.fromisoformat(bas.value) if bas else time(12, 0),
            time.fromisoformat(bit.value) if bit else time(13, 30))

def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value

def _settings_context(db: Session, error: str | None) -> dict:
    bas, bit = _current_hours(db)
    return {"meal_price": get_meal_price(db),
            "saat_baslangic": bas.strftime("%H:%M"),
            "saat_bitis": bit.strftime("%H:%M"),
            "error": error, "aktif_sayfa": "ayarlar"}

@router.get("/admin/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    bas, bit = get_service_hours(db)
    return _render_with_flash(
        request, "admin/settings.html",
        {"meal_price": get_meal_price(db),
         "saat_baslangic": bas.strftime("%H:%M"),
         "saat_bitis": bit.strftime("%H:%M"),
         "error": None, "aktif_sayfa": "ayarlar"})

@router.post("/admin/settings")
def update_settings(request: Request,
                    meal_price: str = Form(...),
                    saat_baslangic: str = Form(""),
                    saat_bitis: str = Form(""),
                    db: Session = Depends(get_db)):
    try:
        price = Decimal(meal_price)
        if not price.is_finite():
            raise InvalidOperation
    except InvalidOperation:
        return templates.TemplateResponse(
            request, "admin/settings.html",
            _settings_context(db, "Geçersiz fiyat"), status_code=200)
    # Saatler: boş alan = değiştirme (mevcut değer korunur). İki değer
    # de doğrulanmadan HİÇBİR ayar yazılmaz (kısmi yazma olmasın).
    bas = bit = None
    if saat_baslangic or saat_bitis:
        cur_bas, cur_bit = _current_hours(db)
        try:
            bas = (time.fromisoformat(saat_baslangic)
                   if saat_baslangic else cur_bas)
            bit = (time.fromisoformat(saat_bitis)
                   if saat_bitis else cur_bit)
            if bit <= bas:
                raise ValueError
        except ValueError:
            return templates.TemplateResponse(
                request, "admin/settings.html",
                _settings_context(db, "Geçersiz saat aralığı"),
                status_code=200)
    _set_setting(db, "meal_price", str(price))
    if bas is not None and bit is not None:
        _set_setting(db, "saat_baslangic", bas.strftime("%H:%M"))
        _set_setting(db, "saat_bitis", bit.strftime("%H:%M"))
    db.commit()
    resp = RedirectResponse("/admin/settings", status_code=303)
    set_flash(resp, "Ayarlar güncellendi")
    return resp
