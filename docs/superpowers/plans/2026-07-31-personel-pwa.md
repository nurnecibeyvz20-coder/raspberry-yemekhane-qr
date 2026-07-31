# Personel PWA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Personel telefonuna kurulan PWA: giriş, şifremi unuttum (SMS/mail/gizli soru — demo sağlayıcılar), zorunlu şifre değişimi, QR, geçmiş, demo sanal POS ile bakiye yükleme, oturum güvenliği.

**Architecture:** Mevcut FastAPI monolith genişler. Yeni: providers (Protocol + Demo), services (reset, payment_flow), payment_routes, PWA app-shell şablonları, migration 0002. Oturum çerezi `user_id:session_version` çiftine geçer.

**Tech Stack:** Mevcut yığın + hashlib/secrets (kod üretimi). Yeni pip bağımlılığı YOK.

## Global Constraints

- Reset kodu: 6 hane, 10 dk geçerli, tek kullanımlık, DB'de yalnız hash (demo gösterimi ayrı `demo_gosterim` alanı); 5 yanlış → kod iptal; sicil başına saatte 3 talep
- Ödeme: min 50, max 5000 TL; test kartı 4242 ile başlar → başarılı, 4000 ile başlar → red; idempotent doğrulama; başarılı ödeme TEK atomik commit (payment+transaction+balance)
- Oturum çerezi değeri `f"{user_id}:{session_version}"` imzalı; sürüm uyuşmazlığı → login'e; personel 30 gün (2592000), admin 12 saat (43200)
- `must_change_password=True` kullanıcı yalnız şifre değiştirme sayfasına ve logout'a erişebilir
- Sicil var/yok sızdırılmaz: şifremi unuttum'da bilinmeyen sicil de "yöntem yok" ekranı gösterir
- Gizli cevap normalize: `casefold()` sonrası Türkçe İ/ı düzeltmesi, strip
- Türkçe UI, Karatay token'ları, ham hex yasak, dokunma hedefleri min 44px
- Her task sonunda tam suite yeşil (şu an 81); commit İngilizce
- Mevcut kiosk/check-in/admin akışları BOZULMAZ

---

### Task 1: Migration 0002 + model güncellemeleri

**Files:**
- Modify: `app/models.py`
- Create: `app/migrations/versions/0002_pwa_alanlari.py`
- Test: `app/tests/test_models.py`

**Interfaces:**
- Produces:
  - `User` ek kolonlar: `telefon: str|None (String(20))`, `eposta: str|None (String(120))`, `gizli_soru: str|None (String(200))`, `gizli_cevap_hash: str|None (String(200))`, `must_change_password: bool default False`, `session_version: int default 0`
  - `ResetCode(id, user_id FK, kanal String(10), kod_hash String(200), demo_gosterim String(6) NULL, expires_at DateTime, used Boolean default False, created_at)`
  - `Payment(id, user_id FK, tutar Numeric(10,2), durum String(12), saglayici String(20), saglayici_ref String(100), transaction_id FK NULL, created_at, updated_at DateTime onupdate)`
  - Migration 0001'in üstüne 0002: yeni kolonlar (server_default'larla: false/0) + 2 tablo; downgrade tersini yapar

- [ ] **Step 1: Failing testler** (test_models.py'ye)

```python
def test_user_pwa_defaults(db_session):
    u = User(sicil_no="m1", ad_soyad="M", role="personel", password_hash="x")
    db_session.add(u); db_session.commit()
    assert u.must_change_password is False
    assert u.session_version == 0
    assert u.telefon is None and u.gizli_soru is None

def test_reset_code_and_payment_models(db_session):
    from datetime import datetime, timedelta
    from app.models import ResetCode, Payment
    u = User(sicil_no="m2", ad_soyad="N", role="personel", password_hash="x")
    db_session.add(u); db_session.commit()
    rc = ResetCode(user_id=u.id, kanal="sms", kod_hash="h",
                   expires_at=datetime.now() + timedelta(minutes=10))
    p = Payment(user_id=u.id, tutar=Decimal("250.00"),
                durum="baslatildi", saglayici="demo", saglayici_ref="ref1")
    db_session.add_all([rc, p]); db_session.commit()
    assert rc.used is False and rc.demo_gosterim is None
    assert p.transaction_id is None
```

- [ ] **Step 2: FAIL doğrula** → import hataları
- [ ] **Step 3: models.py + migration yaz** — migration elle (0001 kalıbı); modeldeki default'lar `default=`, migration'da `server_default=sa.text("false")/("0")`
- [ ] **Step 4: SQLite smoke:** `alembic upgrade head` temp SQLite'ta 0001+0002 uygular; inspector ile yeni kolon/tablolar doğrulanır (0001'deki yöntemle)
- [ ] **Step 5: PASS + tam suite** → 83
- [ ] **Step 6: Commit** — `feat: PWA data model and migration`

