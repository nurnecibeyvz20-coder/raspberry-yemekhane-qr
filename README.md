# Yemekhane QR Giriş Sistemi

Raspberry Pi üzerinde çalışan, QR kod ile yemekhane giriş (check-in) sistemi.
Personel telefonundan `/qr` sayfasındaki QR kodu gösterir, yemekhanedeki
USB QR okuyucu kioska okutur, bakiyeden düşülür.

## Gereksinimler

- Raspberry Pi 4 veya 5
- Raspberry Pi OS (masaüstü sürümü — kiosk ekranı için gerekli)
- USB HID (klavye modu) QR kod okuyucu
- Kiosk için bağlı bir ekran
- Yerel ağ bağlantısı (personel telefonları aynı ağdan erişir)

## Kurulum

1. Depoyu Pi'ye klonlayın:

   ```bash
   git clone <repo-url> /home/pi/yemekhane
   cd /home/pi/yemekhane
   ```

2. Ortam dosyasını oluşturup düzenleyin:

   ```bash
   cp .env.example .env
   nano .env
   ```

   Doldurulması gerekenler:
   - `SECRET_KEY`: uzun, rastgele bir değer
   - `POSTGRES_PASSWORD` ve `DATABASE_URL` içindeki aynı şifre
   - `INITIAL_ADMIN_SICIL` / `INITIAL_ADMIN_PASSWORD`: ilk admin hesabı

3. Kurulum scriptini çalıştırın:

   ```bash
   sudo bash deploy/install.sh
   ```

   Script; Docker'ı (yoksa) kurar, uygulamayı başlatır, kiosk servisini
   kurar ve günlük yedekleme cron'unu ekler.

4. Yeniden başlatın:

   ```bash
   sudo reboot
   ```

   Açılışta kiosk ekranı (`http://localhost/kiosk`) otomatik olarak
   tam ekran Chromium'da açılır.

## Erişim Adresleri

Pi'nin yerel IP adresini `hostname -I` ile öğrenin (örn. `192.168.1.50`).

| Sayfa | Adres | Kim kullanır |
|-------|-------|--------------|
| Personel QR | `http://<pi-ip>/qr` | Personel (telefon) |
| Admin paneli | `http://<pi-ip>/admin` | Yönetici |
| Kiosk | `http://localhost/kiosk` | Yemekhane ekranı (otomatik açılır) |

## İlk Admin Girişi

İlk admin hesabı `.env` dosyasındaki `INITIAL_ADMIN_SICIL` ve
`INITIAL_ADMIN_PASSWORD` değerlerinden oluşturulur. **İlk girişten sonra
admin panelinden şifrenizi değiştirmeniz önerilir.**

## Yedekler

Veritabanı her gece 03:00'te otomatik yedeklenir:

- Konum: `/home/pi/backups/yemekhane-YYYY-AA-GG.sql.gz`
- 30 günden eski yedekler otomatik silinir.

Elle yedek almak için:

```bash
bash /home/pi/yemekhane/deploy/backup.sh
```

## Sorun Giderme

- Uygulama loglarını görüntüleme:

  ```bash
  cd /home/pi/yemekhane
  docker compose logs -f app
  ```

- Kiosk ekranı açılmıyorsa:

  ```bash
  systemctl status kiosk
  journalctl -u kiosk -e
  ```

- Uygulamayı yeniden başlatma:

  ```bash
  cd /home/pi/yemekhane
  docker compose restart
  ```

- Sağlık kontrolü: `curl http://localhost/health` — `ok` dönmelidir.
