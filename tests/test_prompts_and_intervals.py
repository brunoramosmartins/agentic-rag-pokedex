"""Prompt loading with hashes, and the Wilson interval."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agentic_pokedex.evaluation.intervals import wilson
from agentic_pokedex.prompts import load_prompt


def test_load_prompt_strips_and_hashes(tmp_path: Path) -> None:
    (tmp_path / "p.md").write_text("  Answer briefly.\n\n", encoding="utf-8")
    prompt = load_prompt("p", tmp_path)
    assert prompt.text == "Answer briefly."
    assert prompt.sha256 == hashlib.sha256(b"Answer briefly.").hexdigest()


def test_the_identity_probe_prompt_is_the_registered_one() -> None:
    text = load_prompt("identity_probe").text
    assert text.startswith("The page below describes a Pokémon species.")
    assert text.endswith("Answer with its English name, or 'unknown'.")


@pytest.mark.parametrize(
    ("k", "n", "low", "high"),
    [
        (5, 50, 0.0435, 0.2137),  # the E-003 twin threshold
        (0, 50, 0.0, 0.0713),
        (50, 50, 0.9287, 1.0),
    ],
)
def test_wilson(k: int, n: int, low: float, high: float) -> None:
    lo, hi = wilson(k, n)
    assert lo == pytest.approx(low, abs=5e-4)
    assert hi == pytest.approx(high, abs=5e-4)


def test_wilson_with_no_trials() -> None:
    assert wilson(0, 0) == (0.0, 1.0)
