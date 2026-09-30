"""Generate questions: templates → candidates → filters → questions.

Each template's Cypher (``examiner/templates.py``) returns the raw rows; a
builder per template turns them into candidates with a gold answer, the gold
facts the answer is derived from, and — for S1 — the anchor's own answer. The
fact → units registry then gives each gold fact its **cover** (the indexed
units that state it), and the filters of `docs/examiner.md` run in order, each
counted N-of-M.

Gold facts are the facts the answer is derived from. For an arg-max question
("the last move") that is every fact compared, so only a unit holding all of
them — the learnset — covers it.

Usage::

    python -m agentic_pokedex.examiner.generate               # all templates
    python -m agentic_pokedex.examiner.generate --show S1-A1  # print examples
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentic_pokedex.examiner import surfaces
from agentic_pokedex.examiner.templates import BY_ID, QUERIES, TEMPLATES
from agentic_pokedex.world.download import DEFAULT_RAW_DIR
from agentic_pokedex.world.index import DEFAULT_WORLD_DIR
from agentic_pokedex.world.pokeapi import VERSION_SCOPE, iter_learnsets, read_world
from agentic_pokedex.world.registry import (
    Registry,
    eff_id,
    evo_id,
    evoend_id,
    learn_id,
    mcat_id,
    mpower_id,
    mtype_id,
    pability_id,
    ptype_id,
)
from agentic_pokedex.world.render import Names, World, build_world, choose_withheld
from agentic_pokedex.world.twin import DEFAULT_MAP_PATH, POKEMON_TERM, TwinMap

if TYPE_CHECKING:
    from neo4j import Driver

GENERATOR_SEED = 20260929
S3_SIZE = (3, 25)
S1_B1_MOVES = 40
"""S1-B1 crosses damaging moves with every species (~560k pairs); a seeded
sample of moves keeps the pool large and the query small."""
CAP_FLOOR = 0.10
CAP_FACTOR = 1.5
"""Answer-concentration cap: majority share ≤ max(10%, 1.5 × uniform) (PI-012)."""

Rows = list[dict[str, Any]]


@dataclass
class Question:
    """A generated question before splitting.

    Attributes:
        id: Stable id: template and PokéAPI ids (local; opaque ids are used for
            publication).
        template, stratum, group: From the template.
        slots: Entity ids filling the surface form (``X``, ``M``, ``A``, ``B``,
            ``T``: ids; ``V``: group identifier; ``L``: level).
        answer: Canonical answer (ids, numbers, or a sorted list for sets).
        gold_facts: Fact ids the answer is derived from.
        anchor_answer: S1 only: the same attribute read on the anchor.
        material: S1 only: the gold answer differs from the anchor's.
        cover: Gold fact → indexed units stating it (filled by
            ``attach_covers``).
        distractor_facts: S2 and S4: the same question answered by another
            version group of the scope.
        near_certain: S2 and S4: indexed units stating a distractor fact
            (filled by ``attach_covers``).
        withheld_units: S4 only: the withheld units stating the gold facts.
        set_size: S3 only.
    """

    id: str
    template: str
    stratum: str
    group: str
    slots: dict[str, Any]
    answer: Any
    gold_facts: list[str]
    anchor_answer: Any = None
    material: bool | None = None
    cover: dict[str, list[str]] = field(default_factory=dict)
    distractor_facts: list[str] = field(default_factory=list)
    near_certain: list[str] = field(default_factory=list)
    withheld_units: list[str] = field(default_factory=list)
    set_size: int | None = None


@dataclass
class Context:
    """Everything the builders read besides the rows."""

    world: World
    scope: tuple[str, ...]
    withheld: set[tuple[int, str]]

    def hidden(self, pokemon: int) -> frozenset[int]:
        """Canonical hidden-ability keys of a Pokémon entry."""
        return frozenset(
            k for _, k, h in self.world.pokemon_abilities.get(pokemon, []) if h
        )

    def types(self, pokemon: int) -> list[tuple[int, int]]:
        """(slot, type) of a Pokémon entry."""
        return list(self.world.pokemon_types.get(pokemon, []))


def _q(template: str, key: str, **fields: Any) -> Question:
    t = BY_ID[template]
    return Question(id=f"{template}:{key}", template=template, stratum=t.stratum,
                    group=t.group, **fields)


# --- Builders: rows → candidates -------------------------------------------


def build_s0(
    template: str, rows: Rows, ctx: Context, drop: Counter[str]
) -> list[Question]:
    """S0: one fact, one unit."""
    out = []
    for r in rows:
        if template == "S0-A1":
            keys = {ctx.world.ability_key[a] for a in r["abilities"]}
            if len(keys) != 1:
                drop["ambiguous: several hidden abilities"] += 1
                continue
            (key,) = keys
            out.append(_q(template, f"x={r['species']}", slots={"X": r["species"]},
                          answer=key,
                          gold_facts=[pability_id(r["pokemon"], key, True)]))
        elif template == "S0-A2":
            out.append(_q(template, f"m={r['move']}", slots={"M": r["move"]},
                          answer=r["power"],
                          gold_facts=[mpower_id(r["move"], r["power"])]))
        elif template == "S0-A3":
            out.append(_q(template, f"m={r['move']}", slots={"M": r["move"]},
                          answer=r["category"],
                          gold_facts=[mcat_id(r["move"], r["category"])]))
        elif template == "S0-A4":
            out.append(_q(template, f"m={r['move']}", slots={"M": r["move"]},
                          answer=r["type"],
                          gold_facts=[mtype_id(r["move"], r["type"])]))
        elif template == "S0-B1":
            out.append(_q(template, f"a={r['attacker']},b={r['defender']}",
                          slots={"A": r["attacker"], "B": r["defender"]},
                          answer=r["factor"] / 100,
                          gold_facts=[eff_id(r["attacker"], r["defender"],
                                             r["factor"])]))
    return out


def _evo_facts(line: Sequence[int]) -> list[str]:
    return [evo_id(child, par) for par, child in zip(line, line[1:], strict=False)]


def build_s1_final(
    template: str, rows: Rows, ctx: Context, drop: Counter[str]
) -> list[Question]:
    """S1-A1 / S1-A2: an attribute of the single final form of X's line."""
    out = []
    for r in rows:
        line, fp, xp = r["line"], r["final_pokemon"], r["anchor_pokemon"]
        if any(s in ctx.world.form_only for s in line[1:]):
            drop["the line needs a non-default form to evolve"] += 1
            continue
        path = _evo_facts(line) + [evoend_id(line[-1])]
        if template == "S1-A1":
            gold_keys = ctx.hidden(fp)
            if len(gold_keys) != 1:
                drop["final form has no single hidden ability"] += 1
                continue
            (key,) = gold_keys
            answer, anchor = key, sorted(ctx.hidden(xp))
            facts = path + [pability_id(fp, key, True)]
            material = anchor != [key]
        else:
            types = ctx.types(fp)
            answer = sorted(t for _, t in types)
            anchor = sorted(t for _, t in ctx.types(xp))
            facts = path + [ptype_id(fp, slot, t) for slot, t in types]
            material = anchor != answer
        out.append(_q(template, f"x={r['anchor']}", slots={"X": r["anchor"]},
                      answer=answer, gold_facts=facts, anchor_answer=anchor,
                      material=material))
    return out


