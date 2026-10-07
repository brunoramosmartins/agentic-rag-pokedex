"""Trajectory-level check under the tool contract (E-001, amendment of
2026-09-30, item 7; PI-021).

The state-level reachability (``examiner/reachability.py``) shows that a set of
units with the right label exists. This module asks whether tool calls can
produce it, and at what cost, before dev is first used:

- **Shortest page reading.** For each question, the fewest ``open_page`` calls
  — and, among those, the fewest evidence tokens — whose results together make
  a sufficient state. A call is a *window*: the units ``open_page(title,
  section, offset)`` returns under the token cap. The search is exact over
  windows of the pages that hold a gold unit; the oracle knows which pages and
  sections to open, an agent does not, so the numbers are what the contract
  allows at best when reading pages. ``search`` can pack units of different
  pages into one call, so it could only lower a count; whether it does depends
  on the ranking. S4 is never sufficient by construction.
- **One search could hold it.** Whether some set of at most ``MAX_K`` gold
  units, one per gold fact, fits in one call's cap: the questions a single
  lucky search could make sufficient. Optimistic by design.
- **Trajectory witnesses on dev.** Each witness state of the state-level check
  is realized by ``open_page`` windows whose union carries the same label.

The check is model-free — registry, gold covers and unit sizes — so it is not
an opening of an evaluation split (decision of 2026-10-06). It prints and
writes counts only; question ids appear for dev only.

Usage::

    python -m agentic_pokedex.examiner.trajectories
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from agentic_pokedex.examiner.reachability import T_MAX, witnesses
from agentic_pokedex.labeling.sufficiency import Gold, gold_from, label_state
from agentic_pokedex.tools.contract import (
    MAX_K,
    TOKEN_CAP,
    UNIT_SEPARATOR,
    TokenCounter,
    pack,
)
from agentic_pokedex.tools.open_page import Pages, select
from agentic_pokedex.world.index import DEFAULT_WORLD_DIR, Unit, load_units
from agentic_pokedex.world.registry import Registry

EVIDENCE_BUDGET = 4_000
"""B, evidence tokens per trajectory (E-001)."""

SEARCH_DEPTH = T_MAX + 1
"""Calls the shortest-trajectory search tries before reporting "beyond"."""

Record = Mapping[str, Any]


@dataclass(frozen=True)
class Window:
    """One ``open_page`` call and what it returns.

    Attributes:
        title: Page title.
        section: The ``section`` argument (``None``: the whole page).
        offset: The ``offset`` argument.
        units: Unit ids returned.
        tokens: Tokens of the returned text.
    """

    title: str
    section: str | None
    offset: int
    units: frozenset[str]
    tokens: int

    def call(self) -> str:
        """The call, as an agent would write it."""
        args = [repr(self.title)]
        if self.section is not None:
            args.append(f"section={self.section!r}")
        if self.offset:
            args.append(f"offset={self.offset}")
        return f"open_page({', '.join(args)})"


def page_windows(
    units: Sequence[Unit], counter: TokenCounter, cap: int = TOKEN_CAP
) -> list[Window]:
    """Every distinct window of one page.

    Selections are the whole page and, for each section line on the page, the
    units ``open_page`` selects with it; each selection is read from every
    offset. Windows returning the same units keep the cheapest call.
    """
    selections: dict[tuple[str, ...], tuple[str | None, list[Unit]]] = {
        tuple(u.id for u in units): (None, list(units))
    }
    for section in sorted({u.section for u in units}):
        chosen = select(list(units), section)
        selections.setdefault(tuple(u.id for u in chosen), (section, chosen))
    best: dict[frozenset[str], Window] = {}
    for section, chosen in selections.values():
        for offset in range(len(chosen)):
            result = pack(chosen[offset:], counter, cap)
            window = Window(units[0].title, section, offset,
                            frozenset(result.unit_ids), result.tokens)
            kept = best.get(window.units)
            if kept is None or window.tokens < kept.tokens:
                best[window.units] = window
    return list(best.values())


class WindowCache:
    """Windows per page title, computed once."""

    def __init__(self, pages: Pages, counter: TokenCounter, cap: int = TOKEN_CAP):
        self.pages = pages
        self.counter = counter
        self.cap = cap
        self.title_of = {u.id: u.title for us in pages.by_title.values() for u in us}
        self._cache: dict[str, list[Window]] = {}

    def of(self, title: str) -> list[Window]:
        """The windows of one page."""
        if title not in self._cache:
            self._cache[title] = page_windows(self.pages.by_title[title],
                                              self.counter, self.cap)
        return self._cache[title]

    def touching(self, unit_ids: Iterable[str]) -> list[Window]:
        """Windows of every page that holds one of ``unit_ids``."""
        titles = sorted({self.title_of[u] for u in unit_ids if u in self.title_of})
        return [w for t in titles for w in self.of(t)]


@dataclass(frozen=True)
class Shortest:
    """The shortest page reading to a sufficient state.

    Attributes:
        calls: Number of calls (``None``: none within the search depth, or
            never sufficient).
        tokens: Evidence tokens of the cheapest trajectory with that many calls.
        windows: The calls, in no particular order.
    """

    calls: int | None
    tokens: int | None
    windows: tuple[Window, ...] = ()


def shortest(gold: Gold, cache: WindowCache, depth: int = SEARCH_DEPTH) -> Shortest:
    """Fewest calls, then fewest tokens, from nothing to a sufficient state.

    Exact set cover over windows: each gold fact needs one of its cover units in
    some window. Facts hit by exactly the same windows are merged, dominated
    windows dropped, and branches cut when the remaining calls cannot cover the
    remaining facts even at the best window's coverage.
    """
    covers = [frozenset(units) for units in gold.cover.values()]
    if not covers or any(not c for c in covers):
        return Shortest(None, None)
    relevant = frozenset().union(*covers)
    by_hits: dict[frozenset[int], Window] = {}
    for window in cache.touching(relevant):
        hits = frozenset(i for i, c in enumerate(covers) if window.units & c)
        kept = by_hits.get(hits)
        if hits and (kept is None or window.tokens < kept.tokens):
            by_hits[hits] = window
    # Merge facts hit by the same windows.
    signature: dict[frozenset[frozenset[int]], int] = {}
    group_of: dict[int, int] = {}
    for i in range(len(covers)):
        sig = frozenset(h for h in by_hits if i in h)
        group_of[i] = signature.setdefault(sig, len(signature))
    candidates: dict[frozenset[int], Window] = {}
    for hits, window in by_hits.items():
        merged = frozenset(group_of[i] for i in hits)
        kept = candidates.get(merged)
        if kept is None or window.tokens < kept.tokens:
            candidates[merged] = window
    items = [(h, w) for h, w in candidates.items()
             if not any(h2 > h and w2.tokens <= w.tokens
                        for h2, w2 in candidates.items())]
    by_group: dict[int, list[tuple[frozenset[int], Window]]] = defaultdict(list)
    for h, w in sorted(items, key=lambda x: (x[1].tokens, x[1].call())):
        for g in h:
            by_group[g].append((h, w))
    full = frozenset(signature.values())
    if any(g not in by_group for g in full):
        return Shortest(None, None)

    def bound(left: frozenset[int]) -> int:
        return max(len(h & left) for h, _ in items)

    def feasible(left: frozenset[int], k: int) -> bool:
        if not left:
            return True
        if k == 0 or k * bound(left) < len(left):
            return False
        g = min(left, key=lambda x: len(by_group[x]))
        return any(feasible(left - h, k - 1) for h, _ in by_group[g])

    calls = next((k for k in range(1, depth + 1) if feasible(full, k)), None)
    if calls is None:
        return Shortest(None, None)
    best: list[Any] = [None, ()]

    def cheapest(left: frozenset[int], k: int, tokens: int,
                 chosen: tuple[Window, ...]) -> None:
        if best[0] is not None and tokens >= best[0]:
            return
        if not left:
            best[0], best[1] = tokens, chosen
            return
        if k == 0 or k * bound(left) < len(left):
            return
        g = min(left, key=lambda x: len(by_group[x]))
        for h, w in by_group[g]:
            cheapest(left - h, k - 1, tokens + w.tokens, (*chosen, w))

    cheapest(full, calls, 0, ())
    return Shortest(calls, best[0], best[1])


def one_search_could(
    gold: Gold, texts: Mapping[str, str], counter: TokenCounter,
    cap: int = TOKEN_CAP, max_k: int = MAX_K,
) -> bool:
    """Whether at most ``max_k`` gold units, one per fact, fit in one call.

    A search result packs up to ``max_k`` units under ``cap``; a single unit
    larger than the cap would still be shown. Optimistic: it ignores ranking.
    """
    covers = sorted((frozenset(c) for c in gold.cover.values()), key=len)
    if not covers or any(not c for c in covers):
        return False

    def fits(chosen: tuple[str, ...]) -> bool:
        if len(chosen) <= 1:
            return True
        return counter(UNIT_SEPARATOR.join(texts[u] for u in chosen)) <= cap

    def go(i: int, chosen: tuple[str, ...]) -> bool:
        while i < len(covers) and covers[i] & set(chosen):
            i += 1
        if i == len(covers):
            return True
        for u in sorted(covers[i]):
            nxt = (*chosen, u)
            if len(nxt) <= max_k and fits(nxt) and go(i + 1, nxt):
                return True
        return False

    return go(0, ())


@dataclass(frozen=True)
class Realized:
    """A trajectory witness: calls whose union has the code's label."""

    code: str
    question: str
    windows: tuple[Window, ...]
    label: str


