"""Learnset coverage: answerable pairs, S2-usable pairs, candidate sets."""

from __future__ import annotations

from pathlib import Path

from agentic_pokedex.world.coverage import (
    answerable_level,
    combination_rows,
    group_rows,
    level_table,
    pairwise_rows,
    render_markdown,
    rows_from_csv,
    s2_usable,
)

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"


def row(pokemon: int, move: int, group: str, level: int) -> dict:
    return {"pokemon_id": pokemon, "move_id": move, "version_group": group,
            "level": level}


# Pair (1, 1): levels 5 / 9 / 5  → g1 and g3 agree.
# Pair (1, 2): levels 3 / 7 / —  → differs, absent in g3.
# Pair (1, 3): level 4 in g1 only → no distractor anywhere.
# Pair (2, 1): levels {1, 20} in g1 (ambiguous) / 8 in g2.
# Pair (2, 2): level 0 in g1 (on evolution) / 6 in g2.
ROWS = [
    row(1, 1, "g1", 5), row(1, 1, "g2", 9), row(1, 1, "g3", 5),
    row(1, 2, "g1", 3), row(1, 2, "g2", 7),
    row(1, 3, "g1", 4),
    row(2, 1, "g1", 1), row(2, 1, "g1", 20), row(2, 1, "g2", 8),
    row(2, 2, "g1", 0), row(2, 2, "g2", 6),
]
GROUPS = ("g1", "g2", "g3")
GENERATIONS = {"g1": 6, "g2": 7, "g3": 8}
TABLE = level_table(ROWS, GROUPS)


def test_level_table_collects_every_level() -> None:
    assert TABLE["g1"][(2, 1)] == frozenset({1, 20})
    assert TABLE["g3"] == {(1, 1): frozenset({5})}


def test_level_table_ignores_other_groups_and_keeps_empty_ones() -> None:
    table = level_table([row(1, 1, "other", 5)], ("g1",))
    assert table == {"g1": {}}


def test_answerable_level() -> None:
    assert answerable_level(frozenset({5})) == 5
    assert answerable_level(frozenset({1, 20})) is None  # ambiguous
    assert answerable_level(frozenset({0})) is None  # on evolution
    assert answerable_level(None) is None


def test_s2_usable_needs_a_distractor_at_a_different_level() -> None:
    # (1, 1) in g1: g3 lists it at the same level → a third version answers it.
    # (1, 2) in g1: g2 lists it at 7 → usable.
    # (1, 3) in g1: nobody else lists it → no distractor.
    assert s2_usable(TABLE, GROUPS, "g1") == {(1, 2)}
    # Without g3, (1, 1) becomes usable for g1.
    assert s2_usable(TABLE, ("g1", "g2"), "g1") == {(1, 1), (1, 2)}


def test_s2_usable_counts_ambiguous_distractors() -> None:
    # (2, 1) in g2 at 8; g1 lists {1, 20}, neither is 8 → usable.
    # (2, 2) in g2 at 6; g1 lists {0} → usable (0 is not 6).
    assert s2_usable(TABLE, ("g1", "g2"), "g2") == {(1, 1), (1, 2), (2, 1), (2, 2)}


def test_group_rows() -> None:
    rows = {r.group: r for r in group_rows(TABLE, GENERATIONS)}
    assert (rows["g1"].pokemon, rows["g1"].pairs, rows["g1"].answerable) == (2, 5, 3)
    assert rows["g2"].generation == 7


def test_pairwise_rows_use_pairs_answerable_in_both() -> None:
    rows = {(r.a, r.b): r for r in pairwise_rows(TABLE)}
    g1g2 = rows[("g1", "g2")]
    assert (g1g2.shared, g1g2.differ) == (2, 2)  # (1, 1) and (1, 2)
    g1g3 = rows[("g1", "g3")]
    assert (g1g3.shared, g1g3.differ, g1g3.rate) == (1, 0, 0.0)


def test_combination_rows_skip_repeated_generations() -> None:
    generations = {"g1": 6, "g2": 6, "g3": 8}
    rows = combination_rows(TABLE, generations, sizes=(2,))
    # (g1, g2) share a generation; (g2, g3) has more S2 material than (g1, g3).
    assert [r.groups for r in rows] == [("g2", "g3"), ("g1", "g3")]
    every = combination_rows(
        TABLE, generations, sizes=(2,), distinct_generations=False
    )
    assert len(every) == 3


def test_combination_rows_are_sorted_by_s2_material() -> None:
    rows = combination_rows(TABLE, GENERATIONS, sizes=(2, 3))
    totals = [r.s2_total for r in rows]
    assert totals == sorted(totals, reverse=True)
    top = rows[0]
    assert top.groups == ("g1", "g2")
    assert top.s2_per_group == (2, 4)
    assert (top.pokemon_all, top.pokemon_any) == (2, 2)


def test_render_markdown_has_the_three_sections() -> None:
    text = render_markdown(TABLE, GENERATIONS, "test rows")
    assert "## Learnset coverage by version group" in text
    assert "### Level differences between two groups" in text
    assert "### Candidate sets (one group per generation)" in text
    assert "| g1 | 6 | 2 | 5 | 3 |" in text


def test_rows_from_csv_keep_default_level_up_rows_of_the_groups() -> None:
    rows, generations = rows_from_csv(RAW, ("alpha-beta", "gamma"))
    assert generations["gamma"] == 2
    keys = {(r["pokemon_id"], r["move_id"], r["version_group"]) for r in rows}
    # Machine moves and non-default forms (10001) are left out.
    assert keys == {
        (1, 1, "alpha-beta"), (1, 1, "gamma"), (2, 1, "alpha-beta"),
        (3, 1, "alpha-beta"), (4, 2, "alpha-beta"), (4, 2, "gamma"),
    }
