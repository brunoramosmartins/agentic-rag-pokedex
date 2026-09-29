"""Graph load against a live Neo4j, on the fictional fixture world.

A load replaces the whole database, so these tests run only when
``NEO4J_TEST_ALLOW_RESET=1`` is set (CI sets it). Never set it against a
database holding the real world you want to keep.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from agentic_pokedex.world.load_graph import check_load, graph_stats, load_world

pytestmark = pytest.mark.integration

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"


@pytest.fixture(scope="module")
def driver() -> Iterator[Any]:
    if os.environ.get("NEO4J_TEST_ALLOW_RESET") != "1":
        pytest.skip("set NEO4J_TEST_ALLOW_RESET=1 to let tests wipe Neo4j")
    from agentic_pokedex.world.load_graph import connect

    with connect() as drv:
        yield drv


@pytest.fixture(scope="module")
def loaded(driver: Any) -> dict[str, Any]:
    tables = load_world(driver, RAW)
    return {"tables": tables, "stats": graph_stats(driver)}


def single(driver: Any, query: str, **params: Any) -> Any:
    records, _, _ = driver.execute_query(query, **params)
    assert len(records) == 1
    return records[0]


def test_every_record_reaches_the_graph(loaded: dict[str, Any]) -> None:
    assert check_load(loaded["stats"], loaded["tables"]) == []
    assert loaded["stats"]["learns_by_version_group"] == {
        "alpha-beta": 5,
        "gamma": 4,
    }


def test_reload_is_idempotent(driver: Any, loaded: dict[str, Any]) -> None:
    load_world(driver, RAW)
    assert graph_stats(driver) == loaded["stats"]


def test_hidden_ability_of_the_final_form(driver: Any, loaded: dict) -> None:
    # The S1 shape: final form of a chain → its hidden ability.
    record = single(
        driver,
        """
        MATCH (base:Species {name: $name})
        MATCH (final:Species)-[:EVOLVES_FROM*]->(base)
        WHERE NOT ()-[:EVOLVES_FROM]->(final)
        MATCH (p:Pokemon {is_default: true})-[:FORM_OF]->(final)
        MATCH (p)-[:HAS_ABILITY {hidden: true}]->(a:Ability)
        RETURN final.name AS final, a.name AS ability
        """,
        name="Sprig",
    )
    assert (record["final"], record["ability"]) == ("Sproutree", "Undertow")


def test_learn_level_depends_on_version_group(driver: Any, loaded: dict) -> None:
    # The S2 shape: the same (Pokémon, move) at different levels per group.
    records, _, _ = driver.execute_query(
        """
        MATCH (:Pokemon {name: 'Sprig'})-[r:LEARNS {method: 'level-up'}]->
              (:Move {name: 'Vine Lash'})
        RETURN r.version_group AS vg, r.level AS level ORDER BY vg
        """
    )
    assert [(r["vg"], r["level"]) for r in records] == [("alpha-beta", 1), ("gamma", 5)]


def test_type_efficacy_direction(driver: Any, loaded: dict) -> None:
    record = single(
        driver,
        "MATCH (:Type {name: 'Ember'})-[d:DAMAGE]->(:Type {name: 'Moss'}) "
        "RETURN d.factor AS factor",
    )
    assert record["factor"] == 200


def test_flavor_text_is_tied_to_species_and_version(
    driver: Any, loaded: dict
) -> None:
    record = single(
        driver,
        """
        MATCH (:Species {name: 'Blaze'})-[:HAS_FLAVOR]->(f)-[:IN_VERSION]->(v)
        RETURN f.text AS text, v.name AS version
        """,
    )
    assert (record["text"], record["version"]) == (
        "Its tail flickers in the rain.",
        "Gamma",
    )


def test_moves_without_power_have_no_power_property(
    driver: Any, loaded: dict
) -> None:
    record = single(driver, "MATCH (m:Move {name: 'Soak'}) RETURN m.power AS power")
    assert record["power"] is None
