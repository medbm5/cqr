#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError(
            "Couldn't import Django. Install the api extra with "
            '`pip install -e "backend[dev,api]"` and make sure your virtualenv '
            "is active."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
