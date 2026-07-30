# Saat Kısıtlaması Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Check-in yalnız servis saatlerinde (varsayılan 12:00–13:30, ayarlanabilir) kabul edilsin; kiosk kapalıyken bunu göstersin ve söylesin.

**Architecture:** settings tablosuna 2 anahtar; checkin'e saat kontrolü (mükerrerden önce); tts'e saat okunuşu; kiosk'a durum endpoint'i + bekleme metni; ayarlar formuna saat alanları.

**Tech Stack:** mevcut yığın; yeni bağımlılık yok.

## Global Constraints

- Aralık KAPSAYICI: tam başlangıç ve tam bitiş dakikası kabul
- Kontrol sırası: imza → süre → kullanıcı aktif → SAAT → mükerrer → bakiye
- Yeni durum adı `saat_disi`; mesaj "Yemekhane şu an kapalı"
- Settings anahtarları: `saat_baslangic`/`saat_bitis`, "HH:MM" string
- Kiosk id'leri ve mevcut JS akışı korunur; yalnız yönerge metni + anons eklenir
- Her task sonunda tam suite yeşil (şu an 70); commit İngilizce

---

### Task 1: get_service_hours + checkin saat kontrolü

**Files:**
- Modify: `app/services/checkin.py`
- Test: `app/tests/test_checkin.py`

**Interfaces:**
- Produces:
  - `get_service_hours(db) -> tuple[datetime.time, datetime.time]` — settings'ten `saat_baslangic`/`saat_bitis` okur; anahtar yoksa "12:00"/"13:30" yazar ve döner (get_meal_price kalıbı; iki anahtar tek commit)
  - `process_checkin`: aktif-kullanıcı kontrolünden SONRA, mükerrerden ÖNCE:
    ```python
    bas, bit = get_service_hours(db)
    simdi = datetime.now().time()
    if not (bas <= simdi <= bit):
        return _fail(db, raw_token, "saat_disi", user)
    ```
    `from datetime import datetime, time` import güncellemesi; MESSAGES'a `"saat_disi": "Yemekhane şu an kapalı"`
  - Saat parse yardımcı: `_parse_hhmm(s: str) -> time` (`time.fromisoformat` yeterli)

