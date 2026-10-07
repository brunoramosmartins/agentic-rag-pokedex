"""E-005, G2's closed-book half: A0 on twin and real-name questions.

50 questions per template, outside the evaluation splits, each asked twice with
no evidence: in twin names and in real names. A template fails G2 when the
Wilson 95% lower limit of A0's correct rate on the twin passes its chance rate
plus 5 points; real names are the positive control (registry, E-005). Graded
numbers are read only after the grader's audit (PI-024).

Usage::

    python -m agentic_pokedex.evaluation.closed_book prepare [--limit N] [--yes]
    python -m agentic_pokedex.evaluation.closed_book submit
    python -m agentic_pokedex.evaluation.closed_book collect   # until done
    python -m agentic_pokedex.evaluation.closed_book decide    # after the audit
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from agentic_pokedex.arms import single
from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.evaluation import batchrun
from agentic_pokedex.evaluation.batchrun import (
    MAX_COMPLETION_TOKENS,
    MODEL,
    REASONING,
    REASONING_EFFORT,
    VISIBLE_OUTPUT,
    RunDir,
    parse_custom_id,
)
from agentic_pokedex.evaluation.e002 import cluster_key
from agentic_pokedex.evaluation.grader import GoldAnswer, grade
from agentic_pokedex.evaluation.intervals import wilson

EXPERIMENT = "e005"
RUN_DIR = REPO_ROOT / "runs" / "e005"
CLOSED_BOOK_SEED = 20261008
"""Draws the 50 questions per template; registered in E-005 before the run."""

PER_TEMPLATE = 50
MARGIN = 0.05
CONTROL_TEMPLATES = ("S0-A1", "S0-A2", "S0-A3", "S0-A4")
CONTROL_NEEDED = 3
NAMINGS = ("twin", "real")

Record = Mapping[str, Any]


def sample(
    records: Sequence[Record], excluded: Iterable[str], seed: int = CLOSED_BOOK_SEED,
    per_template: int = PER_TEMPLATE,
) -> list[str]:
    """``per_template`` questions per template, never an excluded one; within a
    template, one per cluster before any cluster gives a second, in a seeded
    order."""
    rng = random.Random(seed)
    excluded = set(excluded)
    by_template: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list))
    for r in sorted(records, key=lambda r: r["id"]):
        if r["id"] not in excluded:
            by_template[r["template"]][cluster_key(r)].append(r["id"])
    chosen: list[str] = []
    for template in sorted(by_template):
        clusters = by_template[template]
        keys = sorted(clusters)
        rng.shuffle(keys)
        for key in keys:
            rng.shuffle(clusters[key])
        picked: list[str] = []
        while len(picked) < per_template and any(clusters[k] for k in keys):
            for key in keys:
                if clusters[key] and len(picked) < per_template:
                    picked.append(clusters[key].pop())
        chosen += picked
    return chosen


def chance(
    template: str, report: Mapping[str, Any], golds: Sequence[GoldAnswer]
) -> float:
    """A template's chance rate: its majority-answer rate after the cap, never
    below uniform; for S4, the majority share of the withheld values sampled."""
    cap = report.get(template, {}).get("cap", {})
    if cap.get("values"):
        return max(cap["majority_after"], 1.0 / cap["values"])
    values = Counter(json.dumps(g.value, sort_keys=True) for g in golds)
    return max(values.values()) / len(golds) if golds else 0.0


@dataclass(frozen=True)
class TemplateReading:
    """One template's reading in one naming."""

    template: str
    naming: str
    correct: int
    graded: int
    chance: float
    lower: float
    upper: float

    @property
    def above(self) -> bool:
        """Wilson lower limit above chance + 5 points."""
        return self.lower > self.chance + MARGIN


def read_template(
    template: str, naming: str, grades: Sequence[bool], chance_rate: float
) -> TemplateReading:
    """Correct rate with Wilson 95%."""
    n, k = len(grades), sum(grades)
    lo, hi = wilson(k, n) if n else (0.0, 0.0)
    return TemplateReading(template, naming, k, n, chance_rate, lo, hi)


