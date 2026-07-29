# Yemekhane QR Sistemi — Tasarım Dokümanı

Tarih: 2026-07-29
Durum: Onaylandı (kullanıcı ile bölüm bölüm gözden geçirildi)

## Amaç

Raspberry Pi 4/5 üzerinde, tamamı Docker'da çalışan bir yemekhane giriş ve
bakiye sistemi. Personel telefonundaki dinamik QR kodu, yemekhane girişindeki
USB HID QR okuyucuya okutur; sistem bakiyesinden yemek ücretini düşer ve
sonucu kiosk ekranında gösterir.

## Kapsam ve Kararlar

| Konu | Karar |
|---|---|
| QR tipi | Telefonda dinamik QR (kısa ömürlü, otomatik yenilenen) |
| QR erişimi | Yerel ağ web sitesi (internete kapalı) |
| QR ömrü | 60 sn token ömrü, 45 sn'de bir otomatik yenileme |
| Bakiye modeli | Ön yüklü TL bakiyesi |
| Yemek ücreti | Sabit 125 TL (admin panelden değiştirilebilir) |
| Giriş limiti | Günde 1 giriş (DB kısıtıyla garanti) |
| Kiosk ekranı | Ad + kalan bakiye + ONAY/RED, sesli/görsel uyarı |
| Admin paneli | Personel yönetimi + bakiye yükleme + ayarlar |
| Roller | 2 rol: personel, admin |
| Hesap oluşturma | Admin sabit şifreyle oluşturur; personel isterse değiştirir |
| Ölçek | 100–500 personel, RPi 4/5 |
| Uyarılar | Kiosk ekranında (yetersiz bakiye, geçersiz/süresi dolmuş QR, mükerrer giriş) + personel sayfasında düşük bakiye bandı |

## Mimari (Yaklaşım A: Tek backend + sunucu taraflı HTML)

```
┌─────────────────────── Raspberry Pi 4/5 ───────────────────────┐
│  ┌──────────── Docker Compose ────────────┐                    │
│  │  ┌──────────┐      ┌──────────────┐    │   ┌─────────────┐  │
│  │  │ Postgres │◄────►│ FastAPI app  │◄───┼───│ Chromium    │  │
│  │  │  16      │      │ (API + HTML) │    │   │ kiosk mode  │  │
│  │  └──────────┘      └──────┬───────┘    │   │ (systemd)   │  │
│  │  volume: pgdata           │ :80        │   └──────▲──────┘  │
│  └───────────────────────────┼────────────┘          │         │
│                              │                USB HID QR       │
│                              │                (klavye girdisi) │
└──────────────────────────────┼─────────────────────────────────┘
                               │ yerel ağ (LAN/WiFi)
                     ┌─────────┴──────────┐
                     │ Personel telefonu  │──► /qr  (dinamik QR)
                     │ Admin bilgisayarı  │──► /admin
                     └────────────────────┘
```

Bileşenler:

1. **`db` konteyneri** — PostgreSQL 16 (ARM64 resmi imaj), veriler named
   volume'da (`pgdata`). Port dışarı açılmaz, yalnız iç ağ.
2. **`app` konteyneri** — FastAPI + Jinja2 + hafif JS. Üç yüz:
   - `/qr` — personel girişi + dinamik QR (mobil öncelikli)
   - `/admin` — yönetim paneli
   - `/kiosk` — tam ekran sonuç ekranı (yalnız localhost)
3. **Kiosk tarayıcı (host)** — systemd servisi her boot'ta Chromium'u
   `--kiosk http://localhost/kiosk` ile açar. Docker dışındaki tek parça.
4. **USB HID QR okuyucu** — klavye emülasyonu; QR içeriğini yazıp Enter
   basar. Kiosk sayfası JS ile yakalar.

Teknoloji: Python 3.12, FastAPI, SQLAlchemy, Alembic (migration), psycopg,
passlib (bcrypt), Jinja2. Ağ erişimi RPi IP'si veya mDNS
(`http://yemekhane.local`).

