"""Render the world as sectioned pages whose sections are the evidence units.

One page per species, move, ability and type (ADR-002). Every unit starts with
a metadata header, like a wiki section title::

    Species: Kedros · Section: Learnset · Method: level-up · Version: Diprok/Kastoxgi

Every body line is generated from registered facts, so the fact → units
registry is complete by construction; ``check_world`` proves it by parsing the
text back into fact ids and comparing them with the registry, unit by unit.

Pages:

- **Species:** ``Profile`` (types, abilities, the whole evolution line, forms);
  one ``Form`` unit per non-default entry (types, abilities); ``Notes`` (up to
  two Pokédex texts, free text, outside the registry); one ``Learnset`` unit per
  learn method and version group of the scope.
- **Move:** ``Profile`` (type, category, power); ``Learned by`` per version
  group, level-up only, each entry with the learner's types (S3 filters on
  them), split every ``HUB_CHUNK`` entries.
- **Ability:** ``Holders``, split every ``HOLDERS_CHUNK`` entries.
- **Type:** ``Matchups``, attacking and defending.

Split units share the same header and carry no pagination marker (ADR-009);
the cue variant (``cues=True``) adds ``Part k/N``, for the S3 ablation only.

**Withheld units (S4).** A seeded sample of (species, version group) pairs,
``WITHHELD_PER_GROUP`` per group, among species with a level-up learnset in
every group of the scope. Their level-up ``Learnset`` units leave the index,
and their entries are left out of that group's ``Learned by`` hubs, so no
indexed unit states the withheld levels. Machine, egg and tutor units of the
same species stay: plausible, insufficient evidence.

Out of scope, declared in ``docs/world.md``: learnsets of non-default forms,
learn methods other than level-up, machine, egg and tutor.

Usage::

    python -m agentic_pokedex.world.render
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.world.download import DEFAULT_RAW_DIR
from agentic_pokedex.world.pokeapi import (
    VERSION_SCOPE,
    Record,
    WorldTables,
    iter_learnsets,
    read_world,
)
from agentic_pokedex.world.registry import (
    Fields,
    Registry,
    UnitMeta,
    eff_id,
    evo_id,
    form_id,
    learn_id,
    mcat_id,
    mpower_id,
    mtype_id,
    pability_id,
    ptype_id,
)
from agentic_pokedex.world.twin import DEFAULT_MAP_PATH, TextRewriter, TwinMap

LEARN_METHODS = ("level-up", "machine", "egg", "tutor")
HUB_CHUNK = 20
HOLDERS_CHUNK = 20
MOVES_CHUNK = 40
NOTES_PER_SPECIES = 2
WITHHELD_PER_GROUP = 40
WITHHELD_SEED = 20260929
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "world"

SEP = " · "
ATTACKING = {
    200: "super effective against",
    50: "not very effective against",
    0: "no effect on",
    100: "normal damage against",
}
DEFENDING = {200: "weak to", 50: "resists", 0: "immune to", 100: "normal damage from"}
FACTOR_ORDER = (200, 50, 0, 100)

_LINK = re.compile(r"\[\[(.+?)\]\]")
HUB_ENTRY = re.compile(r"\[\[(.+?)\]\] \((.+?)\) — (?:level (\d+)|on evolution)")


# --- The world model (naming-independent) ------------------------------------


@dataclass
class World:
    """Everything the pages state, keyed by PokéAPI ids."""

    scope: tuple[str, ...]
    species: dict[int, Record]
    pokemon: dict[int, Record]
    default_of: dict[int, int]
    forms_of: dict[int, list[int]]
    types: dict[int, Record]
    moves: dict[int, Record]
    abilities: dict[int, str]
    group_names: dict[str, str]
    pokemon_types: dict[int, list[tuple[int, int]]]
    pokemon_abilities: dict[int, list[tuple[int, int, bool]]]
    parent: dict[int, int]
    chains: dict[int, list[int]]
    efficacy: dict[tuple[int, int], int]
    learnsets: list[Record]
    notes: dict[int, list[str]]
    dropped: Counter[str] = field(default_factory=Counter)


def build_world(
    tables: WorldTables, learn_rows: Sequence[Record], scope: Sequence[str]
) -> World:
    """Index the records for rendering.

    Args:
        tables: Records from ``pokeapi.read_world``.
        learn_rows: Every learnset row (``pokeapi.iter_learnsets``).
        scope: Version groups rendered.

    Returns:
        The world model; ``dropped`` counts learnset rows outside the scope's
        entries and methods.
    """
    species = {s["id"]: s for s in sorted(tables.species, key=lambda r: r["id"])}
    pokemon = {p["id"]: p for p in sorted(tables.pokemon, key=lambda r: r["id"])}
    default_of: dict[int, int] = {}
    forms_of: dict[int, list[int]] = defaultdict(list)
    for p in pokemon.values():
        if p["is_default"]:
            default_of[p["species_id"]] = p["id"]
        else:
            forms_of[p["species_id"]].append(p["id"])

    canonical: dict[str, int] = {}
    for a in sorted(tables.abilities, key=lambda r: r["id"]):
        canonical.setdefault(a["name"], a["id"])
    ability_key = {a["id"]: canonical[a["name"]] for a in tables.abilities}

    pokemon_types: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for r in sorted(tables.pokemon_types, key=lambda r: (r["pokemon_id"], r["slot"])):
        pokemon_types[r["pokemon_id"]].append((r["slot"], r["type_id"]))
    pokemon_abilities: dict[int, list[tuple[int, int, bool]]] = defaultdict(list)
    for r in sorted(
        tables.pokemon_abilities, key=lambda r: (r["pokemon_id"], r["slot"])
    ):
        pokemon_abilities[r["pokemon_id"]].append(
            (r["slot"], ability_key[r["ability_id"]], r["hidden"])
        )

    parent = {e["species_id"]: e["from_species_id"] for e in tables.evolutions}
    chains: dict[int, list[int]] = defaultdict(list)
    for s in species.values():
        chains[s["evolution_chain_id"]].append(s["id"])

    in_scope = set(scope)
    defaults = set(default_of.values())
    dropped: Counter[str] = Counter()
    learnsets = []
    for r in learn_rows:
        if r["version_group"] not in in_scope:
            continue
        if r["pokemon_id"] not in defaults:
            dropped["form learnset rows"] += 1
        elif r["method"] not in LEARN_METHODS:
            dropped[f"method {r['method']}"] += 1
        else:
            learnsets.append(r)

    texts: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for f in tables.flavor_texts:
        texts[f["species_id"]].append((f["version_id"], f["text"]))
    notes: dict[int, list[str]] = {}
    for sid, entries in texts.items():
        chosen: list[str] = []
        for _, text in sorted(entries, key=lambda e: -e[0]):
            if text not in chosen:
                chosen.append(text)
            if len(chosen) == NOTES_PER_SPECIES:
                break
        notes[sid] = chosen

    return World(
        scope=tuple(scope),
        species=species,
        pokemon=pokemon,
        default_of=default_of,
        forms_of=dict(forms_of),
        types={t["id"]: t for t in sorted(tables.types, key=lambda r: r["id"])},
        moves={m["id"]: m for m in sorted(tables.moves, key=lambda r: r["id"])},
        abilities={k: a for a, k in canonical.items()},
        group_names={g["identifier"]: g["name"] for g in tables.version_groups},
        pokemon_types=dict(pokemon_types),
        pokemon_abilities=dict(pokemon_abilities),
        parent=parent,
        chains=dict(chains),
        efficacy={(e["attacker"], e["defender"]): e["factor"] for e in tables.efficacy},
        learnsets=learnsets,
        notes=notes,
        dropped=dropped,
    )


def choose_withheld(
    world: World, per_group: int = WITHHELD_PER_GROUP, seed: int = WITHHELD_SEED
) -> list[tuple[int, str]]:
    """Draw the (Pokémon, version group) pairs whose level-up learnset is withheld.

    Eligible: default entries with a level-up learnset in every group of the
    scope, so the other versions remain as distractors. A species is withheld
    in at most one group.

    Raises:
        ValueError: Fewer eligible species than ``per_group × len(scope)``.
    """
    groups_of: dict[int, set[str]] = defaultdict(set)
    for r in world.learnsets:
        if r["method"] == "level-up":
            groups_of[r["pokemon_id"]].add(r["version_group"])
    eligible = sorted(p for p, gs in groups_of.items() if gs >= set(world.scope))
    needed = per_group * len(world.scope)
    if len(eligible) < needed:
        raise ValueError(f"{len(eligible)} eligible species, {needed} needed")
    random.Random(seed).shuffle(eligible)
    return [
        (eligible[i * per_group + j], group)
        for i, group in enumerate(world.scope)
        for j in range(per_group)
    ]


def world_facts(world: World) -> dict[str, Fields]:
    """Every in-scope fact, by id: what the pages must state."""
    facts: dict[str, Fields] = {}
    for child, par in world.parent.items():
        facts[evo_id(child, par)] = {"kind": "evo", "species": child, "parent": par}
    for sid, forms in world.forms_of.items():
        for pid in forms:
            facts[form_id(pid, sid)] = {"kind": "form", "pokemon": pid, "species": sid}
    for pid, types in world.pokemon_types.items():
        for slot, tid in types:
            facts[ptype_id(pid, slot, tid)] = {
                "kind": "ptype", "pokemon": pid, "slot": slot, "type": tid
            }
    for pid, abilities in world.pokemon_abilities.items():
        for _, key, hidden in abilities:
            facts[pability_id(pid, key, hidden)] = {
                "kind": "pability", "pokemon": pid, "ability": key, "hidden": hidden
            }
    for mid, m in world.moves.items():
        facts[mtype_id(mid, m["type_id"])] = {
            "kind": "mtype", "move": mid, "type": m["type_id"]
        }
        if m["category"]:
            facts[mcat_id(mid, m["category"])] = {
                "kind": "mcat", "move": mid, "category": m["category"]
            }
        if m["power"] is not None:
            facts[mpower_id(mid, m["power"])] = {
                "kind": "mpower", "move": mid, "power": m["power"]
            }
    for (a, d), factor in world.efficacy.items():
        facts[eff_id(a, d, factor)] = {
            "kind": "eff", "attacker": a, "defender": d, "factor": factor
        }
    for r in world.learnsets:
        facts[_learn_fact(r)] = {"kind": "learn", **r}
    return facts


def _learn_fact(r: Record) -> str:
    return learn_id(
        r["pokemon_id"], r["move_id"], r["version_group"], r["method"], r["level"]
    )


# --- Units (naming-independent) ----------------------------------------------


@dataclass
class Unit:
    """A unit's metadata (registered) and its structured body (rendered)."""

    meta: UnitMeta
    body: dict[str, Any]