- [ ] **Step 1: Failing testler** (test_checkin.py'ye ekle)

```python
from datetime import time as dtime

class SabitDatetime:
    """checkin.datetime yerine monkeypatch edilir."""
    sabit = None
    @classmethod
    def now(cls):
        class N:
            @staticmethod
            def time():
                return SabitDatetime.sabit
        return N()

def _saat_sabitle(monkeypatch, hh, mm):
    SabitDatetime.sabit = dtime(hh, mm)
    monkeypatch.setattr("app.services.checkin.datetime", SabitDatetime)

def test_service_hours_defaults(db_session):
    from app.services.checkin import get_service_hours
    bas, bit = get_service_hours(db_session)
    assert bas == dtime(12, 0) and bit == dtime(13, 30)

def test_checkin_outside_hours_rejected(db_session, monkeypatch):
    u = make_user(db_session, sicil="7001")
    _saat_sabitle(monkeypatch, 15, 0)
    r = process_checkin(db_session, generate_token(u.id))
    assert r.status == "saat_disi"
    db_session.refresh(u)
    assert u.balance == Decimal("500.00")          # bakiye düşmedi
    assert db_session.query(MealEntry).count() == 0
    assert db_session.query(FailedAttempt).one().reason == "saat_disi"

def test_checkin_boundary_times_accepted(db_session, monkeypatch):
    u1 = make_user(db_session, sicil="7002")
    _saat_sabitle(monkeypatch, 12, 0)              # tam açılış
    assert process_checkin(db_session, generate_token(u1.id)).ok
    u2 = make_user(db_session, sicil="7003")
    _saat_sabitle(monkeypatch, 13, 30)             # tam kapanış
    assert process_checkin(db_session, generate_token(u2.id)).ok

def test_checkin_just_after_close_rejected(db_session, monkeypatch):
    u = make_user(db_session, sicil="7004")
    _saat_sabitle(monkeypatch, 13, 31)
    assert process_checkin(db_session, generate_token(u.id)).status == "saat_disi"
```

DİKKAT: mevcut checkin testleri saat kontrolüne takılmasın — dosyadaki
diğer testler `datetime.now()` gerçek saatiyle koşar; CI/lokal gündüz
her saatte çalışabilmeli. Çözüm: conftest'e AUTOUSE fixture ekle:

```python
@pytest.fixture(autouse=True)
def _servis_saati_serbest(request, monkeypatch):
    """Saat testleri dışında servis saatini tüm güne aç."""
    if "saat" in request.node.name or "hours" in request.node.name or "boundary" in request.node.name or "close" in request.node.name:
        yield; return
    from datetime import time as _t
    monkeypatch.setattr("app.services.checkin.get_service_hours",
                        lambda db: (_t(0, 0), _t(23, 59)))
    yield
```

(İsim filtresi yerine marker da kullanılabilir; basit tut.)

- [ ] **Step 2: FAIL doğrula** — 4 yeni test FAIL (saat_disi yok / get_service_hours yok)

- [ ] **Step 3: checkin.py implement** — Interfaces'teki gibi

- [ ] **Step 4: PASS + tam suite** → 74 passed

- [ ] **Step 5: Commit** — `feat: service-hours restriction on check-in`

---

### Task 2: Anons (saat okunuşu) + kiosk yanıtı/durum endpoint'i

**Files:**
- Modify: `app/tts.py`, `app/routers/kiosk_routes.py`
- Test: `app/tests/test_tts.py`, `app/tests/test_kiosk_routes.py`

**Interfaces:**
- Produces:
  - `tts.saat_okunusu(t: time) -> str` — "12:00"→"on iki", "13:30"→"on üç otuz", "09:15"→"dokuz on beş". Sayı okunuşu 0-59: birler ("", "bir".."dokuz"), onlar ("", "on", "yirmi", "otuz", "kırk", "elli"); saat 0→"sıfır", 23→"yirmi üç". Dakika 0 → yalnız saat okunur.
  - `tts.anons_metni(result, saatler: tuple[time, time] | None = None)` — `saat_disi` durumunda: `f"Yemekhane şu an kapalı. Servis saatleri {saat_okunusu(bas)}, {saat_okunusu(bit)} arasıdır."`; saatler None ise kısa form "Yemekhane şu an kapalı."
  - kiosk_routes `/api/checkin`: sonuç `saat_disi` ise `get_service_hours` çağırıp anons'u saatlerle üretir ve yanıta `"saatler": "12:00 - 13:30"` ekler (diğer durumlarda `"saatler": null`); saat stringi `f"{bas:%H:%M} - {bit:%H:%M}"`
  - Yeni `GET /api/kiosk-durum` (localhost_only): `{"acik": bool, "saatler": "12:00 - 13:30"}` — `get_service_hours` + `datetime.now().time()` karşılaştırması

- [ ] **Step 1: Failing testler**

test_tts.py:
```python
def test_saat_okunusu():
    from datetime import time as t
    from app.tts import saat_okunusu
    assert saat_okunusu(t(12, 0)) == "on iki"
    assert saat_okunusu(t(13, 30)) == "on üç otuz"
    assert saat_okunusu(t(9, 15)) == "dokuz on beş"
    assert saat_okunusu(t(0, 5)) == "sıfır beş"

def test_anons_saat_disi():
    from datetime import time as t
    r = R("saat_disi")
    assert anons_metni(r) == "Yemekhane şu an kapalı."
    assert anons_metni(r, saatler=(t(12, 0), t(13, 30))) == \
        "Yemekhane şu an kapalı. Servis saatleri on iki, on üç otuz arasıdır."
```

test_kiosk_routes.py:
```python
def test_checkin_outside_hours_response(client, seeded_db, monkeypatch):
    from datetime import time as t
    monkeypatch.setattr(
        "app.services.checkin.get_service_hours",
        lambda db: (t(0, 0), t(0, 1)))   # hep kapali
    from app.qr_token import generate_token
    r = client.post("/api/checkin", json={"token": generate_token(seeded_db)})
    body = r.json()
    assert body["status"] == "saat_disi"
    assert body["saatler"] == "00:00 - 00:01"
    assert "kapalı" in body["anons"]["text"]

def test_kiosk_durum_endpoint(client, seeded_db, monkeypatch):
    from datetime import time as t
    monkeypatch.setattr(
        "app.routers.kiosk_routes.get_service_hours",
        lambda db: (t(0, 0), t(23, 59)))
    r = client.get("/api/kiosk-durum")
    assert r.json()["acik"] is True

def test_kiosk_durum_remote_403(client_remote, seeded_db):
    assert client_remote.get("/api/kiosk-durum").status_code == 403
```

DİKKAT: Task 1'in autouse fixture'ı `get_service_hours`'u checkin
modülünde patch'liyor; `test_checkin_outside_hours_response` kendi
patch'ini fixture'dan SONRA uygular (monkeypatch sırası test gövdesi
kazanır) — isim filtresine "hours" geçtiği için fixture zaten atlar.

- [ ] **Step 2: FAIL doğrula**

- [ ] **Step 3: Implement** — Interfaces'teki gibi; kiosk_routes'ta import: `from app.services.checkin import get_service_hours, process_checkin` + `from datetime import datetime`

- [ ] **Step 4: PASS + tam suite** → 79 passed

- [ ] **Step 5: Commit** — `feat: closed-hours announcement and kiosk status endpoint`

---

### Task 3: Ayarlar formu + kiosk bekleme metni + dağıtım

**Files:**
- Modify: `app/routers/admin_routes.py`, `app/templates/admin/settings.html`, `app/templates/kiosk.html`
- Test: `app/tests/test_admin_routes.py`

**Interfaces:**
- Produces:
  - Ayarlar GET context'ine `saat_baslangic`, `saat_bitis` (get_service_hours'tan, `%H:%M` string)
  - Ayarlar POST: form alanları `meal_price`, `saat_baslangic`, `saat_bitis`; saatler `time.fromisoformat` ile parse; hata veya bitis<=baslangic → "Geçersiz saat aralığı" error render; başarıda iki Setting yazılır + flash "Ayarlar güncellendi" (PRG)
  - settings.html: "Yemekhane Saatleri" bölümü, iki `<input type="time" class="alan">`
  - kiosk.html: yönerge div'ine `id="yonerge"`; JS'e durum kontrolü:
    ```javascript
    async function durumKontrol() {
        try {
            const r = await fetch("/api/kiosk-durum");
            if (!r.ok) return;
            const d = await r.json();
            document.getElementById("yonerge").textContent =
                d.acik ? "QR kodunuzu okutun"
                       : "Yemekhane kapalı — Servis: " + d.saatler;
        } catch {}
    }
    durumKontrol();
    setInterval(durumKontrol, 60000);
    ```
  - showResult'ta saat_disi için ekstra iş yok (kırmızı zaten default; mesaj backend'den geliyor); yalnız `result-balance` alanına saatler yazılabilir: `d.saatler ? "Servis saatleri: " + d.saatler : (d.balance != null ? "Kalan: " + d.balance + " TL" : "")`

