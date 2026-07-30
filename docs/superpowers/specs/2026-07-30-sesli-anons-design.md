# Sesli Anons (Piper TTS) — Tasarım Dokümanı

Tarih: 2026-07-30
Durum: Onaylandı

## Amaç

Kiosk'ta bip sesleri yerine Türkçe sesli anons: "Afiyet olsun Ahmet. Kalan
bakiyeniz 375 lira." Sistem internetsiz çalıştığı için ses cihazda (Piper
TTS, Docker imajında) üretilir.

## Kararlar

| Konu | Karar |
|---|---|
| TTS motoru | Piper (`tr_TR-dfki-medium` modeli, ~60 MB, imaja gömülü) |
| Üretim yeri | Backend (app konteyneri); kiosk hazır WAV çalar |
| Bip sesleri | Kaldırılır; anons onay/hata ayrımını zaten verir |
| Önbellek | Disk cache (aynı metin ikinci kez anında) |
| Güvenlik | `/api/tts` localhost-only + imzalı metin (keyfi metin okutulamaz) |

## Anons Metinleri

| Durum | Metin |
|---|---|
| onay | "Afiyet olsun {ad}. Kalan bakiyeniz {tam_lira} lira." |
| yetersiz_bakiye | "{ad}, bakiyeniz yetersiz." |
| mukerrer | "{ad}, bugün zaten giriş yaptınız." |
| suresi_dolmus | "QR kodun süresi dolmuş, lütfen yenileyin." |
| gecersiz | "Geçersiz QR kodu." |
| hesap_pasif | "Hesabınız pasif durumda." |

Bakiye kuruşsuz okunur: `int(balance)` → "375 lira" (virgül okunmaz).

## Akış

```
POST /api/checkin → CheckinResult → anons metni + HMAC imzası yanıt alanına:
  {"ok":..., "anons": {"text": "...", "sig": "..."}}
        ↓
Kiosk JS: new Audio(`/api/tts?text=...&sig=...`).play()
        ↓
GET /api/tts (localhost_only): imza doğrula → cache'e bak → yoksa Piper
  ile üret (WAV) → dosyayı döndür (media_type=audio/wav)
```

## Teknik Detaylar

- **Yeni modül `app/tts.py`:** `anons_metni(result: CheckinResult) -> str`,
  `imzala(text) -> str` / `dogrula(text, sig) -> bool` (itsdangerous,
  salt="tts"), `uret(text) -> Path` (Piper subprocess → cache dosyası,
  cache anahtarı metnin sha256'sı, dizin `/tmp/tts-cache`).
- **Dockerfile:** `piper-tts` pip paketi + model dosyaları
  (`tr_TR-dfki-medium.onnx` + `.json`) imaja indirilir (build sırasında
  HuggingFace'ten; RPi'de build internet gerektirir — mevcut durumla aynı).
- **checkin yanıtı:** `/api/checkin` yanıtına `anons` alanı eklenir
  (kiosk_routes'ta üretilir; CheckinResult değişmez).
- **Kiosk JS:** `sesCal(ok)` yerine `anonsCal(d.anons)`; Audio src
  `/api/tts?...`; ses yüklenemezse sessiz devam (catch).
- **Testler:** anons metni 6 durum; imza doğrulama (geçerli/sahte); tts
  endpoint 403 (remote), 400 (bozuk imza); cache hit davranışı (Piper'ı
  mock'layarak — gerçek model testte çağrılmaz).

## Kapsam Dışı

- Ses hızı/perde ayarı, çoklu ses seçimi
- Personel sayfasında ses
- Anonsun kuyruk yönetimi (üst üste okutma nadir; son anons öncekini keser)
