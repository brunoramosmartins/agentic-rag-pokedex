"""`.env` fills in missing variables and never overrides the environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_pokedex.config import load_env


def test_env_file_fills_missing_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("POKEDEX_TEST_VAR", raising=False)
    env = tmp_path / ".env"
    env.write_text("POKEDEX_TEST_VAR=from-file\n", encoding="utf-8")
    assert load_env(env) is True
    import os

    assert os.environ["POKEDEX_TEST_VAR"] == "from-file"


def test_environment_wins_over_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POKEDEX_TEST_VAR", "from-environment")
    env = tmp_path / ".env"
    env.write_text("POKEDEX_TEST_VAR=from-file\n", encoding="utf-8")
    load_env(env)
    import os

    assert os.environ["POKEDEX_TEST_VAR"] == "from-environment"


def test_missing_env_file_is_not_an_error(tmp_path: Path) -> None:
    assert load_env(tmp_path / "absent.env") is False