def build_s1_next(
    template: str, rows: Rows, ctx: Context, drop: Counter[str]
) -> list[Question]:
    """S1-A3: the hidden ability of the single species X evolves into."""
    out = []
    for r in rows:
        if r["next"] in ctx.world.form_only:
            drop["the line needs a non-default form to evolve"] += 1
            continue
        gold_keys = ctx.hidden(r["next_pokemon"])
        if len(gold_keys) != 1:
            drop["next form has no single hidden ability"] += 1
            continue
        (key,) = gold_keys
        anchor = sorted(ctx.hidden(r["anchor_pokemon"]))
        out.append(_q(template, f"x={r['anchor']}", slots={"X": r["anchor"]},
                      answer=key,
                      gold_facts=[evo_id(r["next"], r["anchor"]),
                                  pability_id(r["next_pokemon"], key, True)],
                      anchor_answer=anchor, material=anchor != [key]))
    return out


def build_s1_move(
    template: str, rows: Rows, ctx: Context, drop: Counter[str]
) -> list[Question]:
    """S1-B1: the type multiplier of move M against species X (three facts)."""
    out = []
    for r in rows:
        multiplier = math.prod(f / 100 for _, _, f in r["parts"])
        facts = [mtype_id(r["move"], r["move_type"])]
        for slot, dt, factor in sorted(r["parts"]):
            facts += [ptype_id(r["pokemon"], slot, dt),
                      eff_id(r["move_type"], dt, factor)]
        out.append(_q(template, f"m={r['move']},x={r['species']}",
                      slots={"M": r["move"], "X": r["species"]},
                      answer=multiplier, gold_facts=facts, material=True))
    return out


