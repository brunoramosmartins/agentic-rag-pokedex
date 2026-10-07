"""Splits: families, sizes, the draw, separation, ids and freezing."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from agentic_pokedex.examiner import splits
from agentic_pokedex.examiner.splits import (
    SPECS,
    Draw,
    SplitSpec,
    allocation,
    anchor_key,
    apportion,
    build_splits,
    eligible,
    families,
    family_key,
    load_kept,
    opaque_id,
    open_split,
    read_openings,
    separation,
    template_pools,
    write_split,
)
from agentic_pokedex.examiner.templates import BY_ID, TEMPLATES

MATERIAL = {"S1-A1": 70, "S1-A2": 104, "S1-A3": 57}


def rec(qid: str, slots: dict, facts: list[str], material: bool | None = None,
        set_size: int | None = None) -> dict:
    template = qid.split(":", 1)[0]
    t = BY_ID[template]
    return {"id": qid, "template": template, "stratum": t.stratum, "group": t.group,
            "slots": slots, "gold_facts": facts, "material": material,
            "set_size": set_size}


def world(per_template: int = 12) -> list[dict]:
    """Synthetic questions for every template: one anchor per question, except
    that S2-A1/S2-A2 and S4-A1/S4-B1 share a learn fact per species."""
    out = []
    for i in range(per_template):
        x, v = 100 + i, "x-y"
        out += [
            rec(f"S0-A1:x={x}", {"X": x}, [f"pability:{x}:1:hidden"]),
            rec(f"S0-A2:m={i}", {"M": i}, [f"mpower:{i}:40"]),
            rec(f"S0-A3:m={i}", {"M": i}, [f"mcat:{i}:physical"]),
            rec(f"S0-A4:m={i}", {"M": i}, [f"mtype:{i}:1"]),
            rec(f"S0-B1:a={i},b=1", {"A": i, "B": 1}, [f"eff:{i}:1:100"]),
            rec(f"S1-A1:x={x}", {"X": x}, [f"evo:{x + 1}:{x}", f"a1:{x}"], i % 2 == 0),
            rec(f"S1-A2:x={x}", {"X": x}, [f"evo:{x + 1}:{x}", f"a2:{x}"], i % 2 == 0),
            rec(f"S1-A3:x={x}", {"X": x}, [f"evo:{x + 1}:{x}", f"a3:{x}"], i % 2 == 0),
            rec(f"S1-B1:m=1,x={x}", {"M": 1, "X": x}, [f"b1:{x}"], True),
            rec(f"S2-A1:p={x},m=1,v={v}", {"X": x, "M": 1, "V": v},
                [f"learn:{x}:1:{v}:level-up:5"]),
            rec(f"S2-A2:p={x},l=5,v={v}", {"X": x, "L": 5, "V": v},
                [f"learn:{x}:1:{v}:level-up:5"]),
            rec(f"S2-B1:p={x},v={v}", {"X": x, "V": v}, [f"last:{x}"]),
            rec(f"S3-A1:m={i},v={v},t=1", {"M": i, "V": v, "T": 1}, [f"s3a:{i}"],
                set_size=3 + i),
            rec(f"S3-B1:m={i},v={v},t=1,l=9", {"M": i, "V": v, "T": 1, "L": 9},
                [f"s3b:{i}"], set_size=3),
            rec(f"S4-A1:p={x},m=1,v=gamma", {"X": x, "M": 1, "V": "gamma"},
                [f"learn:{x}:1:gamma:level-up:7"]),
            rec(f"S4-B1:p={x},l=7,v=gamma", {"X": x, "L": 7, "V": "gamma"},
                [f"learn:{x}:1:gamma:level-up:7"]),
        ]
    return out


TINY = (
    SplitSpec("dev", {"S0": 4, "S1": 3, "S2": 2, "S3": 1, "S4": 2}, group="A",
              frozen=True),
    SplitSpec("eval-L1", {"S0": 5, "S1": 4, "S2": 3, "S3": 2, "S4": 2}),
    SplitSpec("eval-L1-benign", {"S1": 3}, group="A", benign=True),
    SplitSpec("val-B", {"S0": 1, "S1": 1, "S2": 1, "S3": 1, "S4": 1}, group="B"),
)


# --- Sizes ----------------------------------------------------------------------


def test_apportion() -> None:
    assert apportion(30, [1, 1, 1, 1]) == [8, 8, 7, 7]
    assert apportion(80, [1, 1, 1]) == [27, 27, 26]
    assert apportion(60, [70, 104, 57]) == [18, 27, 15]
    assert sum(apportion(17, [3, 5, 9])) == 17


def test_allocation_of_the_registered_splits() -> None:
    by_name = {s.name: allocation(s, MATERIAL) for s in SPECS}
    l1 = by_name["eval-L1"]
    assert [l1[t] for t in ("S1-A1", "S1-A2", "S1-A3", "S1-B1")] == [18, 27, 15, 20]
    assert [l1[t] for t in ("S2-A1", "S2-A2", "S2-B1")] == [27, 27, 26]
    assert all(l1[t] == 16 for t in ("S0-A1", "S0-A2", "S0-A3", "S0-A4", "S0-B1"))
    dev = by_name["dev"]
    assert [dev[t] for t in ("S0-A1", "S0-A2", "S0-A3", "S0-A4")] == [8, 8, 7, 7]
    assert [dev[t] for t in ("S1-A1", "S1-A2", "S1-A3")] == [9, 14, 7]
    assert all(BY_ID[t].group == "A" for t in dev)
    assert by_name["eval-L1-benign"] == {"S1-A1": 14, "S1-A2": 13, "S1-A3": 13}
    assert set(by_name["val-B"]) == {t.id for t in TEMPLATES if t.group == "B"}
    for spec in SPECS:
        counts = Counter()
        for t, n in by_name[spec.name].items():
            counts[BY_ID[t].stratum] += n
        assert dict(counts) == dict(spec.per_stratum), spec.name


def test_material_s1_fits_every_split() -> None:
    need = Counter()
    for spec in SPECS:
        if not spec.benign:
            for t, n in allocation(spec, MATERIAL).items():
                if t in MATERIAL:
                    need[t] += n
    assert all(need[t] <= MATERIAL[t] for t in MATERIAL), need


def test_eligibility() -> None:
    material = rec("S1-A1:x=1", {"X": 1}, [], True)
    benign = rec("S1-A1:x=2", {"X": 2}, [], False)
    main, slice_ = SPECS[0], next(s for s in SPECS if s.benign)
    assert eligible(material, main) and not eligible(benign, main)
    assert eligible(benign, slice_) and not eligible(material, slice_)
    assert eligible(rec("S2-A1:p=1,m=1,v=x", {"X": 1}, []), main)


# --- Families -------------------------------------------------------------------


def test_anchor_keys() -> None:
    records = {r["template"]: r for r in world(1)}
    assert anchor_key(records["S0-A2"]) == "move:0"
    assert anchor_key(records["S3-B1"]) == "move:0"
    assert anchor_key(records["S0-B1"]) == "types:0,1"
    assert anchor_key(records["S1-B1"]) == "species:100"
    assert anchor_key(records["S4-A1"]) == "pair:100:gamma"
    assert family_key(records["S4-A1"]) == family_key(records["S4-B1"])
    assert family_key(records["S2-A1"]) != family_key(records["S2-A2"])


def test_families_join_shared_chains_and_anchors() -> None:
    records = world(2)
    records.append(rec("S2-A1:p=100,m=2,v=x-y", {"X": 100, "M": 2, "V": "x-y"},
                       ["learn:100:2:x-y:level-up:9"]))
    fam = families(records)
    # Same learn fact: S2-A1 and S2-A2 of species 100 are one family, and the
    # second S2-A1 question on species 100 joins it through the anchor.
    assert (fam["S2-A1:p=100,m=1,v=x-y"] == fam["S2-A2:p=100,l=5,v=x-y"]
            == fam["S2-A1:p=100,m=2,v=x-y"])
    assert fam["S4-A1:p=100,m=1,v=gamma"] == fam["S4-B1:p=100,l=7,v=gamma"]
    assert fam["S2-A1:p=100,m=1,v=x-y"] != fam["S2-A1:p=101,m=1,v=x-y"]
    assert fam["S1-A1:x=100"] != fam["S1-A2:x=100"]  # different chains
    pools = template_pools(records, fam)
    assert pools["S2-A2"] == pools["S2-A1"] and pools["S4-B1"] == pools["S4-A1"]
    assert pools["S2-B1"] == "S2-B1"


# --- Draw -----------------------------------------------------------------------


def test_draw_takes_one_question_per_family_per_pass() -> None:
    records = world(4)
    records += [rec(f"S4-A1:p=100,m={m},v=gamma", {"X": 100, "M": m, "V": "gamma"},
                    [f"learn:100:{m}:gamma:level-up:{m}"]) for m in (2, 3)]
    by_id = {r["id"]: r for r in records}
    fam = families(records)
    draw = Draw(by_id, fam, template_pools(records, fam))
    got = draw.draw(SPECS[0], "S4-A1", 4)
    assert len({fam[q] for q in got}) == 4  # four species before any repeat
    more = draw.draw(SPECS[0], "S4-A1", 2)
    assert {fam[q] for q in more} == {fam["S4-A1:p=100,m=1,v=gamma"]}
    with pytest.raises(ValueError, match="ran out"):
        draw.draw(SPECS[0], "S4-A1", 1)


def test_caps_hold_families_for_later_splits() -> None:
    records = world(4)
    by_id = {r["id"]: r for r in records}
    fam = families(records)
    draw = Draw(by_id, fam, template_pools(records, fam))
    first, second = SplitSpec("first", {}), SplitSpec("second", {})
    draw.caps[("first", "S4-A1")] = 2
    draw.caps[("second", "S4-A1")] = 2
    assert len(draw.draw(first, "S4-A1", 2)) == 2
    # "first" is at its cap: a third question must come from its own families.
    extra = draw.draw(first, "S4-B1", 2)
    assert {fam[q] for q in extra} <= {draw.family[q] for q in draw.taken["first"][:2]}
    assert len(draw.draw(second, "S4-B1", 2)) == 2


def test_build_splits_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(splits, "SPECS", TINY)
    records = world()
    by_id = {r["id"]: r for r in records}
    out, report = build_splits(records)
    assert {n: len(q) for n, q in out.items()} == {
        "dev": 12, "eval-L1": 16, "eval-L1-benign": 3, "val-B": 5}
    assert all(by_id[q]["group"] == "A" for q in out["dev"])
    assert all(by_id[q]["group"] == "B" for q in out["val-B"])
    assert all(by_id[q]["material"] is False for q in out["eval-L1-benign"])
    assert all(by_id[q]["material"] for n in ("dev", "eval-L1") for q in out[n]
               if by_id[q]["stratum"] == "S1")
    assert set(separation(out, by_id).values()) == {0}
    again, _ = build_splits(records)
    assert again == out  # deterministic


def test_extension_leaves_everything_else_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(splits, "SPECS", TINY)
    records = world()
    base, _ = build_splits(records)
    grown, report = build_splits(records, eval_l1_extra=1)
    assert grown["eval-L1"][: len(base["eval-L1"])] == base["eval-L1"]
    assert len(grown["eval-L1"]) == len(base["eval-L1"]) + 5
    for name in ("dev", "eval-L1-benign", "val-B"):
        assert grown[name] == base[name]
    assert set(separation(grown, {r["id"]: r for r in records}).values()) == {0}


def test_separation_counts_clashes() -> None:
    records = {r["id"]: r for r in world(2)}
    clash = separation({"dev": ["S2-A1:p=100,m=1,v=x-y"],
                        "eval-L1": ["S2-A2:p=100,l=5,v=x-y", "S0-A2:m=0"]}, records)
    assert clash == {"dev": 1, "eval-L1": 1}


# --- Ids and files --------------------------------------------------------------


def test_opaque_ids() -> None:
    a = opaque_id("S2-A1:p=4,m=2,v=gamma")
    assert a == opaque_id("S2-A1:p=4,m=2,v=gamma") and a.startswith("q-")
    assert len(a) == 12 and all(c in "0123456789abcdef" for c in a[2:])
    assert a != opaque_id("S2-A1:p=4,m=2,v=gamma", seed=1)


def test_frozen_split_refuses_to_change(tmp_path: Path) -> None:
    path = tmp_path / "dev.txt"
    write_split(path, ["q-1", "q-2"], frozen=True)
    write_split(path, ["q-1", "q-2"], frozen=True)  # same ids: fine
    with pytest.raises(ValueError, match="frozen"):
        write_split(path, ["q-1", "q-3"], frozen=True)
    write_split(tmp_path / "eval-L1.txt", ["q-1"], frozen=False)
    write_split(tmp_path / "eval-L1.txt", ["q-2"], frozen=False)


def test_load_kept_requires_a_resolved_scan(tmp_path: Path) -> None:
    out = tmp_path / "examiner"
    out.mkdir()
    rows = [rec("S0-A2:m=1", {"M": 1}, []), rec("S0-A2:m=2", {"M": 2}, [])]
    (out / "questions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(ValueError, match="shortcut scan first"):
        load_kept(tmp_path)
    scan = out / "shortcuts.json"
    scan.write_text(json.dumps({"status": {"S0-A2:m=1": "unresolved"}}))
    with pytest.raises(ValueError, match="unresolved"):
        load_kept(tmp_path)
    scan.write_text(json.dumps({"status": {"S0-A2:m=1": "discarded"}}))
    assert [r["id"] for r in load_kept(tmp_path)] == ["S0-A2:m=2"]


# --- Openings -------------------------------------------------------------------


def test_openings_are_counted(tmp_path: Path) -> None:
    world_dir, splits_dir = tmp_path / "world", tmp_path / "splits"
    (world_dir / "examiner").mkdir(parents=True)
    splits_dir.mkdir()
    (world_dir / "examiner" / "splits.json").write_text(json.dumps(
        {"splits": {"dev": ["S0-A1:x=1"], "eval-L1": ["S0-A1:x=2"]}}))
    assert read_openings(splits_dir)["eval-L1"] == {"count": 0, "log": []}
    kw = {"splits_dir": splits_dir, "world_dir": world_dir}
    assert open_split("dev", "", **kw) == ["S0-A1:x=1"]  # free, not logged
    with pytest.raises(ValueError, match="purpose"):
        open_split("eval-L1", " ", **kw)
    assert open_split("eval-L1", "E-001 run", when="2026-10-01", **kw) == [
        "S0-A1:x=2"]
    with pytest.raises(ValueError, match="opened 1 time"):
        open_split("eval-L1", "again", **kw)
    open_split("eval-L1", "rerun after an API outage", reopen=True, **kw)
    entry = read_openings(splits_dir)["eval-L1"]
    assert entry["count"] == 2 and entry["log"][0]["purpose"] == "E-001 run"
    assert "dev" not in read_openings(splits_dir)
