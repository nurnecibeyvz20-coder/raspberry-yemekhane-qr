# Karatay Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tüm arayüzleri #205c42 kurumsal yeşil ve Karatay Belediyesi logosu etrafında kurulan token tabanlı design system ile yeniden tasarlamak.

**Architecture:** `style.css` CSS custom property token'ları + bileşen class'larıyla baştan yazılır; 9 Jinja2 şablonu bu class'ları kullanacak şekilde refactor edilir. Logo `app/static/logo.jpg` olarak eklenir. Davranış değişmez — mevcut 42 test yeşil kalmalıdır.

**Tech Stack:** Saf CSS (custom properties), Jinja2 şablonları. Framework/build yok.

## Global Constraints

- Ana renk `#205c42`; tüm renkler token üzerinden — şablonlarda/CSS bileşenlerinde ham hex YASAK (yalnız `:root` bloğunda hex bulunur)
- Token adları spec'teki gibi: `--k-birincil`, `--k-birincil-koyu: #17452f`, `--k-birincil-acik: #2e7a58`, `--k-yesil-100: #e8f2ed`, `--k-yesil-50: #f4f9f6`, `--k-basari: #2e7a58`, `--k-uyari: #d97706`, `--k-hata: #b91c1c`, `--k-uyari-zemin: #fef3cd`, `--k-hata-zemin: #fde8e8`, `--k-metin: #1a2e24`, `--k-metin-soluk: #5f7268`, `--k-cizgi: #d5e3db`, `--k-beyaz: #ffffff`, `--k-radius: 12px`, `--k-radius-sm: 8px`, `--k-golge`, `--k-golge-buyuk`, `--k-a1..--k-a6`, `--k-font`
- Bileşen class adları: `.topbar`, `.btn`, `.btn-ikincil`, `.btn-tehlike`, `.alan`, `.kart`, `.tablo`, `.bant-hata`, `.bant-uyari`, `.bant-basari`, `.rozet`
- Testlerin aradığı metinler AYNEN korunur: "Bakiyeniz yetersiz", "Hatalı sicil no veya şifre", "Eski şifre hatalı", "Çok fazla deneme", "QR kodunuzu okutun", "Bu sicil no zaten kayıtlı"
- Testlerin aradığı element id'leri korunur: `qrcode`, `balance`, `low-band`, `countdown`, `scan-input`, `idle`, `result`, `connecting`
- Kiosk sonuç renkleri: onay→`--k-basari`, mükerrer→`--k-uyari`, diğer→`--k-hata`
- Logo: `app/static/logo.jpg`; üst çubukta 32px, login kartında 64px, kiosk beklemede 160px beyaz yuvarlak zemin içinde
- Marka metni: "Karatay Belediyesi" + "Yemekhane" alt etiketi
- Her task sonunda TAM suite çalışır: `python -m pytest app/tests -v` → 42 passed
- Commit mesajları İngilizce, `feat:`/`refactor:`/`docs:` önekli

---

### Task 1: Logo + design token'ları + bileşen CSS'i + base.html topbar

**Files:**
- Create: `app/static/logo.jpg` (kaynak: `C:\Users\YAVUZ\AppData\Local\Temp\opencode\logo\karatay-logo.jpg` — kopyala)
- Modify: `app/static/style.css` (baştan yaz)
- Modify: `app/templates/base.html`
- Test: mevcut suite (görsel task; davranış testi yok, regresyon kontrolü var)