def _chunks(items: Sequence[Any], size: int) -> list[list[Any]]:
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


def _split(
    base: dict[str, Any], items: Sequence[Any], size: int
) -> list[tuple[dict[str, Any], list[Any]]]:
    parts = _chunks(items, size)
    return [
        ({**base, "id": f"{base['id']}/{i}", "chunk": i, "chunks": len(parts)}, part)
        for i, part in enumerate(parts)
    ]


def _evolution_line(world: World, sid: int) -> list[tuple[int, list[int]]]:
    """(parent, children) pairs of the species' chain, breadth first."""
    members = set(world.chains[world.species[sid]["evolution_chain_id"]])
    children: dict[int, list[int]] = defaultdict(list)
    for child in sorted(members):
        if world.parent.get(child) in members:
            children[world.parent[child]].append(child)
    queue = [m for m in sorted(members) if world.parent.get(m) not in members]
    line = []
    while queue:
        node = queue.pop(0)
        if children[node]:
            line.append((node, children[node]))
            queue.extend(children[node])
    return line


def _profile_facts(world: World, pid: int) -> list[str]:
    facts = [ptype_id(pid, slot, t) for slot, t in world.pokemon_types.get(pid, [])]
    facts += [
        pability_id(pid, key, hidden)
        for _, key, hidden in world.pokemon_abilities.get(pid, [])
    ]
    return facts


