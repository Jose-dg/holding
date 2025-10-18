# Makefile
SHELL := /bin/bash
-include .env

IMAGE ?= $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: init up down logs restart setup migrate build shell backup restore lint test push-image

init:
	cp -n .env.example .env || true
	echo "Edita .env y luego ejecuta 'make build && make up && make setup'"

build:
	docker build -t $(IMAGE) .

up:
	docker compose up -d --remove-orphans

down:
	docker compose down --volumes

logs:
	docker compose logs -f --tail=200

restart:
	docker compose restart backend queue-short queue-long

setup:
	docker compose run --rm setup

migrate:
	docker compose exec backend bash -lc "bench --site $$FRAPPE_SITE_NAME migrate"

shell:
	docker compose exec backend bash

backup:
	./scripts/backup.sh

restore:
	./scripts/restore.sh

lint:
	./scripts/lint.sh

test:
	./scripts/test.sh

push-image:
	docker push $(IMAGE)
