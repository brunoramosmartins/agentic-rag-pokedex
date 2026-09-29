"""PokéAPI reader: scope filters, English names, learnsets (fictional fixture)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_pokedex.world.pokeapi import (
    WorldTables,
    iter_learnsets,
    normalize_text,
    read_world,
)

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"


@pytest.fixture(scope="module")
def tables() -> WorldTables:
    return read_world(RAW)


def by_id(records: list[dict], key: str = "id") -> dict:
    return {r[key]: r for r in records}


def test_record_counts(tables: WorldTables) -> None:
    counts = {k: len(v) for k, v in vars(tables).items() if isinstance(v, list)}
    assert counts == {
        "types": 3,
        "efficacy": 9,
        "version_groups": 2,
        "versions": 3,
        "species": 4,
        "evolutions": 2,
        "pokemon": 6,
        "pokemon_types": 8,
        "abilities": 3,
        "pokemon_abilities": 8,
        "moves": 3,
        "flavor_texts": 2,
    }


def test_every_drop_is_counted(tables: WorldTables) -> None:
    list(iter_learnsets(RAW, tables))
    assert dict(tables.dropped) == {
        "types": 1,  # no efficacy rows
        "abilities": 1,  # not main series
        "pokemon_abilities": 1,  # points at the dropped ability
        "moves": 2,  # never learned; learned but of a non-battle type
        "flavor_texts": 1,  # not English
        "learnsets": 1,  # the non-battle-type move
    }


def test_types_are_the_ones_with_efficacy_rows(tables: WorldTables) -> None:
    assert sorted(t["identifier"] for t in tables.types) == ["ember", "moss", "tide"]
    assert {t["name"] for t in tables.types} == {"Ember", "Moss", "Tide"}


def test_efficacy_keeps_direction_and_factor(tables: WorldTables) -> None:
    rows = {(e["attacker"], e["defender"]): e["factor"] for e in tables.efficacy}
    assert rows[(1, 3)] == 200  # ember → moss
    assert rows[(3, 1)] == 50  # moss → ember


def test_names_are_english(tables: WorldTables) -> None:
    assert by_id(tables.species)[1]["name"] == "Sprig"
    assert by_id(tables.versions)[1]["name"] == "Alpha"


def test_version_group_name_joins_its_versions(tables: WorldTables) -> None:
    groups = by_id(tables.version_groups)
    assert groups[1]["name"] == "Alpha/Beta"
    assert groups[2]["name"] == "Gamma"
    assert groups[2]["generation"] == 2


def test_form_names(tables: WorldTables) -> None:
    pokemon = by_id(tables.pokemon)
    assert pokemon[3]["name"] == "Sproutree"  # default entry: species name
    assert pokemon[10001]["name"] == "Mega Blaze"  # form's own Pokémon name
    assert pokemon[10002]["name"] == "Sproutree (Tidal Form)"  # form name only
    assert pokemon[10001]["is_default"] is False
    assert pokemon[10001]["species_id"] == 4


def test_evolution_edges_point_to_the_parent(tables: WorldTables) -> None:
    edges = {(e["species_id"], e["from_species_id"]) for e in tables.evolutions}
    assert edges == {(2, 1), (3, 2)}


def test_hidden_ability_flag(tables: WorldTables) -> None:
    hidden = {
        (a["pokemon_id"], a["ability_id"])
        for a in tables.pokemon_abilities
        if a["hidden"]
    }
    assert hidden == {(1, 3), (3, 3)}


def test_moves_keep_type_power_and_category(tables: WorldTables) -> None:
    moves = by_id(tables.moves)
    assert set(moves) == {1, 2, 3}
    assert moves[1] == {
        "id": 1,
        "identifier": "vine-lash",
        "name": "Vine Lash",
        "type_id": 3,
        "power": 45,
        "category": "physical",
    }
    assert moves[3]["power"] is None
    assert moves[3]["category"] == "status"


def test_flavor_text_is_english_and_whitespace_collapsed(
    tables: WorldTables,
) -> None:
    texts = by_id(tables.flavor_texts, "key")
    assert texts["1:1"]["text"] == "A tiny seed that wakes at dawn."
    assert texts["4:3"]["text"] == "Its tail flickers in the rain."


def test_normalize_text_handles_form_feeds() -> None:
    assert normalize_text("a\nb\x0cc  d ") == "a b c d"


def test_learnsets(tables: WorldTables) -> None:
    rows = list(iter_learnsets(RAW, tables))
    assert len(rows) == 9
    keyed = {(r["pokemon_id"], r["move_id"], r["version_group"]): r for r in rows}
    # The same move at different levels in different version groups (S2 material).
    assert keyed[(1, 1, "alpha-beta")]["level"] == 1
    assert keyed[(1, 1, "gamma")]["level"] == 5
    # Level 0 is kept: "on evolution" in recent games.
    assert keyed[(3, 1, "alpha-beta")]["level"] == 0
    # Non-level-up methods carry no level.
    assert keyed[(3, 3, "alpha-beta")] == {
        "pokemon_id": 3,
        "move_id": 3,
        "version_group": "alpha-beta",
        "method": "machine",
        "level": None,
    }
    assert all(r["move_id"] != 5 for r in rows)
