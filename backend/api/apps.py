"""Django app configuration for the presentation API."""

from __future__ import annotations

import os
import threading

from django.apps import AppConfig


def _enabled(name: str) -> bool:
    """Read a boolean environment flag."""
    return os.environ.get(name, "0").strip().lower() in {"1", "true", "yes", "on"}


class ApiConfig(AppConfig):
    """Wires the cache warm-up, when the environment asks for it."""

    name = "api"
    verbose_name = "Citalid Risk Engine API"

    def ready(self) -> None:
        """Optionally pre-compute the default simulation in the background.

        Off by default and gated on `RISK_ENGINE_WARM_START`, because `ready()`
        also runs for `migrate`, `collectstatic` and every test process - none of
        which should spend ten seconds fitting a model they will not use. The
        deployed service sets the flag; the build does not.

        The work happens on a daemon thread so the port binds immediately and
        the health check answers while the dataset is still loading. A cold
        request that arrives first blocks on the same lock and gets the same
        cached answer rather than computing a second copy.
        """
        if not _enabled("RISK_ENGINE_WARM_START"):
            return

        from . import pipeline

        threading.Thread(
            target=pipeline.warm_start, name="risk-engine-warm-start", daemon=True
        ).start()
