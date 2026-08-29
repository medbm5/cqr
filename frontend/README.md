# Citalid Risk Cockpit

The Next.js 14 frontend. It renders what the API computed and calculates no risk
figure of its own — every number on screen came from `risk_engine` through an
endpoint, which is what keeps a figure traceable from the browser back to the
CSV row it started as.

## Local development

```bash
npm install
npm run dev        # http://localhost:3000
```

The API must be running (`make api` from the repository root). Without it, every
page renders an explicit "engine not reachable" state rather than zeros — a zero
AAL is a number someone could act on, and it would be false.

```bash
npm run lint       # eslint, next/core-web-vitals
npm run typecheck  # tsc --noEmit, strict
npm run build
```

## Environment

One variable, and it is required in any deployment:

| Variable | Example | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://citalid-risk-engine-api.onrender.com` | No trailing slash. Defaults to `http://localhost:8000`. |

Copy `.env.example` to `.env.local` for local overrides.

> **`NEXT_PUBLIC_*` is inlined at build time, not read at runtime.** Setting it
> after a deploy has no effect until the next build. On Vercel, set it *before*
> the first deploy, and redeploy after any change — a Vercel "Redeploy" with
> "use existing build cache" unchecked is enough.

## Deploying to Vercel

1. **Import the repository** and set the **Root Directory** to `frontend`. Vercel
   detects Next.js and needs no build-command override.
2. **Add `NEXT_PUBLIC_API_URL`** in Project → Settings → Environment Variables,
   pointing at the deployed API. Set it for Production, Preview and Development.
3. **Deploy.** Then add the resulting Vercel URL to the API's
   `CORS_ALLOWED_ORIGINS`, or the browser will block every request from it.

Steps 2 and 3 are a chicken-and-egg pair: the frontend needs the API's URL and
the API needs the frontend's origin. Deploy the API first, point the frontend at
it, then feed the frontend's URL back.

## Routes

| Route | What it shows | Rendering |
|---|---|---|
| `/` | Company profile and the four headline figures | dynamic |
| `/telemetry` | Ingestion funnel, weekly volume, severity mix, normalization report | dynamic |
| `/frequency` | λ per attack type, asset × week heatmap, live convention controls | dynamic |
| `/severity` | Per-type fitted distributions, QQ plots, the peer-weighting rules | dynamic |
| `/simulation` | AAL, VaR/TVaR, loss distribution, exceedance curves, sensitivity | dynamic |

Every route is `force-dynamic`. These figures come from a live engine; statically
prerendering them would ship whatever the API happened to say at build time — or,
if it was not running, a permanently cached error page.

## Notes

- Charts are recharts; the palette is validated for colour-vision deficiency
  (see `components/charts/tokens.ts`, which records what failed and why).
- Every chart carries a table view, so no value is reachable only by hovering.
- The design is dark-only by choice, not by omission.
