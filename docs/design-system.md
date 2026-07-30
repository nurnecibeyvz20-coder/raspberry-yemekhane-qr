# Karatay Belediyesi Yemekhane — Tasarım Sistemi

Tek doğruluk kaynağı: `app/static/style.css` dosyasındaki `:root` token'ları.
Tüm renkler, aralıklar, radius ve gölgeler bu token'lardan gelir.

## 1. Renk Paleti

| Token | Hex | Kullanım Yeri |
|---|---|---|
| `--k-birincil` | `#205c42` | Ana marka yeşili: `.btn` zemini, `.baslik`, tablo başlığı metni, topbar marka adı, aktif nav çizgisi, bakiye rakamları, kiosk idle gradyanının üst rengi |
| `--k-birincil-koyu` | `#17452f` | `.btn:hover` zemini, kiosk idle gradyanının alt rengi |
| `--k-birincil-acik` | `#2e7a58` | Bağlantı (`a`) rengi |
| `--k-yesil-100` | `#e8f2ed` | Açık yeşil zemin: tablo başlığı (`th`), `.bant-basari` zemini, `.rozet` zemini, `.alan:focus` halkası, `.btn-ikincil:hover` |
| `--k-yesil-50` | `#f4f9f6` | Sayfa arka planı (`body`), tablo satırı hover zemini |
| `--k-basari` | `#2e7a58` | Başarı durumu: kiosk yeşil sonuç ekranı, `.tutar-arti`, `.bant-basari` sol çizgisi |
| `--k-uyari` | `#d97706` | Uyarı durumu: kiosk sarı (mükerrer) sonuç ekranı, `.bant-uyari` metni ve sol çizgisi |
| `--k-hata` | `#b91c1c` | Hata durumu: kiosk kırmızı sonuç ekranı, `.btn-tehlike`, `.tutar-eksi`, `.bant-hata` metni ve sol çizgisi |
| `--k-uyari-zemin` | `#fef3cd` | `.bant-uyari` zemini |
| `--k-hata-zemin` | `#fde8e8` | `.bant-hata` zemini |
| `--k-metin` | `#1a2e24` | Ana metin rengi (`body`), kiosk "bağlanıyor" ekranının zemini |
| `--k-metin-soluk` | `#5f7268` | İkincil metin: `.soluk`, `.alan-etiket`, topbar nav/kullanıcı, `.rozet-gri` metni |
| `--k-cizgi` | `#d5e3db` | Kenarlıklar: topbar alt çizgisi, `.alan` kenarlığı, tablo satır ayracı, `.rozet-gri` zemini, QR kutusu kenarlığı |
| `--k-beyaz` | `#ffffff` | Kart/topbar/form zeminleri, buton metni, kiosk ekran metinleri, kiosk logo dairesi |

## 2. Tipografi, Aralık, Radius, Gölge

