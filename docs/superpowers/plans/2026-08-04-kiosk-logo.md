# Kiosk Logo ve Gorsel Tasarim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kiosk ekraninda yatay belediye logosu ve CSS tabanli modern arka plan kullanmak.

**Architecture:** Logo dosyasi Raspberry Pi uzerinde proje static klasorune kopyalanir. Kiosk sablonu yeni varligi kullanir; gradyan ve dekoratif desenler ek bagimlilik olmadan inline CSS ile uygulanir.

**Tech Stack:** Jinja2, CSS, Pytest.

## Global Constraints

- Kaynak logo Pi'de `~/Desktop/imagebelediye.png` olur.
- Harici ikon paketi veya ag bagimliligi eklenmez.
- Kiosk QR okuyucu, ses ve sonuc ekrani davranislari korunur.

---

### Task 1: Logo Varligi ve Kiosk Gorsel Duzeni

**Files:**
- Create: `app/static/imagebelediye.png` copied from `~/Desktop/imagebelediye.png` on the Pi.
- Modify: `app/templates/kiosk.html:13-47`
- Test: `app/tests/test_kiosk_routes.py`

**Interfaces:**
- Produces: kiosk markup referencing `/static/imagebelediye.png`.
- Produces: `.kiosk-logo`, `.kiosk-doku`, `.kiosk-icerik` visual classes.

- [ ] **Step 1: Write failing template test**

```python
def test_kiosk_uses_horizontal_municipality_logo(client, seeded_db):
    r = client.get("/kiosk")
    assert 'src="/static/imagebelediye.png"' in r.text
    assert 'class="kiosk-doku"' in r.text
```

- [ ] **Step 2: Verify red**

Run: `pytest app/tests/test_kiosk_routes.py::test_kiosk_uses_horizontal_municipality_logo -q`

Expected: FAIL because the existing template uses `/static/logo.jpg`.

- [ ] **Step 3: Copy the logo and update kiosk markup/CSS**

Run on Pi:

```bash
cp ~/Desktop/imagebelediye.png ~/yemekhane/app/static/imagebelediye.png
```

Replace the circular logo wrapper with a horizontal `kiosk-logo` wrapper. Add a `kiosk-doku` decorative element and layered green gradient. Use `object-fit: contain`, avoid a white circular background, and keep the current content IDs unchanged.

- [ ] **Step 4: Verify green**

Run: `pytest app/tests/test_kiosk_routes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit application source**

```bash
git add app/templates/kiosk.html app/tests/test_kiosk_routes.py
git commit -m "feat: refresh kiosk branding"
```

### Task 2: Full Verification

**Files:**
- Test: `app/tests/`

- [ ] **Step 1: Run full suite**

Run: `pytest app/tests -q`

Expected: PASS.

- [ ] **Step 2: Inspect whitespace and state**

Run: `git diff --check; git status --short`

Expected: no whitespace errors and no unintended files.