def learnset_tables(rows: Rows) -> tuple[dict, dict]:
    """(pokemon, group) → level → moves, and (pokemon, move) → group → levels."""
    by_level: dict[tuple[int, str], dict[int, set[int]]] = defaultdict(
        lambda: defaultdict(set)
    )
    by_move: dict[tuple[int, int], dict[str, set[int]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for r in rows:
        p, m, g, level = r["pokemon"], r["move"], r["version_group"], r["level"]
        by_level[(p, g)][level].add(m)
        by_move[(p, m)][g].add(level)
    return by_level, by_move


def _species(ctx: Context, pokemon: int) -> int:
    return ctx.world.pokemon[pokemon]["species_id"]


def build_learnsets(
    template: str, rows: Rows, ctx: Context, drop: Counter[str]
) -> list[Question]:
    """S2-A1, S2-A2, S2-B1, S4-A1, S4-B1 over the level-up rows of the scope."""
    by_level, by_move = learnset_tables(rows)
    out = []
    withheld_side = template.startswith("S4")
    for (p, g), levels in sorted(by_level.items()):
        if ((p, g) in ctx.withheld) != withheld_side:
            continue
        others = [h for h in ctx.scope if h != g and (p, h) in by_level]
        if not others:
            drop["no other group lists this learnset"] += 1
            continue
        x = _species(ctx, p)
        if template in ("S2-A1", "S4-A1"):
            for m in sorted({m for ms in levels.values() for m in ms}):
                mine = by_move[(p, m)][g]
                if len(mine) != 1 or min(mine) < 1:
                    drop["ambiguous: level 0 or several levels"] += 1
                    continue
                (level,) = mine
                listed = [by_move[(p, m)][h] for h in others if by_move[(p, m)].get(h)]
                if not listed:
                    drop["no distractor: other groups do not list the move"] += 1
                    continue
                if not withheld_side and any(level in lv for lv in listed):
                    drop["another group has the same level"] += 1
                    continue
                out.append(_q(template, f"p={p},m={m},v={g}",
                              slots={"X": x, "M": m, "V": g},
                              answer=level,
                              gold_facts=[learn_id(p, m, g, "level-up", level)],
                              distractor_facts=[
                                  learn_id(p, m, h, "level-up", lv)
                                  for h in others
                                  for lv in sorted(by_move[(p, m)].get(h, ()))
                              ]))
        elif template in ("S2-A2", "S4-B1"):
            for level, moves in sorted(levels.items()):
                if level < 1 or len(moves) != 1:
                    drop["ambiguous: level 0 or several moves at the level"] += 1
                    continue
                (m,) = moves
                listed = [by_level[(p, h)].get(level, set()) for h in others]
                listed = [ms for ms in listed if ms]
                if not listed:
                    drop["no distractor: other groups list nothing at the level"] += 1
                    continue
                if not withheld_side and any(m in ms for ms in listed):
                    drop["another group has the same move at the level"] += 1
                    continue
                out.append(_q(template, f"p={p},l={level},v={g}",
                              slots={"X": x, "L": level, "V": g}, answer=m,
                              gold_facts=[learn_id(p, m, g, "level-up", level)],
                              distractor_facts=[
                                  learn_id(p, mv, h, "level-up", level)
                                  for h in others
                                  for mv in sorted(by_level[(p, h)].get(level, ()))
                              ]))
        elif template == "S2-B1":
            top = max(levels)
            if top < 1 or len(levels[top]) != 1:
                drop["ambiguous: several moves at the top level"] += 1
                continue
            (m,) = levels[top]
            last = [by_level[(p, h)][max(by_level[(p, h)])] for h in others]
            if any(m in ms for ms in last):
                drop["another group has the same last move"] += 1
                continue
            facts = [learn_id(p, mv, g, "level-up", lv)
                     for lv, ms in sorted(levels.items()) for mv in sorted(ms)]
            tops = {h: max(by_level[(p, h)]) for h in others}
            out.append(_q(template, f"p={p},v={g}", slots={"X": x, "V": g},
                          answer=m, gold_facts=facts,
                          distractor_facts=[
                              learn_id(p, mv, h, "level-up", tops[h])
                              for h in others
                              for mv in sorted(by_level[(p, h)][tops[h]])
                          ]))
    return out


def build_s3(
    template: str, rows: Rows, ctx: Context, drop: Counter[str]
) -> list[Question]:
    """S3-A1 / S3-B1: the type-T learners of M in V (optionally up to level L)."""
    groups: dict[tuple[int, str, int], dict[int, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        member = groups[(r["move"], r["version_group"], r["type"])].setdefault(
            r["pokemon"], {"slot": r["slot"], "levels": set()}
        )
        member["levels"].add(r["level"])
    out = []
    low, high = S3_SIZE
    for (m, g, t), members in sorted(groups.items()):
        if any((p, g) in ctx.withheld for p in members):
            drop["a member's learnset is withheld"] += 1
            continue
        chosen, slots = dict(members), {"T": t, "M": m, "V": g}
        if template == "S3-B1":
            firsts = sorted(min(v["levels"]) for v in members.values())
            if len(firsts) < low + 1:
                drop["too few learners for a level cap"] += 1
                continue
            cap = firsts[max(low, len(firsts) // 2) - 1]
            chosen = {p: v for p, v in members.items() if min(v["levels"]) <= cap}
            if len(chosen) >= len(members):
                drop["the level cap removes no learner"] += 1
                continue
            slots["L"] = cap
        if not low <= len(chosen) <= high:
            drop["set size outside 3-25"] += 1
            continue
        facts = []
        for p, v in sorted(chosen.items()):
            levels = sorted(v["levels"])
            if template == "S3-B1":
                levels = [lv for lv in levels if lv <= slots["L"]]
            facts += [learn_id(p, m, g, "level-up", lv) for lv in levels]
            facts.append(ptype_id(p, v["slot"], t))
        species = sorted(_species(ctx, p) for p in chosen)
        key = f"m={m},v={g},t={t}" + (f",l={slots['L']}" if "L" in slots else "")
        out.append(_q(template, key, slots=slots, answer=species, gold_facts=facts,
                      set_size=len(species)))
    return out


BUILDERS: Mapping[str, Callable[..., list]] = {
    "S0_HIDDEN_ABILITY": build_s0, "S0_MOVE_POWER": build_s0,
    "S0_MOVE_CATEGORY": build_s0, "S0_MOVE_TYPE": build_s0,
    "S0_TYPE_EFFICACY": build_s0, "S1_FINAL_FORM": build_s1_final,
    "S1_NEXT_FORM": build_s1_next, "S1_MOVE_VS_SPECIES": build_s1_move,
    "LEVEL_UP_LEARNSETS": build_learnsets, "TYPED_LEARNERS": build_s3,
}


# --- Covers and filters ------------------------------------------------------


def attach_covers(questions: Iterable[Question], registry: Registry) -> None:
    """Fill each question's cover, near-certain and withheld units.

    Near-certain units are the indexed units stating a distractor fact: another
    version's answer, which reads as evidence but answers a different question.
    """
    for q in questions:
        q.cover = {f: registry.fact_units(f, indexed_only=True) for f in q.gold_facts}
        q.near_certain = sorted({
            u for f in q.distractor_facts
            for u in registry.fact_units(f, indexed_only=True)
        })
        if q.stratum == "S4":
            q.withheld_units = sorted({
                u for f in q.gold_facts for u in registry.fact_units(f)
                if registry.units[u].withheld
            })


def single_unit(q: Question) -> bool:
    """One indexed unit states every gold fact."""
    covers = [set(units) for units in q.cover.values()]
    return bool(covers) and bool(set.intersection(*covers))


def stratum_filter(q: Question, drop: Counter[str]) -> bool:
    """The stratum's coverage condition (filter 4-5 of the specification)."""
    missing = [f for f, units in q.cover.items() if not units]
    if q.stratum == "S4":
        if len(missing) != len(q.cover):
            drop["S4: an indexed unit states the answer"] += 1
            return False
        return True
    if missing:
        drop["a gold fact is in no indexed unit"] += 1
        return False
    # S2 is one fact by nature (its difficulty is the wrong-version
    # distractor); S0 is one unit by design. Only multi-hop strata are checked.
    if q.stratum in ("S1", "S3") and single_unit(q):
        drop["single-unit shortcut"] += 1
        return False
    return True


def answer_key(q: Question) -> str:
    """Hashable answer, for the concentration cap."""
    return json.dumps(q.answer, sort_keys=True)


def cap_concentration(
    questions: Sequence[Question], seed: int = GENERATOR_SEED
) -> tuple[list[Question], dict[str, Any]]:
    """Downsample so the majority answer holds at most the cap share.

    The cap is max(10%, 1.5 × uniform chance), uniform over the answers present
    in the pool. The largest per-answer count ``k`` with k ≤ cap × Σ min(c, k)
    is kept; each answer keeps a seeded sample of at most ``k``.

    Returns:
        The kept questions (original order) and a before/after summary.
    """
    counts = Counter(answer_key(q) for q in questions)
    n_values = len(counts)
    if not questions:
        return [], {"values": 0}
    cap = max(CAP_FLOOR, CAP_FACTOR / n_values)
    k = max(counts.values())
    while k > 1 and k > cap * sum(min(c, k) for c in counts.values()):
        k -= 1
    rng = random.Random(seed)
    keep_ids: set[str] = set()
    by_answer: dict[str, list[Question]] = defaultdict(list)
    for q in questions:
        by_answer[answer_key(q)].append(q)
    for key in sorted(by_answer):
        group = sorted(by_answer[key], key=lambda q: q.id)
        rng.shuffle(group)
        keep_ids.update(q.id for q in group[:k])
    kept = [q for q in questions if q.id in keep_ids]
    after = Counter(answer_key(q) for q in kept)
    summary = {
        "values": n_values,
        "cap": round(cap, 4),
        "majority_before": round(max(counts.values()) / len(questions), 4),
        "majority_after": round(max(after.values()) / len(kept), 4),
        "before": len(questions),
        "after": len(kept),
    }
    return kept, summary


# --- Text --------------------------------------------------------------------


def slot_text(q: Question, names: Names, term: str) -> dict[str, str]:
    """Display names for a question's slots in one naming."""
    s = q.slots
    text: dict[str, str] = {"TERM": term}
    if "X" in s:
        text["X"] = names.species[s["X"]]
    if "M" in s:
        text["M"] = names.moves[s["M"]]
    for key in ("A", "B", "T"):
        if key in s:
            text[key] = names.types[s[key]]
    if "V" in s:
        text["V"] = names.groups[s["V"]]
    if "L" in s:
        text["L"] = str(s["L"])
    return text


def answer_text(q: Question, names: Names) -> str:
    """The gold answer in one naming."""
    kind = BY_ID[q.template].answer
    a = q.answer
    if q.stratum == "S4":
        value = names.moves[a] if kind == "move" else str(a)
        return f"abstain (withheld value: {value})"
    if kind == "ability":
        return names.abilities[a]
    if kind == "type":
        return names.types[a]
    if kind == "types":
        return " / ".join(names.types[t] for t in a)
    if kind == "move":
        return names.moves[a]
    if kind == "species-set":
        return ", ".join(sorted(names.species[x] for x in a))
    if kind == "factor":
        return f"×{a:g}"
    return str(a)


def question_text(q: Question, names: Names, term: str, seed: int) -> str:
    """The question in one naming, with its seeded surface form."""
    index = surfaces.surface_index(q.id, seed)
    return surfaces.render(q.template, index, slot_text(q, names, term))


# --- Pipeline ----------------------------------------------------------------


def run_query(driver: Driver, name: str, **params: Any) -> Rows:
    """Rows of one named query."""
    records, _, _ = driver.execute_query(QUERIES[name], **params)
    return [dict(r) for r in records]


def check_scope(rows: Rows, scope: Sequence[str]) -> None:
    """Refuse rows from a version group outside the scope.

    Raises:
        ValueError: A row carries a version group outside ``scope``.
    """
    outside = {r["version_group"] for r in rows if "version_group" in r} - set(scope)
    if outside:
        raise ValueError(f"rows outside the version scope: {sorted(outside)}")


def sample_moves(
    world: World, n: int = S1_B1_MOVES, seed: int = GENERATOR_SEED
) -> list[int]:
    """A seeded sample of damaging moves for S1-B1."""
    damaging = sorted(m for m, move in world.moves.items() if move["power"] is not None)
    return sorted(random.Random(seed).sample(damaging, min(n, len(damaging))))


def generate(
    driver: Driver, world: World, registry: Registry, scope: Sequence[str],
    withheld: Iterable[tuple[int, str]], templates: Sequence[str] | None = None,
) -> tuple[list[Question], dict[str, Any]]:
    """Run every template and every filter.

    Returns:
        The questions that pass, and per-template counts (candidates, each
        drop reason, the concentration cap summary, the S1 material split).
    """
    ctx = Context(world, tuple(scope), set(withheld))
    cache: dict[str, Rows] = {}
    questions: list[Question] = []
    report: dict[str, Any] = {}
    for t in TEMPLATES:
        if templates and t.id not in templates:
            continue
        if t.query not in cache:
            params: dict[str, Any] = {"scope": list(scope)}
            if t.query == "S1_MOVE_VS_SPECIES":
                params["moves"] = sample_moves(world)
            rows = run_query(driver, t.query, **params)
            check_scope(rows, scope)
            cache[t.query] = rows
        drop: Counter[str] = Counter()
        candidates = BUILDERS[t.query](t.id, cache[t.query], ctx, drop)
        built_drops = sum(drop.values())
        attach_covers(candidates, registry)
        passed = [q for q in candidates if stratum_filter(q, drop)]
        if t.stratum == "S4":
            # The correct S4 answer is always to abstain: no guess of the
            # withheld value can be lucky, so there is nothing to cap.
            kept, cap = passed, {"values": 0, "exempt": "S4"}
        else:
            kept, cap = cap_concentration(passed)
        questions += kept
        entry: dict[str, Any] = {
            "candidates": len(candidates) + built_drops,
            "dropped": dict(sorted(drop.items())),
            "after_filters": len(passed),
            "cap": cap,
            "kept": len(kept),
        }
        if t.stratum == "S1":
            entry["material"] = sum(1 for q in kept if q.material)
            entry["benign"] = sum(1 for q in kept if q.material is False)
        report[t.id] = entry
    return questions, report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate the examiner's questions.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--twin-map", type=Path, default=DEFAULT_MAP_PATH)
    parser.add_argument("--template", action="append", help="only these templates")
    parser.add_argument("--show", default=None, help="print examples of a template")
    parser.add_argument("-n", type=int, default=3, help="examples to print")
    args = parser.parse_args(argv)

    from agentic_pokedex.world.load_graph import connect

    tables = read_world(args.raw_dir)
    learn_rows = list(iter_learnsets(args.raw_dir, tables))
    world = build_world(tables, learn_rows, VERSION_SCOPE)
    registry = Registry.load(args.world_dir / "registry.json")
    twin_map = TwinMap.load(args.twin_map)
    withheld = choose_withheld(world)
    wanted = args.template or ([args.show] if args.show else None)
    with connect() as driver:
        questions, report = generate(driver, world, registry, VERSION_SCOPE,
                                     withheld, wanted)

    twin, real = Names.twin(world, twin_map), Names.real(world)
    twin_term = twin_map.to_twin("term", POKEMON_TERM)
    print(f"{'template':<8} {'candidates':>10} {'filters':>8} {'kept':>6}  cap")
    for tid, e in report.items():
        cap = e["cap"]
        extra = (f"  material {e['material']} / benign {e['benign']}"
                 if "material" in e else "")
        shares = (f"majority {cap.get('majority_before', 0):.0%}→"
                  f"{cap.get('majority_after', 0):.0%}" if cap.get("values") else "")
        print(f"{tid:<8} {e['candidates']:>10,} {e['after_filters']:>8,} "
              f"{e['kept']:>6,}  {shares}{extra}")
        for reason, n in e["dropped"].items():
            print(f"{'':<10}- {reason}: {n:,}")

    if args.show:
        shown = [q for q in questions if q.template == args.show]
        rng = random.Random(GENERATOR_SEED)
        for q in rng.sample(shown, min(args.n, len(shown))):
            print(f"\n[{q.id}]  stratum {q.stratum}"
                  + (f", {'material' if q.material else 'benign'}"
                     if q.material is not None else ""))
            print("  twin:", question_text(q, twin, twin_term, GENERATOR_SEED))
            print("        answer:", answer_text(q, twin))
            print("  real:", question_text(q, real, POKEMON_TERM, GENERATOR_SEED))
            print("        answer:", answer_text(q, real))
            for fact, units in q.cover.items():
                shown_units = ", ".join(units[:3]) + (" …" if len(units) > 3 else "")
                print(f"    {fact:<40} {shown_units or '(withheld)'}")
            if q.near_certain:
                print(f"    near-certain: {', '.join(q.near_certain[:3])}"
                      + (" …" if len(q.near_certain) > 3 else ""))

    if wanted:
        print("\n(partial run: the question file is written only by a full run)")
        return 0
    out = args.world_dir / "examiner"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "questions.jsonl").open("w", encoding="utf-8") as handle:
        for q in questions:
            row = asdict(q) | {
                "expected": "abstain" if q.stratum == "S4" else "answer",
                "twin_text": question_text(q, twin, twin_term, GENERATOR_SEED),
                "twin_answer": answer_text(q, twin),
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    digest = hashlib.sha256((out / "questions.jsonl").read_bytes()).hexdigest()
    print(f"\n{len(questions):,} questions → {out / 'questions.jsonl'} "
          f"(sha256 {digest[:16]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
