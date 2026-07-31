# Personel PWA Uygulaması — Tasarım Dokümanı

Tarih: 2026-07-31
Durum: Onaylandı (kullanıcı ile bölüm bölüm gözden geçirildi)

## Amaç

Personelin telefonuna kurulan (PWA) uygulama: sicil+şifre ile giriş,
şifremi unuttum (SMS/e-posta/gizli soru), zorunlu şifre değişimi, dinamik
QR, anlık bakiye + işlem geçmişi, mobilden bakiye yükleme (demo sanal
POS). Dış servisler (SMS/mail/ödeme) demo modda simüle; sağlayıcı
arayüzleriyle gerçeğe tek noktadan geçilir. Müşteri sunumuna hazır.

## Kararlar

| Konu | Karar |
|---|---|
| Teknoloji | PWA (manifest + service worker); tek codebase, mevcut FastAPI |
| Dış servisler | Demo mod: SMS/mail kodları admin panelde görünür; sanal POS test kartlarıyla simüle; `PaymentProvider`/`SmsProvider`/`MailProvider` arayüzleri |
| Bakiye yükleme | Personel kendisi yükler (demo ödeme → GERÇEK bakiye artışı) |
| Gizli soru | Tamamen yerel, demo değil gerçek |
| Oturum | Personel 30 gün, admin 12 saat; `session_version` ile toplu iptal |
| Admin paneli | Değişmez + Dashboard'a "Bekleyen Doğrulama Kodları" ve "Bugün Yüklenen" eklenir |

## Bölüm 1: Veri Modeli

`users` ek kolonlar (migration 0002):

```
telefon              VARCHAR(20)  NULL   (05xx — SMS sıfırlama)
eposta               VARCHAR(120) NULL
gizli_soru           VARCHAR(200) NULL
gizli_cevap_hash     VARCHAR(200) NULL   (bcrypt)
must_change_password BOOLEAN default false
session_version      INTEGER default 0
```

Yeni tablo `reset_codes`:

```
id, user_id(FK), kanal('sms'|'eposta'), kod_hash, demo_gosterim VARCHAR(6) NULL,
expires_at (10 dk), used BOOL, created_at
```

`demo_gosterim`: yalnız demo sağlayıcıda doldurulur (admin panelde
göstermek için); gerçek sağlayıcıda NULL kalır — hash her zaman yazılır.

Yeni tablo `payments`:

```
id, user_id(FK), tutar NUMERIC(10,2),
durum('baslatildi'|'basarili'|'basarisiz'),
saglayici('demo'|...), saglayici_ref VARCHAR(100),
transaction_id FK->transactions NULL, created_at, updated_at
```

Kurallar:
- Başarılı ödeme tek atomik commit: payments güncelle + Transaction
  (type='yukleme', created_by=NULL) + users.balance.
- Admin personel formuna telefon/eposta/gizli soru-cevap alanları
  (opsiyonel); personel Profil'den kendisi de günceller.
- Yeni personel ve admin şifre sıfırlaması → must_change_password=true.

## Bölüm 2: Şifremi Unuttum Akışı

1. Giriş ekranında "Şifremi unuttum" → sicil no gir.
2. Kayıtlı yöntemler maskeli listelenir (05** *** **12, a***@**.com,
   gizli soru). Hiçbiri yoksa: "Yöneticinize başvurun" (sicil
   var/yok sızdırılmaz — görünüm aynı).
3. SMS/e-posta: 6 haneli kod, 10 dk, tek kullanımlık, hash'li. Demo:
   kod admin Dashboard "Bekleyen Doğrulama Kodları" panelinde görünür.
   Kod ekranı: 6 haneli giriş + 60 sn beklemeli "yeniden gönder".
   Gizli soru: bcrypt karşılaştırma; küçük/büyük harf duyarsız, Türkçe
   normalize (İ→i, I→ı vb. lower).
4. Doğrulama → yeni şifre (min 8) → kaydet + must_change_password=false
   + session_version+1 → "Şifreniz değişti, giriş yapın".
5. Sınırlar: kod 5 yanlış → iptal; sicil başına saatte 3 talep.

Zorunlu değişim: must_change_password=true olan kullanıcı girişte şifre
değiştirme ekranına kilitlenir.

## Bölüm 3: Bakiye Yükleme (Demo Sanal POS)

