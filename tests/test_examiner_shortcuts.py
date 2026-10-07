"""Shortcut scan: statements, lexical matching, planted leaks and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_pokedex.examiner.shortcuts import (
    Flag,
    Lexicon,
    ScanIndex,
    build_index,
    check_plants,
    line_kind,
    plants,
    probe,
    resolve,
    statements,
)
from agentic_pokedex.world.pokeapi import iter_learnsets, read_world
from agentic_pokedex.world.registry import Registry
from agentic_pokedex.world.render import Names, build_world

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"

# Fixture world: 1 Sprig -> 2 Sprout -> 3 Sproutree; 4 Blaze. Move 1 Vine Lash
# (Moss). Type 3 Moss. Ability 3 Undertow. Sprig's alpha-beta learnset withheld.
S0_A1 = {"id": "S0-A1:x=1", "template": "S0-A1", "slots": {"X": 1}, "answer": 3,
         "cover": {"pability:1:3:hidden": ["species/1/profile",
                                           "ability/3/holders/0"]}}
S0_A4 = {"id": "S0-A4:m=1", "template": "S0-A4", "slots": {"M": 1}, "answer": 3,
         "cover": {"mtype:1:3": ["move/1/profile"]}}
S1_A1 = {"id": "S1-A1:x=2", "template": "S1-A1", "slots": {"X": 2}, "answer": 3,
         "cover": {"evo:3:2": ["species/2/profile"],
                   "evoend:3": ["species/3/profile"],
                   "pability:3:3:hidden": ["species/3/profile",
                                           "ability/3/holders/0"]}}
S4_A1 = {"id": "S4-A1:p=1,m=1,v=alpha-beta", "template": "S4-A1",
         "slots": {"X": 1, "M": 1, "V": "alpha-beta"}, "answer": 1,
         "cover": {"learn:1:1:alpha-beta:level-up:1": []}}


@pytest.fixture(scope="module")
def names() -> Names:
    tables = read_world(RAW)
    world = build_world(tables, list(iter_learnsets(RAW, tables)),
                        ("alpha-beta", "gamma"))
    return Names.real(world)


@pytest.fixture(scope="module")
def lexicon(names: Names) -> Lexicon:
    return Lexicon(names)


@pytest.fixture(scope="module")
def index(fixture_world_dir: Path, lexicon: Lexicon) -> ScanIndex:
    registry = Registry.load(fixture_world_dir / "registry.json")
    return build_index(fixture_world_dir / "pages" / "real.jsonl", registry, lexicon)


# --- Text ---------------------------------------------------------------------


def test_statements_pair_the_header_with_each_line() -> None:
    text = ("Species: Sprig · Section: Profile\nTypes: [[Moss]]\n"
            "Evolves into: [[Sprout]]")
    assert statements(text) == [
        "Species: Sprig · Section: Profile\nTypes: [[Moss]]",
        "Species: Sprig · Section: Profile\nEvolves into: [[Sprout]]",
    ]
    assert statements(text, free_text=True) == [text]


def test_line_kinds() -> None:
    head = "Species: Sprig · Section: Learnset"
    assert line_kind(f"{head}\nLevel 13: [[Vine Lash]]") == "Level N"
    assert line_kind(f"{head}\n[[Sprout]] (Moss) — level 1") == "entry"
    assert line_kind(f"{head}\nAttacking — resists: [[Moss]]") == "Attacking — resists"
    assert line_kind(f"{head}\nanything", free_text=True) == "free text"


def test_mentions_match_whole_token_sequences(lexicon: Lexicon) -> None:
    found = lexicon.mentions("[[Sproutree (Tidal Form)]] — level 12, Sprout's")
    assert {"Sproutree", "Sproutree (Tidal Form)", "Sprout", "12"} <= found
    assert "Sprig" not in found
    assert "Sprout" not in lexicon.mentions("[[Sproutree]]")
    assert "1" not in lexicon.mentions("level 12")


# --- Probes -------------------------------------------------------------------


def test_probe_forms(names: Names) -> None:
    assert probe(S0_A1, names).anchors == ("Sprig",)
    assert probe(S0_A1, names).names == ("Undertow",)
    s4 = probe(S4_A1, names)
    assert s4.anchors == ("Sprig", "Vine Lash", "Alpha/Beta") and s4.names == ("1",)
    factor = {"id": "S1-B1:m=1,x=4", "template": "S1-B1", "slots": {"M": 1, "X": 4},
              "answer": 0.5}
    assert probe(factor, names).phrases == ("not very effective against", "resists")
    assert probe(factor | {"answer": 4.0}, names) is None  # ×4 is never rendered
    category = {"id": "S0-A3:m=1", "template": "S0-A3", "slots": {"M": 1},
                "answer": "physical"}
    assert probe(category, names).phrases == ("physical",)


# --- Scan ---------------------------------------------------------------------


def test_gold_units_are_not_flags(index: ScanIndex, names: Names) -> None:
    assert index.scan(S0_A1, probe(S0_A1, names)) == []


def test_statements_not_units(index: ScanIndex, names: Names) -> None:
    # Sprig's Profile names Sprout ("Evolves into") and Undertow (its own hidden
    # ability) on two different lines: two facts, not a statement of the answer.
    # A unit-level scan would flag it.
    assert index.scan(S1_A1, probe(S1_A1, names)) == []


def test_a_coincidence_is_flagged_and_classed(index: ScanIndex, names: Names) -> None:
    # Vine Lash's hubs list its learners with their types, and Moss is one.
    flags = index.scan(S0_A4, probe(S0_A4, names))
    assert {f.unit for f in flags} == {"move/1/learned-by/alpha-beta/0",
                                       "move/1/learned-by/gamma/0"}
    assert {f.klass for f in flags} == {("S0-A4", "Learned by", "entry")}
    assert len(flags) == 3  # Sprout and Sproutree in alpha-beta, Sprig in gamma


def test_withheld_units_are_not_scanned(index: ScanIndex, names: Names) -> None:
    # Sprig's alpha-beta learnset states the S4 value, but no agent can see it.
    assert index.scan(S4_A1, probe(S4_A1, names)) == []


# --- Planted leaks --------------------------------------------------------------


@pytest.mark.parametrize("record", [S0_A1, S0_A4, S1_A1, S4_A1],
                         ids=lambda r: r["id"])
def test_each_plant_is_flagged(record: dict, lexicon: Lexicon, names: Names) -> None:
    p = probe(record, names)
    for unit, text, free in plants(record, p):
        planted = ScanIndex(lexicon)
        planted.add(unit, text, "Planted", free)
        assert [f.unit for f in planted.scan(record, p)] == [unit]


def test_a_plant_inside_the_gold_units_is_not_a_flag(
    lexicon: Lexicon, names: Names
) -> None:
    p = probe(S0_A1, names)
    unit, text, free = plants(S0_A1, p)[0]
    planted = ScanIndex(lexicon)
    planted.add(unit, text, "Planted", free)
    record = S0_A1 | {"cover": {"pability:1:3:hidden": [unit]}}
    assert planted.scan(record, p) == []


def test_check_plants(lexicon: Lexicon, names: Names) -> None:
    flagged, planted, missed = check_plants([S0_A1, S0_A4, S1_A1, S4_A1], names,
                                            lexicon)
    assert (flagged, planted, missed) == (8, 8, [])


# --- Resolution -----------------------------------------------------------------


def flag(qid: str, section: str) -> Flag:
    return Flag(qid, "u", 0, section, "entry", "")


def test_resolve() -> None:
    verdicts = {("S0-A4", "Learned by", "entry"): ("coincidence", "types"),
                ("S0-A4", "Holders", "entry"): ("leak", "states it")}
    status = resolve({
        "S0-A4:m=1": [flag("S0-A4:m=1", "Learned by")],
        "S0-A4:m=2": [flag("S0-A4:m=2", "Learned by"), flag("S0-A4:m=2", "Holders")],
        "S0-A4:m=3": [flag("S0-A4:m=3", "Profile")],
    }, verdicts)
    assert status == {"S0-A4:m=1": "kept", "S0-A4:m=2": "discarded",
                      "S0-A4:m=3": "unresolved"}


def test_verdicts_are_well_formed() -> None:
    from agentic_pokedex.examiner.shortcuts import VERDICTS
    from agentic_pokedex.examiner.templates import BY_ID

    for (template, section, kind), (verdict, reason) in VERDICTS.items():
        assert template in BY_ID and section and kind
        assert verdict in ("coincidence", "leak") and reason
