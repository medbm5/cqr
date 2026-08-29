"""The architectural rule that matters most: risk_engine must not know Django.

If this ever fails, business logic has leaked into the presentation layer (or
vice versa) and the engine is no longer runnable standalone - from a notebook,
from the CLI, or from a test that has no settings module.

The check runs in a subprocess. Doing it in-process would mean deleting `django`
from `sys.modules` while pytest-django holds a configured app registry, which
breaks every test that runs afterwards. A fresh interpreter is both a cleaner
assertion and a more faithful one: it proves the engine imports on its own, not
merely that it tolerates Django already being gone.
"""

import os
import subprocess
import sys

import risk_engine

SUBPACKAGES = ["ingestion", "frequency", "severity", "simulation", "explain"]

PROBE = """
import importlib
import pkgutil
import sys

import risk_engine

for module in pkgutil.walk_packages(risk_engine.__path__, "risk_engine."):
    importlib.import_module(module.name)

leaked = sorted(name for name in sys.modules if name.split(".")[0] == "django")
print(",".join(leaked))
"""


def test_every_subpackage_imports():
    for name in SUBPACKAGES:
        assert __import__(f"risk_engine.{name}", fromlist=["_"]) is not None


def test_risk_engine_never_imports_django():
    completed = subprocess.run(
        [sys.executable, "-c", PROBE],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    leaked = completed.stdout.strip()
    assert leaked == "", f"risk_engine pulled Django in: {leaked}"


def test_the_engine_runs_without_a_settings_module():
    """The CLI must work with no DJANGO_SETTINGS_MODULE set at all."""
    environment = {
        key: value for key, value in os.environ.items() if key != "DJANGO_SETTINGS_MODULE"
    }

    completed = subprocess.run(
        [sys.executable, "-m", "risk_engine", "--help"],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--data-dir" in completed.stdout


def test_the_version_is_exposed():
    assert risk_engine.__version__
