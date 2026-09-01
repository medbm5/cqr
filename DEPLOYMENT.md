# Deployment

The two halves deploy separately: the API as a container, the frontend as a
static-plus-SSR Next.js app. Deploy the API first — the frontend needs its URL
at build time.

## 1. The API on Render

`render.yaml` defines the service, so a blueprint deploy picks it up. Or by hand:

1. **New → Web Service**, connect the repository.
2. **Runtime: Docker.** Dockerfile path `./backend/Dockerfile`, Docker context
   `.` — the image needs `data/` as well as `backend/`, so the context is the
   repository root.
3. **Health check path** `/api/health/`.
4. **Environment variables:**

   | Key | Value |
   |---|---|
   | `DJANGO_SETTINGS_MODULE` | `api.settings.prod` |
   | `SECRET_KEY` | generate one — the settings refuse to boot without it |
   | `DEBUG` | `0` |
   | `ALLOWED_HOSTS` | the service hostname, e.g. `citalid-risk-engine-api.onrender.com` |
   | `CORS_ALLOWED_ORIGINS` | the Vercel URL, scheme included |
   | `SECURE_SSL_REDIRECT` | `0` — Render terminates TLS in front of the container |
   | `RISK_ENGINE_WARM_START` | `1` |

5. **Deploy.** First build is a few minutes; the dataset is baked into the image,
   so there is no volume to attach and no storage to configure.

`ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` are marked `sync: false` in the
blueprint because neither is known until both services exist.

## 2. The frontend on Vercel

1. **Import the repository**, set **Root Directory** to `frontend`.
2. Set **`NEXT_PUBLIC_API_URL`** to the Render URL, for all environments.
3. **Deploy**, then add the resulting Vercel URL to the API's
   `CORS_ALLOWED_ORIGINS` and redeploy the API.

`NEXT_PUBLIC_*` is **inlined at build time**, so changing it later requires a
rebuild, not just a restart. See [`frontend/README.md`](frontend/README.md).

## Cold starts on free tiers

Render's free tier **stops the container after ~15 minutes idle**, and the next
request pays the full spin-up. On top of that, this service loads four CSVs,
deduplicates 45,840 rows and fits nine severity distributions before it can
answer anything.

Two things reduce the damage, and neither eliminates it:

- `RISK_ENGINE_WARM_START=1` runs that work on a **background thread at boot**,
  so the port binds and `/api/health/` answers immediately while the model
  loads. The health check passes early; the first *data* request may still wait.
- Every stage is memoized per worker, and the default-parameter simulation is
  cached during the warm-up — so the landing page hits a warm cache, and only a
  request with unusual parameters computes anything.

**Expect the first request after an idle period to take 30–60 seconds.** That is
the free tier, not the engine. A paid instance that never sleeps removes it
entirely; so does any always-on host.

## Memory on a 512 MB instance

The image runs **one gunicorn worker** by default. Each worker holds its own copy
of the loaded dataset and fitted model — around 200 MB — so two of them plus a
simulation's working arrays do not fit in the 512 MB a free instance gets. Two
workers OOM-kill the process within seconds of the first `POST /api/simulate/`.

Raise `WEB_CONCURRENCY` on an instance with the memory for it; no rebuild needed.
Measured on a 512 MB container: 138 MB idle, 152 MB after a 200,000-year run.

## CPU, and why the API's defaults are smaller than the CLI's

A free instance runs at roughly **4.2 ms per simulated year** — about fourteen
times slower than a workstation. The API therefore defaults to a **5,000-year**
simulation and a **9 × 1,000-year** sensitivity grid, which the background
warm-up absorbs in about a minute. The earlier defaults — 25,000 years plus a
9 × 10,000 grid — needed some eight minutes of CPU and never survived the
gateway timeout, so every uncached request returned 502.

Three environment variables tune this without a rebuild:

| Variable | Default | What it does |
|---|---|---|
| `RISK_ENGINE_DEFAULT_YEARS` | `5000` | Years the API simulates when the caller does not say |
| `RISK_ENGINE_SENSITIVITY_YEARS` | `1000` | Years per cell of the 3×3 grid |
| `RISK_ENGINE_MAX_YEARS` | `200000` | Hard cap on what a caller may request |

The CLI is untouched at 100,000 years — it has a whole machine to itself.

On a free instance, raising `n_years` from the UI still works but is slow: 25,000
years is about two minutes of compute, and anything past that will outlive the
platform's request timeout. Lower `RISK_ENGINE_MAX_YEARS` if you would rather the
API refuse those requests than hang on them.

The cap exists so that one caller cannot occupy a worker indefinitely on an
instance this small.
