"""Dated LLM price table.

Source of truth: `docs/data-sources.md`, section "LLM prices". Prices are in
US$ per million tokens and change without notice: they are re-checked before
every registered run, and the value used is written in that run's registry
entry. Changing a price here means updating that document on the same day.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

PRICES_AS_OF = "2026-09-24"


class Tier(Enum):
    """API pricing tier."""

    STANDARD = "standard"
    BATCH = "batch"


@dataclass(frozen=True)
class Price:
    """Per-million-token prices for one model and tier.

    Attributes:
        input: Uncached input tokens.
        cached_input: Cached input tokens, or None when the tier lists no
            cached price (billed as uncached input, the conservative choice).
        output: Output tokens, reasoning tokens included.
    """

    input: float
    cached_input: float | None
    output: float


PRICES: dict[tuple[str, Tier], Price] = {
    ("gpt-5-mini", Tier.STANDARD): Price(input=0.25, cached_input=0.025, output=2.00),
    ("gpt-5-mini", Tier.BATCH): Price(input=0.125, cached_input=0.0125, output=1.00),
    ("gpt-4o-mini", Tier.STANDARD): Price(input=0.15, cached_input=0.075, output=0.60),
    ("gpt-4o-mini", Tier.BATCH): Price(input=0.075, cached_input=None, output=0.30),
}


def price_for(model: str, tier: Tier) -> Price:
    """Look up the price of a model on a tier.

    Args:
        model: Model id, e.g. "gpt-5-mini". A dated snapshot id such as
            "gpt-5-mini-2025-08-07" resolves to its base model.
        tier: Pricing tier.

    Returns:
        The registered price.

    Raises:
        KeyError: If the model has no registered price on that tier.
    """
    for (known, known_tier), price in PRICES.items():
        if known_tier is tier and (model == known or model.startswith(known + "-2")):
            return price
    raise KeyError(f"no registered price for {model!r} on the {tier.value} tier")
