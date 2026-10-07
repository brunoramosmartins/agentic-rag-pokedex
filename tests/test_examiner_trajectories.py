"""Trajectory-level check: shortest page reading, one-search flag, witnesses."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_pokedex.examiner.reachability import T_MAX
from agentic_pokedex.examiner.trajectories import (
    EVIDENCE_BUDGET,
    Measure,
    Window,
    WindowCache,
    measure,
    one_search_could,
    page_windows,
    realize_witnesses,
    shortest,
    summarize,
)
from agentic_pokedex.labeling.sufficiency import gold_from, label_state
from agentic_pokedex.tools.open_page import Pages
from agentic_pokedex.world.index import Unit, load_units
from agentic_pokedex.world.registry import Registry

DEV = [
    {"id": "S0-A1:x=1", "stratum": "S0", "template": "S0-A1",
     "gold_facts": ["pability:1:3:hidden"], "twin_answer": "Undertow"},
    {"id": "S1-A1:x=1", "stratum": "S1", "template": "S1-A1",
     "twin_answer": "Undertow",
     "gold_facts": ["evo:2:1", "evo:3:2", "evoend:3", "pability:3:3:hidden"]},
    {"id": "S2-A1:p=4,m=2,v=gamma", "stratum": "S2", "template": "S2-A1",
     "twin_answer": "7", "gold_facts": ["learn:4:2:gamma:level-up:7"],
     "distractor_facts": ["learn:4:2:alpha-beta:level-up:1"]},
    {"id": "S3-A1:m=1,v=alpha-beta,t=3", "stratum": "S3", "template": "S3-A1",
     "twin_answer": "",
     "gold_facts": ["learn:2:1:alpha-beta:level-up:1", "ptype:2:1:3",
                    "learn:3:1:alpha-beta:level-up:0", "ptype:3:1:3"]},
    {"id": "S4-A1:p=1,m=1,v=alpha-beta", "stratum": "S4", "template": "S4-A1",
     "twin_answer": "", "gold_facts": ["learn:1:1:alpha-beta:level-up:1"],
     "distractor_facts": ["learn:1:1:gamma:level-up:5"]},
]


def chars(text: str) -> int:
    """A test token counter: one token per four characters."""
    return len(text) // 4


@pytest.fixture(scope="module")
def registry(fixture_world_dir: Path) -> Registry:
    return Registry.load(fixture_world_dir / "registry.json")


@pytest.fixture(scope="module")
def units(fixture_world_dir: Path, registry: Registry) -> list[Unit]:
    return load_units(fixture_world_dir / "pages" / "real.jsonl", registry)


@pytest.fixture(scope="module")
def texts(units: list[Unit]) -> dict[str, str]:
    return {u.id: u.text for u in units}


@pytest.fixture(scope="module")
def cache(units: list[Unit]) -> WindowCache:
    return WindowCache(Pages(units), chars)


def record(rid: str) -> dict:
    return next(r for r in DEV if r["id"] == rid)


# --- Windows -------------------------------------------------------------------


def page(n: int, size: int = 40, sections: tuple[str, ...] = ("A", "B")) -> list[Unit]:
    return [Unit(f"u{i}", "P", sections[i % len(sections)], "x" * size)
            for i in range(n)]


def test_windows_read_every_selection_from_every_offset() -> None:
    windows = page_windows(page(4), chars, cap=25)  # 10 tokens a unit, 2 a call
    sets = {w.units for w in windows}
    assert frozenset({"u0", "u1"}) in sets  # whole page from the top
    assert frozenset({"u0", "u2"}) in sets  # section "A" from the top
    assert frozenset({"u3"}) in sets  # the last unit, from its offset
    assert all(w.tokens <= 25 or len(w.units) == 1 for w in windows)


def test_windows_keep_the_cheapest_call_per_unit_set() -> None:
    windows = page_windows(page(2, sections=("A",)), chars, cap=100)
    # Whole page and section "A" select the same units: one window each.
    assert len({w.units for w in windows}) == len(windows)


def test_window_call_text() -> None:
    w = Window("Kedros", "Profile", 2, frozenset({"u"}), 10)
    assert w.call() == "open_page('Kedros', section='Profile', offset=2)"
    assert Window("Kedros", None, 0, frozenset(), 0).call() == "open_page('Kedros')"


# --- Shortest page reading -----------------------------------------------------


def test_s0_takes_one_call(registry: Registry, cache: WindowCache) -> None:
    best = shortest(gold_from(record("S0-A1:x=1"), registry), cache)
    assert best.calls == 1 and len(best.windows) == 1
    assert best.tokens == best.windows[0].tokens


def test_s1_reads_one_page_per_hop(registry: Registry, cache: WindowCache) -> None:
    # Profiles link forward only: the anchor, the middle form and the final
    # form each state one fact of the chain.
    gold = gold_from(record("S1-A1:x=1"), registry)
    best = shortest(gold, cache)
    assert best.calls == 3
    seen = frozenset().union(*(w.units for w in best.windows))
    assert label_state(gold, sorted(seen)).sufficient
    assert len({w.title for w in best.windows}) == 3


def test_the_shortest_reading_is_sufficient_on_every_stratum(
    registry: Registry, cache: WindowCache,
) -> None:
    for r in DEV:
        if r["stratum"] == "S4":
            continue
        gold = gold_from(r, registry)
        best = shortest(gold, cache)
        assert best.calls is not None, r["id"]
        assert best.calls == len(best.windows)
        seen = frozenset().union(*(w.units for w in best.windows))
        assert label_state(gold, sorted(seen)).sufficient, r["id"]
        assert best.tokens == sum(w.tokens for w in best.windows)


def test_no_shorter_reading_exists(registry: Registry, cache: WindowCache) -> None:
    # Exactness: no single window of the S1 question's pages is sufficient.
    gold = gold_from(record("S1-A1:x=1"), registry)
    relevant = {u for us in gold.cover.values() for u in us}
    assert not any(label_state(gold, sorted(w.units)).sufficient
                   for w in cache.touching(relevant))


def test_beyond_the_search_depth(registry: Registry, cache: WindowCache) -> None:
    best = shortest(gold_from(record("S1-A1:x=1"), registry), cache, depth=2)
    assert best.calls is None and best.windows == ()


def test_a_tighter_cap_takes_more_calls(registry: Registry, units: list[Unit]) -> None:
    gold = gold_from(record("S3-A1:m=1,v=alpha-beta,t=3"), registry)
    wide = shortest(gold, WindowCache(Pages(units), chars, cap=10_000))
    narrow = shortest(gold, WindowCache(Pages(units), chars, cap=1))
    assert wide.calls is not None and narrow.calls is not None
    assert narrow.calls >= wide.calls


def test_s4_is_never_sufficient(
    registry: Registry, cache: WindowCache, texts: dict,
) -> None:
    m = measure(record("S4-A1:p=1,m=1,v=alpha-beta"), registry, cache, texts)
    assert m.never and m.calls is None and not m.one_search


# --- One search ------------------------------------------------------------------


def test_one_search_could_hold_a_short_chain(registry: Registry, texts: dict) -> None:
    gold = gold_from(record("S1-A1:x=1"), registry)
    assert one_search_could(gold, texts, chars, cap=10_000)
    assert not one_search_could(gold, texts, chars, cap=1)
    assert not one_search_could(gold, texts, chars, cap=10_000, max_k=1)


def test_one_search_always_holds_a_single_unit(registry: Registry, texts: dict) -> None:
    gold = gold_from(record("S0-A1:x=1"), registry)
    assert one_search_could(gold, texts, chars, cap=1)


# --- Witnesses -------------------------------------------------------------------


def test_every_code_is_realized_by_calls(
    registry: Registry, texts: dict, cache: WindowCache,
) -> None:
    by_id = {r["id"]: r for r in DEV}
    found = realize_witnesses(DEV, registry, texts, cache)
    assert all(r is not None for r in found.values()), found
    for code, r in found.items():
        gold = gold_from(by_id[r.question], registry)
        seen = frozenset().union(*(w.units for w in r.windows))
        lab = label_state(gold, sorted(seen))
        text = lab.state + (f" ({lab.subtype})" if lab.subtype else "")
        assert text == r.label, code
    assert len(found["never-reached"].windows) == T_MAX
    assert found["over-search"].label == "sufficient"


# --- Summaries ---------------------------------------------------------------------


def test_summary_counts() -> None:
    ms = [
        Measure("S0-A1", "S0", 1, 30, True, False),
        Measure("S3-A1", "S3", 7, 3_000, False, False),
        Measure("S3-A1", "S3", None, None, False, False),
        Measure("S3-A1", "S3", 2, EVIDENCE_BUDGET + 1, False, False),
        Measure("S4-A1", "S4", None, None, False, True),
    ]
    s = summarize(ms)
    assert s["questions"] == 5 and s["never_sufficient"] == 1
    assert s["one_call"] == 1 and s["one_search_could"] == 1
    assert s["beyond_t_max"] == 2  # 7 calls, and none found within the depth
    assert s["beyond_b"] == 1
    assert s["calls"] == {1: 1, 2: 1, 7: 1}
