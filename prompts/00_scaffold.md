# 00 — Monorepo scaffold

**Commit:** `chore: scaffold monorepo (risk_engine, django api, nextjs, notebooks, tooling)`

## Prompt given

> Scaffold the monorepo exactly as described in CLAUDE.md's architecture section.
> Backend: Python 3.12, pyproject.toml making risk_engine installable, dev deps
> pytest/pytest-cov/ruff/mypy, pre-commit running ruff+mypy. Django 5 project in
> backend/api with DRF, django-cors-headers, drf-spectacular, settings split
> base/dev/prod (prod reads env vars: SECRET_KEY, ALLOWED_HOSTS,
> CORS_ALLOWED_ORIGINS, DEBUG=0), SQLite, gunicorn + whitenoise in prod deps.
> Frontend: Next.js 14 app router, TypeScript, Tailwind, framer-motion, recharts —
> scaffold only, landing page saying "Citalid Risk Engine", typed lib/api.ts stub
> reading NEXT_PUBLIC_API_URL. Add the Makefile from the repo root spec (install,
> lint, test, api, web, run, eda, archive, docker-build, docker-up). Root
> .gitignore, .env.example for both apps. No business logic yet.

## What was produced

- `backend/pyproject.toml` — `risk_engine` installable, extras `dev` / `api` / `prod`;
  ruff (with pydocstyle on the engine), mypy strict scoped to `risk_engine`, pytest
  with coverage.
- `backend/risk_engine/` — package plus the five sub-packages, each documenting the
  stage it owns; `cli.py` as the standalone entry point.
- `backend/api/` — Django project, split settings, one thin health view, OpenAPI schema.
- `backend/tests/` — CLI tests and a boundary test asserting `risk_engine` never
  pulls Django into `sys.modules`.
- `frontend/` — Next 14 app router, Tailwind cockpit palette, `FadeIn` (framer-motion,
  200ms), typed `lib/api.ts`.
- `Makefile`, `.gitignore`, `.pre-commit-config.yaml`, `.env.example` ×2, `docker/`.

## Decisions taken (flagged for validation)

1. **`make run` on an empty engine.** Rather than failing, the CLI writes a run
   manifest to `results.json` (engine version, input dir, seed, per-stage
   `not_implemented`). It keeps the target green and gives every later stage a
   place to publish into. Zero modeling logic.
2. **Docstring linting (`ruff` rule set `D`) is enforced on `risk_engine` only**,
   and switched off for `api/`, `tests/` and `manage.py` — the modeling
   justification is what needs to be written down, Django glue is not.
3. **mypy strict covers `risk_engine` alone.** Type-checking Django without
   `django-stubs` produces noise, not safety.
4. **`recharts` is installed but unused** at this stage — it is a scaffold
   dependency for the cockpit charts, declared now so the lockfile is stable.
5. **SQLite backs Django's own tables only** (admin, sessions). No risk data is
   persisted; the engine reads the CSVs on every run, which keeps results
   reproducible from the raw inputs.
6. **Docker is compose-based** (`docker/`), with `data/` mounted read-only into
   the API container.
