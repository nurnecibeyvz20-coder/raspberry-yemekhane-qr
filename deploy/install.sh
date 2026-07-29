#!/bin/bash
set -e
# 1. Docker kur (yoksa)
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker pi
fi
# 2. unclutter + curl kur
apt-get update && apt-get install -y unclutter curl
# 3. .env kontrolü
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  cp .env.example .env
  echo ">>> .env olusturuldu. SECRET_KEY ve sifreleri duzenleyin,"
  echo ">>> sonra scripti tekrar calistirin."
  exit 1
fi
# 4. Stack'i başlat
docker compose up --build -d
# 5. Chromium binary adını bul, service'i kur
CHROMIUM=$(command -v chromium-browser || command -v chromium)
sed "s|/usr/bin/chromium-browser|$CHROMIUM|" deploy/kiosk.service \
  > /etc/systemd/system/kiosk.service
systemctl daemon-reload
systemctl enable kiosk.service
# 6. Yedekleme cron'u
chmod +x deploy/backup.sh
CRON_LINE="0 3 * * * $(pwd)/deploy/backup.sh"
(crontab -l -u pi 2>/dev/null | grep -vF backup.sh; echo "$CRON_LINE") \
  | crontab -u pi -
echo "Kurulum tamam. Yeniden baslatin: sudo reboot"
