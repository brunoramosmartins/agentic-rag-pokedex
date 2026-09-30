"""Read the PokéAPI CSVs into graph records: the v1 world scope, English names.

Pure functions over ``data/raw/``; no Neo4j here, so every filter is unit-tested
on hand-built fixtures. ``load_graph`` writes the records.

In scope (``docs/world.md``): species and forms; the 18 battle types and their
efficacy table; evolution chains; moves (type, power, category); abilities with
the hidden flag; learnsets per version group; Pokédex flavor text. Everything
else in PokéAPI stays out.

Filters, each counted in ``WorldTables.dropped``:

- **Types**: only the types that appear as an attacker in ``type_efficacy.csv``
  (the 18 battle types). ``unknown``, ``shadow`` and the Tera-only ``stellar``
  have no efficacy rows and no Pokémon.
- **Moves**: only moves some Pokémon learns in some version group, with a
  battle type. Drops shadow moves and the Z- and Max-move variants.
- **Abilities**: ``is_main_series = 1`` only.
- **Flavor text**: English only, whitespace collapsed (the source breaks lines
  with ``\\n`` and form feeds).

Learnsets keep every version group and every learn method; the version scope is
chosen later from the coverage report, not here.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Record = dict[str, Any]

ENGLISH = "en"
"""``languages.identifier`` of the language whose names the real world uses."""

VERSION_SCOPE: tuple[str, ...] = ("x-y", "ultra-sun-ultra-moon", "scarlet-violet")
"""Base version groups of world v1 (generations 6, 7, 9), frozen on 2026-09-29
from the coverage report (``docs/world.md``). The graph keeps every group; pages
and questions use only these."""


@dataclass
class WorldTables:
    """Node and relationship records, except learnsets (streamed separately)."""

    types: list[Record] = field(default_factory=list)
    efficacy: list[Record] = field(default_factory=list)
    version_groups: list[Record] = field(default_factory=list)
    versions: list[Record] = field(default_factory=list)
    species: list[Record] = field(default_factory=list)
    evolutions: list[Record] = field(default_factory=list)
    pokemon: list[Record] = field(default_factory=list)
    pokemon_types: list[Record] = field(default_factory=list)
    abilities: list[Record] = field(default_factory=list)
    pokemon_abilities: list[Record] = field(default_factory=list)
    moves: list[Record] = field(default_factory=list)
    flavor_texts: list[Record] = field(default_factory=list)
    form_only_evolutions: set[int] = field(default_factory=set)
    dropped: Counter[str] = field(default_factory=Counter)


def read_csv(raw_dir: Path, name: str) -> Iterator[dict[str, str]]:
    """Yield the rows of one CSV as dicts of strings."""
    with (raw_dir / name).open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def _int(value: str) -> int | None:
    return int(value) if value.strip() else None


def _bool(value: str) -> bool:
    return value.strip() == "1"


def normalize_text(text: str) -> str:
    """Collapse every run of whitespace (newlines, form feeds) into one space."""
    return " ".join(text.split())


def english_language_id(raw_dir: Path) -> int:
    """Return the id of English in ``languages.csv``."""
    for row in read_csv(raw_dir, "languages.csv"):
        if row["identifier"] == ENGLISH:
            return int(row["id"])
    raise ValueError("languages.csv has no English row")


def english_names(
    raw_dir: Path, name: str, id_column: str, language_id: int
) -> dict[int, str]:
    """Map entity id → English name from a ``*_names.csv`` file."""
    return {
        int(row[id_column]): row["name"]
        for row in read_csv(raw_dir, name)
        if int(row["local_language_id"]) == language_id
    }


def learned_move_ids(raw_dir: Path) -> set[int]:
    """Ids of every move that some Pokémon learns in some version group."""
    return {int(row["move_id"]) for row in read_csv(raw_dir, "pokemon_moves.csv")}


def _version_group_names(
    raw_dir: Path, version_names: dict[int, str]
) -> tuple[dict[int, str], list[Record]]:
    """Build version records and a display name per group ("Scarlet/Violet")."""
    versions: list[Record] = []
    by_group: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for row in read_csv(raw_dir, "versions.csv"):
        vid, gid = int(row["id"]), int(row["version_group_id"])
        name = version_names.get(vid, row["identifier"])
        versions.append(
            {"id": vid, "identifier": row["identifier"], "name": name,
             "version_group_id": gid}
        )
        by_group[gid].append((vid, name))
    names = {gid: "/".join(n for _, n in sorted(vs)) for gid, vs in by_group.items()}
    return names, versions


def _pokemon_names(
    raw_dir: Path, language_id: int, species_names: dict[int, str],
    pokemon_species: dict[int, int],
) -> dict[int, str]:
    """English name per Pokémon entry.

    A default entry takes its species name. A non-default entry (a regional
    form, a Mega, ...) takes the English ``pokemon_name`` of its default form
    ("Mega Charizard X"); failing that, "<species> (<form name>)".
    """
    form_names: dict[int, tuple[str, str]] = {
        int(row["pokemon_form_id"]): (row["pokemon_name"], row["form_name"])
        for row in read_csv(raw_dir, "pokemon_form_names.csv")
        if int(row["local_language_id"]) == language_id
    }
    default_form: dict[int, int] = {
        int(row["pokemon_id"]): int(row["id"])
        for row in read_csv(raw_dir, "pokemon_forms.csv")
        if _bool(row["is_default"])
    }
    names: dict[int, str] = {}
    for pid, sid in pokemon_species.items():
        species = species_names[sid]
        pokemon_name, form_name = form_names.get(default_form.get(pid, -1), ("", ""))
        if pokemon_name:
            names[pid] = pokemon_name
        elif form_name and form_name != species:
            names[pid] = f"{species} ({form_name})"
        else:
            names[pid] = species
    return names


def form_only_evolutions(raw_dir: Path) -> set[int]:
    """Species reached only by evolving a non-default form of their parent.

    ``pokemon_evolution.csv`` names, per evolution method, the form that must
    evolve (``required_pokemon_form_id``). A species is form-only when every
    method requires a form other than the default form of the parent's default
    entry: Cursola evolves from Galarian Corsola, never from Corsola as its
    Profile shows it. The species graph keeps the link; S1 questions do not
    use it (PI-019).
    """
    default_pokemon = {
        int(r["id"]) for r in read_csv(raw_dir, "pokemon.csv") if _bool(r["is_default"])
    }
    default_forms = {
        int(r["id"]) for r in read_csv(raw_dir, "pokemon_forms.csv")
        if _bool(r["is_default"]) and int(r["pokemon_id"]) in default_pokemon
    }
    required: dict[int, list[int | None]] = {}
    for row in read_csv(raw_dir, "pokemon_evolution.csv"):
        species = int(row["evolved_species_id"])
        required.setdefault(species, []).append(_int(row["required_pokemon_form_id"]))
    return {
        species for species, forms in required.items()
        if all(f is not None and f not in default_forms for f in forms)
    }


def read_world(raw_dir: Path) -> WorldTables:
    """Read and filter every table except learnsets.

    Args:
        raw_dir: Directory with the manifest CSVs.

    Returns:
        The records, with the count of every dropped row in ``dropped``.
    """
    t = WorldTables()
    en = english_language_id(raw_dir)

    # Types: the ones with efficacy rows.
    efficacy_rows = list(read_csv(raw_dir, "type_efficacy.csv"))
    battle_types = {int(r["damage_type_id"]) for r in efficacy_rows}
    type_names = english_names(raw_dir, "type_names.csv", "type_id", en)
    for row in read_csv(raw_dir, "types.csv"):
        tid = int(row["id"])
        if tid not in battle_types:
            t.dropped["types"] += 1
            continue
        t.types.append(
            {"id": tid, "identifier": row["identifier"], "name": type_names[tid]}
        )
    t.efficacy = [
        {"attacker": int(r["damage_type_id"]), "defender": int(r["target_type_id"]),
         "factor": int(r["damage_factor"])}
        for r in efficacy_rows
    ]

    # Versions and version groups.
    version_names = english_names(raw_dir, "version_names.csv", "version_id", en)
    group_names, t.versions = _version_group_names(raw_dir, version_names)
    for row in read_csv(raw_dir, "version_groups.csv"):
        gid = int(row["id"])
        t.version_groups.append(
            {"id": gid, "identifier": row["identifier"],
             "name": group_names.get(gid, row["identifier"]),
             "generation": int(row["generation_id"]), "order": int(row["order"])}
        )

    # Species and evolution.
    species_names = english_names(
        raw_dir, "pokemon_species_names.csv", "pokemon_species_id", en
    )
    for row in read_csv(raw_dir, "pokemon_species.csv"):
        sid = int(row["id"])
        t.species.append(
            {"id": sid, "identifier": row["identifier"], "name": species_names[sid],
             "generation": int(row["generation_id"]),
             "evolution_chain_id": int(row["evolution_chain_id"]),
             "is_baby": _bool(row["is_baby"]),
             "is_legendary": _bool(row["is_legendary"]),
             "is_mythical": _bool(row["is_mythical"])}
        )
        parent = _int(row["evolves_from_species_id"])
        if parent is not None:
            t.evolutions.append({"species_id": sid, "from_species_id": parent})

    t.form_only_evolutions = form_only_evolutions(raw_dir)

    # Pokémon entries (forms).
    pokemon_rows = list(read_csv(raw_dir, "pokemon.csv"))
    pokemon_species = {int(r["id"]): int(r["species_id"]) for r in pokemon_rows}
    pokemon_names = _pokemon_names(raw_dir, en, species_names, pokemon_species)
    for row in pokemon_rows:
        pid = int(row["id"])
        t.pokemon.append(
            {"id": pid, "identifier": row["identifier"], "name": pokemon_names[pid],
             "species_id": pokemon_species[pid], "is_default": _bool(row["is_default"])}
        )
    for row in read_csv(raw_dir, "pokemon_types.csv"):
        tid = int(row["type_id"])
        if tid not in battle_types:
            t.dropped["pokemon_types"] += 1
            continue
        t.pokemon_types.append(
            {"pokemon_id": int(row["pokemon_id"]), "type_id": tid,
             "slot": int(row["slot"])}
        )

    # Abilities.
    ability_names = english_names(raw_dir, "ability_names.csv", "ability_id", en)
    kept_abilities: set[int] = set()
    for row in read_csv(raw_dir, "abilities.csv"):
        aid = int(row["id"])
        if not _bool(row["is_main_series"]):
            t.dropped["abilities"] += 1
            continue
        kept_abilities.add(aid)
        t.abilities.append(
            {"id": aid, "identifier": row["identifier"], "name": ability_names[aid]}
        )
    for row in read_csv(raw_dir, "pokemon_abilities.csv"):
        aid = int(row["ability_id"])
        if aid not in kept_abilities:
            t.dropped["pokemon_abilities"] += 1
            continue
        t.pokemon_abilities.append(
            {"pokemon_id": int(row["pokemon_id"]), "ability_id": aid,
             "slot": int(row["slot"]), "hidden": _bool(row["is_hidden"])}
        )

    # Moves: learned by someone, with a battle type.
    categories = {
        int(r["id"]): r["identifier"]
        for r in read_csv(raw_dir, "move_damage_classes.csv")
    }
    move_names = english_names(raw_dir, "move_names.csv", "move_id", en)
    learned = learned_move_ids(raw_dir)
    for row in read_csv(raw_dir, "moves.csv"):
        mid, tid = int(row["id"]), int(row["type_id"])
        if mid not in learned or tid not in battle_types:
            t.dropped["moves"] += 1
            continue
        damage_class = _int(row["damage_class_id"])
        t.moves.append(
            {"id": mid, "identifier": row["identifier"], "name": move_names[mid],
             "type_id": tid, "power": _int(row["power"]),
             "category": categories.get(damage_class) if damage_class else None}
        )

    # Flavor text: English, whitespace collapsed.
    for row in read_csv(raw_dir, "pokemon_species_flavor_text.csv"):
        if int(row["language_id"]) != en:
            t.dropped["flavor_texts"] += 1
            continue
        sid, vid = int(row["species_id"]), int(row["version_id"])
        t.flavor_texts.append(
            {"key": f"{sid}:{vid}", "species_id": sid, "version_id": vid,
             "text": normalize_text(row["flavor_text"])}
        )
    return t


def iter_learnsets(raw_dir: Path, tables: WorldTables) -> Iterator[Record]:
    """Stream learnset rows whose Pokémon and move are both in the world.

    ``level`` is the level for ``level-up`` rows (0 means "on evolution" in
    recent games) and ``None`` for the other methods.

    Args:
        raw_dir: Directory with the manifest CSVs.
        tables: The records from ``read_world`` (for ids and lookups).

    Yields:
        ``{pokemon_id, move_id, version_group, method, level}``.
    """
    pokemon_ids = {p["id"] for p in tables.pokemon}
    move_ids = {m["id"] for m in tables.moves}
    groups = {g["id"]: g["identifier"] for g in tables.version_groups}
    methods = {
        int(r["id"]): r["identifier"]
        for r in read_csv(raw_dir, "pokemon_move_methods.csv")
    }
    for row in read_csv(raw_dir, "pokemon_moves.csv"):
        pid, mid = int(row["pokemon_id"]), int(row["move_id"])
        if pid not in pokemon_ids or mid not in move_ids:
            tables.dropped["learnsets"] += 1
            continue
        method = methods[int(row["pokemon_move_method_id"])]
        yield {
            "pokemon_id": pid,
            "move_id": mid,
            "version_group": groups[int(row["version_group_id"])],
            "method": method,
            "level": _int(row["level"]) if method == "level-up" else None,
        }
