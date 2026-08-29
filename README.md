# Citalid Risk Engine

Estimate the **annualized cyber loss** of a target company (ETI, retail/e-commerce,
1,200 employees, security maturity 55/100, ~20 assets) from its SIEM/EDR telemetry
and an external incident base — and make every number traceable back to its inputs.

## Layout

| Path | Role |
| --- | --- |
| `backend/risk_engine/` | Pure Python engine — ingestion, frequency, severity, simulation, explain. Never imports Django. |
| `backend/api/` | Django 5 + DRF presentation layer. Thin views only. |
| `backend/tests/` | pytest suite, fixtures under `tests/fixtures/`. |
| `frontend/` | Next.js 14 (app router) risk cockpit. Renders API responses, computes nothing. |
| `notebooks/01_eda.ipynb` | Where the modeling constants are derived and justified. |
| `data/` | The four input CSVs. Read-only. |
| `prompts/` | One `.md` per feature — the AI-usage annex required by the case. |

## Getting started

```bash
make install     # editable backend install + pre-commit hooks + npm install
make lint        # ruff, mypy (strict, risk_engine only), next lint
make test        # pytest with coverage on risk_engine
```

Then, in two terminals:

```bash
make api         # Django on :8000  (schema at /api/schema/, docs at /api/docs/)
make web         # Next.js on :3000
```

The engine runs without any server:

```bash
make run         # python -m risk_engine.cli --data data --out results.json
make eda         # open the exploratory notebook
```

Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` →
`frontend/.env.local` before running against anything but the dev defaults.

Requires Python 3.11+ and Node 20+.
