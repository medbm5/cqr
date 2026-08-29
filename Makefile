# Citalid Risk Engine — developer entry points.
# Every target is runnable from the repo root.

PY      ?= python
NPM     ?= npm
BACKEND := backend
FRONT   := frontend
ARCHIVE := dist-archive/citalid-risk-engine.zip

export DJANGO_SETTINGS_MODULE ?= api.settings.dev

.DEFAULT_GOAL := help
.PHONY: help install lint test api web run eda archive prompts-index docker-build docker-up

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (editable, dev+api+prod extras) and frontend dependencies
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "$(BACKEND)[dev,api,prod]"
	$(PY) -m pre_commit install
	$(NPM) --prefix $(FRONT) install

lint: ## ruff (lint + format check) + mypy strict on risk_engine + next lint
	$(PY) -m ruff check $(BACKEND) scripts
	$(PY) -m ruff format --check $(BACKEND) scripts
	$(PY) -m mypy --config-file $(BACKEND)/pyproject.toml $(BACKEND)/risk_engine
	$(NPM) --prefix $(FRONT) run lint
	$(PY) scripts/build_prompts_index.py --check

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

prompts-index: ## Regenerate PROMPTS.md from the per-feature annexes
	$(PY) scripts/build_prompts_index.py

archive: ## Zip the deliverable into dist-archive/ (tracked files only)
	@mkdir -p dist-archive
	@$(PY) scripts/build_prompts_index.py --check
	@git diff --quiet HEAD || (echo "refusing to archive: uncommitted changes" && exit 1)
	@rm -f $(ARCHIVE)
	git archive --format=zip --prefix=citalid-risk-engine/ --output=$(ARCHIVE) HEAD
	@$(PY) scripts/verify_archive.py $(ARCHIVE)

docker-build: ## Build the api + web images
	docker compose build

docker-up: ## Start the api (:8000) and web (:3000) containers
	docker compose up
