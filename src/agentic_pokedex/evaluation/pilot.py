"""E-004, the pilot: noise, cost and reasoning per arm (registry, E-004).

A0, A1 and A2 answer dev's 150 questions in one call each; A3 runs the agent
loop on 30 dev S1–S4 questions, one Batch round per step. The report prints
tokens, reasoning, steps, the implicit detector's firing rate and B binding —
never a difference between arms, and no mean C per arm. The proxy SD of D
needs graded answers, read only after the grader's audit (PI-024).

Usage::

    python -m agentic_pokedex.evaluation.pilot prepare [--limit N] [--yes]
    python -m agentic_pokedex.evaluation.pilot submit
    python -m agentic_pokedex.evaluation.pilot collect     # repeat until done
    python -m agentic_pokedex.evaluation.pilot report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from agentic_pokedex.arms import agent as agent_arm
from agentic_pokedex.arms import single
from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.evaluation import batchrun
from agentic_pokedex.evaluation.batchrun import (
    MAX_COMPLETION_TOKENS,
    MAX_TRIES,
    MODEL,
    REASONING,
    REASONING_EFFORT,
    VISIBLE_OUTPUT,
    RunDir,
    custom_id,
    parse_custom_id,
)
from agentic_pokedex.evaluation.e002 import cluster_key
from agentic_pokedex.llm.batch import BatchResult, chat_request

EXPERIMENT = "e004"
RUN_DIR = REPO_ROOT / "runs" / "e004"
PILOT_SEED = 20261007
"""Draws the 30 A3 questions; registered in E-004 before the run."""

AGENT_QUESTIONS = 30
SINGLE_ARMS = ("A0", "A1", "A2")
AGENT_ARM = "A3"
AGENT_STEPS_ASSUMED = 4
"""Steps per A3 question assumed by the estimate (T_max is 6)."""

Record = Mapping[str, Any]


def sample_agent_questions(
    records: Sequence[Record], seed: int = PILOT_SEED, n: int = AGENT_QUESTIONS
) -> list[str]:
    """The A3 questions: dev S1–S4, as even as n allows, one per cluster first.

    Strata get ``n // 4`` each, and the remainder goes to strata in a seeded
    order. Within a stratum, questions are taken round-robin over their
    clusters in a seeded order, so a cluster gives a second question only
    after every cluster has given one.
    """
    rng = random.Random(seed)
    strata = ["S1", "S2", "S3", "S4"]
    share = {s: n // len(strata) for s in strata}
    extra = strata[:]
    rng.shuffle(extra)
    for s in extra[: n - sum(share.values())]:
        share[s] += 1
    chosen: list[str] = []
    for s in strata:
        clusters: dict[str, list[str]] = defaultdict(list)
        for r in sorted(records, key=lambda r: r["id"]):
            if r["stratum"] == s:
                clusters[cluster_key(r)].append(r["id"])
        keys = sorted(clusters)
        rng.shuffle(keys)
        for key in keys:
            rng.shuffle(clusters[key])
        picked: list[str] = []
        while len(picked) < share[s] and any(clusters[k] for k in keys):
            for key in keys:
                if clusters[key] and len(picked) < share[s]:
                    picked.append(clusters[key].pop())
        chosen += picked
    return chosen


def single_request(entry: Mapping[str, Any], round_: int) -> dict[str, Any]:
    """The Batch line of a one-call arm."""
    return batchrun.single_request(EXPERIMENT, entry, round_)


def agent_request(
    state: agent_arm.AgentState, round_: int, attempt: int, final_prompt: str
) -> dict[str, Any]:
    """The Batch line of the agent's next turn."""
    messages, offer = agent_arm.turn_messages(state, final_prompt)
    return chat_request(
        custom_id(EXPERIMENT, AGENT_ARM, state.question, round_, attempt),
        model=MODEL, messages=messages,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        reasoning_effort=REASONING_EFFORT,
        tools=agent_arm.TOOLS if offer else None,
    )


def apply_results(
    state: dict[str, Any], results: Sequence[BatchResult], world: Any,
    counter: Any, final_prompt: str, round_: int,
) -> list[dict[str, Any]]:
    """Fold a round's results into the state; return the next round's lines.

    One-call arms are done on success; an API failure is re-sent on the same
    question up to ``MAX_TRIES`` times, then recorded as failed (C = λ). The
    agent advances a step, or is re-sent its turn after a failure.
    """
    nxt: list[dict[str, Any]] = []
    for res in results:
        _, arm, question, _, _ = parse_custom_id(res.custom_id)
        if arm in SINGLE_ARMS:
            entry = state["single"][f"{arm}|{question}"]
            line = batchrun.apply_single(EXPERIMENT, entry, res, round_)
            if line:
                nxt.append(line)
        else:
            data = state["agent"][question]
            run = agent_arm.AgentState.from_dict(data["state"])
            if run.done:
                continue
            if res.error is not None:
                agent_arm.fail(run, MAX_TRIES)
                data["attempt"] += 1
            else:
                agent_arm.advance(run, res, world, counter)
                data["attempt"] = 0
            if not run.done:
                nxt.append(agent_request(run, round_, data["attempt"], final_prompt))
            data["state"] = run.to_dict()
    return nxt


