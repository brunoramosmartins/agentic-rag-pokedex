"""The sufficiency labeler: golden trajectories (100% required) and its rules."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from agentic_pokedex.labeling.sufficiency import (
    ABSTAINED,
    SUBTYPES,
    Gold,
    final_state,
    first_sufficient,
    gold_from,
    label_state,
    label_trajectory,
)
from agentic_pokedex.world.registry import Registry

GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_trajectories.json").read_text(
        encoding="utf-8"
    )
)


@pytest.fixture(scope="module")
def registry(fixture_world_dir: Path) -> Registry:
    return Registry.load(fixture_world_dir / "registry.json")


# --- Golden trajectories ------------------------------------------------------


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda c: c["name"])
def test_golden_trajectory(case: dict, registry: Registry) -> None:
    gold = gold_from(case["question"], registry)
    labels = label_trajectory(gold, case["steps"], registry)
    assert len(labels) == len(case["expected"]) == len(case["steps"]) + 1
    for t, (label, expected) in enumerate(zip(labels, case["expected"], strict=True)):
        assert label.step == t
        assert label.state == expected["state"], t
        assert label.subtype == expected["subtype"], t
        assert list(label.missing) == expected["missing"], t
        assert list(label.near_certain) == expected.get("near_certain", []), t
        members = expected.get("members")
        assert label.members == (tuple(members) if members else None), t


@pytest.mark.parametrize("case", GOLDEN["refused"], ids=lambda c: c["name"])
def test_golden_refusal(case: dict, registry: Registry) -> None:
    with pytest.raises(ValueError, match=case["error"]):
        gold = gold_from(case["question"], registry)
        label_trajectory(gold, case["steps"], registry)


def test_golden_file_covers_every_stratum_and_subtype() -> None:
    strata = {c["question"]["stratum"] for c in GOLDEN["cases"]}
    assert strata == set(SUBTYPES)
    reached = {e["state"] for c in GOLDEN["cases"] for e in c["expected"]}
    assert reached == {"sufficient", "insufficient"}


# --- Rules --------------------------------------------------------------------


def gold(
    stratum: str, cover: dict[str, set[str]], near: frozenset[str] = frozenset()
) -> Gold:
    return Gold("q", stratum, {f: frozenset(u) for f, u in cover.items()},
                frozenset(near))


def test_subtypes_follow_the_stratum() -> None:
    assert SUBTYPES == {"S0": "missing-hop", "S1": "missing-hop",
                        "S2": "wrong-version", "S3": "truncated",
                        "S4": "nonexistent"}
    for stratum, subtype in SUBTYPES.items():
        # A real fact id: S3 reads the member (the Pokémon entry) from it.
        g = gold(stratum, {"ptype:2:1:3": {"u"}})
        assert label_state(g, []).subtype == subtype


def test_one_copy_of_each_fact_is_enough() -> None:
    g = gold("S1", {"f": {"u1", "u2"}, "g": {"u3"}})
    assert not label_state(g, ["u1"]).sufficient
    assert label_state(g, ["u2", "u3"]).sufficient
    assert label_state(g, ["u1", "u3"]).sufficient


def test_counts() -> None:
    g = gold("S1", {"f": {"u1"}, "g": {"u2"}, "h": {"u3"}})
    label = label_state(g, ["u2", "x"])
    assert (label.covered, label.total, label.missing) == (1, 3, ("f", "h"))


def test_s3_members_group_facts_by_entry() -> None:
    g = gold("S3", {"learn:2:1:v:level-up:1": {"a"}, "ptype:2:1:3": {"b"},
                    "learn:3:1:v:level-up:4": {"c"}, "ptype:3:1:3": {"d"}})
    assert label_state(g, ["a"]).members == (0, 2)  # a member needs both facts
    assert label_state(g, ["a", "b", "c"]).members == (1, 2)
    assert label_state(g, ["a", "b", "c", "d"]).members == (2, 2)


def test_near_certain_is_reported_not_counted() -> None:
    g = gold("S2", {"f": {"u1"}}, near=frozenset({"d1", "d2"}))
    label = label_state(g, ["d2", "d1"])
    assert label.near_certain == ("d1", "d2") and not label.sufficient
    assert label_state(g, ["d1", "u1"]).sufficient


def test_labels_are_monotone(registry: Registry) -> None:
    # More evidence never loses a fact: over random trajectories on the fixture
    # world, the missing set only shrinks and a sufficient state stays so.
    indexed = sorted(registry.indexed_units())
    rng = random.Random(0)
    for case in GOLDEN["cases"]:
        g = gold_from(case["question"], registry)
        for _ in range(20):
            steps = [rng.sample(indexed, rng.randint(0, 3)) for _ in range(6)]
            labels = label_trajectory(g, steps, registry)
            for before, after in zip(labels, labels[1:], strict=False):
                assert set(after.missing) <= set(before.missing)
                assert not before.sufficient or after.sufficient
            if g.stratum == "S4":
                assert first_sufficient(labels) is None


def test_first_sufficient_and_final_state(registry: Registry) -> None:
    case = GOLDEN["cases"][0]
    labels = label_trajectory(gold_from(case["question"], registry), case["steps"],
                              registry)
    assert first_sufficient(labels) == 2
    assert final_state(labels, 1, abstained=False) == "insufficient"
    assert final_state(labels, 2, abstained=False) == "sufficient"
    assert final_state(labels, 2, abstained=True) == ABSTAINED


def test_gold_ignores_a_stale_cover_in_the_record(registry: Registry) -> None:
    record = {"id": "S0-A2:m=1", "stratum": "S0", "gold_facts": ["mpower:1:45"],
              "cover": {"mpower:1:45": ["species/1/profile"]}}
    assert gold_from(record, registry).cover == {
        "mpower:1:45": frozenset({"move/1/profile"})
    }
