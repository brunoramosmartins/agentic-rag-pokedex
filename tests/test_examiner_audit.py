"""G3 audit: sample, sheet and score."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_pokedex.examiner.audit import (
    THRESHOLD,
    allocation,
    audit_pool,
    chain_units,
    normalize_verdict,
    read_verdicts,
    render_block,
    review,
    sample,
    score,
    set_verdict,
)
from agentic_pokedex.examiner.splits import families
from agentic_pokedex.examiner.templates import TEMPLATES
from agentic_pokedex.world.pokeapi import iter_learnsets, read_world
from agentic_pokedex.world.render import Names, build_world

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"


def pool(per_template: int = 20) -> list[dict]:
    out = []
    for t in TEMPLATES:
        for i in range(per_template):
            material = i % 2 == 0 if t.id in ("S1-A1", "S1-A2", "S1-A3") else None
            out.append({"id": f"{t.id}:k={i}", "template": t.id, "stratum": t.stratum,
                        "material": material, "gold_facts": [f"{t.id}:{i}"],
                        "slots": {"X": i, "M": i, "A": i, "B": 1, "V": "x-y"}})
    return out


# --- Sample ---------------------------------------------------------------------


def test_allocation_is_twelve_per_stratum() -> None:
    a = allocation()
    assert sum(a.values()) == 60
    s0 = ("S0-A1", "S0-A2", "S0-A3", "S0-A4", "S0-B1")
    assert [a[t] for t in s0] == [3, 3, 2, 2, 2]
    assert [a[t] for t in ("S1-A1", "S1-A2", "S1-A3", "S1-B1")] == [3, 3, 3, 3]
    assert [a[t] for t in ("S2-A1", "S2-A2", "S2-B1")] == [4, 4, 4]
    assert [a[t] for t in ("S3-A1", "S3-B1", "S4-A1", "S4-B1")] == [6, 6, 6, 6]


def test_pool_leaves_out_evaluation_seen_and_benign() -> None:
    records = pool(4)
    kept = {r["id"] for r in audit_pool(records, {"S0-A1:k=0"}, {"S0-A1:k=1"})}
    assert "S0-A1:k=0" not in kept and "S0-A1:k=1" not in kept
    assert "S0-A1:k=2" in kept
    assert "S1-A1:k=0" in kept and "S1-A1:k=1" not in kept  # benign out
    assert "S1-B1:k=1" in kept


def test_sample_is_seeded_and_fresh_per_round() -> None:
    records = pool()
    fam = families(records)
    first = sample(audit_pool(records, set(), set()), fam, 1)
    assert len(first) == 60
    assert [r["id"] for r in first] == [r["id"] for r in sample(
        audit_pool(records, set(), set()), fam, 1)]
    seen = {r["id"] for r in first}
    second = sample(audit_pool(records, set(), seen), fam, 2)
    assert not seen & {r["id"] for r in second}
    assert all(r["material"] for r in first if r["template"] in ("S1-A1", "S1-A2"))


def test_sample_refuses_a_short_template() -> None:
    records = pool(4)
    # S1-A1 has 2 material questions among 4, and the sample needs 3.
    with pytest.raises(ValueError, match="S1-A1: 2 of 3"):
        sample(audit_pool(records, set(), set()), families(records), 1)


# --- Sheet ----------------------------------------------------------------------


def test_chain_units_cover_greedily_and_read_in_chain_order() -> None:
    record = {"stratum": "S1", "gold_facts": ["f1", "f2", "f3"],
              "cover": {"f1": ["species/1/profile", "u/2"], "f2": ["u/2"],
                        "f3": ["species/3/profile"]}}
    assert chain_units(record) == [("u/2", ["f1", "f2"]),
                                   ("species/3/profile", ["f3"])]
    tie = {"stratum": "S0", "gold_facts": ["f"],
           "cover": {"f": ["ability/1/holders/0", "species/1/profile"]}}
    assert chain_units(tie) == [("species/1/profile", ["f"])]
    s4 = {"stratum": "S4", "gold_facts": ["g"], "cover": {"g": []},
          "withheld_units": ["species/1/learnset/level-up/x-y/0"]}
    assert chain_units(s4) == [("species/1/learnset/level-up/x-y/0", ["g"])]


def test_render_block(fixture_world_dir: Path) -> None:
    tables = read_world(RAW)
    world = build_world(tables, list(iter_learnsets(RAW, tables)),
                        ("alpha-beta", "gamma"))
    pages = {}
    with (fixture_world_dir / "pages" / "real.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            pages[row["id"]] = row["text"]
    record = {
        "id": "S1-A1:x=1", "template": "S1-A1", "stratum": "S1", "group": "A",
        "slots": {"X": 1}, "answer": 3,
        "gold_facts": ["evo:2:1", "evo:3:2", "evoend:3", "pability:3:3:hidden"],
        "anchor_answer": [3], "material": False,
        "cover": {"evo:2:1": ["species/1/profile"], "evo:3:2": ["species/2/profile"],
                  "evoend:3": ["species/3/profile"],
                  "pability:3:3:hidden": ["species/3/profile", "ability/3/holders/0"]},
        "distractor_facts": [], "near_certain": [], "withheld_units": [],
        "set_size": None,
    }
    text = render_block(7, record, Names.real(world), pages)
    assert "Sprig" in text and "**Gold answer:** Undertow" in text
    assert "**Anchor's own value:** Undertow → benign" in text
    units = [line.split("`")[1] for line in text.splitlines()
             if line.startswith("`species/")]
    assert units == ["species/1/profile", "species/2/profile", "species/3/profile"]
    assert read_verdicts(text) == [("S1-A1", text.split(" — ")[1].split()[0],
                                    "pending")]


# --- Score ----------------------------------------------------------------------


def test_read_verdicts() -> None:
    text = "\n".join([
        "## 1. S0-A1 — q-aaaaaaaaaa", "**Verdict:** ok", "",
        "## 2. S2-A1 — q-bbbbbbbbbb", "**Verdict:** Wrong — level is 30",
        "## 3. S3-A1 — q-cccccccccc", "**Verdict:** ",
        "## 4. S4-A1 — q-dddddddddd", "**Verdict:** maybe",
    ])
    assert read_verdicts(text) == [
        ("S0-A1", "q-aaaaaaaaaa", "ok"), ("S2-A1", "q-bbbbbbbbbb", "wrong"),
        ("S3-A1", "q-cccccccccc", "pending"), ("S4-A1", "q-dddddddddd", "unreadable"),
    ]


def verdicts(ok: int, wrong: int, pending: int = 0) -> list[tuple[str, str, str]]:
    states = ["ok"] * ok + ["wrong"] * wrong + ["pending"] * pending
    return [("S2-A1", f"q-{i:010x}", s) for i, s in enumerate(states)]


def test_score_threshold() -> None:
    assert score(verdicts(THRESHOLD, 60 - THRESHOLD))["decision"] == "pass"
    failed = score(verdicts(THRESHOLD - 1, 61 - THRESHOLD))
    assert failed["decision"] == "fail" and failed["wrong_by_template"] == {"S2-A1": 3}
    assert score(verdicts(59, 0, 1))["decision"] == "pending"


# --- Marking --------------------------------------------------------------------

SHEET = "\n".join([
    "# G3 audit — round 1", "", "---", "",
    "## 1. S0-A1 — q-aaaaaaaaaa", "", "**Question:** a?", "", "**Verdict:** ", "",
    "---", "",
    "## 2. S2-A1 — q-bbbbbbbbbb", "", "**Question:** b?", "", "**Verdict:** ok", "",
    "---", "",
    "## 3. S3-A1 — q-cccccccccc", "", "**Question:** c?", "", "**Verdict:** ", "",
])


def test_normalize_verdict() -> None:
    assert normalize_verdict(" OK ") == normalize_verdict("o") == "ok"
    assert normalize_verdict("w level is 30") == "wrong — level is 30"
    assert normalize_verdict("wrong: level is 30") == "wrong — level is 30"
    assert normalize_verdict("Wrong — misses Azurill") == "wrong — misses Azurill"
    assert normalize_verdict("w") is None
    assert normalize_verdict("maybe") is None


def test_set_verdict_touches_one_item() -> None:
    text = set_verdict(SHEET, 3, "wrong — misses one")
    assert [v for *_, v in read_verdicts(text)] == ["pending", "ok", "wrong"]
    assert text.replace("wrong — misses one", "") == SHEET
    with pytest.raises(KeyError):
        set_verdict(SHEET, 9, "ok")


def test_review_saves_each_answer_and_skips(tmp_path: Path) -> None:
    sheet = tmp_path / "g3-round-1.md"
    sheet.write_text(SHEET, encoding="utf-8")
    answers = iter(["huh", "ok", "s"])  # item 1: rejected then ok; item 3 skipped
    left = review(sheet, read=lambda _: next(answers))
    assert left == 1
    assert [v for *_, v in read_verdicts(sheet.read_text(encoding="utf-8"))] == [
        "ok", "ok", "pending"]
    answers = iter(["q"])
    assert review(sheet, read=lambda _: next(answers)) == 1
