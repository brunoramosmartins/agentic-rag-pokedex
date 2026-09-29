"""Token meter and price table — no network, no tokenizer download, no API key."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest

from agentic_pokedex.observability.pricing import PRICES, Tier, price_for
from agentic_pokedex.observability.tokens import (
    REASONING_SCENARIOS,
    TOKENS_PER_MESSAGE,
    TOKENS_PER_REPLY,
    Usage,
    UsageMeter,
    add_cost_guard_args,
    confirm_or_exit,
    cost_usd,
    count_chat_tokens,
    estimate_cost,
    input_count_within_tolerance,
)


class WordEncoder:
    """Fake tokenizer: one token per whitespace-separated word."""

    def encode(self, text: str) -> list[int]:
        return list(range(len(text.split())))


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------


def test_batch_is_half_of_standard_for_input_and_output() -> None:
    for model in ("gpt-5-mini", "gpt-4o-mini"):
        standard = price_for(model, Tier.STANDARD)
        batch = price_for(model, Tier.BATCH)
        assert batch.input == pytest.approx(standard.input / 2)
        assert batch.output == pytest.approx(standard.output / 2)


def test_dated_snapshot_resolves_to_base_model() -> None:
    assert price_for("gpt-5-mini-2025-08-07", Tier.BATCH) == PRICES[
        ("gpt-5-mini", Tier.BATCH)
    ]


@pytest.mark.parametrize("model", ["gpt-5", "gpt-5-mini-high", "unknown"])
def test_unknown_model_has_no_price(model: str) -> None:
    with pytest.raises(KeyError):
        price_for(model, Tier.BATCH)


# ---------------------------------------------------------------------------
# Local counting
# ---------------------------------------------------------------------------


def test_count_chat_tokens_adds_format_overhead() -> None:
    messages = [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "what is the level"},
    ]
    expected = 2 + 4 + 2 * TOKENS_PER_MESSAGE + TOKENS_PER_REPLY
    assert count_chat_tokens(messages, WordEncoder()) == expected


# ---------------------------------------------------------------------------
# Parsing API usage
# ---------------------------------------------------------------------------

CHAT_USAGE = {
    "prompt_tokens": 120,
    "completion_tokens": 80,
    "total_tokens": 200,
    "prompt_tokens_details": {"cached_tokens": 20},
    "completion_tokens_details": {"reasoning_tokens": 64},
}

RESPONSES_USAGE = {
    "input_tokens": 120,
    "output_tokens": 80,
    "total_tokens": 200,
    "input_tokens_details": {"cached_tokens": 20},
    "output_tokens_details": {"reasoning_tokens": 64},
}

EXPECTED = Usage(
    input_tokens=120, cached_input_tokens=20, output_tokens=80, reasoning_tokens=64
)


@pytest.mark.parametrize("raw", [CHAT_USAGE, RESPONSES_USAGE])
def test_usage_from_api_dicts(raw: dict) -> None:
    assert Usage.from_api(raw) == EXPECTED


def test_usage_from_sdk_like_object() -> None:
    obj = SimpleNamespace(
        prompt_tokens=120,
        completion_tokens=80,
        prompt_tokens_details=SimpleNamespace(cached_tokens=20),
        completion_tokens_details=SimpleNamespace(reasoning_tokens=64),
    )
    assert Usage.from_api(obj) == EXPECTED


def test_usage_from_api_without_details() -> None:
    usage = Usage.from_api({"prompt_tokens": 10, "completion_tokens": 5})
    assert usage == Usage(input_tokens=10, output_tokens=5)


def test_usage_from_api_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError):
        Usage.from_api({"tokens": 3})


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------


def test_cost_of_one_million_tokens_matches_price_table() -> None:
    price = price_for("gpt-5-mini", Tier.BATCH)
    one_m_in = Usage(input_tokens=1_000_000)
    one_m_out = Usage(input_tokens=0, output_tokens=1_000_000)
    assert cost_usd(one_m_in, "gpt-5-mini", Tier.BATCH) == pytest.approx(price.input)
    assert cost_usd(one_m_out, "gpt-5-mini", Tier.BATCH) == pytest.approx(price.output)


def test_reasoning_tokens_are_not_billed_twice() -> None:
    with_reasoning = Usage(input_tokens=0, output_tokens=1000, reasoning_tokens=900)
    without = Usage(input_tokens=0, output_tokens=1000)
    assert cost_usd(with_reasoning, "gpt-5-mini", Tier.BATCH) == pytest.approx(
        cost_usd(without, "gpt-5-mini", Tier.BATCH)
    )


def test_cached_input_uses_cached_price() -> None:
    usage = Usage(input_tokens=1_000_000, cached_input_tokens=400_000)
    expected = (600_000 * 0.25 + 400_000 * 0.025) / 1_000_000
    assert cost_usd(usage, "gpt-5-mini", Tier.STANDARD) == pytest.approx(expected)


def test_missing_cached_price_bills_as_uncached_input() -> None:
    usage = Usage(input_tokens=1_000_000, cached_input_tokens=400_000)
    price = price_for("gpt-4o-mini", Tier.BATCH)
    assert price.cached_input is None
    assert cost_usd(usage, "gpt-4o-mini", Tier.BATCH) == pytest.approx(price.input)


# ---------------------------------------------------------------------------
# Meter
# ---------------------------------------------------------------------------


def test_meter_totals_and_cost() -> None:
    meter = UsageMeter(model="gpt-5-mini", tier=Tier.BATCH)
    meter.record("q1-A3-s1", EXPECTED, estimated_input_tokens=118)
    meter.record("q1-A3-s2", Usage(input_tokens=30, output_tokens=10))
    assert meter.total == Usage(
        input_tokens=150, cached_input_tokens=20, output_tokens=90, reasoning_tokens=64
    )
    assert meter.cost == pytest.approx(cost_usd(meter.total, "gpt-5-mini", Tier.BATCH))
    assert [r.call_id for r in meter.records] == ["q1-A3-s1", "q1-A3-s2"]


@pytest.mark.parametrize(
    ("estimated", "reported", "ok"),
    [
        (100, 100, True),
        (110, 100, True),  # 10 tokens absolute
        (111, 100, False),
        (1040, 1000, True),  # 4% relative
        (1060, 1000, False),  # 6% relative, above 10 tokens
        (950, 1000, True),  # exactly 5%
    ],
)
def test_input_tolerance(estimated: int, reported: int, ok: bool) -> None:
    assert input_count_within_tolerance(estimated, reported) is ok


def test_meter_flags_only_estimates_outside_tolerance() -> None:
    meter = UsageMeter(model="gpt-5-mini", tier=Tier.STANDARD)
    meter.record("ok", Usage(input_tokens=100), estimated_input_tokens=105)
    meter.record("bad", Usage(input_tokens=100), estimated_input_tokens=150)
    meter.record("no-estimate", Usage(input_tokens=100))
    assert [r.call_id for r in meter.input_count_failures()] == ["bad"]


# ---------------------------------------------------------------------------
# Pre-flight estimate and guard
# ---------------------------------------------------------------------------


def test_estimate_pessimistic_costs_more_than_central() -> None:
    est = estimate_cost(
        model="gpt-5-mini",
        tier=Tier.BATCH,
        calls=1000,
        input_tokens_per_call=1500,
        visible_output_tokens_per_call=50,
    )
    assert set(est.usd_by_scenario) == set(REASONING_SCENARIOS)
    assert est.usd_by_scenario["pessimistic"] > est.usd_by_scenario["central"]
    # central: 1.5M input + (50 + 150) × 1000 output at batch prices
    expected_central = (1_500_000 * 0.125 + 200_000 * 1.00) / 1_000_000
    assert est.usd_by_scenario["central"] == pytest.approx(expected_central)


def test_estimate_render_mentions_every_scenario() -> None:
    est = estimate_cost(
        model="gpt-5-mini",
        tier=Tier.BATCH,
        calls=10,
        input_tokens_per_call=100,
        visible_output_tokens_per_call=10,
    )
    text = est.render()
    assert "gpt-5-mini" in text and "batch" in text
    for scenario in REASONING_SCENARIOS:
        assert scenario in text


def _estimate():
    return estimate_cost(
        model="gpt-5-mini",
        tier=Tier.BATCH,
        calls=1,
        input_tokens_per_call=10,
        visible_output_tokens_per_call=10,
    )


def test_guard_prints_estimate_even_with_yes() -> None:
    printed: list[str] = []
    confirm_or_exit(
        _estimate(), assume_yes=True, ask=lambda _: "n", out=printed.append
    )
    assert printed and "Estimated cost" in printed[0]


@pytest.mark.parametrize("answer", ["y", "yes", " Y "])
def test_guard_proceeds_on_confirmation(answer: str) -> None:
    confirm_or_exit(_estimate(), assume_yes=False, ask=lambda _: answer, out=print)


@pytest.mark.parametrize("answer", ["", "n", "no", "sure"])
def test_guard_aborts_without_confirmation(answer: str) -> None:
    with pytest.raises(SystemExit):
        confirm_or_exit(
            _estimate(), assume_yes=False, ask=lambda _: answer, out=lambda _: None
        )


def test_cost_guard_args() -> None:
    parser = argparse.ArgumentParser()
    add_cost_guard_args(parser)
    args = parser.parse_args(["--limit", "5", "--yes"])
    assert args.limit == 5 and args.yes is True
    defaults = parser.parse_args([])
    assert defaults.limit is None and defaults.yes is False