def usage_rows(state: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Every call's usage, per arm."""
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in state["single"].values():
        if entry.get("usage"):
            rows[entry["arm"]].append(entry["usage"])
    for data in state["agent"].values():
        for turn in data["state"]["turns"]:
            if turn.get("usage"):
                rows[AGENT_ARM].append(turn["usage"])
    return dict(rows)


def _dist(values: Sequence[float]) -> str:
    if not values:
        return "—"
    v = sorted(values)
    p90 = v[min(len(v) - 1, int(0.9 * len(v)))]
    return f"median {median(v):,.0f} · p90 {p90:,.0f} · max {v[-1]:,.0f}"


def describe(state: Mapping[str, Any]) -> dict[str, Any]:
    """What the pilot reports: tokens per arm, A3's steps and firing rate.

    No grade, no C: those wait for the grader's audit (PI-024).
    """
    from agentic_pokedex.observability.pricing import Tier
    from agentic_pokedex.observability.tokens import Usage, cost_usd

    out: dict[str, Any] = {"arms": {}}
    for arm, rows in sorted(usage_rows(state).items()):
        usage = [Usage(**r) for r in rows]
        total = sum(usage, Usage(0))
        out["arms"][arm] = {
            "calls": len(rows),
            "input": _dist([u.input_tokens for u in usage]),
            "output": _dist([u.output_tokens for u in usage]),
            "reasoning": _dist([u.reasoning_tokens for u in usage]),
            "at_the_cap": sum(u.output_tokens >= MAX_COMPLETION_TOKENS for u in usage),
            "cost_usd": round(cost_usd(total, MODEL, Tier.BATCH), 4),
        }
    runs = [agent_arm.AgentState.from_dict(d["state"])
            for d in state["agent"].values()]
    ended = [r for r in runs if r.done]
    if ended:
        out["A3"] = {
            "questions": f"{len(ended)} of {len(runs)} ended",
            "steps": dict(sorted(Counter(r.calls for r in ended).items())),
            "searched_again_after_first": sum(r.calls >= 2 for r in ended),
            "b_spent": sum(r.budget_spent for r in ended),
            "t_max_reached": sum(r.calls >= agent_arm.T_MAX for r in ended),
            "api_failures": sum(r.failed for r in ended),
        }
    out["single_failed"] = sum(e["status"] == "failed"
                               for e in state["single"].values())
    return out


def render_case(state: Mapping[str, Any], arm: str) -> str:
    """One case of an arm: prompt (head), evidence size, completion."""
    if arm == AGENT_ARM:
        data = next(iter(state["agent"].values()))
        run = data["state"]
        lines = [f"[{arm} {run['question']}]",
                 run["messages"][0]["content"][-300:]]
        for step in run["steps"]:
            lines.append(f"  → {step['tool']}({step['arguments']}) "
                         f"{len(step['units'])} units, {step['tokens']} tokens")
        lines.append(f"  final: {run['final']!r}")
        return "\n".join(lines)
    entry = next(e for e in state["single"].values() if e["arm"] == arm)
    content = entry["messages"][0]["content"]
    return (f"[{arm} {entry['question']}] evidence {entry['evidence']['tokens']} "
            f"tokens, {len(entry['evidence']['units'])} units\n"
            f"{content[:400]}…\n  completion: {entry.get('completion')!r}")


def sha256_file(path: Path) -> str:
    """SHA-256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="E-004, the pilot.")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--limit", type=int, default=None,
                      help="first N dev questions per one-call arm, N/5 for A3")
    prep.add_argument("--yes", action="store_true")
    prep.add_argument("--run-dir", type=Path, default=RUN_DIR)
    for name in ("submit", "collect", "report"):
        p = sub.add_parser(name)
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
    print(json.dumps(describe(run.load("state.json")), indent=1))
    state = run.load("state.json")
    for arm in (*SINGLE_ARMS, AGENT_ARM):
        print("\n" + render_case(state, arm))
    return 0


def _world() -> tuple[Any, Any, Any]:
    from agentic_pokedex.arms.typed_expansion import World
    from agentic_pokedex.tools.contract import default_counter
    from agentic_pokedex.world.index import (
        DEFAULT_WORLD_DIR,
        FastEmbedder,
        build_index,
    )
    from agentic_pokedex.world.registry import Registry

    registry = Registry.load(DEFAULT_WORLD_DIR / "registry.json")
    index = build_index(DEFAULT_WORLD_DIR, "twin",
                        FastEmbedder(cache_dir=DEFAULT_WORLD_DIR / "models"))
    return World.build(index, registry), registry, default_counter()


def prepare(run: RunDir, limit: int | None, yes: bool) -> int:
    """Draw the A3 questions, build round 0, print the estimate."""
    from agentic_pokedex.examiner.splits import opaque_id, open_split
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
    world, _, counter = _world()
    dev = open_split("dev", "", world_dir=DEFAULT_WORLD_DIR)
    wanted = set(dev)
    with (DEFAULT_WORLD_DIR / "examiner" / "questions.jsonl").open(
            encoding="utf-8") as fh:
        by_id = {r["id"]: r for r in map(json.loads, fh) if r["id"] in wanted}
    records = [by_id[q] for q in dev]
    agent_ids = sample_agent_questions(records)
    if limit is not None:
        records = records[:limit]
        agent_ids = agent_ids[: max(1, limit // 5)]
    prompts = {name: load_prompt(name) for name in (
        single.CLOSED_BOOK_PROMPT, single.EVIDENCE_PROMPT,
        agent_arm.AGENT_PROMPT, agent_arm.FINAL_PROMPT)}
    encoder = load_encoder(MODEL)
    state: dict[str, Any] = {"single": {}, "agent": {}}
    lines, input_tokens = [], []
    for r in records:
        q, text = opaque_id(r["id"]), r["twin_text"]
        evidence = {
            "A0": single.Evidence((), 0, ""),
            "A1": single.single_shot(world, text, counter),
            "A2": single.fixed_pipeline(world, text, counter),
        }
        for arm in SINGLE_ARMS:
            body = (single.closed_book_text(prompts[single.CLOSED_BOOK_PROMPT].text,
                                            text) if arm == "A0" else
                    single.evidence_text(prompts[single.EVIDENCE_PROMPT].text, text,
                                         evidence[arm]))
            entry = {"arm": arm, "question": q, "local": r["id"], "attempt": 0,
                     "status": "pending", "messages": single.user_messages(body),
                     "evidence": {"units": list(evidence[arm].units),
                                  "tokens": evidence[arm].tokens}}
            state["single"][f"{arm}|{q}"] = entry
            lines.append(single_request(entry, 0))
            input_tokens.append(count_chat_tokens(entry["messages"], encoder))
    agent_input = []
    for local in agent_ids:
        q = opaque_id(local)
        st = agent_arm.start(q, by_id[local]["twin_text"],
                             prompts[agent_arm.AGENT_PROMPT].text)
        state["agent"][q] = {"local": local, "attempt": 0, "state": st.to_dict()}
        lines.append(agent_request(st, 0, 0, prompts[agent_arm.FINAL_PROMPT].text))
        agent_input.append(count_chat_tokens(st.messages, encoder))
    # The agent's later turns carry its earlier observations: about one 700-token
    # result more per step, AGENT_STEPS_ASSUMED steps and a final turn.
    steps = AGENT_STEPS_ASSUMED + 1
    for base in agent_input:
        input_tokens += [base + 700 * i for i in range(steps)]
    estimate = estimate_cost(
        model=MODEL, tier=Tier.BATCH, calls=len(input_tokens),
        input_tokens_per_call=sum(input_tokens) / len(input_tokens),
        visible_output_tokens_per_call=VISIBLE_OUTPUT, reasoning_scenarios=REASONING)
    confirm_or_exit(estimate, assume_yes=yes)
    run.save("state.json", state)
    run.write_round(lines)
    run.save("manifest.json", {
        "experiment": "E-004", "prepared_at": datetime.now(UTC).isoformat(),
        "model": MODEL, "reasoning_effort": REASONING_EFFORT,
        "max_completion_tokens": MAX_COMPLETION_TOKENS, "seed": PILOT_SEED,
        "limit": limit, "agent_questions": [opaque_id(q) for q in agent_ids],
        "prompts": {n: p.sha256 for n, p in prompts.items()},
        "sha256": {
            "pages/twin.jsonl": sha256_file(DEFAULT_WORLD_DIR / "pages" / "twin.jsonl"),
            "registry.json": sha256_file(DEFAULT_WORLD_DIR / "registry.json"),
            "data/splits/dev.txt": sha256_file(REPO_ROOT / "data" / "splits"
                                               / "dev.txt"),
        },
        "estimate_usd": dict(estimate.usd_by_scenario),
    })
    print(f"{len(lines)} round-0 requests written to {run.path}")
    return 0


def collect(run: RunDir) -> int:
    """Fetch ended batches, advance the agent, write the next round."""
    from openai import OpenAI

    from agentic_pokedex.config import load_env
    from agentic_pokedex.prompts import load_prompt

    load_env()
    results, running = run.collect(OpenAI())
    state = run.load("state.json")
    if results:
        world, _, counter = _world()
        final = load_prompt(agent_arm.FINAL_PROMPT).text
        nxt = apply_results(state, results, world, counter, final, run.next_round())
        run.save("state.json", state)
        path = run.write_round(nxt)
        if path:
            print(f"next round: {len(nxt)} requests in {path.name}; run `submit`")
    pending = sum(e["status"] == "pending" for e in state["single"].values())
    open_runs = sum(not d["state"]["done"] for d in state["agent"].values())
    print(f"{len(results)} results; one-call pending {pending}; A3 running "
          f"{open_runs}; batches still running: {', '.join(running) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
