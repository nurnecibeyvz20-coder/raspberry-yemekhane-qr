# UX Yeniden Tasarımı Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admin panelini SaaS seviyesine çıkarmak (sol menü, dashboard, modaller, sayfalama/sıralama, toast), personel sayfasına geçmiş eklemek, kiosk'u cilalamak.

**Architecture:** Mevcut FastAPI + Jinja2 + vanilla JS mimarisi korunur. Yeni modüller: `app/services/stats.py` (istatistik + sayfalama), `app/flash.py` (imzalı flash çerezi). Admin şablonları yeni `admin/_base.html` (sol menülü layout) üzerine kurulur. Backend form endpoint'leri DEĞİŞMEZ — modaller mevcut POST'lara gönderir.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Jinja2, saf CSS (Karatay token'ları), native `<dialog>`, inline SVG (Lucide).

## Global Constraints

- Ham hex YASAK (yalnız style.css `:root`); tüm renkler `var(--k-*)` token'larından
- Route haritası: `GET /admin` = dashboard; `GET /admin/personel` = liste (q, page, sort, dir paramları); `GET /admin/islemler` = işlem listesi (page, tur paramları); diğer admin POST/GET route'ları AYNEN korunur
- Sayfalama: 50 kayıt/sayfa; sıralama paramları `sort` ∈ (sicil_no, ad_soyad, balance), `dir` ∈ (asc, desc)
- Flash çerezi: ad `flash`, itsdangerous imzalı, max_age 60 sn; toast 4 sn görünür
- Kiosk: id'ler (`idle`, `result`, `connecting`, `scan-input`, `clock`, `result-*`) ve JS akışı (buffer, charFromCode, submitToken, showResult, 5 sn dönüş) DEĞİŞMEZ; yalnız CSS animasyonları eklenir
- Korunan test metinleri: "Bakiyeniz yetersiz", "QR kodunuzu okutun", "Bu sicil no zaten kayıtlı", "Hatalı sicil no veya şifre"
- Her task sonunda TAM suite yeşil: `python -m pytest app/tests -v`
- Commit mesajları İngilizce: `feat:`/`refactor:`/`test:` önekli
- Öğün göstergesi: `int(balance // meal_price)` — "≈ N öğün"

---

### Task 1: stats servisi + flash modülü (backend temelleri)

**Files:**
- Create: `app/services/stats.py`, `app/flash.py`
- Test: `app/tests/test_stats.py`, `app/tests/test_flash.py`

**Interfaces:**
- Consumes: modeller (`User`, `Transaction`, `MealEntry`, `FailedAttempt`), `app.config.settings.secret_key`
- Produces:
  - `stats.dashboard_stats(db) -> dict` — anahtarlar: `bugun_yiyen: int`, `aktif_personel: int`, `toplam_bakiye: Decimal`, `bugun_ciro: Decimal` (bugünkü type='yemek' işlemlerinin mutlak toplamı), `son_islemler: list[Transaction]` (10, user ilişkisiyle), `son_hatalar: list[FailedAttempt]` (5)
  - `stats.paginate(query, page: int, per_page: int = 50) -> Page` — `Page` dataclass: `items: list`, `total: int`, `page: int`, `pages: int` (ceil, min 1); page < 1 → 1'e sabitlenir, page > pages → pages'e sabitlenir
  - `flash.set_flash(response, mesaj: str, tur: str = "basari") -> None` — imzalı `flash` çerezi (itsdangerous TimestampSigner, salt="flash", değer `tur|mesaj`)
  - `flash.get_flash(request) -> dict | None` — `{"mesaj": str, "tur": str}` döner ve None (bozuk/60sn+ eski imzada None); çerez okunduktan sonra template response tarafında silinir (get_flash saf okuyucudur, silme route'ta yapılır — aşağıdaki kullanım kalıbına bak)

Kullanım kalıbı (Task 3'te uygulanacak): GET route'ları `flash_data = get_flash(request)` alır, context'e koyar ve `response.delete_cookie("flash")` çağırır.

- [ ] **Step 1: Failing testleri yaz**

`app/tests/test_stats.py`:
```python
from datetime import date
from decimal import Decimal
from app.auth import hash_password
from app.models import User, Transaction, MealEntry, FailedAttempt
from app.services.stats import dashboard_stats, paginate

def make_user(db, sicil, balance="0.00", active=True):
    u = User(sicil_no=sicil, ad_soyad=f"Kisi {sicil}", role="personel",
             password_hash=hash_password("x"),
             balance=Decimal(balance), is_active=active)
    db.add(u); db.commit()
    return u

def test_dashboard_stats_counts(db_session):
    u1 = make_user(db_session, "s1", "300.00")
    u2 = make_user(db_session, "s2", "200.00")
    make_user(db_session, "s3", "999.00", active=False)  # pasif: toplama girmez
    db_session.add(MealEntry(user_id=u1.id, entry_date=date.today()))
    db_session.add(Transaction(user_id=u1.id, type="yemek",
                               amount=Decimal("-125.00"),
                               balance_after=Decimal("175.00")))
    db_session.add(Transaction(user_id=u2.id, type="yukleme",
                               amount=Decimal("200.00"),
                               balance_after=Decimal("200.00")))
    db_session.add(FailedAttempt(raw_qr="x", reason="gecersiz"))
    db_session.commit()
    s = dashboard_stats(db_session)
    assert s["bugun_yiyen"] == 1
    assert s["aktif_personel"] == 2
    assert s["toplam_bakiye"] == Decimal("500.00")
    assert s["bugun_ciro"] == Decimal("125.00")
    assert len(s["son_islemler"]) == 2
    assert len(s["son_hatalar"]) == 1

def test_paginate_basic(db_session):
    for i in range(120):
        make_user(db_session, f"p{i:03d}")
    q = db_session.query(User).order_by(User.sicil_no)
    p1 = paginate(q, page=1, per_page=50)
    assert p1.total == 120 and p1.pages == 3 and len(p1.items) == 50
    p3 = paginate(q, page=3, per_page=50)
    assert len(p3.items) == 20

def test_paginate_clamps_out_of_range(db_session):
    make_user(db_session, "tek")
    q = db_session.query(User)
    assert paginate(q, page=0).page == 1
    assert paginate(q, page=99).page == 1  # tek sayfa var

def test_paginate_empty(db_session):
    p = paginate(db_session.query(User), page=1)
    assert p.total == 0 and p.pages == 1 and p.items == []
```

`app/tests/test_flash.py`:
```python
from app.flash import set_flash, get_flash
from fastapi import Response, Request

def make_request_with_cookie(value):
    scope = {"type": "http", "headers": [
        (b"cookie", f"flash={value}".encode())]}
    return Request(scope)

def test_flash_roundtrip():
    resp = Response()
    set_flash(resp, "Kayıt eklendi", "basari")
    cookie = resp.headers["set-cookie"]
    value = cookie.split("flash=")[1].split(";")[0]
    req = make_request_with_cookie(value)
    f = get_flash(req)
    assert f == {"mesaj": "Kayıt eklendi", "tur": "basari"}

def test_flash_tampered_returns_none():
    req = make_request_with_cookie("sahte-deger")
    assert get_flash(req) is None

def test_flash_missing_returns_none():
    req = Request({"type": "http", "headers": []})
    assert get_flash(req) is None
```

- [ ] **Step 2: FAIL doğrula**

Run: `python -m pytest app/tests/test_stats.py app/tests/test_flash.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: `app/services/stats.py` yaz**

```python
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import User, Transaction, MealEntry, FailedAttempt

@dataclass
class Page:
    items: list
    total: int
    page: int
    pages: int

def paginate(query, page: int, per_page: int = 50) -> Page:
    total = query.count()
    pages = max(1, math.ceil(total / per_page))
    page = max(1, min(page, pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return Page(items=items, total=total, page=page, pages=pages)

def dashboard_stats(db: Session) -> dict:
    today = date.today()
    bugun_yiyen = (db.query(func.count(MealEntry.id))
                     .filter(MealEntry.entry_date == today).scalar()) or 0
    aktif_personel = (db.query(func.count(User.id))
                        .filter(User.is_active.is_(True)).scalar()) or 0
    toplam_bakiye = (db.query(func.coalesce(func.sum(User.balance), 0))
                       .filter(User.is_active.is_(True)).scalar())
    bugun_ciro = (db.query(func.coalesce(func.sum(Transaction.amount), 0))
                    .filter(Transaction.type == "yemek",
                            func.date(Transaction.created_at) == today)
                    .scalar())
    son_islemler = (db.query(Transaction)
                      .order_by(Transaction.created_at.desc(),
                                Transaction.id.desc())
                      .limit(10).all())
    son_hatalar = (db.query(FailedAttempt)
                     .order_by(FailedAttempt.created_at.desc(),
                               FailedAttempt.id.desc())
                     .limit(5).all())
    return {
        "bugun_yiyen": int(bugun_yiyen),
        "aktif_personel": int(aktif_personel),
        "toplam_bakiye": Decimal(toplam_bakiye),
        "bugun_ciro": abs(Decimal(bugun_ciro)),
        "son_islemler": son_islemler,
        "son_hatalar": son_hatalar,
    }
```

- [ ] **Step 4: `app/flash.py` yaz**

```python
from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from app.config import settings

_signer = TimestampSigner(settings.secret_key, salt="flash")

def set_flash(response: Response, mesaj: str, tur: str = "basari") -> None:
    value = _signer.sign(f"{tur}|{mesaj}".encode()).decode()
    response.set_cookie("flash", value, max_age=60, httponly=True,
                        samesite="lax")

def get_flash(request: Request) -> dict | None:
    raw = request.cookies.get("flash")
    if not raw:
        return None
    try:
        data = _signer.unsign(raw, max_age=60).decode()
    except (BadSignature, SignatureExpired):
        return None
    tur, _, mesaj = data.partition("|")
    return {"mesaj": mesaj, "tur": tur}
```

- [ ] **Step 5: PASS doğrula + tam suite**

Run: `python -m pytest app/tests/test_stats.py app/tests/test_flash.py -v` → 7 PASS
Run: `python -m pytest app/tests -v` → 49 passed (42 + 7)

- [ ] **Step 6: Commit**

```bash
git add app/services/stats.py app/flash.py app/tests/test_stats.py app/tests/test_flash.py
git commit -m "feat: dashboard stats, pagination and signed flash helpers"
```

---

### Task 2: Admin route yeniden düzeni — dashboard, personel listesi, işlemler

**Files:**
- Modify: `app/routers/admin_routes.py`
- Test: `app/tests/test_admin_routes.py` (route güncellemeleri + yeni testler)

**Interfaces:**
- Consumes: `dashboard_stats`, `paginate` (Task 1); mevcut route gövdeleri
- Produces (şablon adları Task 3-4'te oluşturulacak; bu task'te route'lar yeni şablon adlarını referans alır — Task 3-4 gelene kadar şablonlar eski içerikle yeni ada kopyalanır, aşağıda Step 3'te):
  - `GET /admin` → `admin/dashboard.html` render eder; context: `stats` (dashboard_stats çıktısı), `flash` (get_flash), `aktif_sayfa="genel"`
  - `GET /admin/personel` → `admin/list.html`; query params `q: str = ""`, `page: int = 1`, `sort: str = "ad_soyad"`, `dir: str = "asc"`; geçersiz sort/dir sessizce varsayılana döner; context: `page_obj` (Page), `q`, `sort`, `dir`, `flash`, `aktif_sayfa="personel"`
  - `GET /admin/islemler` → `admin/islemler.html`; params `page: int = 1`, `tur: str = ""` (boş=tümü, değilse type filtresi); context: `page_obj`, `tur`, `aktif_sayfa="islemler"`
  - Mevcut POST route'ları redirect hedefleri güncellenir: create_user → `/admin/personel`; load_balance/edit/password/toggle-active detaydan çağrılırsa `/admin/users/{id}`'ye, listeden çağrılırsa `/admin/personel`'e döner — ayrım için formlarda opsiyonel `next: str = Form("")` alanı; `next` "personel" ise `/admin/personel`e redirect
  - Başarılı POST'larda `set_flash(response, mesaj)` çağrılır; mesajlar: "Personel eklendi", "{ad} bilgileri güncellendi", "Şifre sıfırlandı", "{ad} pasife alındı"/"{ad} aktifleştirildi", "{ad} kişisine {tutar} TL yüklendi" (negatifte "{ad} bakiyesi {tutar} TL düzeltildi"), "Yemek ücreti güncellendi"
  - RedirectResponse'a çerez: `resp = RedirectResponse(...); set_flash(resp, ...); return resp`

- [ ] **Step 1: Test güncellemelerini + yenilerini yaz**

`test_admin_routes.py` değişiklikleri:
```python
# GÜNCELLE: eski /admin listesi artık /admin/personel
def test_search_users(client, db_session):
    login_admin(client, db_session)
    db_session.add(User(sicil_no="4001", ad_soyad="Mehmet Öz",
                        role="personel", password_hash="x"))
    db_session.commit()
    r = client.get("/admin/personel?q=Mehmet")
    assert "Mehmet Öz" in r.text

# GÜNCELLE: create_user redirect hedefi
def test_create_user(client, db_session):
    login_admin(client, db_session)
    r = client.post("/admin/users/new",
                    data={"sicil_no": "3001", "ad_soyad": "Yeni Kişi",
                          "password": "sifre123", "role": "personel"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/admin/personel"
    u = db_session.query(User).filter_by(sicil_no="3001").one()
    assert u.ad_soyad == "Yeni Kişi"

# YENİ testler:
def test_dashboard_renders_stats(client, db_session):
    login_admin(client, db_session)
    r = client.get("/admin")
    assert r.status_code == 200
    assert "Bugün Yiyen" in r.text

def test_personel_pagination(client, db_session):
    login_admin(client, db_session)
    for i in range(60):
        db_session.add(User(sicil_no=f"pg{i:03d}", ad_soyad=f"Kisi {i:03d}",
                            role="personel", password_hash="x"))
    db_session.commit()
    r1 = client.get("/admin/personel?page=1")
    r2 = client.get("/admin/personel?page=2")
    assert "Kisi 000" in r1.text and "Kisi 000" not in r2.text

def test_personel_sort_by_balance(client, db_session):
    login_admin(client, db_session)
    db_session.add(User(sicil_no="z1", ad_soyad="Zengin", role="personel",
                        password_hash="x", balance=Decimal("900.00")))
    db_session.add(User(sicil_no="f1", ad_soyad="Fakir", role="personel",
                        password_hash="x", balance=Decimal("10.00")))
    db_session.commit()
    r = client.get("/admin/personel?sort=balance&dir=desc")
    assert r.text.index("Zengin") < r.text.index("Fakir")

def test_islemler_page_filters_by_type(client, db_session):
    admin = login_admin(client, db_session)
    u = User(sicil_no="i1", ad_soyad="Islemci", role="personel",
             password_hash="x")
    db_session.add(u); db_session.commit()
    db_session.add(Transaction(user_id=u.id, type="yukleme",
                               amount=Decimal("100.00"),
                               balance_after=Decimal("100.00"),
                               created_by=admin.id))
    db_session.add(Transaction(user_id=u.id, type="yemek",
                               amount=Decimal("-125.00"),
                               balance_after=Decimal("-25.00")))
    db_session.commit()
    r = client.get("/admin/islemler?tur=yukleme")
    assert "yukleme" in r.text.lower() or "Yükleme" in r.text
    assert "-125" not in r.text

def test_load_balance_sets_flash_cookie(client, db_session):
    login_admin(client, db_session)
    u = User(sicil_no="f2", ad_soyad="Flaslı", role="personel",
             password_hash="x")
    db_session.add(u); db_session.commit()
    r = client.post(f"/admin/users/{u.id}/load-balance",
                    data={"amount": "250.00"}, follow_redirects=False)
    assert r.status_code == 303
    assert "flash=" in r.headers.get("set-cookie", "")
```

Mevcut diğer testlerde `/admin` liste beklentisi varsa `/admin/personel`e güncelle (test_admin_requires_admin_role `/admin`'de kalır — dashboard da korumalı).

- [ ] **Step 2: FAIL doğrula**

Run: `python -m pytest app/tests/test_admin_routes.py -v`
Expected: yeni/güncellenen testler FAIL (404 veya redirect hedefi)

- [ ] **Step 3: Route'ları yeniden düzenle**

`admin_routes.py`'de:
- `user_list` → `personel_list`, path `/admin/personel`; paginate + sıralama:
```python
SORT_COLS = {"sicil_no": User.sicil_no, "ad_soyad": User.ad_soyad,
             "balance": User.balance}

@router.get("/admin/personel", response_class=HTMLResponse)
def personel_list(request: Request, q: str = "", page: int = 1,
                  sort: str = "ad_soyad", dir: str = "asc",
                  db: Session = Depends(get_db)):
    col = SORT_COLS.get(sort, User.ad_soyad)
    if sort not in SORT_COLS: sort = "ad_soyad"
    if dir not in ("asc", "desc"): dir = "asc"
    query = db.query(User)
    if q:
        query = query.filter(or_(User.sicil_no.ilike(f"%{q}%"),
                                 User.ad_soyad.ilike(f"%{q}%")))
    query = query.order_by(col.desc() if dir == "desc" else col.asc())
    page_obj = paginate(query, page)
    flash_data = get_flash(request)
    resp = templates.TemplateResponse(
        request, "admin/list.html",
        {"page_obj": page_obj, "q": q, "sort": sort, "dir": dir,
         "flash": flash_data, "aktif_sayfa": "personel"})
    if flash_data: resp.delete_cookie("flash")
    return resp
```
- Yeni `GET /admin` dashboard route'u (`dashboard_stats` + `meal_price` context); yeni `GET /admin/islemler` (Transaction join User, tur filtresi, paginate, `aktif_sayfa="islemler"`).
- POST'lara `next: str = Form("")` + `set_flash`; redirect mantığı Interfaces'teki gibi.
- Settings POST'u da PRG'ye çevrilir: başarıda `RedirectResponse("/admin/settings", 303)` + flash "Yemek ücreti güncellendi" (test `test_update_meal_price` davranışı korunur — Setting değeri hala yazılır).
- GEÇİCİ ŞABLONLAR (Task 3-4 gelene kadar suite yeşil kalsın): `admin/dashboard.html` ve `admin/islemler.html` minimal oluştur — base.html'i extend eden, `{{ stats.bugun_yiyen }}` / işlem döngüsü içeren, "Bugün Yiyen" metni geçen iskeletler. `admin/list.html`'i `page_obj.items` üzerinden döngüye güncelle (eski `users` değişkeni kalkar).

- [ ] **Step 4: PASS + tam suite**

Run: `python -m pytest app/tests -v`
Expected: tümü PASS (49 + yeni 6 ≈ 55; güncellenenler dahil)

- [ ] **Step 5: Commit**

```bash
git add app/routers/admin_routes.py app/templates/admin/ app/tests/test_admin_routes.py
git commit -m "feat: dashboard, paginated staff list, transactions page, flash"
```

---

### Task 3: Admin layout (sol menü) + dashboard + işlemler şablonları + ikonlar + toast

**Files:**
- Create: `app/templates/admin/_base.html`, `app/templates/_icons.html`
- Modify: `app/templates/admin/dashboard.html`, `admin/islemler.html`, `admin/settings.html`; `app/static/style.css` (yeni bileşenler)
- Delete: `app/templates/admin/_nav.html` (yerini _base alır)
- Test: mevcut suite (görsel task)

**Interfaces:**
- Consumes: Task 2 context'leri (`stats`, `page_obj`, `flash`, `aktif_sayfa`)
- Produces:
  - `admin/_base.html`: base.html'i extend eder; yapı: `.admin-yerlesim` (CSS grid: 232px sol menü + içerik), `.yan-menu` (logo, 4 nav maddesi ikonlu — Genel Bakış `/admin`, Personel `/admin/personel`, İşlemler `/admin/islemler`, Ayarlar `/admin/settings`; `aktif_sayfa` ile `.aktif` class), `.ust-serit` (`{% block baslik %}` + çıkış POST formu), `{% block govde %}`, toast bloğu (flash varsa `.toast .toast-{{ flash.tur }}` render + 4 sn sonra kaybolan 10 satır JS)
  - `_icons.html`: `{% macro ikon(ad, boyut=20) %}` — inline SVG'ler: `genel` (layout-dashboard), `personel` (users), `islemler` (wallet), `ayarlar` (settings), `ara` (search), `arti` (plus), `duzenle` (pencil), `anahtar` (key-round), `guc` (power), `cikis` (log-out), `onay` (check), `uyari` (alert-triangle), `para` (banknote) — Lucide 24x24 viewBox, `stroke="currentColor" fill="none" stroke-width="2"`
  - style.css yeni class'ları: `.admin-yerlesim`, `.yan-menu` (+`.yan-menu a`, `.aktif`), `.ust-serit`, `.stat-kartlar` (grid 4 kolon, darda 2), `.stat-kart` (büyük sayı + etiket + ikon), `.toast` (+`.toast-basari`, `.toast-hata`; sağ üst sabit, giriş animasyonu), `.sayfalama`, `.panel-cift` (2 kolonlu panel grid'i)
  - Tüm admin sayfaları artık `admin/_base.html`'i extend eder (bu task'te dashboard/islemler/settings; Task 4'te list/form/detail)

- [ ] **Step 1: `_icons.html` yaz** — 13 Lucide ikonu macro içinde `{% if ad == "genel" %}...{% endif %}` zinciriyle; her SVG Lucide sitesindeki resmi path'lerle (boyut parametresi width/height'a bağlanır)

- [ ] **Step 2: style.css'e yeni bileşenleri ekle** — Interfaces'teki class listesi; toast animasyonu:
```css
.toast { position: fixed; top: var(--k-a2); right: var(--k-a2);
  z-index: 100; padding: var(--k-a2) var(--k-a3);
  border-radius: var(--k-radius-sm); box-shadow: var(--k-golge-buyuk);
  color: var(--k-beyaz); animation: toast-gir .25s ease-out;
  display: flex; align-items: center; gap: var(--k-a1); }
.toast-basari { background: var(--k-basari); }
.toast-hata { background: var(--k-hata); }
@keyframes toast-gir { from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: none; } }
```
`.stat-kart` sayısı 28px kalın `--k-birincil`; `.yan-menu` `--k-birincil` zemin, linkler `--k-beyaz` %80 opak, `.aktif` tam opak + `--k-birincil-koyu` zemin.

- [ ] **Step 3: `admin/_base.html` yaz** — Interfaces'teki yapı; toast JS:
```html
{% if flash %}
<div class="toast toast-{{ flash.tur }}" id="toast">
  {{ ikon('onay' if flash.tur == 'basari' else 'uyari') }} {{ flash.mesaj }}
</div>
<script>setTimeout(() => document.getElementById("toast")?.remove(), 4000);</script>
{% endif %}
```
`{% from "_icons.html" import ikon %}` en üstte.

- [ ] **Step 4: dashboard.html'i gerçek tasarıma getir** — `.stat-kartlar`da 4 `.stat-kart` (ikonlu; "Bugün Yiyen" metni korunur); `.panel-cift`te "Son İşlemler" tablosu (kişi adı `t.user.ad_soyad` — Transaction'a `user` relationship yoksa route'ta join'li sorgudan gelen çiftler kullanılır; Task 2'deki sorgu yapısına uy) ve "Son Başarısız Okutmalar" (saat, sebep etiketi `.rozet`).

- [ ] **Step 5: islemler.html + settings.html'i _base'e geçir** — islemler: tür filtresi (3 link: Tümü/Yükleme/Yemek/Düzeltme `?tur=`), tablo (tarih, kişi, tür `.rozet`, tutar `.tutar-arti/eksi`, sonrası bakiye), `.sayfalama`. settings: mevcut form `_base` içinde `.kart`ta; `saved` yerine artık flash toast kullanılır.

- [ ] **Step 6: `_nav.html`'i sil** — kullanan kalmadıysa (`grep -r "_nav" app/templates`) sil; Task 4'e kadar list/form/detail hâlâ kullanıyorsa silme, Task 4'te sil.

- [ ] **Step 7: Tam suite + hex denetimi**

Run: `python -m pytest app/tests -v` → tümü PASS
Run: `Select-String -Path app\templates\admin\*.html,app\templates\_icons.html -Pattern "#[0-9a-fA-F]{3,6}\b"` → boş

- [ ] **Step 8: Commit**

```bash
git add app/templates/ app/static/style.css
git commit -m "feat: admin sidebar layout, dashboard UI, icons and toasts"
```

---

### Task 4: Personel listesi UI — tablo, modaller, sayfalama/sıralama

**Files:**
- Modify: `app/templates/admin/list.html`, `admin/detail.html`; `app/templates/admin/form.html` silinir (modal'a taşınır); `app/static/style.css` (.modal)
- Test: mevcut suite

**Interfaces:**
- Consumes: Task 2 context (`page_obj`, `q`, `sort`, `dir`), Task 3 `_base`/ikonlar/toast, mevcut POST endpoint'leri
- Produces:
  - list.html: arama satırı (`.alan` + debounce JS 400ms: `input` event → `clearTimeout/setTimeout(form.submit, 400)`) + "Yeni Personel" `.btn` (modal açar); sıralanabilir başlıklar (link `?q={{q}}&sort=sicil_no&dir={{ 'desc' if sort=='sicil_no' and dir=='asc' else 'asc' }}` kalıbı + yön oku ▲▼); satırlar: sicil, ad (detaya link), bakiye `.sag`, durum rozeti, işlem ikonları (para/duzenle/anahtar/guc); alt `.sayfalama` ("{{ page_obj.total }} personel", ◀ sayfa linkleri ▶ — q/sort/dir korunarak)
  - Modaller (list.html sonunda 3 `<dialog class="modal">`): yeni-personel (sicil/ad/şifre/rol formu → POST /admin/users/new + `next=personel` hidden), bakiye-yükle (başlıkta ad + mevcut bakiye JS ile doldurulur; tutar alanı + 4 hızlı buton `+125/+250/+500/+625` (JS: tutar alanına yazar); form action JS ile `/admin/users/{id}/load-balance`a set edilir + `next=personel`), şifre-sıfırla (yeni şifre alanı; action JS ile set). Pasife alma modal değil `confirm()` ile: küçük inline form + `onsubmit="return confirm('...')"` + `next=personel`
  - Modal JS (~30 satır, list.html içinde): `data-modal-ac="id"` butonları dialog.showModal(); `data-doldur-*` özellikleriyle satırdan ad/bakiye/action aktarımı; ESC/kapat butonu dialog.close()
  - `.modal` CSS: `dialog::backdrop` karartma, `.modal` kart görünümü (radius, gölge, 400px)
  - detail.html: `_base`'e geçirilir (topbar/nav'sız eski hali yerine `aktif_sayfa="personel"`); işlevler aynı kalır (formlar `next`siz → detaya döner)
  - form.html silinir; `GET /admin/users/new` route'u da silinir (modal varken gereksiz) — testlerden `new_user_page` GET testi varsa kaldırılır; POST testi kalır

- [ ] **Step 1: Route/test temizliği** — `GET /admin/users/new` route'unu ve varsa GET testini kaldır; POST akışı aynen. IntegrityError durumunda form.html yok artık: hata flash'la listeye döner — `set_flash(resp, "Bu sicil no zaten kayıtlı", "hata")` + redirect `/admin/personel`; `test_create_user_duplicate` güncellenir (303 + flash çerezi + kayıt yok assert'i; "Bu sicil no zaten kayıtlı" metni artık toast'ta — takip redirect'iyle sayfada görünür: `follow_redirects=True` ile `r.text`te aranır)

- [ ] **Step 2: FAIL doğrula** — güncellenen duplicate testi FAIL

- [ ] **Step 3: list.html'i yeniden yaz** — Interfaces'teki tüm parçalar; sıralama linki kalıbı her üç kolon için tekrarlanır

- [ ] **Step 4: detail.html'i _base'e geçir** — mevcut kart/tablolar `{% block govde %}` içine; formlar aynen

- [ ] **Step 5: Modal CSS + JS** — style.css'e `.modal`, `dialog::backdrop`; list.html'e modal JS

- [ ] **Step 6: form.html + eski route'u sil; tam suite**

Run: `python -m pytest app/tests -v` → tümü PASS

- [ ] **Step 7: Commit**

```bash
git add -A app/templates/admin/ app/static/style.css app/routers/admin_routes.py app/tests/
git commit -m "feat: staff table with sorting, pagination and modal workflows"
```

---

### Task 5: Personel geçmişi + öğün göstergesi

**Files:**
- Modify: `app/routers/qr_routes.py` (GET /qr context), `app/templates/qr.html`
- Test: `app/tests/test_qr_routes.py`

**Interfaces:**
- Consumes: mevcut `/qr` route + şablon, `get_meal_price`
- Produces: `GET /qr` context'ine ek: `gecmis` (kullanıcının son 20 Transaction'ı, created_at desc), `ogun_sayisi` (`int(user.balance // price)`); qr.html'e Geçmişim bölümü + öğün rozeti

- [ ] **Step 1: Failing test**

```python
def test_qr_page_shows_history_and_meals(client, seeded_db, db_session):
    from decimal import Decimal
    from app.models import Transaction
    db_session.add(Transaction(user_id=seeded_db, type="yukleme",
                               amount=Decimal("500.00"),
                               balance_after=Decimal("500.00")))
    db_session.commit()
    login(client)
    r = client.get("/qr")
    assert "Geçmişim" in r.text
    assert "+500.00" in r.text
    assert "4 öğün" in r.text   # 500 // 125
```

- [ ] **Step 2: FAIL doğrula** — "Geçmişim" yok

- [ ] **Step 3: Route + şablon**

Route: `gecmis = db.query(Transaction).filter_by(user_id=user.id).order_by(Transaction.created_at.desc(), Transaction.id.desc()).limit(20).all()`; `ogun_sayisi = int(user.balance // price)`. Şablon: bakiye altına `<span class="rozet">≈ {{ ogun_sayisi }} öğün</span>`; kart altına yeni `.kart`: başlık "Geçmişim", `.tablo` (tarih `%d.%m %H:%M`, tür rozeti, tutar `.tutar-arti/eksi` `{{ "+" if t.amount > 0 }}{{ t.amount }}`, sonrası bakiye `.soluk`); boşsa "Henüz işlem yok" `.soluk`.

- [ ] **Step 4: PASS + tam suite** → tümü PASS

- [ ] **Step 5: Commit**

```bash
git add app/routers/qr_routes.py app/templates/qr.html app/tests/test_qr_routes.py
git commit -m "feat: staff transaction history and meal count badge"
```

---

### Task 6: Kiosk cilası (yalnız CSS) + dağıtım

**Files:**
- Modify: `app/templates/kiosk.html` (yalnız `<style>` bloğu + ekran class'larına animasyon; JS DEĞİŞMEZ)
- Test: mevcut suite + RPi görsel doğrulama

**Interfaces:**
- Consumes: mevcut kiosk yapısı
- Produces: animasyonlar — spec değerleri: 250ms fade, ikon pop, 4sn logo nefes, 5sn geri sayım şeridi

- [ ] **Step 1: `<style>` bloğuna animasyonları ekle**

```css
.screen { transition: opacity .25s ease; opacity: 0; pointer-events: none; }
.screen.active { opacity: 1; pointer-events: auto; }
/* display:none yerine opacity geçişi: display flex kalır, görünmez ekranlar tıklanamaz */
.screen { display: flex; }
#result.active #result-icon { animation: ikon-pop .35s ease-out; }
@keyframes ikon-pop { from { transform: scale(.4); opacity: 0; }
  60% { transform: scale(1.15); } to { transform: scale(1); opacity: 1; } }
#idle .logo-yuvarlak { animation: nefes 4s ease-in-out infinite; }
@keyframes nefes { 0%, 100% { transform: scale(1); }
  50% { transform: scale(1.04); } }
#result.active::after { content: ""; position: absolute; bottom: 0; left: 0;
  height: 4px; background: var(--k-beyaz); opacity: .8;
  animation: sayac 5s linear forwards; }
@keyframes sayac { from { width: 0; } to { width: 100%; } }
```

DİKKAT: `.screen { display: none }` kaldırılıp opacity'ye geçildiği için ekranların üst üste binme sırası önemli — `#idle { z-index: 1 }`, `#result, #connecting { z-index: 2 }` ekle. JS'teki `classList.add/remove("active")` mantığı aynen çalışır.

- [ ] **Step 2: Tam suite** → tümü PASS (kiosk testleri HTML durum koduna bakar, etkilenmez)

- [ ] **Step 3: Commit + push**

```bash
git add app/templates/kiosk.html
git commit -m "refactor: kiosk transition polish with CSS animations"
git push origin main
```

- [ ] **Step 4: RPi'ye dağıt (kontrolör oturumunda)**

Tar arşivi → SFTP → `tar xzf ... app` → `docker compose up --build -d` → `/health` + `/admin` (redirect login) + `/kiosk` 200 doğrulaması → Chromium kiosk yeniden başlat → kullanıcı gözle doğrular: dashboard istatistikleri, modal akışı, toast, kiosk animasyonları.

## Plan Notları

- Task 2 route değişikliği en riskli adım: mevcut testlerin hangilerinin `/admin` listesine bağlı olduğunu implementer önce grep'le bulmalı (`Select-String -Path app\tests\test_admin_routes.py -Pattern "/admin"`).
- Dashboard "Son İşlemler"de kişi adı gerekir; `Transaction` modelinde `user` relationship YOK. Task 2'de dashboard route'u join'li sorgu KULLANMAZ — `stats.dashboard_stats` Transaction listesi döner; şablonda ad göstermek için Task 3'te dashboard route'una küçük ek yapılabilir (id→ad sözlüğü: tek sorgu `db.query(User.id, User.ad_soyad).filter(User.id.in_(ids))`). Bu ek Task 3 Step 4'ün parçasıdır.
- Modaller JS gerektirir ama form POST'ları standart kalır — JS kapalıysa bile dialog açılamasa da detay sayfasındaki formlar çalışmaya devam eder (kademeli bozulma).
