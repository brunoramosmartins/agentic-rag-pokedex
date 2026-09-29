"""E-003, the identity probe, through the Batch API.

Three steps, each re-runnable; state lives in ``runs/e003/`` for run 1 and
``runs/e003-run{n}/`` for later runs (gitignored):

    python scripts/identity_probe.py [--run N] prepare [--limit N] [--yes]
    python scripts/identity_probe.py [--run N] submit [--file F]
                                     [--max-completion-tokens M]
    python scripts/identity_probe.py [--run N] collect

``prepare`` samples the species (run 2 excludes run 1's), builds each
condition's page, counts the input tokens locally, prints the estimated cost and
asks before writing the requests. ``submit`` uploads a request file as a batch.
``collect`` downloads every finished batch (raw outputs kept), keeps the first
valid answer per request, grades, prints the report with the bounded decision
rule, and writes ``retry.jsonl`` for invalid answers.

Runs (``identity_probe.RUNS``): 1 — three conditions on the world with notes;
2 — the G2 exit: control and twin on the world rendered without notes.

Requires the ``llm`` and ``retrieval`` extras, the world built
(``data/world/``: registry and the real and twin page files) and
``OPENAI_API_KEY`` (environment, or ``.env``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from agentic_pokedex.config import load_env
from agentic_pokedex.evaluation import identity_probe as probe
from agentic_pokedex.llm.batch import (
    BatchResult,
    chat_request,
    fetch,
    parse_output_line,
    read_jsonl,
    submit,
    write_jsonl,
)
from agentic_pokedex.observability.pricing import Tier
from agentic_pokedex.observability.tokens import (
    UsageMeter,
    add_cost_guard_args,
    confirm_or_exit,
    count_chat_tokens,
    estimate_cost,
    load_encoder,
)
from agentic_pokedex.prompts import load_prompt
from agentic_pokedex.tools.contract import default_counter
from agentic_pokedex.world.download import DEFAULT_RAW_DIR
from agentic_pokedex.world.index import DEFAULT_WORLD_DIR, load_units
from agentic_pokedex.world.pokeapi import VERSION_SCOPE, iter_learnsets, read_world
from agentic_pokedex.world.registry import Registry
from agentic_pokedex.world.render import World, build_world

PROMPT = "identity_probe"
ENDED = ("completed", "failed", "expired", "cancelled")


def run_dir(run: int) -> Path:
    """Where a run keeps its state."""
    return Path("runs/e003") if run == 1 else Path(f"runs/e003-run{run}")


def load_world() -> World:
    tables = read_world(DEFAULT_RAW_DIR)
    learn_rows = list(iter_learnsets(DEFAULT_RAW_DIR, tables))
    return build_world(tables, learn_rows, VERSION_SCOPE)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_prepare(args: argparse.Namespace) -> int:
    config = probe.RUNS[args.run]
    out = run_dir(args.run)
    world = load_world()
    exclude: list[int] = []
    if config.exclude_run:
        earlier = run_dir(config.exclude_run) / "manifest.json"
        exclude = json.loads(earlier.read_text())["species"]
    species = probe.sample_species(world, seed=config.seed, exclude=exclude)
    if args.limit:
        species = species[: args.limit]

    registry = Registry.load(DEFAULT_WORLD_DIR / "registry.json")
    pages = {
        name: DEFAULT_WORLD_DIR / "pages" / f"{name}.jsonl" for name in ("real", "twin")
    }
    real_units = load_units(pages["real"], registry)
    twin_units = load_units(pages["twin"], registry)
    has_notes = any(u.section == "Notes" for u in twin_units)
    if has_notes != config.notes_expected:
        expected = "with" if config.notes_expected else "without"
        found = "has" if has_notes else "has no"
        print(f"Run {args.run} expects a world {expected} notes, but data/world "
              f"{found} notes. Re-render first.")
        return 1

    prompt = load_prompt(PROMPT)
    counter = default_counter()
    encoder = load_encoder(probe.MODEL)
    requests, input_tokens = [], []
    for sid in species:
        for condition in config.conditions:
            page = probe.condition_page(
                condition, sid, world, real_units, twin_units, counter
            )
            messages = [
                {"role": "system", "content": prompt.text},
                {"role": "user", "content": page},
            ]
            input_tokens.append(count_chat_tokens(messages, encoder))
            requests.append(
                chat_request(
                    probe.custom_id(condition, sid, args.run),
                    model=probe.MODEL,
                    messages=messages,
                    max_completion_tokens=probe.MAX_COMPLETION_TOKENS,
                    reasoning_effort=probe.REASONING_EFFORT,
                    response_format=probe.RESPONSE_FORMAT,
                )
            )

    estimate = estimate_cost(
        model=probe.MODEL,
        tier=Tier.BATCH,
        calls=len(requests),
        input_tokens_per_call=sum(input_tokens) / len(input_tokens),
        visible_output_tokens_per_call=probe.VISIBLE_OUTPUT_TOKENS,
    )
    confirm_or_exit(estimate, assume_yes=args.yes)

    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "requests.jsonl", requests)
    manifest = {
        "experiment": "E-003",
        "run": args.run,
        "prepared_at": datetime.now(UTC).isoformat(),
        "model": probe.MODEL,
        "reasoning_effort": probe.REASONING_EFFORT,
        "max_completion_tokens": probe.MAX_COMPLETION_TOKENS,
        "prompt": {"name": prompt.name, "sha256": prompt.sha256},
        "seed": config.seed,
        "conditions": list(config.conditions),
        "excluded_species": exclude,
        "species": species,
        "limit": args.limit,
        "pages_sha256": {name: sha256_file(path) for name, path in pages.items()},
        "registry_sha256": sha256_file(DEFAULT_WORLD_DIR / "registry.json"),
        "estimate_usd": dict(estimate.usd_by_scenario),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(requests)} requests written to {out / 'requests.jsonl'}")
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    from openai import OpenAI

    load_env()
    out = run_dir(args.run)
    path = out / args.file
    if args.max_completion_tokens:
        # Amendment of 2026-09-29: re-sends may raise the output cap. The
        # rewritten file is kept beside the original for the audit trail.
        rows = read_jsonl(path)
        for row in rows:
            row["body"]["max_completion_tokens"] = args.max_completion_tokens
        path = path.with_name(f"{path.stem}-mct{args.max_completion_tokens}.jsonl")
        write_jsonl(path, rows)
    metadata = {"experiment": "E-003", "run": str(args.run), "file": path.name}
    batch_id = submit(OpenAI(), path, metadata=metadata)
    batches_path = out / "batches.json"
    batches = json.loads(batches_path.read_text()) if batches_path.is_file() else []
    batches.append({"id": batch_id, "file": path.name,
                    "submitted_at": datetime.now(UTC).isoformat()})
    batches_path.write_text(json.dumps(batches, indent=2) + "\n")
    print(f"Batch {batch_id} submitted ({path.name}). Run `collect` when it ends.")
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    from openai import OpenAI

    load_env()
    out = run_dir(args.run)
    client = OpenAI()
    batches = json.loads((out / "batches.json").read_text())
    meter = UsageMeter(model=probe.MODEL, tier=Tier.BATCH)
    results: dict[str, BatchResult] = {}
    pending = []
    # Batches in submission order; per request, the FIRST valid answer is kept
    # (a later one never replaces it), so no answer is chosen after the fact.
    for batch in batches:
        status, raw = fetch(client, batch["id"])
        batch["status"] = status
        if status not in ENDED:
            pending.append(batch["id"])
            continue
        write_jsonl(out / "outputs" / f"{batch['id']}.jsonl", raw)
        for row in raw:
            result = parse_output_line(row)
            if result.usage:
                meter.record(f"{batch['id']}:{result.custom_id}", result.usage)
            kept = results.get(result.custom_id)
            if kept is None or (not kept.ok and result.ok):
                results[result.custom_id] = result
    (out / "batches.json").write_text(json.dumps(batches, indent=2) + "\n")
    if pending:
        print(f"Still running: {', '.join(pending)}. Collect again later.")
        return 0

    world = load_world()
    manifest = json.loads((out / "manifest.json").read_text())
    conditions = tuple(manifest.get("conditions", probe.CONDITIONS))
    rows, invalid = [], []
    for cid, result in sorted(results.items()):
        parsed = probe.parse_guess(result.content) if result.ok else None
        if parsed is None:
            invalid.append(cid)
            continue
        condition, sid = probe.parse_custom_id(cid)
        rows.append(probe.grade(world, condition, sid, *parsed))

    expected = len(manifest["species"]) * len(conditions)
    requests = {r["custom_id"]: r for r in read_jsonl(out / "requests.jsonl")}
    missing = sorted(set(requests) - set(results))
    write_jsonl(out / "retry.jsonl", [requests[cid] for cid in invalid + missing])

    summary = probe.summarize(rows)
    print(f"E-003 run {args.run} — {len(rows)} valid answers of {expected} requests; "
          f"{len(invalid)} invalid, {len(missing)} missing (written to retry.jsonl)")
    for condition in conditions:
        s = summary.get(condition)
        if s is None:
            continue
        low, high = s.interval
        print(f"  {condition:<14} identified {s.identified:>2} of {s.valid} "
              f"({s.rate:.0%}, 95% CI {low:.0%}–{high:.0%}) · exact {s.exact} · "
              f"unknown {s.unknown}")
        per_gen = "  ".join(f"G{g} {k}/{n}" for g, (k, n) in s.by_generation.items())
        print(f"  {'':<14} {per_gen}")
    invalid_by_condition = dict.fromkeys(conditions, 0)
    for cid in invalid + missing:
        invalid_by_condition[probe.parse_custom_id(cid)[0]] += 1
    for condition, k in invalid_by_condition.items():
        s = summary.get(condition)
        if k and s:
            print(f"  {condition:<14} bounds with {k} invalid: identified "
                  f"{s.identified}–{s.identified + k} of {s.valid + k}")
    complete = all(c in summary for c in conditions)
    verdict = (
        probe.decide_bounded(summary, invalid_by_condition) if complete
        else "incomplete"
    )
    print(f"Measured cost (every call, retries included): US$ {meter.cost:.4f}")
    print(f"DECISION RULE: {verdict}")

    (out / "results.json").write_text(json.dumps({
        "collected_at": datetime.now(UTC).isoformat(),
        "manifest": manifest,
        "verdict": verdict,
        "measured_cost_usd": meter.cost,
        "invalid_by_condition": invalid_by_condition,
        "invalid": invalid,
        "missing": missing,
        "rows": [r.__dict__ for r in rows],
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"Results written to {out / 'results.json'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=int, default=1, choices=sorted(probe.RUNS))
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="sample, build requests, estimate cost")
    add_cost_guard_args(prepare)
    submit_parser = sub.add_parser("submit", help="upload a request file as a batch")
    submit_parser.add_argument("--file", default="requests.jsonl")
    submit_parser.add_argument(
        "--max-completion-tokens", type=int, default=None,
        help="rewrite the output cap before submitting (amendment of 2026-09-29)",
    )
    sub.add_parser("collect", help="download results, grade, report")
    args = parser.parse_args()
    return {"prepare": cmd_prepare, "submit": cmd_submit, "collect": cmd_collect}[
        args.command
    ](args)


if __name__ == "__main__":
    sys.exit(main())
