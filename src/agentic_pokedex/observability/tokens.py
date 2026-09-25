"""Token meter: pre-flight cost estimate and API-reported usage.

Two numbers, never mixed:

- **Estimate** (before a run): input tokens counted locally with the model's
  tokenizer, plus assumed output and reasoning tokens per call. Printed before
  any loop that calls an LLM; the loop only starts after confirmation.
- **Measured** (during a run): the usage the API reports for each call. This
  is the only source for registered costs.

Measurability gate 7 checks the meter against the API on 10 real calls
(`scripts/check_token_meter.py`): the meter's totals must equal the sum of the
API-reported usage, and the local input count must be within
``INPUT_TOLERANCE_REL`` or ``INPUT_TOLERANCE_ABS`` tokens of what the API
reports.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from agentic_pokedex.observability.pricing import Tier, price_for

TOKENS_PER_MESSAGE = 3
"""Chat-format overhead per message (role and separators)."""
TOKENS_PER_REPLY = 3
"""Chat-format overhead that primes the assistant reply."""

REASONING_SCENARIOS: Mapping[str, int] = {"central": 150, "pessimistic": 400}
"""Assumed reasoning tokens per call until Phase 3 replaces them with medians."""

INPUT_TOLERANCE_REL = 0.05
INPUT_TOLERANCE_ABS = 10
"""Gate 7: a local input count passes if within 5% or 10 tokens of the API."""

_FALLBACK_ENCODING = "o200k_base"


class Encoder(Protocol):
    """Anything that turns text into a sequence of token ids."""

    def encode(self, text: str) -> Sequence[int]:
        """Encode text into token ids."""
        ...


def load_encoder(model: str) -> Encoder:
    """Load the tokenizer for a model (requires the `llm` extra).

    Args:
        model: Model id.

    Returns:
        The model's tiktoken encoding, or ``o200k_base`` when tiktoken does not
        know the model.
    """
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding(_FALLBACK_ENCODING)


def count_chat_tokens(messages: Sequence[Mapping[str, str]], encoder: Encoder) -> int:
    """Count the input tokens of a chat request locally.

    Args:
        messages: Chat messages with "role" and "content".
        encoder: Tokenizer.

    Returns:
        Content tokens plus the chat-format overhead.
    """
    total = TOKENS_PER_REPLY
    for message in messages:
        total += TOKENS_PER_MESSAGE
        total += len(encoder.encode(message["content"]))
    return total


# ---------------------------------------------------------------------------
# Measured usage
# ---------------------------------------------------------------------------


def _get(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


@dataclass(frozen=True)
class Usage:
    """Token usage of one call, as reported by the API.

    Attributes:
        input_tokens: All input tokens, cached ones included.
        cached_input_tokens: The cached part of ``input_tokens``.
        output_tokens: All output tokens, reasoning ones included.
        reasoning_tokens: The reasoning part of ``output_tokens``.
    """

    input_tokens: int
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    @classmethod
    def from_api(cls, usage: Any) -> Usage:
        """Read a usage object from the Chat Completions or Responses API.

        Accepts the SDK object or its dict form, including the ``usage`` of a
        Batch API output line.

        Args:
            usage: The ``usage`` field of a response.

        Returns:
            The parsed usage.

        Raises:
            ValueError: If neither API shape is recognized.
        """
        if _get(usage, "prompt_tokens") is not None:  # Chat Completions
            input_details = _get(usage, "prompt_tokens_details")
            output_details = _get(usage, "completion_tokens_details")
            return cls(
                input_tokens=_get(usage, "prompt_tokens"),
                cached_input_tokens=_get(input_details, "cached_tokens") or 0,
                output_tokens=_get(usage, "completion_tokens") or 0,
                reasoning_tokens=_get(output_details, "reasoning_tokens") or 0,
            )
        if _get(usage, "input_tokens") is not None:  # Responses
            input_details = _get(usage, "input_tokens_details")
            output_details = _get(usage, "output_tokens_details")
            return cls(
                input_tokens=_get(usage, "input_tokens"),
                cached_input_tokens=_get(input_details, "cached_tokens") or 0,
                output_tokens=_get(usage, "output_tokens") or 0,
                reasoning_tokens=_get(output_details, "reasoning_tokens") or 0,
            )
        raise ValueError(f"unrecognized usage object: {usage!r}")

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            cached_input_tokens=self.cached_input_tokens + other.cached_input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
        )


def cost_usd(usage: Usage, model: str, tier: Tier) -> float:
    """Cost of a usage in US$, with the registered price.

    Reasoning tokens are part of ``output_tokens`` and are not added again.

    Args:
        usage: Token usage.
        model: Model id.
        tier: Pricing tier.

    Returns:
        Cost in US$.
    """
    price = price_for(model, tier)
    cached_price = price.input if price.cached_input is None else price.cached_input
    uncached = usage.input_tokens - usage.cached_input_tokens
    return (
        uncached * price.input
        + usage.cached_input_tokens * cached_price
        + usage.output_tokens * price.output
    ) / 1_000_000


@dataclass
class CallRecord:
    """One metered call."""

    call_id: str
    usage: Usage
    estimated_input_tokens: int | None = None


@dataclass
class UsageMeter:
    """Accumulates API-reported usage for one run.

    Attributes:
        model: Model id used for every call of the run.
        tier: Pricing tier of the run.
        records: One record per call, in order.
    """

    model: str
    tier: Tier
    records: list[CallRecord] = field(default_factory=list)

    def record(
        self, call_id: str, usage: Usage, estimated_input_tokens: int | None = None
    ) -> CallRecord:
        """Record the usage the API reported for one call.

        Args:
            call_id: Stable id (e.g. question id + arm + step).
            usage: API-reported usage.
            estimated_input_tokens: Local count made before the call, if any.

        Returns:
            The stored record.
        """
        rec = CallRecord(call_id, usage, estimated_input_tokens)
        self.records.append(rec)
        return rec

    @property
    def total(self) -> Usage:
        """Sum of the usage of every recorded call."""
        total = Usage(0)
        for rec in self.records:
            total = total + rec.usage
        return total

    @property
    def cost(self) -> float:
        """Total cost in US$ of the recorded calls."""
        return cost_usd(self.total, self.model, self.tier)

    def input_count_failures(self) -> list[CallRecord]:
        """Records whose local input count misses the gate 7 tolerance.

        Returns:
            Records with an estimate outside the tolerance; records without an
            estimate are skipped.
        """
        return [
            rec
            for rec in self.records
            if rec.estimated_input_tokens is not None
            and not input_count_within_tolerance(
                rec.estimated_input_tokens, rec.usage.input_tokens
            )
        ]


def input_count_within_tolerance(estimated: int, reported: int) -> bool:
    """Gate 7 tolerance between a local input count and the API's.

    Args:
        estimated: Local count.
        reported: API-reported input tokens.

    Returns:
        True if the difference is within 5% of the reported count or within 10
        tokens, whichever is larger.
    """
    allowed = max(INPUT_TOLERANCE_REL * reported, INPUT_TOLERANCE_ABS)
    return abs(estimated - reported) <= allowed


# ---------------------------------------------------------------------------
# Pre-flight estimate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CostEstimate:
    """Pre-flight cost estimate of a run, per reasoning scenario."""

    model: str
    tier: Tier
    calls: int
    input_tokens_per_call: float
    visible_output_tokens_per_call: float
    usd_by_scenario: Mapping[str, float]

    def render(self) -> str:
        """Human-readable summary, printed before the run starts."""
        lines = [
            f"Estimated cost — {self.model} ({self.tier.value}), "
            f"{self.calls} calls, prices as of the registered table",
            f"  input/call: {self.input_tokens_per_call:,.0f} tokens · "
            f"visible output/call: {self.visible_output_tokens_per_call:,.0f} tokens",
        ]
        for scenario, usd in self.usd_by_scenario.items():
            reasoning = REASONING_SCENARIOS.get(scenario, "?")
            lines.append(
                f"  {scenario:<12} (+{reasoning} reasoning/call): US$ {usd:,.4f}"
            )
        return "\n".join(lines)


def estimate_cost(
    *,
    model: str,
    tier: Tier,
    calls: int,
    input_tokens_per_call: float,
    visible_output_tokens_per_call: float,
    reasoning_scenarios: Mapping[str, int] = REASONING_SCENARIOS,
) -> CostEstimate:
    """Estimate the cost of a run before it starts.

    Args:
        model: Model id.
        tier: Pricing tier.
        calls: Number of LLM calls the run will make (after ``--limit``).
        input_tokens_per_call: Mean input tokens per call (count them locally
            with ``count_chat_tokens`` whenever the prompts are known).
        visible_output_tokens_per_call: Assumed visible output per call.
        reasoning_scenarios: Assumed reasoning tokens per call, by scenario.

    Returns:
        The estimate, one US$ figure per scenario.
    """
    usd = {}
    for scenario, reasoning in reasoning_scenarios.items():
        output = visible_output_tokens_per_call + reasoning
        usage = Usage(
            input_tokens=round(calls * input_tokens_per_call),
            output_tokens=round(calls * output),
            reasoning_tokens=round(calls * reasoning),
        )
        usd[scenario] = cost_usd(usage, model, tier)
    return CostEstimate(
        model=model,
        tier=tier,
        calls=calls,
        input_tokens_per_call=input_tokens_per_call,
        visible_output_tokens_per_call=visible_output_tokens_per_call,
        usd_by_scenario=usd,
    )


def add_cost_guard_args(parser: argparse.ArgumentParser) -> None:
    """Add the flags every LLM-looping script must support.

    Args:
        parser: The script's argument parser.
    """
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="process at most N items (the estimate is computed on N)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the confirmation prompt after the estimate is printed",
    )


def confirm_or_exit(
    estimate: CostEstimate,
    *,
    assume_yes: bool,
    ask: Callable[[str], str] = input,
    out: Callable[[str], object] = print,
) -> None:
    """Print the estimate and stop unless the run is confirmed.

    Args:
        estimate: Pre-flight estimate.
        assume_yes: Skip the prompt (``--yes``); the estimate is still printed.
        ask: Prompt function (injectable for tests).
        out: Output function (injectable for tests).

    Raises:
        SystemExit: If the user does not confirm.
    """
    out(estimate.render())
    if assume_yes:
        return
    answer = ask("Proceed? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        out("Aborted before any call.")
        sys.exit(1)
