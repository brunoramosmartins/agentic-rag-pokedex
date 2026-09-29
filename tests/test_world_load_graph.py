"""Graph loader: batching and the load check (no Neo4j needed)."""

from __future__ import annotations

from pathlib import Path

from agentic_pokedex.world.load_graph import batched, check_load, expected_counts
from agentic_pokedex.world.pokeapi import read_world

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"


def test_batched_splits_without_losing_rows() -> None:
    rows = [{"i": i} for i in range(12)]
    batches = list(batched(rows, size=5))
    assert [len(b) for b in batches] == [5, 5, 2]
    assert [r for b in batches for r in b] == rows


def test_batched_on_empty_input() -> None:
    assert list(batched([], size=5)) == []


def perfect_stats(learnsets: int = 9) -> dict:
    tables = read_world(RAW)
    expected = expected_counts(tables, learnsets)
    return {
        "nodes": dict(expected["nodes"]),
        "relationships": dict(expected["relationships"]),
        "learns_by_version_group": {"alpha-beta": 5, "gamma": learnsets - 5},
    }


def test_expected_counts_follow_the_records() -> None:
    tables = read_world(RAW)
    expected = expected_counts(tables, learnsets=9)
    assert expected["nodes"]["Pokemon"] == 6
    assert expected["relationships"]["FORM_OF"] == 6
    assert expected["relationships"]["IN_VERSION"] == 2
    assert expected["relationships"]["LEARNS"] == 9


def test_check_load_passes_when_counts_match() -> None:
    assert check_load(perfect_stats(), read_world(RAW)) == []


def test_check_load_flags_a_silent_match_miss() -> None:
    # A MATCH that finds no endpoint writes nothing and raises nothing.
    stats = perfect_stats()
    stats["relationships"]["HAS_ABILITY"] -= 1
    problems = check_load(stats, read_world(RAW))
    assert problems == ["relationships.HAS_ABILITY: graph 7, records 8"]


def test_check_load_flags_unexpected_labels() -> None:
    stats = perfect_stats()
    stats["nodes"]["Stray"] = 1
    assert check_load(stats, read_world(RAW)) == ["nodes.Stray: unexpected in graph"]