def build_units(
    world: World, withheld: Sequence[tuple[int, str]], *, notes: bool = True
) -> list[Unit]:
    """Every unit of every page, in a fixed order, with its facts.

    Args:
        world: The world model.
        withheld: Pairs from ``choose_withheld``.
        notes: Render Pokédex notes (``False`` is the G2 exit plan).

    Returns:
        Units ordered by page kind, entity id, section, method, group, chunk.
    """
    held = set(withheld)
    units: list[Unit] = []

    by_learnset: dict[tuple[int, str, str], list[Record]] = defaultdict(list)
    by_hub: dict[tuple[int, str], list[Record]] = defaultdict(list)
    for r in world.learnsets:
        by_learnset[(r["pokemon_id"], r["method"], r["version_group"])].append(r)
        pair = (r["pokemon_id"], r["version_group"])
        if r["method"] == "level-up" and pair not in held:
            by_hub[(r["move_id"], r["version_group"])].append(r)

    for sid in world.species:
        pid = world.default_of[sid]
        line = _evolution_line(world, sid)
        forms = world.forms_of.get(sid, [])
        facts = _profile_facts(world, pid)
        facts += [evo_id(c, p) for p, cs in line for c in cs]
        facts += [form_id(f, sid) for f in forms]
        base = {"page": "species", "key": sid}
        units.append(Unit(
            UnitMeta(
                id=f"species/{sid}/profile", section="Profile", facts=facts, **base
            ),
            {"pokemon": pid, "evolution": line, "forms": forms},
        ))
        for form in forms:
            units.append(Unit(
                UnitMeta(id=f"species/{sid}/form/{form}", section="Form", form=form,
                         facts=_profile_facts(world, form), **base),
                {"pokemon": form},
            ))
        if notes and world.notes.get(sid):
            units.append(Unit(
                UnitMeta(id=f"species/{sid}/notes", section="Notes", free_text=True,
                         **base),
                {"texts": world.notes[sid]},
            ))
        for method in LEARN_METHODS:
            for group in world.scope:
                rows = by_learnset.get((pid, method, group))
                if not rows:
                    continue
                rows = sorted(rows, key=lambda r: (r["level"] or 0, r["move_id"]))
                head = {"id": f"species/{sid}/learnset/{method}/{group}",
                        "section": "Learnset", "method": method,
                        "version_group": group,
                        "withheld": method == "level-up" and (pid, group) in held,
                        **base}
                for meta, part in _split(head, rows, MOVES_CHUNK):
                    units.append(Unit(
                        UnitMeta(facts=[_learn_fact(r) for r in part], **meta),
                        {"rows": part},
                    ))

    for mid, move in world.moves.items():
        facts = [mtype_id(mid, move["type_id"])]
        if move["category"]:
            facts.append(mcat_id(mid, move["category"]))
        if move["power"] is not None:
            facts.append(mpower_id(mid, move["power"]))
        units.append(Unit(
            UnitMeta(id=f"move/{mid}/profile", page="move", key=mid,
                     section="Profile", facts=facts),
            {},
        ))
        for group in world.scope:
            rows = by_hub.get((mid, group))
            if not rows:
                continue
            rows = sorted(rows, key=lambda r: (
                world.pokemon[r["pokemon_id"]]["species_id"], r["level"] or 0
            ))
            head = {"id": f"move/{mid}/learned-by/{group}", "page": "move",
                    "key": mid, "section": "Learned by", "version_group": group}
            for meta, part in _split(head, rows, HUB_CHUNK):
                facts = []
                for r in part:
                    facts.append(_learn_fact(r))
                    facts += [
                        ptype_id(r["pokemon_id"], slot, t)
                        for slot, t in world.pokemon_types.get(r["pokemon_id"], [])
                    ]
                units.append(Unit(UnitMeta(facts=facts, **meta), {"rows": part}))

    holders: dict[int, list[tuple[int, bool]]] = defaultdict(list)
    for pid, abilities in world.pokemon_abilities.items():
        for _, key, hidden in abilities:
            holders[key].append((pid, hidden))
    for key in sorted(world.abilities):
        entries = sorted(holders.get(key, []))
        head = {"id": f"ability/{key}/holders", "page": "ability", "key": key,
                "section": "Holders"}
        for meta, part in _split(head, entries, HOLDERS_CHUNK):
            units.append(Unit(
                UnitMeta(facts=[pability_id(p, key, h) for p, h in part], **meta),
                {"entries": part},
            ))

    for tid in world.types:
        facts = [eff_id(tid, d, f) for (a, d), f in world.efficacy.items() if a == tid]
        facts += [eff_id(a, tid, f) for (a, d), f in world.efficacy.items() if d == tid]
        units.append(Unit(
            UnitMeta(id=f"type/{tid}/matchups", page="type", key=tid,
                     section="Matchups", facts=facts),
            {},
        ))
    # A fact listed twice in one unit (a type against itself, a move learned at
    # two levels) is still one fact of that unit.
    for unit in units:
        unit.meta.facts = list(dict.fromkeys(unit.meta.facts))
    return units


