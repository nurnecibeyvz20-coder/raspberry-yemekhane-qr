# Misafir Talep ve QR Tasarımı

## Amaç

Personelin misafir için yemek talebi oluşturmasını, yöneticinin talebi
incelemesini ve onaylanan misafire tarih-saat ve kullanım hakkıyla sınırlı QR
verilmesini sağlar.

## Veri Modeli

- `GuestRequest`: personel sahibi, ad, soyad, isteğe bağlı TC no, telefon,
  ziyaret nedeni, ziyaret tarihi, yemek adedi, başlangıç/bitiş saati, durum,
  QR sırrı, kalan hak ve oluşturulma/güncellenme zamanlarını tutar.
- Durumlar `pending`, `approved`, `rejected`, `exhausted`, `expired` olur.
- `GuestRequestEvent`: talep oluşturma, düzenleme, onay, red ve QR kullanımı
  için denetim kaydı tutar. Kaydı oluşturan kullanıcı ve zaman saklanır.

## Personel Akışı

- Personel profil/sekmeler alanından `Misafir Talebi` sayfasına gider.
- Formda ad, soyad, isteğe bağlı TC no, telefon, ziyaret nedeni, ziyaret
  tarihi ve 1 veya daha fazla yemek adedi bulunur.
- Talep yalnızca gelecekteki veya bugünün tarihi için oluşturulur; başlangıç
  ve bitiş saati sistem servis saatleriyle otomatik doldurulur.
- Gönderimden sonra talep `pending` olur ve QR gösterilmez.
- Onaylanan talebin QR ekranı, kullanıcının kendi talep detayında görünür.

## Yönetici Akışı

- Yönetici genel bakışta `Bekleyen Misafir Talepleri` listesini görür.
- Düzenleme ekranında ziyaret bilgileri, yemek adedi ve saat aralığı
  güncellenebilir; bitiş saati başlangıçtan sonra olmalıdır.
- Onay güvenli rastgele QR sırrı üretir, kalan hakkı yemek adedine eşitler ve
  durumu `approved` yapar.
- Red gerekçesi isteğe bağlıdır; durum `rejected` olur ve QR oluşturulmaz.

## QR ve Kiosk Doğrulaması

- Misafir QR tokenı normal personel tokenından ayrı imza tuzu kullanır.
- Kiosk tokenı doğruladığında talebin `approved` durumda olduğunu, ziyaret
  tarihinin bugüne eşit olduğunu, saat aralığında bulunduğunu ve kalan hakkın
  sıfırdan büyük olduğunu denetler.
- Başarılı kullanım kalan hakkı atomik olarak bir azaltır; sıfır olduğunda
  durum `exhausted` olur.
- Geçmiş tarihli kullanılmamış onaylar ilk kontrolde `expired` durumuna geçer.
- Misafir QR kullanımı personel bakiyesini, `MealEntry` kaydını veya personel
  günlük giriş sınırını değiştirmez.

## Denetim ve Test

- Oluşturma, düzenleme, onay, red ve her QR kullanımı `GuestRequestEvent`
  kaydı oluşturur.
- Testler form doğrulamasını, yetkiyi, saat/tarih sınırını, tek/çoklu kullanım
  hakkını, QR tükenmesini ve normal personel check-in akışının etkilenmediğini
  kapsar.
