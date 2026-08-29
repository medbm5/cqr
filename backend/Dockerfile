# Build context is the repository root: the image needs `backend/` for the API
# and `data/` for the four CSVs the engine reads.
#
#   docker build -f backend/Dockerfile -t citalid-risk-engine .

# ---------------------------------------------------------------- builder ---
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Dependencies are resolved once, into a virtualenv the runtime stage copies
# whole. Nothing from this stage - compilers, pip's caches, build metadata -
# reaches the final image.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/risk_engine backend/risk_engine
RUN pip install "./backend[api,prod]"

# ---------------------------------------------------------------- runtime ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/backend \
    DJANGO_SETTINGS_MODULE=api.settings.prod \
    PORT=8000

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY backend backend
# The dataset is four static CSVs totalling under 3 MB. Baking them in keeps the
# image self-contained: no volume to mount, no object store to reach, and the
# engine's answer is reproducible from the image alone.
COPY data data

# Collected once at build time so the running container never writes to disk.
# The prod settings refuse to import without a secret, so a throwaway one is
# supplied here; it is never the key the service runs with.
RUN SECRET_KEY=build-time-only-not-a-secret \
    ALLOWED_HOSTS=localhost \
    SECURE_SSL_REDIRECT=0 \
    python backend/manage.py collectstatic --noinput --clear

# Least privilege: nothing in the image needs to be written at runtime.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# `PORT` is what Render, Fly and Cloud Run all inject.
#
# **One worker by default.** Each worker holds its own copy of the loaded
# dataset and fitted severity model - roughly 200 MB - so two of them plus a
# simulation's working arrays do not fit in the 512 MB a free instance gets.
# Two workers OOM-killed the process within seconds of the first request; one
# runs comfortably. Raise `WEB_CONCURRENCY` on an instance with the memory for
# it; no rebuild needed.
#
# The timeout is generous because a 200,000-year simulation is a legitimate
# request that takes half a minute.
CMD ["sh", "-c", "gunicorn api.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-1} --timeout 120 --access-logfile - --error-logfile -"]