def _label_text(gold: Gold, units: Iterable[str]) -> str:
    lab = label_state(gold, sorted(units))
    return lab.state + (f" ({lab.subtype})" if lab.subtype else "")


def realize(
    gold: Gold, state: Sequence[str], label: str, cache: WindowCache,
) -> tuple[Window, ...] | None:
    """Windows, one per unit of ``state``, whose union carries ``label``.

    Tries every combination of windows holding the state's units (states are
    one or two units), cheapest first.
    """
    options = [sorted((w for w in cache.touching([u]) if u in w.units),
                      key=lambda w: (w.tokens, w.call()))
               for u in state]
    if any(not o for o in options):
        return None

    def go(i: int, chosen: tuple[Window, ...]) -> tuple[Window, ...] | None:
        if i == len(options):
            seen = frozenset().union(*(w.units for w in chosen))
            return chosen if _label_text(gold, seen) == label else None
        if any(state[i] in w.units for w in chosen):
            return go(i + 1, chosen)
        for w in options[i]:
            found = go(i + 1, (*chosen, w))
            if found is not None:
                return found
        return None

    return go(0, ())


def realize_witnesses(
    records: Sequence[Record], registry: Registry, texts: Mapping[str, str],
    cache: WindowCache,
) -> dict[str, Realized | None]:
    """A trajectory per subtype and error code on dev (``None``: not realized).

    ``never-reached`` needs T_max calls without a sufficient state: the witness
    question's first window is insufficient, and repeating it T_max times keeps
    it so.
    """
    by_id = {r["id"]: r for r in records}
    out: dict[str, Realized | None] = {}
    for code, w in witnesses(records, registry, texts).items():
        if w is None:
            out[code] = None
            continue
        gold = gold_from(by_id[w.question], registry)
        windows = realize(gold, w.state, w.label, cache)
        if windows is not None and code == "never-reached":
            windows = windows * T_MAX
        out[code] = (Realized(code, w.question, windows, w.label)
                     if windows is not None else None)
    return out