## Veri Modeli (PostgreSQL)

```
users
├── id            (PK)
├── sicil_no      (unique, giriş için kullanıcı adı)
├── ad_soyad
├── role          ('personel' | 'admin')
├── password_hash (bcrypt)
├── balance       (NUMERIC(10,2))
├── is_active     (soft delete)
└── created_at

transactions                      ← tüm para hareketleri
├── id            (PK)
├── user_id       (FK → users)
├── type          ('yukleme' | 'yemek' | 'duzeltme')
├── amount        (işaretli: +yükleme, -yemek)
├── balance_after (işlem sonrası bakiye — denetim)
├── created_by    (FK → users; yüklemeyi yapan admin, yemekte NULL)
└── created_at

meal_entries                      ← yemekhane girişleri
├── id            (PK)
├── user_id       (FK → users)
├── entry_date    (DATE)
├── transaction_id(FK → transactions)
├── created_at
└── UNIQUE(user_id, entry_date)   ← günde 1 giriş garantisi

settings                          ← anahtar-değer ayarları
├── key           (PK, örn. 'meal_price')
└── value         (örn. '125.00')

failed_attempts                   ← hatalı okutma kayıtları
├── id, raw_qr
├── reason ('gecersiz'|'suresi_dolmus'|'hesap_pasif'|'yetersiz_bakiye'|'mukerrer')
├── user_id       (çözümlenebildiyse)
└── created_at
```

Önemli kararlar:

- **Bakiye çift kayıtlı:** hızlı okuma için `users.balance`, denetim için
  `transactions`. İkisi tek DB transaction'ında güncellenir.
- **`UNIQUE(user_id, entry_date)`:** günde-1-giriş kuralı DB kısıtında; yarış
  durumunda dahi çift giriş imkânsız.
- **Soft delete:** pasife alınan personelin geçmişi korunur, girişi engellenir.

## Dinamik QR Mekanizması

- Personel `/qr` sayfasına sicil no + şifreyle girer; oturum çerezi 7 gün.
- Sunucu her istekte imzalı kompakt token üretir: `user_id + son_kullanma
  (60 sn)`, HMAC ile `SECRET_KEY` üzerinden imzalanır.
- Sayfa QR'ı tarayıcıda çizer, 45 sn'de bir fetch ile yeniler (15 sn pay).
- Ekranda: QR, ad soyad, güncel bakiye, geri sayım. Bakiye < yemek ücreti ise
  kırmızı "Bakiyeniz yetersiz" bandı.

## Giriş (Check-in) Akışı

```
HID okuyucu QR'ı yazar + Enter
        ▼
Kiosk JS ──► POST /api/checkin {token}   (yalnız localhost)
        ▼
Kontroller (sırayla):
 1. İmza geçerli mi?      ✗ → "Geçersiz QR"                (kırmızı + ses)
 2. Süresi geçmiş mi?     ✗ → "QR süresi dolmuş"           (kırmızı + ses)
 3. Kullanıcı aktif mi?   ✗ → "Hesap pasif"                (kırmızı + ses)
 4. Bugün girmiş mi?      ✗ → "Bugün zaten girdiniz"       (sarı + ses)
 5. Bakiye ≥ ücret mi?    ✗ → "Yetersiz bakiye"            (kırmızı + ses)
        │ hepsi ✓
        ▼
Atomik: transactions(-ücret) + meal_entries + users.balance güncelle
        ▼
YEŞİL — "Afiyet olsun, <ad>" + kalan bakiye + onay sesi
(5 sn sonra bekleme ekranı: logo + saat)
```

- Tüm başarısız denemeler `failed_attempts`'a yazılır.
- Kiosk sayfası odağı daima gizli input'ta tutar; dokunmatik/fare gerekmez.
- Sesler tarayıcıda gömülü dosyalardan çalınır.

## Web Arayüzleri

**Personel (`/qr`)** — mobil öncelikli, tek ekran: giriş formu; ana ekranda
dinamik QR, ad soyad, bakiye, geri sayım, düşük bakiye bandı, şifre
değiştirme linki.

