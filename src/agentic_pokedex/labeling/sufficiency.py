"""The per-step sufficiency label (`docs/examiner.md`, "The sufficiency label").

A state is the set of units an agent has seen. It is **sufficient** when every
gold fact is stated by at least one seen unit — equivalently, when the seen
units cover a minimal sufficient set (ADR-001, update of 2026-09-26). Covers
are indexed units only, so an S4 state is never sufficient.

The label is a pure function of the question's gold facts, the fact → units
registry and the unit ids a trajectory showed: no model, no answer text, no
outcome. Covers are recomputed from the registry, never read from the question
record, so a stale record cannot change a label.

Usage::

    python -m agentic_pokedex.labeling.sufficiency S1-A1:x=147 \\
        species/147/profile "species/148/profile,ability/39/holders/0"

Each argument after the question id is one step: the ids of the units it
showed, comma-separated (an empty string is a step that showed nothing).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_pokedex.world.index import DEFAULT_WORLD_DIR
from agentic_pokedex.world.registry import Registry

SUFFICIENT = "sufficient"
INSUFFICIENT = "insufficient"
ABSTAINED = "abstained"

SUBTYPES: Mapping[str, str] = {
    "S0": "not-found",
    "S1": "missing-hop",
    "S2": "wrong-version",
    "S3": "truncated",
    "S4": "nonexistent",
}
"""The subtype an insufficient state carries, by the question's stratum."""


@dataclass(frozen=True)
class Gold:
    """Everything the label of one question depends on.

    Attributes:
        question: Question id.
        stratum: ``S0`` … ``S4``.
        cover: Gold fact → indexed units stating it, in gold-fact order.
        near_certain: Indexed units stating a distractor fact (S2, S4).
        members: S3: the Pokémon entries of the gold set. The gold facts cover
            the whole hub (PI-020); members are what ``members`` counts.
    """

    question: str
    stratum: str
    cover: Mapping[str, frozenset[str]]
    near_certain: frozenset[str] = frozenset()
    members: frozenset[int] = frozenset()


@dataclass(frozen=True)
class StepLabel:
    """The label of the state after one step.

    Attributes:
        step: Observations so far; 0 is the state before any tool call.
        state: ``sufficient`` or ``insufficient``.
        subtype: The stratum's subtype when insufficient, else ``None``.
        missing: Gold facts no seen unit states, in gold-fact order.
        covered: Gold facts some seen unit states.
        total: Gold facts.
        near_certain: Near-certain units seen so far, sorted.
        members: S3 only: (set members whose facts are all seen, set size).
    """

    step: int
    state: str
    subtype: str | None
    missing: tuple[str, ...]
    covered: int
    total: int
    near_certain: tuple[str, ...] = ()
    members: tuple[int, int] | None = None

    @property
    def sufficient(self) -> bool:
        """Whether every gold fact is stated by a seen unit."""
        return self.state == SUFFICIENT


def gold_from(record: Mapping[str, Any], registry: Registry) -> Gold:
    """The label inputs of a question record.

    Args:
        record: A question as a mapping: a generated ``Question`` through
            ``dataclasses.asdict`` or a row of ``questions.jsonl``. Reads
            ``id``, ``stratum``, ``gold_facts`` and ``distractor_facts``.
        registry: The fact → units registry of the rendering.

    Returns:
        The gold facts' covers and the near-certain units, from the registry.

    Raises:
        ValueError: Unknown stratum; no gold fact; a gold or distractor fact the
            registry does not know; outside S4, a gold fact no indexed unit
            states (no sufficient set exists); in S4, a gold fact an indexed
            unit states (the question would be answerable).
    """
    qid, stratum = record["id"], record["stratum"]
    if stratum not in SUBTYPES:
        raise ValueError(f"{qid}: unknown stratum {stratum!r}")
    facts = list(dict.fromkeys(record["gold_facts"]))
    if not facts:
        raise ValueError(f"{qid}: no gold fact")
    distractors = list(record.get("distractor_facts") or [])
    unknown = [f for f in facts + distractors if f not in registry.facts]
    if unknown:
        raise ValueError(f"{qid}: unknown fact {unknown[0]}")
    cover = {f: frozenset(registry.fact_units(f, indexed_only=True)) for f in facts}
    stated = [f for f, units in cover.items() if units]
    if stratum == "S4" and stated:
        raise ValueError(f"{qid}: an indexed unit states the S4 gold fact {stated[0]}")
    if stratum != "S4" and len(stated) < len(facts):
        lost = next(f for f, units in cover.items() if not units)
        raise ValueError(f"{qid}: gold fact {lost} has no indexed unit")
    near = frozenset(
        u for f in distractors for u in registry.fact_units(f, indexed_only=True)
    )
    members = frozenset(int(p) for p in record.get("set_members") or [])
    return Gold(qid, stratum, cover, near, members)


