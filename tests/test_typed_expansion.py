"""Typed expansion (E-002's pipeline), its golden trace, and the E-002 reading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_pokedex.arms.typed_expansion import (
    LINK_ORDER,
    Delivery,
    Link,
    Step,
    World,
    expand,
    expand_from,
    link_type,
    links_of,
    ordered,
)
from agentic_pokedex.evaluation.e002 import (
    Outcome,
    cluster_key,
    hub_units,
    rate,
    read,
    report,
    summarize,
    two_by_two,
)
from agentic_pokedex.labeling.sufficiency import gold_from
from agentic_pokedex.tools.contract import ToolResult
from agentic_pokedex.tools.open_page import Pages
from agentic_pokedex.world.index import HybridIndex, Unit, load_units
from agentic_pokedex.world.registry import Registry


def chars(text: str) -> int:
    """A test token counter: one token per four characters."""
    return len(text) // 4


# --- Link types ----------------------------------------------------------------


def test_link_types() -> None:
    assert link_type("Profile", "Evolves into: [[B]]", "species") == "evolves-into"
    assert link_type("Profile", "Forms: [[B]]", "species") is None
    assert link_type("Learned by", "[[B]] (Fire) — level 3", "species") == "learner"
    assert link_type("Holders", "[[B]] (hidden)", "species") == "holder"
    assert link_type("Form", "Abilities: [[X]]", "ability") == "ability"
    assert link_type("Matchups", "Super effective: [[X]]", "type") == "type"
    assert link_type("Learnset", "Level 1: [[X]]", "move") == "move"
    assert link_type("Profile", "Type: [[X]]", "move") is None


def test_the_order_is_the_registered_one() -> None:
    assert LINK_ORDER == ("evolves-into", "ability", "type", "move", "learner",
                          "holder")


def test_ordered_is_stable_within_a_type() -> None:
    links = [Link("move", "m1"), Link("type", "t1"), Link("move", "m2"),
             Link("evolves-into", "s1"), Link("type", "t2")]
    assert [link.title for link in ordered(links)] == ["s1", "t1", "t2", "m1", "m2"]
    assert [link.title for link in ordered(links, tuple(reversed(LINK_ORDER)))] == [
        "m1", "m2", "t1", "t2", "s1"]


# --- A small world --------------------------------------------------------------

UNITS = [
    Unit("s/kedros/profile", "Kedros", "Profile",
         "Species: Kedros · Section: Profile\nTypes: [[Fiero]]\n"
         "Hidden ability: [[Blazor]]\nEvolves into: [[Tarnlet]]\n"
         "Forms: [[Kedros Alt]]"),
    Unit("s/tarnlet/profile", "Tarnlet", "Profile",
         "Species: Tarnlet · Section: Profile\nTypes: [[Fiero]]\nEvolves into: —"),
    Unit("t/fiero/matchups", "Fiero", "Matchups",
         "Type: Fiero · Section: Matchups\nSuper effective: [[Fiero]]"),
    Unit("a/blazor/holders", "Blazor", "Holders",
         "Ability: Blazor · Section: Holders\n[[Kedros]] (hidden)\n[[Tarnlet]]"),
]
KINDS = {"Kedros": "species", "Tarnlet": "species", "Fiero": "type",
         "Blazor": "ability"}
SECTIONS = {"s/kedros/profile": "Profile", "s/tarnlet/profile": "Profile",
            "t/fiero/matchups": "Matchups", "a/blazor/holders": "Holders"}


@pytest.fixture()
def world() -> World:
    return World(HybridIndex(UNITS), Pages(UNITS), {u.id: u.text for u in UNITS},
                 SECTIONS, KINDS)


def test_links_of_skips_pageless_targets_and_repeats(world: World) -> None:
    links = links_of(["s/kedros/profile", "s/tarnlet/profile"], world.texts,
                     world.sections, world.page_kind)
    # "Kedros Alt" has no page; Fiero appears twice.
    assert links == [Link("type", "Fiero"), Link("ability", "Blazor"),
                     Link("evolves-into", "Tarnlet")]


def test_expand_completes_the_hit_then_goes_breadth_first(world: World) -> None:
    d = expand(world, "Kedros evolves", k=1, counter=chars)
    assert d.searched == ("s/kedros/profile",)
    calls = [s.call for s in d.steps]
    # Level 0 reads the hit's section to its end: the unit, then "No more units."
    assert calls[1:3] == ["open_page('Kedros', section='Profile')",
                          "open_page('Kedros', section='Profile', offset=1)"]
    # Level 1 in link order: Tarnlet (evolves-into), Blazor (ability), Fiero.
    assert calls[3:6] == ["open_page('Tarnlet')", "open_page('Blazor')",
                          "open_page('Fiero')"]
    # Level 2: Blazor's holders link Kedros, never opened by a link before.
    assert calls[6:] == ["open_page('Kedros')"]
    assert d.units == ("s/kedros/profile", "s/tarnlet/profile", "a/blazor/holders",
                       "t/fiero/matchups")
    assert d.calls == 6 and d.deepest == 2 and not d.bound


def test_expand_stops_at_the_budget(world: World) -> None:
    full = expand(world, "Kedros evolves", k=1, counter=chars, budget=10_000)
    tight = expand(world, "Kedros evolves", k=1, counter=chars,
                   budget=full.tokens - 1)
    assert tight.bound and tight.tokens <= full.tokens - 1
    assert tight.calls == full.calls - 1


def test_expand_with_another_order(world: World) -> None:
    d = expand(world, "Kedros evolves", k=1, counter=chars,
               order=tuple(reversed(LINK_ORDER)))
    assert d.steps[3].call == "open_page('Fiero')"


def test_through_and_deepest() -> None:
    d = Delivery(("a", "b", "c"), 30, 2, False, ("a",), (
        Step(-1, "search", ("a",), 10), Step(0, "x", ("a", "b"), 10),
        Step(1, "y", ("c",), 10)))
    assert d.through(-1) == ("a",) and d.through(0) == ("a", "b")
    assert d.through(5) == ("a", "b", "c") and d.deepest == 1


# --- Golden trace on the fixture world (gate 7) ------------------------------------
#
# Traced by hand from the fixture's pages (one token per four characters, cap
# 700): the search result is Sprig's Profile; level 0 reads that section (32
# tokens) and learns it has ended ("No more units.", 3); level 1 takes Sprig's
# links in type order — Sprout (evolves-into; Profile + Learnset, 202 characters,
# 50), Thicket and Undertow (abilities, 17 and 26), Moss (type, 51); level 2 —
# Sproutree (evolves-into, four units, 480 characters, 120), Tide and Ember
# (types, 51 and 52), Vine Lash (move, three units, 73), Sprig (holder, three
# units, 72; its Profile is not delivered twice); level 3 — Soak (move, 18).
# 32 + 35 + 144 + 368 + 18 = 597 tokens, 12 open_page calls.

GOLDEN_CALLS = [
    (-1, "search('')", 32),
    (0, "open_page('Sprig', section='Profile')", 32),
    (0, "open_page('Sprig', section='Profile', offset=1)", 3),
    (1, "open_page('Sprout')", 50),
    (1, "open_page('Thicket')", 17),
    (1, "open_page('Undertow')", 26),
    (1, "open_page('Moss')", 51),
    (2, "open_page('Sproutree')", 120),
    (2, "open_page('Tide')", 51),
    (2, "open_page('Ember')", 52),
    (2, "open_page('Vine Lash')", 73),
    (2, "open_page('Sprig')", 72),
    (3, "open_page('Soak')", 18),
]
GOLDEN_UNITS = (
    "species/1/profile", "species/2/profile",
    "species/2/learnset/level-up/alpha-beta/0", "ability/1/holders/0",
    "ability/3/holders/0", "type/3/matchups", "species/3/profile",
    "species/3/form/10002", "species/3/learnset/level-up/alpha-beta/0",
    "species/3/learnset/machine/alpha-beta/0", "type/2/matchups",
    "type/1/matchups", "move/1/profile", "move/1/learned-by/alpha-beta/0",
    "move/1/learned-by/gamma/0", "species/1/notes",
    "species/1/learnset/level-up/gamma/0", "move/3/profile",
)


@pytest.fixture(scope="module")
def registry(fixture_world_dir: Path) -> Registry:
    return Registry.load(fixture_world_dir / "registry.json")


@pytest.fixture(scope="module")
def fixture_world(fixture_world_dir: Path, registry: Registry) -> World:
    units = load_units(fixture_world_dir / "pages" / "real.jsonl", registry)
    return World.build(HybridIndex(units), registry)


def sprig_first(world: World) -> ToolResult:
    return ToolResult(world.texts["species/1/profile"], ("species/1/profile",), 32)


def test_golden_expansion_trace(fixture_world: World) -> None:
    d = expand_from(fixture_world, sprig_first(fixture_world), counter=chars)
    assert [(s.level, s.call, s.tokens) for s in d.steps] == GOLDEN_CALLS
    assert d.units == GOLDEN_UNITS
    assert (d.tokens, d.calls, d.deepest, d.bound) == (597, 12, 3, False)


def test_golden_trace_stops_where_b_binds(fixture_world: World) -> None:
    # 32 + 35 + 144 + 120 = 331 fits; Tide's 51 would pass 381.
    d = expand_from(fixture_world, sprig_first(fixture_world), counter=chars,
                    budget=381)
    assert (d.tokens, d.calls, d.bound) == (331, 7, True)
    assert d.steps[-1].call == "open_page('Sproutree')"


# --- The E-002 reading ------------------------------------------------------------


S1 = {"id": "S1-A1:x=1", "stratum": "S1", "template": "S1-A1", "slots": {"X": 1},
      "gold_facts": ["evo:2:1", "evo:3:2", "evoend:3", "pability:3:3:hidden"]}
S3 = {"id": "S3-A1:m=1,v=alpha-beta,t=3", "stratum": "S3", "template": "S3-A1",
      "slots": {"M": 1, "V": "alpha-beta", "T": 3},
      "gold_facts": ["learn:2:1:alpha-beta:level-up:1", "ptype:2:1:3",
                     "learn:3:1:alpha-beta:level-up:0", "ptype:3:1:3"]}


def delivery(levels: list[list[str]]) -> Delivery:
    """A delivery whose search returns levels[0] and level i-1 the rest."""
    steps = tuple(Step(i - 1, f"call {i}", tuple(us), 10)
                  for i, us in enumerate(levels))
    units = tuple(dict.fromkeys(u for us in levels for u in us))
    return Delivery(units, 10 * len(levels), len(levels) - 1, False,
                    tuple(levels[0]) if levels else (), steps)


def test_read_labels_each_level(registry: Registry) -> None:
    gold = gold_from(S1, registry)
    every = sorted({sorted(us)[0] for us in gold.cover.values()})
    o = read(S1, delivery([every[:1], [], every[1:]]), registry, "q-1")
    assert o.sufficient and o.by_level == {"-1": False, "0": False, "1": True}
    assert o.cluster == "line:3" and o.deepest == 1
    partial = read(S1, delivery([every[:1]]), registry, "q-1")
    assert not partial.sufficient and partial.subtype == "missing-hop"


def test_read_s3_reports_members_and_hub_units(registry: Registry) -> None:
    hub = hub_units(S3, registry)
    assert hub and all("learned-by" in u for u in hub)
    o = read(S3, delivery([hub]), registry, "q-3", beyond=True)
    assert o.hub_units == (len(hub), len(hub)) and o.members is not None
    assert o.beyond_t_max and o.version == "alpha-beta" and o.cluster == "move:1"


def test_cluster_keys() -> None:
    assert cluster_key({"stratum": "S4", "template": "S4-B1",
                        "slots": {"X": 2, "V": "x-y", "L": 3},
                        "gold_facts": []}) == "pair:2:x-y"
    assert cluster_key({"stratum": "S0", "template": "S0-B1",
                        "slots": {"A": 1, "B": 2}, "gold_facts": []}) == "types:1:2"
    assert cluster_key({"stratum": "S0", "template": "S0-A3", "slots": {"M": 7},
                        "gold_facts": []}) == "move:7"
    assert cluster_key({"stratum": "S1", "template": "S1-A3", "slots": {"X": 5},
                        "gold_facts": ["evo:6:5"]}) == "line:5"
    assert cluster_key({"stratum": "S2", "template": "S2-A1",
                        "slots": {"X": 9, "M": 1, "V": "x-y"},
                        "gold_facts": []}) == "species:9"


def test_structural_zeros_carry_no_interval() -> None:
    assert rate(0, 30, structural=True) == {"n": 0, "of": 30,
                                             "note": "by construction"}
    assert "wilson95" in rate(3, 30)


def test_summary_and_report(registry: Registry) -> None:
    hub = hub_units(S3, registry)
    outcomes = [read(S3, delivery([hub]), registry, "q-a", beyond=True),
                read(S3, delivery([hub[:1]]), registry, "q-b"),
                read(S1, delivery([[]]), registry, "q-c")]
    s = summarize(outcomes)
    assert s["questions"] == 3 and s["clusters"] == 2
    assert s["sufficient"]["n"] == sum(o.sufficient for o in outcomes)
    r = report(outcomes)
    assert r["S3"]["questions"] == 2
    assert r["S3 beyond T_max"]["questions"] == 1
    assert r["S3 within T_max"]["questions"] == 1
    assert r["S1"]["sufficient"]["n"] == 0
    assert r["S1 S1-A1"]["questions"] == 1


def test_two_by_two() -> None:
    base = dict(question="q", stratum="S2", template="S2-A1", version="x-y",
                cluster="species:1", subtype=None)
    outs = [Outcome(sufficient=True, near_certain=True, **base),
            Outcome(sufficient=False, near_certain=True, **base),
            Outcome(sufficient=False, near_certain=False, **base)]
    assert two_by_two(outs) == {"sufficient, near-certain too": 1,
                                "sufficient only": 0, "near-certain only": 1,
                                "neither": 1}
