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
{rows}

{count} annexes, {words} words, covering {prompt_lines} lines of verbatim prompt.

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
