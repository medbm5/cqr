# CLAUDE.md — Citalid Risk Engine

Project context and rules for every Claude Code session in this repo. Read fully before writing code.

## What this project is

Technical case study for Citalid (cyber risk quantification). Goal: estimate the **annualized cyber loss** of a target company (ETI, Retail/e-commerce, 1,200 employees, security maturity 55/100, ~20 assets) from its SIEM/EDR telemetry and an external incident base — and make every number **traceable and explainable**. Explainability is Citalid's core value: any metric shown anywhere must be reconstructable from its inputs.

Deliverable graded hardest: the pure Python package `risk_engine`. Django and Next.js are presentation layers on top.

## Architecture — hard rules

```
backend/
  risk_engine/        # PURE Python package. NEVER imports Django. Runs standalone (CLI/notebook).
    ingestion/        # loaders, normalization, cross-feed dedup
    frequency/        # annualized attack frequency (episodes, not alerts)
    severity/         # loss distribution fitted on peer incidents
    simulation/       # Monte Carlo aggregation, AAL/VaR/TVaR, OEP/AEP
    explain/          # audit trail helpers
  api/                # Django 5 + DRF. Thin views only — zero business logic here.
  tests/
frontend/             # Next.js 14 app router, TypeScript, Tailwind, framer-motion, recharts
notebooks/01_eda.ipynb
data/                 # 4 CSVs — read-only, never modify or commit derived files here
prompts/              # one .md per feature (AI-usage annex required by the case instructions)
```

- `risk_engine` → no Django, no HTTP, no globals holding state. Pure functions + small typed result objects.
- `api/` views: parse request → call risk_engine → serialize. If a view exceeds ~30 lines, logic is leaking.
- `frontend/` never computes risk math; it renders API responses. Only Tailwind + framer-motion + recharts (no component libraries).

## Data facts (verified — trust these, don't rediscover)

- Telemetry window: **2025-11-01 → 2026-05-31 (~212 days)**. Compute the window from data, never hardcode 212; annualization = 365 / observed_days.
- `feed_siem.csv`: 26,490 events, severity ∈ {Low, Medium, High, Critical}. `feed_edr.csv`: 19,350 events, `risk` numeric 0–999.
- **~12,343 events exist in BOTH feeds** (same asset + MITRE technique + timestamp). Merging without dedup doubles frequency — dedup is mandatory.
- `cyber_incidents.csv` (1,600 rows): `sector` contains mojibake duplicates (`Ã‰nergie`→`Énergie`, `SantÃ©`→`Santé`); `financial_loss_eur` contains **-1 sentinels = missing**, never treat as €0.
- Losses are heavy-tailed: median ≈ €39k, mean ≈ €609k, max ≈ €31.6M → lognormal on logs is the default fit; challenge the tail with QQ/KS before accepting.
- Attack types in incident base: phishing, ransomware, credential_theft, data_breach, misconfiguration, ddos, insider_error, supply_chain.

## Modeling conventions (do not silently change)

- Severity normalization: SIEM Low/Medium/High/Critical → 0.25/0.5/0.75/1.0; EDR 0–999 mapped to the same classes via cut points derived in the EDA notebook (named constants + comment referencing the notebook).
- Duplicate SIEM/EDR event → keep **max** severity (worst observed signal), `sources=["siem","edr"]`.
- Frequency counts **episodes**, not alerts: attack-grade events (high/critical, threshold parameterized) clustered per asset with gap ≤ session window (default 24h, parameterized).
- Peer group for severity: **soft weighting**, not hard filtering (sector, size, maturity kernel) — report effective sample size; per-attack-type fit falls back to pooled when effective n < 30.
- Simulation: Poisson(λ per attack_type) × lognormal draws, vectorized numpy, explicit seed everywhere. TVaR ≥ VaR must hold.
- Every model object exposes `to_explanation()` returning a human-readable numbered trace of inputs → outputs.

## Code standards

- Python 3.12, type hints everywhere, mypy strict on `risk_engine`, ruff clean, PEP8.
- Docstrings on every public function: what, why (the modeling justification), args, returns.
- Tests: pytest, small fixture CSVs under `backend/tests/fixtures/` (never the real data), cover edge cases named in the feature prompt. Every feature ships with its tests in the same commit.
- Reproducibility: any randomness takes an explicit `seed`/`rng` argument.
- No premature abstraction. No dead code. No TODOs left in committed code.
- Frontend: typed API client in `lib/api.ts` (env `NEXT_PUBLIC_API_URL`), server components where possible, framer-motion transitions ~200ms, dark "risk cockpit" aesthetic (deep navy, one accent color, Inter/Geist).

## Workflow

- After coding: run `make lint test`; everything green before finishing.
- Conventional commits (`feat(scope): ...`, `chore:`, `docs:`). One commit per feature — the human writes/approves the message.
- If a decision isn't covered here or in the prompt, choose the simplest defensible option and flag it clearly in your summary so the human can validate — this is interview material.

## Commands

`make install` · `make lint` · `make test` · `make api` (Django :8000) · `make web` (Next :3000) · `make run` (CLI pipeline → results.json) · `make eda` (jupyter) · `make archive` (zip deliverable) — see Makefile.