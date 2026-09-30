"""Reachability on dev (ADR-007): every insufficiency subtype and every error
code of E-001 is producible by at least one dev question, or unreachable by
declared design.

A code is **reachable** when some dev question has a state an agent can reach
— a set of indexed units — whose label is the one the code needs. The witness
state is labelled by the sufficiency labeler, never by hand. Error codes that
depend on the model's output, not on the question, are **declared**: they need
a state the witnesses below already show, plus an output.

Usage::

    python -m agentic_pokedex.examiner.reachability
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_pokedex.examiner.splits import opaque_id
from agentic_pokedex.labeling.sufficiency import Gold, gold_from, label_state
from agentic_pokedex.world.index import DEFAULT_WORLD_DIR
from agentic_pokedex.world.registry import Registry

T_MAX = 6
"""Steps per trajectory (E-001)."""

Record = Mapping[str, Any]


@dataclass(frozen=True)
class Witness:
    """A dev question and a reachable state that produce a code.

    Attributes:
        code: Subtype or error code.
        question: Question id (local).
        state: Unit ids of the state.
        label: The labeler's label of the state, e.g. ``insufficient
            (wrong-version)``.
        why: What the state shows.
    """

    code: str
    question: str
    state: tuple[str, ...]
    label: str
    why: str


def _label_text(gold: Gold, state: Sequence[str]) -> str:
    lab = label_state(gold, state)
    return lab.state + (f" ({lab.subtype})" if lab.subtype else "")


def _first(
    records: Sequence[Record], registry: Registry, stratum: str | tuple[str, ...],
    state_of: Callable[[Record, Gold], Sequence[str] | None],
    accept: Callable[[Gold, Sequence[str]], bool],
) -> tuple[Record, Gold, tuple[str, ...]] | None:
    """The first dev question of a stratum with a state that ``accept`` takes."""
    strata = (stratum,) if isinstance(stratum, str) else stratum
    for r in records:
        if r["stratum"] not in strata:
            continue
        gold = gold_from(r, registry)
        state = state_of(r, gold)
        if state is not None and accept(gold, state):
            return r, gold, tuple(state)
    return None


def _one_cover_unit(r: Record, gold: Gold) -> list[str]:
    first = next(iter(gold.cover.values()))
    return [sorted(first)[0]]


def _first_near_certain(r: Record, gold: Gold) -> list[str] | None:
    return [sorted(gold.near_certain)[0]] if gold.near_certain else None


def _species_first(units: frozenset[str]) -> str:
    return min(units, key=lambda u: (not u.startswith("species/"), u))


def _first_member(r: Record, gold: Gold) -> list[str]:
    """The species units of the set's first member (a hub would hold more)."""
    member = next(iter(gold.cover)).split(":")[1]
    return sorted({_species_first(u) for f, u in gold.cover.items()
                   if f.split(":")[1] == member})


def _answer_unit(
    texts: Mapping[str, str],
) -> Callable[[Record, Gold], list[str] | None]:
    """A single gold unit whose text shows the answer name (S1)."""

    def state_of(r: Record, gold: Gold) -> list[str] | None:
        answer = r.get("twin_answer", "")
        for units in gold.cover.values():
            for u in sorted(units):
                if answer and answer in texts.get(u, ""):
                    return [u]
        return None

    return state_of


def _insufficient(subtype: str) -> Callable[[Gold, Sequence[str]], bool]:
    def accept(gold: Gold, state: Sequence[str]) -> bool:
        lab = label_state(gold, state)
        return not lab.sufficient and lab.subtype == subtype and bool(state)

    return accept


def _sufficient(gold: Gold, state: Sequence[str]) -> bool:
    return label_state(gold, state).sufficient


def _no_single_unit(gold: Gold, state: Sequence[str]) -> bool:
    """No single unit is sufficient: sufficiency takes at least two steps."""
    units = {u for us in gold.cover.values() for u in us}
    return not any(label_state(gold, [u]).sufficient for u in units)


