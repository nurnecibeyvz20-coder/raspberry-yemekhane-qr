# UX Yeniden Tasarımı — Tasarım Dokümanı

Tarih: 2026-07-30
Durum: Onaylandı (kullanıcı ile bölüm bölüm gözden geçirildi)

## Amaç

Yemekhane QR sisteminin kullanıcı deneyimini modern SaaS paneli seviyesine
çıkarmak: sol menülü admin layout'u, istatistikli dashboard, az tıklamalı
akışlar (modaller), güçlü tablolar (arama + sıralama + sayfalama), toast
bildirimleri, personel işlem geçmişi ve kiosk görsel cilası.

Mevcut Karatay design system'i (#205c42 token'ları, logo) temel alınır;
mimari değişmez (FastAPI + Jinja2 + vanilla JS, framework yok).

## Kapsam ve Kararlar

| Konu | Karar |
|---|---|
| Hedef görünüm | Modern SaaS paneli (sol menü, kartlar, ikonlar) |
| Admin sorunları | Özet yok, çok tıklama, tablo zayıf, görsel fakir, geri bildirim yok — hepsi çözülür |
| Personel sayfası | Mevcut yapı + kendi işlem geçmişi (son 20) + öğün göstergesi |
| Kiosk | Akış aynı; animasyonlu geçişler + tipografi cilası |
| Teknoloji | Sunucu taraflı kalınır; native `<dialog>` modaller, inline SVG ikonlar |
| Test hedefi | Mevcut 42 korunur/güncellenir + yeniler ≈ 55 |

## Bölüm 1: Admin Layout ve Dashboard

### Sol kenar menülü layout

```
┌────────┬──────────────────────────────────────────┐
│  LOGO  │  Sayfa başlığı            Admin ▪ Çıkış  │
│ Karatay├──────────────────────────────────────────┤
│ ▣ Genel│                                          │
│ ▤ Perso│   (sayfa içeriği)                        │
│ ▥ İşlem│                                          │
│ ⚙ Ayarl│                                          │
└────────┴──────────────────────────────────────────┘
```

- Sol menü: `--k-birincil` zemin, beyaz ikonlu 4 madde — Genel Bakış,
  Personel, İşlemler, Ayarlar. Aktif madde açık zemin vurgulu. Altta
  "Karatay Belediyesi" imzası.
- Üst şerit: sayfa başlığı + sağda oturum bilgisi ve çıkış.
- Dar ekranda (tablet) menü ikonlara daralır (CSS media query).

### Dashboard (`/admin` yeni içeriği)

- 4 istatistik kartı: **Bugün Yiyen** (bugünkü meal_entries sayısı),
  **Aktif Personel**, **Toplam Bakiye** (aktif personel toplamı),
  **Bugünkü Ciro** (bugünkü 'yemek' işlemlerinin mutlak toplamı).
- İki panel: **Son İşlemler** (son 10: kim, tür, tutar, saat) ve **Son
  Başarısız Okutmalar** (failed_attempts son 5 — ilk kez arayüze çıkar).
- Personel listesi `/admin/personel`'e taşınır; eski `/admin` testleri
  güncellenir.

### İkon seti

Inline SVG (Lucide'den ~12 ikon: kullanıcılar, cüzdan, grafik, ayar,
arama, artı, düzenle, anahtar, güç, çıkış, onay, uyarı) —
`app/templates/_icons.html` Jinja makrosu. Harici bağımlılık yok.

## Bölüm 2: Personel Listesi, Modaller, Toast'lar

### Personel sayfası (`/admin/personel`)

```
┌──────────────────────────────────────────────────┐
│ [🔍 Ara: sicil veya ad...]      [+ Yeni Personel] │
├──────────────────────────────────────────────────┤
│ Sicil ▲│ Ad Soyad │ Bakiye ▼│ Durum │ İşlemler   │
│ 1001   │ Ali Veli │ 375,00  │ Aktif │ 💰 ✏ 🔑 ⏻  │
├──────────────────────────────────────────────────┤
│ 142 personel      ◀ 1 2 3 ▶      Sayfa: 50 kişi  │
└──────────────────────────────────────────────────┘
```

- **Sayfalama:** sunucu taraflı, 50 kayıt/sayfa, `?page=`; alt çubukta
  toplam + gezinme.
- **Sıralama:** Sicil/Ad/Bakiye başlıkları tıklanabilir
  (`?sort=balance&dir=desc`); yön oku gösterilir.
