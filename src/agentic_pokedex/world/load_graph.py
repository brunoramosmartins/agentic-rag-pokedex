"""Load the world into Neo4j and report load statistics.

The graph is the examiner (ADR-007): questions, gold chains and step labels are
generated from it, and no arm ever queries it. It holds the **real** world; the
twin is a renaming layer applied later (``world/twin.py``).

Schema::

    (:Species {id, identifier, name, generation, evolution_chain_id,
               is_baby, is_legendary, is_mythical})
    (:Pokemon {id, identifier, name, is_default})-[:FORM_OF]->(:Species)
    (:Species)-[:EVOLVES_FROM]->(:Species)
    (:Pokemon)-[:HAS_TYPE {slot}]->(:Type {id, identifier, name})
    (:Type)-[:DAMAGE {factor}]->(:Type)          # attacker → defender, percent
    (:Pokemon)-[:HAS_ABILITY {slot, hidden}]->(:Ability {id, identifier, name})
    (:Move {id, identifier, name, power, category})-[:OF_TYPE]->(:Type)
    (:Pokemon)-[:LEARNS {version_group, method, level}]->(:Move)
    (:Version {id, identifier, name})-[:IN_GROUP]->
        (:VersionGroup {id, identifier, name, generation, order})
    (:Species)-[:HAS_FLAVOR]->(:FlavorText {key, text})-[:IN_VERSION]->(:Version)

A load **replaces** the whole database: it deletes every node, then writes the
world from ``data/raw/``. The Neo4j of ``docker-compose.yml`` is dedicated to
this project. Loading the same CSVs twice yields the same statistics.

Usage::

    python -m agentic_pokedex.world.load_graph
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterable, Iterator
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentic_pokedex.config import REPO_ROOT, load_env
from agentic_pokedex.world.download import DEFAULT_RAW_DIR, verify
from agentic_pokedex.world.pokeapi import (
    Record,
    WorldTables,
    iter_learnsets,
    read_world,
)

if TYPE_CHECKING:
    from neo4j import Driver

BATCH_SIZE = 5_000
DEFAULT_STATS_PATH = REPO_ROOT / "data" / "world" / "load_stats.json"

# --- Cypher: reset and schema ----------------------------------------------

DELETE_RELATIONSHIPS = """
MATCH ()-[r]->()
CALL (r) { DELETE r } IN TRANSACTIONS OF 50000 ROWS
"""

DELETE_NODES = """
MATCH (n)
CALL (n) { DELETE n } IN TRANSACTIONS OF 50000 ROWS
"""

CONSTRAINTS = (
    "CREATE CONSTRAINT species_id IF NOT EXISTS "
    "FOR (n:Species) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT pokemon_id IF NOT EXISTS "
    "FOR (n:Pokemon) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT type_id IF NOT EXISTS FOR (n:Type) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT move_id IF NOT EXISTS FOR (n:Move) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ability_id IF NOT EXISTS "
    "FOR (n:Ability) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT version_id IF NOT EXISTS "
    "FOR (n:Version) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT version_group_id IF NOT EXISTS "
    "FOR (n:VersionGroup) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT flavor_key IF NOT EXISTS "
    "FOR (n:FlavorText) REQUIRE n.key IS UNIQUE",
    "CREATE INDEX learns_version_group IF NOT EXISTS "
    "FOR ()-[r:LEARNS]-() ON (r.version_group)",
)

# --- Cypher: nodes ----------------------------------------------------------

CREATE_TYPES = """
UNWIND $rows AS row
CREATE (:Type {id: row.id, identifier: row.identifier, name: row.name})
"""

CREATE_VERSION_GROUPS = """
UNWIND $rows AS row
CREATE (:VersionGroup {id: row.id, identifier: row.identifier, name: row.name,
                       generation: row.generation, order: row.order})
"""

CREATE_VERSIONS = """
UNWIND $rows AS row
MATCH (g:VersionGroup {id: row.version_group_id})
CREATE (:Version {id: row.id, identifier: row.identifier, name: row.name})
       -[:IN_GROUP]->(g)
"""

CREATE_SPECIES = """
UNWIND $rows AS row
CREATE (:Species {id: row.id, identifier: row.identifier, name: row.name,
                  generation: row.generation,
                  evolution_chain_id: row.evolution_chain_id,
                  is_baby: row.is_baby, is_legendary: row.is_legendary,
                  is_mythical: row.is_mythical})