@dataclass(frozen=True)
class Measure:
    """One question's numbers."""

    template: str
    stratum: str
    calls: int | None
    tokens: int | None
    one_search: bool
    never: bool


def measure(
    record: Record, registry: Registry, cache: WindowCache,
    texts: Mapping[str, str],
) -> Measure:
    """The shortest page reading and the one-search flag of a question."""
    gold = gold_from(record, registry)
    if record["stratum"] == "S4":
        return Measure(record["template"], "S4", None, None, False, True)
    best = shortest(gold, cache)
    return Measure(record["template"], record["stratum"], best.calls, best.tokens,
                   one_search_could(gold, texts, cache.counter, cache.cap),
                   False)


def summarize(measures: Sequence[Measure]) -> dict[str, Any]:
    """Counts of one group of questions (N-of-M everywhere)."""
    n = len(measures)
    reached = [m for m in measures if m.calls is not None]
    tokens = [m.tokens for m in reached if m.tokens is not None]
    return {
        "questions": n,
        "never_sufficient": sum(m.never for m in measures),
        "calls": dict(sorted(Counter(m.calls for m in reached).items())),
        "beyond_t_max": sum(not m.never and (m.calls is None or m.calls > T_MAX)
                            for m in measures),
        "one_call": sum(m.calls == 1 for m in measures),
        "one_search_could": sum(m.one_search for m in measures),
        "beyond_b": sum(t > EVIDENCE_BUDGET for t in tokens),
        "tokens_median": median(tokens) if tokens else None,
        "tokens_max": max(tokens) if tokens else None,
    }


