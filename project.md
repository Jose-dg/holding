Quiero que generes toda la estructura y archivos de un proyecto Frappe/ERPNext con una app personalizada llamada workflows, siguiendo mejores prácticas de Docker (imagenes inmutables, no-root user, healthchecks, .env, multi-stage builds, CI básico). Objetivo: automatizar ventas y fulfillment de pines digitales con multi-compañía (A central, B/C/D retail), integración con Shopify vía webhook firmado (HMAC), lógica intercompañía (SI/PI atómica), asignación FIFO de seriales y triggers por stock, más base para integración con Alegra.

Requisitos clave del proyecto

ERPNext v15 (imagen oficial frappe/erpnext como base).

App Frappe workflows instalada en el mismo site (no contenedor aparte).

Docker Compose prod-lite con servicios: db (MariaDB 10.6), redis-cache, redis-queue, backend, websocket, frontend (nginx), queue-short, queue-long, scheduler, y un job one-off setup que:

setea common_site_config (db, redis, socketio),

crea el site SITE_NAME,

instala erpnext y workflows,

corre migrate, build, clear-cache.

Dockerfile propio (multi-stage) que extiende frappe/erpnext y empaqueta la app workflows y sus pip deps → evita builds en caliente.

Usuario no root donde aplique, permisos correctos, read-only rootfs en servicios de solo lectura (cuando sea viable).

Healthchecks (DB, backend ping, websocket).

Colas: short y long,default explícitas.

Variables en .env + .env.example (no secretos hardcodeados).

Scripts en scripts/ (bootstrap, backup/restore, lint, test).

Fixtures para Doctypes Alegra Settings y Shopify Settings.

Endpoint público whitelisted workflows.api.shopify.handle_shopify_order con HMAC (X-Shopify-Hmac-Sha256), idempotencia, logging a Integration Log y encolado de fulfillment.

Hooks:

on_submit de Sales Invoice → intercompañía SI (A) + PI (B/C/D) atómicos.

on_update_after_submit de Serial No y Stock Entry → reintentos de pendientes (Awaiting Stock).

Email templates por compañía (B/C/D) para envío de seriales.

Pruebas mínimas (unit/integration stubs) con pytest.

CI: workflow GitHub Actions que lint/testea, construye la imagen y hace push a un registry (placeholder).

Documentación en README.md con comandos de inicio, troubleshooting y checklist.

