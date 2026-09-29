"""Look up any species, move, ability or type and see its page in both namings.

A local inspection tool for the author: give a real or a twin name, get the
twin ↔ real mapping and the page as the tools serve it, side by side. Real
names and the twin map stay local (`data/world/`); nothing here is published.

Usage::

    python -m agentic_pokedex.world.explore Gengar
    python -m agentic_pokedex.world.explore Reskoxdam --naming twin
    python -m agentic_pokedex.world.explore "Vine Whip" --section level-up
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentic_pokedex.tools.contract import TOKEN_CAP, UNIT_SEPARATOR
from agentic_pokedex.world.index import DEFAULT_WORLD_DIR, Unit, load_units
from agentic_pokedex.world.registry import Registry
from agentic_pokedex.world.twin import DEFAULT_MAP_PATH, TwinMap


def find(twin_map: TwinMap, name: str) -> list[tuple[str, str, str]]:
    """Every (kind, real, twin) whose real or twin name equals ``name``."""
    hits = []
    folded = name.casefold()
    species = set(twin_map.names["species"])
    for kind in ("species", "move", "ability", "type", "pokemon"):
        for real, twin in twin_map.names[kind].items():
            if kind == "pokemon" and real in species:
                continue  # a default entry is its species
            if folded in (real.casefold(), twin.casefold()):
                hits.append((kind, real, twin))
    return hits


def page(units: list[Unit], title: str, section: str | None) -> list[Unit]:
    """The units of a page in page order, filtered like ``open_page``."""
    chosen = [u for u in units if u.title == title]
    if section:
        needle = section.lower()
        chosen = [u for u in chosen if needle in u.section.lower()] or chosen
    return chosen


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Inspect a page in both namings.")
    parser.add_argument("name", help="a real or twin name")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--twin-map", type=Path, default=DEFAULT_MAP_PATH)
    parser.add_argument("--naming", choices=("both", "twin", "real"), default="both")
    parser.add_argument("--section", default=None, help="filter like open_page")
    parser.add_argument("--all", action="store_true",
                        help="the whole page, not only what one call returns")
    args = parser.parse_args(argv)

    twin_map = TwinMap.load(args.twin_map)
    hits = find(twin_map, args.name)
    if not hits:
        print(f"No species, move, ability, type or form named {args.name!r}.")
        return 1
    registry = Registry.load(args.world_dir / "registry.json")
    namings = ("twin", "real") if args.naming == "both" else (args.naming,)
    units = {n: load_units(args.world_dir / "pages" / f"{n}.jsonl", registry)
             for n in namings}

    for kind, real, twin in hits:
        print(f"== {kind}: real {real!r} ↔ twin {twin!r}")
        if kind == "pokemon":
            print("   (a form: its units live on its species' page)\n")
            continue
        for naming in namings:
            title = twin if naming == "twin" else real
            shown = page(units[naming], title, args.section)
            text = UNIT_SEPARATOR.join(u.text for u in shown)
            tokens = len(text) // 4
            note = "" if args.all or tokens <= TOKEN_CAP else (
                f"  (≈{tokens} tokens: one open_page call shows the first ~{TOKEN_CAP})"
            )
            print(f"\n--- {naming} page, {len(shown)} units{note}\n")
            print(text if text else "(no indexed unit)")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
