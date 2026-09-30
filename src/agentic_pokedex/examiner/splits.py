"""Split the generated questions: dev, train and the evaluation splits.

Rules (`docs/examiner.md`, "Splits"; E-001):

- **Families.** Questions that share a (template, anchor entity) pair or an
  identical gold chain form one family, and a family belongs to one split
  only. Anchor entity: the species X, or the move M (S0-A2 to A4, S3), or the
  type pair (S0-B1). Identical chains join S2-A1 with S2-A2 and S4-A1 with
  S4-B1 (the same learn fact asked two ways). Every split is disjoint from every
  other, not only dev and train from eval-L1.
- **Sizes per stratum**, split evenly across the stratum's templates by largest
  remainder, group A first. In S1, the group-A share is then split across S1-A1
  to S1-A3 in proportion to their material pools (PI-018); S1-B1 keeps its
  even share, so the A/B proportion is unchanged.
- **Eligibility.** Questions discarded by the shortcut scan never enter. S1
  group-A questions are material everywhere except the benign slice
  (``eval-L1-benign``), which is benign only.
- **Draw.** Per template, a seeded permutation of its families; each pass takes
  at most one question per family, so a split spreads over as many anchors (for
  S4, withheld pairs) as it can. A split claims a new family while it is under
  its cap for the family's pool; a pool with fewer families than questions
  demanded (S4: 121 families) is capped in proportion to each split's demand.
- **Order.** dev, train, eval-L1, eval-L1-benign, val-B, eval-L2, eval-L3. A
  later eval-L1 extension (gate 8) draws after all of them, so it leaves every
  other split — and the first 400 of eval-L1 — unchanged.
- **Ids.** Versioned files hold opaque ids, ``q-`` + 10 hex of
  sha256(seed:id). The seed is public, so the mapping can be rebuilt by running
  this module; the point is to keep PokéAPI ids, which map twin names back to
  real ones, out of published files. The mapping is written locally.
- **Freezing.** dev and train are frozen: rewriting them with different ids
  fails. Evaluation ids are frozen at the dress rehearsal.
- **Openings.** ``openings.json`` counts each evaluation split's openings,
  from 0. ``open_split`` is the only reader of an evaluation split's ids and
  records every call; a second opening needs ``reopen=True`` and is counted
  too. An opened split can no longer be redrawn.

Usage::

    python -m agentic_pokedex.examiner.splits
    python -m agentic_pokedex.examiner.splits --eval-l1-extra 20   # gate 8
    python -m agentic_pokedex.examiner.splits --refreeze   # before any use only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.examiner.templates import TEMPLATES
from agentic_pokedex.world.index import DEFAULT_WORLD_DIR

SPLIT_SEED = 20260929
ID_PREFIX = "q-"
DEFAULT_SPLITS_DIR = REPO_ROOT / "data" / "splits"
OPENINGS_FILE = "openings.json"
EVALUATION_SPLITS = ("eval-L1", "eval-L1-benign", "val-B", "eval-L2", "eval-L3")
"""Opened once each; the opening count is published."""
STRATA = ("S0", "S1", "S2", "S3", "S4")
S1_GROUP_A = ("S1-A1", "S1-A2", "S1-A3")

Record = Mapping[str, Any]


@dataclass(frozen=True)
class SplitSpec:
    """One split.

    Attributes:
        name: File name without extension.
        per_stratum: Questions per stratum.
        group: ``A`` or ``B`` for one template group only; ``None`` for both.
        frozen: Rewriting it with different ids is refused.
        benign: The S1 benign slice: benign questions only.
    """

    name: str
    per_stratum: Mapping[str, int]
    group: str | None = None
    frozen: bool = False
    benign: bool = False


def _even(n: int) -> dict[str, int]:
    return {s: n for s in STRATA}


SPECS: tuple[SplitSpec, ...] = (
    SplitSpec("dev", _even(30), group="A", frozen=True),
    SplitSpec("train", _even(30), group="A", frozen=True),
    SplitSpec("eval-L1", {"S0": 80, "S1": 80, "S2": 80, "S3": 80, "S4": 80}),
    SplitSpec("eval-L1-benign", {"S1": 40}, group="A", benign=True),
    SplitSpec("val-B", _even(12), group="B"),
    SplitSpec("eval-L2", {"S0": 40, "S1": 60, "S2": 60, "S3": 60, "S4": 60}),
    SplitSpec("eval-L3", _even(30)),
)
"""In draw order. ``train`` holds the 150 questions for real trajectories; the
pool of simulated states is the group-A families left unassigned once eval-L1
is frozen."""


# --- Families -------------------------------------------------------------------


def anchor_key(record: Record) -> str:
    """The anchor entity of a question, for the separation rule. S4's is its
    withheld pair: both S4 templates rest on the same missing learnset."""
    t, s = record["template"], record["slots"]
    if record["stratum"] == "S4":
        return f"pair:{s['X']}:{s['V']}"
    if t in ("S0-A2", "S0-A3", "S0-A4") or record["stratum"] == "S3":
        return f"move:{s['M']}"
    if t == "S0-B1":
        return f"types:{s['A']},{s['B']}"
    return f"species:{s['X']}"


def family_key(record: Record) -> tuple[str, str, str]:
    """(template, anchor) — for S4 (stratum, withheld pair), across templates."""
    scope = "S4" if record["stratum"] == "S4" else record["template"]
    return ("anchor", scope, anchor_key(record))


def families(records: Sequence[Record]) -> dict[str, str]:
    """Question id → family id (the smallest question id of the family)."""
    parent: dict[str, str] = {r["id"]: r["id"] for r in records}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    groups: dict[Any, list[str]] = defaultdict(list)
    for r in records:
        groups[family_key(r)].append(r["id"])
        groups[("chain", tuple(sorted(r["gold_facts"])))].append(r["id"])
    for ids in groups.values():
        for other in ids[1:]:
            union(ids[0], other)
    return {r["id"]: find(r["id"]) for r in records}


def template_pools(
    records: Sequence[Record], family: Mapping[str, str]
) -> dict[str, str]:
    """Template → pool: templates that share a family draw from one pool."""
    templates_of: dict[str, set[str]] = defaultdict(set)
    for r in records:
        templates_of[family[r["id"]]].add(r["template"])
    pool = {t.id: t.id for t in TEMPLATES}

    def find(t: str) -> str:
        while pool[t] != t:
            t = pool[t]
        return t

    for ts in templates_of.values():
        first, *rest = sorted(ts)
        for t in rest:
            a, b = find(first), find(t)
            if a != b:
                pool[max(a, b)] = min(a, b)
    return {t: find(t) for t in pool}


# --- Sizes ----------------------------------------------------------------------


def apportion(n: int, weights: Sequence[float]) -> list[int]:
    """Largest-remainder apportionment; ties go to the earlier position."""
    total = sum(weights)
    quotas = [n * w / total for w in weights]
    counts = [int(q) for q in quotas]
    order = sorted(range(len(weights)), key=lambda i: (-(quotas[i] - counts[i]), i))
    for i in order[: n - sum(counts)]:
        counts[i] += 1
    return counts


def allocation(
    spec: SplitSpec,
    material: Mapping[str, int],
    per_stratum: Mapping[str, int] | None = None,
) -> dict[str, int]:
    """Questions per template for one split.

    Args:
        spec: The split.
        material: S1 group-A template → size of its material pool.
        per_stratum: Override of ``spec.per_stratum`` (an eval-L1 extension).
    """
    sizes = per_stratum or spec.per_stratum
    out: dict[str, int] = {}
    for stratum, n in sizes.items():
        templates = [t.id for t in TEMPLATES if t.stratum == stratum
                     and (spec.group is None or t.group == spec.group)]
        if spec.benign:
            templates = [t for t in templates if t in S1_GROUP_A]
        counts = dict(zip(templates, apportion(n, [1] * len(templates)), strict=True))
        group_a = [t for t in templates if t in S1_GROUP_A]
        if stratum == "S1" and not spec.benign and group_a:
            share = sum(counts[t] for t in group_a)
            counts.update(zip(group_a, apportion(share, [material[t] for t in group_a]),
                              strict=True))
        out.update(counts)
    return out


# --- Draw -----------------------------------------------------------------------


def eligible(record: Record, spec: SplitSpec) -> bool:
    """Whether a question may enter the split (the template aside)."""
    if record["template"] in S1_GROUP_A:
        return bool(record["material"]) != spec.benign
    return True


@dataclass
class Draw:
    """The state of a draw: which split owns each family, and what was taken."""

    records: Mapping[str, Record]
    family: Mapping[str, str]
    pool: Mapping[str, str]
    seed: int = SPLIT_SEED
    owner: dict[str, str] = field(default_factory=dict)
    claims: Counter[tuple[str, str]] = field(default_factory=Counter)
    caps: dict[tuple[str, str], int] = field(default_factory=dict)
    taken: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def __post_init__(self) -> None:
        self._by_template: dict[str, dict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list))
        for qid, r in sorted(self.records.items()):
            self._by_template[r["template"]][self.family[qid]].append(qid)
        self._used: set[str] = set()

    def families_of(self, template: str) -> list[str]:
        """The template's families in its seeded order."""
        fams = sorted(self._by_template[template])
        random.Random(f"{self.seed}:{template}").shuffle(fams)
        return fams

    def _questions(self, template: str, fam: str) -> list[str]:
        qids = list(self._by_template[template][fam])
        random.Random(f"{self.seed}:{template}:{fam}").shuffle(qids)
        return qids

    def draw(self, spec: SplitSpec, template: str, n: int) -> list[str]:
        """Take ``n`` questions of a template for a split.

        Raises:
            ValueError: The pool runs out before ``n`` questions.
        """
        key = (spec.name, self.pool[template])
        got: list[str] = []
        order = self.families_of(template)
        while len(got) < n:
            progress = False
            for fam in order:
                if len(got) == n:
                    break
                owner = self.owner.get(fam)
                if owner is not None and owner != spec.name:
                    continue
                if owner is None and self.claims[key] >= self.caps.get(key, n):
                    continue
                free = [q for q in self._questions(template, fam)
                        if q not in self._used and eligible(self.records[q], spec)]
                if not free:
                    continue
                if owner is None:
                    self.owner[fam] = spec.name
                    self.claims[key] += 1
                self._used.add(free[0])
                got.append(free[0])
                progress = True
            if not progress:
                raise ValueError(
                    f"{spec.name}: {template} ran out at {len(got)} of {n}")
        self.taken[spec.name] += got
        return got


