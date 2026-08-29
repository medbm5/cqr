"""Production settings.

Everything environment-specific is read from the environment and fails loudly
when missing, so a misconfigured deployment never silently falls back to a
development secret or an open host list.

Expected variables: SECRET_KEY (required), DEBUG (default 0), ALLOWED_HOSTS and
CORS_ALLOWED_ORIGINS (comma-separated).
"""

import os

from .base import *  # noqa: F403
from .base import MIDDLEWARE


def _env_flag(name: str, default: str = "0") -> bool:
    """Read a boolean environment variable ("1"/"true"/"yes" are true)."""
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str) -> list[str]:
    """Read a comma-separated environment variable into a list of trimmed values."""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def _env_required(name: str) -> str:
    """Read a required environment variable, or refuse to boot."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


DEBUG = _env_flag("DEBUG", "0")
SECRET_KEY = _env_required("SECRET_KEY")
ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS")

# WhiteNoise serves the collected static files (schema UI assets, admin).
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Opt-out only, and only for a local container demo served over plain HTTP.
SECURE_SSL_REDIRECT = _env_flag("SECURE_SSL_REDIRECT", "1")
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
