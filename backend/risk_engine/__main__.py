"""Entry point for ``python -m risk_engine``.

Guarded so the module can be imported without running the pipeline: importing
every module is how `tests/test_package_boundaries.py` proves the engine never
pulls Django in, and an unguarded call would execute a full run on import.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