def build_registry(
    world: World, units: Sequence[Unit], withheld: Sequence[tuple[int, str]]
) -> Registry:
    """The registry of a rendering: every in-scope fact and every unit."""
    return Registry(
        facts=world_facts(world),
        units={u.meta.id: u.meta for u in units},
        version_scope=world.scope,
        withheld_pairs=list(withheld),
    )


# --- Names ------------------------------------------------------------------


@dataclass
class Names:
    """Display names of one naming (real or twin), with inverse lookups.

    Non-default entries sharing a display name get " (2)", " (3)" in id order,
    so every page and form title is unique.
    """

    species: dict[int, str]
    pokemon: dict[int, str]
    types: dict[int, str]
    moves: dict[int, str]
    abilities: dict[int, str]
    groups: dict[str, str]
    rewrite: Callable[[str], str]

    def __post_init__(self) -> None:
        seen: Counter[str] = Counter()
        for pid in sorted(self.pokemon):
            name = self.pokemon[pid]
            seen[name] += 1
            if seen[name] > 1:
                self.pokemon[pid] = f"{name} ({seen[name]})"
        self.inverse: dict[str, dict[str, int]] = {
            kind: {name: key for key, name in getattr(self, kind).items()}
            for kind in ("species", "pokemon", "types", "moves", "abilities")
        }

    def lookup(self, kind: str, name: str) -> int:
        """Id of a display name."""
        return self.inverse[kind][name]

    @classmethod
    def real(cls, world: World) -> Names:
        """The real English names."""
        return cls(
            species={k: s["name"] for k, s in world.species.items()},
            pokemon={k: p["name"] for k, p in world.pokemon.items()},
            types={k: t["name"] for k, t in world.types.items()},
            moves={k: m["name"] for k, m in world.moves.items()},
            abilities=dict(world.abilities),
            groups=dict(world.group_names),
            rewrite=lambda text: text,
        )

    @classmethod
    def twin(cls, world: World, twin_map: TwinMap) -> Names:
        """The twin names; free text rewritten with the same map."""
        real = cls.real(world)
        t = twin_map.to_twin
        return cls(
            species={k: t("species", n) for k, n in real.species.items()},
            pokemon={k: t("pokemon", world.pokemon[k]["name"]) for k in real.pokemon},
            types={k: t("type", n) for k, n in real.types.items()},
            moves={k: t("move", n) for k, n in real.moves.items()},
            abilities={k: t("ability", n) for k, n in real.abilities.items()},
            groups={k: t("version_group", n) for k, n in real.groups.items()},
            rewrite=TextRewriter.from_map(twin_map).rewrite,
        )


