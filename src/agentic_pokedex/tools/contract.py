"""The tool contract: identical for every arm, every stratum.

- ``search(query, k ≤ 5)`` returns the best units, with their headers.
- ``open_page(title, section=None, offset=0)`` returns the units of a page by
  its exact title; ``section`` filters them (a section matching nothing is
  ignored, and the whole page is served), ``offset`` skips the first ones.

**Principle (ADR-009, Updates):** the structure may be artificial, but the
signal an agent uses to decide sufficiency is never handed over by the
infrastructure. No tool states that evidence is missing, how much remains, or
that a section does not exist.
- A call returns at most ``TOKEN_CAP`` tokens of units, packed in rank or page
  order; the first unit is always returned, the rest stop at the first one
  that does not fit.

**Main condition** (``cues=False``): nothing says how many units matched or
remain. The agent has to suspect that a list is incomplete and ask again — the
decision the project measures. **Cue condition** (``cues=True``, S3 ablation
only, ADR-009): ``search`` and ``open_page`` state the total number of matching
units, and the page file carries ``Part k/N`` markers.

Every result records the ids of the units it showed: the sufficiency labeler
reads them, never the text.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from agentic_pokedex.world.index import Unit

MAX_K = 5
TOKEN_CAP = 700
UNIT_SEPARATOR = "\n\n"
NO_RESULTS = "No results."
NO_MORE = "No more units."

TokenCounter = Callable[[str], int]


def default_counter() -> TokenCounter:
    """Token count with ``o200k_base``, the primary model's encoding (``llm`` extra)."""
    import tiktoken

    encoding = tiktoken.get_encoding("o200k_base")
    return lambda text: len(encoding.encode(text))


@dataclass(frozen=True)
class ToolConfig:
    """Condition and limits of a run; frozen with the run's configuration."""

    cues: bool = False
    token_cap: int = TOKEN_CAP
    max_k: int = MAX_K


@dataclass(frozen=True)
class ToolResult:
    """What a tool call returns to the agent, and what it showed."""

    text: str
    unit_ids: tuple[str, ...]
    tokens: int


def message(text: str, counter: TokenCounter) -> ToolResult:
    """A result that shows no unit."""
    return ToolResult(text, (), counter(text))


def pack(
    units: Sequence[Unit], counter: TokenCounter, cap: int, preamble: str = ""
) -> ToolResult:
    """Join units in order until the next one would pass ``cap`` tokens.

    Args:
        units: Units in rank or page order.
        counter: Token counter.
        cap: Token cap of the call.
        preamble: A first line (the cue condition's count), counted in the cap.

    Returns:
        The joined text and the ids of the units it holds; at least one unit.
    """
    parts = [preamble] if preamble else []
    shown: list[str] = []
    for unit in units:
        candidate = UNIT_SEPARATOR.join([*parts, unit.text])
        if shown and counter(candidate) > cap:
            break
        parts.append(unit.text)
        shown.append(unit.id)
    text = UNIT_SEPARATOR.join(parts)
    return ToolResult(text, tuple(shown), counter(text))