1. Tutar: hızlı seçim 125/250/500/1000 + elle (min 50, max 5000 TL).
   → payments 'baslatildi'.
2. Demo POS ekranı: kart no/SKT/CVV/isim + "TEST MODU" ibaresi.
   Test kartları: 4242... → başarılı, 4000... → red.
   3D Secure simülasyonu: doğrulama kodu admin panelde görünür (SMS
   demo mekanizması).
3. Başarılı: atomik yükleme (Bölüm 1 kuralı) → yeni bakiye + öğün
   ekranı. Başarısız: 'basarisiz' + tekrar dene.

Sağlayıcı arayüzü:

```python
class PaymentProvider(Protocol):
    def baslat(tutar, user) -> OdemeOturumu
    def dogrula(oturum_ref) -> OdemeSonucu   # idempotent
```

`.env`: PAYMENT_PROVIDER=demo, SMS_PROVIDER=demo, MAIL_PROVIDER=demo.
İdempotens: aynı saglayici_ref ikinci kez işlenmez (çifte yükleme yok).
Admin: İşlemler'de "Mobil ödeme #ref" açıklaması; Dashboard'a "Bugün
Yüklenen" kartı.

## Bölüm 4: PWA Arayüzü

- manifest.json: "Karatay Yemekhane", logo ikonları 192/512, standalone,
  tema #205c42.
- Service worker: app-shell önbellek (CSS/JS/logo); API istekleri hep
  ağdan; ağ yoksa "Bağlantı yok" ekranı.
- "Ana ekrana ekle" yönlendirmesi (iOS için yönerge metni).
- Alt sekmeler: 🎫 QR | 📋 Geçmiş | 💳 Yükle | 👤 Profil.
  - QR: mevcut ekran (QR, geri sayım, bakiye+öğün, yedi kartı).
  - Geçmiş: işlem listesi + ay özeti (yenen öğün, yüklenen).
  - Yükle: Bölüm 3 akışı.
  - Profil: şifre değiştir, kurtarma bilgileri (telefon/eposta/gizli
    soru — gizli cevap değişiminde mevcut şifre sorulur), çıkış.
- Giriş: tam ekran, logo, "Şifremi unuttum" bağlantısı.
- Mevcut /qr URL'leri app-shell'e evrilir; masaüstünde dar kolon.
- Design system token'ları aynen; yeni bileşenler: alt sekme çubuğu,
  dokunma hedefleri min 44px.

## Bölüm 5: Oturum Güvenliği ve Teknik Yerleşim

- Çerez: `user_id:session_version` imzalı; sürüm uyuşmazsa oturum düşer.
- Sürüm artıran olaylar: şifre değişimi (kendi/admin), sıfırlama
  tamamlanması.
- Personel max_age 30 gün, admin 12 saat.

Modüller:

```
app/providers/{sms,mail,payment}.py   (Protocol + Demo implementasyonlar)
app/services/{reset,payment_flow}.py
app/routers/payment_routes.py (+ auth/qr routes genişler)
app/templates/app/  (PWA şablonları)
app/static/manifest.json, sw.js, icons/
migrations/0002_pwa_alanlari
```

## Test Stratejisi (~30 yeni; hedef ~110)

- Reset: üret/doğrula/süre/5-yanlış-iptal/saatte-3; gizli soru
  normalize; sicil sızdırmama.
- Ödeme: atomiklik, idempotens, red kartı, tutar sınırları.
- Oturum: sürüm iptali, must_change_password kilidi, farklı süreler.
- PWA: manifest/sw servis; sekmeler auth'lu; mevcut 81 test yeşil.

## Dağıtım ve Sunum

- Migration otomatik (entrypoint). PWA ikonları logodan üretilir.
- `docs/demo-senaryosu.md`: müşteri sunum adımları (giriş → şifremi
  unuttum → kodu admin panelden okuma → ödeme → QR okutma → sesli anons).

## Kapsam Dışı (sonraki fazlar)

- Admin mobil uygulaması (ayrı spec)
- Gerçek iyzico/Netgsm/SMTP entegrasyonları (arayüzler hazır; anahtar +
  implementasyon fazı)
- Raporlama/CSV, teslim paketi, izleme (ayrı spec'ler)
- Push bildirimleri
