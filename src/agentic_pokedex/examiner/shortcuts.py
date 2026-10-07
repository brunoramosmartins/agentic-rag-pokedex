"""Shortcut scan (filter 7 of `docs/examiner.md`; ADR-002, gate 7).

The label trusts the fact → units registry. The scan is a check on that trust
that reads only text: a **statement** outside the question's gold units that
mentions every anchor of the question together with its answer flags the
question. A statement is one body line of a structured unit read with the
unit's header line (the header names the page's entity, and a line alone does
not say whose it is), or a whole free-text unit.

Matching is lexical and exact: names are matched as whole token sequences
(``[[Sprout]]`` and ``Sprout's`` mention Sprout; ``Sproutree`` does not), numbers
as whole digit tokens, category and damage-factor answers as their rendered
phrase. It misses paraphrase, which is why the G3 audit reads chains by hand.

Flags are grouped into **classes** — (template, section of the flagged unit,
kind of the flagged line) — because rendered pages are templated: every flag
of a class is the same line pattern with different names. Each class is read
with rendered examples and resolved in ``VERDICTS``: ``coincidence`` (the
statement is another fact that happens to mention the same names; the
question is kept) or ``leak`` (the statement gives the answer; the question is
discarded). A class without a verdict is unresolved and fails the scan.

Before the scan is trusted, every run plants leaks — synthetic units stating a
sampled question's answer next to its anchors, in prose and as a structured
line — and requires all of them flagged.

The scan reads the twin pages: the population the agents see. Real names
collide lexically ("Fire" inside "Fire Punch", "Porygon" inside "Porygon-Z"),
which is noise of the scan, not a leak of the registry.

Usage::

    python -m agentic_pokedex.examiner.shortcuts              # scan and report
    python -m agentic_pokedex.examiner.shortcuts --examples 3
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic_pokedex.world.index import DEFAULT_WORLD_DIR
from agentic_pokedex.world.registry import Registry
from agentic_pokedex.world.render import ATTACKING, DEFENDING, Names

SCAN_SEED = 20260929
PLANTS_PER_TEMPLATE = 5

_TOKEN = re.compile(r"\w+|[^\w\s]")
_DIGITS = re.compile(r"\d+")

ANSWER_KIND: Mapping[str, str] = {
    "S0-A1": "ability", "S0-A2": "number", "S0-A3": "category", "S0-A4": "type",
    "S0-B1": "factor", "S1-A1": "ability", "S1-A2": "types", "S1-A3": "ability",
    "S1-B1": "factor", "S2-A1": "number", "S2-A2": "move", "S2-B1": "move",
    "S3-A1": "species-set", "S3-B1": "species-set", "S4-A1": "number",
    "S4-B1": "move",
}
"""How each template's answer is written on a page. S4's answer is the withheld
value: a leak would state it."""

_FORM = "a form of the anchor: another entry, whose ability or types are its own"
_OWN = ("the anchor's own value (or a form's), not the final form's: the benign "
        "S1 case, tracked by the material tag")
_MATCHUP = "a third type's matchup line that lists both types"

VERDICTS: Mapping[tuple[str, str, str], tuple[str, str]] = {
    ("S0-A1", "Form", "Abilities"): ("coincidence", _FORM),
    ("S0-A1", "Holders", "entry"): ("coincidence", _FORM),
    ("S0-A2", "Learned by", "entry"): (
        "coincidence", "a learn level equal to the move's power"),
    ("S0-A2", "Learnset", "Level N"): (
        "coincidence", "a learn level equal to the move's power"),
    ("S0-A4", "Learned by", "entry"): (
        "coincidence", "a learner's types in the move's hub, not the move's type"),
    ("S0-B1", "Matchups", "Attacking — normal damage against"): (
        "coincidence", _MATCHUP),
    ("S0-B1", "Matchups", "Attacking — not very effective against"): (
        "coincidence", _MATCHUP),
    ("S0-B1", "Matchups", "Attacking — super effective against"): (
        "coincidence", _MATCHUP),
    ("S0-B1", "Matchups", "Defending — normal damage from"): (
        "coincidence", _MATCHUP),
    ("S0-B1", "Matchups", "Defending — resists"): ("coincidence", _MATCHUP),
    ("S0-B1", "Matchups", "Defending — weak to"): ("coincidence", _MATCHUP),
    ("S1-A1", "Form", "Abilities"): ("coincidence", _FORM),
    ("S1-A1", "Holders", "entry"): ("coincidence", _OWN),
    ("S1-A2", "Form", "Types"): ("coincidence", _FORM),
    ("S1-A2", "Learned by", "entry"): ("coincidence", _OWN),
    ("S1-A3", "Form", "Abilities"): ("coincidence", _FORM),
    ("S1-A3", "Holders", "entry"): ("coincidence", _OWN),
    ("S2-B1", "Learnset", "Moves"): (
        "coincidence", "the same move learned by another method (machine or "
        "tutor), not the last level-up move"),
}
"""(template, section, line kind) → (``coincidence`` | ``leak``, reason).

