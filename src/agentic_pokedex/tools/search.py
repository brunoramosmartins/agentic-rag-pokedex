"""``search(query, k ≤ 5)``: the best indexed units for a query."""

from __future__ import annotations

from agentic_pokedex.tools.contract import (
    NO_RESULTS,
    TokenCounter,
    ToolConfig,
    ToolResult,
    message,
    pack,
)
from agentic_pokedex.world.index import HybridIndex


def search(
    index: HybridIndex,
    query: str,
    k: int,
    *,
    counter: TokenCounter,
    config: ToolConfig | None = None,
) -> ToolResult:
    """Run the hybrid index and pack the top ``k`` units under the token cap.

    Args:
        index: The hybrid index of the run's page file.
        query: Free text chosen by the arm.
        k: Units requested; clamped to ``1 ≤ k ≤ config.max_k``.
        counter: Token counter.
        config: Condition and limits (main condition by default).

    Returns:
        The units, best first. In the cue condition, a first line states how
        many units match the query lexically.
    """
    config = config or ToolConfig()
    k = max(1, min(k, config.max_k))
    hits = index.search(query, k)
    if not hits:
        return message(NO_RESULTS, counter)
    units = [index.units[h.unit_id] for h in hits]
    preamble = f"{index.match_count(query)} matching units." if config.cues else ""
    return pack(units, counter, config.token_cap, preamble)