---

### Task 2: Oturum sürümü + süre ayrımı + zorunlu şifre kilidi

**Files:**
- Modify: `app/auth.py`, `app/config.py`, `app/routers/auth_routes.py`
- Test: `app/tests/test_auth.py`

**Interfaces:**
- Produces:
  - config: `session_max_age` kalkmaz (geri uyum) ama yeni `personel_session_age: int = 2592000`, `admin_session_age: int = 43200`
  - `create_session_cookie(user_id, session_version) -> str` — değer `f"{user_id}:{session_version}"`
  - `read_session_cookie(value) -> tuple[int, int] | None`
  - `current_user`: çerez sürümü != user.session_version → 303 login. ESKİ FORMAT çerezler (":" içermeyen) → geçersiz say (herkes bir kez yeniden girer; kabul edilen davranış)
  - login route: çereze role göre max_age (personel 30g/admin 12s); sürümlü değer
  - `must_change_password` kilidi: yeni dependency `current_user_unlocked` — must_change_password=True ise 303 → `/sifre-degistir-zorunlu`; `/qr*`, `/admin*`, `/api/qr-token`, ödeme rotaları bu dependency'ye geçer (kiosk rotaları HARİÇ — localhost akışı etkilenmez). Şifre değiştirme rotaları + logout `current_user` (kilitsiz) kalır
  - Yeni sayfa `GET/POST /sifre-degistir-zorunlu`: yalnız yeni şifre (min 8) ister; kaydette must_change_password=False + session_version+1 + YENİ sürümlü çerez set edilip /qr'a yönlendirir (kullanıcı düşmez)
  - Şifre değişimi (normal /change-password ve admin sıfırlama): session_version+1; kendi değiştirdiyse yeni çerez verilir

- [ ] **Step 1: Failing testler**

```python
def test_session_version_invalidates_old_cookie(client, seeded_db):
    login(client)
    from app.db import get_db; from app.main import app
    db = next(app.dependency_overrides[get_db]())
    u = db.get(User, seeded_db); u.session_version += 1; db.commit()
    r = client.get("/qr", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"

def test_password_change_keeps_current_session(client, seeded_db):
    login(client)
    r = client.post("/change-password",
                    data={"old_password": "dogru123", "new_password": "yeni12345"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert client.get("/qr").status_code == 200   # yeni çerez verildi

def test_must_change_password_locks_pages(client, seeded_db):
    from app.db import get_db; from app.main import app
    db = next(app.dependency_overrides[get_db]())
    u = db.get(User, seeded_db); u.must_change_password = True; db.commit()
    login(client)
    r = client.get("/qr", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/sifre-degistir-zorunlu"

def test_forced_change_unlocks(client, seeded_db):
    from app.db import get_db; from app.main import app
    db = next(app.dependency_overrides[get_db]())
    u = db.get(User, seeded_db); u.must_change_password = True; db.commit()
    login(client)
    r = client.post("/sifre-degistir-zorunlu",
                    data={"new_password": "taze12345"}, follow_redirects=False)
    assert r.status_code == 303
    assert client.get("/qr").status_code == 200
```

