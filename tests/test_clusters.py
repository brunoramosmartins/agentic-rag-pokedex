"""Stratified cluster bootstrap, and the pilot's proxy SD of D."""

from __future__ import annotations

import random

import pytest

from agentic_pokedex.evaluation import pilot
from agentic_pokedex.evaluation.clusters import (
    Item,
    bootstrap_interval,
    grouped,
    resample,
    sd,
)
from agentic_pokedex.evaluation.grader import GoldAnswer


def test_sd_is_the_sample_standard_deviation() -> None:
    assert sd([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.138, abs=1e-3)
    assert sd([1.0]) == 0.0 and sd([]) == 0.0


def items() -> list[Item]:
    out = []
    for stratum in ("S1", "S2"):
        for c in range(5):
            out += [Item(stratum, f"c{c}", float(c)), Item(stratum, f"c{c}", c + 0.5)]
    return out


def test_resample_keeps_clusters_whole_and_strata_apart() -> None:
    groups = grouped(items())
    draw = resample(groups, random.Random(1))
    assert len(draw) == 20  # 2 strata × 5 clusters × 2 values
    # Every value comes with its cluster partner (c, c + 0.5).
    whole = sorted(draw)
    assert all(whole.count(v) == whole.count(v + 0.5) for v in whole if v % 1 == 0)


def test_interval_is_seeded_and_brackets_a_constant() -> None:
    const = [Item("S1", f"c{i}", 3.0) for i in range(6)]
    assert bootstrap_interval(const, sd, seed=3) == (0.0, 0.0, 0.0)
    a = bootstrap_interval(items(), sd, replicates=300, seed=7)
    b = bootstrap_interval(items(), sd, replicates=300, seed=7)
    assert a == b and a[1] <= a[2]


def test_proxy_sd_reads_a1_and_a3_on_the_agent_questions() -> None:
    gold = GoldAnswer("level", "answer", 3)
    right = '{"answer": "3", "abstain": false}'
    wrong = '{"answer": "9", "abstain": false}'
    abstain = '{"answer": null, "abstain": true}'
    state = {"single": {}, "agent": {}}
    records, golds = {}, {}
    finals = [(right, wrong), (abstain, right), (right, right), (wrong, abstain)]
    for i, (a1, a3) in enumerate(finals):
        q = f"S2-A1:x={i}"
        records[q] = {"id": q, "stratum": "S2", "template": "S2-A1",
                      "slots": {"X": i}, "gold_facts": []}
        golds[q] = gold
        state["single"][f"A1|q-{i}"] = {"arm": "A1", "local": q, "status": "done",
                                        "completion": a1}
        state["agent"][f"q-{i}"] = {"local": q, "state": {"final": a3, "failed": False}}
    out = pilot.proxy_sd(state, golds, records)
    # D = C(A1) − C(A3): 0 − 4, 1 − 0, 0 − 0, 4 − 1
    assert out["questions"] == 4 and out["discordant"] == 3
    assert out["sd"] == pytest.approx(round(sd([-4.0, 1.0, 0.0, 3.0]), 3))
    assert out["sd_80"][0] <= out["sd_80"][1]
    assert "mean" not in str(out)