- **Arama:** mevcut `q` mantığı; 400ms debounce ile otomatik gönderim.
- **Satır içi işlemler** (ikon + tooltip): Bakiye Yükle (modal), Düzenle
  (modal), Şifre Sıfırla (modal), Pasife Al (onay sorusu).
- Ada tıklayınca detay sayfası açılır (detay korunur, yeni layout'a
  uyarlanır).

### Modaller

- Native `<dialog>` + hafif vanilla JS.
- Bakiye Yükle modalı: kişi adı, mevcut bakiye, tutar alanı, hızlı
  butonlar (+125 / +250 / +500 / +625), onay.
- Yeni Personel modalı: sicil, ad soyad, şifre, rol.
- Modaller MEVCUT POST endpoint'lerine gönderir — backend akışı
  değişmez, yalnız form taşınır; mevcut testler geçerli kalır.

### Toast bildirimleri

- Başarılı POST → redirect'te imzalı kısa ömürlü `flash` çerezi; sayfa
  yüklenince sağ üstte yeşil toast ("✓ Ali Veli'ye 500 TL yüklendi"),
  4 sn sonra kaybolur. Hatalar kırmızı toast.
- Yardımcı: `app/flash.py` — `set_flash(response, mesaj, tur)` +
  `get_flash(request)` (imzalı çerez, 60 sn ömür). Layout'ta toast HTML +
  ~10 satır JS.

### İşlemler sayfası (`/admin/islemler`)

Tüm para hareketleri: sayfalama + tür filtresi (yükleme/yemek/düzeltme).
Tarih aralığı filtresi YOK (YAGNI).

## Bölüm 3: Personel Sayfası ve Kiosk Cilası

### Personel QR sayfası

- Mevcut yapı korunur (topbar + QR kartı + bakiye + geri sayım).
- Bakiye kartına ek: "≈ N öğün" göstergesi (bakiye ÷ yemek ücreti,
  tam sayıya yuvarlanır aşağı).
- Altına **Geçmişim** bölümü: son 20 işlem (tarih, tür, tutar, işlem
  sonrası bakiye); yemekler `-125,00` kırmızı, yüklemeler `+500,00`
  yeşil. Aynı sayfada, telefonda kaydırılarak görülür. `GET /qr`
  context'ine son 20 transaction eklenir.

### Kiosk cilası (akış aynen korunur)

- Ekranlar arası 250ms fade; sonuç kartında hafif ölçek animasyonu
  (CSS transition/keyframes; JS mantığı değişmez, yalnız class'lar).
- Sonuç ikonuna giriş animasyonu (küçükten büyüyerek).
- Bekleme ekranı logo dairesine hafif nefes animasyonu (4 sn döngü).
- Sonuç ekranı alt kenarında 5 saniyede dolan ince beyaz geri sayım
  şeridi.

## Teknik Detaylar

- **Route değişiklikleri:** `/admin` → dashboard; `/admin/personel` →
  liste; yeni `/admin/islemler`. `require_admin` korumaları aynen.
- **Yeni modül:** `app/services/stats.py` — `dashboard_stats(db)`,
  `paginate(query, page, per_page=50)`.
- **Yeni modül:** `app/flash.py` (imzalı flash çerezi).
- **CSS:** style.css'e yeni bileşenler: `.yan-menu`, `.stat-kart`,
  `.modal`, `.toast`, `.sayfalama`, `.tablo-baslik-sirala` — hepsi
  mevcut token'larla; ham hex yasağı devam eder.
- **Testler:** taşınan route testleri güncellenir; yeniler: dashboard
  istatistik doğruluğu, sayfalama, sıralama, flash çerezi, personel
  geçmişi, işlemler sayfası filtresi. Hedef ≈ 55 test.

## Kapsam Dışı (YAGNI)

- SPA/framework geçişi, build zinciri
- Tarih aralığı filtreleri, CSV dışa aktarım
- Grafik/chart kütüphanesi (istatistikler sayısal kart)
- Personel fotoğrafı/avatar
- Kiosk bekleme ekranına menü/sayaç ekleme (kullanıcı istemedi)
- Koyu tema

## Doğrulama

- Tam suite her task sonunda yeşil; kritik sözleşmeler (kiosk id'leri,
  check-in akışı, form endpoint'leri) değişmez.
- RPi'ye dağıtım sonrası: dashboard istatistikleri gerçek veriyle,
  modal akışları ve toast'lar tarayıcıda, kiosk animasyonları ekranda
  gözle doğrulanır.
