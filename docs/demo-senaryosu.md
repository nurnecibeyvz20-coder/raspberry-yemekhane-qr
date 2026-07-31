# Müşteri Demo Senaryosu

## Sistem Özeti

Yemekhane QR sistemi; personelin telefonundaki PWA uygulamasından ürettiği
QR kodu, yemekhane girişindeki Raspberry Pi kioskuna okutmasıyla çalışır.
Okutma anında bakiyeden yemek ücreti düşülür ve sesli anons yapılır. Admin
paneli personel yönetimi, bakiye yükleme, işlem geçmişi, servis saati ve
yemek ücreti ayarlarını sunar; personel PWA'sı bakiye görüntüleme, kartla
bakiye yükleme ve "şifremi unuttum" akışını içerir. Demo modunda SMS /
e-posta gerçek gönderilmez; doğrulama kodları admin panosundaki "Bekleyen
Doğrulama Kodları" panelinden okunur.

## Hazırlık

- Raspberry Pi açık, kiosk ekranı çalışır durumda (QR okuyucu bağlı).
- Sunucu ayakta, yerel ağda erişilebilir.
- Admin hesabıyla `/admin` girişi yapılmış.
- Demo telefonu aynı ağda, tarayıcı açık.
- Servis saatinin şu anki saati kapsadığından emin olun
  (Ayarlar → Servis Saatleri) — QR okutma adımı buna bağlıdır.

## Senaryo Adımları

### a) Admin panelde personel oluşturma (kurtarma bilgileriyle)

1. Admin → Personel → "Yeni Personel".
2. Sicil no, ad soyad, geçici şifre ve rolü girin.
3. "Kurtarma Bilgileri (opsiyonel)" bölümünde telefon, e-posta ve gizli
   soru + cevap girin (şifremi unuttum adımında kullanılacak).
4. Kaydet.

**Beklenen:** "Personel eklendi" bildirimi; listede yeni kişi görünür.
Detay sayfasında Telefon: VAR ▪ E-posta: VAR ▪ Gizli Soru: TANIMLI satırı.

### b) Personel telefonunda PWA kurulumu

1. Telefonun tarayıcısından sunucu adresine gidin, personel girişi yapın.
2. Tarayıcı menüsünden **"Ana ekrana ekle"** seçin (iOS Safari: Paylaş →
   Ana Ekrana Ekle; Android Chrome: menü → Ana ekrana ekle).
3. Ana ekrandaki simgeden uygulamayı açın.

**Beklenen:** Uygulama tam ekran, uygulama görünümünde açılır; simge ve
adı ana ekranda görünür.

### c) İlk giriş + zorunlu şifre değişimi

1. Yeni personel sicil no + admin'in verdiği geçici şifre ile giriş yapar.
2. Sistem şifre değiştirme ekranına yönlendirir (atlanamaz).
3. Yeni şifre belirlenir.

**Beklenen:** Şifre değişmeden hiçbir sayfaya geçilemez; değişim sonrası
ana ekran (bakiye) açılır.

### d) QR okutma + sesli anons

> Hatırlatma: Servis saati şu anki saati kapsamalı (Hazırlık bölümü).

1. PWA'da QR kod ekranını açın.
2. Kod kiosk okuyucusuna okutulur.

**Beklenen:** Kioskta onay ekranı, sesli anons (kişi adıyla karşılama),
bakiyeden yemek ücreti düşer. Admin panosunda "Bugün Yiyen" 1 artar.

### e) Mükerrer okutma senaryosu

1. Aynı personel aynı gün QR'ı tekrar okutur.

**Beklenen:** Kiosk "bugün zaten yemek aldı" uyarısı verir; bakiye ikinci
kez düşmez, yemek girişi tekrarlanmaz.

### f) Bakiye yükleme (4242 kartı) + dashboard

1. PWA'da Bakiye Yükle ekranını açın, tutar seçin.
2. Demo kart **4242 4242 4242 4242** ile ödemeyi tamamlayın.

**Beklenen:** "Ödeme başarılı" mesajı, bakiye anında güncellenir. Admin
panosunda "Bugün Yüklenen" tutar artar; İşlemler sayfasında yükleme kaydı.

### g) Red senaryosu (4000 kartı)

1. Aynı ekranda demo kart **4000 0000 0000 0002** ile ödeme deneyin.

**Beklenen:** "Ödeme reddedildi" mesajı; bakiye değişmez, işlem listesine
yükleme kaydı düşmez.

### h) Şifremi unuttum (kod admin panosundan okunur)

1. PWA'dan çıkış yapın → giriş ekranında "Şifremi unuttum".
2. Sicil no girin, kanal olarak **SMS** seçin.
3. Admin panosunu açın: "Bekleyen Doğrulama Kodları" panelinde kişinin
   adı, kanalı ve 6 haneli kod görünür (demo modunda SMS gitmez, kod
   burada gösterilir).
4. Kodu telefonda girin, yeni şifre belirleyin.
5. Yeni şifreyle giriş yapın.

**Beklenen:** Kod doğrulanır, şifre değişir, giriş başarılı olur. Kod
kullanıldıktan sonra panelden düşer.

### i) Saat dışı senaryo

1. Admin → Ayarlar → servis saatini şu anki saati kapsamayacak şekilde
   daraltın (ör. 23:00–23:30).
2. Personel QR'ı kioska okutur.

**Beklenen:** Kiosk "yemekhane kapalı" anonsu/uyarısı verir; bakiye
düşmez, giriş kaydı oluşmaz.

3. Demo sonunda servis saatini eski değerine geri alın.
