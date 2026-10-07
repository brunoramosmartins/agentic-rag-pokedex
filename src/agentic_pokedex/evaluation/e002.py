"""E-002: how much sufficient evidence a fixed pipeline with typed expansion
delivers, and from which step.

Descriptive and retrieval only: no LLM call, zero API spend. For each
question, the evidence the pipeline of ``arms/typed_expansion.py`` delivers is
labelled by the sufficiency labeler after search, after level 0 and after
each link level (registry, E-002 and its amendments of 2026-10-07). It never
selects strata, thresholds or n for E-001, and never changes the world, the
rendering, the tool contract, the templates or the filters.

Dev runs whole, once per k, each run logged with its freeze manifest; partial
runs (``--limit``) are refused on dev and meant for train.

Usage::

    python -m agentic_pokedex.evaluation.e002                     # k = 5 governs
    python -m agentic_pokedex.evaluation.e002 -k 3                # descriptive
    python -m agentic_pokedex.evaluation.e002 --split train --limit 20   # smoke
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from statistics import median
from typing import Any

from agentic_pokedex.arms.typed_expansion import (
    EVIDENCE_BUDGET,
    LINK_ORDER,
    Delivery,
    World,
    expand,
)
from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.evaluation.intervals import wilson
from agentic_pokedex.labeling.sufficiency import Gold, gold_from, label_state
from agentic_pokedex.tools.contract import MAX_K, TOKEN_CAP, TokenCounter
from agentic_pokedex.world.index import (
    CANDIDATES,
    DEFAULT_WORLD_DIR,
    DENSE_MODEL,
    RRF_K,
)
from agentic_pokedex.world.registry import Registry

Record = Mapping[str, Any]
RUNS_DIR = REPO_ROOT / "runs" / "e002"
STRUCTURAL_ZERO = frozenset({"S4"})
"""Strata never sufficient by construction: counted, never given an interval."""


def cluster_key(record: Record) -> str:
    """E-001's cluster of a question (its keys; components are not merged).

    Withheld pair (S4), move (S3, S0-A2 to A4), final form of the line (S1-A1
    to A3, the anchor where the gold states no final form), type pair (S0-B1),
    anchor species otherwise.
    """
    s, t = record["slots"], record["template"]
    if record["stratum"] == "S4":
        return f"pair:{s.get('X')}:{s.get('V')}"
    if record["stratum"] == "S3" or t in ("S0-A2", "S0-A3", "S0-A4"):
        return f"move:{s.get('M')}"
    if t == "S0-B1":
        return f"types:{s.get('A')}:{s.get('B')}"
    if t in ("S1-A1", "S1-A2", "S1-A3"):
        final = [f.split(":")[1] for f in record["gold_facts"]
                 if f.startswith("evoend:")]
        return f"line:{final[0] if final else s.get('X')}"
    return f"species:{s.get('X')}"


@dataclass(frozen=True)
class Outcome:
    """One question's reading.

    Attributes:
        question: Opaque question id.
        stratum: Stratum.
        template: Template.
        version: Version group asked (S2, S3, S4), else ``None``.
        cluster: E-001 cluster key.
        sufficient: The delivered set is labelled sufficient.
        subtype: Insufficiency subtype, if any.
        by_level: Sufficient after each level: ``"-1"`` search, ``"0"``
            section completion, ``"1"``… link levels.
        near_certain: A near-certain unit (another version's answer) delivered.
        near_certain_level: The first level that delivered one.
        members: S3: set members covered, of the set size.
        hub_units: S3: hub units delivered, of the hub's units.
        tokens: Evidence tokens delivered.
        calls: ``open_page`` calls made.
        deepest: The last level that made a call.
        bound: B stopped the pipeline.
        beyond_t_max: Beyond T_max in the trajectory-level check.
    """

    question: str
    stratum: str
    template: str
    version: str | None
    cluster: str
    sufficient: bool
    subtype: str | None
    by_level: dict[str, bool] = field(default_factory=dict)
    near_certain: bool = False
    near_certain_level: int | None = None
    members: tuple[int, int] | None = None
    hub_units: tuple[int, int] | None = None
    tokens: int = 0
    calls: int = 0
    deepest: int = -1
    bound: bool = False
    beyond_t_max: bool = False


def hub_units(record: Record, registry: Registry) -> list[str]:
    """Indexed units of an S3 question's (move, version) hub."""
    slots = record["slots"]
    return sorted(u.id for u in registry.units.values()
                  if u.section == "Learned by" and not u.withheld
                  and u.key == slots["M"] and u.version_group == slots["V"])


def _levels(delivery: Delivery) -> list[int]:
    return sorted({s.level for s in delivery.steps} | {-1, 0})


def read(
    record: Record, delivery: Delivery, registry: Registry, qid: str,
    beyond: bool = False,
) -> Outcome:
    """Label one delivery, after each level and at the end."""
    gold: Gold = gold_from(record, registry)
    label = label_state(gold, delivery.units)
    by_level, first_near = {}, None
    for level in _levels(delivery):
        state = label_state(gold, delivery.through(level))
        by_level[str(level)] = state.sufficient
        if first_near is None and state.near_certain:
            first_near = level
    hub = None
    if record["stratum"] == "S3":
        units = hub_units(record, registry)
        hub = (len(set(units) & set(delivery.units)), len(units))
    return Outcome(
        question=qid, stratum=record["stratum"], template=record["template"],
        version=record["slots"].get("V"), cluster=cluster_key(record),
        sufficient=label.sufficient, subtype=label.subtype, by_level=by_level,
        near_certain=bool(label.near_certain), near_certain_level=first_near,
        members=label.members, hub_units=hub, tokens=delivery.tokens,
        calls=delivery.calls, deepest=delivery.deepest, bound=delivery.bound,
        beyond_t_max=beyond,
    )


def rate(n: int, m: int, structural: bool = False) -> dict[str, Any]:
    """N-of-M with Wilson 95%, or a structural zero with no interval."""
    out: dict[str, Any] = {"n": n, "of": m}
    if structural:
        out["note"] = "by construction"
    elif m:
        low, high = wilson(n, m)
        out["wilson95"] = [round(low, 3), round(high, 3)]
    return out


def summarize(outcomes: Sequence[Outcome], structural: bool = False) -> dict[str, Any]:
    """Counts of one group, every rate as N-of-M."""
    m = len(outcomes)
    levels = sorted({int(k) for o in outcomes for k in o.by_level})
    out: dict[str, Any] = {
        "questions": m,
        "clusters": len({o.cluster for o in outcomes}),
        "sufficient": rate(sum(o.sufficient for o in outcomes), m, structural),
        # A question past its last level keeps its final label (monotone).
        "sufficient_by_level": {
            str(level): sum(o.by_level.get(str(level), o.sufficient)
                            for o in outcomes)
            for level in levels},
        "near_certain_delivered": sum(o.near_certain for o in outcomes),
        "near_certain_first_level": dict(sorted(Counter(
            o.near_certain_level for o in outcomes
            if o.near_certain_level is not None).items())),
        "b_bound": sum(o.bound for o in outcomes),
        "deepest_level": dict(sorted(Counter(o.deepest for o in outcomes).items())),
        "calls": dict(sorted(Counter(o.calls for o in outcomes).items())),
        "tokens_median": median(o.tokens for o in outcomes) if m else None,
    }
    members = [o.members for o in outcomes if o.members]
    if members:
        out["members_all_covered"] = sum(c == t for c, t in members)
        out["members_covered"] = [f"{c}/{t}" for c, t in members]
        out["hub_units_delivered"] = [f"{c}/{t}" for c, t in
                                      (o.hub_units for o in outcomes if o.hub_units)]
        clusters = {o.cluster for o in outcomes}
        out["clusters_with_a_sufficient_question"] = len(
            {o.cluster for o in outcomes if o.sufficient})
        out["clusters_total"] = len(clusters)
    return out


def two_by_two(outcomes: Iterable[Outcome]) -> dict[str, int]:
    """Sufficient × near-certain delivered (S2)."""
    c = Counter((o.sufficient, o.near_certain) for o in outcomes)
    return {"sufficient, near-certain too": c[(True, True)],
            "sufficient only": c[(True, False)],
            "near-certain only": c[(False, True)],
            "neither": c[(False, False)]}


def report(outcomes: Sequence[Outcome]) -> dict[str, Any]:
    """Per stratum, S1 per template, S2 and S4 per version, S3 by T_max."""
    by: dict[str, list[Outcome]] = defaultdict(list)
    for o in outcomes:
        by[o.stratum].append(o)
        if o.stratum == "S1":
            by[f"S1 {o.template}"].append(o)
        if o.stratum in ("S2", "S4"):
            by[f"{o.stratum} {o.version}"].append(o)
        if o.stratum == "S3":
            by["S3 beyond T_max" if o.beyond_t_max else "S3 within T_max"].append(o)
    out: dict[str, Any] = {
        key: summarize(by[key], key.split()[0] in STRUCTURAL_ZERO)
        for key in sorted(by)}
    if by["S2"]:
        out["S2 2x2"] = two_by_two(by["S2"])
    return out


def run(
    records: Sequence[Record], world: World, registry: Registry,
    counter: TokenCounter, k: int, ids: Mapping[str, str],
    beyond: frozenset[str] = frozenset(),
) -> list[Outcome]:
    """The pipeline and the labels, for each question."""
    out = []
    for r in records:
        delivery = expand(world, r["twin_text"], k=k, counter=counter)
        qid = ids[r["id"]]
        out.append(read(r, delivery, registry, qid, qid in beyond))
    return out


def sha256(path: Path) -> str:
    """SHA-256 of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def manifest(world_dir: Path, split: str, k: int) -> dict[str, Any]:
    """What the run read and which code ran it."""
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()

    files = {
        "pages/twin.jsonl": world_dir / "pages" / "twin.jsonl",
        "registry.json": world_dir / "registry.json",
        "examiner/questions.jsonl": world_dir / "examiner" / "questions.jsonl",
        "examiner/trajectories.json": world_dir / "examiner" / "trajectories.json",
        f"data/splits/{split}.txt": REPO_ROOT / "data" / "splits" / f"{split}.txt",
    }
    return {
        "when": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
        "split": split, "k": k, "budget": EVIDENCE_BUDGET, "token_cap": TOKEN_CAP,
        "max_k": MAX_K, "link_order": list(LINK_ORDER),
        "fusion": {"rrf_k": RRF_K, "candidates": CANDIDATES,
                   "dense_model": DENSE_MODEL, "weights": "equal"},
        "versions": {p: _version(p) for p in ("fastembed", "tiktoken", "numpy")},
        "sha256": {name: sha256(path) for name, path in files.items()
                   if path.exists()},
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="E-002 (no LLM).")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--split", default="dev", choices=("dev", "train"))
    parser.add_argument("-k", type=int, default=5, help="5 governs; 3 descriptive")
    parser.add_argument("--limit", type=int, default=None,
                        help="first N questions (train only)")
    args = parser.parse_args(argv)
    if args.limit is not None and args.split == "dev":
        parser.error("partial runs are refused on dev: dev runs whole, once per k")

    from agentic_pokedex.examiner.splits import opaque_id, open_split
    from agentic_pokedex.tools.contract import default_counter
    from agentic_pokedex.world.index import FastEmbedder, build_index

    world_dir = args.world_dir
    registry = Registry.load(world_dir / "registry.json")
    index = build_index(world_dir, "twin", FastEmbedder(cache_dir=world_dir / "models"))
    world = World.build(index, registry)
    qids = open_split(args.split, "", world_dir=world_dir)[: args.limit]
    wanted = set(qids)
    with (world_dir / "examiner" / "questions.jsonl").open(encoding="utf-8") as fh:
        by_id = {r["id"]: r for r in map(json.loads, fh) if r["id"] in wanted}
    trajectories = json.loads((world_dir / "examiner" / "trajectories.json")
                              .read_text(encoding="utf-8"))
    beyond = frozenset(trajectories["dev_beyond_t_max"])
    info = manifest(world_dir, args.split, args.k)
    print(f"E-002 on {args.split}: {len(qids)} questions, k = {args.k}, "
          f"B = {EVIDENCE_BUDGET}; commit {info['git_commit'][:10]}"
          f"{' (dirty)' if info['git_dirty'] else ''}; no API call")
    outcomes = run([by_id[q] for q in qids], world, registry, default_counter(),
                   args.k, {q: opaque_id(q) for q in qids}, beyond)
    summary = report(outcomes)
    print(f"\n{'group':<22} {'M':>4} {'clust.':>6} {'sufficient':>16} "
          f"{'by level (-1, 0, 1, …)':<26} {'near-c.':>7} {'B':>4}")
    for key, s in summary.items():
        if key == "S2 2x2":
            continue
        r = s["sufficient"]
        ci = (f"{r['wilson95'][0]:.0%}–{r['wilson95'][1]:.0%}" if "wilson95" in r
              else r.get("note", ""))
        levels = ", ".join(str(v) for v in s["sufficient_by_level"].values())
        print(f"{key:<22} {s['questions']:>4} {s['clusters']:>6} "
              f"{r['n']:>3} {ci:>12} {levels:<26} "
              f"{s['near_certain_delivered']:>7} {s['b_bound']:>4}")
    if "S2 2x2" in summary:
        print(f"\nS2, sufficient × near-certain: {summary['S2 2x2']}")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = info["when"].replace(":", "").replace("-", "")
    path = RUNS_DIR / f"{args.split}-k{args.k}-{stamp}.json"
    path.write_text(json.dumps({
        "manifest": info, "questions": len(qids), "summary": summary,
        "outcomes": [asdict(o) for o in outcomes],
    }, indent=1) + "\n", encoding="utf-8")
    with (RUNS_DIR / "log.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"file": path.name, **info}) + "\n")
    print(f"\nwritten to {path}; logged in {RUNS_DIR / 'log.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
