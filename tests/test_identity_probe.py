"""E-003 identity probe: sample, pages, masking, grading, decision rule."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agentic_pokedex.evaluation import identity_probe as probe
from agentic_pokedex.evaluation.identity_probe import (
    CONTROL,
    MASK,
    TWIN,
    TWIN_NO_NOTES,
    ConditionSummary,
    ProbeRow,
)
from agentic_pokedex.world.index import load_units
from agentic_pokedex.world.pokeapi import iter_learnsets, read_world
from agentic_pokedex.world.registry import Registry
from agentic_pokedex.world.render import World, build_world

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"


def chars(text: str) -> int:
    return len(text) // 4


@pytest.fixture(scope="module")
def world() -> World:
    tables = read_world(RAW)
    rows = list(iter_learnsets(RAW, tables))
    return build_world(tables, rows, ("alpha-beta", "gamma"))


@pytest.fixture(scope="module")
def units(fixture_world_dir: Path) -> dict[str, list]:
    registry = Registry.load(fixture_world_dir / "registry.json")
    return {
        name: load_units(fixture_world_dir / "pages" / f"{name}.jsonl", registry)
        for name in ("real", "twin")
    }


# --- Sample -----------------------------------------------------------------


def test_eligible_species(world: World) -> None:
    assert probe.eligible_species(world) == [1, 2, 3, 4]


def test_sample_is_stratified_and_seeded(world: World) -> None:
    quotas = {1: 2, 2: 1}
    sample = probe.sample_species(world, quotas, seed=7)
    assert len(sample) == 3
    assert [world.species[s]["generation"] for s in sample] == [1, 1, 2]
    assert probe.sample_species(world, quotas, seed=7) == sample


def test_sample_refuses_a_short_generation(world: World) -> None:
    with pytest.raises(ValueError, match="generation 2"):
        probe.sample_species(world, {2: 2})


def test_registered_quotas_total_fifty() -> None:
    assert sum(probe.QUOTAS.values()) == 50


# --- Pages ------------------------------------------------------------------


def test_mask_name_is_whole_word_and_case_insensitive() -> None:
    text = "Species: Sprig\n[[Sprig]] → [[Sprout]]; SPRIG naps. Sprigs grow."
    assert probe.mask_name(text, "Sprig") == (
        f"Species: {MASK}\n[[{MASK}]] → [[Sprout]]; {MASK} naps. Sprigs grow."
    )


def test_control_page_masks_the_species_and_keeps_relatives(world, units) -> None:
    page = probe.condition_page(CONTROL, 1, world, units["real"], units["twin"], chars)
    assert "Sprig" not in page.replace("Sprigs", "")
    assert f"Species: {MASK} · Section: Profile" in page
    assert "[[Sprout]]" in page  # the evolution relative stays real
    assert "A tiny seed" in page  # notes are shown


def test_control_masks_form_names(world, units) -> None:
    page = probe.condition_page(CONTROL, 4, world, units["real"], units["twin"], chars)
    assert "Blaze" not in page
    assert f"Mega {MASK}" in page


def test_twin_pages_show_no_real_name(world, units) -> None:
    for condition in (TWIN, TWIN_NO_NOTES):
        page = probe.condition_page(condition, 1, world, units["real"], units["twin"],
                                    chars)
        for real in ("Sprig", "Sprout", "Sproutree", "Moss", "Thicket"):
            assert not re.search(rf"(?<!\w){real}(?!\w)", page), real


def test_no_notes_condition_drops_only_the_notes(world, units) -> None:
    with_notes = probe.condition_page(TWIN, 1, world, units["real"], units["twin"],
                                      chars)
    without = probe.condition_page(TWIN_NO_NOTES, 1, world, units["real"],
                                   units["twin"], chars)
    assert "Section: Notes" in with_notes
    assert "Section: Notes" not in without
    assert "Section: Profile" in without


def test_pages_respect_the_token_cap(world, units) -> None:
    page = probe.condition_page(TWIN, 4, world, units["real"], units["twin"],
                                lambda t: 10 * len(t))  # every unit exceeds 700
    assert page.count("Species: ") == 1  # the first unit only, always shown


def test_custom_ids_round_trip() -> None:
    for condition in probe.CONDITIONS:
        assert probe.parse_custom_id(probe.custom_id(condition, 25)) == (condition, 25)


# --- Grading ----------------------------------------------------------------


def test_accepted_names_cover_the_line_and_its_forms(world: World) -> None:
    line, exact = probe.accepted_names(world, 1)
    assert line == {"sprig", "sprout", "sproutree", "sproutreetidalform"}
    assert exact == {"sprig"}


@pytest.mark.parametrize(
    ("guess", "identified", "exact"),
    [
        ("Sprig", True, True),
        ("sprout", True, False),  # same line counts
        ("Sproutree (Tidal Form)", True, False),
        ("Blaze", False, False),
        ("unknown", False, False),
    ],
)
def test_grade(world: World, guess: str, identified: bool, exact: bool) -> None:
    row = probe.grade(world, TWIN, 1, guess, 0.4)
    assert (row.identified, row.exact, row.generation) == (identified, exact, 1)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"guess": "Sprig", "confidence": 0.9}', ("Sprig", 0.9)),
        ('{"guess": "unknown", "confidence": 0}', ("unknown", 0.0)),
        ('{"guess": 3, "confidence": 0.5}', None),
        ('{"confidence": 0.5}', None),
        ("not json", None),
        (None, None),
    ],
)
def test_parse_guess(content, expected) -> None:
    assert probe.parse_guess(content) == expected


# --- Summary and decision ---------------------------------------------------


def rows(condition: str, identified: int, total: int) -> list[ProbeRow]:
    return [
        ProbeRow(i, 1 + i % 9, condition, "x" if i < identified else "unknown", 0.5,
                 i < identified, False)
        for i in range(total)
    ]


def test_summarize_counts() -> None:
    summary = probe.summarize(rows(TWIN, 3, 50))
    s = summary[TWIN]
    assert (s.valid, s.identified, s.unknown) == (50, 3, 47)
    assert s.rate == pytest.approx(0.06)
    low, high = s.interval
    assert low < 0.06 < high
    assert sum(n for _, n in s.by_generation.values()) == 50


@pytest.mark.parametrize(
    ("control", "twin", "no_notes", "verdict"),
    [
        (24, 0, 0, "probe broken"),
        (25, 5, 5, "pass"),
        (45, 6, 2, "fail: notes"),
        (45, 6, 6, "fail: structural"),
    ],
)
def test_decide(control: int, twin: int, no_notes: int, verdict: str) -> None:
    summary: dict[str, ConditionSummary] = {}
    for condition, k in ((CONTROL, control), (TWIN, twin), (TWIN_NO_NOTES, no_notes)):
        summary |= probe.summarize(rows(condition, k, 50))
    assert probe.decide(summary) == verdict


def summary_of(counts: dict[str, tuple[int, int]]) -> dict[str, ConditionSummary]:
    summary: dict[str, ConditionSummary] = {}
    for condition, (k, n) in counts.items():
        summary |= probe.summarize(rows(condition, k, n))
    return summary


def test_decide_bounded_takes_a_shared_verdict() -> None:
    # The first E-003 collection: twin fails either way.
    summary = summary_of({CONTROL: (48, 50), TWIN: (22, 34), TWIN_NO_NOTES: (1, 37)})
    invalid = {CONTROL: 0, TWIN: 16, TWIN_NO_NOTES: 13}
    assert probe.decide_bounded(summary, invalid) == (
        "undetermined: fail: structural / fail: notes"
    )
    few = {CONTROL: 0, TWIN: 16, TWIN_NO_NOTES: 2}
    summary = summary_of({CONTROL: (48, 50), TWIN: (22, 34), TWIN_NO_NOTES: (1, 48)})
    assert probe.decide_bounded(summary, few) == "fail: notes"


def test_decide_bounded_without_invalid_equals_decide() -> None:
    summary = summary_of({CONTROL: (45, 50), TWIN: (2, 50), TWIN_NO_NOTES: (1, 50)})
    none = dict.fromkeys(probe.CONDITIONS, 0)
    assert probe.decide_bounded(summary, none) == probe.decide(summary) == "pass"


def test_invalid_control_answers_count_against_the_probe() -> None:
    summary = summary_of({CONTROL: (25, 45), TWIN: (0, 50), TWIN_NO_NOTES: (0, 50)})
    invalid = {CONTROL: 5, TWIN: 0, TWIN_NO_NOTES: 0}
    # worst: 25 of 50 → valid probe; best: 30 of 50 → valid probe → pass
    assert probe.decide_bounded(summary, invalid) == "pass"
    summary = summary_of({CONTROL: (22, 45), TWIN: (0, 50), TWIN_NO_NOTES: (0, 50)})
    assert probe.decide_bounded(summary, invalid) == "undetermined: probe broken / pass"