Written 2026-09-29 after reading every class of the first scan with rendered
examples (`docs/examiner.md`, "Shortcut scan"). A class seen for the first time
has no verdict and fails the scan until it is read."""


def tokens(text: str) -> tuple[str, ...]:
    """Word and punctuation tokens: the unit of lexical matching."""
    return tuple(_TOKEN.findall(text))


def statements(text: str, free_text: bool = False) -> list[str]:
    """A unit's statements: header + each body line, or the whole free text."""
    if free_text:
        return [text]
    head, *lines = text.split("\n")
    return [f"{head}\n{line}" for line in lines]


def line_kind(statement: str, free_text: bool = False) -> str:
    """The pattern of a statement's body line, for grouping flags into classes.

    ``Level 13: [[Bite]]`` → ``Level N``; ``[[Sprout]] (Moss) — level 1`` →
    ``entry``; ``Attacking — resists: …`` → ``Attacking — resists``.
    """
    if free_text:
        return "free text"
    line = statement.split("\n", 1)[1]
    if line.startswith("[["):
        return "entry"
    return _DIGITS.sub("N", line.split(":", 1)[0])


class Lexicon:
    """Every display name of one naming, matched as token sequences."""

    def __init__(self, names: Names) -> None:
        self._names: dict[tuple[str, ...], set[str]] = defaultdict(set)
        for kind in ("species", "pokemon", "types", "moves", "abilities", "groups"):
            for name in getattr(names, kind).values():
                self._names[tokens(name)].add(name)
        self._longest = max(len(t) for t in self._names)

    def mentions(self, text: str) -> set[str]:
        """Names and whole numbers the text mentions."""
        toks = tokens(text)
        found = {t for t in toks if t.isdigit()}
        for i in range(len(toks)):
            for j in range(i + 1, min(i + self._longest, len(toks)) + 1):
                found |= self._names.get(toks[i:j], set())
        return found


@dataclass(frozen=True)
class Probe:
    """What the scan looks for in one question.

    Attributes:
        anchors: Names (or numbers) of the question's slots; all must appear.
        names: Answer names or numbers; all must appear (a set, a type pair).
        phrases: Rendered phrases of the answer; one must appear (lower case).
    """

    anchors: tuple[str, ...]
    names: tuple[str, ...] = ()
    phrases: tuple[str, ...] = ()


def probe(record: Mapping[str, Any], names: Names) -> Probe | None:
    """The anchors and answer forms of a question, or ``None`` when its answer
    has no rendered form (a ×4 or ×0.25 multiplier appears on no page)."""
    s, answer = record["slots"], record["answer"]
    anchors: list[str] = []
    if "X" in s:
        anchors.append(names.species[s["X"]])
    if "M" in s:
        anchors.append(names.moves[s["M"]])
    anchors += [names.types[s[k]] for k in ("A", "B", "T") if k in s]
    if "V" in s:
        anchors.append(names.groups[s["V"]])
    if "L" in s:
        anchors.append(str(s["L"]))
    kind = ANSWER_KIND[record["template"]]
    if kind == "factor":
        percent = round(answer * 100)
        if percent not in ATTACKING:
            return None
        return Probe(tuple(anchors), phrases=(ATTACKING[percent], DEFENDING[percent]))
    if kind == "category":
        return Probe(tuple(anchors), phrases=(answer,))
    answer_names = {
        "ability": lambda: [names.abilities[answer]],
        "type": lambda: [names.types[answer]],
        "types": lambda: [names.types[t] for t in answer],
        "move": lambda: [names.moves[answer]],
        "number": lambda: [str(answer)],
        "species-set": lambda: [names.species[x] for x in answer],
    }[kind]()
    return Probe(tuple(anchors), names=tuple(answer_names))


@dataclass(frozen=True)
class Flag:
    """One statement that mentions a question's anchors with its answer."""

    question: str
    unit: str
    statement: int
    section: str
    kind: str
    text: str

    @property
    def klass(self) -> tuple[str, str, str]:
        """(template, section, line kind)."""
        return (self.question.split(":", 1)[0], self.section, self.kind)


