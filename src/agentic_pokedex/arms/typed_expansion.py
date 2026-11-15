"""Search, complete the hits' sections, then expand typed links up to B (no LLM).

The retrieval half of the fixed pipeline: E-002 measures what it delivers, and
the Phase 4 A2 arm reuses it, at its frozen hash, with only the registered grid
parameters varying. Specified in E-002's amendments of 2026-10-07:

1. **Search.** ``search(question, k)`` under the tool contract (700-token cap,
   so fewer than k units may come back).
2. **Level 0, section completion.** For each search hit, in rank order, the
   hit's section is read from its top: ``open_page(title, section, offset)``
   with ``offset`` advanced by the units returned, until a reply holds no unit
   ("No more units." is a call and its tokens, as for any agent: the main
   condition never says that a section ended). A section already read is not
   read again. ``section`` is the hit's section line.
3. **Link levels.** Links (``[[Title]]``) are expanded **breadth-first**:
   level 1 is the links in the units delivered by search and level 0, level
   n+1 the links in the windows opened at level n. Within a level, links are
   taken by **link type** in ``LINK_ORDER``, then in order of appearance; a
   title appears once per level. Each expansion is ``open_page(title)``, the
   first window of the page from its top; a page is opened this way at most
   once, even if its units already came back (they are not delivered twice,
   but their tokens count). A link whose target is not a page title, or that
   no type covers ("Forms:", a Notes line), is skipped: no call, no tokens.
4. **B.** Evidence tokens are the sum of every result's ``tokens`` (search
   included, separators and "No more units." included), as for the agent
   arms. The pipeline stops at the first call whose result would pass
   ``budget``; it does not skip to a smaller one.

Search fuses BM25 and dense rankings by unweighted RRF (``world/index.py``):
equal weights, the 0.5 point of A2's registered grid.

Link types are read from the source unit's section and the target's page kind:

| Type | Source → target |
|---|---|
| ``evolves-into`` | species ``Profile``, line "Evolves into" → species |
| ``ability`` | ``Profile`` or ``Form`` → ability |
| ``type`` | ``Profile``, ``Form`` or ``Matchups`` → type |
| ``move`` | ``Learnset`` → move |
| ``learner`` | ``Learned by`` → species |
| ``holder`` | ``Holders`` → species |
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from agentic_pokedex.tools.contract import TokenCounter, ToolConfig, ToolResult
from agentic_pokedex.tools.open_page import Pages, open_page
from agentic_pokedex.tools.search import search
from agentic_pokedex.world.index import HybridIndex
from agentic_pokedex.world.registry import Registry

LINK_ORDER = ("evolves-into", "ability", "type", "move", "learner", "holder")
"""Registered in E-002 before its run (2026-10-07)."""

EVIDENCE_BUDGET = 4_000
"""B, evidence tokens (E-001)."""

LINK = re.compile(r"\[\[([^\]]+)\]\]")
EVOLVES_INTO = "Evolves into"


def link_type(section: str, line: str, target_kind: str) -> str | None:
    """The type of one link, or ``None`` for a link no type covers.

    Args:
        section: Registry section of the source unit (``Profile``,
            ``Learnset``, ``Form``, ``Learned by``, ``Holders``, ``Matchups``).
        line: The text line holding the link.
        target_kind: Page kind of the target (``species``, ``move``,
            ``ability``, ``type``).
    """
    if target_kind == "species":
        if section == "Profile" and line.startswith(EVOLVES_INTO):
            return "evolves-into"
        return {"Learned by": "learner", "Holders": "holder"}.get(section)
    if target_kind == "ability" and section in ("Profile", "Form"):
        return "ability"
    if target_kind == "type" and section in ("Profile", "Form", "Matchups"):
        return "type"
    if target_kind == "move" and section == "Learnset":
        return "move"
    return None


@dataclass(frozen=True)
class Link:
    """One expandable link, in the order it appeared."""

    kind: str
    title: str


def links_of(
    unit_ids: Sequence[str], texts: Mapping[str, str], sections: Mapping[str, str],
    page_kind: Mapping[str, str],
) -> list[Link]:
    """Typed links of some units, distinct by title, in order of appearance."""
    seen: set[str] = set()
    out: list[Link] = []
    for uid in unit_ids:
        for line in texts[uid].split("\n")[1:]:  # the header names its own page
            for title in LINK.findall(line):
                kind = page_kind.get(title)
                lt = link_type(sections[uid], line, kind) if kind else None
                if lt is None or title in seen:
                    continue
                seen.add(title)
                out.append(Link(lt, title))
    return out


def ordered(links: Sequence[Link], order: Sequence[str] = LINK_ORDER) -> list[Link]:
    """Links by type rank, then by appearance (a stable sort)."""
    rank = {kind: i for i, kind in enumerate(order)}
    return sorted(links, key=lambda link: rank[link.kind])


@dataclass(frozen=True)
class Step:
    """One call of the pipeline.

    Attributes:
        level: ``-1`` search, ``0`` section completion, ``n ≥ 1`` link level.
        call: The call, as written.
        units: Unit ids the call returned.
        tokens: Tokens of its result.
    """

    level: int
    call: str
    units: tuple[str, ...]
    tokens: int


@dataclass(frozen=True)
class Delivery:
    """What the pipeline put in front of the model.

    Attributes:
        units: Distinct unit ids, in delivery order.
        tokens: Evidence tokens delivered.
        calls: ``open_page`` calls made.
        bound: Whether B stopped the pipeline.
        searched: Unit ids the search returned.
        steps: Every call, search first, in order.
    """

    units: tuple[str, ...]
    tokens: int
    calls: int
    bound: bool
    searched: tuple[str, ...]
    steps: tuple[Step, ...] = ()

    def through(self, level: int) -> tuple[str, ...]:
        """Distinct units delivered by the end of ``level``."""
        seen: dict[str, None] = {}
        for step in self.steps:
            if step.level <= level:
                seen.update(dict.fromkeys(step.units))
        return tuple(seen)

    @property
    def deepest(self) -> int:
        """The last level that made a call (``-1``: search only)."""
        return max((s.level for s in self.steps), default=-1)


@dataclass
class World:
    """What the pipeline reads: index, pages, unit texts and link targets."""

    index: HybridIndex
    pages: Pages
    texts: dict[str, str]
    sections: dict[str, str]
    page_kind: dict[str, str]

    @classmethod
    def build(cls, index: HybridIndex, registry: Registry) -> World:
        """From an index and its registry."""
        units = list(index.units.values())
        page_kind: dict[str, str] = {}
        for u in units:
            page_kind.setdefault(u.title, registry.units[u.id].page)
        return cls(index, Pages(units), {u.id: u.text for u in units},
                   {u.id: registry.units[u.id].section for u in units}, page_kind)


class _Run:
    """The state of one pipeline run."""

    def __init__(self, world: World, counter: TokenCounter, budget: int,
                 config: ToolConfig | None) -> None:
        self.world, self.counter, self.budget, self.config = (
            world, counter, budget, config)
        self.delivered: dict[str, None] = {}
        self.steps: list[Step] = []
        self.tokens = 0
        self.calls = 0
        self.bound = False

    def take(self, level: int, call: str, result: ToolResult) -> bool:
        """Record a result if it fits in B; ``False`` stops the run."""
        if self.tokens + result.tokens > self.budget:
            self.bound = True
            return False
        self.tokens += result.tokens
        self.steps.append(Step(level, call, result.unit_ids, result.tokens))
        self.delivered.update(dict.fromkeys(result.unit_ids))
        if level >= 0:
            self.calls += 1
        return True

    def open(self, level: int, title: str, section: str | None = None,
             offset: int = 0) -> ToolResult | None:
        result = open_page(self.world.pages, title, section, offset,
                           counter=self.counter, config=self.config)
        args = [repr(title)] + ([f"section={section!r}"] if section else []) + (
            [f"offset={offset}"] if offset else [])
        return result if self.take(level, f"open_page({', '.join(args)})",
                                   result) else None


def expand_from(
    world: World, first: ToolResult, *, counter: TokenCounter,
    budget: int = EVIDENCE_BUDGET, order: Sequence[str] = LINK_ORDER,
    config: ToolConfig | None = None, query: str = "",
) -> Delivery:
    """Levels 0 and up, from a search result (see the module docstring)."""
    run = _Run(world, counter, budget, config)
    if not run.take(-1, f"search({query!r})", first):
        return Delivery((), 0, 0, True, tuple(first.unit_ids), ())
    units_by_id = {u.id: u for us in world.pages.by_title.values() for u in us}
    done: set[tuple[str, str]] = set()
    for uid in first.unit_ids:  # level 0
        unit = units_by_id[uid]
        if (unit.title, unit.section) in done:
            continue
        done.add((unit.title, unit.section))
        offset = 0
        while True:
            result = run.open(0, unit.title, unit.section, offset)
            if result is None:
                return _delivery(run, first)
            if not result.unit_ids:
                break
            offset += len(result.unit_ids)
    opened: set[str] = set()
    frontier = list(run.delivered)
    level = 1
    while frontier:
        reached: list[str] = []
        for link in ordered(links_of(frontier, world.texts, world.sections,
                                     world.page_kind), order):
            if link.title in opened:
                continue
            result = run.open(level, link.title)
            if result is None:
                return _delivery(run, first)
            opened.add(link.title)
            reached.extend(result.unit_ids)
        frontier, level = reached, level + 1
    return _delivery(run, first)


def _delivery(run: _Run, first: ToolResult) -> Delivery:
    return Delivery(tuple(run.delivered), run.tokens, run.calls, run.bound,
                    tuple(first.unit_ids), tuple(run.steps))


def expand(
    world: World, query: str, *, k: int = 5, counter: TokenCounter,
    budget: int = EVIDENCE_BUDGET, order: Sequence[str] = LINK_ORDER,
    config: ToolConfig | None = None,
) -> Delivery:
    """Search for ``query``, then levels 0 and up until ``budget``.

    Args:
        world: The pipeline's world.
        query: The question text.
        k: Units requested from ``search``.
        counter: Token counter.
        budget: Evidence tokens B.
        order: Link-type order.
        config: Tool condition (main condition by default).
    """
    first = search(world.index, query, k, counter=counter, config=config)
    return expand_from(world, first, counter=counter, budget=budget, order=order,
                       config=config, query=query)
