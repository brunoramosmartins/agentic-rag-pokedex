"""Power and sizing — the numbers that decide n, pinned against known answers.

Measurability gate 7: the power script must reproduce E-026 of the previous
project before any of its numbers is used here. Then every figure quoted in
`docs/measurability-gate.md` is recomputed, so the document and the code cannot
drift apart.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

from agentic_pokedex.evaluation import power as pw

REPO_ROOT = Path(__file__).resolve().parents[1]
SDS = (1.0, 1.5, 2.0)


# ---------------------------------------------------------------------------
# The power function is the standard one
# ---------------------------------------------------------------------------


def test_zero_effect_has_power_equal_to_alpha() -> None:
    assert pw.power_two_sided(0.0, 0.1, alpha=0.05) == pytest.approx(0.05, abs=1e-9)


def test_the_classic_2_8_standard_errors_rule() -> None:
    assert pw.power_two_sided(2.80 * 0.1, 0.1, alpha=0.05) == pytest.approx(
        0.80, abs=0.01
    )


def test_power_rises_with_effect_and_falls_with_se() -> None:
    assert pw.power_two_sided(0.1, 0.1) < pw.power_two_sided(0.3, 0.1)
    assert pw.power_two_sided(0.2, 0.2) < pw.power_two_sided(0.2, 0.1)


def test_mde_is_where_power_reaches_the_target() -> None:
    floor = pw.mde(320, 1.5, alpha=pw.ALPHA_PER_CONTRAST)
    se = pw.se_paired(320, 1.5)
    assert pw.power_two_sided(floor, se, alpha=pw.ALPHA_PER_CONTRAST) == pytest.approx(
        pw.TARGET_POWER, abs=1e-6
    )


def test_n_for_is_the_inverse_of_the_floor() -> None:
    n = pw.n_for(0.25, 1.5, alpha=pw.ALPHA_PER_CONTRAST)
    assert n is not None
    se_ok, se_short = pw.se_paired(n, 1.5), pw.se_paired(n - 1, 1.5)
    assert pw.power_two_sided(0.25, se_ok, alpha=pw.ALPHA_PER_CONTRAST) >= 0.80
    assert pw.power_two_sided(0.25, se_short, alpha=pw.ALPHA_PER_CONTRAST) < 0.80
    assert pw.n_for(0.0, 1.5) is None


def test_an_interaction_costs_four_times_the_questions() -> None:
    sd = math.sqrt(pw.E026_DISCORDANCE)
    simple = pw.mde(57, sd)
    per_group = pw.n_for(simple, sd, interaction=True)
    assert per_group == 114  # two groups of 114 = 228 = 4 × 57


# ---------------------------------------------------------------------------
# Gate 7: the known answer
# ---------------------------------------------------------------------------


def test_reproduces_e026_of_the_previous_project() -> None:
    assert pw.reproduce_e026() == []


def test_e026_contrast_list_is_complete_and_consistent() -> None:
    # E-001's five strata partition its 57 questions; the overall row is their sum.
    strata = [
        c
        for c in pw.E026_CONTRASTS
        if c[0].startswith("E-001 ") and "overall" not in c[0]
    ]
    overall = next(c for c in pw.E026_CONTRASTS if "overall" in c[0])
    assert sum(c[3] for c in strata) == overall[3] == 57
    assert sum(c[1] for c in strata) == overall[1]
    assert sum(c[2] for c in strata) == overall[2]
    assert len(pw.E026_CONTRASTS) == 9


def test_reproduction_detects_a_wrong_published_number(monkeypatch) -> None:
    broken = ((57, 0.250, 0.287),) + pw.E026_FLOOR_TABLE[1:]
    monkeypatch.setattr(pw, "E026_FLOOR_TABLE", broken)
    assert any("n=57" in p for p in pw.reproduce_e026())


def test_cli_reports_pass(capsys) -> None:
    assert pw.main(["--reproduce-e026"]) == 0
    assert "GATE 7 POWER SCRIPT: PASS" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The numbers quoted in docs/measurability-gate.md
# ---------------------------------------------------------------------------


def test_n_to_detect_the_action_threshold() -> None:
    got = [pw.n_for(0.25, s, alpha=pw.ALPHA_PER_CONTRAST) for s in SDS]
    assert got == [153, 343, 609]


def test_per_stratum_mde() -> None:
    got = [round(pw.mde(80, s), 2) for s in SDS]
    assert got == [0.31, 0.47, 0.63]


def test_h3_noninferiority_n() -> None:
    assert [pw.n_noninferiority(s) for s in SDS] == [99, 223, 396]


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (0.25, [0.50, 0.50, 0.50]),
        (0.30, [0.81, 0.72, 0.67]),
        (0.35, [0.96, 0.88, 0.81]),
        (0.40, [1.00, 0.96, 0.91]),
    ],
)
def test_p_supported_at_the_plan(delta: float, expected: list[float]) -> None:
    assert [round(pw.p_supported(delta, s, 320), 2) for s in SDS] == expected


def test_supported_is_a_coin_flip_at_the_threshold() -> None:
    for sd in SDS:
        for n in (320, 640, 5000):
            assert pw.p_supported(0.25, sd, n) == pytest.approx(0.5)


def test_n_star_at_design_effect() -> None:
    assert [pw.n_star(s) for s in SDS] == [78, 175, 311]


def test_sd_thresholds_quoted_for_gate_8() -> None:
    assert pw.n_star(2.03) <= 320 < pw.n_star(2.04)
    assert pw.n_star(2.87) <= 640 < pw.n_star(2.88)


def test_n_star_unreachable_when_design_effect_is_the_threshold() -> None:
    assert pw.n_star(1.0, delta_design=0.25) is None


@pytest.mark.parametrize(
    ("delta", "expected"),
    [(0.0, [0.99, 0.77, 0.50]), (0.10, [0.67, 0.33, 0.18])],
)
def test_p_refuted_at_the_plan(delta: float, expected: list[float]) -> None:
    assert [round(pw.p_refuted(delta, s, 320), 2) for s in SDS] == expected


def test_supported_and_refuted_never_both_likely() -> None:
    for delta in (0.0, 0.2, 0.25, 0.35):
        for sd in SDS:
            total = pw.p_supported(delta, sd, 320) + pw.p_refuted(delta, sd, 320)
            assert total <= 1.0 + 1e-12


def _gate3_mde_table() -> dict[int, list[float]]:
    text = (REPO_ROOT / "docs/measurability-gate.md").read_text(encoding="utf-8")
    section = text[text.index("Minimum detectable effect") :]
    rows: dict[int, list[float]] = {}
    for line in section.splitlines():
        cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.match(r"^\d+", cells[0]):
            n = int(re.match(r"^\d+", cells[0]).group())
            rows[n] = [float(c) for c in cells[1:]]
        elif rows and not line.startswith("|"):
            break
    return rows


def test_gate3_mde_table_in_the_document_matches_the_code() -> None:
    table = _gate3_mde_table()
    assert set(table) == {240, 320, 400, 480, 640}
    for n, published in table.items():
        got = [round(pw.mde(n, s, alpha=pw.ALPHA_PER_CONTRAST), 3) for s in SDS]
        assert got == published, n


# ---------------------------------------------------------------------------
# Gate 8: n_max and the sizing decision
# ---------------------------------------------------------------------------


def test_n_max_adds_what_the_remaining_budget_pays_for() -> None:
    got = pw.n_max(cap_usd=13.5, committed_usd=12.9, cost_per_extra_question_usd=0.016)
    assert got == 357


def test_n_max_falls_below_the_plan_when_already_over_cap() -> None:
    assert pw.n_max(13.5, 14.0, 0.016) < pw.PLANNED_POOLED_N


@pytest.mark.parametrize(
    ("sd_h1", "sd_h2", "n_max", "prefix"),
    [
        (1.7, 1.9, 440, "keep the plan"),
        (2.2, 1.5, 440, "draw more questions up to n* = 376"),
        (2.5, 1.5, 440, "row 0"),
    ],
)
def test_sizing_decision_branches(
    sd_h1: float, sd_h2: float, n_max: int, prefix: str
) -> None:
    decision = pw.sizing_decision(sd_h1, sd_h2, n_max)
    assert decision.branch.startswith(prefix)
    assert decision.n_star == max(decision.n_star_h1, decision.n_star_h2)


def test_the_larger_n_star_governs_both_contrasts() -> None:
    decision = pw.sizing_decision(1.0, 2.2, 1000)
    assert decision.n_star == decision.n_star_h2 > decision.n_star_h1