# --- Text -------------------------------------------------------------------


def _link(name: str) -> str:
    return f"[[{name}]]"


def header(meta: UnitMeta, names: Names, *, cues: bool = False) -> str:
    """The unit's metadata line."""
    label, title = {
        "species": ("Species", lambda: names.species[meta.key]),
        "move": ("Move", lambda: names.moves[meta.key]),
        "ability": ("Ability", lambda: names.abilities[meta.key]),
        "type": ("Type", lambda: names.types[meta.key]),
    }[meta.page]
    parts = [f"{label}: {title()}", f"Section: {meta.section}"]
    if meta.form is not None:
        parts.append(f"Form: {names.pokemon[meta.form]}")
    if meta.method:
        parts.append(f"Method: {meta.method}")
    if meta.version_group:
        parts.append(f"Version: {names.groups[meta.version_group]}")
    if cues and meta.chunks > 1:
        parts.append(f"Part {meta.chunk + 1}/{meta.chunks}")
    return SEP.join(parts)


def _types_line(world: World, names: Names, pid: int) -> str:
    types = [names.types[t] for _, t in world.pokemon_types.get(pid, [])]
    return "Types: " + " / ".join(_link(t) for t in types)


def _abilities_line(world: World, names: Names, pid: int) -> str:
    entries = world.pokemon_abilities.get(pid, [])
    regular = [_link(names.abilities[k]) for _, k, h in entries if not h]
    hidden = [_link(names.abilities[k]) for _, k, h in entries if h]
    line = "Abilities: " + (", ".join(regular) or "—")
    if hidden:
        line += f"{SEP}Hidden ability: " + ", ".join(hidden)
    return line


