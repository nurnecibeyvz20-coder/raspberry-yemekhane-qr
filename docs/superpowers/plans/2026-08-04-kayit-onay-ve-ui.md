# Kayit, Onay ve Arayuz Gelistirmeleri Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Personel kayit/onay ve kalici QR guvenligini eklerken odeme, gecmis ve genel arayuz deneyimini modernlestirmek.

**Architecture:** `User` tablosu kayit durumunu ve kalici QR sirrini saklar; mevcut `is_active` hesabin sonradan pasife alinmasini temsil etmeye devam eder. Routerlar HTTP/form akisini yonetir, yeni QR servisi QR kimligi uretme ve dogrulama kurallarini merkezilestirir. Jinja sablonlari ve ortak CSS/vanilla JavaScript arayuz davranislarini saglar.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Jinja2, vanilla JavaScript, CSS, Pytest.

## Global Constraints

- Mevcut roller, bakiye, kiosk, odeme ve sifre sifirlama davranislari korunacak.
- `registration_status` degerleri yalnizca `pending`, `approved`, `rejected` olacak.
- Kalici QR kimligi tahmin edilemez, benzersiz ve veritabaninda saklanir.
- Demo kodu sadece demo SMS/e-posta saglayicisinda input varsayilan degeri olur.
- Kart sahibi, SKT ve CVV sadece tarayici onizlemesinde kullanilir; sunucuya gonderilmez veya saklanmaz.
- Pasif ya da onaysiz kullanici yeni bakiye, odeme veya check-in islemi olusturamaz.
- Tum yeni davranislar test-first uygulanir ve tum `app/tests` paketi calisir.

---

## File Structure

- Modify: `app/models.py` - Kullanici kayit durumu ve QR sirri alanlari.
- Create: `app/migrations/versions/0003_kayit_onay_qr.py` - Uretim veritabani migrationi.
- Create: `app/services/user_qr.py` - QR sirri uretme ve onaylanmis kullanici uygunluk kurallari.
- Modify: `app/auth.py` - Oturumda kayit onayi denetimi.
- Modify: `app/qr_token.py`, `app/routers/kiosk_routes.py` - Kalici QR sirri ile token uretme/dogrulama.
- Modify: `app/routers/auth_routes.py` - Kayit endpointleri, onaysiz giris mesaji, basari flashlari.
- Create: `app/templates/register.html` - Personel basvuru formu.
- Modify: `app/templates/login.html`, `app/static/style.css` - Modern login/kayit ve ortak gorsel stiller.
- Modify: `app/routers/admin_routes.py`, `app/templates/admin/dashboard.html`, `app/templates/admin/list.html`, `app/templates/admin/detail.html` - Bekleyen kullanicilar, onay/red/QR yenileme ve pasif hesap kontrolleri.
- Modify: `app/services/payment_flow.py`, `app/services/checkin.py`, `app/routers/payment_routes.py` - Onay/pasif hesap islem korumalari.
- Modify: `app/templates/app/odeme_tutar.html`, `app/templates/app/odeme_pos.html` - Hazir tutar ve canli kart arayuzu.
- Modify: `app/routers/qr_routes.py`, `app/templates/app/gecmis.html`, `app/templates/app/profil.html` - Aylik yemek takvimi, kalici QR profil gorunumu ve gizli soru placeholderi.
- Modify: `app/templates/app/unuttum_kod.html` - Demo kod input varsayilan degeri.
- Modify: `app/tests/test_auth.py`, `app/tests/test_admin_routes.py`, `app/tests/test_qr_routes.py`, `app/tests/test_kiosk_routes.py`, `app/tests/test_payment.py`, `app/tests/test_pwa.py`, `app/tests/test_reset_flow.py` - Yeni davranislarin regresyon testleri.

### Task 1: Kayit Durumu ve Kalici QR Veri Katmani

**Files:**
- Modify: `app/models.py:8-23`
- Create: `app/migrations/versions/0003_kayit_onay_qr.py`
- Create: `app/services/user_qr.py`
- Test: `app/tests/test_models.py`
- Test: `app/tests/test_user_qr.py`

**Interfaces:**
- Produces: `User.registration_status: str`, `User.qr_secret: str | None`.
- Produces: `approve_user(user: User) -> None`, `regenerate_qr_secret(user: User) -> str`, `is_approved(user: User) -> bool` from `app.services.user_qr`.

- [ ] **Step 1: Write failing model and QR service tests**

