.PHONY: help venv install db-up db-down db-wipe migrate downgrade reset check load test test-integration run-eval run-api

help:
	@echo "make venv            create .venv"
	@echo "make install         editable install with dev deps"
	@echo "make db-up           start local PostgreSQL (docker) and wait until healthy"
	@echo "make db-down         stop local PostgreSQL (keep data)"
	@echo "make db-wipe         stop local PostgreSQL and delete its volume"
	@echo "make migrate         alembic upgrade head"
	@echo "make downgrade       roll back one migration"
	@echo "make reset           downgrade to base then upgrade head"
	@echo "make check           run the FSIE contract validator"
	@echo "make load            load rules/cases into the database"
	@echo "make test            run offline unit tests"
	@echo "make test-integration run live-DB integration tests (needs db-up+migrate)"
	@echo "make run-eval        run the 3 synthetic evaluation cases against the DB"
	@echo "make run-api         start the FastAPI shell (uvicorn)"

venv:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip

install:
	.venv/bin/python -m pip install -e ".[dev]"

db-up:
	docker compose -f infrastructure/postgres/docker-compose.yml up -d
	@echo "waiting for PostgreSQL to become healthy..."
	@for i in $$(seq 1 30); do \
	  s=$$(docker inspect --format '{{.State.Health.Status}}' fsie_l0_postgres 2>/dev/null); \
	  if [ "$$s" = "healthy" ]; then echo "postgreSQL healthy"; exit 0; fi; \
	  sleep 2; \
	done; echo "postgreSQL did not become healthy in time"; exit 1

db-down:
	docker compose -f infrastructure/postgres/docker-compose.yml down

db-wipe:
	docker compose -f infrastructure/postgres/docker-compose.yml down -v

migrate:
	.venv/bin/alembic upgrade head

downgrade:
	.venv/bin/alembic downgrade -1

reset:
	.venv/bin/alembic downgrade base
	.venv/bin/alembic upgrade head

check:
	.venv/bin/python scripts/validate_fsie_package.py

load:
	.venv/bin/python -m packages.knowledge_loader.cli

test:
	.venv/bin/python -m pytest -m "not integration"

test-integration:
	FSIE_RUN_INTEGRATION=1 .venv/bin/python -m pytest -m integration

run-eval:
	.venv/bin/python -m packages.rule_engine.cli

run-api:
	.venv/bin/uvicorn apps.api.main:app --reload
