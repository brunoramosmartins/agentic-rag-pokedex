"""The re-estimated v1.0 budget and gate 8's n_max."""

from __future__ import annotations

import pytest

from agentic_pokedex.evaluation import budget as bg
from agentic_pokedex.evaluation.power import PLANNED_POOLED_N


def test_assumed_arms_are_multiples_of_measured_ones() -> None:
    for arm, (base, factor, why) in bg.ASSUMED.items():
        assert base in bg.MEASURED and factor >= 1.0 and why, arm
        for s in bg.STRATA:
            assert bg.per_question(arm, s) == pytest.approx(
                factor * bg.MEASURED[base][s])


def test_a6_runs_on_s3_only() -> None:
    assert bg.per_question("A6", "S3") == bg.A6_PER_QUESTION
    assert all(bg.per_question("A6", s) == 0.0 for s in bg.STRATA if s != "S3")


def test_eval_question_cost_follows_which_arms_run_where() -> None:
    base = {s: sum(bg.per_question(a, s) for a in bg.ARMS_EVAL) for s in bg.STRATA}
    # S0: no placebo; S4: no evidence oracle (no gold units).
    assert bg.eval_question_cost("S0") == pytest.approx(
        base["S0"] + bg.per_question("O1", "S0"))
    assert bg.eval_question_cost("S4") == pytest.approx(
        base["S4"] + bg.per_question("A4p", "S4"))
    assert bg.eval_question_cost("S2") == pytest.approx(
        base["S2"] + bg.per_question("A4p", "S2") + bg.per_question("O1", "S2"))


def test_the_three_cut_arms_are_not_committed_on_eval_l1() -> None:
    assert not {"A6", "A3'"} & set(bg.ARMS_EVAL)
    items = [line.item for line in bg.projected() if line.phase == "6"]
    assert not any("cue" in i or "A3'" in i for i in items if "eval-L1" in i)


def test_budget_adds_spent_and_projected_with_the_margin() -> None:
    b = bg.budget()
    assert b.spent == pytest.approx(sum(bg.SPENT.values()))
    assert b.projected == pytest.approx(
        bg.MARGIN * sum(line.usd for line in bg.projected()))
    assert b.committed == pytest.approx(b.spent + b.projected)
    assert b.committed < bg.CAP_USD


def test_n_max_and_the_balanced_growth_ceiling() -> None:
    b = bg.budget()
    expected = PLANNED_POOLED_N + int((bg.CAP_USD - b.committed) // b.extra_question)
    assert b.n_max == expected
    assert b.n_max_eff == min(b.n_max, bg.BALANCED_GROWTH_CEILING)
    assert b.n_max_eff <= 448


def test_extra_question_carries_its_s0_share_and_the_margin() -> None:
    s14 = ("S1", "S2", "S3", "S4")
    raw = (sum(bg.eval_question_cost(s) for s in s14) / 4
           + 0.25 * bg.eval_question_cost("S0"))
    assert bg.extra_question_cost() == pytest.approx(bg.MARGIN * raw)