def _level(level: int | None) -> str:
    return "on evolution" if level == 0 else f"level {level}"


def body(unit: Unit, world: World, names: Names) -> list[str]:
    """The unit's body lines."""
    meta, data = unit.meta, unit.body
    if meta.page == "species" and meta.section in ("Profile", "Form"):
        pid = data["pokemon"]
        lines = [_types_line(world, names, pid), _abilities_line(world, names, pid)]
        if meta.section == "Profile":
            line = data["evolution"]
            lines.append(
                "Evolution: "
                + ("; ".join(
                    f"{_link(names.species[p])} → "
                    + ", ".join(_link(names.species[c]) for c in cs)
                    for p, cs in line
                ) or "does not evolve")
            )
            if data["forms"]:
                forms = ", ".join(_link(names.pokemon[f]) for f in data["forms"])
                lines.append(f"Forms: {forms}")
        return lines
    if meta.section == "Notes":
        return [names.rewrite(text) for text in data["texts"]]
    if meta.section == "Learnset" and meta.method == "level-up":
        by_level: dict[int, list[str]] = defaultdict(list)
        for r in data["rows"]:
            by_level[r["level"]].append(_link(names.moves[r["move_id"]]))
        return [
            ("On evolution" if lvl == 0 else f"Level {lvl}") + ": " + ", ".join(ms)
            for lvl, ms in sorted(by_level.items())
        ]
    if meta.section == "Learnset":
        moves = ", ".join(_link(names.moves[r["move_id"]]) for r in data["rows"])
        return [f"Moves: {moves}"]
    if meta.page == "move" and meta.section == "Profile":
        move = world.moves[meta.key]
        power = "—" if move["power"] is None else str(move["power"])
        category = move["category"] or "—"
        return [
            f"Type: {_link(names.types[move['type_id']])}{SEP}"
            f"Category: {category}{SEP}Power: {power}"
        ]
    if meta.section == "Learned by":
        return [
            f"{_link(names.pokemon[r['pokemon_id']])} ("
            + "/".join(names.types[t] for _, t in world.pokemon_types[r["pokemon_id"]])
            + f") — {_level(r['level'])}"
            for r in data["rows"]
        ]
    if meta.section == "Holders":
        return [
            _link(names.pokemon[p]) + (" (hidden)" if hidden else "")
            for p, hidden in data["entries"]
        ]
    if meta.section == "Matchups":
        lines = []
        for side, labels, pick in (
            ("Attacking", ATTACKING, lambda a, d: (a == meta.key, d)),
            ("Defending", DEFENDING, lambda a, d: (d == meta.key, a)),
        ):
            groups: dict[int, list[str]] = defaultdict(list)
            for (a, d), factor in sorted(world.efficacy.items()):
                match, other = pick(a, d)
                if match:
                    groups[factor].append(_link(names.types[other]))
            for factor in FACTOR_ORDER:
                if groups.get(factor):
                    listed = ", ".join(groups[factor])
                    lines.append(f"{side} — {labels[factor]}: {listed}")
        return lines
    raise ValueError(f"no body for {meta.id}")


def render_text(unit: Unit, world: World, names: Names, *, cues: bool = False) -> str:
    """Header and body of a unit, one line each."""
    return "\n".join([header(unit.meta, names, cues=cues), *body(unit, world, names)])


