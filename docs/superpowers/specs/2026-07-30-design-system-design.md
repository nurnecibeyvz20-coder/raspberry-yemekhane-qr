# Karatay Belediyesi Design System — Tasarım Dokümanı

Tarih: 2026-07-30
Durum: Onaylandı (kullanıcı ile bölüm bölüm gözden geçirildi)

## Amaç

Yemekhane QR sisteminin tüm arayüzlerini Karatay Belediyesi kurumsal
kimliğine (#205c42 kurumsal yeşil + belediye logosu) uygun, tutarlı bir
design system ile yeniden tasarlamak. Stil: modern & yumuşak (açık yeşil
tonlu zeminler, yuvarlak köşeler, yumuşak gölgeler).

## Kapsam ve Kararlar

| Konu | Karar |
|---|---|
| Ana renk | #205c42 (kurumsal yeşil) |
| Stil | Modern & yumuşak: yuvarlak köşe, yumuşak gölge, açık yeşil zeminler |
| Logo | Tüm ekranlarda: üst çubukta küçük, kiosk beklemede büyük |
| Logo dosyası | `app/static/logo.jpg` (Wikipedia'dan indirilen Karatay Belediyesi logosu; kullanıcı teyidi bekleniyor) |
| Yöntem | CSS custom properties (token'lar) + mevcut şablonların refactor'u; framework yok |
| Kapsanan ekranlar | login, qr, change_password, kiosk, admin/list, admin/form, admin/detail, admin/settings (8 şablon) + base.html |
| Dokümantasyon | `docs/design-system.md` |

## Design Token'ları

`app/static/style.css` başında `:root` altında tanımlanır. Sistemin tek
doğruluk kaynağıdır; hiçbir şablonda ham hex kullanılmaz.

```css
:root {
  /* Kurumsal yeşil ve tonları */
  --k-birincil:       #205c42;  /* ana renk: butonlar, üst çubuk, vurgular */
  --k-birincil-koyu:  #17452f;  /* hover/aktif durumlar */
  --k-birincil-acik:  #2e7a58;  /* ikincil vurgu, linkler */
  --k-yesil-100:      #e8f2ed;  /* açık yeşil zemin (kartlar, satır hover) */
  --k-yesil-50:       #f4f9f6;  /* sayfa arka planı */

  /* Durum renkleri */
  --k-basari:  #2e7a58;
  --k-uyari:   #d97706;
  --k-hata:    #b91c1c;
  --k-uyari-zemin: #fef3cd;
  --k-hata-zemin:  #fde8e8;

  /* Nötrler */
  --k-metin:        #1a2e24;
  --k-metin-soluk:  #5f7268;
  --k-cizgi:        #d5e3db;
  --k-beyaz:        #ffffff;

  /* Modern & yumuşak stil */
  --k-radius:    12px;
  --k-radius-sm: 8px;
  --k-golge:     0 2px 8px rgba(32, 92, 66, .10);
  --k-golge-buyuk: 0 8px 24px rgba(32, 92, 66, .14);

  /* Aralık (8px taban) */
  --k-a1: 8px;  --k-a2: 16px;  --k-a3: 24px;  --k-a4: 32px;  --k-a6: 48px;

  /* Tipografi */
  --k-font: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
```

Kurallar:

- Kiosk sonuç renkleri palete bağlıdır: onay → `--k-basari`, mükerrer →
  `--k-uyari`, diğer hatalar → `--k-hata`.
- Kontrast: `#205c42` üzeri beyaz metin WCAG AA uyumlu (7.5:1). Buton ve
  üst çubuk metinleri her zaman beyaz.

## Bileşen Stilleri

Tek `style.css`, class tabanlı:

- **`.topbar`** — beyaz zemin, altta `--k-cizgi` çizgi, hafif gölge.
  Solda logo (32px) + "Karatay Belediyesi" (koyu yeşil, yarı kalın) +
  "Yemekhane" alt etiketi. Sağda kullanıcı adı + çıkış. Admin'de nav
  linkleri (Personel / Ayarlar), aktif sayfa altı yeşil çizgili.
- **`.btn`** — `--k-birincil` zemin, beyaz metin, `--k-radius-sm`;
  hover: `--k-birincil-koyu` + `translateY(-1px)` + gölge.
  **`.btn-ikincil`** — beyaz zemin, yeşil kenarlık + metin.
  **`.btn-tehlike`** — `--k-hata` zemin (pasife alma vb.).
- **`.alan`** — form alanı: beyaz zemin, `--k-cizgi` kenarlık,
  `--k-radius`; odak: yeşil kenarlık + `box-shadow: 0 0 0 3px
  var(--k-yesil-100)`. Etiketler küçük, `--k-metin-soluk`.
- **`.kart`** — beyaz zemin, `--k-radius`, `--k-golge`. Login formu, QR
  alanı, admin formları kart içinde. Sayfa zemini `--k-yesil-50`.
- **`.tablo`** — kart içinde; başlık satırı `--k-yesil-100` zemin + koyu
  yeşil metin; satır hover `--k-yesil-50`; ince satır çizgileri.
- **`.bant-hata` / `.bant-uyari` / `.bant-basari`** — durum bantları;
  ilgili zemin tonu + koyu renk metin, `--k-radius-sm`, sol kenarda 4px
  renk şeridi.
- **`.rozet`** — rol (personel/admin) ve durum (aktif/pasif) etiketleri;
  küçük, yuvarlak; yeşil/gri.

## Ekran Ekran Refactor

**Login:** `--k-yesil-50` zemin ortasında tek kart. Kart üstünde logo
(64px) + "Karatay Belediyesi" + "Yemekhane Sistemi" alt başlığı. Sicil no
+ şifre, tam genişlik yeşil "Giriş Yap" butonu. Hata `.bant-hata`.

**Personel QR:** Üst çubuk (logo + ad soyad + çıkış). Ortada kart: QR
(beyaz dolgu, ince yeşil çerçeve), altında bakiye büyük puntoyla
(`--k-birincil`, 32px kalın), geri sayım yeşil tonlarda. Düşük bakiye
bandı kartın üstünde `.bant-hata`. Şifre değiştir linki altta soluk.

**Kiosk:**
- Bekleme: `--k-birincil` → `--k-birincil-koyu` dikey degrade tam ekran;
  ortada büyük logo (160px, beyaz yuvarlak zemin içinde), beyaz "Karatay
  Belediyesi — Yemekhane", canlı saat (ince, büyük), "QR kodunuzu
  okutun" yönergesi.
- Sonuç: tam ekran düz renk (onay `--k-basari`, mükerrer `--k-uyari`,
  hata `--k-hata`); ortada büyük ikon (✓/⚠/✕), ad soyad, mesaj, kalan
  bakiye — beyaz, büyük punto.
- "Sistem bağlanıyor...": nötr koyu zemin.

**Admin (4 şablon):** Üst çubuk + nav. Liste: arama kutusu + "Yeni
Personel" butonu aynı satırda, altında `.tablo` kartı; bakiye sütunu sağa
hizalı; pasif satırlar soluk + gri rozet. Detay: üstte kişi kartı (ad,
sicil, bakiye büyük) + bakiye yükleme formu; altında iki tablo (işlemler,
girişler) — yüklemeler yeşil, yemek kesintileri kırmızı tutar rengiyle.
Form ve ayarlar tek kolonlu kart.

**change_password:** Login ile aynı düzen (ortalanmış kart), üst çubuk
ile.

## Logo

- Kaynak: `https://upload.wikimedia.org/wikipedia/tr/9/9b/Karatay-Belediyesi-logo.jpg`
  (kullanıcının verdiği karatay.bel.tr sayfasına bu ortamdan erişilemedi;
  Wikipedia'daki resmi logo görseli kullanıldı, kullanıcı teyidi
  masaüstündeki kopya üzerinden bekleniyor).
- Dosya: `app/static/logo.jpg`. Kiosk beklemede beyaz yuvarlak zemin
  içinde gösterilir (JPG'nin beyaz arka planı bu sayede sorun olmaz).

## Dokümantasyon

`docs/design-system.md`: palet tablosu (token → hex → kullanım yeri),
bileşen listesi ve kullanım örnekleri, "yeni ekran eklerken bu token'ları
kullan; ham hex yazma" kuralı.

## Kapsam Dışı (YAGNI)

- Koyu tema / tema değiştirici
- CSS framework, build süreci, icon font (ikonlar unicode karakter)
- Logo SVG'ye çevirme, favicon üretimi
- Animasyon kütüphanesi (yalnız CSS transition'lar)

## Test / Doğrulama

- Görsel değişiklik olduğu için mevcut 42 test davranış bozulmadığını
  doğrular (şablon class/yapı değişse de testler status code + içerik
  metnine baktığı için kritik metinler korunur: "Bakiyeniz yetersiz",
  "Hatalı sicil no veya şifre" vb.).
- Refactor sonrası tam suite çalıştırılır; kiosk ve QR sayfaları RPi'de
  gözle doğrulanır.