- [ ] **Step 1: Failing testler** (test_admin_routes.py)

```python
def test_settings_updates_service_hours(client, db_session):
    login_admin(client, db_session)
    r = client.post("/admin/settings",
                    data={"meal_price": "125.00",
                          "saat_baslangic": "11:30",
                          "saat_bitis": "14:00"},
                    follow_redirects=False)
    assert r.status_code == 303
    from app.models import Setting
    assert db_session.get(Setting, "saat_baslangic").value == "11:30"
    assert db_session.get(Setting, "saat_bitis").value == "14:00"

def test_settings_rejects_invalid_hours(client, db_session):
    login_admin(client, db_session)
    r = client.post("/admin/settings",
                    data={"meal_price": "125.00",
                          "saat_baslangic": "14:00",
                          "saat_bitis": "12:00"})
    assert "Geçersiz saat aralığı" in r.text
    from app.models import Setting
    assert db_session.get(Setting, "saat_baslangic") is None
```

DİKKAT: mevcut `test_update_meal_price` ve `test_settings_rejects_nan`
yalnız `meal_price` gönderiyor — form artık 3 alan istiyorsa kırılırlar.
Çözüm: saat alanlarına route'ta varsayılan ver (`saat_baslangic: str =
Form("12:00")` gibi DEĞİL — mevcut kayıtlı değeri koru: `Form("")` ve
boşsa dokunma). Boş gelen saat alanı = değiştirme.

- [ ] **Step 2: FAIL doğrula**

- [ ] **Step 3: Implement** — route + şablonlar

- [ ] **Step 4: PASS + tam suite** → 81 passed

- [ ] **Step 5: Commit + push** — `feat: configurable service hours in settings and kiosk idle text`

- [ ] **Step 6: RPi dağıtım (kontrolör)** — tar → compose up --build → health → kiosk restart → doğrulama: `curl /api/kiosk-durum` (saat aralığına göre acik true/false), ayarlar sayfasında saat alanları, kapalı saatteyse kiosk yönergesi "Yemekhane kapalı"
