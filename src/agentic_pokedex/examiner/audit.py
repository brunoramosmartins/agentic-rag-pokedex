"""G3 audit of the generator: 60 stratified questions read by hand, real names.

``draw`` writes a local sheet (`data/world/examiner/audit/`, gitignored: it
holds real names and gold answers) with, per question: the question and its
gold answer in real names, the units that state its gold chain as the corpus
renders them, the evidence that makes it hard (another version's unit for S2
and S4, the anchor's own value for S1) and what to check it against. The author
writes a verdict under each question; ``score`` reads them.

Sample: 12 questions per stratum, spread evenly over the stratum's templates
(largest remainder, group A first); one question per family; S1 group A is
material (the H1 population). Questions come only from outside the evaluation
splits — dev, train and unassigned families — so auditing opens nothing. Each
round excludes every question an earlier round drew (G3: a re-audit uses a
sample never seen before).

A gold answer is **correct** when it matches the game data for the question as
asked — in the named version group, for the default form — and the question has
exactly that answer. S1 also needs the material tag right; S3 the set complete
and exact; S4 the withheld value right.

Usage::

    python -m agentic_pokedex.examiner.audit draw --round 1
    python -m agentic_pokedex.examiner.audit review --round 1   # one by one
    python -m agentic_pokedex.examiner.audit mark --round 1 --item 7 --verdict ok
    python -m agentic_pokedex.examiner.audit score --round 1
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import fields
from pathlib import Path
from typing import Any

from agentic_pokedex.examiner.generate import (
    GENERATOR_SEED,
    Question,
    answer_text,
    question_text,
)
from agentic_pokedex.examiner.splits import (
    EVALUATION_SPLITS,
    S1_GROUP_A,
    STRATA,
    apportion,
    families,
    load_kept,
    opaque_id,
)
from agentic_pokedex.examiner.templates import TEMPLATES
from agentic_pokedex.world.index import DEFAULT_WORLD_DIR
from agentic_pokedex.world.render import Names
from agentic_pokedex.world.twin import POKEMON_TERM

AUDIT_SEED = 20260929
PER_STRATUM = 12
THRESHOLD = 58

Record = Mapping[str, Any]

GENERATION = {"x-y": "Generation VI", "ultra-sun-ultra-moon": "Generation VII",
              "scarlet-violet": "Generation IX"}

CHECKS: Mapping[str, str] = {
    "S0-A1": "{X}'s hidden ability (default form).",
    "S0-A2": "{M}'s base power, current (Generation IX) data.",
    "S0-A3": "{M}'s damage category, current data.",
    "S0-A4": "{M}'s type, current data.",
    "S0-B1": "Type chart (Generation VI onward): {A} attacking {B}.",
    "S1-A1": "{X}'s evolution line has one final form; that form's hidden ability. "
             "Material tag: whether {X}'s own hidden ability differs.",
    "S1-A2": "{X}'s evolution line has one final form; that form's types. "
             "Material tag: whether {X}'s own types differ.",
    "S1-A3": "{X} evolves into exactly one species; that species' hidden ability. "
             "Material tag: whether {X}'s own hidden ability differs.",
    "S1-B1": "{M}'s type against {X}'s types (default form), type chart from "
             "Generation VI; abilities ignored.",
    "S2-A1": "{X}'s level-up learnset in {V} ({G}): the level of {M} — one level "
             "only — and another version of the scope lists it at a different level.",
    "S2-A2": "{X}'s level-up learnset in {V} ({G}): the single move at level {L}, "
             "and another version lists a different move there.",
    "S2-B1": "{X}'s level-up learnset in {V} ({G}): the single move at the highest "
             "level, and another version's last move differs.",
    "S3-A1": "Every default-form {T}-type Pokémon that learns {M} by level-up in "
             "{V} ({G}): the set is complete and exact.",
    "S3-B1": "Every default-form {T}-type Pokémon that learns {M} by level-up in "
             "{V} ({G}) at or below level {L}: complete and exact.",
    "S4-A1": "The withheld value is right: {X} learns {M} at that level in {V} "
             "({G}). The expected answer is to abstain: that learnset is not in "
             "the corpus.",
    "S4-B1": "The withheld value is right: {X} learns that move at level {L} in "
             "{V} ({G}). The expected answer is to abstain.",
}

_HEADING = re.compile(r"^## \d+\. (\S+) — (q-[0-9a-f]+)\s*$")
_VERDICT = re.compile(r"^\*\*Verdict:\*\*\s*(.*)$")


# --- Sample ---------------------------------------------------------------------


def audit_pool(
    records: Sequence[Record], evaluation: set[str], seen: set[str]
) -> list[Record]:
    """Questions an audit may draw: outside the evaluation splits, not drawn by
    an earlier round, and material in S1 group A."""
    return [
        r for r in records
        if r["id"] not in evaluation and r["id"] not in seen
        and (r["template"] not in S1_GROUP_A or r["material"])
    ]


def allocation() -> dict[str, int]:
    """Questions per template: 12 per stratum, evenly over its templates."""
    out: dict[str, int] = {}
    for stratum in STRATA:
        templates = [t.id for t in TEMPLATES if t.stratum == stratum]
        out.update(zip(templates, apportion(PER_STRATUM, [1] * len(templates)),
                       strict=True))
    return out


def sample(
    pool: Sequence[Record], family: Mapping[str, str], round_: int,
    seed: int = AUDIT_SEED,
) -> list[Record]:
    """Draw one round: per template, a seeded order, one question per family.

    Raises:
        ValueError: A template has too few families left.
    """
    by_template: dict[str, list[Record]] = defaultdict(list)
    for r in sorted(pool, key=lambda r: r["id"]):
        by_template[r["template"]].append(r)
    used: set[str] = set()
    out: list[Record] = []
    for template, n in allocation().items():
        candidates = list(by_template[template])
        random.Random(f"{seed}:g3:{round_}:{template}").shuffle(candidates)
        got = []
        for r in candidates:
            if len(got) == n:
                break
            if family[r["id"]] not in used:
                used.add(family[r["id"]])
                got.append(r)
        if len(got) < n:
            raise ValueError(f"{template}: {len(got)} of {n} questions available")
        out += got
    return out


# --- Sheet ----------------------------------------------------------------------


def as_question(record: Record) -> Question:
    """A question record back as a ``Question``."""
    names = {f.name for f in fields(Question)}
    return Question(**{k: v for k, v in record.items() if k in names})


def chain_units(record: Record) -> list[tuple[str, list[str]]]:
    """Units to show for the gold chain: a greedy cover, largest first.

    Returns:
        (unit id, gold facts it states) in chain order. S4 shows its
        withheld units, which state the gold facts but are not indexed.
    """
    if record["stratum"] == "S4":
        return [(u, list(record["gold_facts"])) for u in record["withheld_units"]]
    covers: dict[str, set[str]] = defaultdict(set)
    for fact, units in record["cover"].items():
        for u in units:
            covers[u].add(fact)
    missing = set(record["cover"])
    chosen = []
    while missing:
        # Most facts first; on a tie, a species page reads more directly than a
        # move's or an ability's list.
        unit = max(sorted(covers), key=lambda u: (len(covers[u] & missing),
                                                  u.startswith("species/")))
        facts = [f for f in record["gold_facts"] if f in covers[unit] & missing]
        chosen.append((unit, facts))
        missing -= covers[unit]
    # Read in chain order: the unit stating the earliest gold fact first.
    position = {f: i for i, f in enumerate(record["gold_facts"])}
    return sorted(chosen, key=lambda c: min(position[f] for f in c[1]))


def _quote(text: str) -> list[str]:
    return [f"> {line}" for line in text.split("\n")]


def _slots_text(record: Record, names: Names) -> dict[str, str]:
    s = record["slots"]
    out = {"L": str(s.get("L", "")), "V": names.groups.get(s.get("V", ""), ""),
           "G": GENERATION.get(s.get("V", ""), "")}
    if "X" in s:
        out["X"] = names.species[s["X"]]
    if "M" in s:
        out["M"] = names.moves[s["M"]]
    for key in ("A", "B", "T"):
        if key in s:
            out[key] = names.types[s[key]]
    return out


def _anchor_value(record: Record, names: Names) -> str:
    values = record["anchor_answer"] or []
    lookup = names.types if record["template"] == "S1-A2" else names.abilities
    return " / ".join(lookup[v] for v in values) or "none"


def render_block(
    n: int, record: Record, names: Names, pages: Mapping[str, str]
) -> str:
    """One question of the sheet, ending with an empty verdict line."""
    q = as_question(record)
    lines = [
        f"## {n}. {record['template']} — {opaque_id(record['id'])}",
        "",
        f"Local id: `{record['id']}`",
        "",
        f"**Question:** {question_text(q, names, POKEMON_TERM, GENERATOR_SEED)}",
        "",
        f"**Gold answer:** {answer_text(q, names)}",
        "",
    ]
    if record["stratum"] == "S1" and record["anchor_answer"] is not None:
        tag = "material" if record["material"] else "benign"
        lines += [f"**Anchor's own value:** {_anchor_value(record, names)} → {tag}",
                  ""]
    label = "Withheld units" if record["stratum"] == "S4" else "Gold chain"
    lines += [f"**{label}** (as the corpus renders them):", ""]
    for unit, facts in chain_units(record):
        lines += [f"`{unit}` — states {', '.join(f'`{f}`' for f in facts)}", ""]
        lines += _quote(pages[unit]) + [""]
    if record["near_certain"]:
        lines += ["**Another version** (the distractor):", ""]
        for unit in record["near_certain"][:2]:
            lines += [f"`{unit}`", ""] + _quote(pages[unit]) + [""]
    check = CHECKS[record["template"]].format(**_slots_text(record, names))
    lines += [f"**Check:** {check}", "", "**Verdict:** ", "", "---", ""]
    return "\n".join(lines)


def render_sheet(
    round_: int, drawn: Sequence[Record], names: Names, pages: Mapping[str, str]
) -> str:
    """The whole sheet for one round."""
    head = [
        f"# G3 audit — round {round_}",
        "",
        f"{len(drawn)} questions, {PER_STRATUM} per stratum. Pass: at least "
        f"{THRESHOLD} correct. Local file: real names and gold answers.",
        "",
        "A gold answer is correct when it matches the game data for the question "
        "as asked — in the named version group, for the default form — and the "
        "question has exactly that answer. S1 also needs the material tag right; "
        "S3 the set complete and exact; S4 the withheld value right.",
        "",
        "Write `ok` after **Verdict:**, or `wrong — <what is wrong>`.",
        "",
        "---",
        "",
    ]
    blocks = [render_block(i, r, names, pages) for i, r in enumerate(drawn, start=1)]
    return "\n".join(head) + "\n".join(blocks)


# --- Score ----------------------------------------------------------------------


def read_verdicts(text: str) -> list[tuple[str, str, str]]:
    """(template, opaque id, verdict) per question: ``ok``, ``wrong`` or
    ``pending`` (nothing written)."""
    out: list[tuple[str, str, str]] = []
    current: tuple[str, str] | None = None
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            current = (heading.group(1), heading.group(2))
            continue
        verdict = _VERDICT.match(line)
        if verdict and current:
            value = verdict.group(1).strip().lower()
            state = ("ok" if value == "ok" else "wrong" if value.startswith("wrong")
                     else "pending" if not value else "unreadable")
            out.append((*current, state))
            current = None
    return out


def score(verdicts: Sequence[tuple[str, str, str]]) -> dict[str, Any]:
    """Counts, failing templates and the G3 decision."""
    states = Counter(v for _, _, v in verdicts)
    wrong = Counter(t for t, _, v in verdicts if v == "wrong")
    complete = not states["pending"] and not states["unreadable"]
    return {
        "questions": len(verdicts),
        "ok": states["ok"],
        "wrong": states["wrong"],
        "pending": states["pending"],
        "unreadable": states["unreadable"],
        "wrong_by_template": dict(sorted(wrong.items())),
        "decision": ("pending" if not complete
                     else "pass" if states["ok"] >= THRESHOLD else "fail"),
        "ids": {oid: v for _, oid, v in verdicts},
    }


# --- Marking --------------------------------------------------------------------


def split_blocks(text: str) -> tuple[str, list[str]]:
    """The sheet's head and its question blocks, each starting at its heading."""
    parts = re.split(r"(?m)^(?=## \d+\. )", text)
    return parts[0], parts[1:]


