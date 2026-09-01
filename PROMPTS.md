# AI usage annex

The case allows AI tooling on condition that the author can explain what was
delegated and what was written or reworked by hand. This repository was built
with Claude Code, and this annex is the record.

Every feature was specified as a written prompt, and **one annex per feature**
lives in [`prompts/`](prompts/). Each annex holds the prompt **verbatim**, what
was produced, the decisions taken with their justification, and — the part worth
reading — what was flagged back for human validation.

This file is generated from those annexes by `make prompts-index`, so it cannot
drift from them. `make lint` fails if it has.

## What was delegated, and what was not

| Delegated to the model | Retained by hand |
|---|---|
| Writing code against a written specification | Every modeling decision in the table below |
| Deriving the EDA constants from the data | Approving the technique → attack-type mapping before it was used |
| Test cases for the edge conditions each prompt named | The episode key, which changes λ by 5.7× |
| Wiring the API and UI over the engine | Judging which flagged findings were real |

Two decisions were escalated mid-feature and answered by a human *before* the
code was written: the **MITRE technique → attack type mapping** — all 21
techniques, reviewed with their attack-grade event weights — and the **episode
key** for sessionization. Both are recorded in `prompts/03_frequency.md`.

## The annexes

| # | Feature | Commit | Decisions recorded |
|---|---|---|---|
| 0 | [00 — Monorepo scaffold](prompts/00_scaffold.md) | `chore` | 6 |
| 1 | [01 — Exploratory data audit (`notebooks/01_eda.ipynb`)](prompts/01_eda.md) | `feat(eda)` | 8 |
| 2 | [02 — Ingestion & normalization](prompts/02_ingestion.md) | `feat(ingestion)` | 8 |
| 3 | [03 — Frequency model](prompts/03_frequency.md) | `feat(frequency)` | 7 |
| 4 | [04 — Severity model](prompts/04_severity.md) | `feat(severity)` | 6 |
| 5 | [05 — Monte Carlo simulation](prompts/05_simulation.md) | `feat(simulation)` | 6 |
| 6 | [06 — DRF API](prompts/06_api.md) | `feat(api)` | 6 |
| 7 | [07 — Frontend shell](prompts/07_web_shell.md) | `feat(web)` | 9 |
| 8 | [08 — Telemetry and frequency views](prompts/08_web_telemetry_frequency.md) | `feat(web)` | 8 |
| 9 | [09 — Severity and simulation views](prompts/09_web_severity_simulation.md) | `feat(web)` | 8 |
| 10 | [10 — Deployment](prompts/10_deploy.md) | `feat(deploy)` | 8 |
| 11 | [11 — Frequency calibration](prompts/11_calibration.md) | `fix(frequency)` | 5 |
| 12 | [12 — Plain-language hint tooltips](prompts/12_hint_tooltips.md) | `feat(web)` | 5 |
| 13 | [13 — Loss plausibility cap and a readable loss histogram](prompts/13_loss_cap_histogram.md) | `feat(simulation)` | 0 |
| 14 | [14 — Exceedance curves rendering on log axes](prompts/14_exceedance_curves.md) | `fix(web)` | 0 |
| 15 | [15 — Roadmap page](prompts/15_roadmap.md) | `feat(web)` | 0 |

16 annexes, 13,426 words, covering 222 lines of verbatim prompt.

## Findings the model surfaced and a human judged

These are the moments the process earned its keep. Each was found by running the
code against the real data, not by writing it:

| Finding | Annex |
|---|---|
| The EDR `risk` field is 0–100 with six `999` sentinels, not the documented 0–999 scale | `01_eda.md` |
| A pooled lognormal is rejected by KS — the base is a mixture of five severity strata | `01_eda.md` |
| Both telemetry feeds carry gaps and exactly duplicated rows | `01_eda.md` |
| λ ≈ 9,168/yr is implausible, and flattens the loss distribution as well as inflating it | `03_frequency.md`, `05_simulation.md` |
| A Pareto tail beats the lognormal on five of eight attack types | `04_severity.md` |
| `supply_chain` and `insider_error` are unobservable from this telemetry | `03_frequency.md` |
| The first chart palette failed CVD validation — the accent collapses against violet | `08_web_telemetry_frequency.md` |
| `__main__.py` ran the whole pipeline on import; the architecture test caught it | `05_simulation.md` |
