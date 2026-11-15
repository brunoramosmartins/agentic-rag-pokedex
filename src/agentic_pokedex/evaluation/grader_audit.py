"""Gate 4: the grader's audit on 100 stratified outputs (PI-024).

The grader is right when its verdict — answer, abstention or format error;
correct or not; the cost — is what a careful reader concludes from the
completion and the gold. 100 outputs of E-004 and E-005 are drawn, 20 per
stratum, round-robin over their sources (each E-004 arm, each E-005 naming),
format errors first and answered outputs before abstentions (an abstention is
the easy case). The auditor marks each item ``ok`` (the grader is right) or
``wrong — <why>``. Pass: at least 98 of 100. Until the audit passes, no graded
number of E-004 or E-005 is read. A failed round is followed, after the grader
is fixed, by a round on a **fresh sample**: seed ``AUDIT_SEED + round − 1``,
excluding every output an earlier round drew.

The sheet is local (``runs/grader-audit/``): E-005 items carry real names.

Usage::

    python -m agentic_pokedex.evaluation.grader_audit draw --round 2
    python -m agentic_pokedex.evaluation.grader_audit review --round 2
    python -m agentic_pokedex.evaluation.grader_audit mark --round 2 --item 7 \\
        --verdict ok
    python -m agentic_pokedex.evaluation.grader_audit score --round 2
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.evaluation.grader import GoldAnswer, grade

AUDIT_DIR = REPO_ROOT / "runs" / "grader-audit"
AUDIT_SEED = 20261009
PER_STRATUM = 20
THRESHOLD = 98
STRATA = ("S0", "S1", "S2", "S3", "S4")
_ITEM = re.compile(r"(?m)^## \d+\. \S+?/(\S+) — (q-[0-9a-f]+)\s*$")


@dataclass(frozen=True)
class Output:
    """One graded output.

    Attributes:
        source: ``e004-A0`` … ``e004-A3``, ``e005-twin``, ``e005-real``.
        question: Opaque question id.
        template: Template.
        text: The question as the model saw it.
        completion: The model's final output (``None`` after API failures).
        gold: The gold in the naming the model saw.
    """

    source: str
    question: str
    template: str
    text: str
    completion: str | None
    gold: GoldAnswer

    @property
    def stratum(self) -> str:
        """The template's stratum."""
        return self.template[:2]


def _gold(data: Mapping[str, Any]) -> GoldAnswer:
    return GoldAnswer(data["kind"], data["expected"], data["value"],
                      tuple(data.get("aliases", ())))


def _question_text(messages: Sequence[Mapping[str, Any]]) -> str:
    content = messages[0]["content"]
    return content.split("Question: ")[-1].split("\n\nEvidence:\n")[0].strip()


def outputs_e005(state: Mapping[str, Any]) -> list[Output]:
    """E-005's outputs (each entry stores its gold)."""
    return [Output(f"e005-{e['arm']}", e["question"], e["template"],
                   _question_text(e["messages"]), e.get("completion"),
                   _gold(e["gold"]))
            for e in state["single"].values() if e["status"] != "pending"]


def outputs_e004(
    state: Mapping[str, Any], golds: Mapping[str, GoldAnswer],
    templates: Mapping[str, str],
) -> list[Output]:
    """E-004's outputs; ``golds`` and ``templates`` by local question id."""
    out = [Output(f"e004-{e['arm']}", e["question"], templates[e["local"]],
                  _question_text(e["messages"]), e.get("completion"),
                  golds[e["local"]])
           for e in state["single"].values() if e["status"] != "pending"]
    for data in state["agent"].values():
        run = data["state"]
        out.append(Output("e004-A3", run["question"], templates[data["local"]],
                          _question_text(run["messages"]), run["final"],
                          golds[data["local"]]))
    return out


def sheet_path(round_: int) -> Path:
    """The sheet of a round."""
    return AUDIT_DIR / f"sheet-r{round_}.md"


def result_path(round_: int) -> Path:
    """The scored result of a round."""
    return AUDIT_DIR / f"result-r{round_}.json"


def latest_result() -> dict[str, Any] | None:
    """The result of the last scored round, or ``None``."""
    rounds = sorted(AUDIT_DIR.glob("result-r*.json"),
                    key=lambda p: int(p.stem.split("-r")[1]))
    return json.loads(rounds[-1].read_text(encoding="utf-8")) if rounds else None


def drawn_before(round_: int) -> set[tuple[str, str]]:
    """(source, question) of every item earlier rounds drew."""
    seen: set[tuple[str, str]] = set()
    for r in range(1, round_):
        path = sheet_path(r)
        if path.is_file():
            for m in _ITEM.finditer(path.read_text(encoding="utf-8")):
                seen.add((m.group(1), m.group(2)))
    return seen


def sample(
    outputs: Sequence[Output], seed: int = AUDIT_SEED, per_stratum: int = PER_STRATUM,
    exclude: frozenset[tuple[str, str]] | set[tuple[str, str]] = frozenset(),
) -> list[Output]:
    """``per_stratum`` outputs per stratum: format errors first, then answered
    outputs, then abstentions, round-robin over sources in a seeded order."""
    rng = random.Random(seed)
    rank = {"format-error": 0, "answer": 1, "abstain": 2}
    chosen: list[Output] = []
    for stratum in STRATA:
        by_source: dict[str, list[Output]] = defaultdict(list)
        for o in sorted(outputs, key=lambda o: (o.source, o.question)):
            if o.stratum == stratum and (o.source, o.question) not in exclude:
                by_source[o.source].append(o)
        sources = sorted(by_source)
        rng.shuffle(sources)
        for s in sources:
            rng.shuffle(by_source[s])
            by_source[s].sort(key=lambda o: rank[grade(o.completion, o.gold).action])
        picked: list[Output] = []
        while len(picked) < per_stratum and any(by_source[s] for s in sources):
            for s in sources:
                if by_source[s] and len(picked) < per_stratum:
                    picked.append(by_source[s].pop(0))
        chosen += picked
    return chosen


