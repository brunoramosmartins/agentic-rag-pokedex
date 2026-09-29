"""E-003, the identity probe, through the Batch API.

Three steps, each re-runnable; state lives in ``runs/e003/`` (gitignored):

    python scripts/identity_probe.py prepare [--limit N] [--yes]
    python scripts/identity_probe.py submit [--file requests.jsonl]
    python scripts/identity_probe.py collect

``prepare`` samples the 50 species, builds the three pages of each, counts the
input tokens locally, prints the estimated cost and asks before writing the
requests. ``submit`` uploads them as a batch. ``collect`` downloads every
finished batch, grades the answers, writes ``results.json``, prints the report
with the decision rule applied, and writes ``retry.jsonl`` for invalid answers
(re-send them with ``submit --file retry.jsonl``; at most twice, per E-003).

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

RUN_DIR = Path("runs/e003")
PROMPT = "identity_probe"


def load_world() -> World:
    tables = read_world(DEFAULT_RAW_DIR)
    learn_rows = list(iter_learnsets(DEFAULT_RAW_DIR, tables))
    return build_world(tables, learn_rows, VERSION_SCOPE)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_prepare(args: argparse.Namespace) -> int:
    world = load_world()
    species = probe.sample_species(world)
    if args.limit:
        species = species[: args.limit]
    registry = Registry.load(DEFAULT_WORLD_DIR / "registry.json")
    pages = {
        name: DEFAULT_WORLD_DIR / "pages" / f"{name}.jsonl" for name in ("real", "twin")
    }
    real_units = load_units(pages["real"], registry)
    twin_units = load_units(pages["twin"], registry)
    prompt = load_prompt(PROMPT)
    counter = default_counter()
    encoder = load_encoder(probe.MODEL)

    requests, input_tokens = [], []
    for sid in species:
        for condition in probe.CONDITIONS:
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
                    probe.custom_id(condition, sid),
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

    write_jsonl(RUN_DIR / "requests.jsonl", requests)
    manifest = {
        "experiment": "E-003",
        "prepared_at": datetime.now(UTC).isoformat(),
        "model": probe.MODEL,
        "reasoning_effort": probe.REASONING_EFFORT,
        "max_completion_tokens": probe.MAX_COMPLETION_TOKENS,
        "prompt": {"name": prompt.name, "sha256": prompt.sha256},
        "seed": probe.PROBE_SEED,
        "species": species,
        "limit": args.limit,
        "pages_sha256": {name: sha256_file(path) for name, path in pages.items()},
        "estimate_usd": dict(estimate.usd_by_scenario),
    }
    (RUN_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(requests)} requests written to {RUN_DIR / 'requests.jsonl'}")
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    from openai import OpenAI

    load_env()
    path = RUN_DIR / args.file
    if args.max_completion_tokens:
        # Amendment of 2026-09-29: re-sends may raise the output cap. The
        # rewritten file is kept beside the original for the audit trail.
        rows = read_jsonl(path)
        for row in rows:
            row["body"]["max_completion_tokens"] = args.max_completion_tokens
        path = path.with_name(f"{path.stem}-mct{args.max_completion_tokens}.jsonl")
        write_jsonl(path, rows)
    metadata = {"experiment": "E-003", "file": path.name}
    batch_id = submit(OpenAI(), path, metadata=metadata)
    batches_path = RUN_DIR / "batches.json"
    batches = json.loads(batches_path.read_text()) if batches_path.is_file() else []
    batches.append({"id": batch_id, "file": path.name,
                    "submitted_at": datetime.now(UTC).isoformat()})
    batches_path.write_text(json.dumps(batches, indent=2) + "\n")
    print(f"Batch {batch_id} submitted ({path.name}). Run `collect` when it ends.")
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    from openai import OpenAI

    load_env()
    client = OpenAI()
    batches = json.loads((RUN_DIR / "batches.json").read_text())
    meter = UsageMeter(model=probe.MODEL, tier=Tier.BATCH)
    results: dict[str, BatchResult] = {}
    pending = []
    # Batches in submission order; per request, the FIRST valid answer is kept
    # (a later one never replaces it), so no answer is chosen after the fact.
    for batch in batches:
        status, raw = fetch(client, batch["id"])
        batch["status"] = status
        if status not in ("completed", "failed", "expired", "cancelled"):
            pending.append(batch["id"])
            continue
        write_jsonl(RUN_DIR / "outputs" / f"{batch['id']}.jsonl", raw)
        for row in raw:
            result = parse_output_line(row)
            if result.usage:
                meter.record(f"{batch['id']}:{result.custom_id}", result.usage)
            kept = results.get(result.custom_id)
            if kept is None or (not kept.ok and result.ok):
                results[result.custom_id] = result
    (RUN_DIR / "batches.json").write_text(json.dumps(batches, indent=2) + "\n")
    if pending:
        print(f"Still running: {', '.join(pending)}. Collect again later.")
        return 0

    world = load_world()
    manifest = json.loads((RUN_DIR / "manifest.json").read_text())
    rows, invalid = [], []
    for cid, result in sorted(results.items()):
        parsed = probe.parse_guess(result.content) if result.ok else None
        if parsed is None:
            invalid.append(cid)
            continue
        condition, sid = probe.parse_custom_id(cid)
        rows.append(probe.grade(world, condition, sid, *parsed))

    expected = len(manifest["species"]) * len(probe.CONDITIONS)
    requests = {r["custom_id"]: r for r in read_jsonl(RUN_DIR / "requests.jsonl")}
    missing = sorted(set(requests) - set(results))
    retry = [requests[cid] for cid in invalid + missing]
    write_jsonl(RUN_DIR / "retry.jsonl", retry)

    summary = probe.summarize(rows)
    print(f"E-003 — {len(rows)} valid answers of {expected} requests; "
          f"{len(invalid)} invalid, {len(missing)} missing "
          f"(written to retry.jsonl)")
    for condition in probe.CONDITIONS:
        s = summary.get(condition)
        if s is None:
            continue
        low, high = s.interval
        print(f"  {condition:<14} identified {s.identified:>2} of {s.valid} "
              f"({s.rate:.0%}, 95% CI {low:.0%}–{high:.0%}) · exact {s.exact} · "
              f"unknown {s.unknown}")
        per_gen = "  ".join(f"G{g} {k}/{n}" for g, (k, n) in s.by_generation.items())
        print(f"  {'':<14} {per_gen}")
    invalid_by_condition = {c: 0 for c in probe.CONDITIONS}
    for cid in invalid + missing:
        invalid_by_condition[probe.parse_custom_id(cid)[0]] += 1
    for condition, k in invalid_by_condition.items():
        s = summary.get(condition)
        if k and s:
            total = s.valid + k
            print(f"  {condition:<14} bounds with {k} invalid: identified "
                  f"{s.identified}–{s.identified + k} of {total}")
    complete = all(c in summary for c in probe.CONDITIONS)
    verdict = (
        probe.decide_bounded(summary, invalid_by_condition) if complete
        else "incomplete"
    )
    print(f"Measured cost (every call, retries included): US$ {meter.cost:.4f}")
    print(f"DECISION RULE: {verdict}")

    (RUN_DIR / "results.json").write_text(json.dumps({
        "collected_at": datetime.now(UTC).isoformat(),
        "manifest": manifest,
        "verdict": verdict,
        "measured_cost_usd": meter.cost,
        "invalid_by_condition": invalid_by_condition,
        "invalid": invalid,
        "missing": missing,
        "rows": [r.__dict__ for r in rows],
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"Results written to {RUN_DIR / 'results.json'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    return {"prepare": cmd_prepare, "submit": cmd_submit, "collect": cmd_collect}[
        args.command
    ](args)


if __name__ == "__main__":
    sys.exit(main())