"""

CREATE_POKEMON = """
UNWIND $rows AS row
MATCH (s:Species {id: row.species_id})
CREATE (:Pokemon {id: row.id, identifier: row.identifier, name: row.name,
                  is_default: row.is_default})-[:FORM_OF]->(s)
"""

CREATE_ABILITIES = """
UNWIND $rows AS row
CREATE (:Ability {id: row.id, identifier: row.identifier, name: row.name})
"""

CREATE_MOVES = """
UNWIND $rows AS row
MATCH (t:Type {id: row.type_id})
CREATE (:Move {id: row.id, identifier: row.identifier, name: row.name,
               power: row.power, category: row.category})-[:OF_TYPE]->(t)
"""

CREATE_FLAVOR_TEXTS = """
UNWIND $rows AS row
MATCH (s:Species {id: row.species_id})
MATCH (v:Version {id: row.version_id})
CREATE (s)-[:HAS_FLAVOR]->
       (:FlavorText {key: row.key, text: row.text})
       -[:IN_VERSION]->(v)
"""

# --- Cypher: relationships --------------------------------------------------

CREATE_EFFICACY = """
UNWIND $rows AS row
MATCH (a:Type {id: row.attacker})
MATCH (d:Type {id: row.defender})
CREATE (a)-[:DAMAGE {factor: row.factor}]->(d)
"""

CREATE_EVOLUTIONS = """
UNWIND $rows AS row
MATCH (s:Species {id: row.species_id})
MATCH (p:Species {id: row.from_species_id})
CREATE (s)-[:EVOLVES_FROM]->(p)
"""

CREATE_POKEMON_TYPES = """
UNWIND $rows AS row
MATCH (p:Pokemon {id: row.pokemon_id})
MATCH (t:Type {id: row.type_id})
CREATE (p)-[:HAS_TYPE {slot: row.slot}]->(t)
"""

CREATE_POKEMON_ABILITIES = """
UNWIND $rows AS row
MATCH (p:Pokemon {id: row.pokemon_id})
MATCH (a:Ability {id: row.ability_id})
CREATE (p)-[:HAS_ABILITY {slot: row.slot, hidden: row.hidden}]->(a)
"""

CREATE_LEARNSETS = """
UNWIND $rows AS row
MATCH (p:Pokemon {id: row.pokemon_id})
MATCH (m:Move {id: row.move_id})
CREATE (p)-[:LEARNS {version_group: row.version_group, method: row.method,
                     level: row.level}]->(m)