def decide(readings: Sequence[TemplateReading]) -> dict[str, Any]:
    """G2's closed-book verdict (E-005's decision rule)."""
    twin = [r for r in readings if r.naming == "twin"]
    real = {r.template: r for r in readings if r.naming == "real"}
    control = [t for t in CONTROL_TEMPLATES if t in real and real[t].above]
    if len(control) < CONTROL_NEEDED:
        return {"verdict": "not evaluated: positive control failed",
                "control": f"{len(control)} of {len(CONTROL_TEMPLATES)}",
                "failing": []}
    failing = [r.template for r in twin if r.above]
    return {"verdict": "fail" if failing else "pass",
            "control": f"{len(control)} of {len(CONTROL_TEMPLATES)}",
            "failing": failing}


def correct_for_g2(completion: str | None, gold: GoldAnswer) -> bool:
    """"Correct" for G2: the right answer, or, in S4, the withheld value
    stated. An abstention is never correct here."""
    g = grade(completion, gold)
    if gold.expected == "abstain":
        return g.states_withheld
    return g.action == "answer" and g.correct


def real_question(record: Record, names: Any) -> str:
    """The question in real names, with the same surface form as its twin."""
    from agentic_pokedex.examiner.generate import GENERATOR_SEED, question_text
    from agentic_pokedex.world.twin import POKEMON_TERM

    q = SimpleNamespace(id=record["id"], template=record["template"],
                        slots=record["slots"])
    return question_text(q, names, POKEMON_TERM, GENERATOR_SEED)


def _names() -> tuple[Any, Any]:
    from agentic_pokedex.world.download import DEFAULT_RAW_DIR
    from agentic_pokedex.world.pokeapi import VERSION_SCOPE, iter_learnsets, read_world
    from agentic_pokedex.world.render import Names, build_world
    from agentic_pokedex.world.twin import DEFAULT_MAP_PATH, TwinMap

    tables = read_world(DEFAULT_RAW_DIR)
    world = build_world(tables, list(iter_learnsets(DEFAULT_RAW_DIR, tables)),
                        VERSION_SCOPE)
    return Names.twin(world, TwinMap.load(DEFAULT_MAP_PATH)), Names.real(world)


