#!/usr/bin/env bash
set -euo pipefail

echo "[bootstrap] Levantando base (db/redis) ..."
docker compose up -d db redis-cache redis-queue

echo "[bootstrap] Setup de site/app (idempotente) ..."
docker compose run --rm setup

echo "[bootstrap] Levantando servicios ..."
docker compose up -d

echo "[bootstrap] Listo: http://localhost:8081"
