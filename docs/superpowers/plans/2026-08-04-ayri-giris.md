# Ayrı Personel ve Yönetici Girişi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Personel ve yönetici girişlerini ayırmak, yönetici hesaplarını personel listesinden kaldırmak.

**Architecture:** Mevcut oturum çerezi ve rol kontrolü korunur. Personel ve yönetici girişleri aynı doğrulama mantığını rol filtresiyle kullanır; yönetici listesi sorgulardan filtrelenir.

**Tech Stack:** FastAPI, SQLAlchemy, Jinja2, Pytest.

## Global Constraints

- Personel giriş rotası `/login`, yönetici giriş rotası `/admin/login` olur.
- Yanlış roldeki giriş genel hata mesajı döner.
- `/admin/personel` yalnızca `role="personel"` satırlarını gösterir.

---

### Task 1: Rol Bazlı Giriş Rotaları

**Files:**
- Modify: `app/routers/auth_routes.py:57-141`
- Modify: `app/templates/login.html`
- Create: `app/templates/admin/login.html`
- Test: `app/tests/test_auth.py`

**Interfaces:**
- Produces: `GET/POST /admin/login`.
- Produces: `/login` only accepts personnel and redirects to `/qr`.

- [ ] **Step 1: Write failing tests**

```python
def test_admin_login_rejects_personnel(client, seeded_db):
    r = client.post("/admin/login", data={"sicil_no": "1001", "password": "dogru123"})
    assert "Hatalı sicil no veya şifre" in r.text

def test_personnel_login_rejects_admin(client, admin_db):
    login_admin(client, admin_db)
    client.post("/logout")
    r = client.post("/login", data={"sicil_no": "9001", "password": "admin123"})
    assert "Hatalı sicil no veya şifre" in r.text
```

- [ ] **Step 2: Verify red**

Run: `pytest app/tests/test_auth.py -q`

Expected: FAIL because admin credentials are accepted by `/login` and `/admin/login` is absent.

- [ ] **Step 3: Implement minimal role filtering**

```python
def _login(..., expected_role: str, template: str, target: str):
    user = db.execute(select(User).where(User.sicil_no == sicil_no,
                                         User.role == expected_role)).scalar_one_or_none()
    # Retain existing password, active, and registration-status checks.
```

Make `/login` call the helper with `personel`, `login.html`, `/qr`; make `/admin/login` use `admin`, `admin/login.html`, `/admin`. Add cross-links between templates.

- [ ] **Step 4: Verify green**

Run: `pytest app/tests/test_auth.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/auth_routes.py app/templates/login.html app/templates/admin/login.html app/tests/test_auth.py
git commit -m "feat: separate admin and personnel login"
```

### Task 2: Personnel-Only Admin Listing

**Files:**
- Modify: `app/routers/admin_routes.py:64-82`
- Test: `app/tests/test_admin_routes.py`

**Interfaces:**
- Produces: `personel_list()` query filters `User.role == "personel"` before search, sorting, and pagination.

- [ ] **Step 1: Write failing test**

```python
def test_personnel_list_hides_admin_accounts(client, admin_db):
    login_admin(client, admin_db)
    admin_db.add(User(sicil_no="3009", ad_soyad="Personel", role="personel", password_hash="x"))
    admin_db.commit()
    r = client.get("/admin/personel")
    assert "Personel" in r.text
    assert "Admin" not in r.text
```

- [ ] **Step 2: Verify red**

Run: `pytest app/tests/test_admin_routes.py::test_personnel_list_hides_admin_accounts -q`

Expected: FAIL because the list includes all roles.

- [ ] **Step 3: Apply query filter**

```python
query = db.query(User).filter(User.role == "personel")
```

Keep all existing search and sort clauses attached to `query`.

- [ ] **Step 4: Verify green**

Run: `pytest app/tests/test_admin_routes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/admin_routes.py app/tests/test_admin_routes.py
git commit -m "fix: hide admins from personnel list"
```

### Task 3: Full Verification

**Files:**
- Test: `app/tests/`

- [ ] **Step 1: Run full suite**

Run: `pytest app/tests -q`

Expected: PASS.

- [ ] **Step 2: Check worktree**

Run: `git diff --check; git status --short`

Expected: no whitespace errors and no unintended changes.