- [ ] **Step 2: FAIL** — DİKKAT: mevcut auth testleri create_session_cookie imza değişiminden etkilenir; onları da güncelle (roundtrip testi `(42, 0)` çifti döner)
- [ ] **Step 3: Implement** — auth.py çekirdek + auth_routes'a zorunlu sayfa + admin `set_password` route'una `must_change_password=True; session_version+=1`
- [ ] **Step 4: PASS + tam suite** → 87 civarı (güncellenenler dahil)
- [ ] **Step 5: Commit** — `feat: versioned sessions, role-based expiry, forced password change`

---

### Task 3: Sağlayıcı katmanı (SMS/Mail/Payment protokolleri + demo'lar)

**Files:**
- Create: `app/providers/__init__.py`, `app/providers/messaging.py`, `app/providers/payment.py`
- Test: `app/tests/test_providers.py`

**Interfaces:**
- Produces:
  - messaging.py: `MessageProvider(Protocol)` → `gonder(hedef: str, kod: str) -> None`; `DemoMessageProvider` — gonder() hiçbir şey yapmaz (kod zaten reset servisinde demo_gosterim'e yazılır); `get_sms_provider()/get_mail_provider()` — env `SMS_PROVIDER/MAIL_PROVIDER` ("demo" → Demo; bilinmeyen → ValueError)
  - payment.py:
    ```python
    @dataclass
    class OdemeSonucu:
        basarili: bool
        ref: str
        mesaj: str
    class PaymentProvider(Protocol):
        def dogrula(self, kart_no: str, tutar: Decimal, ref: str) -> OdemeSonucu: ...
    class DemoPos:
        def dogrula(self, kart_no, tutar, ref):
            temiz = kart_no.replace(" ", "")
            if temiz.startswith("4242"):
                return OdemeSonucu(True, ref, "Onaylandı")
            return OdemeSonucu(False, ref, "Kart reddedildi")
    def get_payment_provider() -> PaymentProvider  # env PAYMENT_PROVIDER
    ```
  - config.py'ye: `sms_provider: str = "demo"`, `mail_provider: str = "demo"`, `payment_provider: str = "demo"`

- [ ] **Step 1: Failing testler** — DemoPos 4242 başarılı / 4000 red / boşluklu kart no; get_*_provider demo döner, bilinmeyen ValueError
- [ ] **Step 2: FAIL** → **Step 3: Implement** → **Step 4: PASS + tam suite** (~92)
- [ ] **Step 5: Commit** — `feat: provider layer with demo SMS, mail and POS`

---

### Task 4: Reset servisi (kod üretimi/doğrulama/sınırlar/gizli soru)

**Files:**
- Create: `app/services/reset.py`
- Test: `app/tests/test_reset.py`

**Interfaces:**
- Produces:
  - `normalize(cevap: str) -> str` — strip + Türkçe-duyarlı küçültme ("İstanbul"→"istanbul", "IĞDIR"→"ığdır"; çeviri tablosu İ→i, I→ı sonra lower)
  - `kanallar(user) -> list[dict]` — tanımlı yöntemler maskeli: `[{"kanal": "sms", "maske": "05** *** **12"}, {"kanal": "eposta", "maske": "a***@**.com"}, {"kanal": "gizli_soru", "soru": "..."}]`; maske kuralı: telefonun son 2 hanesi + eposta ilk harf ve @ sonrası ilk harf açık
  - `kod_talep(db, user, kanal) -> str|None` — saatte 3 sınırı (user_id bazlı ResetCode sayımı, son 1 saat); 6 haneli `secrets.randbelow` kod; bcrypt YERİNE sha256 hash (hız; kod zaten 10 dk ömürlü); demo sağlayıcıysa demo_gosterim doldurulur; provider.gonder çağrılır; None → sınır aşıldı
  - `kod_dogrula(db, user, girilen) -> bool` — kullanılmamış+süresi geçmemiş son kodu bulur; 5 yanlış denemede kodu used=True yapar (deneme sayacı ResetCode'a `attempts int default 0` — Task 1 migration'ına dahil ET); doğruysa used=True + True
  - `gizli_dogrula(user, cevap) -> bool` — normalize + bcrypt verify
  - `sifre_sifirla(db, user, yeni) -> None` — hash + must_change_password=False + session_version+=1 + commit

DİKKAT Task 1 bağı: `attempts` kolonu ResetCode'da olmalı — Task 1'i uygularken bu kolonu ekle (int, default 0, server_default "0").

- [ ] **Step 1: Failing testler** — normalize Türkçe; kanallar maskeleri; kod talep + doğrula turu; yanlış kod 5. denemede iptal; saatte 3 sınırı; süresi geçmiş kod red; gizli soru doğru/yanlış; sifre_sifirla sürüm artırır
- [ ] **Step 2-4: FAIL → implement → PASS + tam suite** (~101)
- [ ] **Step 5: Commit** — `feat: password reset service with limits and secret question`

---

### Task 5: Şifremi unuttum akış sayfaları

**Files:**
- Modify: `app/routers/auth_routes.py`, `app/templates/login.html`
- Create: `app/templates/app/unuttum_sicil.html`, `unuttum_yontem.html`, `unuttum_kod.html`, `unuttum_soru.html`, `unuttum_yeni.html`
- Test: `app/tests/test_reset_flow.py`

**Interfaces:**
- Produces (rotalar; akış durumu imzalı kısa ömürlü `reset_state` çereziyle taşınır — user_id+aşama+kanal, 15 dk, salt="reset-state"):
  - `GET /sifremi-unuttum` — sicil formu
  - `POST /sifremi-unuttum` — sicil bul; kullanıcı yoksa VEYA yöntemi yoksa AYNI "yöntem bulunamadı → Yöneticinize başvurun" şablonu; varsa yöntem listesi (kanallar())
  - `POST /sifremi-unuttum/yontem` — kanal seç; sms/eposta → kod_talep (None → "Çok fazla deneme, sonra deneyin") + kod ekranı; gizli_soru → soru ekranı
  - `POST /sifremi-unuttum/kod` — kod_dogrula; başarı → aşama='yeni' çerezle yeni şifre ekranı; hata → mesajlı kod ekranı. "Yeniden gönder" butonu 60 sn client-side kilit
  - `POST /sifremi-unuttum/soru` — gizli_dogrula; aynı geçiş
  - `POST /sifremi-unuttum/yeni` — min 8 kontrol; sifre_sifirla; reset_state silinir; login'e "Şifreniz değişti, giriş yapın" flash
  - login.html'e "Şifremi unuttum" linki
  - Şablonlar PWA login stilinde (sayfa-orta kart, logo)

- [ ] **Step 1: Failing testler** — bilinmeyen sicil ve yöntemsiz kullanıcı aynı içerik (response.text eşit denecek kadar: her ikisinde "Yöneticinize başvurun" var, yöntem listesi yok); sms akışı uçtan uca (demo_gosterim'den kod okunup girilir → yeni şifre → yeni şifreyle login OK, eski şifre FAIL); gizli soru akışı; kod olmadan /yeni'ye direkt POST → 303 başa
- [ ] **Step 2-4: FAIL → implement → PASS + tam suite** (~107)
- [ ] **Step 5: Commit** — `feat: forgot-password flow pages`

---

### Task 6: Ödeme servisi + rotalar + demo POS sayfaları

**Files:**
- Create: `app/services/payment_flow.py`, `app/routers/payment_routes.py`, `app/templates/app/odeme_tutar.html`, `odeme_pos.html`, `odeme_sonuc.html`
- Modify: `app/main.py` (router)
- Test: `app/tests/test_payment.py`

**Interfaces:**
- Produces:
  - payment_flow: `baslat(db, user, tutar) -> Payment` (sınır 50-5000 kontrolü, ValueError; durum='baslatildi', saglayici_ref=`uuid4().hex[:16]`); `tamamla(db, payment_id, kart_no) -> Payment` — İDEMPOTENT: durum != 'baslatildi' ise mevcut kaydı aynen döner; provider.dogrula; başarılıysa TEK commit: payment.durum='basarili' + Transaction(type='yukleme', amount=tutar, balance_after, created_by=None) + payment.transaction_id + user.balance; redde 'basarisiz'
  - Rotalar (hepsi `current_user_unlocked`):
    - `GET /yukle` — tutar sayfası (hızlı 125/250/500/1000 + elle)
    - `POST /yukle` — baslat; hatada mesaj; başarıda `/yukle/{id}/pos`
    - `GET /yukle/{id}/pos` — POS formu (yalnız kendi payment'ı ve durum='baslatildi'; değilse 303 /yukle); "TEST MODU" ibaresi
    - `POST /yukle/{id}/pos` — tamamla(kart_no); sonuç sayfasına 303
    - `GET /yukle/{id}/sonuc` — başarılı: yeni bakiye+öğün; başarısız: tekrar dene butonu
  - Dashboard: `stats.dashboard_stats`'a `bugun_yuklenen` (bugünkü type='yukleme' toplamı) + dashboard.html'e 5. kart "Bugün Yüklenen" (grid 4→5'e değil: "Bugünkü Ciro" yanına sığdır — stat-kartlar grid'i auto-fit'e çevrilebilir)

- [ ] **Step 1: Failing testler** — sınırlar (49 red, 50 ok, 5000 ok, 5001 red); başarılı akış atomik (payment+tx+balance; tx.type=yukleme, created_by None); idempotens (tamamla ikinci çağrı: bakiye bir kez artar); 4000 kartı → basarisiz + bakiye değişmez; başkasının payment'ına erişim 303; dashboard bugun_yuklenen doğru
- [ ] **Step 2-4: FAIL → implement → PASS + tam suite** (~115)
- [ ] **Step 5: Commit** — `feat: balance top-up with demo POS`

---

### Task 7: PWA app-shell — manifest, SW, alt sekmeler, profil

**Files:**
- Create: `app/static/manifest.json`, `app/static/sw.js`, `app/static/icons/icon-192.png`, `icon-512.png`
- Modify: `app/templates/base.html` (manifest link + SW register, yalnız app sayfalarında), `app/templates/qr.html` (app-shell'e), `app/routers/qr_routes.py`
- Create: `app/templates/app/_shell.html` (alt sekmeli layout), `gecmis.html`, `profil.html`
- Test: `app/tests/test_pwa.py`

**Interfaces:**
- Produces:
  - `_shell.html`: base'i extend; `{% block sekme %}` + alt `.sekme-cubuk` (4 sekme, aktif vurgu, ikonlar _icons.html'den veya emoji); min 44px hedefler
  - Rotalar: `GET /qr` (QR sekmesi — mevcut içerik shell'e taşınır, Geçmişim bölümü ÇIKAR), `GET /gecmis` (işlem listesi + ay özeti: bu ay yenen öğün sayısı, bu ay yüklenen toplam), `GET /profil` (şifre değiştir linki, kurtarma bilgileri formu: telefon/eposta/gizli soru+cevap — kaydında mevcut şifre doğrulaması `POST /profil/kurtarma`), `/yukle` Task 6'dan sekmeye bağlanır
  - manifest.json: name "Karatay Yemekhane", short_name "Yemekhane", start_url "/qr", display standalone, theme_color #205c42, background #f4f9f6, icons 192/512
  - sw.js: install'da app-shell varlıklarını (style.css, logo, qrcode.min.js) cache'ler; fetch: static → cache-first, diğer her şey network-only; offline navigasyonda basit "Bağlantı yok" yanıtı
  - İkonlar: logo.jpg'den Pillow ile üretilir (kare beyaz zemin ortasında logo) — üretim script'i tek seferlik çalıştırılıp PNG'ler commit edilir (Pillow yoksa `pip install pillow` yalnız lokal; requirements'a GİRMEZ)
  - base.html: `<link rel="manifest">` + theme-color meta + SW register script'i — yalnız `{% block pwa %}` içinde; _shell bu bloğu doldurur (admin/kiosk sayfaları PWA'sız kalır)

- [ ] **Step 1: Failing testler** — /manifest.json ve /static/sw.js 200; /gecmis ve /profil auth'lu (giriş yoksa 303); /gecmis "Bu ay" özet metni; /profil kurtarma POST mevcut şifre yanlışsa hata, doğruysa alanlar kaydolur ve gizli_cevap_hash düz metin DEĞİL
- [ ] **Step 2-4: FAIL → implement → PASS + tam suite** (~121)
- [ ] **Step 5: Commit** — `feat: PWA shell with tabs, history, profile and recovery info`

---

### Task 8: Admin entegrasyonu — bekleyen kodlar paneli, personel formu alanları, demo senaryosu

**Files:**
- Modify: `app/routers/admin_routes.py`, `app/templates/admin/dashboard.html`, `app/templates/admin/list.html` (yeni personel modalına opsiyonel alanlar), `app/templates/admin/detail.html` (kurtarma bilgileri görünümü)
- Create: `docs/demo-senaryosu.md`
- Test: `app/tests/test_admin_routes.py`

**Interfaces:**
- Produces:
  - Dashboard'a "Bekleyen Doğrulama Kodları" paneli: son 15 dk, used=False, demo_gosterim dolu ResetCode'lar (kişi adı + kanal + kod + kalan süre); stats.dashboard_stats'a `bekleyen_kodlar` listesi
  - create_user POST'una opsiyonel `telefon/eposta/gizli_soru/gizli_cevap` Form("") alanları (gizli_cevap doluysa hash'lenir); modal'a alanlar
  - detail.html: kurtarma bilgileri satırı (telefon/eposta VAR/YOK; gizli soru tanımlı mı) — değer düzenleme personelin işi, admin yalnız görür
  - Admin şifre sıfırlama zaten Task 2'de must_change_password=True yapıyor — detay sayfasındaki forma bilgi notu: "Personel ilk girişte yeni şifre belirlemek zorunda kalır"
  - docs/demo-senaryosu.md: sunum adımları (kurulum özeti, admin girişi, personel oluşturma, PWA kurulumu 'Ana ekrana ekle', şifremi unuttum + kodu dashboard'dan okuma, bakiye yükleme 4242 kartıyla, QR okutma + sesli anons, mükerrer/saat dışı senaryoları, 4000 kartıyla red senaryosu)

- [ ] **Step 1: Failing testler** — dashboard bekleyen kod görünür (kod_talep sonrası GET /admin içinde demo kod metni); create_user telefon+gizli soru ile → alanlar kayıtlı + cevap hash'li
- [ ] **Step 2-4: FAIL → implement → PASS + tam suite** (~124)
- [ ] **Step 5: Commit + push** — `feat: admin integration for reset codes and recovery fields`

---

### Task 9: RPi dağıtımı + uçtan uca doğrulama (kontrolör)

- [ ] Tar → RPi → `docker compose up --build -d` (migration 0002 otomatik)
- [ ] Doğrulamalar: `/health`; `/manifest.json` 200; migration sonrası eski kullanıcılar girebiliyor (session_version=0 ile yeni çerez akışı); telefondan PWA kurulumu; şifremi unuttum uçtan uca (kod admin dashboard'dan okunarak); 4242 ile yükleme → bakiye arttı → QR okutma çalışıyor; kiosk/anons regresyonsuz
- [ ] Kullanıcı gözle doğrular; demo-senaryosu.md üzerinden tam sunum provası

## Plan Notları

- Task 2 en riskli: çerez formatı değişiyor → dağıtımda TÜM mevcut oturumlar düşer (kabul edildi; kullanıcılar yeniden girer). Test güncellemeleri geniş — implementer önce `Select-String -Path app\tests -Pattern "create_session_cookie|session"` ile etki alanını çıkarmalı.
- Task 4'ün `attempts` kolonu Task 1 migration'ında olmalı — Task 1 brief'i bunu içerir (ResetCode'a `attempts int default 0` eklendi sayılır).
- `current_user_unlocked` dependency'si Task 2'de doğar; Task 6-7 rotaları onu kullanır.
- Kod hash'i sha256 (bcrypt değil): 6 haneli 10 dk ömürlü kod için bcrypt maliyeti gereksiz; sha256(kod + user_id salt) yeterli.
- SW cache sürümlemesi: sw.js içinde `CACHE_V = 'v1'` — statik değişince elle artırılır (YAGNI: otomatik build yok).
