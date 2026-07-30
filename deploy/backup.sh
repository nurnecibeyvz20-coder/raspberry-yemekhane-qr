#!/bin/bash
set -eo pipefail
BACKUP_DIR=/home/pi/backups
mkdir -p "$BACKUP_DIR"
cd /home/pi/yemekhane
docker compose exec -T db pg_dump -U yemekhane yemekhane \
  | gzip > "$BACKUP_DIR/yemekhane-$(date +%F).sql.gz"
find "$BACKUP_DIR" -name "yemekhane-*.sql.gz" -mtime +30 -delete
