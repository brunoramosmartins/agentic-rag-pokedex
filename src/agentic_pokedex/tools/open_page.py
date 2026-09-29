"""``open_page(title, section=None, offset=0)``: follow a ``[[link]]``."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from agentic_pokedex.tools.contract import (
    NO_MORE,
    ToolConfig,
    ToolResult,
    TokenCounter,
    message,
    pack,
)
from agentic_pokedex.world.index import Unit


class Pages:
    """Indexed units grouped by page title, in page order.

    In the twin every title is unique. In the real naming a type and a move
    can share a name ("Psychic"); ``open_page`` then returns both pages, in
    page-kind order (species, move, ability, type).
    """

    def __init__(self, units: Iterable[Unit]) -> None:
        self.by_title: dict[str, list[Unit]] = defaultdict(list)
        for unit in units:
            self.by_title[unit.title].append(unit)


def open_page(
    pages: Pages,
    title: str,
    section: str | None = None,
    offset: int = 0,
    *,
    counter: TokenCounter,
    config: ToolConfig | None = None,
) -> ToolResult:
    """Return a page's units from the top, under the token cap.

    Args:
        pages: The run's pages.
        title: Exact page title (what a ``[[link]]`` shows).
        section: Case-insensitive text matched against each unit's section
            line (e.g. ``"Profile"``, ``"level-up"``, ``"Learned by"``).
        offset: Units of the (filtered) page to skip, to continue reading.
        counter: Token counter.
        config: Condition and limits (main condition by default).

    Returns:
        The units. Past the last one, ``"No more units."``; in the main
        condition nothing else says whether more remain.
    """
    config = config or ToolConfig()
    units = pages.by_title.get(title)
    if not units:
        return message(f"No page titled {title!r}.", counter)
    if section:
        needle = section.strip().lower()
        units = [u for u in units if needle in u.section.lower()]
        if not units:
            return message(f"No section matching {section!r} on {title!r}.", counter)
    remaining = units[max(offset, 0) :]
    if not remaining:
        return message(NO_MORE, counter)
    preamble = f"{len(units)} units in this selection." if config.cues else ""
    return pack(remaining, counter, config.token_cap, preamble)