@dataclass
class ScanIndex:
    """Statements of the indexed units, with an inverted index by mention."""

    lexicon: Lexicon
    _statements: dict[tuple[str, int], tuple[set[str], str, str, str, str]] = field(
        default_factory=dict
    )
    _by_mention: dict[str, set[tuple[str, int]]] = field(
        default_factory=lambda: defaultdict(set)
    )

    def add(self, unit: str, text: str, section: str, free_text: bool = False) -> None:
        """Index one unit's statements."""
        for i, stmt in enumerate(statements(text, free_text)):
            found = self.lexicon.mentions(stmt)
            self._statements[(unit, i)] = (
                found, stmt, stmt.lower(), section, line_kind(stmt, free_text)
            )
            for m in found:
                self._by_mention[m].add((unit, i))

    def scan(self, record: Mapping[str, Any], p: Probe) -> list[Flag]:
        """Statements outside the gold units that mention anchors and answer."""
        gold = {u for units in record["cover"].values() for u in units}
        pools = [self._by_mention.get(a, set()) for a in p.anchors]
        candidates = set.intersection(*pools) if pools else set()
        flags = []
        for unit, i in sorted(candidates):
            if unit in gold:
                continue
            found, text, lower, section, kind = self._statements[(unit, i)]
            if not all(n in found for n in p.names):
                continue
            if p.phrases and not any(ph in lower for ph in p.phrases):
                continue
            flags.append(Flag(record["id"], unit, i, section, kind, text))
        return flags


def build_index(
    pages: Path, registry: Registry, lexicon: Lexicon
) -> ScanIndex:
    """Index the indexed units of a page file (withheld units are never seen)."""
    index = ScanIndex(lexicon)
    with pages.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            meta = registry.units[row["id"]]
            if not meta.withheld:
                index.add(row["id"], row["text"], meta.section, meta.free_text)
    return index


# --- Planted leaks ------------------------------------------------------------


def plants(record: Mapping[str, Any], p: Probe) -> list[tuple[str, str, bool]]:
    """Two leaks for one question: (unit id, text, free text).

    One in prose, as a Pokédex note would state it; one as a structured line.
    Both mention every anchor with the answer and are registered for nothing.
    """
    answer = [*p.names, *p.phrases[:1]]
    anchors = list(p.anchors)
    prose = (f"Species: {anchors[0]} · Section: Notes\n"
             f"Seen with {', '.join(anchors[1:]) or anchors[0]}, it is known for "
             f"{' and '.join(answer)}.")
    line = (f"Move: {anchors[0]} · Section: Planted\n"
            + ", ".join(f"[[{a}]]" for a in [*anchors[1:], *answer]))
    qid = record["id"]
    return [(f"planted/{qid}/prose", prose, True),
            (f"planted/{qid}/line", line, False)]


def check_plants(
    records: Sequence[Mapping[str, Any]], names: Names, lexicon: Lexicon,
    per_template: int = PLANTS_PER_TEMPLATE, seed: int = SCAN_SEED,
) -> tuple[int, int, list[str]]:
    """Plant leaks for a seeded sample per template and scan for them.

    Returns:
        (flagged, planted, ids of the plants the scan missed).
    """
    by_template: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for r in records:
        if probe(r, names) is not None:
            by_template[r["template"]].append(r)
    rng = random.Random(seed)
    flagged, planted, missed = 0, 0, []
    for template in sorted(by_template):
        pool = sorted(by_template[template], key=lambda r: r["id"])
        for r in rng.sample(pool, min(per_template, len(pool))):
            p = probe(r, names)
            assert p is not None
            for unit, text, free in plants(r, p):
                index = ScanIndex(lexicon)
                index.add(unit, text, "Planted", free)
                planted += 1
                if any(f.unit == unit for f in index.scan(r, p)):
                    flagged += 1
                else:
                    missed.append(unit)
    return flagged, planted, missed


# --- Resolution -----------------------------------------------------------------


def resolve(
    flags_by_question: Mapping[str, list[Flag]],
    verdicts: Mapping[tuple[str, str, str], tuple[str, str]] = VERDICTS,
) -> dict[str, str]:
    """Each flagged question's status: ``kept``, ``discarded`` or ``unresolved``.

    A question is discarded if any of its flags is in a ``leak`` class, and
    unresolved if any flag's class has no verdict.
    """
    status = {}
    for qid, flags in flags_by_question.items():
        found = [verdicts.get(f.klass, ("unresolved", ""))[0] for f in flags]
        if "leak" in found:
            status[qid] = "discarded"
        elif "unresolved" in found:
            status[qid] = "unresolved"
        else:
            status[qid] = "kept"
    return status


