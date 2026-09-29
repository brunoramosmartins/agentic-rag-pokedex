"""Examiner: templates, surfaces, builders, filters and the concentration cap."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from agentic_pokedex.examiner import surfaces
from agentic_pokedex.examiner.generate import (
    Context,
    Question,
    answer_text,
    build_learnsets,
    build_s0,
    build_s1_final,
    build_s1_next,
    build_s3,
    cap_concentration,
    check_scope,
    single_unit,
    stratum_filter,
)
from agentic_pokedex.examiner.templates import (
    BY_ID,
    LEARNS_TEMPLATES,
    QUERIES,
    TEMPLATES,
)
from agentic_pokedex.world.pokeapi import iter_learnsets, read_world
from agentic_pokedex.world.render import Names, World, build_world

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"
SCOPE = ("alpha-beta", "gamma")


@pytest.fixture(scope="module")
def world() -> World:
    tables = read_world(RAW)
    return build_world(tables, list(iter_learnsets(RAW, tables)), SCOPE)


def ctx(world: World, withheld=()) -> Context:
    return Context(world, SCOPE, set(withheld))


def level_rows(world: World) -> list[dict]:
    return [
        {"species": world.pokemon[r["pokemon_id"]]["species_id"],
         "pokemon": r["pokemon_id"], "move": r["move_id"],
         "version_group": r["version_group"], "level": r["level"]}
        for r in world.learnsets if r["method"] == "level-up"
    ]


def q(stratum: str, cover: dict[str, list[str]]) -> Question:
    return Question(id="t", template="x", stratum=stratum, group="A", slots={},
                    answer=None, gold_facts=list(cover), cover=cover)


# --- Templates and surfaces ---------------------------------------------------


def test_every_learns_query_filters_the_scope() -> None:
    for name, query in LEARNS_TEMPLATES.items():
        assert re.search(r"r\.version_group IN \$scope", query), name
    for name, query in QUERIES.items():
        if "LEARNS" in query:
            assert name in LEARNS_TEMPLATES, name


def test_templates_are_consistent() -> None:
    ids = [t.id for t in TEMPLATES]
    assert len(ids) == len(set(ids)) == 16
    for t in TEMPLATES:
        assert t.query in QUERIES
        assert t.id.startswith(t.stratum) and t.group in ("A", "B")
    for stratum in ("S0", "S1", "S2", "S3", "S4"):
        assert any(t.group == "B" for t in TEMPLATES if t.stratum == stratum)


def test_every_template_has_three_surface_forms() -> None:
    for t in TEMPLATES:
        assert len(surfaces.SURFACES[t.id]) == 3


def test_s4_reads_exactly_like_s2() -> None:
    assert surfaces.SURFACES["S4-A1"] == surfaces.SURFACES["S2-A1"]
    assert surfaces.SURFACES["S4-B1"] == surfaces.SURFACES["S2-A2"]


def test_surface_choice_is_stable() -> None:
    first = surfaces.surface_index("S0-A1:x=1", 7)
    assert first == surfaces.surface_index("S0-A1:x=1", 7)
    assert first in (0, 1, 2)


def test_render_fills_placeholders_and_refuses_missing_ones() -> None:
    text = surfaces.render("S3-A1", 0, {"T": "Moss", "TERM": "Tosdor", "M": "Lash",
                                        "V": "Alpha"})
    assert text == "Which Moss-type Tosdor learn Lash by leveling up in Alpha?"
    with pytest.raises(KeyError):
        surfaces.render("S2-A1", 0, {"X": "Sprig"})


# --- Builders -----------------------------------------------------------------


def test_s0_hidden_ability_requires_a_single_one(world: World) -> None:
    drop: Counter[str] = Counter()
    rows = [{"species": 1, "pokemon": 1, "abilities": [3]},
            {"species": 3, "pokemon": 3, "abilities": [1, 3]}]
    out = build_s0("S0-A1", rows, ctx(world), drop)
    assert [x.id for x in out] == ["S0-A1:x=1"]
    assert out[0].gold_facts == ["pability:1:3:hidden"]
    assert drop == {"ambiguous: several hidden abilities": 1}


def test_s1_final_form_material_and_benign(world: World) -> None:
    rows = [{"anchor": 1, "anchor_pokemon": 1, "line": [1, 2, 3], "final_pokemon": 3},
            {"anchor": 2, "anchor_pokemon": 2, "line": [2, 3], "final_pokemon": 3}]
    out = {x.id: x for x in build_s1_final("S1-A1", rows, ctx(world), Counter())}
    sprig, sprout = out["S1-A1:x=1"], out["S1-A1:x=2"]
    assert sprig.gold_facts == ["evo:2:1", "evo:3:2", "evoend:3", "pability:3:3:hidden"]
    assert (sprig.answer, sprig.anchor_answer, sprig.material) == (3, [3], False)
    assert (sprout.anchor_answer, sprout.material) == ([], True)  # no hidden one


def test_s1_final_form_types(world: World) -> None:
    rows = [{"anchor": 1, "anchor_pokemon": 1, "line": [1, 2, 3], "final_pokemon": 3}]
    (out,) = build_s1_final("S1-A2", rows, ctx(world), Counter())
    assert out.answer == [2, 3] and out.anchor_answer == [3] and out.material
    assert out.gold_facts[-2:] == ["ptype:3:1:3", "ptype:3:2:2"]


def test_s1_next_form(world: World) -> None:
    rows = [{"anchor": 2, "anchor_pokemon": 2, "next": 3, "next_pokemon": 3}]
    (out,) = build_s1_next("S1-A3", rows, ctx(world), Counter())
    assert out.gold_facts == ["evo:3:2", "pability:3:3:hidden"] and out.material


def test_s2_level_questions_need_a_different_level_elsewhere(world: World) -> None:
    drop: Counter[str] = Counter()
    out = build_learnsets("S2-A1", level_rows(world), ctx(world), drop)
    assert sorted(x.id for x in out) == [
        "S2-A1:p=1,m=1,v=alpha-beta", "S2-A1:p=1,m=1,v=gamma",
        "S2-A1:p=4,m=2,v=alpha-beta", "S2-A1:p=4,m=2,v=gamma",
    ]
    assert drop["no other group lists this learnset"] == 2  # Sprout, Sproutree


def test_withheld_pairs_move_from_s2_to_s4(world: World) -> None:
    withheld = [(1, "alpha-beta")]
    s2 = build_learnsets("S2-A1", level_rows(world), ctx(world, withheld), Counter())
    s4 = build_learnsets("S4-A1", level_rows(world), ctx(world, withheld), Counter())
    assert "S2-A1:p=1,m=1,v=alpha-beta" not in {x.id for x in s2}
    assert [x.id for x in s4] == ["S4-A1:p=1,m=1,v=alpha-beta"]
    assert s4[0].answer == 1


def test_last_move_shared_with_another_group_is_dropped(world: World) -> None:
    drop: Counter[str] = Counter()
    out = build_learnsets("S2-B1", level_rows(world), ctx(world), drop)
    # Sprig and Blaze keep the same last move in both groups (4 learnsets).
    assert out == [] and drop["another group has the same last move"] == 4


def typed_rows(levels: dict[int, int]) -> list[dict]:
    return [{"move": 1, "version_group": "alpha-beta", "type": 3, "pokemon": p,
             "slot": 1, "level": lv} for p, lv in levels.items()]


def test_s3_sets(world: World) -> None:
    rows = typed_rows({1: 1, 2: 5, 3: 10, 4: 20})
    (a1,) = build_s3("S3-A1", rows, ctx(world), Counter())
    assert a1.answer == [1, 2, 3, 4] and a1.set_size == 4
    assert "learn:1:1:alpha-beta:level-up:1" in a1.gold_facts
    (b1,) = build_s3("S3-B1", rows, ctx(world), Counter())
    assert b1.slots["L"] == 10 and b1.answer == [1, 2, 3]


def test_s3_drops_sets_with_a_withheld_member(world: World) -> None:
    drop: Counter[str] = Counter()
    out = build_s3("S3-A1", typed_rows({1: 1, 2: 5, 3: 10}),
                   ctx(world, [(2, "alpha-beta")]), drop)
    assert out == [] and drop["a member's learnset is withheld"] == 1


# --- Filters ------------------------------------------------------------------


def test_single_unit() -> None:
    assert single_unit(q("S1", {"f": ["u1", "u2"], "g": ["u2"]}))
    assert not single_unit(q("S1", {"f": ["u1"], "g": ["u2"]}))


def test_stratum_filter() -> None:
    drop: Counter[str] = Counter()
    assert not stratum_filter(q("S1", {"f": ["u1"], "g": ["u1", "u2"]}), drop)
    assert stratum_filter(q("S1", {"f": ["u1"], "g": ["u2"]}), drop)
    assert stratum_filter(q("S2", {"f": ["u1"]}), drop)  # one fact by nature
    assert stratum_filter(q("S4", {"f": []}), drop)
    assert not stratum_filter(q("S4", {"f": ["u1"]}), drop)
    assert not stratum_filter(q("S3", {"f": []}), drop)
    assert drop == {
        "single-unit shortcut": 1,
        "S4: an indexed unit states the answer": 1,
        "a gold fact is in no indexed unit": 1,
    }


def test_check_scope() -> None:
    check_scope([{"version_group": "gamma"}], SCOPE)
    with pytest.raises(ValueError, match="outside the version scope"):
        check_scope([{"version_group": "red-blue"}], SCOPE)


def questions_with(answers: list[str]) -> list[Question]:
    return [Question(id=f"q{i}", template="S0-A2", stratum="S0", group="A",
                     slots={}, answer=a, gold_facts=[]) for i, a in enumerate(answers)]


def test_cap_on_a_small_answer_space() -> None:
    kept, summary = cap_concentration(questions_with(["a"] * 8 + ["b", "c"]))
    assert summary["cap"] == 0.5  # 1.5 × 1/3
    assert Counter(x.answer for x in kept) == {"a": 2, "b": 1, "c": 1}
    assert summary["majority_after"] <= summary["cap"]


def test_cap_on_an_open_answer_space() -> None:
    answers = ["a"] * 50 + [f"v{i}" for i in range(60)]
    kept, summary = cap_concentration(questions_with(answers))
    assert summary["cap"] == 0.10
    assert summary["majority_after"] <= 0.10
    assert len([x for x in kept if x.answer != "a"]) == 60  # only "a" is thinned


def test_cap_is_deterministic() -> None:
    answers = ["a"] * 30 + ["b"] * 5 + ["c"] * 5
    first, _ = cap_concentration(questions_with(answers), seed=3)
    again, _ = cap_concentration(questions_with(answers), seed=3)
    assert [x.id for x in first] == [x.id for x in again]


def test_s4_answer_text_is_an_abstention(world: World) -> None:
    names = Names.real(world)
    s4 = Question(id="S4-A1:x", template="S4-A1", stratum="S4", group="A",
                  slots={}, answer=41, gold_facts=[])
    assert answer_text(s4, names) == "abstain (withheld value: 41)"
    factor = Question(id="S0-B1:x", template="S0-B1", stratum="S0", group="B",
                      slots={}, answer=0.5, gold_facts=[])
    assert answer_text(factor, names) == "×0.5"
    assert BY_ID["S4-B1"].answer == "move"
