# Ayrı Personel ve Yönetici Girişi Tasarımı

## Amaç

Personel listesinde yönetici hesaplarının görünmesini önlemek ve personel ile
yönetici için ayrı giriş ekranları sunmak.

## Rotalar

- `GET /login` ve `POST /login` yalnızca `role="personel"` hesaplarını kabul
  eder ve başarılı girişte `/qr` sayfasına yönlendirir.
- `GET /admin/login` ve `POST /admin/login` yalnızca `role="admin"`
  hesaplarını kabul eder ve başarılı girişte `/admin` sayfasına yönlendirir.
- Yanlış roldeki kimlik bilgileri, kullanıcı hesabının türünü açıklamayan
  genel `Hatalı sicil no veya şifre` mesajıyla reddedilir.
- Personel giriş ekranı yönetici girişine, yönetici giriş ekranı personel
  girişine bağlantı verir.

## Personel Listesi

- `/admin/personel` sorgusu `User.role == "personel"` ile sınırlanır.
- Arama, sıralama ve sayfalama bu filtre üzerinde çalışır.
- Dashboard bekleyen başvurular sorgusu da yalnızca personel başvurularını
  içerir.

## Testler

- Personel hesabı yönetici girişinden, yönetici hesabı personel girişinden
  reddedilir.
- Her rol kendi giriş ekranından doğru hedefe yönlenir.
- Personel listesi ve araması yönetici hesabını içermez.