# --- Parsing back (the registry check) ---------------------------------------


def _links(text: str) -> list[str]:
    return _LINK.findall(text)


def parse_facts(meta: UnitMeta, text: str, world: World, names: Names) -> set[str]:
    """Recover the fact ids a unit's text states, from the text alone.

    Only the header's page, section, method, group and form are taken from the
    metadata; every value comes from the body. Used to prove the registry
    complete: ``parse_facts`` must equal the unit's registered facts.
    """
    lines = text.split("\n")[1:]
    facts: set[str] = set()
    group = meta.version_group

    def profile_line(pid: int, line: str) -> None:
        if line.startswith("Types: "):
            for slot, name in enumerate(_links(line), start=1):
                facts.add(ptype_id(pid, slot, names.lookup("types", name)))
        elif line.startswith("Abilities: "):
            regular, _, hidden = line.partition(f"{SEP}Hidden ability: ")
            for name in _links(regular):
                facts.add(pability_id(pid, names.lookup("abilities", name), False))
            for name in _links(hidden):
                facts.add(pability_id(pid, names.lookup("abilities", name), True))
        elif line.startswith("Evolution: "):
            for segment in line.removeprefix("Evolution: ").split("; "):
                found = _links(segment)
                if not found:
                    continue
                par = names.lookup("species", found[0])
                for child in found[1:]:
                    facts.add(evo_id(names.lookup("species", child), par))
        elif line.startswith("Forms: "):
            for name in _links(line):
                facts.add(form_id(names.lookup("pokemon", name), meta.key))
        else:
            raise ValueError(f"unexpected line in {meta.id}: {line!r}")

    if meta.section == "Profile" and meta.page == "species":
        pid = world.default_of[meta.key]
        for line in lines:
            profile_line(pid, line)
    elif meta.section == "Form":
        assert meta.form is not None
        for line in lines:
            profile_line(meta.form, line)
    elif meta.section == "Learnset":
        pid = world.default_of[meta.key]
        for line in lines:
            label, _, rest = line.partition(": ")
            if meta.method == "level-up":
                level = 0 if label == "On evolution" else int(label.split()[1])
            else:
                level = None
            for name in _links(rest):
                move = names.lookup("moves", name)
                facts.add(learn_id(pid, move, group, meta.method, level))
    elif meta.section == "Profile" and meta.page == "move":
        m = re.fullmatch(
            rf"Type: \[\[(.+?)\]\]{SEP}Category: (\S+){SEP}Power: (\S+)", lines[0]
        )
        assert m, lines[0]
        facts.add(mtype_id(meta.key, names.lookup("types", m.group(1))))
        if m.group(2) != "—":
            facts.add(mcat_id(meta.key, m.group(2)))
        if m.group(3) != "—":
            facts.add(mpower_id(meta.key, int(m.group(3))))
    elif meta.section == "Learned by":
        for line in lines:
            m = HUB_ENTRY.fullmatch(line)
            assert m, line
            pid = names.lookup("pokemon", m.group(1))
            for slot, name in enumerate(m.group(2).split("/"), start=1):
                facts.add(ptype_id(pid, slot, names.lookup("types", name)))
            level = int(m.group(3)) if m.group(3) else 0
            facts.add(learn_id(pid, meta.key, group, "level-up", level))
    elif meta.section == "Holders":
        for line in lines:
            m = re.fullmatch(r"\[\[(.+?)\]\]( \(hidden\))?", line)
            assert m, line
            pid = names.lookup("pokemon", m.group(1))
            facts.add(pability_id(pid, meta.key, bool(m.group(2))))
    elif meta.section == "Matchups":
        factor_of = {
            ("Attacking", label): f for f, label in ATTACKING.items()
        } | {("Defending", label): f for f, label in DEFENDING.items()}
        for line in lines:
            side_label, _, rest = line.partition(": ")
            side, _, label = side_label.partition(" — ")
            factor = factor_of[(side, label)]
            for name in _links(rest):
                other = names.lookup("types", name)
                a, d = (meta.key, other) if side == "Attacking" else (other, meta.key)
                facts.add(eff_id(a, d, factor))
    return facts


