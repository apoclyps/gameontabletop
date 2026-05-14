.PHONY: help \
	install install-backend install-frontend \
	update update-backend update-frontend \
	dev dev-backend dev-frontend \
	migrate migrate-create migrate-downgrade \
	seed \
	test test-backend test-frontend test-watch \
	lint lint-backend lint-frontend \
	format format-backend format-frontend \
	build \
	up down logs \
	clean

# ── default ──────────────────────────────────────────────────────────────────

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}' | sort

# ── install ───────────────────────────────────────────────────────────────────

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies (incl. dev)
	cd backend && uv sync

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

# ── update ────────────────────────────────────────────────────────────────────

update: update-backend update-frontend ## Update all dependencies and lockfiles

update-backend: ## Upgrade backend packages and regenerate uv.lock
	cd backend && uv lock --upgrade && uv sync

update-frontend: ## Upgrade frontend packages
	cd frontend && npm update

# ── dev servers ───────────────────────────────────────────────────────────────

dev: ## Run backend and frontend dev servers (requires two terminals — use 'make up' for Docker)
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals."

dev-backend: ## Run FastAPI dev server with hot-reload
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## Run Vite dev server
	cd frontend && npm run dev

# ── docker ────────────────────────────────────────────────────────────────────

up: ## Build and start all services via Docker Compose
	docker-compose up --build

down: ## Stop and remove Docker Compose containers
	docker-compose down

logs: ## Tail Docker Compose logs
	docker-compose logs -f

# ── migrations ────────────────────────────────────────────────────────────────

migrate: ## Apply all pending Alembic migrations
	cd backend && uv run alembic upgrade head

migrate-create: ## Create a new migration — usage: make migrate-create name="description"
	cd backend && uv run alembic revision --autogenerate -m "$(name)"

migrate-downgrade: ## Roll back one migration
	cd backend && uv run alembic downgrade -1

# ── seed ──────────────────────────────────────────────────────────────────────

seed: ## Seed the database
	cd backend && uv run python seed.py

# ── test ──────────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd backend && uv run pytest

test-frontend: ## Run frontend unit tests
	cd frontend && npm run test

test-watch: ## Run frontend tests in watch mode
	cd frontend && npm run test:watch

# ── lint ──────────────────────────────────────────────────────────────────────

lint: lint-backend lint-frontend ## Lint all code

lint-backend: ## Lint backend with ruff
	cd backend && uv run ruff check .

lint-frontend: ## Lint frontend with eslint
	cd frontend && npm run lint

# ── format ────────────────────────────────────────────────────────────────────

format: format-backend format-frontend ## Format all code

format-backend: ## Format backend with ruff
	cd backend && uv run ruff format . && uv run ruff check --fix .

format-frontend: ## Format frontend with prettier
	cd frontend && npx prettier --write src/

# ── build ─────────────────────────────────────────────────────────────────────

build: ## Build frontend for production
	cd frontend && npm run build

# ── clean ─────────────────────────────────────────────────────────────────────

clean: ## Remove build artefacts and caches
	cd frontend && rm -rf dist node_modules/.vite
	cd backend && rm -rf .venv __pycache__ .ruff_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
