# Citalid Risk Engine — developer entry points.
# Every target is runnable from the repo root.

PY      ?= python
NPM     ?= npm
BACKEND := backend
FRONT   := frontend
ARCHIVE := dist-archive/citalid-risk-engine.zip

export DJANGO_SETTINGS_MODULE ?= api.settings.dev

.DEFAULT_GOAL := help
.PHONY: help install lint test api web run eda archive docker-build docker-up

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (editable, dev+api+prod extras) and frontend dependencies
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "$(BACKEND)[dev,api,prod]"
	$(PY) -m pre_commit install
	$(NPM) --prefix $(FRONT) install

lint: ## ruff (lint + format check) + mypy strict on risk_engine + next lint
	$(PY) -m ruff check $(BACKEND)
	$(PY) -m ruff format --check $(BACKEND)
	$(PY) -m mypy --config-file $(BACKEND)/pyproject.toml $(BACKEND)/risk_engine
	$(NPM) --prefix $(FRONT) run lint

test: ## Run the pytest suite with coverage on risk_engine
	$(PY) -m pytest $(BACKEND)

api: ## Run the Django API on :8000
	$(PY) $(BACKEND)/manage.py runserver 0.0.0.0:8000

web: ## Run the Next.js frontend on :3000
	$(NPM) --prefix $(FRONT) run dev

run: ## Run the standalone risk_engine pipeline -> results.json
	$(PY) -m risk_engine --data-dir data --out results.json

eda: ## Open the exploratory analysis notebook
	$(PY) -m jupyter lab notebooks/01_eda.ipynb

archive: ## Zip the tracked deliverable into dist-archive/
	@mkdir -p dist-archive
	git archive --format=zip --output=$(ARCHIVE) HEAD
	@echo "Archive written to $(ARCHIVE)"

docker-build: ## Build the api + web images
	docker compose -f docker/docker-compose.yml build

docker-up: ## Start the api (:8000) and web (:3000) containers
	docker compose -f docker/docker-compose.yml up