```python
from app.models import User
from app.services.user_qr import approve_user, regenerate_qr_secret

def test_new_user_is_pending_without_qr(db_session):
    user = User(sicil_no="9002", ad_soyad="Basvuru", role="personel",
                password_hash="x")
    db_session.add(user); db_session.commit()
    assert user.registration_status == "pending"
    assert user.qr_secret is None

def test_approve_user_generates_unique_qr_secret(db_session):
    user = User(sicil_no="9003", ad_soyad="Onay", role="personel",
                password_hash="x")
    approve_user(user)
    first = user.qr_secret
    assert user.registration_status == "approved"
    assert user.is_active is True
    assert first and len(first) >= 32
    assert regenerate_qr_secret(user) != first
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_models.py app/tests/test_user_qr.py -q`

Expected: FAIL because `registration_status`, `qr_secret`, and `app.services.user_qr` do not exist.

- [ ] **Step 3: Add columns, migration, and minimal QR service**

```python
# app/models.py
registration_status: Mapped[str] = mapped_column(
    String(10), default="pending", server_default="pending")
qr_secret: Mapped[str | None] = mapped_column(String(64), unique=True,
                                               nullable=True)

# app/services/user_qr.py
import secrets
from app.models import User

def is_approved(user: User) -> bool:
    return user.registration_status == "approved" and user.is_active

def regenerate_qr_secret(user: User) -> str:
    user.qr_secret = secrets.token_urlsafe(32)
    return user.qr_secret

def approve_user(user: User) -> None:
    user.registration_status = "approved"
    user.is_active = True
    regenerate_qr_secret(user)
```

Migration must add nullable columns, update existing rows to `approved`, then make `registration_status` non-null with server default `approved` only for upgrade compatibility; application-created users explicitly use `pending`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest app/tests/test_models.py app/tests/test_user_qr.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/services/user_qr.py app/migrations/versions/0003_kayit_onay_qr.py app/tests/test_models.py app/tests/test_user_qr.py
git commit -m "feat: add registration status and QR secret"
```

### Task 2: Registration, Approval, Rejection, and Session Gates

**Files:**
- Modify: `app/auth.py:61-79`
- Modify: `app/routers/auth_routes.py:56-100`
- Modify: `app/routers/admin_routes.py:45-78,186-196`
- Create: `app/templates/register.html`
- Modify: `app/templates/login.html`
- Modify: `app/templates/admin/dashboard.html`
- Test: `app/tests/test_auth.py`
- Test: `app/tests/test_admin_routes.py`

**Interfaces:**
- Consumes: `approve_user(user: User) -> None` from Task 1.
- Produces: `GET/POST /kayit`, `POST /admin/users/{user_id}/approve`, `POST /admin/users/{user_id}/reject`.
- Produces: `current_user()` rejects users whose `registration_status != "approved"`.

- [ ] **Step 1: Write failing registration and approval flow tests**

```python
def test_registration_creates_pending_user(client, admin_db):
    r = client.post("/kayit", data={"sicil_no": "8010", "ad_soyad": "Yeni",
                                     "password": "guvenli123"},
                    follow_redirects=False)
    assert r.status_code == 303
    user = admin_db.query(User).filter_by(sicil_no="8010").one()
    assert user.registration_status == "pending"
    assert user.is_active is False

def test_pending_user_cannot_login_until_approved(client, admin_db):
    user = User(sicil_no="8011", ad_soyad="Bekleyen", role="personel",
                password_hash=hash_password("guvenli123"), is_active=False,
                registration_status="pending")
    admin_db.add(user); admin_db.commit()
    r = client.post("/login", data={"sicil_no": "8011", "password": "guvenli123"})
    assert "onay bekliyor" in r.text.lower()

def test_admin_approval_enables_login_and_assigns_qr(client, admin_db):
    admin = login_admin(client, admin_db)
    user = User(sicil_no="8012", ad_soyad="Onay", role="personel",
                password_hash=hash_password("guvenli123"), is_active=False,
                registration_status="pending")
    admin_db.add(user); admin_db.commit()
    r = client.post(f"/admin/users/{user.id}/approve", follow_redirects=False)
    assert r.status_code == 303
    admin_db.refresh(user)
    assert user.registration_status == "approved" and user.qr_secret