**Admin (`/admin`)** — masaüstü odaklı, sade tablolar:

1. Personel listesi: ad, sicil no, bakiye, durum; arama kutusu. Ekle /
   düzenle / şifre sıfırla / pasife al.
2. Bakiye yükleme: personel seç → tutar → yükle. Negatif tutar = düzeltme
   (`'duzeltme'` tipiyle kaydedilir).
3. Personel detayı: işlem geçmişi + giriş kayıtları.
4. Ayarlar: yemek ücreti.

Admin de `users` tablosunda (`role='admin'`); rota bazlı role kontrolü. İlk
admin ilk açılışta `.env`'deki bilgilerle otomatik oluşturulur.

**Kiosk (`/kiosk`)** — bekleme (logo + saat + "QR kodunuzu okutun") ve sonuç
(tam ekran yeşil/sarı/kırmızı kart). Yalnız localhost'tan erişilebilir.

## Docker Kurulumu ve RPi Entegrasyonu

Proje yapısı:

```
yemekhane/
├── docker-compose.yml
├── .env                      # SECRET_KEY, DB şifresi, ilk admin bilgileri
├── app/
│   ├── Dockerfile            # python:3.12-slim (ARM64)
│   ├── requirements.txt
│   ├── main.py + routers/ + models/ + templates/ + static/
│   └── migrations/           # alembic
└── deploy/
    ├── kiosk.service         # systemd: boot'ta Chromium kiosk
    └── install.sh            # tek komutla RPi kurulumu
```

- `db`: `postgres:16`, volume `pgdata`, yalnız iç ağ.
- `app`: `80:8000`, `depends_on: db (healthcheck)`, açılışta migration +
  ilk admin oluşturma.
- Her iki konteyner `restart: unless-stopped` → reboot'ta otomatik başlar.
- `kiosk.service`: graphical.target sonrası; `/health` yanıt verene kadar
  bekler, sonra Chromium'u kiosk modda açar. Ekran uyuması kapatılır, imleç
  gizlenir.
- `install.sh`: Docker kurulumu (yoksa) + compose up + systemd etkinleştirme.
- **Yedekleme:** cron + `pg_dump` ile günlük yedek (`/home/pi/backups`,
  son 30 gün).

Hata dayanıklılığı: app çökerse Docker yeniden başlatır; kiosk sayfası
bağlantı kopunca "Sistem bağlanıyor..." gösterip otomatik dener; DB kopması
healthcheck ile toparlanır.

## Güvenlik

- Şifreler bcrypt; QR token'ları HMAC imzalı; `SECRET_KEY` `.env`'de, git'e
  girmez.
- `/kiosk` ve `/api/checkin` yalnız localhost → telefondan sahte check-in
  yapılamaz.
- Admin rotaları role kontrolü; oturumlar imzalı çerez.
- Giriş denemelerine rate-limit (kaba kuvvet koruması).
- Sistem yalnız yerel ağda; internete açık yüzey yok.

## Test Stratejisi (TDD)

- **pytest birim/entegrasyon testleri:** token üretimi/doğrulama (geçerli,
  süresi dolmuş, sahte imza), check-in akışının 5 kontrolü, atomik bakiye
  düşme, günde-1-giriş kısıtı, bakiye yükleme/düzeltme.
- **Yarış durumu testi:** aynı token ile eşzamanlı iki istek → yalnız biri
  başarılı.
- Çalıştırma: `docker compose run app pytest` (RPi'ye atmadan önce lokalde).

## Kapsam Dışı (YAGNI)

- İnternete açık erişim, mobil uygulama
- Öğüne/role göre değişken ücret
- Raporlama/CSV dışa aktarım, canlı izleme panosu
- Görevli (üçüncü) rol
- Toplu personel içe aktarımı

Bunlar gerekirse sonraki iterasyonlarda eklenebilir; veri modeli buna
engel değil (örn. raporlar mevcut `transactions`/`meal_entries` üzerinden
üretilebilir).
