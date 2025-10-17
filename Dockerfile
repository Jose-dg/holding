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

# Node.js para compilar assets (bench build lo requiere)
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && npm install -g yarn \
    && npm_prefix="$(npm prefix -g)" \
    && ln -sf "${npm_prefix}/bin/yarn" /usr/local/bin/yarn \
    && ln -sf "${npm_prefix}/bin/yarnpkg" /usr/local/bin/yarnpkg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia ruedas y código de la app
COPY --from=builder /wheels /tmp/wheels
COPY --from=builder /app/workflows /home/frappe/frappe-bench/apps/workflows

# Instalar en el virtualenv de Bench (NO en el Python global)
RUN /home/frappe/frappe-bench/env/bin/pip install --no-index --find-links=/tmp/wheels workflows && \
    /home/frappe/frappe-bench/env/bin/pip install -e /home/frappe/frappe-bench/apps/workflows && \
    rm -rf /tmp/wheels

# Permisos y usuario no-root
RUN chown -R frappe:frappe /home/frappe
USER frappe
ENV PATH="/home/frappe/.local/bin:${PATH}"