def set_caps(
    draw: Draw, plan: Mapping[str, Mapping[str, int]]
) -> dict[str, dict[str, int]]:
    """Cap the families each split may claim from a scarce pool.

    A pool with at least as many families as questions demanded is not capped
    (a split may claim one family per question). Otherwise each split may claim
    its proportional share of the pool's families, at least one.

    Returns:
        Per pool: families, questions demanded, and whether it is capped.
    """
    demand: Counter[tuple[str, str]] = Counter()
    for split, counts in plan.items():
        for template, n in counts.items():
            demand[(split, draw.pool[template])] += n
    pool_families: dict[str, set[str]] = defaultdict(set)
    for qid, r in draw.records.items():
        pool_families[draw.pool[r["template"]]].add(draw.family[qid])
    totals: Counter[str] = Counter()
    for (_, pool), n in demand.items():
        totals[pool] += n
    summary = {}
    for pool, fams in sorted(pool_families.items()):
        scarce = len(fams) < totals[pool]
        summary[pool] = {"families": len(fams), "demand": totals[pool],
                         "capped": scarce}
        for (split, p), n in demand.items():
            if p == pool:
                draw.caps[(split, pool)] = (
                    max(1, len(fams) * n // totals[pool]) if scarce else n
                )
    return summary


def build_splits(
    records: Sequence[Record], eval_l1_extra: int = 0, seed: int = SPLIT_SEED
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Draw every split.

    Args:
        records: The kept questions (discarded ones already removed).
        eval_l1_extra: Extra eval-L1 questions per stratum (gate 8), drawn last.
        seed: The split seed.

    Returns:
        Split name → question ids in draw order, and a report (allocation,
        pools, families per split).
    """
    by_id = {r["id"]: r for r in records}
    family = families(records)
    pool = template_pools(records, family)
    material = Counter(r["template"] for r in records
                       if r["template"] in S1_GROUP_A and r["material"])
    plan = {spec.name: allocation(spec, material) for spec in SPECS}
    draw = Draw(by_id, family, pool, seed)
    pools = set_caps(draw, plan)
    for spec in SPECS:
        for template, n in plan[spec.name].items():
            draw.draw(spec, template, n)
    if eval_l1_extra:
        spec = next(s for s in SPECS if s.name == "eval-L1")
        grown = allocation(spec, material,
                           {s: n + eval_l1_extra for s, n in spec.per_stratum.items()})
        extra = {t: max(0, grown[t] - plan["eval-L1"].get(t, 0)) for t in grown}
        more: Counter[str] = Counter()
        for template, n in extra.items():
            more[pool[template]] += n
        for p, n in more.items():
            draw.caps[("eval-L1", p)] = draw.claims[("eval-L1", p)] + n
        for template, n in extra.items():
            draw.draw(spec, template, n)
        plan["eval-L1+"] = extra
    report = {
        "seed": seed,
        "allocation": plan,
        "material_pools": dict(sorted(material.items())),
        "pools": pools,
        "families": len(set(family.values())),
    }
    return dict(draw.taken), report


# --- Checks and summaries -----------------------------------------------------------


def separation(
    splits: Mapping[str, Sequence[str]], records: Mapping[str, Record]
) -> dict[str, int]:
    """Count questions sharing a (template, anchor) pair or a gold chain with a
    question of another split; every count must be 0."""
    where: dict[Any, set[str]] = defaultdict(set)
    for name, qids in splits.items():
        for q in qids:
            r = records[q]
            where[family_key(r)].add(name)
            where[("chain", tuple(sorted(r["gold_facts"])))].add(name)
    shared = {k for k, names in where.items() if len(names) > 1}
    out = {}
    for name, qids in splits.items():
        out[name] = sum(
            1 for q in qids
            if family_key(records[q]) in shared
            or ("chain", tuple(sorted(records[q]["gold_facts"]))) in shared
        )
    return out


def opaque_id(question_id: str, seed: int = SPLIT_SEED) -> str:
    """The published id of a question."""
    digest = hashlib.sha256(f"{seed}:{question_id}".encode()).hexdigest()
    return ID_PREFIX + digest[:10]


def describe(qids: Iterable[str], records: Mapping[str, Record]) -> dict[str, Any]:
    """Per-split summary for the manifest: counts and distributions."""
    rs = [records[q] for q in qids]
    s3 = sorted(r["set_size"] for r in rs if r["stratum"] == "S3")
    s4_pairs = {(r["slots"]["X"], r["slots"]["V"]) for r in rs if r["stratum"] == "S4"}
    return {
        "questions": len(rs),
        "per_template": dict(sorted(Counter(r["template"] for r in rs).items())),
        "group": dict(sorted(Counter(r["group"] for r in rs).items())),
        "s1_material": dict(Counter("material" if r["material"] else "benign"
                                    for r in rs if r["stratum"] == "S1")),
        "s2_versions": dict(sorted(Counter(r["slots"]["V"] for r in rs
                                           if r["stratum"] == "S2").items())),
        "s3_set_size": ({"min": s3[0], "median": statistics.median(s3), "max": s3[-1]}
                        if s3 else {}),
        "s4_withheld_pairs": len(s4_pairs),
    }


def write_split(path: Path, ids: Sequence[str], frozen: bool) -> str:
    """Write one split file (opaque ids, draw order); refuse to change a frozen one.

    Returns:
        The file's SHA-256.

    Raises:
        ValueError: A frozen split exists with different ids.
    """
    text = "".join(f"{i}\n" for i in ids)
    if frozen and path.exists() and path.read_text(encoding="utf-8") != text:
        raise ValueError(f"{path.name} is frozen and would change")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def read_openings(splits_dir: Path) -> dict[str, dict[str, Any]]:
    """Opening counts and logs per evaluation split (all 0 if the file is new)."""
    path = splits_dir / OPENINGS_FILE
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {name: {"count": 0, "log": []} for name in EVALUATION_SPLITS}


def write_openings(splits_dir: Path, openings: Mapping[str, Any]) -> None:
    """Write the opening counts (versioned with the split files)."""
    (splits_dir / OPENINGS_FILE).write_text(
        json.dumps(openings, indent=1) + "\n", encoding="utf-8")


def open_split(
    name: str, purpose: str, *, splits_dir: Path = DEFAULT_SPLITS_DIR,
    world_dir: Path = DEFAULT_WORLD_DIR, reopen: bool = False, when: str = "",
) -> list[str]:
    """The question ids of a split, in draw order; opening an evaluation split
    is recorded.

    Args:
        name: Split name.
        purpose: What the opening is for (logged; required for evaluation).
        reopen: Allow a second opening of an evaluation split (counted).
        when: Date of the opening, for the log.

    Raises:
        ValueError: An evaluation split opened before, without ``reopen``, or an
            opening with no purpose.
    """
    local = json.loads((world_dir / "examiner" / "splits.json").read_text(
        encoding="utf-8"))
    ids = list(local["splits"][name])
    if name not in EVALUATION_SPLITS:
        return ids
    if not purpose.strip():
        raise ValueError(f"opening {name} needs a purpose")
    openings = read_openings(splits_dir)
    entry = openings.setdefault(name, {"count": 0, "log": []})
    if entry["count"] and not reopen:
        raise ValueError(f"{name} was opened {entry['count']} time(s) already")
    entry["count"] += 1
    entry["log"].append({"when": when, "purpose": purpose})
    write_openings(splits_dir, openings)
    return ids


def load_kept(world_dir: Path) -> list[dict[str, Any]]:
    """Generated questions minus those the shortcut scan discarded.

    Raises:
        ValueError: The scan was not run, or left questions unresolved.
    """
    out = world_dir / "examiner"
    scan_path = out / "shortcuts.json"
    if not scan_path.exists():
        raise ValueError("run the shortcut scan first")
    status = json.loads(scan_path.read_text(encoding="utf-8"))["status"]
    unresolved = [q for q, s in status.items() if s == "unresolved"]
    if unresolved:
        raise ValueError(f"{len(unresolved)} questions unresolved by the shortcut scan")
    with (out / "questions.jsonl").open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    return [r for r in records if status.get(r["id"]) != "discarded"]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Draw the question splits.")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--splits-dir", type=Path, default=DEFAULT_SPLITS_DIR)
    parser.add_argument("--eval-l1-extra", type=int, default=0,
                        help="extra eval-L1 questions per stratum (gate 8)")
    parser.add_argument("--refreeze", action="store_true",
                        help="rewrite frozen splits; only before any use, with a "
                        "journal entry saying why")
    args = parser.parse_args(argv)

    records = load_kept(args.world_dir)
    by_id = {r["id"]: r for r in records}
    splits, report = build_splits(records, args.eval_l1_extra)
    clash = separation(splits, by_id)
    if any(clash.values()):
        print("separation broken:", clash)
        return 1
    opaque = {q: opaque_id(q) for q in by_id}
    if len(set(opaque.values())) != len(opaque):
        print("opaque id collision")
        return 1

    manifest: dict[str, Any] = {
        "seed": report["seed"],
        "questions_kept": len(records),
        "families": report["families"],
        "material_pools": report["material_pools"],
        "pools": report["pools"],
        "splits": {},
    }
    openings = read_openings(args.splits_dir)
    opened = {n for n, e in openings.items() if e["count"]}
    frozen = {s.name: s.frozen or s.name in opened for s in SPECS}
    if opened and (args.refreeze or args.eval_l1_extra):
        print(f"opened splits cannot be redrawn: {', '.join(sorted(opened))}")
        return 1
    print(f"{'split':<15} {'n':>4}  " + "  ".join(f"{s:>3}" for s in STRATA)
          + "   clash")
    for name, qids in splits.items():
        refreezable = args.refreeze and name not in opened
        digest = write_split(args.splits_dir / f"{name}.txt",
                             [opaque[q] for q in qids],
                             frozen[name] and not refreezable)
        info = describe(qids, by_id)
        manifest["splits"][name] = {"frozen": frozen[name], "sha256": digest,
                                    "allocation": report["allocation"][name], **info}
        per_stratum = Counter(by_id[q]["stratum"] for q in qids)
        print(f"{name:<15} {len(qids):>4}  "
              + "  ".join(f"{per_stratum[s]:>3}" for s in STRATA)
              + f"   {clash[name]} of {len(qids)}")
    if args.eval_l1_extra:
        manifest["eval_l1_extra_per_stratum"] = args.eval_l1_extra
    write_openings(args.splits_dir, openings)
    (args.splits_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    local = args.world_dir / "examiner" / "splits.json"
    local.write_text(json.dumps({
        "opaque": {opaque[q]: q for qids in splits.values() for q in qids},
        "splits": splits,
    }, indent=1) + "\n", encoding="utf-8")
    print("\nper pool (families / questions demanded):")
    for p, info in report["pools"].items():
        mark = "  capped" if info["capped"] else ""
        print(f"  {p:<6} {info['families']:>6,} / {info['demand']:>4}{mark}")
    print(f"\nsplit files → {args.splits_dir}; mapping (local) → {local}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
