"""Measurability gate 7: check the token meter against the API on real calls.

Makes N small chat calls (default 10) with varied prompts and checks that:

1. the meter's totals equal the sum of the usage fields the API reported,
   summed independently from the raw responses (the parser loses nothing);
2. the local input count of every call is within the registered tolerance of
   the API-reported input tokens (5% or 10 tokens, whichever is larger).

Prints the estimated cost and asks for confirmation before the first call.
Writes the per-call results to ``runs/`` (gitignored); the summary goes into
the decision journal by hand.

Requires the `llm` extra and OPENAI_API_KEY:

    pip install -e ".[llm]"
    python scripts/check_token_meter.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from agentic_pokedex.observability.pricing import PRICES_AS_OF, Tier
from agentic_pokedex.observability.tokens import (
    INPUT_TOLERANCE_ABS,
    INPUT_TOLERANCE_REL,
    Usage,
    UsageMeter,
    add_cost_guard_args,
    confirm_or_exit,
    count_chat_tokens,
    estimate_cost,
    load_encoder,
)

MAX_COMPLETION_TOKENS = 600
"""Upper bound per call on output tokens, reasoning included."""

SYSTEM = "You are a terse assistant. Answer in one short sentence."

# Varied on purpose: length, number of messages, pseudo-words like the twin's,
# numbers, non-ASCII text, and a table-like section header.
PROMPTS: list[list[dict[str, str]]] = [
    [{"role": "user", "content": "Say OK."}],
    [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "What is 17 times 23?"},
    ],
    [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": "Species: Vexmoor · Section: Learnset · Version: "
            "Ambergleam\nLevel 1: Tarnish Bite\nLevel 12: Gloam Spark\n"
            "Level 42: Cinderwake\nAt what level does Vexmoor learn Cinderwake?",
        },
    ],
    [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": "Translate to Portuguese: the evidence is not enough.",
        },
    ],
    [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Name a prime number."},
        {"role": "assistant", "content": "7"},
        {"role": "user", "content": "Another one, larger than 100."},
    ],
    [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": "Summarize in five words: " + "retrieval step " * 120,
        },
    ],
    [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Café, naïve, Pokédex, ação — how many words?"},
    ],
    [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": "Evolves into: [[Tarnlet]]\nEvolves into: [[Brumeclaw]]\n"
            "Which is the final form?",
        },
    ],
    [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": '{"answer": null, "abstain": true} — valid JSON?'},
    ],
    [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": "List three colors, comma separated, and nothing else.",
        },
    ],
]


def main() -> int:
    """Run the check and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument(
        "--reasoning-effort",
        default="low",
        choices=["none", "minimal", "low", "medium", "high"],
        help="'none' omits the parameter (for non-reasoning models)",
    )
    parser.add_argument("--out", type=Path, default=Path("runs/token-meter-check.json"))
    add_cost_guard_args(parser)
    args = parser.parse_args()

    prompts = PROMPTS[: args.limit] if args.limit else PROMPTS
    encoder = load_encoder(args.model)
    estimates = [count_chat_tokens(messages, encoder) for messages in prompts]

    estimate = estimate_cost(
        model=args.model,
        tier=Tier.STANDARD,
        calls=len(prompts),
        input_tokens_per_call=sum(estimates) / len(estimates),
        visible_output_tokens_per_call=30,
    )
    confirm_or_exit(estimate, assume_yes=args.yes)

    from openai import OpenAI

    client = OpenAI()
    meter = UsageMeter(model=args.model, tier=Tier.STANDARD)
    raw_sum = {"input": 0, "cached": 0, "output": 0, "reasoning": 0}
    rows = []
    snapshot = None

    for i, (messages, est) in enumerate(zip(prompts, estimates, strict=True)):
        kwargs = {}
        if args.reasoning_effort != "none":
            kwargs["reasoning_effort"] = args.reasoning_effort
        response = client.chat.completions.create(
            model=args.model,
            messages=messages,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            **kwargs,
        )
        snapshot = response.model
        raw = response.usage.model_dump()
        raw_sum["input"] += raw["prompt_tokens"]
        raw_sum["output"] += raw["completion_tokens"]
        raw_sum["cached"] += (raw.get("prompt_tokens_details") or {}).get(
            "cached_tokens"
        ) or 0
        raw_sum["reasoning"] += (raw.get("completion_tokens_details") or {}).get(
            "reasoning_tokens"
        ) or 0

        rec = meter.record(f"call-{i:02d}", Usage.from_api(raw), est)
        rows.append(
            {
                "call_id": rec.call_id,
                "estimated_input": est,
                "api_input": rec.usage.input_tokens,
                "api_cached_input": rec.usage.cached_input_tokens,
                "api_output": rec.usage.output_tokens,
                "api_reasoning": rec.usage.reasoning_tokens,
                "diff_input": est - rec.usage.input_tokens,
            }
        )

    total = meter.total
    totals_match = (
        total.input_tokens == raw_sum["input"]
        and total.cached_input_tokens == raw_sum["cached"]
        and total.output_tokens == raw_sum["output"]
        and total.reasoning_tokens == raw_sum["reasoning"]
    )
    failures = meter.input_count_failures()
    passed = totals_match and not failures

    print(f"\n{'call':<8}{'est_in':>8}{'api_in':>8}{'diff':>6}{'out':>6}{'reason':>8}")
    for row in rows:
        print(
            f"{row['call_id']:<8}{row['estimated_input']:>8}{row['api_input']:>8}"
            f"{row['diff_input']:>6}{row['api_output']:>6}{row['api_reasoning']:>8}"
        )
    print(f"\nModel snapshot: {snapshot}")
    print(f"Totals match raw API usage: {totals_match}")
    print(
        f"Input counts within tolerance ({INPUT_TOLERANCE_REL:.0%} or "
        f"{INPUT_TOLERANCE_ABS} tokens): {len(rows) - len(failures)} of {len(rows)}"
    )
    print(f"Measured cost: US$ {meter.cost:.6f} (prices as of {PRICES_AS_OF})")
    print("GATE 7 TOKEN METER:", "PASS" if passed else "FAIL")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "run_at": datetime.now(UTC).isoformat(),
                "model": args.model,
                "snapshot": snapshot,
                "reasoning_effort": args.reasoning_effort,
                "prices_as_of": PRICES_AS_OF,
                "totals_match": totals_match,
                "input_failures": [rec.call_id for rec in failures],
                "measured_cost_usd": meter.cost,
                "passed": passed,
                "calls": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Results written to {args.out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