def test_admin_rejection_keeps_record_and_blocks_login(client, admin_db):
    login_admin(client, admin_db)
    user = User(sicil_no="8013", ad_soyad="Red", role="personel",
                password_hash=hash_password("guvenli123"), is_active=False,
                registration_status="pending")
    admin_db.add(user); admin_db.commit()
    client.post(f"/admin/users/{user.id}/reject")
    admin_db.refresh(user)
    assert user.registration_status == "rejected"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_auth.py app/tests/test_admin_routes.py -q`

Expected: FAIL because registration and approval/rejection routes do not exist.

- [ ] **Step 3: Implement registration and admin review routes**

```python
@router.post("/kayit")
def register(sicil_no: str = Form(...), ad_soyad: str = Form(...),
             password: str = Form(...), db: Session = Depends(get_db)):
    if len(password) < 8:
        return templates.TemplateResponse(request, "register.html",
            {"error": "Şifre en az 8 karakter olmalı"})
    user = User(sicil_no=sicil_no.strip(), ad_soyad=ad_soyad.strip(),
                role="personel", password_hash=hash_password(password),
                is_active=False, registration_status="pending")
    db.add(user); db.commit()
    response = RedirectResponse("/login", status_code=303)
    set_flash(response, "Başvurunuz alındı, yönetici onayı bekleniyor")
    return response

