#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: ./scripts/restore.sh <ruta-archivo-sql.gz>"
  exit 1
fi

FILE="$1"
echo "[restore] Restaurando desde: $FILE"
docker compose exec backend bash -lc "bench --site \$FRAPPE_SITE_NAME --force restore $FILE"
