"""Benchmark export: opaque ids, published answers and the leak checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_pokedex.examiner.benchmark import (
    gold_order,
    opaque_fact,
    opaque_unit,
    published_answer,
    published_record,
    raw_ids,
    real_names_in,
    split_of,
)
from agentic_pokedex.examiner.shortcuts import Lexicon
from agentic_pokedex.world.pokeapi import iter_learnsets, read_world
from agentic_pokedex.world.render import Names, build_world

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"


@pytest.fixture(scope="module")
def names() -> Names:
    tables = read_world(RAW)
    world = build_world(tables, list(iter_learnsets(RAW, tables)),
                        ("alpha-beta", "gamma"))
    return Names.real(world)


def rec(qid: str, stratum: str, answer, **extra) -> dict:
    return {"id": qid, "template": qid.split(":")[0], "stratum": stratum,
            "group": "A", "answer": answer, "material": None, "set_size": None,
            "twin_text": "Q?", "gold_facts": [], "cover": {}, "near_certain": [],
            "withheld_units": [], **extra}


def test_opaque_ids() -> None:
    f, u = opaque_fact("learn:6:53:x-y:level-up:1"), opaque_unit("species/6/profile")
    assert f.startswith("f-") and len(f) == 14 and f == opaque_fact(
        "learn:6:53:x-y:level-up:1")
    assert u.startswith("u-") and len(u) == 14
    assert opaque_unit("species/6/profile", seed=1) != u


def test_published_answers(names: Names) -> None:
    assert published_answer(rec("S0-A1:x=1", "S0", 3), names) == {
        "expected": "answer", "answer": "Undertow", "aliases": []}
    assert published_answer(rec("S3-A1:m=1", "S3", [3, 2]), names)["answer"] == [
        "Sprout", "Sproutree"]
    factor = published_answer(rec("S0-B1:a=1,b=2", "S0", 0.5), names)
    assert factor["answer"] == 0.5 and factor["aliases"] == ["×0.5", "x0.5", "0.5"]
    s4 = published_answer(rec("S4-B1:p=1,l=1,v=alpha-beta", "S4", 1), names)
    assert s4 == {"expected": "abstain", "answer": None, "aliases": [],
                  "withheld_value": "Vine Lash"}


def test_gold_order() -> None:
    assert gold_order(["f-b", "f-a"], "S1") == ["f-b", "f-a"]  # chain order
    assert gold_order(["f-b", "f-a"], "S3") == ["f-a", "f-b"]


def test_published_record_carries_no_raw_id(names: Names) -> None:
    record = rec("S2-A1:p=4,m=2,v=gamma", "S2", 7,
                 gold_facts=["learn:4:2:gamma:level-up:7"],
                 cover={"learn:4:2:gamma:level-up:7": [
                     "species/4/learnset/level-up/gamma/0",
                     "move/2/learned-by/gamma/0"]},
                 near_certain=["species/4/learnset/level-up/alpha-beta/0"])
    row = published_record(record, "dev", names)
    assert raw_ids([row]) == []
    assert row["id"].startswith("q-") and row["split"] == "dev"
    assert list(row["cover"]) == [opaque_fact("learn:4:2:gamma:level-up:7")]
    assert len(row["cover"][row["gold_facts"][0]]) == 2


def test_raw_ids_are_caught() -> None:
    assert raw_ids([{"a": "species/6/profile", "b": ["evoend:3"]}]) == [
        "species/6", "evoend:3"]


def test_real_names_are_caught(names: Names) -> None:
    real = Lexicon(names)
    rows = [{"question": "What is Sprig's hidden ability?", "answer": "Undertow"},
            {"question": "What is Ruxpil's hidden ability?", "answer": "Hairrur"}]
    assert real_names_in(rows, real) == {"Sprig": 1, "Undertow": 1}


def test_split_of() -> None:
    local = {"splits": {"dev": ["a"], "eval-L1": ["b"]}}
    assert split_of(local) == {"a": "dev", "b": "eval-L1"}