def block_number(block: str) -> int:
    """The item number of a block (``## 7. …`` → 7)."""
    return int(block.split(".", 1)[0].removeprefix("## "))


def normalize_verdict(answer: str) -> str | None:
    """A typed answer as a verdict: ``ok``, ``wrong — <reason>``, or ``None``
    when it is neither (``o`` and ``w <reason>`` are accepted)."""
    answer = answer.strip()
    if answer.lower() in ("o", "ok"):
        return "ok"
    if answer[:1].lower() == "w":
        reason = re.sub(r"^w(rong)?\s*[—:-]*\s*", "", answer, flags=re.IGNORECASE)
        return f"wrong — {reason}" if reason else None
    return None


def set_verdict(text: str, item: int, verdict: str) -> str:
    """The sheet with one item's verdict line replaced.

    Raises:
        KeyError: No item with that number.
    """
    head, blocks = split_blocks(text)
    for i, block in enumerate(blocks):
        if block_number(block) == item:
            blocks[i] = re.sub(r"(?m)^\*\*Verdict:\*\*.*$",
                               lambda _: f"**Verdict:** {verdict}", block, count=1)
            return head + "".join(blocks)
    raise KeyError(item)


def review(sheet: Path, read: Any = input) -> int:
    """Walk the pending items one by one and save each verdict at once.

    Returns:
        Items still pending when the walk ends.
    """
    text = sheet.read_text(encoding="utf-8")
    _, blocks = split_blocks(text)
    pending = [b for b in blocks if read_verdicts(b)[0][2] not in ("ok", "wrong")]
    for k, block in enumerate(pending, start=1):
        item = block_number(block)
        print("\n" + block.split("**Verdict:**")[0].rstrip())
        while True:
            answer = read(f"[{k}/{len(pending)}] item {item} — ok | w <reason> | "
                          "s skip | q quit: ")
            if answer.strip().lower() in ("q", "quit"):
                return _pending(text)
            if answer.strip().lower() in ("s", "skip", ""):
                break
            verdict = normalize_verdict(answer)
            if verdict is None:
                print("  write ok, or w followed by what is wrong")
                continue
            text = set_verdict(text, item, verdict)
            sheet.write_text(text, encoding="utf-8")
            print(f"  saved: {verdict}")
            break
    return _pending(text)


