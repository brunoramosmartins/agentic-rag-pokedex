"""``open_page(title, section=None, offset=0)``: follow a ``[[link]]``.

The tool never announces that evidence is missing. A ``section`` that matches
nothing on the page is ignored and the page is returned from the top, as a wiki
link whose anchor does not exist lands at the top of the page. An agent asking
for a withheld learnset (S4) therefore sees the other versions' sections — the
plausible, insufficient evidence the stratum is built on — and has to notice
by itself that the one it asked for is not there (ADR-009, Updates).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from agentic_pokedex.tools.contract import (
    NO_MORE,
    TokenCounter,
    ToolConfig,
    ToolResult,
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


def select(units: list[Unit], section: str | None) -> list[Unit]:
    """The units whose section line contains ``section``, or the whole page.

    Matching is case-insensitive. When nothing matches, the whole page is
    returned — never an empty selection, which would state the absence.
    """
    if not section:
        return units
    needle = section.strip().lower()
    matched = [u for u in units if needle in u.section.lower()]
    return matched or units


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
            line (e.g. ``"Profile"``, ``"level-up"``, ``"Learned by"``). A
            section matching nothing is ignored: the whole page is served.
        offset: Units of the selection to skip, to continue reading.
        counter: Token counter.
        config: Condition and limits (main condition by default).

    Returns:
        The units. Past the last one, ``"No more units."``; in the main
        condition nothing else says whether more remain or whether a section
        exists.
    """
    config = config or ToolConfig()
    units = pages.by_title.get(title)
    if not units:
        return message(f"No page titled {title!r}.", counter)
    selection = select(units, section)
    remaining = selection[max(offset, 0) :]
    if not remaining:
        return message(NO_MORE, counter)
    preamble = f"{len(selection)} units in this selection." if config.cues else ""
    return pack(remaining, counter, config.token_cap, preamble)