Estructura deseada (genera archivos completos

holding/
├─ .env.example
├─ docker-compose.yml
├─ Dockerfile
├─ Makefile
├─ README.md
├─ scripts/
│  ├─ bootstrap.sh
│  ├─ backup.sh
│  ├─ restore.sh
│  ├─ lint.sh
│  └─ test.sh
├─ workflows/
│  ├─ pyproject.toml        # o setup.cfg/setup.py
│  ├─ requirements.txt
│  ├─ MANIFEST.in
│  └─ workflows/
│     ├─ __init__.py
│     ├─ hooks.py
│     ├─ api/
│     │  └─ shopify.py
│     ├─ events/
│     │  ├─ intercompany.py
│     │  └─ fulfillment.py
│     ├─ integrations/
│     │  └─ alegra/
│     │     ├─ __init__.py
│     │     └─ client.py
│     ├─ fixtures/
│     │  └─ alegra_shopify_settings.json
│     └─ tests/
│        ├─ conftest.py
│        ├─ test_shopify_webhook.py
│        ├─ test_intercompany.py
│        └─ test_fulfillment.py
└─ .github/workflows/
   └─ ci.yml


Contenidos mínimos y criterios por archivo (sé concreto; no pongas TODOs vacíos)

.env.example
Variables: DB_HOST, DB_PORT, MYSQL_ROOT_PASSWORD, MARIADB_ROOT_PASSWORD, REDIS_CACHE, REDIS_QUEUE, SOCKETIO_PORT, SITE_NAME, ADMIN_PASSWORD, REGISTRY, IMAGE_NAME, IMAGE_TAG. No pongas credenciales reales.

docker-compose.yml

Usa version: "3", restart: unless-stopped, depends_on, volumes para sites, logs, db-data, redis-queue-data.

Healthcheck en DB con mysqladmin ping.

backend, websocket, frontend, queue-short, queue-long, scheduler montan sites/logs.

Servicio setup (one-off) con bench set-config, bench new-site, bench --site $SITE_NAME install-app workflows, bench migrate, bench build, bench clear-cache.

Exponer frontend en 8081:8080.

No uses deploy: (no Swarm).

Dockerfile (multi-stage)

Stage builder para instalar workflows (copiar pyproject.toml/requirements.txt y pip install --no-cache-dir).

Stage final desde frappe/erpnext:v15.82.1, copia de la app a /home/frappe/frappe-bench/apps/workflows.

Ajuste de permisos y usuario adecuado (no root si aplica).

No embedear secretos.

Makefile
Targets: init, up, down, logs, setup, migrate, build, shell, backup, restore, lint, test, push-image.

scripts/

bootstrap.sh: docker compose up -d db redis-cache redis-queue && docker compose run --rm setup && docker compose up -d

backup.sh/restore.sh: wrappers de bench backup y restore (con advertencias).

lint.sh: ruff/flake8/black (elige uno consistente).

test.sh: correr pytest en contenedor.

workflows/pyproject.toml (o setup.cfg/setup.py)

Nombre paquete workflows, metadata básica, deps (requests, etc.).

Config de ruff/black si usas.

workflows/requirements.txt

Lista mínima (e.g., requests>=2.32).

workflows/workflows/hooks.py

fixtures = ["alegra_shopify_settings.json"]

doc_events con:

Sales Invoice.on_submit -> workflows.events.intercompany.on_submit_sales_invoice

Serial No.on_update_after_submit -> workflows.events.fulfillment.try_pending

Stock Entry.on_update_after_submit -> workflows.events.fulfillment.try_pending

(Opcional) website_route_rules para exponer /api/workflows/shopify/order.

workflows/workflows/api/shopify.py

@frappe.whitelist(allow_guest=True, methods=["POST"]) handle_shopify_order()

Verifica HMAC (X-Shopify-Hmac-Sha256) usando secret de Shopify Settings (por company_code del payload).

Idempotencia: Integration Log con request_id calculado (order_id + hash).

Crear Sales Invoice en la compañía del payload.

Encolar workflows.events.fulfillment.process_invoice (cola short).

Responder 200/202 o 4xx en validaciones, 5xx en excepciones.

workflows/workflows/events/intercompany.py

En on_submit_sales_invoice, si doc.company in ("B","C","D"): crea SI en A y PI en B/C/D de forma atómica (savepoint/rollback).

Copia ítems, cantidades, precios, impuestos; valida stock.

Guarda referencias cruzadas (linked_invoice).

workflows/workflows/events/fulfillment.py

process_invoice(invoice: str): asigna seriales FIFO, renderiza y encola email con plantilla de la compañía (B/C/D).

Si no hay stock → marcar Awaiting Stock y crear Sales Order en A.

try_pending(...): al actualizar Serial No/Stock Entry, reintentar pendientes en orden FIFO.

workflows/workflows/integrations/alegra/client.py

Clase AlegraClient(company) que lee credenciales de Alegra Settings y hace peticiones con requests, manejo de errores y timeouts.

workflows/workflows/fixtures/alegra_shopify_settings.json

Dos Doctypes custom: Alegra Settings (company, alegra_user, alegra_token:Password) y Shopify Settings (company, webhook_secret:Password) con permisos a System Manager.

workflows/workflows/tests/

Stubs de pytest que prueben: verificación HMAC, idempotencia (no duplicar), creación de SI desde payload, creación intercompañía, transición a Awaiting Stock.

.github/workflows/ci.yml

Jobs: lint, test, build-image (docker build) y push a ${{ secrets.REGISTRY }} si está en main (usa secrets y no hardcodees nada).

README.md

Requisitos, instalación (make init), arranque (make up), setup (make setup), acceso (http://localhost:8081).

Cómo probar el webhook con curl (cálculo HMAC).

Troubleshooting (ModuleNotFoundError, workers, HMAC inválido).

Checklist de “hecho”.

Estilo y buenas prácticas obligatorias

No inventes secretos, usa variables de entorno.

Comentarios breves y útiles en YAML/bash/Python.

Evita latest; fija tags (ej. frappe/erpnext:v15.82.1).

Comandos deterministas y idempotentes (el setup puede re-ejecutarse sin romper).

No metas dependencias innecesarias; mantiene el Dockerfile limpio y reproducible.

No uses deploy: de Swarm en Compose.

Expón solo el puerto de frontend.

Usa --no-cache-dir en pip.

Añade set -euo pipefail a scripts bash.

Criterios de aceptación (auto-verificables)

docker compose run --rm setup crea el site e instala workflows sin errores.

docker compose up -d levanta todo y http://localhost:8081 responde.

bench --site $SITE_NAME list-apps muestra workflows.

curl al endpoint con HMAC válido devuelve 200/202 y crea Sales Invoice.

Workers procesan colas short y long,default.

Tests pytest corren (aunque sean stubs) y CI los ejecuta.

Genera todos los archivos con contenido listo para usar. Si algo no puede implementarse completamente (p. ej., dominio del registry), pon placeholders bien marcados y explica en comentarios dónde setearlos.