def render_item(n: int, o: Output) -> str:
    """One item of the sheet."""
    g = grade(o.completion, o.gold)
    value = o.gold.value
    value = " / ".join(map(str, value)) if isinstance(value, list) else value
    aliases = f"; aliases {', '.join(o.gold.aliases)}" if o.gold.aliases else ""
    completion = "\n".join("    " + line
                           for line in (o.completion or "(none)").splitlines())
    expected = (f"abstain (withheld value: {value})"
                if o.gold.expected == "abstain" else f"{value}{aliases}")
    return (f"## {n}. {o.template}/{o.source} — {o.question}\n\n"
            f"**Question:** {o.text}\n\n"
            f"**Gold ({o.gold.kind}):** {expected}\n\n"
            f"**Completion:**\n\n{completion}\n\n"
            f"**Grader:** {g.action} · correct {'yes' if g.correct else 'no'} · "
            f"C {g.cost:g}\n\n"
            f"**Verdict:** \n\n")


def render_sheet(items: Sequence[Output]) -> str:
    """The audit sheet."""
    head = ("# Grader audit (gate 4)\n\n"
            "For each item, is the grader's verdict right for this completion and "
            "this gold? Write `ok`, or `wrong — <why>`. Judge the grader, not the "
            f"model. Pass: at least {THRESHOLD} of {len(items)}.\n\n")
    return head + "".join(render_item(n, o) for n, o in enumerate(items, start=1))


def score(verdicts: Sequence[tuple[str, str, str]]) -> dict[str, Any]:
    """Counts and the gate 4 decision."""
    states = Counter(v for _, _, v in verdicts)
    wrong = Counter(t for t, _, v in verdicts if v == "wrong")
    complete = not states["pending"] and not states["unreadable"]
    return {
        "items": len(verdicts), "ok": states["ok"], "wrong": states["wrong"],
        "pending": states["pending"], "unreadable": states["unreadable"],
        "wrong_by_item_kind": dict(sorted(wrong.items())),
        "decision": ("pending" if not complete
                     else "pass" if states["ok"] >= THRESHOLD else "fail"),
    }


def _e004_golds(state: Mapping[str, Any]) -> tuple[dict, dict]:
    from agentic_pokedex.evaluation.closed_book import _names
    from agentic_pokedex.evaluation.grader import gold_answer
    from agentic_pokedex.world.index import DEFAULT_WORLD_DIR

    wanted = {e["local"] for e in state["single"].values()} | {
        d["local"] for d in state["agent"].values()}
    twin, _ = _names()
    golds, templates = {}, {}
    with (DEFAULT_WORLD_DIR / "examiner" / "questions.jsonl").open(
            encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["id"] in wanted:
                golds[r["id"]] = gold_answer(r, twin)
                templates[r["id"]] = r["template"]
    return golds, templates


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    from agentic_pokedex.examiner.audit import read_verdicts, review, set_verdict

    parser = argparse.ArgumentParser(description="Gate 4: the grader's audit.")
    sub = parser.add_subparsers(dest="command", required=True)
    commands = {name: sub.add_parser(name) for name in
                ("draw", "review", "mark", "score")}
    for p in commands.values():
        p.add_argument("--round", type=int, default=1)
    commands["mark"].add_argument("--item", type=int, required=True)
    commands["mark"].add_argument("--verdict", required=True,
                                  help="ok, or 'wrong — why'")
    args = parser.parse_args(argv)
    sheet = sheet_path(args.round)
    if args.command == "draw":
        if sheet.exists():
            print(f"{sheet} exists; refusing to redraw over verdicts.")
            return 1
        earlier = latest_result()
        if args.round > 1 and (earlier is None or earlier["decision"] == "pass"):
            print("A new round follows a scored, failed round only.")
            return 1
        runs = REPO_ROOT / "runs"
        e004 = json.loads((runs / "e004" / "state.json").read_text(encoding="utf-8"))
        e005 = json.loads((runs / "e005" / "state.json").read_text(encoding="utf-8"))
        golds, templates = _e004_golds(e004)
        items = sample(outputs_e004(e004, golds, templates) + outputs_e005(e005),
                       seed=AUDIT_SEED + args.round - 1,
                       exclude=drawn_before(args.round))
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        sheet.write_text(render_sheet(items), encoding="utf-8")
        mix = Counter(o.source for o in items)
        print(f"{len(items)} items written to {sheet}; "
              f"by source {dict(sorted(mix.items()))}")
        return 0
    if args.command == "review":
        left = review(sheet)
        print(f"{left} item(s) still pending")
        return 0
    if args.command == "mark":
        text = sheet.read_text(encoding="utf-8")
        sheet.write_text(set_verdict(text, args.item, args.verdict), encoding="utf-8")
        print(f"item {args.item}: {args.verdict}")
        return 0
    result = score(read_verdicts(sheet.read_text(encoding="utf-8")))
    result["round"] = args.round
    result_path(args.round).write_text(json.dumps(result, indent=1) + "\n",
                                       encoding="utf-8")
    print(f"round {args.round}: {result['ok']} ok, {result['wrong']} wrong, "
          f"{result['pending']} pending, {result['unreadable']} unreadable of "
          f"{result['items']} → {result['decision']} (pass: ≥ {THRESHOLD})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
