# 10 — Deployment

**Commit:** `feat(deploy): dockerized backend on Render, frontend on Vercel`

## Prompt given

> Make the app deployable:
> - backend/Dockerfile: python:3.12-slim, multi-stage, installs risk_engine +
>   api, collectstatic with whitenoise, gunicorn api.wsgi --workers 2, honors
>   PORT env. Data CSVs baked into the image (small, static).
> - api prod settings already read SECRET_KEY / ALLOWED_HOSTS /
>   CORS_ALLOWED_ORIGINS / DEBUG from env — verify and add a /api/health/
>   endpoint.
> - render.yaml (or fly.toml) defining the web service from the Dockerfile with
>   those env vars.
> - docker-compose.yml for local parity: api on :8000, web on :3000 with
>   NEXT_PUBLIC_API_URL=http://localhost:8000.
> - frontend: vercel-ready (no changes beyond env var docs); add frontend/README
>   section: set NEXT_PUBLIC_API_URL to the Render URL.
> - Simulation endpoint guard for a small instance: cap n_years at 200k, and
>   precompute/cache the default-params simulation at startup so the landing page
>   is instant.
> - README "Deployment" section: step-by-step (Render: new Web Service from repo,
>   env vars, deploy; Vercel: import frontend/ dir, set env var). Include
>   cold-start caveat for free tiers.

## The bug this feature existed to find

The warm-up worked, the log said so, and **the first request still took 21
seconds**. The second took 0.04.

`lru_cache` keys on the *call*, not on the resolved arguments. The warm-up called
`get_simulation(25_000, 42)` and let the two remaining parameters default; the
view called `get_simulation(25_000, 42, SeverityClass.HIGH, 24.0)` explicitly.
Same answer, two cache entries. The warm-up was faithfully pre-computing a key
nothing would ever ask for.

Two further mismatches sat behind it: a default POST also builds the sensitivity
grid, which the warm-up never touched, and the landing page requested
`n_years: 10_000` while the server's default — and so the warmed value — was
25,000.

**The fix was structural rather than a patched call.** The cached functions now
take **no defaults at all**, so every caller must be explicit and two spellings of
one request cannot diverge. The canonical values live in `pipeline` as
`DEFAULT_SEED` / `DEFAULT_THRESHOLD` / `DEFAULT_WINDOW_HOURS` / `DEFAULT_YEARS`,
and the serializers, the query-parameter helper, the warm-up and both frontend
pages all read them from there. The landing page and the simulation page now send
no `n_years` at all, so what they ask for is by construction what the server
warmed.

After the fix, in the container: **0.031s, 0.006s, 0.138s**.

This is the exact class of defect that only appears when the thing is actually
run. Every unit test passed both before and after.

## Decisions taken

1. **Data baked into the image.** Under 3 MB of static CSV. No volume to mount,
   no object store to reach, and the engine's answer is reproducible from the
   image alone.
2. **`collectstatic` runs at build with a throwaway `SECRET_KEY`.** The prod
   settings refuse to import without one — deliberately — so the build supplies a
   labelled fake. It is never the key the service runs with.
3. **Two gunicorn workers.** Each holds its own memoized dataset and fitted
   model, so a third costs another copy of everything for no extra throughput on
   a read-mostly API. Measured at 470 MB resident with both warm.
4. **Warm-up on a background daemon thread**, gated on `RISK_ENGINE_WARM_START`
   and off by default. `AppConfig.ready()` also runs for `migrate`,
   `collectstatic` and every test process, none of which should spend half a
   minute fitting a model. The port binds immediately and `/api/health/` answers
   in ~5s while the model is still loading.
5. **A lock serializes the warm-up against a first request** that arrives during
   it. Without one both compute the same simulation concurrently — correct,
   because `lru_cache` keeps one, but twice the peak memory on an instance chosen
   for being small.
6. **A warm-up failure is logged and swallowed.** It is an optimisation, and a
   service that refuses to start because it could not pre-compute one is worse
   than a service that starts cold.
7. **`SECURE_SSL_REDIRECT=0` on Render.** Render terminates TLS in front of the
   container and forwards plain HTTP; redirecting again inside would loop. The
   proxy header in the prod settings is what keeps Django aware the original
   request was HTTPS.
8. **`docker/` was flattened** to `backend/Dockerfile`, `frontend/Dockerfile` and
   a root `docker-compose.yml` — where each tool looks by default.

## Verified, not assumed

Docker was not running; it was started, and the image built and exercised:

```
image                146 MB, runs as uid 10001 (appuser)
/api/health/         200 after 5s
warm start           complete in both workers at 27s (background thread)
all five endpoints   200
n_years = 200,000    200
n_years = 200,001    400
CORS                 access-control-allow-origin: http://localhost:3000
default simulate     0.031s / 0.006s / 0.138s
memory               470 MB with both workers warm
```

243 backend tests pass; frontend builds; all five routes dynamic.

## Flagged

- **The container runs Python 3.12 while development targets 3.11.**
  `requires-python` is `>=3.11` so both are supported, and the prompt asked for
  `python:3.12-slim`. Worth knowing the two differ; pinning the image to
  `3.11-slim` would make them identical if that is preferred.
- **470 MB resident with two workers** is close to a 512 MB free instance. One
  worker would halve it at the cost of concurrency. `--workers 1` is a one-line
  change in the Dockerfile if the instance turns out to be tight.
- **Nothing is actually deployed.** The image runs locally and the blueprint is
  written, but no Render service or Vercel project exists, so the README still
  says there is no hosted demo.
