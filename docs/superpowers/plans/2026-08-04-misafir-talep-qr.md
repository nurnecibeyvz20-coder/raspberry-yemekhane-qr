# Misafir Talep ve QR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Personelin onaylı misafir talebi oluşturmasını ve onaylanan misafirin kullanım hakkıyla sınırlı QR ile kiosktan giriş yapmasını sağlamak.

**Architecture:** Misafir başvurusu, durum ve kullanım hakkı `GuestRequest` içinde; denetim olayları `GuestRequestEvent` içinde saklanır. Misafir QR tokenları normal personel QR tokenlarından ayrı imza tuzuyla üretilir. Personel/admin routerları talep yaşam döngüsünü, kiosk servisi ise atomik QR kullanımını yönetir.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Jinja2, itsdangerous, Pytest.

## Global Constraints

- Durumlar yalnızca `pending`, `approved`, `rejected`, `exhausted`, `expired` olur.
- Talep sahibi, kendi talebini görür; yalnızca admin onay/red/düzenleme yapar.
- QR sadece ziyaret tarihinde, tanımlı saat aralığında ve kalan hak varken geçerlidir.
- Misafir QR kullanımı personel bakiyesi veya `MealEntry` kaydı oluşturmaz.
- Her yaşam döngüsü işlemi denetim kaydı oluşturur.

---

### Task 1: Misafir Veri Modeli ve Migration

**Files:**
- Modify: `app/models.py`
- Create: `app/migrations/versions/0004_misafir_talepleri.py`
- Test: `app/tests/test_models.py`

**Interfaces:**
- Produces: `GuestRequest` and `GuestRequestEvent` SQLAlchemy models.

- [ ] **Step 1: Write failing model tests**

```python
def test_guest_request_defaults(db_session):
    request = GuestRequest(owner_id=1, ad="Misafir", soyad="Kişi",
                           ziyaret_tarihi=date.today(), yemek_adedi=2,
                           baslangic_saati=time(12), bitis_saati=time(13, 30))
    db_session.add(request); db_session.commit()
    assert request.durum == "pending"
    assert request.kalan_hak == 0
    assert request.qr_secret is None
```

- [ ] **Step 2: Verify red**

Run: `pytest app/tests/test_models.py -q`

Expected: FAIL because guest models do not exist.

- [ ] **Step 3: Add models and migration**

`GuestRequest` fields: owner foreign key, guest identity/contact fields, reason,
date, integer meal count/remaining count, times, status, optional QR secret,
optional rejection reason, timestamps. `GuestRequestEvent` has request foreign
key, event type, actor user foreign key nullable for kiosk, description, and
timestamp. Migration creates both tables with relevant indexes.

- [ ] **Step 4: Verify green**

Run: `pytest app/tests/test_models.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/migrations/versions/0004_misafir_talepleri.py app/tests/test_models.py
git commit -m "feat: add guest request models"
```

### Task 2: Guest Service and QR Token Rules

**Files:**
- Create: `app/services/guest_requests.py`
- Create: `app/guest_qr_token.py`
- Test: `app/tests/test_guest_requests.py`

**Interfaces:**
- Produces: `create_request`, `approve_request`, `reject_request`, `use_guest_qr`.
- Produces: `generate_guest_token(request_id, secret)` and `verify_guest_token(token)`.

- [ ] **Step 1: Write failing service tests**

```python
def test_approved_guest_qr_consumes_each_meal_right(db_session):
    request = make_guest_request(db_session, yemek_adedi=2)
    approve_request(db_session, request, admin_id=1)
    token = generate_guest_token(request.id, request.qr_secret)
    assert use_guest_qr(db_session, token).ok
    assert use_guest_qr(db_session, token).ok
    assert use_guest_qr(db_session, token).status == "misafir_hakki_bitti"
```

- [ ] **Step 2: Verify red**

Run: `pytest app/tests/test_guest_requests.py -q`

Expected: FAIL because service and token module do not exist.

- [ ] **Step 3: Implement service**

Use `secrets.token_urlsafe(32)` for the QR secret. `approve_request` sets
status, remaining count and QR secret. `use_guest_qr` validates date, time,
status and remaining count before decrementing; it records an event and sets
`exhausted` at zero. Expired requests become `expired` on validation.

