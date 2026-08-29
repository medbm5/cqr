"""The architectural rule that matters most: risk_engine must not know Django.

If this ever fails, business logic has leaked into the presentation layer (or
vice versa) and the engine is no longer runnable standalone.
"""

import importlib
import pkgutil
import sys

import risk_engine

SUBPACKAGES = ["ingestion", "frequency", "severity", "simulation", "explain"]


def test_every_subpackage_imports():
    for name in SUBPACKAGES:
        assert importlib.import_module(f"risk_engine.{name}") is not None


def test_risk_engine_never_imports_django():
    for module in list(sys.modules):
        if module.startswith("django"):
            del sys.modules[module]

    importlib.reload(risk_engine)
    for module_info in pkgutil.walk_packages(risk_engine.__path__, "risk_engine."):
        importlib.import_module(module_info.name)

    assert not [m for m in sys.modules if m.startswith("django")]
