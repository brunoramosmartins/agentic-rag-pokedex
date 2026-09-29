"""Example pages for the docs: twin-side, Pokédex notes elided.

`docs/data-sources.md` allows a few twin-side pages in documentation provided
every flavor-text unit is elided: what remains is PokéAPI fact content under
twin names. This module prints such pages as Markdown, so the examples in
``docs/world.md`` are regenerated rather than pasted by hand.

Usage::

    python -m agentic_pokedex.world.examples            # the default pages
    python -m agentic_pokedex.world.examples --page species:884 --page type:13
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agentic_pokedex.world.index import DEFAULT_WORLD_DIR, Unit, load_units
from agentic_pokedex.world.registry import Registry

DEFAULT_PAGES = ("species:884", "move:806", "ability:204", "type:13")
"""One page of each kind, chosen for coverage: the species page has a form,
notes, three learn methods and a learnset split in two units; the move's hub
shows learners' types."""


def elide(unit: Unit) -> str:
    """The unit's text, with Pokédex notes replaced by a marker."""
    if unit.section != "Notes":
        return unit.text
    head, _, body = unit.text.partition("\n")
    texts = len([line for line in body.split("\n") if line.strip()])
    return f"{head}\n[flavor text — {texts} text{'s' * (texts != 1)}, local only]"


def page_markdown(units: Sequence[Unit], page: str) -> str:
    """One page as Markdown: a heading and one code block per unit.

    Args:
        units: Indexed units of a page file, in page order.
        page: ``kind:key``, e.g. ``species:884``.
    """
    kind, key = page.split(":")
    prefix = f"{kind}/{key}/"
    chosen = [u for u in units if u.id.startswith(prefix)]
    if not chosen:
        raise ValueError(f"no indexed unit for {page}")
    title = chosen[0].title
    n = len(chosen)
    blocks = [f"#### {kind.capitalize()} page: {title} ({n} unit{'s' * (n != 1)})"]
    blocks += [f"```\n{elide(u)}\n```" for u in chosen]
    return "\n\n".join(blocks) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Print example pages.")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--pages", default="twin", help="page file (twin only)")
    parser.add_argument("--page", action="append", help="kind:key, repeatable")
    args = parser.parse_args(argv)

    if args.pages != "twin":
        print("Examples are published twin-side only (docs/data-sources.md).")
        return 1
    registry = Registry.load(args.world_dir / "registry.json")
    units = load_units(args.world_dir / "pages" / f"{args.pages}.jsonl", registry)
    print("\n".join(page_markdown(units, p) for p in args.page or DEFAULT_PAGES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
