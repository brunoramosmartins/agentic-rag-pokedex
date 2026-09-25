"""Smoke test: the package installs and imports."""

import agentic_pokedex


def test_package_imports_with_version() -> None:
    assert agentic_pokedex.__version__ == "0.1.0"
