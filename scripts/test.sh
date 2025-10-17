#!/usr/bin/env bash
set -euo pipefail

echo "[test] Ejecutando pytest ..."
docker compose exec backend bash -lc "python -m pip install --user pytest >/dev/null 2>&1 || true; pytest -q workflows/workflows/tests"
