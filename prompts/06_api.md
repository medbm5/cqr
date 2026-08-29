# 06 — DRF API

**Commit:** `feat(api): DRF endpoints exposing the risk pipeline`

## Prompt given

> Wrap risk_engine in backend/api (thin views, per CLAUDE.md):
> - GET /api/assets/ — inventory + per-asset episode counts.
> - GET /api/telemetry/summary/ — NormalizationReport, weekly event buckets per
>   feed and merged, severity mix.
> - GET /api/frequency/ — FrequencyEstimate + explanation, params echoed. Accepts
>   ?severity_threshold=&session_window_hours=.
> - GET /api/severity/ — per-type params, diagnostics, histogram + fitted-curve
>   plot data.
> - POST /api/simulate/ — {n_years, seed, severity_threshold,
>   session_window_hours} → metrics, OEP/AEP (≤500 points), sensitivity grid,
>   explanation chain.
> Module-level caching of normalized data (static dataset). Serializers
> everywhere, OpenAPI via drf-spectacular, CORS from env, endpoint tests.

## Views stayed thin

Body lengths, excluding docstrings and blank lines — CLAUDE.md's limit is ~30:

```
health 2 · assets 5 · telemetry_summary 7 · frequency 5 · severity 2 · simulate 15
```

Nothing in `api/` computes a risk figure. Three aggregations the endpoints needed
were added to the **engine**, not the API layer, because each is still a statement
about the data and belongs where a notebook can reach it:

| Added to | What | Why not in `api/` |
|---|---|---|
| `ingestion/summary.py` | weekly event buckets, severity and technique mix | a weekly count is an assertion about the telemetry; behind HTTP it would be untestable without a server |
| `severity/fitting.py` | `DistributionPlot` — weighted histogram + fitted density, on the log scale | the chart is how a reader judges the fit by eye; it belongs next to the KS statistic that judges it by number |
| `simulation/engine.py` | `SimulationResult.curve(kind, points)` | re-reads a curve at any resolution from the stored per-year series, a quantile call rather than another simulation |

## Decisions taken (flagged for validation)

1. **`SimulationResult` now stores `annual_maxima` as well as `annual_losses`.**
   800 KB for a 100,000-year run, and it makes the OEP curve re-derivable at any
   resolution instead of frozen at the sixteen round probabilities the CLI uses.
2. **Curve points are log-spaced, not linear.** An exceedance curve carries its
   information in the tail; linear spacing would put nearly every point between a
   1-in-2 and a 1-in-3 year. Capped at 500 as specified, defaulting to 200.
3. **The API caps simulations at 200,000 years and defaults to 25,000.** A full
   100,000-year run takes about 30 seconds, which is not a request. `lru_cache`
   makes a repeat instant, and the cap stops one caller occupying a worker.
4. **The sensitivity grid is opt-out, not mandatory** (`include_sensitivity`,
   default true, with its own year count). It costs nine more runs, and a caller
   refreshing only the headline metrics should not pay for it.
5. **`RISK_ENGINE_DATA_DIR` is a setting read from the environment**, defaulting
   to `<repo>/data`, so a deployment can mount the dataset elsewhere.
6. **Query parameters are validated in a helper shared by two views**, returning
   400 with a message naming the allowed values. The `simulate` body is validated
   by a serializer, so its bounds appear in the OpenAPI schema.

## Two things this feature changed elsewhere

**`test_package_boundaries.py` was rewritten to use a subprocess.** It used to
delete `django` from `sys.modules` in-process, which was harmless until
pytest-django arrived and started holding a configured app registry. A fresh
interpreter is both safer and a stronger claim: it proves `risk_engine` imports on
its own rather than merely tolerating Django's absence. A second test now runs
`python -m risk_engine --help` with `DJANGO_SETTINGS_MODULE` stripped from the
environment, which is the property that actually matters.

**A latent bug in `log_spaced_probabilities`.** Raising 10 to a rounded logarithm
landed the finest probability a hair below `1 / n_years`, so `exceedance_curve`
dropped it as unresolvable and a 200-point request silently returned 199. The
endpoints are now pinned exactly. Only a test asserting the exact length caught
it.

## Verified live

All six endpoints served by `manage.py runserver`, with the dataset cache absorbing
the one-time ~3s load:

```
GET  /api/health/            200
GET  /api/assets/            200    GET /api/frequency/  200
GET  /api/telemetry/summary/ 200    GET /api/severity/   200
POST /api/simulate/          200    150-point AEP and OEP curves, 22 explanation lines
GET  /api/frequency/?severity_threshold=nope   400
```

241 tests, 99% coverage. The figures the API returns are asserted against the
engine's own output rather than hardcoded, so a deliberate model change breaks the
engine tests that argue for it — not the endpoint tests.

## Unchanged and still flagged

The AAL the API serves is the same €12.5bn flagged in `prompts/05_simulation.md`,
for the same reason. Exposing it over HTTP does not make it more defensible, and
the sensitivity grid ships in the same response precisely so a consumer cannot
read the headline without the spread.