| Token | Değer | Kullanım |
|---|---|---|
| `--k-font` | `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | Tüm metinler (`body`, `.btn`, `.alan`) |
| `--k-radius` | `12px` | Kart ve form alanı köşeleri |
| `--k-radius-sm` | `8px` | Buton ve bant köşeleri |
| `--k-golge` | `0 2px 8px rgba(32, 92, 66, .10)` | Kart, topbar, `.btn:hover` |
| `--k-golge-buyuk` | `0 8px 24px rgba(32, 92, 66, .14)` | Kiosk idle ekranındaki logo dairesi |
| `--k-a1` | `8px` | Aralık ölçeği (küçük) |
| `--k-a2` | `16px` | Aralık ölçeği (temel) |
| `--k-a3` | `24px` | Aralık ölçeği (orta) |
| `--k-a4` | `32px` | Aralık ölçeği (büyük) |
| `--k-a6` | `48px` | Aralık ölçeği (çok büyük) |

Not: Yazı boyutları token'a bağlanmamıştır; bileşenlerde sabit `px`
değerleri kullanılır (ör. `.btn` 15px, `.tablo` 14px, `.rozet` 12px).

## 3. Bileşenler

### Yerleşim (Düzen)

| Class | Tarif | Kullanıldığı şablonlar |
|---|---|---|
| `.topbar` | Sayfa üstündeki beyaz marka + navigasyon çubuğu. | `qr.html`, `admin/_nav.html` (tüm admin sayfaları) |
| `.topbar-marka` | Topbar solundaki logo + kurum adı grubu (`.ad` ve `.alt` alt öğeleriyle). | `qr.html`, `admin/_nav.html` |
| `.topbar-nav` | Topbar ortasındaki sekme bağlantıları; aktif sekme `aktif` class'ı alır. | `admin/_nav.html` |
| `.topbar-sag` | Topbar sağındaki kullanıcı adı (`.kullanici`) + çıkış butonu grubu. | `qr.html`, `admin/_nav.html` |
| `.icerik` | Ortalanmış, maksimum 960px genişlikli sayfa içerik sarmalayıcısı. | `qr.html`, `admin/list.html`, `admin/form.html`, `admin/detail.html`, `admin/settings.html` |
| `.sayfa-orta` | İçeriği ekranın tam ortasına yerleştiren tam yükseklik kap (giriş benzeri ekranlar). | `login.html`, `change_password.html` |

### Kart

| Class | Tarif | Kullanıldığı şablonlar |
|---|---|---|
| `.kart` | Beyaz zeminli, yuvarlatılmış, gölgeli içerik kutusu. | `login.html`, `change_password.html`, `qr.html`, `admin/list.html`, `admin/form.html`, `admin/detail.html`, `admin/settings.html` |

### Butonlar

| Class | Tarif | Kullanıldığı şablonlar |
|---|---|---|
| `.btn` | Birincil yeşil eylem butonu. | `login.html`, `change_password.html`, `admin/list.html`, `admin/form.html`, `admin/detail.html`, `admin/settings.html` |
| `.btn-ikincil` | Beyaz zeminli, yeşil kenarlıklı ikincil buton (`.btn` ile birlikte). | `qr.html` (Çıkış), `change_password.html` (Vazgeç), `admin/_nav.html` (Çıkış), `admin/list.html` (Ara), `admin/detail.html` (Değiştir/Aktifleştir) |
| `.btn-tehlike` | Kırmızı tehlikeli eylem butonu (`.btn` ile birlikte). | `admin/detail.html` (Pasifleştir) |
| `.btn-blok` | Butonu tam genişliğe yayar (`.btn` ile birlikte). | `login.html`, `change_password.html`, `admin/form.html` |

### Form

| Class | Tarif | Kullanıldığı şablonlar |
|---|---|---|
| `.alan` | Metin/şifre girişi ve select için standart form alanı. | `login.html`, `change_password.html`, `admin/list.html`, `admin/form.html`, `admin/detail.html`, `admin/settings.html` |
| `.alan-etiket` | Form alanının üstündeki küçük soluk etiket. | `login.html`, `change_password.html`, `admin/form.html`, `admin/detail.html`, `admin/settings.html` |

### Tablo

| Class | Tarif | Kullanıldığı şablonlar |
|---|---|---|
| `.tablo` | Açık yeşil başlıklı, satır çizgili standart veri tablosu. | `admin/list.html`, `admin/detail.html` |
| `.sag` | Tablo hücresini sağa hizalar (sayısal sütunlar). | `admin/list.html`, `admin/detail.html` |
| `.tutar-arti` | Pozitif tutarı yeşil ve kalın gösterir. | `admin/detail.html` |
| `.tutar-eksi` | Negatif tutarı kırmızı ve kalın gösterir. | `admin/detail.html` |
| `.satir-pasif` | Pasif kaydın satırını soluklaştırır. | `admin/list.html` |

### Bantlar (uyarı kutuları)

| Class | Tarif | Kullanıldığı şablonlar |
|---|---|---|
| `.bant-hata` | Kırmızı sol çizgili hata mesajı bandı. | `login.html`, `change_password.html`, `qr.html` (yetersiz bakiye), `admin/form.html`, `admin/settings.html` |
| `.bant-uyari` | Turuncu sol çizgili uyarı bandı. | (Şu an hiçbir şablonda kullanılmıyor; hazır bileşen) |
| `.bant-basari` | Yeşil sol çizgili başarı bandı. | `admin/settings.html` (Kaydedildi) |

### Rozet

| Class | Tarif | Kullanıldığı şablonlar |
|---|---|---|
| `.rozet` | Yuvarlak hatlı küçük durum etiketi (varsayılan yeşil). | `admin/list.html`, `admin/detail.html` |
| `.rozet-gri` | Rozetin gri/pasif varyantı (`.rozet` ile birlikte). | `admin/list.html`, `admin/detail.html` |

### Yardımcılar

| Class | Tarif | Kullanıldığı şablonlar |
|---|---|---|
| `.baslik` | Birincil yeşil renkli sayfa/bölüm başlığı. | `login.html`, `change_password.html`, `admin/form.html`, `admin/detail.html`, `admin/settings.html` |
| `.soluk` | Metni ikincil (soluk) renge çevirir. | `login.html`, `qr.html`, `admin/list.html`, `admin/detail.html` |
| `.ust-bosluk` | Üste `--k-a3` (24px) boşluk ekler. | `login.html`, `change_password.html`, `admin/form.html`, `admin/detail.html`, `admin/settings.html`, `qr.html` |

### Kiosk'a özel stiller

Kiosk ekranı (`kiosk.html`) kendi `<style>` bloğunu içerir; tam ekran
`.screen` yapısı ve `#idle` / `#result` / `#connecting` ekranları burada
tanımlıdır. Renkleri yine `:root` token'larından alır:

