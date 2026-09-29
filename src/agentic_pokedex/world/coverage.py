"""Learnset coverage report: which base version groups make the world.

The version scope is frozen from measured coverage, not preference. What the
choice must buy is stratum S2 (wrong version): a question "at what level does X
learn Y in V?" whose near-certain distractor, the same learnset in another
version group, gives a **different** level. Adjacent generations barely differ
(G1, ``docs/data-sources.md``), so the groups must span generations.

Definitions (level-up moves of default Pokémon entries only; forms are left to
other templates):

- A **pair** is (Pokémon, move). Its **levels** in a group are every level-up
  level listed for it there.
- A pair is **answerable** in a group when it has exactly one level and that
  level is ≥ 1. Level 0 ("on evolution") and pairs listed at several levels
  would make the answer ambiguous.
- A pair is **S2-usable** for group ``g`` within a chosen set ``G`` when it is
  answerable in ``g``, at least one other group of ``G`` lists it (the
  distractor exists), and no other group of ``G`` lists it at ``g``'s level (a
  third version cannot answer it correctly by accident).

The report reads the graph by default; ``--source csv`` recomputes it from the
raw CSVs, and the two must agree.

Usage::

    python -m agentic_pokedex.world.coverage                 # from Neo4j
    python -m agentic_pokedex.world.coverage --source csv    # from data/raw/
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.world.download import DEFAULT_RAW_DIR
from agentic_pokedex.world.pokeapi import iter_learnsets, read_world

if TYPE_CHECKING:
    from neo4j import Driver

CANDIDATE_GROUPS: tuple[str, ...] = (
    "x-y",
    "omega-ruby-alpha-sapphire",
    "sun-moon",
    "ultra-sun-ultra-moon",
    "sword-shield",
    "brilliant-diamond-shining-pearl",
    "scarlet-violet",
)
"""Base groups with near-complete learnsets (G1, ``docs/data-sources.md``)."""

COMBINATION_SIZES = (3, 4)
DEFAULT_OUT = REPO_ROOT / "data" / "world" / "coverage.md"

Pair = tuple[int, int]
LevelTable = dict[str, dict[Pair, frozenset[int]]]
"""Version group → pair → set of level-up levels."""

LEVEL_UP_ROWS = """
MATCH (p:Pokemon {is_default: true})-[r:LEARNS {method: 'level-up'}]->(m:Move)
WHERE r.version_group IN $groups
RETURN p.id AS pokemon_id, m.id AS move_id, r.version_group AS version_group,
       r.level AS level
"""

GROUP_GENERATIONS = """
MATCH (g:VersionGroup) RETURN g.identifier AS identifier, g.generation AS generation
"""


# --- Reading ----------------------------------------------------------------


def level_table(rows: Iterable[Mapping[str, Any]], groups: Sequence[str]) -> LevelTable:
    """Collect the levels of every pair per group.

    Args:
        rows: ``{pokemon_id, move_id, version_group, level}`` level-up rows of
            default Pokémon entries.
        groups: Groups to keep; each gets an entry even if it has no rows.

    Returns:
        Group → pair → levels.
    """
    collected: dict[str, dict[Pair, set[int]]] = {g: defaultdict(set) for g in groups}
    for row in rows:
        group = row["version_group"]
        if group in collected:
            pair = (row["pokemon_id"], row["move_id"])
            collected[group][pair].add(row["level"])
    return {
        g: {pair: frozenset(levels) for pair, levels in pairs.items()}
        for g, pairs in collected.items()
    }


def rows_from_graph(driver: Driver, groups: Sequence[str]) -> list[dict[str, Any]]:
    """Level-up rows of default Pokémon entries, read from Neo4j."""
    records, _, _ = driver.execute_query(LEVEL_UP_ROWS, groups=list(groups))
    return [dict(r) for r in records]


def generations_from_graph(driver: Driver) -> dict[str, int]:
    """Version group identifier → generation, read from Neo4j."""
    records, _, _ = driver.execute_query(GROUP_GENERATIONS)
    return {r["identifier"]: r["generation"] for r in records}


def rows_from_csv(raw_dir: Path, groups: Sequence[str]) -> tuple[list[dict], dict]:
    """The same rows and generations, recomputed from the raw CSVs."""
    tables = read_world(raw_dir)
    defaults = {p["id"] for p in tables.pokemon if p["is_default"]}
    wanted = set(groups)
    rows = [
        r
        for r in iter_learnsets(raw_dir, tables)
        if r["method"] == "level-up"
        and r["pokemon_id"] in defaults
        and r["version_group"] in wanted
    ]
    generations = {g["identifier"]: g["generation"] for g in tables.version_groups}
    return rows, generations


# --- Measures ---------------------------------------------------------------


def answerable_level(levels: frozenset[int] | None) -> int | None:
    """The single level of an answerable pair, else ``None``."""
    if levels is None or len(levels) != 1:
        return None
    (level,) = levels
    return level if level >= 1 else None


def s2_usable(table: LevelTable, chosen: Sequence[str], group: str) -> set[Pair]:
    """Pairs of ``group`` that can carry an S2 question within ``chosen``."""
    others = [h for h in chosen if h != group]
    usable: set[Pair] = set()
    for pair, levels in table[group].items():
        level = answerable_level(levels)
        if level is None:
            continue
        listed = [table[h][pair] for h in others if pair in table[h]]
        if listed and all(level not in lv for lv in listed):
            usable.add(pair)
    return usable


@dataclass(frozen=True)
class GroupRow:
    """Coverage of one version group."""

    group: str
    generation: int
    pokemon: int
    pairs: int
    answerable: int


@dataclass(frozen=True)
class PairwiseRow:
    """Level agreement between two groups on the pairs answerable in both."""

    a: str
    b: str
    shared: int
    differ: int

    @property
    def rate(self) -> float:
        """Share of shared pairs whose level differs."""
        return self.differ / self.shared if self.shared else 0.0


@dataclass(frozen=True)
class CombinationRow:
    """S2 material and species coverage of one candidate set."""

    groups: tuple[str, ...]
    s2_per_group: tuple[int, ...]
    pokemon_all: int
    pokemon_any: int

    @property
    def s2_total(self) -> int:
        """S2-usable pairs summed over the set's groups."""
        return sum(self.s2_per_group)

    @property
    def s2_min(self) -> int:
        """S2-usable pairs of the set's weakest group."""
        return min(self.s2_per_group)


