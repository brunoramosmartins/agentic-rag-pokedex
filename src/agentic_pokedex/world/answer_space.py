"""Answer spaces: how many values each answer slot admits, and how skewed it is.

The G2 closed-book check (``docs/contingency.md``) asks whether a model with no
evidence answers twin questions better than chance. "Chance" depends on the
slot: a type is one of 18, a category one of 3, a species one of 1,025. And a
slot can be **skewed**: a guesser who always says the most common value scores
that value's share, with no leak at all. So each slot reports both:

- ``n`` admissible values and the **uniform** chance ``1 / n``;
- the **modal** value and its share of the population — the score of the best
  constant guess.

Populations are world-level (every fact of the slot in scope). A template's
own population, known only once questions exist, can be more or less skewed;
the world-level figures bound what to expect.

Usage::

    python -m agentic_pokedex.world.answer_space
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from pathlib import Path

from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.world.coverage import answerable_level, level_table, s2_usable
from agentic_pokedex.world.download import DEFAULT_RAW_DIR
from agentic_pokedex.world.pokeapi import VERSION_SCOPE, iter_learnsets, read_world
from agentic_pokedex.world.render import World, build_world

SMALL_SPACE = 20
"""Slots with at most this many values are checked against chance in G2."""
DEFAULT_OUT = REPO_ROOT / "data" / "world" / "answer_space.md"


@dataclass(frozen=True)
class Slot:
    """The values a slot takes across its population."""

    name: str
    population: str
    counts: Counter[Hashable]

    @property
    def n(self) -> int:
        """Admissible values."""
        return len(self.counts)

    @property
    def uniform(self) -> float:
        """Chance of a uniform guess."""
        return 1 / self.n if self.n else 0.0

    @property
    def mode(self) -> Hashable:
        """The most common value (ties: smallest value, for stability)."""
        top = max(self.counts.values())
        return min((v for v, c in self.counts.items() if c == top), key=repr)

    @property
    def modal_share(self) -> float:
        """Share of the population holding the modal value."""
        total = sum(self.counts.values())
        return self.counts[self.mode] / total if total else 0.0

    @property
    def small(self) -> bool:
        """Whether the slot counts as a small answer space."""
        return self.n <= SMALL_SPACE


def _slot(name: str, population: str, values: Iterable[Hashable]) -> Slot:
    return Slot(name, population, Counter(list(values)))


def answer_slots(world: World) -> list[Slot]:
    """Every answer slot the world's facts can fill, with its population.

    Names are given as ids (types, moves, abilities, species): the same counts
    hold in the twin and in the real naming.
    """
    types = world.pokemon_types
    level_rows = [r for r in world.learnsets if r["method"] == "level-up"]
    table = level_table(level_rows, world.scope)
    s2_levels = [
        answerable_level(table[g][pair])
        for g in world.scope
        for pair in s2_usable(table, world.scope, g)
    ]
    abilities = world.pokemon_abilities
    return [
        _slot("type of a Pokémon (primary)", "Pokémon entries",
              (ts[0][1] for ts in types.values() if ts)),
        _slot("type of a Pokémon (any slot)", "Pokémon type facts",
              (t for ts in types.values() for _, t in ts)),
        _slot("type of a move", "moves",
              (m["type_id"] for m in world.moves.values())),
        _slot("move category", "moves",
              (m["category"] for m in world.moves.values() if m["category"])),
        _slot("move power", "moves with power",
              (m["power"] for m in world.moves.values() if m["power"] is not None)),
        _slot("damage factor", "type pairs", world.efficacy.values()),
        _slot("learn level", "answerable level-up pairs in scope",
              (answerable_level(lv) for g in table.values() for lv in g.values()
               if answerable_level(lv))),
        _slot("learn level (S2-usable)", "S2-usable pairs in scope", s2_levels),
        _slot("ability", "Pokémon ability facts",
              (k for ab in abilities.values() for _, k, _ in ab)),
        _slot("hidden ability", "hidden-ability facts",
              (k for ab in abilities.values() for _, k, h in ab if h)),
        _slot("species", "species", list(world.species)),
        _slot("move", "moves", list(world.moves)),
    ]


def render_markdown(slots: Iterable[Slot]) -> str:
    """The answer-space table."""
    lines = [
        "| Slot | Population | Values (n) | Uniform chance | Modal share | Space |",
        "|---|---|---:|---:|---:|---|",
    ]
    for s in slots:
        size = "small" if s.small else "open"
        lines.append(
            f"| {s.name} | {s.population} ({sum(s.counts.values()):,}) | {s.n:,} "
            f"| {s.uniform:.1%} | {s.modal_share:.1%} | {size} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Answer spaces per slot.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    tables = read_world(args.raw_dir)
    learn_rows = list(iter_learnsets(args.raw_dir, tables))
    world = build_world(tables, learn_rows, VERSION_SCOPE)
    report = render_markdown(answer_slots(world))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