**Interfaces:**
- Consumes: mevcut şablonların linklediği `/static/style.css`, `{% block content %}` yapısı
- Produces:
  - Global Constraints'teki TÜM token'lar `:root` altında
  - Bileşen class'ları: `.topbar` (içinde `.topbar-marka`, `.topbar-nav`, `.topbar-sag`), `.btn`, `.btn-ikincil`, `.btn-tehlike`, `.alan`, `.alan-etiket`, `.kart`, `.tablo`, `.bant-hata`, `.bant-uyari`, `.bant-basari`, `.rozet`, `.rozet-gri`, `.sayfa-orta` (login benzeri ortalanmış sayfalar için), `.icerik` (topbar altı içerik konteyneri, max-width 960px)
  - base.html: `{% block topbar %}{% endblock %}` bloğu (varsayılan boş — kiosk/login topbar istemez) + `{% block content %}`; body `--k-yesil-50` zemin, `--k-font`
  - Topbar makro yapısı base.html'de tanımlı DEĞİL; her şablon kendi topbar'ını `{% block topbar %}` içinde kurar (Task 2-4'te)

- [ ] **Step 1: Logoyu kopyala**

```powershell
Copy-Item "C:\Users\YAVUZ\AppData\Local\Temp\opencode\logo\karatay-logo.jpg" "app\static\logo.jpg"
```

- [ ] **Step 2: style.css'i baştan yaz**

Tam içerik (`app/static/style.css`):

```css
/* ==== Karatay Belediyesi Design System ==== */
/* Tek dogruluk kaynagi: tum renkler bu token'lardan gelir. Ham hex yasak. */
:root {
  --k-birincil:       #205c42;
  --k-birincil-koyu:  #17452f;
  --k-birincil-acik:  #2e7a58;
  --k-yesil-100:      #e8f2ed;
  --k-yesil-50:       #f4f9f6;
  --k-basari:  #2e7a58;
  --k-uyari:   #d97706;
  --k-hata:    #b91c1c;
  --k-uyari-zemin: #fef3cd;
  --k-hata-zemin:  #fde8e8;
  --k-metin:        #1a2e24;
  --k-metin-soluk:  #5f7268;
  --k-cizgi:        #d5e3db;
  --k-beyaz:        #ffffff;
  --k-radius:    12px;
  --k-radius-sm: 8px;
  --k-golge:     0 2px 8px rgba(32, 92, 66, .10);
  --k-golge-buyuk: 0 8px 24px rgba(32, 92, 66, .14);
  --k-a1: 8px; --k-a2: 16px; --k-a3: 24px; --k-a4: 32px; --k-a6: 48px;
  --k-font: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

* { box-sizing: border-box; }
body {
  margin: 0; font-family: var(--k-font);
  background: var(--k-yesil-50); color: var(--k-metin);
}
a { color: var(--k-birincil-acik); }

/* ---- Topbar ---- */
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--k-beyaz); border-bottom: 1px solid var(--k-cizgi);
  box-shadow: var(--k-golge); padding: var(--k-a1) var(--k-a3);
}
.topbar-marka { display: flex; align-items: center; gap: var(--k-a2); }
.topbar-marka img { height: 32px; width: auto; }
.topbar-marka .ad { font-weight: 600; color: var(--k-birincil); }
.topbar-marka .alt { font-size: 12px; color: var(--k-metin-soluk); }
.topbar-nav { display: flex; gap: var(--k-a2); }
.topbar-nav a {
  text-decoration: none; color: var(--k-metin-soluk);
  padding: var(--k-a1) var(--k-a2); border-bottom: 2px solid transparent;
}
.topbar-nav a.aktif, .topbar-nav a:hover {
  color: var(--k-birincil); border-bottom-color: var(--k-birincil);
}
.topbar-sag { display: flex; align-items: center; gap: var(--k-a2); }
.topbar-sag .kullanici { color: var(--k-metin-soluk); font-size: 14px; }

/* ---- Duzen ---- */
.icerik { max-width: 960px; margin: var(--k-a3) auto; padding: 0 var(--k-a2); }
.sayfa-orta {
  min-height: 100vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; padding: var(--k-a2);
}

/* ---- Kart ---- */
.kart {
  background: var(--k-beyaz); border-radius: var(--k-radius);
  box-shadow: var(--k-golge); padding: var(--k-a3);
}

/* ---- Butonlar ---- */
.btn {
  display: inline-block; background: var(--k-birincil); color: var(--k-beyaz);
  border: none; border-radius: var(--k-radius-sm);
  padding: 10px var(--k-a3); font-size: 15px; font-family: var(--k-font);
  cursor: pointer; text-decoration: none;
  transition: background .15s, transform .15s, box-shadow .15s;
}
.btn:hover {
  background: var(--k-birincil-koyu); transform: translateY(-1px);
  box-shadow: var(--k-golge);
}
.btn-ikincil {
  background: var(--k-beyaz); color: var(--k-birincil);
  border: 1px solid var(--k-birincil);
}
.btn-ikincil:hover { background: var(--k-yesil-100); }
.btn-tehlike { background: var(--k-hata); }
.btn-tehlike:hover { background: var(--k-hata); opacity: .85; }
.btn-blok { display: block; width: 100%; text-align: center; }

/* ---- Form alanlari ---- */
.alan {
  width: 100%; padding: 10px var(--k-a2);
  border: 1px solid var(--k-cizgi); border-radius: var(--k-radius);
  font-size: 15px; font-family: var(--k-font); background: var(--k-beyaz);
  color: var(--k-metin);
}
.alan:focus {
  outline: none; border-color: var(--k-birincil);
  box-shadow: 0 0 0 3px var(--k-yesil-100);
}
.alan-etiket {
  display: block; font-size: 13px; color: var(--k-metin-soluk);
  margin: var(--k-a2) 0 4px;
}

/* ---- Tablo ---- */
.tablo { width: 100%; border-collapse: collapse; }
.tablo th {
  background: var(--k-yesil-100); color: var(--k-birincil);
  text-align: left; padding: var(--k-a1) var(--k-a2); font-size: 14px;
}
.tablo td {
  padding: var(--k-a1) var(--k-a2);
  border-bottom: 1px solid var(--k-cizgi); font-size: 14px;
}
.tablo tr:hover td { background: var(--k-yesil-50); }
.tablo .sag { text-align: right; }
.tutar-arti { color: var(--k-basari); font-weight: 600; }
.tutar-eksi { color: var(--k-hata); font-weight: 600; }
.satir-pasif td { opacity: .5; }

/* ---- Bantlar ---- */
.bant-hata, .bant-uyari, .bant-basari {
  border-radius: var(--k-radius-sm); padding: var(--k-a2);
  margin: var(--k-a2) 0; font-size: 14px;
}
.bant-hata {
  background: var(--k-hata-zemin); color: var(--k-hata);
  border-left: 4px solid var(--k-hata);
}
.bant-uyari {
  background: var(--k-uyari-zemin); color: var(--k-uyari);
  border-left: 4px solid var(--k-uyari);
}
.bant-basari {
  background: var(--k-yesil-100); color: var(--k-birincil);
  border-left: 4px solid var(--k-basari);
}

/* ---- Rozet ---- */
.rozet {
  display: inline-block; background: var(--k-yesil-100);
  color: var(--k-birincil); border-radius: 999px;
  padding: 2px 10px; font-size: 12px; font-weight: 600;
}
.rozet-gri { background: var(--k-cizgi); color: var(--k-metin-soluk); }

/* ---- Yardimcilar ---- */
.baslik { color: var(--k-birincil); margin: 0 0 var(--k-a2); }
.soluk { color: var(--k-metin-soluk); }
.ust-bosluk { margin-top: var(--k-a3); }
```

- [ ] **Step 3: base.html'i güncelle**

Tam içerik (`app/templates/base.html`):

```html
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}Karatay Belediyesi Yemekhane{% endblock %}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    {% block topbar %}{% endblock %}
    {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 4: Tam suite çalıştır**

Run: `python -m pytest app/tests -v`
Expected: 42 passed (davranış değişmedi)

- [ ] **Step 5: Ham hex denetimi**

Run (PowerShell): `Select-String -Path app\static\style.css -Pattern "#[0-9a-fA-F]{3,6}" | Where-Object { $_.LineNumber -gt 30 }`
Expected: boş (tüm hex'ler `:root` bloğunda, ~ilk 30 satırda)

- [ ] **Step 6: Commit**

```bash
git add app/static/logo.jpg app/static/style.css app/templates/base.html
git commit -m "feat: Karatay design tokens, component CSS, logo asset"
```

---

### Task 2: Login + şifre değiştirme sayfaları refactor

**Files:**
- Modify: `app/templates/login.html`, `app/templates/change_password.html`
- Test: mevcut suite (test_auth.py, test_qr_routes.py::test_change_password)

**Interfaces:**
- Consumes: Task 1 class'ları (`.sayfa-orta`, `.kart`, `.alan`, `.alan-etiket`, `.btn`, `.btn-blok`, `.bant-hata`, `.baslik`, `.soluk`), `/static/logo.jpg`
- Produces: — (yaprak task)
- Korunacak davranış: login POST form alan adları `sicil_no`/`password`; hata metni "Hatalı sicil no veya şifre" (error değişkeni); change_password form alanları `old_password`/`new_password`, hata "Eski şifre hatalı"

- [ ] **Step 1: login.html'i yeniden yaz**

Tam içerik:

```html
{% extends "base.html" %}
{% block title %}Giriş — Karatay Belediyesi Yemekhane{% endblock %}
{% block content %}
<div class="sayfa-orta">
  <div class="kart" style="width: 100%; max-width: 380px; text-align: center;">
    <img src="/static/logo.jpg" alt="Karatay Belediyesi" style="height: 64px; margin-bottom: 8px;">
    <h1 class="baslik" style="font-size: 20px;">Karatay Belediyesi</h1>
    <p class="soluk" style="margin-top: -8px;">Yemekhane Sistemi</p>
    {% if error %}<div class="bant-hata">{{ error }}</div>{% endif %}
    <form method="post" action="/login" style="text-align: left;">
      <label class="alan-etiket" for="sicil_no">Sicil No</label>
      <input class="alan" type="text" id="sicil_no" name="sicil_no" required autofocus>
      <label class="alan-etiket" for="password">Şifre</label>
      <input class="alan" type="password" id="password" name="password" required>
      <button class="btn btn-blok ust-bosluk" type="submit">Giriş Yap</button>
    </form>
  </div>
</div>
{% endblock %}
```

Not: mevcut login.html'deki error render mantığını (değişken adı, koşul) birebir koru — mevcut dosyaya bakıp `error` yerine farklı bir değişken kullanılıyorsa onu kullan.

- [ ] **Step 2: change_password.html'i yeniden yaz**

Tam içerik (mevcut dosyadaki form action ve alan adlarını koruyarak):

```html
{% extends "base.html" %}
{% block title %}Şifre Değiştir{% endblock %}
{% block content %}
<div class="sayfa-orta">
  <div class="kart" style="width: 100%; max-width: 380px;">
    <h1 class="baslik" style="font-size: 18px;">Şifre Değiştir</h1>
    {% if error %}<div class="bant-hata">{{ error }}</div>{% endif %}
    <form method="post" action="/change-password">
      <label class="alan-etiket" for="old_password">Eski Şifre</label>
      <input class="alan" type="password" id="old_password" name="old_password" required>
      <label class="alan-etiket" for="new_password">Yeni Şifre</label>
      <input class="alan" type="password" id="new_password" name="new_password" required minlength="8">
      <button class="btn btn-blok ust-bosluk" type="submit">Kaydet</button>
      <a class="btn btn-ikincil btn-blok ust-bosluk" href="/qr" style="margin-top: 8px;">Vazgeç</a>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: İlgili testleri çalıştır**

Run: `python -m pytest app/tests/test_auth.py app/tests/test_qr_routes.py -v`
Expected: hepsi PASS

- [ ] **Step 4: Tam suite**

Run: `python -m pytest app/tests -v`
Expected: 42 passed

- [ ] **Step 5: Commit**

```bash
git add app/templates/login.html app/templates/change_password.html
git commit -m "refactor: login and password pages with Karatay design"
```

---

### Task 3: Personel QR sayfası + kiosk refactor

**Files:**
- Modify: `app/templates/qr.html`, `app/templates/kiosk.html`
- Test: mevcut suite (test_qr_routes.py, test_kiosk_routes.py)

**Interfaces:**
- Consumes: Task 1 class'ları + token'ları, `/static/logo.jpg`
- Produces: —
- Korunacak: qr.html'de id'ler `qrcode`, `balance`, `low-band`, `countdown`; "Bakiyeniz yetersiz" metni; mevcut JS mantığı (refresh zinciri, fetch /api/qr-token) AYNEN taşınır. kiosk.html'de id'ler `idle`, `result`, `connecting`, `scan-input`; "QR kodunuzu okutun" metni; mevcut JS (Enter yakalama, fetch /api/checkin, ses, 5 sn dönüş) AYNEN taşınır — yalnız renkler CSS token'a bağlanır.

- [ ] **Step 1: qr.html refactor**

Yapı (mevcut JS bloğunu birebir koruyarak — script içeriğine DOKUNMA):

```html
{% extends "base.html" %}
{% block title %}QR Kodum{% endblock %}
{% block topbar %}
<div class="topbar">
  <div class="topbar-marka">
    <img src="/static/logo.jpg" alt="Karatay Belediyesi">
    <div><div class="ad">Karatay Belediyesi</div><div class="alt">Yemekhane</div></div>
  </div>
  <div class="topbar-sag">
    <span class="kullanici">{{ user.ad_soyad }}</span>
    <form method="post" action="/logout" style="margin:0">
      <button class="btn btn-ikincil" type="submit">Çıkış</button>
    </form>
  </div>
</div>
{% endblock %}
{% block content %}
<div class="icerik" style="max-width: 420px;">
  <div id="low-band" class="bant-hata" style="display: {{ 'block' if low_balance else 'none' }}; text-align:center;">Bakiyeniz yetersiz</div>
  <div class="kart" style="text-align: center;">
    <div id="qrcode" style="display:inline-block; padding: 12px; border: 1px solid var(--k-cizgi); border-radius: var(--k-radius); background: var(--k-beyaz);"></div>
    <div id="balance" style="font-size: 32px; font-weight: 700; color: var(--k-birincil); margin-top: 16px;">{{ user.balance }} TL</div>
    <div class="soluk">Bakiyeniz</div>
    <div id="countdown" class="soluk ust-bosluk" style="font-size: 14px;"></div>
    <a class="soluk" href="/change-password" style="font-size: 13px; display:inline-block; margin-top: 16px;">Şifre değiştir</a>
  </div>
</div>
<script src="/static/qrcode.min.js"></script>
<script>
/* MEVCUT qr.html'deki script bloğu BİREBİR buraya */
</script>
{% endblock %}
```

Önce mevcut `qr.html`'i oku; script bloğunu ve Jinja değişken adlarını (`user`, `low_balance`, `meal_price`) aynen koru. `var(--k-cizgi)` gibi token kullanımı inline style'da serbesttir (ham hex değil).

- [ ] **Step 2: kiosk.html refactor**

Yapı: mevcut script bloğu birebir korunur; yalnız HTML/CSS güncellenir. Ekran stilleri sayfa içi `<style>` bloğunda kalabilir ama TÜM renkler token'dan:

```html
{% extends "base.html" %}
{% block title %}Yemekhane Kiosk{% endblock %}
{% block content %}
<style>
  body { overflow: hidden; }
  .screen { position: fixed; inset: 0; display: none;
    flex-direction: column; align-items: center; justify-content: center;
    text-align: center; color: var(--k-beyaz); }
  .screen.active { display: flex; }
  #idle { background: linear-gradient(180deg, var(--k-birincil), var(--k-birincil-koyu)); }
  #idle .logo-yuvarlak {
    width: 200px; height: 200px; border-radius: 50%;
    background: var(--k-beyaz); display: flex; align-items: center;
    justify-content: center; box-shadow: var(--k-golge-buyuk); }
  #idle .logo-yuvarlak img { width: 160px; height: auto; }
  #idle h1 { font-size: 34px; font-weight: 600; margin: 24px 0 0; }
  #idle .saat { font-size: 72px; font-weight: 200; margin: 8px 0; }
  #idle .yonerge { font-size: 26px; opacity: .9; }
  #result.green  { background: var(--k-basari); }
  #result.yellow { background: var(--k-uyari); }
  #result.red    { background: var(--k-hata); }
  #result .ikon { font-size: 110px; line-height: 1; }
  #result .ad { font-size: 40px; font-weight: 700; margin: 12px 0 0; }
  #result .mesaj { font-size: 30px; margin: 8px 0; }
  #result .bakiye { font-size: 26px; opacity: .95; }
  #connecting { background: var(--k-metin); font-size: 30px; }
  #scan-input { position: absolute; opacity: 0; }
</style>
<div id="idle" class="screen active">
  <div class="logo-yuvarlak"><img src="/static/logo.jpg" alt="Karatay Belediyesi"></div>
  <h1>Karatay Belediyesi — Yemekhane</h1>
  <div class="saat" id="clock"></div>
  <div class="yonerge">QR kodunuzu okutun</div>
</div>
<div id="result" class="screen">
  <div class="ikon" id="result-icon"></div>
  <div class="ad" id="result-name"></div>
  <div class="mesaj" id="result-message"></div>
  <div class="bakiye" id="result-balance"></div>
</div>
<div id="connecting" class="screen">Sistem bağlanıyor...</div>
<input type="text" id="scan-input" autocomplete="off">
<script>
/* MEVCUT kiosk.html'deki script bloğu BİREBİR buraya;
   showResult ikon satırı yoksa ekle: ✓ (ok), ⚠ (mukerrer/yellow), ✕ (red) */
</script>
{% endblock %}
```

Önce mevcut `kiosk.html`'i oku: script'teki element id/class referanslarının (`clock`, `result-name` vb.) yeni HTML ile eşleştiğini doğrula; mevcut script farklı id kullanıyorsa HTML'i script'e uydur (script'i değil). İkon elementi mevcutta yoksa `showResult` içine tek satır ekle (`result-icon` doldurma); status→ikon eşlemesi: ok=✓, yellow=⚠, red=✕.

- [ ] **Step 3: İlgili testler**

Run: `python -m pytest app/tests/test_qr_routes.py app/tests/test_kiosk_routes.py -v`
Expected: hepsi PASS

- [ ] **Step 4: Tam suite**

Run: `python -m pytest app/tests -v`
Expected: 42 passed

- [ ] **Step 5: Commit**

```bash
git add app/templates/qr.html app/templates/kiosk.html
git commit -m "refactor: staff QR page and kiosk with Karatay design"
```

---

### Task 4: Admin şablonları refactor

**Files:**
- Modify: `app/templates/admin/_nav.html`, `admin/list.html`, `admin/form.html`, `admin/detail.html`, `admin/settings.html`
- Test: mevcut suite (test_admin_routes.py)

**Interfaces:**
- Consumes: Task 1 class'ları (`.topbar`, `.topbar-nav`, `.icerik`, `.kart`, `.tablo`, `.rozet`, `.rozet-gri`, `.tutar-arti`, `.tutar-eksi`, `.satir-pasif`, `.btn*`, `.alan*`, `.bant-*`)
- Produces: —
- Korunacak: tüm form action URL'leri ve alan adları; "Bu sicil no zaten kayıtlı" hata akışı; arama `q` parametresi; testin aradığı içerikler (kullanıcı adları listede görünür)

- [ ] **Step 1: _nav.html'i topbar'a dönüştür**

Tam içerik (`admin/_nav.html`):

```html
<div class="topbar">
  <div class="topbar-marka">
    <img src="/static/logo.jpg" alt="Karatay Belediyesi">
    <div><div class="ad">Karatay Belediyesi</div><div class="alt">Yemekhane Yönetimi</div></div>
  </div>
  <nav class="topbar-nav">
    <a href="/admin" class="{{ 'aktif' if aktif_sayfa == 'personel' else '' }}">Personel</a>
    <a href="/admin/settings" class="{{ 'aktif' if aktif_sayfa == 'ayarlar' else '' }}">Ayarlar</a>
  </nav>
  <div class="topbar-sag">
    <form method="post" action="/logout" style="margin:0">
      <button class="btn btn-ikincil" type="submit">Çıkış</button>
    </form>
  </div>
</div>
```

Not: mevcut `_nav.html`'deki logout form yapısını koru. `aktif_sayfa` değişkeni şablonlarda `{% set aktif_sayfa = 'personel' %}` ile include'dan ÖNCE set edilir (list/form/detail → 'personel', settings → 'ayarlar').

- [ ] **Step 2: list.html refactor**

Yapı: `{% block topbar %}{% set aktif_sayfa = 'personel' %}{% include "admin/_nav.html" %}{% endblock %}`; content'te `.icerik` içinde üst satır (arama formu `.alan` + "Ara" `.btn-ikincil` + sağda "Yeni Personel" `.btn`), altında `.kart` içinde `.tablo`: Sicil No / Ad Soyad / Rol (`.rozet`, admin ise düz `.rozet`, personel `.rozet-gri` DEĞİL — rol için: admin=`.rozet`, personel=`.rozet rozet-gri`) / Bakiye (`.sag` hizalı) / Durum (aktif=`.rozet` "Aktif", pasif=`.rozet rozet-gri` "Pasif") / İşlem ("Detay" linki). Pasif kullanıcı satırına `.satir-pasif`. Mevcut Jinja döngü değişkenlerini ve url yapılarını aynen koru.

- [ ] **Step 3: form.html refactor**

`.icerik` (max-width 480px) içinde `.kart`: başlık, hata varsa `.bant-hata`, form alanları `.alan`/`.alan-etiket`, gönder `.btn btn-blok`. Mevcut alan adlarını (sicil_no, ad_soyad, password, role) ve action'ı koru. Rol seçimi `<select class="alan">`.

- [ ] **Step 4: detail.html refactor**

`.icerik` içinde: üstte `.kart` (sol: ad `baslik` + sicil + rol/durum rozetleri; sağ: bakiye 32px `--k-birincil`; altta yatay form satırı: bakiye yükleme `.alan` + `.btn`, şifre sıfırlama formu, pasife al/aktifleştir `.btn-tehlike`/`.btn-ikincil`, düzenleme formu). Altında iki `.kart`: "İşlem Geçmişi" `.tablo` (tutar hücresi: pozitif `.tutar-arti` "+500.00", negatif `.tutar-eksi` "-125.00") ve "Yemek Girişleri" `.tablo`. Mevcut tüm form action'ları ve alan adları aynen korunur.

- [ ] **Step 5: settings.html refactor**

`{% set aktif_sayfa = 'ayarlar' %}` + nav include. `.icerik` (max-width 480px) `.kart`: başlık "Ayarlar", hata `.bant-hata` / başarı durumu varsa `.bant-basari`, meal_price alanı `.alan` + kaydet `.btn`. Mevcut form yapısı korunur.

- [ ] **Step 6: İlgili testler**

Run: `python -m pytest app/tests/test_admin_routes.py -v`
Expected: 9 passed

- [ ] **Step 7: Tam suite**

Run: `python -m pytest app/tests -v`
Expected: 42 passed

- [ ] **Step 8: Commit**

```bash
git add app/templates/admin/
git commit -m "refactor: admin panel with Karatay design"
```

---

### Task 5: Design system dokümantasyonu + RPi'ye dağıtım

**Files:**
- Create: `docs/design-system.md`
- Test: tam suite + RPi'de görsel doğrulama

**Interfaces:**
- Consumes: Task 1-4 çıktıları
- Produces: dokümantasyon; canlı sistemde yeni tasarım

- [ ] **Step 1: docs/design-system.md yaz**

İçerik: (1) Renk paleti tablosu — token adı | hex | kullanım yeri (Global Constraints'teki tüm renk token'ları); (2) tipografi/aralık/radius/gölge token'ları; (3) bileşen listesi — her class için tek cümle kullanım tarifi + hangi şablonlarda kullanıldığı; (4) kurallar: "yeni ekran eklerken bu token'ları kullan; şablon veya CSS bileşenine ham hex yazma (yalnız :root'ta); kiosk sonuç renkleri --k-basari/--k-uyari/--k-hata'ya bağlıdır"; (5) logo kullanımı: dosya yolu, üç boyut (32/64/160px) ve nerede.

- [ ] **Step 2: Tam suite**

Run: `python -m pytest app/tests -v`
Expected: 42 passed

- [ ] **Step 3: Commit + push**

```bash
git add docs/design-system.md
git commit -m "docs: design system reference"
git push origin main
```

- [ ] **Step 4: RPi'ye dağıt**

Kontrolör oturumunda (SSH ile): repo arşivini RPi'ye aktar (önceki dağıtımdaki tar yöntemi), `.env`'i koruyarak dosyaları güncelle, `docker compose up --build -d`, ardından `curl http://localhost/health` + `curl -s http://localhost/login | grep -c "Karatay"` ≥1 doğrulaması. Kiosk'un yeni tasarımla açıldığını kullanıcı ekrandan teyit eder.

## Plan Notları

- Şablon refactor'larında ALTIN KURAL: route'lara, JS mantığına, form alan
  adlarına, id'lere ve test metinlerine dokunma — yalnız görsel katman değişir.
- Her task öncesi implementer ilgili mevcut şablonu OKUMALI ve korunacak
  parçaları (script blokları, Jinja değişkenleri) yeni yapıya taşımalıdır.
- Task 3'teki şablon iskeletleri yol göstericidir; mevcut script'lerle id
  uyuşmazlığı çıkarsa script korunur, HTML uyarlanır.