- [ ] **Step 4: Verify green**

Run: `pytest app/tests/test_guest_requests.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/guest_requests.py app/guest_qr_token.py app/tests/test_guest_requests.py
git commit -m "feat: add guest request QR service"
```

### Task 3: Personel Talep ve QR Görüntüleme

**Files:**
- Create: `app/routers/guest_routes.py`
- Create: `app/templates/app/misafir.html`
- Create: `app/templates/app/misafir_detay.html`
- Modify: `app/main.py`
- Modify: `app/templates/app/_shell.html`
- Test: `app/tests/test_guest_routes.py`

**Interfaces:**
- Produces: `GET/POST /misafir`, `GET /misafir/{id}`.

- [ ] **Step 1: Write failing route tests**

```python
def test_personnel_creates_pending_guest_request(client, seeded_db):
    login(client)
    r = client.post("/misafir", data={"ad": "Ayşe", "soyad": "Yılmaz",
        "telefon": "05551234567", "ziyaret_nedeni": "Ziyaret",
        "ziyaret_tarihi": str(date.today()), "yemek_adedi": "1"},
        follow_redirects=False)
    assert r.status_code == 303
    assert guest_request.durum == "pending"
```

- [ ] **Step 2: Verify red**

Run: `pytest app/tests/test_guest_routes.py -q`

Expected: FAIL because routes do not exist.

- [ ] **Step 3: Implement routes and templates**

Use current service hours as default times. Validate required identity/reason,
positive meal count, and today/future date. The detail page displays QR only
when approved and includes remaining rights and validity window.

- [ ] **Step 4: Verify green**

Run: `pytest app/tests/test_guest_routes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/guest_routes.py app/templates/app/misafir.html app/templates/app/misafir_detay.html app/main.py app/templates/app/_shell.html app/tests/test_guest_routes.py
git commit -m "feat: add personnel guest requests"
```

### Task 4: Admin Guest Review and Kiosk Integration

**Files:**
- Modify: `app/routers/admin_routes.py`
- Modify: `app/templates/admin/dashboard.html`
- Create: `app/templates/admin/misafir_detay.html`
- Modify: `app/routers/kiosk_routes.py`
- Modify: `app/services/checkin.py`
- Test: `app/tests/test_admin_routes.py`
- Test: `app/tests/test_kiosk_routes.py`

**Interfaces:**
- Produces: `GET/POST /admin/guests/{id}`, approval and rejection actions.
- Produces: kiosk response statuses for valid and invalid guest QR use.

- [ ] **Step 1: Write failing admin/kiosk tests**

```python
def test_admin_approves_guest_request(client, admin_db):
    login_admin(client, admin_db)
    request = make_pending_guest_request(admin_db)
    client.post(f"/admin/guests/{request.id}/approve")
    admin_db.refresh(request)
    assert request.durum == "approved" and request.qr_secret
```

- [ ] **Step 2: Verify red**

Run: `pytest app/tests/test_admin_routes.py app/tests/test_kiosk_routes.py -q`

Expected: FAIL because admin guest routes and kiosk handling do not exist.

- [ ] **Step 3: Implement admin and kiosk paths**

Dashboard gets a pending guest table. Admin edit validates times before save.
Kiosk first attempts normal personnel QR, then guest QR; response includes guest
name and remaining rights without touching personnel transaction tables.

- [ ] **Step 4: Verify green**

Run: `pytest app/tests/test_admin_routes.py app/tests/test_kiosk_routes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/admin_routes.py app/templates/admin/dashboard.html app/templates/admin/misafir_detay.html app/routers/kiosk_routes.py app/services/checkin.py app/tests/test_admin_routes.py app/tests/test_kiosk_routes.py
git commit -m "feat: approve guest QR requests"
```

### Task 5: Complete Verification

- [ ] **Step 1: Run migrations and tests**

Run: `alembic -c app/alembic.ini history`

Expected: `0004` follows `0003`.

Run: `pytest app/tests -q`

Expected: PASS.

- [ ] **Step 2: Inspect final state**

Run: `git diff --check; git status --short`

Expected: no whitespace errors or unintended files.
