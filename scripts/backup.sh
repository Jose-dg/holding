#!/usr/bin/env bash
set -euo pipefail

echo "[backup] Este comando crea un backup lógico de Frappe/ERPNext."
echo "[backup] Asegúrate de tener espacio en disco y retención."
docker compose exec backend bash -lc "bench --site \$FRAPPE_SITE_NAME backup"
