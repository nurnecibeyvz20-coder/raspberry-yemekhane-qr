# Kayit, Onay ve Arayuz Gelistirmeleri Tasarimi

## Amac

Mevcut QR yemekhane sistemine personel kendi kayit basvurusu, admin onayi,
kalici QR kimligi, modern arayuzler ve aylik yemek takvimi eklenir. Mevcut
roller, bakiye, kiosk ve sifre sifirlama akislari korunur.

## Kullanici Kaydi ve Onay

- Yeni personel `/kayit` formunda sicil no, ad soyad ve sifre girer.
- Kayit `pending` durumda olusur; giris, QR, bakiye yukleme ve profil
  islemleri yapamaz.
- `User.registration_status` degerleri `pending`, `approved` ve `rejected`
  olur. Mevcut `is_active` alani, onaylanmis hesabin admin tarafindan
  pasife alinmasini temsil etmeye devam eder.
- Admin panelinde bekleyen kullanicilar listelenir. Admin onayladiginda
  kullanici `approved` olur, aktif edilir ve kalici QR kimligi uretilir.
- Admin reddettiginde kullanici `rejected` durumda saklanir ve giris yapamaz.
- Sicil no benzersizligi korunur; pending veya rejected bir basvurunun ayni
  sicil no ile tekrar kaydi engellenir.

## Kalici QR Kimligi

- `User.qr_secret` alaninda tahmin edilemez, rastgele benzersiz bir kimlik
  tutulur.
- Yalnizca onay aninda veya admin yeniden olusturdugunda deger atanir.
- QR token uretim ve kiosk dogrulama akisi, onaylanmis ve aktif kullaniciya
  ait mevcut kalici kimligi kontrol eder.
- Yeniden olusturma eski QR degerini gecersiz kilar.

## Yetki ve Pasiflik

- Admin rolu mevcut `require_admin` korumasi ile ayri kalir.
- `current_user` onaylanmamis veya reddedilmis kayitlari giris disinda bir
  sayfaya eristirmez.
- Pasif hesaplar login, QR, profil, bakiye yukleme, odeme ve check-in
  akislari tarafindan reddedilir.
- Admin bakiye yukleme ve kullanici duzenleme endpointleri pasif kullanici
  icin kullanici dostu hata mesaji doner; yeni islem veya bakiye hareketi
  olusmaz.

## Arayuz

- Login sayfasi modern gradyan zeminli, responsive kartli bir giris ekrani
  olur. Kayit ve sifre sifirlama baglantilari belirgin olur.
- Ortak CSS renk tokenlari, kartlar, butonlar, form durumlari, hover ve
  gecis animasyonlari iyilestirilir; mevcut Karatay yesil gorsel dili
  korunur.
- Kayit formu ayni gorsel dille hata ve basari durumlarini gosterir.
- Gizli soru inputu `Gizli sorunuzu yaziniz` placeholderini tasir.

## Odeme

- Hizli tutarlar 100, 250, 500 ve 1000 TL olur; butona tiklamak tutari form
  inputuna yazar.
- POS sayfasi canli kart on/arka yuz onizlemesi sunar.
- Kart sahibi, kart numarasi ve SKT tarayicida karta yansir.
- CVV odaklandiginda kart arka yuze doner; CVV girisi tamamlaninca on yuze
  geri doner.
- Ilk rakam 4 ise Visa, 5 ise MasterCard markasi gosterilir.
- Ad, SKT ve CVV sadece tarayicidaki onizleme icindir; forma gonderilmez ve
  sunucu/veritabani tarafinda saklanmaz.

## Sifre ve Kod Akisi

- Normal ve zorunlu sifre degisikligi sonrasi `Sifreniz basariyla
  degistirildi.` flash mesaji gosterilir.
- Demo SMS/e-posta saglayicisinda dogrulama kodu inputa varsayilan deger
  olur. Gercek saglayicilarda input bos kalir.

## Yemek Takvimi

- Personel gecmis sayfasi secili ay icin ileri/geri gezinmeli takvim icerir.
- Gecmis ve bugunun yemek kaydi varsa yesil, yoksa kirmizi olur.
- Gelecek gunler notr gorunur.
- Takvim mevcut islem gecmisi ve aylik ozetlerle birlikte gosterilir.

## Veri ve Testler

- Alembic migration `registration_status` ve `qr_secret` alanlarini ekler;
  mevcut kullanicilar `approved` olarak korunur.
- Kayit/onay/red, QR yeniden uretme, pasif hesap engelleri, hizli tutarlar,
  demo kodu, kart onizleme ve aylik takvim icin testler eklenir.
- Tum mevcut testler calismaya devam eder.