def _member(fact: str) -> int:
    """The Pokémon entry an S3 gold fact is about (``learn:`` and ``ptype:``)."""
    return int(fact.split(":")[1])


def label_state(gold: Gold, seen: Iterable[str], step: int = 0) -> StepLabel:
    """Label one state: the units seen so far.

    Args:
        gold: From ``gold_from``.
        seen: Ids of every unit seen up to this step (repeats are harmless).
        step: The step number to record.

    Returns:
        The state's label.
    """
    seen = set(seen)
    missing = tuple(f for f, units in gold.cover.items() if not units & seen)
    total = len(gold.cover)
    members = None
    if gold.stratum == "S3":
        entries = gold.members or frozenset(_member(f) for f in gold.cover)
        lacking = {_member(f) for f in missing} & entries
        members = (len(entries) - len(lacking), len(entries))
    sufficient = not missing
    return StepLabel(
        step=step,
        state=SUFFICIENT if sufficient else INSUFFICIENT,
        subtype=None if sufficient else SUBTYPES[gold.stratum],
        missing=missing,
        covered=total - len(missing),
        total=total,
        near_certain=tuple(sorted(gold.near_certain & seen)),
        members=members,
    )


def check_seen(units: Iterable[str], registry: Registry) -> None:
    """Refuse unit ids a trajectory cannot have seen.

    Raises:
        ValueError: An id the registry does not know (a logging fault), or a
            withheld unit (the index must never serve one).
    """
    for unit in units:
        meta = registry.units.get(unit)
        if meta is None:
            raise ValueError(f"unknown unit {unit!r}")
        if meta.withheld:
            raise ValueError(f"withheld unit {unit!r} was seen")


def label_trajectory(
    gold: Gold, steps: Sequence[Sequence[str]], registry: Registry
) -> list[StepLabel]:
    """Label every state of a trajectory.

    Args:
        gold: From ``gold_from``.
        steps: Per step, the ids of the units its observation showed.
        registry: For ``check_seen``.

    Returns:
        ``labels[t]`` is the state after observation ``t``; ``labels[0]`` is the
        state before any tool call, so ``len(steps) + 1`` labels.
    """
    seen: set[str] = set()
    labels = [label_state(gold, seen, 0)]
    for t, units in enumerate(steps, start=1):
        check_seen(units, registry)
        seen.update(units)
        labels.append(label_state(gold, seen, t))
    return labels


def first_sufficient(labels: Sequence[StepLabel]) -> int | None:
    """The first step whose state is sufficient, or ``None`` if none is."""
    return next((lab.step for lab in labels if lab.sufficient), None)


def final_state(labels: Sequence[StepLabel], stopped_at: int, abstained: bool) -> str:
    """The label at the final action: ``abstained``, or the state it was taken in.

    Args:
        labels: From ``label_trajectory``.
        stopped_at: The observation after which the final action was taken.
        abstained: Whether the final action was abstention.
    """
    return ABSTAINED if abstained else labels[stopped_at].state


# --- CLI ----------------------------------------------------------------------


def _find(path: Path, qid: str) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["id"] == qid:
                return row
    raise SystemExit(f"no question {qid!r} in {path}")


def _parse_steps(args: Sequence[str]) -> list[list[str]]:
    return [[u.strip() for u in arg.split(",") if u.strip()] for arg in args]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: label a hand-written trajectory of a generated question."""
    parser = argparse.ArgumentParser(description="Label a trajectory step by step.")
    parser.add_argument("question", help="question id, e.g. S1-A1:x=147")
    parser.add_argument("steps", nargs="*", help="one argument per step: unit ids, "
                        "comma-separated")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    args = parser.parse_args(argv)

    registry = Registry.load(args.world_dir / "registry.json")
    record = _find(args.world_dir / "examiner" / "questions.jsonl", args.question)
    print(f"[{record['id']}] {record.get('twin_text', '')}")
    print(f"  answer: {record.get('twin_answer', record['answer'])}")
    gold = gold_from(record, registry)
    steps = _parse_steps(args.steps)
    try:
        labels = label_trajectory(gold, steps, registry)
    except ValueError as error:
        print(f"  refused: {error}")
        return 1
    for lab in labels:
        if lab.step == 0:
            shown = "(no evidence yet)"
        else:
            shown = ", ".join(steps[lab.step - 1]) or "(nothing shown)"
        state = lab.state + (f" ({lab.subtype})" if lab.subtype else "")
        extra = f", members {lab.members[0]}/{lab.members[1]}" if lab.members else ""
        print(f"\nstep {lab.step}: {shown}")
        print(f"  {state} — {lab.covered}/{lab.total} gold facts{extra}")
        for fact in lab.missing:
            print(f"    missing {fact}")
        if lab.near_certain:
            print(f"    near-certain seen: {', '.join(lab.near_certain)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
