SHELL := /bin/bash
COMPOSE := docker compose

.DEFAULT_GOAL := help
.PHONY: help up down logs build migrate seed gen-api test test-backend test-e2e lint fmt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Build and start the whole stack — frontend :8896, backend :8897
	@[ -f .env ] || cp .env.example .env
	$(COMPOSE) up --build

down: ## Stop the stack and remove volumes
	$(COMPOSE) down -v

logs: ## Tail logs
	$(COMPOSE) logs -f --tail=100

migrate: ## Apply database migrations inside the backend container
	$(COMPOSE) run --rm backend alembic upgrade head

seed: ## Create the demo account + starter document
	$(COMPOSE) run --rm backend python -m scripts.seed

gen-api: ## Regenerate frontend/openapi.json and the typed TS SDK
	cd backend && uv run python -m scripts.export_openapi
	cd frontend && npm run gen:api

test: test-backend ## Run the backend test suite (pytest)

test-backend: ## Run pytest (spins up throwaway Postgres + Redis via testcontainers)
	cd backend && uv run pytest

test-e2e: ## Run Playwright end-to-end tests (stack must be running — `make up`)
	cd frontend && PLAYWRIGHT_BASE_URL=http://localhost:8896 npx playwright test

lint: ## Lint + typecheck both apps
	cd backend && uv run ruff check . && uv run mypy app
	cd frontend && npm run lint && npm run typecheck

fmt: ## Auto-format both apps
	cd backend && uv run ruff check --fix . && uv run ruff format .
	cd frontend && npm run format