def group_rows(table: LevelTable, generations: Mapping[str, int]) -> list[GroupRow]:
    """One coverage row per group, in the table's order."""
    rows = []
    for group, pairs in table.items():
        rows.append(
            GroupRow(
                group=group,
                generation=generations[group],
                pokemon=len({p for p, _ in pairs}),
                pairs=len(pairs),
                answerable=sum(1 for lv in pairs.values() if answerable_level(lv)),
            )
        )
    return rows


def pairwise_rows(table: LevelTable) -> list[PairwiseRow]:
    """Level agreement for every two groups of the table."""
    rows = []
    for a, b in combinations(table, 2):
        shared = differ = 0
        for pair, levels in table[a].items():
            la, lb = answerable_level(levels), answerable_level(table[b].get(pair))
            if la is None or lb is None:
                continue
            shared += 1
            differ += la != lb
        rows.append(PairwiseRow(a, b, shared, differ))
    return rows


def combination_rows(
    table: LevelTable,
    generations: Mapping[str, int],
    sizes: Sequence[int] = COMBINATION_SIZES,
    distinct_generations: bool = True,
) -> list[CombinationRow]:
    """Every candidate set of the given sizes, most S2 material first.

    Args:
        table: Levels per group.
        generations: Group → generation.
        sizes: Set sizes to enumerate.
        distinct_generations: Keep only sets whose groups all come from
            different generations.

    Returns:
        Rows sorted by total S2-usable pairs, then by the weakest group.
    """
    rows = []
    for size in sizes:
        for chosen in combinations(table, size):
            gens = [generations[g] for g in chosen]
            if distinct_generations and len(set(gens)) < size:
                continue
            per_pokemon = [{p for p, _ in table[g]} for g in chosen]
            rows.append(
                CombinationRow(
                    groups=chosen,
                    s2_per_group=tuple(
                        len(s2_usable(table, chosen, g)) for g in chosen
                    ),
                    pokemon_all=len(set.intersection(*per_pokemon)),
                    pokemon_any=len(set.union(*per_pokemon)),
                )
            )
    return sorted(rows, key=lambda r: (-r.s2_total, -r.s2_min, r.groups))


# --- Report -----------------------------------------------------------------


def render_markdown(
    table: LevelTable, generations: Mapping[str, int], source: str
) -> str:
    """The coverage report as Markdown: groups, pairwise agreement, sets."""
    out = [
        "## Learnset coverage by version group",
        "",
        f"Source: {source}. Level-up moves of default Pokémon entries. A pair is "
        "(Pokémon, move); *answerable* = one level, ≥ 1, in that group.",
        "",
        "| Version group | Gen | Pokémon | Pairs | Answerable |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in group_rows(table, generations):
        out.append(
            f"| {r.group} | {r.generation} | {r.pokemon:,} | {r.pairs:,} "
            f"| {r.answerable:,} |"
        )

    out += [
        "",
        "### Level differences between two groups",
        "",
        "Pairs answerable in both groups, and how many have a different level.",
        "",
        "| Group A | Group B | Shared | Level differs | Rate |",
        "|---|---|---:|---:|---:|",
    ]
    for r in sorted(pairwise_rows(table), key=lambda r: r.rate):
        out.append(
            f"| {r.a} | {r.b} | {r.shared:,} | {r.differ:,} | {r.rate:.0%} |"
        )

    out += [
        "",
        "### Candidate sets (one group per generation)",
        "",
        "S2-usable pairs per group within the set (answerable in the group, "
        "listed in another group of the set, at a different level in every "
        "group that lists it). *Pokémon in all* / *in any*: default entries "
        "with a level-up learnset in every / some group of the set.",
        "",
        "| Groups | S2-usable per group | Total | Weakest | Pokémon in all "
        "| Pokémon in any |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in combination_rows(table, generations):
        per_group = " · ".join(f"{n:,}" for n in r.s2_per_group)
        out.append(
            f"| {', '.join(r.groups)} | {per_group} | {r.s2_total:,} "
            f"| {r.s2_min:,} | {r.pokemon_all:,} | {r.pokemon_any:,} |"
        )
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Learnset coverage report.")
    parser.add_argument("--source", choices=("graph", "csv"), default="graph")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    if args.source == "graph":
        from agentic_pokedex.world.load_graph import connect

        with connect() as driver:
            rows = rows_from_graph(driver, CANDIDATE_GROUPS)
            generations = generations_from_graph(driver)
        source = "Neo4j graph"
    else:
        rows, generations = rows_from_csv(args.raw_dir, CANDIDATE_GROUPS)
        source = "raw CSVs"

    report = render_markdown(level_table(rows, CANDIDATE_GROUPS), generations, source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
