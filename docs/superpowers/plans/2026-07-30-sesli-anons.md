# Sesli Anons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kiosk bip sesleri yerine Piper TTS ile Türkçe sesli anons.

**Architecture:** `app/tts.py` (metin üretimi + HMAC imza + Piper subprocess + disk cache) → `/api/checkin` yanıtına `anons` alanı → yeni `GET /api/tts` endpoint'i (localhost-only, imzalı) → kiosk JS Audio ile çalar. Model imaja build sırasında gömülür.

**Tech Stack:** piper-tts (pip), tr_TR-dfki-medium modeli, itsdangerous, FastAPI FileResponse.

## Global Constraints

- Anons metinleri spec'teki 6 kalıp AYNEN; bakiye `int()` ile kuruşsuz
- `/api/tts` localhost_only + imza zorunlu (imzasız/bozuk → 400, remote → 403)
- Cache: `/tmp/tts-cache/<sha256>.wav`; ikinci istek Piper çalıştırmaz
- Testlerde gerçek Piper ÇALIŞTIRILMAZ (subprocess mock'lanır)
- Kiosk JS'te ses hatası akışı asla bozmaz (catch)
- Her task sonunda tam suite yeşil; commit İngilizce `feat:`/`test:` önekli

---

### Task 1: app/tts.py — metin, imza, üretim, cache

**Files:**
- Create: `app/tts.py`
- Test: `app/tests/test_tts.py`

**Interfaces:**
- Consumes: `CheckinResult` (app.services.checkin), `settings.secret_key`
- Produces:
  - `anons_metni(result: CheckinResult) -> str` — spec tablosundaki 6 kalıp; onay: `f"Afiyet olsun {result.ad_soyad}. Kalan bakiyeniz {int(result.balance)} lira."`; yetersiz_bakiye/mukerrer ad'lı kalıplar (ad None ise adsız düz mesaj: "Bakiyeniz yetersiz." / "Bugün zaten giriş yaptınız."); diğerleri sabit
  - `imzala(text: str) -> str` (itsdangerous `Signer`, salt="tts", url-safe base64 metin üzerinden) ve `dogrula(text: str, sig: str) -> bool`
  - `uret(text: str) -> pathlib.Path` — cache yolu `/tmp/tts-cache/{sha256(text)}.wav`; yoksa `subprocess.run(["piper", "--model", MODEL_PATH, "--output_file", str(path)], input=text.encode(), check=True)`; `MODEL_PATH = os.environ.get("PIPER_MODEL", "/opt/piper/tr_TR-dfki-medium.onnx")`

- [ ] **Step 1: Failing testler**

`app/tests/test_tts.py`:
```python
from decimal import Decimal
from unittest.mock import patch
from app.services.checkin import CheckinResult
from app.tts import anons_metni, imzala, dogrula, uret

def R(status, ok=False, ad=None, bal=None):
    return CheckinResult(ok=ok, status=status, message="",
                         ad_soyad=ad, balance=bal)

def test_anons_onay():
    r = R("onay", ok=True, ad="Ali Veli", bal=Decimal("375.00"))
    assert anons_metni(r) == "Afiyet olsun Ali Veli. Kalan bakiyeniz 375 lira."

def test_anons_yetersiz_ve_mukerrer():
    assert anons_metni(R("yetersiz_bakiye", ad="Ayşe")) == "Ayşe, bakiyeniz yetersiz."
    assert anons_metni(R("mukerrer", ad="Can")) == "Can, bugün zaten giriş yaptınız."
    assert anons_metni(R("yetersiz_bakiye")) == "Bakiyeniz yetersiz."

def test_anons_sabitler():
    assert anons_metni(R("suresi_dolmus")) == "QR kodun süresi dolmuş, lütfen yenileyin."
    assert anons_metni(R("gecersiz")) == "Geçersiz QR kodu."
    assert anons_metni(R("hesap_pasif")) == "Hesabınız pasif durumda."

def test_imza_dogrulama():
    s = imzala("merhaba")
    assert dogrula("merhaba", s)
    assert not dogrula("merhaba", s + "x")
    assert not dogrula("baska", s)

def test_uret_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tts.CACHE_DIR", tmp_path)
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        # piper cikti dosyasini yazmis gibi yap
        from pathlib import Path
        Path(cmd[cmd.index("--output_file") + 1]).write_bytes(b"RIFF")
        class P: returncode = 0
        return P()
    monkeypatch.setattr("app.tts.subprocess.run", fake_run)
    p1 = uret("test metni")
    p2 = uret("test metni")
    assert p1 == p2 and p1.exists()
    assert len(calls) == 1  # ikinci cagri cache'ten
```

- [ ] **Step 2: FAIL doğrula** — `python -m pytest app/tests/test_tts.py -v` → ModuleNotFoundError

- [ ] **Step 3: `app/tts.py` yaz**

```python
import hashlib
import os
import subprocess
from pathlib import Path
from itsdangerous import BadSignature, Signer
from app.config import settings
from app.services.checkin import CheckinResult

CACHE_DIR = Path("/tmp/tts-cache")
MODEL_PATH = os.environ.get("PIPER_MODEL", "/opt/piper/tr_TR-dfki-medium.onnx")

_signer = Signer(settings.secret_key, salt="tts")

def anons_metni(result: CheckinResult) -> str:
    if result.status == "onay":
        return (f"Afiyet olsun {result.ad_soyad}. "
                f"Kalan bakiyeniz {int(result.balance)} lira.")
    if result.status == "yetersiz_bakiye":
        return (f"{result.ad_soyad}, bakiyeniz yetersiz."
                if result.ad_soyad else "Bakiyeniz yetersiz.")
    if result.status == "mukerrer":
        return (f"{result.ad_soyad}, bugün zaten giriş yaptınız."
                if result.ad_soyad else "Bugün zaten giriş yaptınız.")
    if result.status == "suresi_dolmus":
        return "QR kodun süresi dolmuş, lütfen yenileyin."
    if result.status == "hesap_pasif":
        return "Hesabınız pasif durumda."
    return "Geçersiz QR kodu."

def imzala(text: str) -> str:
    return _signer.sign(text.encode()).decode().rsplit(".", 1)[1]

def dogrula(text: str, sig: str) -> bool:
    try:
        _signer.unsign(f"{text}.{sig}".encode())
        return True
    except (BadSignature, UnicodeError):
        return False

def uret(text: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / (hashlib.sha256(text.encode()).hexdigest() + ".wav")
    if path.exists():
        return path
    subprocess.run(
        ["piper", "--model", MODEL_PATH, "--output_file", str(path)],
        input=text.encode(), check=True, timeout=15)
    return path
```

DİKKAT (imza ayracı): Signer imzayı `deger.imza` formatında üretir; metinde
nokta bulunabilir, bu yüzden `rsplit(".", 1)` ile SON parça alınır ve
doğrulamada aynı biçimde birleştirilir — test bunu kanıtlar.

- [ ] **Step 4: PASS + tam suite** → 57 + 5 = 62 passed

- [ ] **Step 5: Commit** — `git add app/tts.py app/tests/test_tts.py && git commit -m "feat: TTS announcement text, signing and cached synthesis"`

---

### Task 2: /api/tts endpoint'i + checkin yanıtına anons alanı

**Files:**
- Modify: `app/routers/kiosk_routes.py`
- Test: `app/tests/test_kiosk_routes.py`

**Interfaces:**
- Consumes: Task 1 (`anons_metni`, `imzala`, `dogrula`, `uret`), `localhost_only`
- Produces:
  - `/api/checkin` yanıtına ek alan: `"anons": {"text": str, "sig": str}`
  - `GET /api/tts?text=...&sig=...` (localhost_only): `dogrula` başarısızsa 400; başarılıysa `uret(text)` → `FileResponse(path, media_type="audio/wav")`

- [ ] **Step 1: Failing testler** (test_kiosk_routes.py'ye ekle)

```python
def test_checkin_response_includes_signed_announcement(client, seeded_db):
    from app.qr_token import generate_token
    from app.tts import dogrula
    r = client.post("/api/checkin", json={"token": generate_token(seeded_db)})
    body = r.json()
    assert "anons" in body
    assert "Afiyet olsun" in body["anons"]["text"]
    assert dogrula(body["anons"]["text"], body["anons"]["sig"])

def test_tts_rejects_bad_signature(client, seeded_db):
    r = client.get("/api/tts", params={"text": "istedigim metni okut", "sig": "sahte"})
    assert r.status_code == 400

def test_tts_rejected_from_remote(client_remote, seeded_db):
    r = client_remote.get("/api/tts", params={"text": "x", "sig": "y"})
    assert r.status_code == 403

def test_tts_serves_wav(client, seeded_db, monkeypatch, tmp_path):
    from app import tts
    wav = tmp_path / "a.wav"; wav.write_bytes(b"RIFFtest")
    monkeypatch.setattr("app.routers.kiosk_routes.uret", lambda t: wav)
    metin = "deneme anonsu"
    r = client.get("/api/tts", params={"text": metin, "sig": tts.imzala(metin)})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content == b"RIFFtest"
```

- [ ] **Step 2: FAIL doğrula**

- [ ] **Step 3: kiosk_routes.py güncelle**

`checkin` fonksiyonunda: `metin = anons_metni(r)` → yanıta `"anons": {"text": metin, "sig": imzala(metin)}`. Yeni route:
```python
@router.get("/api/tts", dependencies=[Depends(localhost_only)])
def tts_endpoint(text: str, sig: str):
    if not dogrula(text, sig):
        raise HTTPException(400, "Geçersiz imza")
    try:
        path = uret(text)
    except Exception:
        raise HTTPException(503, "Ses üretilemedi")
    return FileResponse(path, media_type="audio/wav")
```
Import: `from app.tts import anons_metni, dogrula, imzala, uret` + `from fastapi.responses import FileResponse`.

- [ ] **Step 4: PASS + tam suite** → 66 passed

- [ ] **Step 5: Commit** — `feat: TTS endpoint and announcement in checkin response`

---

### Task 3: Dockerfile'a Piper + model; kiosk JS anons

**Files:**
- Modify: `app/Dockerfile`, `app/requirements.txt`, `app/templates/kiosk.html`
- Test: tam suite (JS/build görsel; testler regresyon)

**Interfaces:**
- Consumes: Task 2 (`anons` alanı, `/api/tts`)
- Produces: imajda piper + model `/opt/piper/`; kiosk anonsu çalar

- [ ] **Step 1: requirements.txt'e ekle** — `piper-tts==1.2.*`

- [ ] **Step 2: Dockerfile'a model indirme ekle** (pip install'dan sonra):

```dockerfile
RUN mkdir -p /opt/piper && \
    python -m piper.download_voices --download-dir /opt/piper tr_TR-dfki-medium 2>/dev/null || \
    (apt-get update && apt-get install -y --no-install-recommends curl && \
     curl -fsSL -o /opt/piper/tr_TR-dfki-medium.onnx \
       "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx" && \
     curl -fsSL -o /opt/piper/tr_TR-dfki-medium.onnx.json \
       "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx.json" && \
     apt-get purge -y curl && rm -rf /var/lib/apt/lists/*)
ENV PIPER_MODEL=/opt/piper/tr_TR-dfki-medium.onnx
```

Not: piper CLI `--model x.onnx` yanında `.onnx.json` config dosyasını otomatik arar; ikisi de indirilir.

- [ ] **Step 3: kiosk.html JS güncelle** — `sesOk/sesHata/sesCal` bloğu kaldırılır; yerine:

```javascript
let aktifAnons = null;
function anonsCal(anons) {
    if (!anons || !anons.text) return;
    try {
        if (aktifAnons) { aktifAnons.pause(); }
        aktifAnons = new Audio("/api/tts?text=" +
            encodeURIComponent(anons.text) + "&sig=" +
            encodeURIComponent(anons.sig));
        aktifAnons.play().catch(() => {});
    } catch (e) { /* ses akisi bozmasin */ }
}
```
`showResult` içindeki `sesCal(d.ok);` → `anonsCal(d.anons);`. Eski `ok.wav/error.wav` dosyaları ve statik ses klasörü silinir (`git rm -r app/static/sounds`).

- [ ] **Step 4: Tam suite** → 66 passed

- [ ] **Step 5: Lokal derleme YAPILMAZ (Docker yok)** — Dockerfile satırları gözle doğrulanır; gerçek doğrulama RPi build'inde

- [ ] **Step 6: Commit + push** — `feat: Piper TTS voice announcements on kiosk` + push

- [ ] **Step 7: RPi dağıtım (kontrolör):** tar → `docker compose up --build -d` (build model indireceği için 5-10 dk) → `curl` sağlık kontrolleri → kiosk restart → kullanıcı QR okutup anonsu duyarak doğrular. Ek doğrulama: `docker compose exec app piper --help` çalışıyor mu; `docker compose exec app ls /opt/piper` model var mı.
