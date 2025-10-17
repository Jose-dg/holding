#!/usr/bin/env bash
set -euo pipefail

echo "[lint] Ejecutando ruff + black (check) ..."
docker compose exec backend bash -lc "python -m pip install --user ruff black >/dev/null 2>&1 || true; ruff check workflows; black --check workflows"
