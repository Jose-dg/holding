Playbook “fix-now” para ERPNext + app custom
0) Requisitos

Docker + Compose V2 instalados.

Carpeta holding/ con tu proyecto (como lo venimos armando).

Archivo .env basado en .env.example (déjalo con los valores por defecto para local).

1) Dockerfile (DEBE ser este)

Asegúrate de que tu holding/Dockerfile es idéntico a este (clave: instala en el venv de Bench y copia el código a apps/workflows):

# ---- Stage 1: Builder (ruedas) ----
FROM python:3.11-slim AS builder
WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1

COPY workflows/pyproject.toml workflows/requirements.txt ./
RUN python -m pip install --upgrade pip && \
    pip wheel --wheel-dir=/wheels -r requirements.txt

COPY workflows /app/workflows
RUN pip wheel --wheel-dir=/wheels /app/workflows

# ---- Stage 2: Final (ERPNext + app) ----
FROM frappe/erpnext:v15.82.1

USER root
WORKDIR /home/frappe/frappe-bench

# Copia ruedas y código de la app al árbol de Bench
COPY --from=builder /wheels /tmp/wheels
COPY --from=builder /app/workflows /home/frappe/frappe-bench/apps/workflows

# Instala en el virtualenv de Bench (NO en Python global)
RUN /home/frappe/frappe-bench/env/bin/pip install --no-index --find-links=/tmp/wheels workflows && \
    /home/frappe/frappe-bench/env/bin/pip install -e /home/frappe/frappe-bench/apps/workflows && \
    rm -rf /tmp/wheels

# Permisos y usuario no-root
RUN chown -R frappe:frappe /home/frappe
USER frappe
ENV PATH="/home/frappe/.local/bin:${PATH}"

Esto evita el “No module named 'workflows'”. Si tu Dockerfile difiere, cámbialo.

2) Servicio setup idempotente

En holding/docker-compose.yml reemplaza solo el servicio setup por este bloque:

  setup:
    image: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
    user: "1000:1000"
    environment:
      FRAPPE_SITE_NAME: ${SITE_NAME}
      DB_HOST: ${DB_HOST}
      DB_PORT: ${DB_PORT}
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      REDIS_CACHE: ${REDIS_CACHE}
      REDIS_QUEUE: ${REDIS_QUEUE}
      SOCKETIO_PORT: ${SOCKETIO_PORT}
    depends_on:
      - db
      - redis-cache
      - redis-queue
    entrypoint: ["bash","-lc"]
    command: >
      "
      set -euxo pipefail
      cd /home/frappe/frappe-bench;

      bench set-config -g db_host ${DB_HOST};
      bench set-config -g redis_cache redis://${REDIS_CACHE};
      bench set-config -g redis_queue redis://${REDIS_QUEUE};
      bench set-config -g socketio_port ${SOCKETIO_PORT};

      if [ ! -f sites/${FRAPPE_SITE_NAME}/site_config.json ]; then
        bench new-site ${FRAPPE_SITE_NAME} \
          --admin-password ${ADMIN_PASSWORD} \
          --db-root-password ${MARIADB_ROOT_PASSWORD} \
          --mariadb-user-host-login-scope='%';
        bench --site ${FRAPPE_SITE_NAME} install-app erpnext;
      fi

      bench --site ${FRAPPE_SITE_NAME} list-apps | grep -q '^workflows$' \
        || bench --site ${FRAPPE_SITE_NAME} install-app workflows;

      bench --site ${FRAPPE_SITE_NAME} migrate;
      bench build --no-minify;
      bench clear-cache;
      echo 'SETUP DONE';
      "
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - logs:/home/frappe/frappe-bench/logs

Usa redis://… (muy importante) y es idempotente: si el sitio o la app ya existen, no falla.

3) Rebuild limpio

Desde holding/:

make build
make down           # limpia todo, incluyendo volúmenes
make up
docker compose logs setup --tail=300

Deberías ver SETUP DONE al final del log de setup.

4) Verificaciones dentro del contenedor

make shell

# 4.1 Python del venv de Bench y paquete visible
python -c "import sys; print(sys.executable)"
# Debe ser: /home/frappe/frappe-bench/env/bin/python

python -c "import workflows; print(workflows.__version__)"
# Debe imprimir la versión 0.1.0 (o la que tengas)

# 4.2 App instalada en el site
bench --site $FRAPPE_SITE_NAME list-apps | grep workflows
# Debe listar 'workflows'

5) Carga de fixtures

Si tu app trae fixtures (por ejemplo alegra_shopify_settings.json), confírmalo:

bench --site $FRAPPE_SITE_NAME migrate
# Revisa que aparezcan los doctypes 'Alegra Settings' y 'Shopify Settings'

bench --site $FRAPPE_SITE_NAME migrate
# Revisa que aparezcan los doctypes 'Alegra Settings' y 'Shopify Settings'

bench --site $FRAPPE_SITE_NAME migrate
# Revisa que aparezcan los doctypes 'Alegra Settings' y 'Shopify Settings'

6) Salud de servicios

Abre http://localhost:8081 (frontend nginx del stack).

Health del backend (desde el host):

curl -s http://localhost:8081/api/method/ping

Debe responder {"message":"pong"} (vía nginx → backend).

Workers:

docker compose ps | egrep "queue-|scheduler"