def scan_all(
    records: Iterable[Mapping[str, Any]], index: ScanIndex, names: Names
) -> tuple[dict[str, list[Flag]], Counter[str], Counter[str]]:
    """Scan every question.

    Returns:
        Flags by question (flagged questions only), questions per template, and
        questions per template whose answer has no rendered form.
    """
    flags: dict[str, list[Flag]] = {}
    total: Counter[str] = Counter()
    unscannable: Counter[str] = Counter()
    for r in records:
        total[r["template"]] += 1
        p = probe(r, names)
        if p is None:
            unscannable[r["template"]] += 1
            continue
        found = index.scan(r, p)
        if found:
            flags[r["id"]] = found
    return flags, total, unscannable


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Shortcut scan with planted leaks.")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--examples", type=int, default=2,
                        help="rendered examples per class")
    args = parser.parse_args(argv)

    from agentic_pokedex.world.download import DEFAULT_RAW_DIR
    from agentic_pokedex.world.pokeapi import VERSION_SCOPE, iter_learnsets, read_world
    from agentic_pokedex.world.render import build_world
    from agentic_pokedex.world.twin import DEFAULT_MAP_PATH, TwinMap

    tables = read_world(DEFAULT_RAW_DIR)
    world = build_world(tables, list(iter_learnsets(DEFAULT_RAW_DIR, tables)),
                        VERSION_SCOPE)
    names = Names.twin(world, TwinMap.load(DEFAULT_MAP_PATH))
    registry = Registry.load(args.world_dir / "registry.json")
    lexicon = Lexicon(names)
    out = args.world_dir / "examiner"
    with (out / "questions.jsonl").open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]

    flagged, planted, missed = check_plants(records, names, lexicon)
    print(f"planted leaks flagged: {flagged} of {planted}")
    if missed:
        print("  missed:", ", ".join(missed[:10]))
        return 1

    index = build_index(args.world_dir / "pages" / "twin.jsonl", registry, lexicon)
    flags, total, unscannable = scan_all(records, index, names)
    status = resolve(flags)
    material = {r["id"]: r.get("material") for r in records}

    print(f"\n{'template':<8} {'questions':>9} {'flagged':>8} {'no form':>8}")
    per_template = Counter(q.split(":", 1)[0] for q in flags)
    for t in sorted(total):
        print(f"{t:<8} {total[t]:>9,} {per_template[t]:>8,} {unscannable[t]:>8,}")

    classes: dict[tuple[str, str, str], list[Flag]] = defaultdict(list)
    for found in flags.values():
        for f in found:
            classes[f.klass].append(f)
    report = {}
    print("\nclasses (template · section · line kind): questions / flags → verdict")
    for klass in sorted(classes):
        found = classes[klass]
        qids = sorted({f.question for f in found})
        verdict = VERDICTS.get(klass, ("unresolved", ""))[0]
        s1 = Counter("material" if material[q] else "benign"
                     for q in qids if material[q] is not None)
        extra = f"  ({dict(s1)})" if s1 else ""
        counts = f"{len(qids):,} / {len(found):,}"
        print(f"\n{' · '.join(klass)}: {counts} → {verdict}{extra}")
        rng = random.Random(SCAN_SEED)
        for f in rng.sample(found, min(args.examples, len(found))):
            print(f"  [{f.question}] {f.unit}")
            for text_line in f.text.split("\n"):
                print(f"      {text_line}")
        report[" · ".join(klass)] = {"questions": len(qids), "flags": len(found),
                                     "verdict": verdict, **dict(s1)}

    counts = Counter(status.values())
    print(f"\nflagged questions: {len(flags):,} of {sum(total.values()):,} — "
          + ", ".join(f"{k} {v:,}" for k, v in sorted(counts.items())))
    (out / "shortcuts.json").write_text(json.dumps({
        "planted": {"flagged": flagged, "planted": planted},
        "templates": {t: {"questions": total[t], "flagged": per_template[t],
                          "no_rendered_form": unscannable[t]} for t in sorted(total)},
        "classes": report,
        "status": dict(sorted(status.items())),
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if not counts["unresolved"] else 2


if __name__ == "__main__":
    sys.exit(main())