def witnesses(
    records: Sequence[Record], registry: Registry, texts: Mapping[str, str]
) -> dict[str, Witness | None]:
    """A witness per subtype and error code (``None``: none on dev).

    Args:
        records: dev questions, in draw order.
        registry: The fact → units registry.
        texts: Unit id → twin text (for the correct-at-insufficient witness).
    """
    found: dict[str, tuple[Record, Gold, tuple[str, ...]] | None] = {
        "missing-hop": _first(records, registry, "S1", _one_cover_unit,
                              _insufficient("missing-hop")),
        "wrong-version": _first(records, registry, "S2", _first_near_certain,
                                _insufficient("wrong-version")),
        "truncated": _first(records, registry, "S3", _first_member,
                            _insufficient("truncated")),
        "nonexistent": _first(records, registry, "S4", _first_near_certain,
                              _insufficient("nonexistent")),
        "sufficient": _first(records, registry, "S0", _one_cover_unit, _sufficient),
        "multi-unit": _first(records, registry, ("S1", "S3"), _one_cover_unit,
                             _no_single_unit),
        "answer-visible": _first(records, registry, "S1", _answer_unit(texts),
                                 _insufficient("missing-hop")),
    }
    why = {
        "missing-hop": "one unit of an S1 chain: a hop still missing",
        "wrong-version": "another version's unit, the asked version's unseen",
        "truncated": "one member of an S3 set",
        "nonexistent": "another version's unit for a withheld learnset",
        "sufficient": "an S0 question's gold unit, reached in one step",
        "multi-unit": "no single unit is sufficient: at least two steps",
        "answer-visible": "a gold unit that shows the answer, the chain unfinished",
    }
    codes = {
        "missing-hop": "missing-hop",
        "wrong-version": "wrong-version",
        "truncated": "truncated",
        "nonexistent": "nonexistent",
        "stop-missing-hop": "missing-hop",
        "accepted-wrong-version": "wrong-version",
        "accepted-truncated-set": "truncated",
        "answered-unanswerable": "nonexistent",
        "abstained-with-sufficient": "sufficient",
        "over-search": "sufficient",
        "generation-error": "sufficient",
        "never-reached": "multi-unit",
        "correct-at-insufficient": "answer-visible",
    }
    out: dict[str, Witness | None] = {}
    for code, key in codes.items():
        hit = found[key]
        if hit is None:
            out[code] = None
            continue
        r, gold, state = hit
        out[code] = Witness(code, r["id"], state, _label_text(gold, state), why[key])
    return out


DECLARED: Mapping[str, str] = {
    "format-error": "a property of the model's output, not of the question: any "
                    "question can produce it",
}
"""Codes that no question state decides."""


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Reachability of every code on dev.")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    args = parser.parse_args(argv)

    from agentic_pokedex.examiner.splits import open_split

    registry = Registry.load(args.world_dir / "registry.json")
    dev = open_split("dev", "", world_dir=args.world_dir)
    with (args.world_dir / "examiner" / "questions.jsonl").open(encoding="utf-8") as fh:
        by_id = {r["id"]: r for r in map(json.loads, fh)}
    texts = {}
    with (args.world_dir / "pages" / "twin.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            texts[row["id"]] = row["text"]
    found = witnesses([by_id[q] for q in dev], registry, texts)
    missing = [code for code, w in found.items() if w is None]
    print(f"{'code':<27} {'dev question':<14} {'units':>5}  label")
    for code, w in found.items():
        if w is None:
            print(f"{code:<27} {'—':<14} {'':>5}  NOT REACHABLE")
        else:
            print(f"{code:<27} {opaque_id(w.question):<14} {len(w.state):>5}  "
                  f"{w.label} — {w.why}")
    for code, reason in DECLARED.items():
        print(f"{code:<27} {'declared':<14} {'':>5}  {reason}")
    if missing:
        print(f"\nnot reachable on dev: {', '.join(missing)}")
        return 1
    print(f"\nall {len(found)} codes reachable on dev "
          f"({len(DECLARED)} declared); witness states have at most "
          f"{max(len(w.state) for w in found.values() if w)} of {T_MAX} steps' units")
    return 0


if __name__ == "__main__":
    sys.exit(main())
