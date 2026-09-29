"""Examiner templates against a live Neo4j, on the fictional fixture world.

Wipes the database, like the other integration tests: runs only with
``NEO4J_TEST_ALLOW_RESET=1``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from agentic_pokedex.examiner.generate import check_scope, run_query
from agentic_pokedex.examiner.templates import LEARNS_TEMPLATES, QUERIES
from agentic_pokedex.world.load_graph import load_world

pytestmark = pytest.mark.integration

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"
FILTER = "WHERE r.version_group IN $scope"


@pytest.fixture(scope="module")
def driver() -> Iterator[Any]:
    if os.environ.get("NEO4J_TEST_ALLOW_RESET") != "1":
        pytest.skip("set NEO4J_TEST_ALLOW_RESET=1 to let tests wipe Neo4j")
    from agentic_pokedex.world.load_graph import connect

    with connect() as drv:
        load_world(drv, RAW)
        yield drv


def test_every_query_runs(driver: Any) -> None:
    for name in QUERIES:
        rows = run_query(driver, name, scope=["alpha-beta", "gamma"], moves=[1, 2])
        check_scope(rows, ["alpha-beta", "gamma"])


def test_learns_queries_stay_in_scope(driver: Any) -> None:
    for name in LEARNS_TEMPLATES:
        rows = run_query(driver, name, scope=["alpha-beta"])
        assert rows and {r["version_group"] for r in rows} == {"alpha-beta"}


def test_removing_the_scope_filter_is_caught(driver: Any) -> None:
    # The negative test: without its filter, a template draws rows from a group
    # outside the scope, and the generator's scope check refuses them.
    for name, query in LEARNS_TEMPLATES.items():
        assert FILTER in query, name
        unfiltered = query.replace(FILTER, "")
        records, _, _ = driver.execute_query(unfiltered, scope=["alpha-beta"])
        rows = [dict(r) for r in records]
        with pytest.raises(ValueError, match="outside the version scope"):
            check_scope(rows, ["alpha-beta"])


def test_final_form_lines(driver: Any) -> None:
    rows = run_query(driver, "S1_FINAL_FORM")
    lines = {r["anchor"]: r["line"] for r in rows}
    assert lines == {1: [1, 2, 3], 2: [2, 3]}


def test_next_form(driver: Any) -> None:
    rows = run_query(driver, "S1_NEXT_FORM")
    assert {(r["anchor"], r["next"]) for r in rows} == {(1, 2), (2, 3)}