def report(
    measures: Mapping[str, Measure], membership: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    """Summaries per split and template, and per split overall."""
    groups: dict[tuple[str, str], list[Measure]] = defaultdict(list)
    for qid, m in measures.items():
        split = membership.get(qid, "pool")
        groups[(split, m.template)].append(m)
        groups[(split, "all")].append(m)
    out: dict[str, dict[str, Any]] = defaultdict(dict)
    for (split, template), ms in sorted(groups.items()):
        out[split][template] = summarize(ms)
    return dict(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Trajectory-level check.")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--pool", action="store_true",
                        help="also measure the unassigned questions (slower)")
    args = parser.parse_args(argv)

    from agentic_pokedex.examiner.splits import opaque_id, open_split
    from agentic_pokedex.tools.contract import default_counter

    world = args.world_dir
    registry = Registry.load(world / "registry.json")
    units = load_units(world / "pages" / "twin.jsonl", registry)
    texts = {u.id: u.text for u in units}
    cache = WindowCache(Pages(units), default_counter())
    # Membership for aggregate counts only (model-free; not an opening).
    local = json.loads((world / "examiner" / "splits.json").read_text(
        encoding="utf-8"))
    membership = {q: name for name, ids in local["splits"].items() for q in ids}
    measures: dict[str, Measure] = {}
    dev_order = open_split("dev", "", world_dir=world)
    dev = set(dev_order)
    dev_records = []
    with (world / "examiner" / "questions.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            if record["id"] in dev:
                dev_records.append(record)
            if record["id"] in membership or args.pool:
                measures[record["id"]] = measure(record, registry, cache, texts)

    summary = report(measures, membership)
    head = (f"{'split':<15} {'template':<7} {'M':>5} {'1 call':>6} {'1 search':>8} "
            f"{'>T_max':>6} {'>B':>3} {'never':>5}  calls  tokens(median/max)")
    print(head)
    for split, rows in summary.items():
        for template, s in rows.items():
            m = s["questions"]
            print(f"{split:<15} {template:<7} {m:>5} {s['one_call']:>6} "
                  f"{s['one_search_could']:>8} {s['beyond_t_max']:>6} "
                  f"{s['beyond_b']:>3} {s['never_sufficient']:>5}  "
                  f"{s['calls']}  {s['tokens_median']}/{s['tokens_max']}")

    by_id = {r["id"]: r for r in dev_records}
    realized = realize_witnesses([by_id[q] for q in dev_order], registry, texts,
                                 cache)
    print(f"\n{'code':<27} {'dev question':<14} {'calls':>5}  label")
    for code, r in realized.items():
        if r is None:
            print(f"{code:<27} {'—':<14} {'':>5}  NOT REALIZED")
        else:
            print(f"{code:<27} {opaque_id(r.question):<14} {len(r.windows):>5}  "
                  f"{r.label} — {r.windows[0].call()}")
    beyond_dev = [opaque_id(q) for q in dev_order
                  if not measures[q].never
                  and (measures[q].calls is None or measures[q].calls > T_MAX)]
    out = {
        "t_max": T_MAX, "evidence_budget": EVIDENCE_BUDGET, "token_cap": TOKEN_CAP,
        "summary": summary,
        "dev_beyond_t_max": beyond_dev,
        "witnesses": {code: None if r is None else {
            "question": opaque_id(r.question), "label": r.label,
            "calls": [w.call() for w in r.windows]} for code, r in realized.items()},
    }
    path = world / "examiner" / "trajectories.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    missing = [code for code, r in realized.items() if r is None]
    if missing:
        print(f"\nnot realized on dev: {', '.join(missing)}")
        return 1
    print(f"\nall {len(realized)} codes realized by trajectories on dev; "
          f"written to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
