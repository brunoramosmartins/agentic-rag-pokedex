"""Export the benchmark v0: twin-side, fact-level, every id opaque.

What goes out follows `docs/data-sources.md` ("Published benchmark"): question
text and answers in twin names, gold chains as fact ids, minimal sufficient
sets (the covers), near-certain and withheld units as unit ids, split ids and
seeds. No unit text, no real names, no twin → real map.

**Opaque ids.** Question, fact and unit ids carry PokéAPI ids
(``learn:6:53:x-y:level-up:1``, ``species/6/profile``), and a PokéAPI id maps
a twin name back to its real one. Published files use
``q-``/``f-``/``u-`` + hex of sha256(seed:id): anyone who rebuilds the corpus
from the pinned commit and the seeds computes the same ids with
``opaque_fact`` and ``opaque_unit``; the files alone reveal nothing.

**Evaluation splits.** By default their questions are listed by id only (the
files in ``data/splits/``); their text, answers and chains are published after
each split's opening. ``--include-evaluation`` exports them too.

Checks before writing: no field holds a raw fact or unit id, and no question or
answer text holds a real species, move, ability or type name. Rows are sorted
by opaque id: generation order follows PokéAPI ids, so row order would leak
the twin → real map.

Usage::

    python -m agentic_pokedex.examiner.benchmark
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from agentic_pokedex.examiner.generate import GENERATOR_SEED
from agentic_pokedex.examiner.shortcuts import Lexicon
from agentic_pokedex.examiner.splits import (
    EVALUATION_SPLITS,
    SPLIT_SEED,
    load_kept,
    opaque_id,
)
from agentic_pokedex.examiner.surfaces import surface_index
from agentic_pokedex.examiner.templates import BY_ID
from agentic_pokedex.world.index import DEFAULT_WORLD_DIR
from agentic_pokedex.world.render import Names

VERSION = "v0"
FORMAT = 1

_RAW_ID = re.compile(
    r"\b(?:species|move|ability|type)/\d+|"
    r"\b(?:learn|ptype|pability|evo|evoend|mtype|mpower|mcat|eff|form):\d"
)


def _opaque(prefix: str, local: str, seed: int, width: int) -> str:
    return prefix + hashlib.sha256(f"{seed}:{local}".encode()).hexdigest()[:width]


def opaque_fact(fact: str, seed: int = SPLIT_SEED) -> str:
    """The published id of a fact."""
    return _opaque("f-", fact, seed, 12)


def opaque_unit(unit: str, seed: int = SPLIT_SEED) -> str:
    """The published id of a unit."""
    return _opaque("u-", unit, seed, 12)


def published_answer(record: Mapping[str, Any], names: Names) -> dict[str, Any]:
    """Expected action, answer, aliases and (S4) the withheld value, in twin
    names. Lists (types, sets) are sorted by name: order is not part of it."""
    kind, a = BY_ID[record["template"]].answer, record["answer"]
    value: Any = {
        "ability": lambda: names.abilities[a],
        "type": lambda: names.types[a],
        "types": lambda: sorted(names.types[t] for t in a),
        "move": lambda: names.moves[a],
        "species-set": lambda: sorted(names.species[x] for x in a),
        "factor": lambda: a,
        "number": lambda: a,
        "level": lambda: a,
        "category": lambda: a,
    }[kind]()
    aliases = [f"×{a:g}", f"x{a:g}", f"{a:g}"] if kind == "factor" else []
    if record["stratum"] == "S4":
        return {"expected": "abstain", "answer": None, "aliases": [],
                "withheld_value": value}
    return {"expected": "answer", "answer": value, "aliases": aliases}


def gold_order(facts: list[str], stratum: str) -> list[str]:
    """S1 keeps chain order (anchor to answer); elsewhere the order carries no
    meaning but can carry PokéAPI id order (S3 members), so it is sorted."""
    return facts if stratum == "S1" else sorted(facts)


def published_record(
    record: Mapping[str, Any], split: str, names: Names
) -> dict[str, Any]:
    """One question as published."""
    return {
        "id": opaque_id(record["id"]),
        "split": split,
        "stratum": record["stratum"],
        "template": record["template"],
        "group": record["group"],
        "surface": surface_index(record["id"], GENERATOR_SEED),
        "question": record["twin_text"],
        **published_answer(record, names),
        "material": record["material"],
        "set_size": record["set_size"],
        "gold_facts": gold_order([opaque_fact(f) for f in record["gold_facts"]],
                                 record["stratum"]),
        "cover": {opaque_fact(f): sorted(opaque_unit(u) for u in units)
                  for f, units in record["cover"].items()},
        "near_certain_units": sorted(opaque_unit(u) for u in record["near_certain"]),
        "withheld_units": sorted(opaque_unit(u) for u in record["withheld_units"]),
    }


def raw_ids(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """Raw fact or unit ids found anywhere in the rows (must be empty)."""
    return [m.group(0) for row in rows
            for m in _RAW_ID.finditer(json.dumps(row, ensure_ascii=False))]


def real_names_in(
    rows: Iterable[Mapping[str, Any]], real: Lexicon
) -> Counter[str]:
    """Real names found in question text and answers, with their counts."""
    found: Counter[str] = Counter()
    for row in rows:
        text = " ".join([row["question"], json.dumps(row.get("answer")),
                         json.dumps(row.get("withheld_value"))])
        found.update(n for n in real.mentions(text) if not n.isdigit())
    return found


def split_of(local: Mapping[str, Any]) -> dict[str, str]:
    """Question id → split name; unassigned questions are ``pool``."""
    return {q: name for name, ids in local["splits"].items() for q in ids}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Export the benchmark v0.")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--include-evaluation", action="store_true",
                        help="export evaluation splits' questions (after opening)")
    args = parser.parse_args(argv)

    from agentic_pokedex.world.download import DEFAULT_RAW_DIR
    from agentic_pokedex.world.pokeapi import VERSION_SCOPE, iter_learnsets, read_world
    from agentic_pokedex.world.render import build_world
    from agentic_pokedex.world.twin import DEFAULT_MAP_PATH, TwinMap

    tables = read_world(DEFAULT_RAW_DIR)
    world = build_world(tables, list(iter_learnsets(DEFAULT_RAW_DIR, tables)),
                        VERSION_SCOPE)
    twin = Names.twin(world, TwinMap.load(DEFAULT_MAP_PATH))
    real = Lexicon(Names.real(world))
    records = load_kept(args.world_dir)
    local = json.loads((args.world_dir / "examiner" / "splits.json").read_text(
        encoding="utf-8"))
    where = split_of(local)

    rows, held = [], Counter()
    for r in records:
        split = where.get(r["id"], "pool")
        if split in EVALUATION_SPLITS and not args.include_evaluation:
            held[split] += 1
            continue
        rows.append(published_record(r, split, twin))
    leaked = raw_ids(rows)
    if leaked:
        print(f"raw ids in the export: {len(leaked)}, e.g. {leaked[:3]}")
        return 1
    names = real_names_in(rows, real)
    if names:
        print(f"real names in question or answer text: {dict(names.most_common(10))}")
        return 1

    # Sorted by opaque id: generation order follows PokéAPI ids (national dex
    # order), and a row's position would map a twin name back to a real one.
    rows.sort(key=lambda row: row["id"])
    out = args.world_dir / "benchmark" / VERSION
    out.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                   for row in rows)
    (out / "questions.jsonl").write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode()).hexdigest()
    counts = Counter(row["split"] for row in rows)
    manifest = {
        "version": VERSION,
        "format": FORMAT,
        "questions": len(rows),
        "by_split": dict(sorted(counts.items())),
        "by_stratum": dict(sorted(Counter(row["stratum"] for row in rows).items())),
        "evaluation_held": dict(sorted(held.items())),
        "seeds": {"generator": GENERATOR_SEED, "splits_and_ids": SPLIT_SEED},
        "questions_sha256": digest,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n",
                                       encoding="utf-8")
    print(f"{len(rows):,} questions → {out / 'questions.jsonl'} (sha256 {digest[:16]})")
    print("by split:", dict(sorted(counts.items())))
    if held:
        print("evaluation splits held back (ids only):", dict(sorted(held.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
