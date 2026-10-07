"""The local explorer: name lookup in both namings."""

from __future__ import annotations

from agentic_pokedex.world.explore import find, page
from agentic_pokedex.world.index import Unit
from agentic_pokedex.world.twin import KINDS, TwinMap


def twin_map() -> TwinMap:
    names = {kind: {} for kind in KINDS}
    names["species"] = {"Sprig": "Molva"}
    names["pokemon"] = {"Sprig": "Molva", "Mega Sprig": "Tark Molva"}
    names["move"] = {"Vine Lash": "Kesso Dran"}
    return TwinMap(seed=0, names=names)


def test_find_by_real_or_twin_name_case_insensitive() -> None:
    assert find(twin_map(), "sprig") == [("species", "Sprig", "Molva")]
    assert find(twin_map(), "KESSO DRAN") == [("move", "Vine Lash", "Kesso Dran")]
    assert find(twin_map(), "Tark Molva") == [("pokemon", "Mega Sprig", "Tark Molva")]
    assert find(twin_map(), "nothing") == []


def test_page_filters_like_open_page() -> None:
    units = [
        Unit("species/1/profile", "Molva", "Profile", "p"),
        Unit(
            "species/1/learnset/level-up/x/0",
            "Molva",
            "Learnset · Method: level-up",
            "l",
        ),
        Unit("move/1/profile", "Kesso Dran", "Profile", "m"),
    ]
    assert [u.id for u in page(units, "Molva", None)] == [
        "species/1/profile", "species/1/learnset/level-up/x/0"
    ]
    assert [u.id for u in page(units, "Molva", "level-up")] == [
        "species/1/learnset/level-up/x/0"
    ]
    assert len(page(units, "Molva", "Matchups")) == 2  # no match: the whole page