"""

# --- Cypher: statistics -----------------------------------------------------

NODE_COUNTS = """
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label
"""

RELATIONSHIP_COUNTS = """
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY type
"""

LEARNS_BY_VERSION_GROUP = """
MATCH ()-[r:LEARNS]->()
RETURN r.version_group AS version_group, count(*) AS n ORDER BY version_group
"""


def connect() -> Driver:
    """Open a driver from ``NEO4J_URI``, ``NEO4J_USER``, ``NEO4J_PASSWORD``.

    ``.env`` fills in what the environment lacks (``config.load_env``).
    Requires the ``graph`` extra.
    """
    from neo4j import GraphDatabase

    load_env()
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD is not set (see .env.example)")
    return GraphDatabase.driver(uri, auth=(user, password))


def batched(rows: Iterable[Record], size: int = BATCH_SIZE) -> Iterator[list[Record]]:
    """Split an iterable of records into lists of at most ``size``."""
    iterator = iter(rows)
    while batch := list(islice(iterator, size)):
        yield batch


def _write(driver: Driver, query: str, rows: Iterable[Record]) -> None:
    for batch in batched(rows):
        driver.execute_query(query, rows=batch)


def reset(driver: Driver) -> None:
    """Delete every relationship and node, then create the schema."""
    with driver.session() as session:
        session.run(DELETE_RELATIONSHIPS).consume()
        session.run(DELETE_NODES).consume()
    for statement in CONSTRAINTS:
        driver.execute_query(statement)


def load_world(driver: Driver, raw_dir: Path) -> WorldTables:
    """Replace the database with the world read from ``raw_dir``.

    Args:
        driver: An open Neo4j driver.
        raw_dir: Directory with the manifest CSVs.

    Returns:
        The records written, with the dropped-row counts (learnsets included).
    """
    tables = read_world(raw_dir)
    reset(driver)
    # Nodes first, in dependency order; then relationships.
    _write(driver, CREATE_TYPES, tables.types)
    _write(driver, CREATE_VERSION_GROUPS, tables.version_groups)
    _write(driver, CREATE_VERSIONS, tables.versions)
    _write(driver, CREATE_SPECIES, tables.species)
    _write(driver, CREATE_POKEMON, tables.pokemon)
    _write(driver, CREATE_ABILITIES, tables.abilities)
    _write(driver, CREATE_MOVES, tables.moves)
    _write(driver, CREATE_FLAVOR_TEXTS, tables.flavor_texts)
    _write(driver, CREATE_EFFICACY, tables.efficacy)
    _write(driver, CREATE_EVOLUTIONS, tables.evolutions)
    _write(driver, CREATE_POKEMON_TYPES, tables.pokemon_types)
    _write(driver, CREATE_POKEMON_ABILITIES, tables.pokemon_abilities)
    _write(driver, CREATE_LEARNSETS, iter_learnsets(raw_dir, tables))
    return tables


def graph_stats(driver: Driver) -> dict[str, Any]:
    """Count nodes per label, relationships per type, learnsets per group."""

    def table(query: str, key: str) -> dict[str, int]:
        records, _, _ = driver.execute_query(query)
        return {r[key]: r["n"] for r in records}

    return {
        "nodes": table(NODE_COUNTS, "label"),
        "relationships": table(RELATIONSHIP_COUNTS, "type"),
        "learns_by_version_group": table(LEARNS_BY_VERSION_GROUP, "version_group"),
    }


def expected_counts(tables: WorldTables, learnsets: int) -> dict[str, dict[str, int]]:
    """What the graph must hold after a load of ``tables``."""
    return {
        "nodes": {
            "Ability": len(tables.abilities),
            "FlavorText": len(tables.flavor_texts),
            "Move": len(tables.moves),
            "Pokemon": len(tables.pokemon),
            "Species": len(tables.species),
            "Type": len(tables.types),
            "Version": len(tables.versions),
            "VersionGroup": len(tables.version_groups),
        },
        "relationships": {
            "DAMAGE": len(tables.efficacy),
            "EVOLVES_FROM": len(tables.evolutions),
            "FORM_OF": len(tables.pokemon),
            "HAS_ABILITY": len(tables.pokemon_abilities),
            "HAS_FLAVOR": len(tables.flavor_texts),
            "HAS_TYPE": len(tables.pokemon_types),
            "IN_GROUP": len(tables.versions),
            "IN_VERSION": len(tables.flavor_texts),
            "LEARNS": learnsets,
            "OF_TYPE": len(tables.moves),
        },
    }


def check_load(stats: dict[str, Any], tables: WorldTables) -> list[str]:
    """Compare graph counts with the records; return one line per mismatch.

    A ``MATCH`` that finds no endpoint silently writes nothing, so a load is
    only trusted when every count equals its record count.
    """
    learnsets = sum(stats["learns_by_version_group"].values())
    problems = []
    for section, expected in expected_counts(tables, learnsets).items():
        for name, n in expected.items():
            got = stats[section].get(name, 0)
            if got != n:
                problems.append(f"{section}.{name}: graph {got}, records {n}")
        for name in set(stats[section]) - set(expected):
            problems.append(f"{section}.{name}: unexpected in graph")
    return problems


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Load the world into Neo4j.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--stats-out", type=Path, default=DEFAULT_STATS_PATH)
    parser.add_argument(
        "--skip-hash-check", action="store_true",
        help="load CSVs that are not the pinned PokéAPI files (fixtures only)",
    )
    args = parser.parse_args(argv)

    if not args.skip_hash_check:
        bad = {n: s for n, s in verify(args.raw_dir).items() if s != "ok"}
        if bad:
            print("Raw CSVs do not match the manifest; run world.download first:")
            for name, s in bad.items():
                print(f"  {s.upper():8} {name}")
            return 1

    with connect() as driver:
        tables = load_world(driver, args.raw_dir)
        stats = graph_stats(driver)
    stats["dropped_rows"] = dict(sorted(tables.dropped.items()))
    problems = check_load(stats, tables)

    for section in ("nodes", "relationships", "dropped_rows"):
        print(f"{section}:")
        for name, n in stats[section].items():
            print(f"  {name:20} {n:>9,}")
    print(f"LEARNS rows: {sum(stats['learns_by_version_group'].values()):,} "
          f"across {len(stats['learns_by_version_group'])} version groups")
    for line in problems:
        print("  MISMATCH", line)
    print("LOAD CHECK:", "PASS" if not problems else "FAIL")

    args.stats_out.parent.mkdir(parents=True, exist_ok=True)
    args.stats_out.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Statistics written to {args.stats_out}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
