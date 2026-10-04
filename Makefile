COMPOSE ?= docker compose

.DEFAULT_GOAL := help

.PHONY: help env up up-d down reset test coverage logs psql metrics

help:
	@printf '%s\n' \
		'make env       Create .env from .env.example if it does not exist' \
		'make up        Build images and run the stack in the foreground' \
		'make up-d      Same as up, detached' \
		'make down      Stop containers (keep the Postgres volume)' \
		'make reset     Stop containers and delete the Postgres volume' \
		'make test      Backend pytest with coverage (Docker, no live GitHub)' \
		'make coverage  Pytest with an HTML coverage report inside the container' \
		'make logs      Follow backend logs (structlog JSON + Uvicorn)' \
		'make metrics   Print Prometheus text from http://localhost:8080/metrics' \
		'make psql      Open psql in the database container'

env:
	@test -f .env || cp .env.example .env

up: env
	$(COMPOSE) up --build

up-d: env
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v

test:
	$(COMPOSE) run --rm --no-deps --build backend pytest

coverage:
	$(COMPOSE) run --rm --no-deps --build backend pytest --cov-report=html

logs:
	$(COMPOSE) logs -f backend

metrics:
	curl -sS http://localhost:8080/metrics

psql:
	$(COMPOSE) exec db psql -U circunomics -d circunomics
