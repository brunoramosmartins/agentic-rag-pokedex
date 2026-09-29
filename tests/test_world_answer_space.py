"""Answer spaces: admissible values, uniform chance, modal share."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from agentic_pokedex.world.answer_space import Slot, answer_slots, render_markdown
from agentic_pokedex.world.pokeapi import iter_learnsets, read_world
from agentic_pokedex.world.render import build_world

FIXTURE_RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"
FIXTURE_SCOPE = ("alpha-beta", "gamma")


@pytest.fixture(scope="module")
def slots() -> dict[str, Slot]:
    tables = read_world(FIXTURE_RAW)
    rows = list(iter_learnsets(FIXTURE_RAW, tables))
    world = build_world(tables, rows, FIXTURE_SCOPE)
    return {s.name: s for s in answer_slots(world)}


def test_slot_measures() -> None:
    slot = Slot("x", "things", Counter({"a": 6, "b": 3, "c": 1}))
    assert (slot.n, slot.mode) == (3, "a")
    assert slot.uniform == pytest.approx(1 / 3)
    assert slot.modal_share == pytest.approx(0.6)
    assert slot.small


def test_ties_pick_a_stable_mode() -> None:
    assert Slot("x", "p", Counter({2: 3, 1: 3})).mode == 1


def test_large_slots_are_open() -> None:
    assert not Slot("x", "p", Counter(range(21))).small
    assert Slot("x", "p", Counter(range(20))).small


@pytest.mark.parametrize(
    ("name", "n", "modal_share"),
    [
        ("type of a Pokémon (primary)", 3, 3 / 6),  # moss ×3 of 6 entries
        ("type of a Pokémon (any slot)", 3, 3 / 8),
        ("type of a move", 3, 1 / 3),
        ("move category", 3, 1 / 3),
        ("move power", 2, 1 / 2),
        ("damage factor", 2, 6 / 9),  # 50% ×6, 200% ×3
        ("learn level", 3, 3 / 5),  # level 0 and multi-level pairs excluded
        ("learn level (S2-usable)", 3, 2 / 4),
        ("ability", 3, 3 / 8),
        ("hidden ability", 1, 1.0),
        ("species", 4, 1 / 4),
        ("move", 3, 1 / 3),
    ],
)
def test_fixture_slots(
    slots: dict[str, Slot], name: str, n: int, modal_share: float
) -> None:
    assert slots[name].n == n
    assert slots[name].modal_share == pytest.approx(modal_share)


def test_render_markdown(slots: dict[str, Slot]) -> None:
    text = render_markdown(slots.values())
    assert text.startswith("| Slot | Population |")
    assert "| damage factor | type pairs (9) | 2 | 50.0% | 66.7% | small |" in text