def prepare(run: RunDir, limit: int | None, yes: bool) -> int:
    """Draw the sample, build both namings' requests, print the estimate."""
    from agentic_pokedex.evaluation.grader import gold_answer
    from agentic_pokedex.examiner.splits import EVALUATION_SPLITS, opaque_id
    from agentic_pokedex.observability.pricing import Tier
    from agentic_pokedex.observability.tokens import (
        confirm_or_exit,
        count_chat_tokens,
        estimate_cost,
        load_encoder,
    )
    from agentic_pokedex.prompts import load_prompt
    from agentic_pokedex.world.index import DEFAULT_WORLD_DIR

    if (run.path / "state.json").exists():
        print(f"{run.path} already holds a run; refusing to overwrite it.")
        return 1
    world_dir = DEFAULT_WORLD_DIR
    local = json.loads((world_dir / "examiner" / "splits.json").read_text(
        encoding="utf-8"))
    excluded = {q for name in EVALUATION_SPLITS for q in local["splits"][name]}
    with (world_dir / "examiner" / "questions.jsonl").open(encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh]
    chosen = sample(records, excluded)
    by_id = {r["id"]: r for r in records}
    if limit is not None:
        per = max(1, limit // 16)
        taken: Counter[str] = Counter()
        kept = []
        for q in chosen:
            template = by_id[q]["template"]
            if taken[template] < per:
                taken[template] += 1
                kept.append(q)
        chosen = kept
    twin_names, real_names = _names()
    prompt = load_prompt(single.CLOSED_BOOK_PROMPT)
    encoder = load_encoder(MODEL)
    state: dict[str, Any] = {"single": {}}
    lines, tokens = [], []
    for local_id in chosen:
        r = by_id[local_id]
        q = opaque_id(local_id)
        texts = {"twin": r["twin_text"], "real": real_question(r, real_names)}
        golds = {"twin": gold_answer(r, twin_names),
                 "real": gold_answer(r, real_names)}
        for naming in NAMINGS:
            entry = {"arm": naming, "question": q, "local": local_id,
                     "template": r["template"], "stratum": r["stratum"],
                     "attempt": 0, "status": "pending",
                     "gold": {"kind": golds[naming].kind,
                              "expected": golds[naming].expected,
                              "value": golds[naming].value,
                              "aliases": list(golds[naming].aliases)},
                     "messages": single.user_messages(
                         single.closed_book_text(prompt.text, texts[naming]))}
            state["single"][f"{naming}|{q}"] = entry
            lines.append(batchrun.single_request(EXPERIMENT, entry, 0))
            tokens.append(count_chat_tokens(entry["messages"], encoder))
    estimate = estimate_cost(
        model=MODEL, tier=Tier.BATCH, calls=len(lines),
        input_tokens_per_call=sum(tokens) / len(tokens),
        visible_output_tokens_per_call=VISIBLE_OUTPUT, reasoning_scenarios=REASONING)
    confirm_or_exit(estimate, assume_yes=yes)
    run.save("state.json", state)
    run.write_round(lines)
    run.save("manifest.json", {
        "experiment": "E-005", "prepared_at": datetime.now(UTC).isoformat(),
        "model": MODEL, "reasoning_effort": REASONING_EFFORT,
        "max_completion_tokens": MAX_COMPLETION_TOKENS, "seed": CLOSED_BOOK_SEED,
        "limit": limit, "questions": [opaque_id(q) for q in chosen],
        "prompt": {prompt.name: prompt.sha256},
        "estimate_usd": dict(estimate.usd_by_scenario),
    })
    print(f"{len(lines)} requests ({len(chosen)} questions × 2 namings) written "
          f"to {run.path}")
    return 0


def collect(run: RunDir) -> int:
    """Fetch ended batches; write re-sends for failures."""
    from openai import OpenAI

    from agentic_pokedex.config import load_env

    load_env()
    results, running = run.collect(OpenAI())
    state = run.load("state.json")
    nxt = []
    round_ = run.next_round()
    for res in results:
        _, naming, question, _, _ = parse_custom_id(res.custom_id)
        entry = state["single"][f"{naming}|{question}"]
        line = batchrun.apply_single(EXPERIMENT, entry, res, round_)
        if line:
            nxt.append(line)
    run.save("state.json", state)
    if run.write_round(nxt):
        print(f"{len(nxt)} re-sends written; run `submit`")
    pending = sum(e["status"] == "pending" for e in state["single"].values())
    print(f"{len(results)} results; pending {pending}; batches still running: "
          f"{', '.join(running) or 'none'}")
    return 0


def readings(
    state: Mapping[str, Any], report: Mapping[str, Any]
) -> list[TemplateReading]:
    """Per template and naming, from a finished state."""
    grouped: dict[tuple[str, str], list[tuple[bool, GoldAnswer]]] = defaultdict(list)
    for e in state["single"].values():
        g = e["gold"]
        gold = GoldAnswer(g["kind"], g["expected"], g["value"], tuple(g["aliases"]))
        ok = e["status"] == "done" and correct_for_g2(e.get("completion"), gold)
        grouped[(e["template"], e["arm"])].append((ok, gold))
    out = []
    for (template, naming), rows in sorted(grouped.items()):
        rate = chance(template, report, [gold for _, gold in rows])
        out.append(read_template(template, naming, [ok for ok, _ in rows], rate))
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="E-005, G2 closed-book.")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--limit", type=int, default=None,
                      help="about N questions in all (N/16 per template)")
    prep.add_argument("--yes", action="store_true")
    for p in (prep, *(sub.add_parser(n) for n in ("submit", "collect", "decide"))):
        p.add_argument("--run-dir", type=Path, default=RUN_DIR)
    args = parser.parse_args(argv)
    run = RunDir(args.run_dir)
    if args.command == "prepare":
        return prepare(run, args.limit, args.yes)
    if args.command == "submit":
        from openai import OpenAI

        from agentic_pokedex.config import load_env

        load_env()
        ids = run.submit_unsent(OpenAI(), EXPERIMENT)
        print(f"submitted {len(ids)} batch(es): {', '.join(ids) or '—'}")
        return 0
    if args.command == "collect":
        return collect(run)
    audit = REPO_ROOT / "runs" / "grader-audit" / "result.json"
    if not audit.is_file() or json.loads(audit.read_text())["decision"] != "pass":
        print("The grader's audit (gate 4) has not passed: no graded number is "
              "read before it (PI-024).")
        return 1
    from agentic_pokedex.world.index import DEFAULT_WORLD_DIR

    report = json.loads((DEFAULT_WORLD_DIR / "examiner" / "report.json").read_text())
    rows = readings(run.load("state.json"), report)
    for r in rows:
        print(f"{r.template:<7} {r.naming:<5} {r.correct:>3} of {r.graded:<3} "
              f"Wilson {r.lower:.0%}–{r.upper:.0%}  chance {r.chance:.0%}"
              f"{'  ABOVE chance + 5' if r.above else ''}")
    print(json.dumps(decide(rows), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