def _pending(text: str) -> int:
    return sum(1 for *_, v in read_verdicts(text) if v not in ("ok", "wrong"))


# --- CLI ------------------------------------------------------------------------


def _seen(audit_dir: Path) -> dict[str, list[str]]:
    path = audit_dir / "rounds.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="G3 audit of the generator.")
    parser.add_argument("command", choices=("draw", "review", "mark", "score"))
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing sheet (verdicts are lost)")
    parser.add_argument("--item", type=int, help="mark: the item number")
    parser.add_argument("--verdict", help="mark: ok, or 'wrong — <reason>'")
    args = parser.parse_args(argv)
    audit_dir = args.world_dir / "examiner" / "audit"
    sheet = audit_dir / f"g3-round-{args.round}.md"

    if args.command == "review":
        left = review(sheet)
        print(f"\n{left} item(s) pending; score with: "
              f"python -m agentic_pokedex.examiner.audit score --round {args.round}")
        return 0

    if args.command == "mark":
        verdict = normalize_verdict(args.verdict or "")
        if args.item is None or verdict is None:
            print("mark needs --item N and --verdict ok | 'w <reason>'")
            return 2
        sheet.write_text(set_verdict(sheet.read_text(encoding="utf-8"), args.item,
                                     verdict), encoding="utf-8")
        print(f"item {args.item}: {verdict}")
        return 0

    if args.command == "score":
        result = score(read_verdicts(sheet.read_text(encoding="utf-8")))
        (audit_dir / f"g3-round-{args.round}.json").write_text(
            json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(f"round {args.round}: {result['ok']} ok, {result['wrong']} wrong, "
              f"{result['pending']} pending, {result['unreadable']} unreadable "
              f"of {result['questions']} → {result['decision']} "
              f"(pass: ≥ {THRESHOLD})")
        for template, n in result["wrong_by_template"].items():
            print(f"  wrong in {template}: {n}")
        return 0 if result["decision"] == "pass" else 1

    if sheet.exists() and not args.force:
        print(f"{sheet} exists; its verdicts would be lost (use --force)")
        return 1
    from agentic_pokedex.world.download import DEFAULT_RAW_DIR
    from agentic_pokedex.world.pokeapi import VERSION_SCOPE, iter_learnsets, read_world
    from agentic_pokedex.world.render import build_world

    records = load_kept(args.world_dir)
    local = json.loads((args.world_dir / "examiner" / "splits.json").read_text(
        encoding="utf-8"))
    evaluation = {q for name in EVALUATION_SPLITS for q in local["splits"][name]}
    rounds = _seen(audit_dir)
    seen = {q for r, ids in rounds.items() if int(r) != args.round for q in ids}
    drawn = sample(audit_pool(records, evaluation, seen), families(records),
                   args.round)

    tables = read_world(DEFAULT_RAW_DIR)
    world = build_world(tables, list(iter_learnsets(DEFAULT_RAW_DIR, tables)),
                        VERSION_SCOPE)
    pages = {}
    with (args.world_dir / "pages" / "real.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            pages[row["id"]] = row["text"]
    audit_dir.mkdir(parents=True, exist_ok=True)
    sheet.write_text(render_sheet(args.round, drawn, Names.real(world), pages),
                     encoding="utf-8")
    rounds[str(args.round)] = [r["id"] for r in drawn]
    (audit_dir / "rounds.json").write_text(json.dumps(rounds, indent=1) + "\n",
                                           encoding="utf-8")
    per = Counter(r["stratum"] for r in drawn)
    print(f"round {args.round}: {len(drawn)} questions "
          f"({', '.join(f'{s} {per[s]}' for s in STRATA)}) → {sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
