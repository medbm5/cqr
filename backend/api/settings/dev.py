"""Local development settings: insecure defaults, runnable with zero env vars."""

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK

DEBUG = True

# Never used outside a developer machine; prod refuses to start without a real one.
SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# The Next.js dev server.
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

# Browsable API is convenient while wiring the frontend.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
