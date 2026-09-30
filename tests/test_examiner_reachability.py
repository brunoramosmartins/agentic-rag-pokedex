"""Reachability: a labelled witness per subtype and error code (fixture world)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_pokedex.examiner.reachability import DECLARED, witnesses
from agentic_pokedex.world.registry import Registry

DEV = [
    {"id": "S0-A1:x=1", "stratum": "S0", "gold_facts": ["pability:1:3:hidden"],
     "twin_answer": "Undertow"},
    {"id": "S1-A1:x=1", "stratum": "S1", "twin_answer": "Undertow",
     "gold_facts": ["evo:2:1", "evo:3:2", "evoend:3", "pability:3:3:hidden"]},
    {"id": "S2-A1:p=4,m=2,v=gamma", "stratum": "S2", "twin_answer": "7",
     "gold_facts": ["learn:4:2:gamma:level-up:7"],
     "distractor_facts": ["learn:4:2:alpha-beta:level-up:1"]},
    {"id": "S3-A1:m=1,v=alpha-beta,t=3", "stratum": "S3", "twin_answer": "",
     "gold_facts": ["learn:2:1:alpha-beta:level-up:1", "ptype:2:1:3",
                    "learn:3:1:alpha-beta:level-up:0", "ptype:3:1:3"]},
    {"id": "S4-A1:p=1,m=1,v=alpha-beta", "stratum": "S4", "twin_answer": "",
     "gold_facts": ["learn:1:1:alpha-beta:level-up:1"],
     "distractor_facts": ["learn:1:1:gamma:level-up:5"]},
]


@pytest.fixture(scope="module")
def registry(fixture_world_dir: Path) -> Registry:
    return Registry.load(fixture_world_dir / "registry.json")


@pytest.fixture(scope="module")
def texts(fixture_world_dir: Path) -> dict[str, str]:
    with (fixture_world_dir / "pages" / "real.jsonl").open(encoding="utf-8") as fh:
        return {r["id"]: r["text"] for r in map(json.loads, fh)}


def test_every_code_has_a_witness(registry: Registry, texts: dict) -> None:
    found = witnesses(DEV, registry, texts)
    assert all(w is not None for w in found.values()), found
    assert found["not-found"].label == "insufficient (not-found)"
    assert found["wrong-version"].label == "insufficient (wrong-version)"
    assert found["wrong-version"].state == ("move/2/learned-by/alpha-beta/0",)
    assert found["accepted-truncated-set"].state == (
        "species/2/learnset/level-up/alpha-beta/0", "species/2/profile")
    assert found["answered-unanswerable"].label == "insufficient (nonexistent)"
    assert found["over-search"].label == "sufficient"
    assert found["never-reached"].question == "S1-A1:x=1"
    # Sprig's own Profile shows Undertow while the chain is unfinished.
    assert found["correct-at-insufficient"].state == ("species/1/profile",)
    assert "format-error" in DECLARED and "format-error" not in found


def test_a_missing_stratum_is_reported(registry: Registry, texts: dict) -> None:
    found = witnesses([r for r in DEV if r["stratum"] != "S4"], registry, texts)
    assert found["nonexistent"] is None and found["answered-unanswerable"] is None
    assert found["wrong-version"] is not None