- `#idle` — `--k-birincil` → `--k-birincil-koyu` gradyanı
- `#result.green` — `--k-basari` (onay)
- `#result.yellow` — `--k-uyari` (mükerrer)
- `#result.red` — `--k-hata` (ret)
- `#connecting` — `--k-metin` zemini
- `.logo-yuvarlak` — beyaz daire + `--k-golge-buyuk`

## 4. Kurallar

1. **Yeni ekran eklerken bu token'ları kullan.** Renk, aralık, radius ve
   gölge için önce `:root`'taki token'lara bak; uymayan bir değer gerekiyorsa
   token ekle, satır içine sabit yazma.
2. **Şablon veya CSS bileşenine ham hex yazma.** Ham hex yalnızca
   `style.css` içindeki `:root` bloğunda bulunabilir. Şablonlardaki inline
   stiller de dahil: renk gerekiyorsa `var(--k-...)` kullan.
3. **Kiosk sonuç renkleri `--k-basari` / `--k-uyari` / `--k-hata`'ya
   bağlıdır.** Kiosk JS'i `green`/`yellow`/`red` class'larını atar; bu
   class'ların arka planları token'lardan gelir. Sonuç renklerini
   değiştirmek için yalnız token değerini güncelle, kiosk şablonuna veya
   JS'e dokunma.

## 5. Logo Kullanımı

Dosya: `app/static/logo.jpg` (URL: `/static/logo.jpg`)

| Boyut | Nerede | Nasıl |
|---|---|---|
| 32px yükseklik | Topbar (`.topbar-marka img`) — QR sayfası ve admin sayfaları | `style.css`'te `height: 32px` |
| 64px yükseklik | Giriş ekranı kartı (`login.html`) | Inline `style="height: 64px"` |
| 160px genişlik | Kiosk idle ekranı, 200px beyaz daire (`.logo-yuvarlak`) içinde | `kiosk.html` içi stil: `width: 160px` |