def check_world(
    registry: Registry, units: Sequence[Unit], texts: Sequence[str],
    world: World, names: Names,
) -> list[str]:
    """Every problem with a rendering; empty when the registry is exact.

    - every in-scope fact is stated by at least one unit;
    - no unit states a fact outside the fact table;
    - each unit's text parses back to exactly its registered facts;
    - no main-condition header carries a pagination marker.
    """
    problems = [f"uncovered fact {f}" for f in registry.uncovered_facts()]
    problems += [f"unknown fact {f}" for f in registry.unknown_facts()]
    for unit, text in zip(units, texts, strict=True):
        parsed = parse_facts(unit.meta, text, world, names)
        registered = set(unit.meta.facts)
        if parsed != registered:
            missing = sorted(registered - parsed)[:3]
            extra = sorted(parsed - registered)[:3]
            problems.append(f"{unit.meta.id}: missing {missing}, extra {extra}")
        if re.search(r"Part \d+/\d+", text.split("\n")[0]):
            problems.append(f"{unit.meta.id}: pagination marker in the main condition")
    return problems


# --- Output -----------------------------------------------------------------


def write_units(path: Path, units: Sequence[Unit], texts: Sequence[str]) -> str:
    """Write ``{"id", "text"}`` lines; return the file's SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps({"id": u.meta.id, "text": t}, ensure_ascii=False)
        for u, t in zip(units, texts, strict=True)
    ]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def stats(units: Sequence[Unit], texts: Sequence[str]) -> dict[str, Any]:
    """Unit counts per section and size in estimated tokens (chars / 4)."""
    sections = Counter(
        "/".join(filter(None, (u.meta.page, u.meta.section, u.meta.method)))
        for u in units
    )
    sizes = sorted(len(t) // 4 for u, t in zip(units, texts, strict=True)
                   if not u.meta.withheld)
    return {
        "units": len(units),
        "indexed": sum(not u.meta.withheld for u in units),
        "withheld": sum(u.meta.withheld for u in units),
        "free_text": sum(u.meta.free_text for u in units),
        "by_section": dict(sorted(sections.items())),
        "tokens_est": {
            "mean": round(sum(sizes) / len(sizes)) if sizes else 0,
            "p90": sizes[int(0.9 * (len(sizes) - 1))] if sizes else 0,
            "max": sizes[-1] if sizes else 0,
            "total": sum(sizes),
        },
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Render the world's pages.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--twin-map", type=Path, default=DEFAULT_MAP_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--no-notes", action="store_true", help="drop Pokédex notes")
    parser.add_argument("--cues", action="store_true", help="S3 ablation variant")
    args = parser.parse_args(argv)

    if not args.twin_map.is_file():
        print(f"{args.twin_map} not found; run `python -m agentic_pokedex.world.twin`")
        return 1
    tables = read_world(args.raw_dir)
    learn_rows = list(iter_learnsets(args.raw_dir, tables))
    world = build_world(tables, learn_rows, VERSION_SCOPE)
    withheld = choose_withheld(world)
    units = build_units(world, withheld, notes=not args.no_notes)
    registry = build_registry(world, units, withheld)
    registry.save(args.out_dir / "registry.json")

    ok = True
    suffix = "-cues" if args.cues else ""
    for label, names in (
        ("twin", Names.twin(world, TwinMap.load(args.twin_map))),
        ("real", Names.real(world)),
    ):
        texts = [render_text(u, world, names, cues=args.cues) for u in units]
        path = args.out_dir / "pages" / f"{label}{suffix}.jsonl"
        digest = write_units(path, units, texts)
        problems = (
            [] if args.cues else check_world(registry, units, texts, world, names)
        )
        ok &= not problems
        print(f"[{label}{suffix}] sha256 {digest[:16]}  problems: {len(problems)}")
        for line in problems[:10]:
            print("  FAIL", line)
        if label == "twin":
            print(json.dumps(stats(units, texts), indent=1))
    print(f"Facts: {len(registry.facts):,}  Withheld pairs: {len(withheld)}")
    print("Dropped learnset rows:", dict(world.dropped))
    print("REGISTRY CHECK:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
