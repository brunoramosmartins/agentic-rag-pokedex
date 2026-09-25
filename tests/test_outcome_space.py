"""The E-001 outcome space leaves no outcome without exactly one reading.

A registered decision rule only protects if every possible outcome falls in
exactly one row. These tests enumerate every combination of the inputs the
rule reads, and every sign combination of the λ* case, and check:

- completeness: every combination matches at least one row;
- reachability: every row is the published row for some combination;
- precedence: rows overlap only where the registered order resolves it on
  purpose;
- the documented edge cases land where the registry says;
- the code and the two documents list the same rows.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path

import pytest

from agentic_pokedex.evaluation.outcome_space import (
    ROW_IDS,
    LambdaCase,
    OracleRoom,
    OutcomeInputs,
    PlaceboStatus,
    Verdict,
    classify,
    lambda_case,
    lambda_star,
    matching_rows,
    verdict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

BOOLS = (False, True)

ALL_INPUTS = [
    OutcomeInputs(*combo)
    for combo in itertools.product(
        BOOLS,  # descriptive_branch
        BOOLS,  # futility_fired
        list(Verdict),  # h1
        BOOLS,  # s0_share_ge_half
        BOOLS,  # s0_excludes_zero
        list(PlaceboStatus),  # placebo
        BOOLS,  # placebo_share_lt_half
        BOOLS,  # mediation_ge_half
        list(OracleRoom),  # oracle_room
    )
]

# Overlaps the registered order resolves on purpose. Rows 0 and 0b pre-empt
# everything; the falsifier (1) and the placebo (2) pre-empt the mechanism
# readings (3, 4); 7b is the "otherwise" of rows 6 and 7.
INTENDED_OVERLAPS = {
    frozenset(pair)
    for pair in (
        [("0", r) for r in ROW_IDS if r != "0"]
        + [("0b", r) for r in ROW_IDS if r not in ("0", "0b")]
        + [("1", "2"), ("1", "3"), ("1", "4"), ("2", "3"), ("2", "4")]
        + [("6", "7b"), ("7", "7b")]
    )
}


def _inputs(**overrides: object) -> OutcomeInputs:
    """Build a neutral H1-supported outcome and apply overrides."""
    base = dict(
        descriptive_branch=False,
        futility_fired=False,
        h1=Verdict.SUPPORTED,
        s0_share_ge_half=False,
        s0_excludes_zero=False,
        placebo=PlaceboStatus.DELIVERED,
        placebo_share_lt_half=False,
        mediation_ge_half=True,
        oracle_room=OracleRoom.STRADDLES,
    )
    base.update(overrides)
    return OutcomeInputs(**base)


# ---------------------------------------------------------------------------
# Outcome space
# ---------------------------------------------------------------------------


def test_every_combination_matches_a_row() -> None:
    gaps = [x for x in ALL_INPUTS if not matching_rows(x)]
    assert not gaps, f"{len(gaps)} combinations match no row, e.g. {gaps[0]}"


def test_every_row_is_reachable() -> None:
    published = {classify(x) for x in ALL_INPUTS}
    assert published == set(ROW_IDS)


def test_overlaps_are_only_the_intended_ones() -> None:
    unexpected = set()
    for x in ALL_INPUTS:
        for pair in itertools.combinations(matching_rows(x), 2):
            if frozenset(pair) not in INTENDED_OVERLAPS:
                unexpected.add(pair)
    assert not unexpected, f"rows overlap without registered precedence: {unexpected}"


def test_first_match_is_the_published_row() -> None:
    for x in ALL_INPUTS:
        assert classify(x) == matching_rows(x)[0]


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        # Row 0 pre-empts everything, including futility.
        ({"descriptive_branch": True, "futility_fired": True}, "0"),
        # 0b: futility declared before the opening; a supported H1 on eval
        # must not be published as "thesis supported".
        ({"futility_fired": True}, "0b"),
        # Falsifier needs both S0 conditions and a supported H1.
        ({"s0_share_ge_half": True, "s0_excludes_zero": True}, "1"),
        ({"s0_share_ge_half": True, "s0_excludes_zero": False}, "3"),
        (
            {
                "h1": Verdict.REFUTED,
                "s0_share_ge_half": True,
                "s0_excludes_zero": True,
            },
            "5",
        ),
        # Placebo explains the gain only when it was delivered.
        ({"placebo_share_lt_half": True}, "2"),
        (
            {"placebo_share_lt_half": True, "placebo": PlaceboStatus.HARMFUL},
            "3",
        ),
        (
            {
                "placebo_share_lt_half": True,
                "placebo": PlaceboStatus.NOT_DELIVERED,
                "mediation_ge_half": False,
            },
            "4",
        ),
        # Mechanism readings.
        ({"mediation_ge_half": True}, "3"),
        ({"mediation_ge_half": False}, "4"),
        # Inconclusive H1: room is read from the O2 − A3 interval.
        ({"h1": Verdict.INCONCLUSIVE, "oracle_room": OracleRoom.BELOW}, "6"),
        ({"h1": Verdict.INCONCLUSIVE, "oracle_room": OracleRoom.ABOVE}, "7"),
        ({"h1": Verdict.INCONCLUSIVE, "oracle_room": OracleRoom.STRADDLES}, "7b"),
        # A refuted H1 ignores the oracle.
        ({"h1": Verdict.REFUTED, "oracle_room": OracleRoom.ABOVE}, "5"),
    ],
)
def test_documented_edge_cases(overrides: dict[str, object], expected: str) -> None:
    assert classify(_inputs(**overrides)) == expected


# ---------------------------------------------------------------------------
# Three-valued verdict
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("point", "lower", "upper", "expected"),
    [
        (0.40, 0.10, 0.70, Verdict.SUPPORTED),
        (0.25, 0.01, 0.49, Verdict.SUPPORTED),  # point exactly at the threshold
        (0.20, 0.05, 0.35, Verdict.INCONCLUSIVE),  # excludes zero, below threshold
        (0.30, -0.05, 0.65, Verdict.INCONCLUSIVE),  # above threshold, includes zero
        (0.10, 0.02, 0.20, Verdict.REFUTED),  # significant but too small
        (-0.30, -0.60, 0.00, Verdict.REFUTED),  # treatment worse
        (0.00, -0.25, 0.25, Verdict.INCONCLUSIVE),  # upper exactly at threshold
    ],
)
def test_verdict(point: float, lower: float, upper: float, expected: Verdict) -> None:
    assert verdict(point, lower, upper) is expected


def test_verdict_rejects_interval_without_point() -> None:
    with pytest.raises(ValueError):
        verdict(0.30, -0.20, 0.20)


def test_verdict_values_are_mutually_exclusive_on_a_grid() -> None:
    grid = [x / 20 for x in range(-20, 21)]
    for lower, point, upper in itertools.product(grid, repeat=3):
        if not lower <= point <= upper:
            continue
        supported = lower > 0 and point >= 0.25
        refuted = upper < 0.25
        assert not (supported and refuted)
        assert verdict(point, lower, upper) is (
            Verdict.SUPPORTED
            if supported
            else Verdict.REFUTED
            if refuted
            else Verdict.INCONCLUSIVE
        )


# ---------------------------------------------------------------------------
# λ* cases
# ---------------------------------------------------------------------------

EXPECTED_LAMBDA_CASES = {
    # (sign of err_A4 − err_ref, sign of abst_A4 − abst_ref)
    (-1, -1): LambdaCase.A4_DOMINATES,
    (-1, 0): LambdaCase.A4_DOMINATES,
    (0, -1): LambdaCase.A4_DOMINATES,
    (-1, 1): LambdaCase.TIPPING_ABOVE,
    (1, -1): LambdaCase.TIPPING_BELOW,
    (1, 1): LambdaCase.A4_DOMINATED,
    (1, 0): LambdaCase.A4_DOMINATED,
    (0, 1): LambdaCase.A4_DOMINATED,
    (0, 0): LambdaCase.NO_DIFFERENCE,
}


@pytest.mark.parametrize(("signs", "expected"), EXPECTED_LAMBDA_CASES.items())
def test_lambda_case_covers_every_sign_combination(
    signs: tuple[int, int], expected: LambdaCase
) -> None:
    d_err, d_abst = signs
    err_ref, abst_ref = 0.30, 0.20
    case = lambda_case(
        err_a4=err_ref + 0.1 * d_err,
        err_ref=err_ref,
        abst_a4=abst_ref + 0.1 * d_abst,
        abst_ref=abst_ref,
        err_diff_resolved=True,
    )
    assert case is expected


def test_lambda_case_is_undetermined_when_error_difference_unresolved() -> None:
    case = lambda_case(0.20, 0.30, 0.30, 0.20, err_diff_resolved=False)
    assert case is LambdaCase.UNDETERMINED


@pytest.mark.parametrize(
    ("err_a4", "err_ref", "abst_a4", "abst_ref"),
    [
        (0.20, 0.30, 0.30, 0.20),  # tipping above
        (0.30, 0.20, 0.20, 0.30),  # tipping below
    ],
)
def test_lambda_star_is_positive_in_tipping_cases(
    err_a4: float, err_ref: float, abst_a4: float, abst_ref: float
) -> None:
    value = lambda_star(err_a4, err_ref, abst_a4, abst_ref)
    assert value == pytest.approx(1.0)
    # At λ*, both arms have the same expected cost: λ·err + abst.
    cost_a4 = value * err_a4 + abst_a4
    cost_ref = value * err_ref + abst_ref
    assert cost_a4 == pytest.approx(cost_ref)


# ---------------------------------------------------------------------------
# Code and documents agree
# ---------------------------------------------------------------------------

_ROW_LINE = re.compile(r"^\| (\d+b?) \|")


def _rows_in(path: Path, start_marker: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    section = text[text.index(start_marker) :]
    rows: list[str] = []
    for line in section.splitlines():
        match = _ROW_LINE.match(line)
        if match:
            rows.append(match.group(1))
        elif rows and not line.startswith("|"):
            break
    return rows


@pytest.mark.parametrize(
    ("relative_path", "start_marker"),
    [
        ("experiments/registry.md", "### Decision rule — outcome space"),
        ("docs/measurability-gate.md", "**Three-valued verdict**"),
    ],
)
def test_documents_list_the_same_rows_in_the_same_order(
    relative_path: str, start_marker: str
) -> None:
    assert _rows_in(REPO_ROOT / relative_path, start_marker) == list(ROW_IDS)