@router.post("/admin/users/{user_id}/approve")
def approve_pending_user(user_id: int, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    if user.registration_status != "pending":
        raise HTTPException(400, "Bu başvuru onay beklemiyor")
    approve_user(user); db.commit()
    response = RedirectResponse("/admin", status_code=303)
    set_flash(response, f"{user.ad_soyad} onaylandı")
    return response
```

Dashboard context includes `pending_users = db.query(User).filter_by(registration_status="pending").all()`. Login returns specific friendly messages for `pending` and `rejected`; inactive approved accounts retain the generic inactive-account message. `current_user` requires approved status.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest app/tests/test_auth.py app/tests/test_admin_routes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/auth.py app/routers/auth_routes.py app/routers/admin_routes.py app/templates/register.html app/templates/login.html app/templates/admin/dashboard.html app/tests/test_auth.py app/tests/test_admin_routes.py
git commit -m "feat: add staff registration approval flow"
```

### Task 3: QR Token Migration and Passive Account Guardrails

**Files:**
- Modify: `app/qr_token.py`
- Modify: `app/routers/qr_routes.py:109-119`
- Modify: `app/routers/kiosk_routes.py`
- Modify: `app/services/checkin.py`
- Modify: `app/services/payment_flow.py`
- Modify: `app/routers/admin_routes.py:198-224`
- Modify: `app/templates/admin/detail.html`
- Modify: `app/templates/app/profil.html`
- Test: `app/tests/test_qr_token.py`
- Test: `app/tests/test_kiosk_routes.py`
- Test: `app/tests/test_payment.py`
- Test: `app/tests/test_admin_routes.py`

**Interfaces:**
- Consumes: `is_approved(user: User) -> bool`, `regenerate_qr_secret(user: User) -> str` from Task 1.
- Produces: `POST /admin/users/{user_id}/regenerate-qr`.
- Produces: QR issue/verify functions bind tokens to `User.qr_secret`.
- Produces: profile context key `qr_secret` for an approved user; the profile template renders its QR image using the existing client-side QR renderer and never renders a QR value for pending/rejected users.

- [ ] **Step 1: Write failing QR rotation and inactive-account tests**

```python
def test_rotated_qr_invalidates_old_token(client, seeded_db):
    login_admin(client, admin_db)
    user = admin_db.get(User, seeded_db)
    user.registration_status = "approved"; approve_user(user); admin_db.commit()
    old = generate_token(user.id)
    client.post(f"/admin/users/{user.id}/regenerate-qr")
    r = client.post("/api/checkin", json={"token": old})
    assert r.json()["status"] == "gecersiz"

def test_passive_user_cannot_receive_balance(client, admin_db):
    login_admin(client, admin_db)
    user = User(sicil_no="8020", ad_soyad="Pasif", role="personel",
                password_hash="x", is_active=False, registration_status="approved")
    admin_db.add(user); admin_db.commit()
    r = client.post(f"/admin/users/{user.id}/load-balance", data={"amount": "100"})
    assert "pasif" in r.text.lower()
    assert admin_db.query(Transaction).filter_by(user_id=user.id).count() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_qr_token.py app/tests/test_kiosk_routes.py app/tests/test_payment.py app/tests/test_admin_routes.py -q`

Expected: FAIL because QR tokens do not bind to `qr_secret`, rotation endpoint is absent, and passive mutations are allowed.

- [ ] **Step 3: Bind tokens to permanent QR secret and reject inactive mutations**

```python
def regenerate_user_qr(user_id: int, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    if not is_approved(user):
        raise HTTPException(400, "Onaylanmamış kullanıcı için QR üretilemez")
    regenerate_qr_secret(user); db.commit()

def load_balance(user_id: int, amount: str = Form(...), next: str = Form(""),
                 admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    if not is_approved(user):
        resp = _detail_or_list_redirect(user_id, next)
        set_flash(resp, "Pasif veya onaysız kullanıcıya bakiye yüklenemez", "hata")
        return resp
```

Update `generate_token` to include `user.qr_secret`; update verification to retrieve the user and compare the signed QR secret before check-in. `payment_flow.baslat`, payment completion, check-in service, profile update, and admin edit endpoints must reject `not is_approved(user)` before mutating state.

Add an approved-user-only profile QR card that renders the current QR token with the project's existing `qrcode.min.js`; the token remains signed and short-lived while `qr_secret` is the server-stored permanent QR identity used to invalidate prior QR images after regeneration.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest app/tests/test_qr_token.py app/tests/test_kiosk_routes.py app/tests/test_payment.py app/tests/test_admin_routes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/qr_token.py app/routers/qr_routes.py app/routers/kiosk_routes.py app/services/checkin.py app/services/payment_flow.py app/routers/admin_routes.py app/templates/admin/detail.html app/templates/app/profil.html app/tests/test_qr_token.py app/tests/test_kiosk_routes.py app/tests/test_payment.py app/tests/test_admin_routes.py
git commit -m "feat: secure approved user QR access"
```

### Task 4: Modern Authentication Screens and Password Feedback

**Files:**
- Modify: `app/templates/login.html`
- Modify: `app/templates/register.html`
- Modify: `app/static/style.css`
- Modify: `app/routers/auth_routes.py:109-132`
- Modify: `app/routers/qr_routes.py:127-151`
- Test: `app/tests/test_auth.py`

**Interfaces:**
- Produces: login/register visual classes `.auth-sahne`, `.auth-kart`, `.auth-aksiyonlar`.
- Produces: flash message exactly `Şifreniz başarıyla değiştirildi.` after standard or forced password changes.

- [ ] **Step 1: Write failing user-visible feedback tests**

```python
def test_change_password_shows_success_message(client, seeded_db):
    login(client)
    r = client.post("/change-password", data={"old_password": "dogru123",
                                                "new_password": "yeni12345"},
                    follow_redirects=True)
    assert "Şifreniz başarıyla değiştirildi." in r.text

def test_login_page_links_to_registration_and_recovery(client):
    r = client.get("/login")
    assert 'href="/kayit"' in r.text
    assert 'href="/sifremi-unuttum"' in r.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_auth.py -q`

Expected: FAIL because password changes do not set the required flash message.

- [ ] **Step 3: Add flash feedback and modern responsive auth CSS**

```python
user.password_hash = hash_password(new_password)
user.session_version += 1
db.commit()
response = RedirectResponse("/qr", status_code=303)
set_flash(response, "Şifreniz başarıyla değiştirildi.")
return response
```

Use a gradient auth page, elevated card, accessible visible focus states, responsive spacing, and subtle entrance animation. Preserve labels, form actions, errors, and CSRF-free existing form conventions.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest app/tests/test_auth.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/templates/login.html app/templates/register.html app/static/style.css app/routers/auth_routes.py app/routers/qr_routes.py app/tests/test_auth.py
git commit -m "feat: modernize authentication screens"
```

### Task 5: Payment Amount Selection and Live Card Preview

**Files:**
- Modify: `app/routers/payment_routes.py:16`
- Modify: `app/templates/app/odeme_tutar.html`
- Modify: `app/templates/app/odeme_pos.html`
- Modify: `app/static/style.css`
- Test: `app/tests/test_payment.py`

**Interfaces:**
- Produces: quick amount buttons with `data-tutar="100|250|500|1000"`.
- Produces: browser-only IDs `card-number-preview`, `card-name-preview`, `card-expiry-preview`, `card-brand-preview`, and `payment-card`.

- [ ] **Step 1: Write failing markup behavior tests**

```python
def test_quick_amount_buttons_fill_payment_input(client, seeded_db):
    login(client)
    r = client.get("/yukle")
    assert 'data-tutar="100"' in r.text
    assert 'data-tutar="1000"' in r.text
    assert 'id="tutar"' in r.text

def test_pos_page_has_live_card_preview_without_cvv_submission(client, seeded_db):
    login(client)
    r = client.post("/yukle", data={"tutar": "100"}, follow_redirects=False)
    payment_url = r.headers["location"]
    r = client.get(payment_url)
    assert 'id="payment-card"' in r.text
    assert 'name="cvv"' not in r.text
    assert 'id="card-brand-preview"' in r.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_payment.py -q`

Expected: FAIL because 100 TL is absent and POS has no card preview.

- [ ] **Step 3: Implement amount buttons and card-only UI fields**

```javascript
document.querySelectorAll("[data-tutar]").forEach((button) => {
  button.addEventListener("click", () => {
    document.getElementById("tutar").value = button.dataset.tutar;
  });
});

cvv.addEventListener("focus", () => card.classList.add("arka-yuz"));
cvv.addEventListener("input", () => {
  if (cvv.value.length >= 3) card.classList.remove("arka-yuz");
});
```

Use inputs without `name` for name/SKT/CVV. Keep `kart_no` as the only payment-card form field submitted. CSS implements `.payment-card` transform with a visible front/back face and Visa/MasterCard text mark based on the normalized first digit.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest app/tests/test_payment.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/payment_routes.py app/templates/app/odeme_tutar.html app/templates/app/odeme_pos.html app/static/style.css app/tests/test_payment.py
git commit -m "feat: add live payment card preview"
```

### Task 6: Monthly Meal Calendar and Recovery Code UI

**Files:**
- Modify: `app/routers/qr_routes.py:42-67`
- Modify: `app/templates/app/gecmis.html`
- Modify: `app/templates/app/profil.html`
- Modify: `app/templates/app/unuttum_kod.html`
- Modify: `app/routers/auth_routes.py:203-233`
- Modify: `app/static/style.css`
- Test: `app/tests/test_pwa.py`
- Test: `app/tests/test_reset_flow.py`

**Interfaces:**
- Produces: `GET /gecmis?year=2026&month=7` context keys `calendar_days`, `previous_month_url`, `next_month_url`, `month_label`.
- Produces: demo-only `demo_kod` passed to verification template and used as input `value`.

- [ ] **Step 1: Write failing calendar and demo-code tests**

```python
def test_history_shows_selected_month_calendar(client, seeded_db):
    login(client)
    r = client.get("/gecmis?year=2026&month=7")
    assert "Temmuz 2026" in r.text
    assert 'class="meal-day alindi"' in r.text
    assert 'class="meal-day alinmadi"' in r.text

def test_demo_code_is_default_value_in_verification_input(client, flow_db):
    _kullanici(flow_db, telefon="05321234512")
    client.post("/sifremi-unuttum", data={"sicil_no": "7001"})
    r = client.post("/sifremi-unuttum/yontem", data={"kanal": "sms"})
    code = flow_db.query(ResetCode).one().demo_gosterim
    assert f'value="{code}"' in r.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_pwa.py app/tests/test_reset_flow.py -q`

Expected: FAIL because the history page has no calendar and the code input has no default value.

- [ ] **Step 3: Implement calendar data and demo-only default code**

```python
import calendar

_, day_count = calendar.monthrange(year, month)
meal_dates = {entry.entry_date.day for entry in db.query(MealEntry).filter(
    MealEntry.user_id == user.id,
    MealEntry.entry_date >= date(year, month, 1),
    MealEntry.entry_date <= date(year, month, day_count),
)}
calendar_days = [
    {"day": day, "status": "alindi" if day in meal_dates else
     "alinmadi" if date(year, month, day) <= date.today() else "gelecek"}
    for day in range(1, day_count + 1)
]
```

The template includes an accessible legend and monthly previous/next links. Add `placeholder="Gizli sorunuzu yazınız"` to the profile question input. Template input adds `value="{{ demo_kod or '' }}"`; route only supplies `demo_kod` for the selected demo provider.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest app/tests/test_pwa.py app/tests/test_reset_flow.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/qr_routes.py app/templates/app/gecmis.html app/templates/app/profil.html app/templates/app/unuttum_kod.html app/routers/auth_routes.py app/static/style.css app/tests/test_pwa.py app/tests/test_reset_flow.py
git commit -m "feat: add meal calendar and demo code default"
```

### Task 7: Full Regression Verification

**Files:**
- Modify: files only if verification exposes an issue in the preceding tasks.
- Test: `app/tests/`

**Interfaces:**
- Consumes: all routes, services, migrations, and templates from Tasks 1-6.
- Produces: verified integrated feature set.

- [ ] **Step 1: Run the complete test suite**

Run: `pytest app/tests -q`

Expected: PASS with no failures.

- [ ] **Step 2: Inspect migration chain and whitespace**

Run: `alembic -c app/alembic.ini history`

Expected: revisions `0001`, `0002`, `0003` form a single linear chain.

Run: `git diff --check`

Expected: no output and exit code 0.

- [ ] **Step 3: Review final state**

Run: `git status --short`

Expected: no unintended modified or untracked files.
