"""The registered outcome space of E-001 (Layer 1 verdict).

Encodes, as code, the decision rule registered in `experiments/registry.md`
(E-001, "Decision rule — outcome space") and mirrored in
`docs/measurability-gate.md` (gate 1):

- the three-valued verdict of a primary contrast;
- the outcome-space rows, evaluated in order (the first matching row wins);
- the four λ* cases (plus "no difference" and "undetermined").

The rows are kept as ordered (id, predicate) pairs rather than an if/else
chain so that tests can evaluate every predicate independently and check that
overlaps between rows are only the ones resolved on purpose by precedence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

ACTION_THRESHOLD = 0.25
"""Action threshold for H1/H2, in units of expected cost C."""


class Verdict(Enum):
    """Three-valued verdict of a primary contrast."""

    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class PlaceboStatus(Enum):
    """Whether the depth placebo (A4p) can be read."""

    DELIVERED = "delivered"
    """Dose adherence passed and the placebo is not harmful."""
    NOT_DELIVERED = "not_delivered"
    """Dose adherence failed twice."""
    HARMFUL = "harmful"
    """Lower limit of C(A3) − C(A4p) is at or below −0.25."""


class OracleRoom(Enum):
    """Position of the 95% interval of O2 − A3 relative to the threshold."""

    BELOW = "below"
    """Upper limit < threshold: a gold-label stop does not reach it."""
    ABOVE = "above"
    """Lower limit ≥ threshold: there is room."""
    STRADDLES = "straddles"
    """The interval contains the threshold: room not resolved."""


class LambdaCase(Enum):
    """Tipping-point case of A4 against a reference arm."""

    A4_DOMINATES = "a4_dominates"
    TIPPING_ABOVE = "tipping_above"
    TIPPING_BELOW = "tipping_below"
    A4_DOMINATED = "a4_dominated"
    NO_DIFFERENCE = "no_difference"
    UNDETERMINED = "undetermined"


def verdict(
    point: float, lower: float, upper: float, threshold: float = ACTION_THRESHOLD
) -> Verdict:
    """Three-valued verdict of a contrast D = C(reference) − C(treatment).

    Args:
        point: Point estimate of the mean of D.
        lower: Lower limit of the registered interval (97.5% BCa).
        upper: Upper limit of the registered interval.
        threshold: Action threshold in units of C.

    Returns:
        SUPPORTED if the interval excludes zero in favour of the treatment and
        the point estimate is at least the threshold; REFUTED if the upper limit
        is below the threshold; INCONCLUSIVE otherwise.

    Raises:
        ValueError: If the interval does not contain the point estimate, which
            would make SUPPORTED and REFUTED simultaneously possible.
    """
    if not lower <= point <= upper:
        raise ValueError(
            f"interval [{lower}, {upper}] does not contain the point {point}"
        )
    if lower > 0 and point >= threshold:
        return Verdict.SUPPORTED
    if upper < threshold:
        return Verdict.REFUTED
    return Verdict.INCONCLUSIVE


@dataclass(frozen=True)
class OutcomeInputs:
    """Everything the E-001 outcome space reads, already reduced to booleans.

    Attributes:
        descriptive_branch: Gate 8 asked for more than it allows: n* times the
            cluster design effect above n_max_eff = min(n_max, 448).
        futility_fired: Upper 80% limit of O2 − A3 on dev S1–S3 < threshold,
            evaluated before the opening.
        h1: Verdict of H1 (A3 − A4, S1–S4 pooled).
        s0_share_ge_half: The S0 gain of A4 over A3 is at least 50% of the
            pooled gain.
        s0_excludes_zero: The S0 interval excludes zero in favour of A4, with
            at least 10 discordant clusters.
        placebo: Whether A4p can be read.
        placebo_share_lt_half: A4's gain over A4p is below 50% of its gain
            over A3.
        mediation_ge_half: The registered mediation (net of A4p when the
            placebo is delivered, gross otherwise) is at least 50%.
        oracle_room: Position of the 95% interval of O2 − A3 on eval S1–S3.
    """

    descriptive_branch: bool
    futility_fired: bool
    h1: Verdict
    s0_share_ge_half: bool
    s0_excludes_zero: bool
    placebo: PlaceboStatus
    placebo_share_lt_half: bool
    mediation_ge_half: bool
    oracle_room: OracleRoom


def _supported(x: OutcomeInputs) -> bool:
    return x.h1 is Verdict.SUPPORTED


ROWS: tuple[tuple[str, Callable[[OutcomeInputs], bool]], ...] = (
    ("0", lambda x: x.descriptive_branch),
    ("0b", lambda x: x.futility_fired),
    ("1", lambda x: _supported(x) and x.s0_share_ge_half and x.s0_excludes_zero),
    (
        "2",
        lambda x: _supported(x)
        and x.placebo is PlaceboStatus.DELIVERED
        and x.placebo_share_lt_half,
    ),
    ("3", lambda x: _supported(x) and x.mediation_ge_half),
    ("4", lambda x: _supported(x) and not x.mediation_ge_half),
    ("5", lambda x: x.h1 is Verdict.REFUTED),
    (
        "6",
        lambda x: x.h1 is Verdict.INCONCLUSIVE and x.oracle_room is OracleRoom.BELOW,
    ),
    (
        "7",
        lambda x: x.h1 is Verdict.INCONCLUSIVE and x.oracle_room is OracleRoom.ABOVE,
    ),
    ("7b", lambda x: x.h1 is Verdict.INCONCLUSIVE),
)
"""Outcome-space rows in registered order; the first matching row wins."""

ROW_IDS: tuple[str, ...] = tuple(row_id for row_id, _ in ROWS)


def matching_rows(inputs: OutcomeInputs) -> list[str]:
    """Return every row whose condition holds, in registered order.

    Args:
        inputs: The reduced E-001 results.

    Returns:
        Row ids whose predicate is true, before precedence is applied.
    """
    return [row_id for row_id, predicate in ROWS if predicate(inputs)]


def classify(inputs: OutcomeInputs) -> str:
    """Return the published outcome-space row (first matching row wins).

    Args:
        inputs: The reduced E-001 results.

    Returns:
        The id of the first matching row.

    Raises:
        LookupError: If no row matches, meaning the outcome space has a gap.
    """
    rows = matching_rows(inputs)
    if not rows:
        raise LookupError(f"no outcome-space row matches {inputs}")
    return rows[0]


def lambda_case(
    err_a4: float,
    err_ref: float,
    abst_a4: float,
    abst_ref: float,
    err_diff_resolved: bool,
) -> LambdaCase:
    """Classify A4 against a reference arm by operating point.

    Args:
        err_a4: Error rate of A4.
        err_ref: Error rate of the reference arm.
        abst_a4: Abstention rate of A4.
        abst_ref: Abstention rate of the reference arm.
        err_diff_resolved: Whether the 95% interval of the error difference
            excludes zero. λ* is only published when it does.

    Returns:
        The λ* case, NO_DIFFERENCE when both rates are equal, or UNDETERMINED
        when the error difference is not resolved.
    """
    if not err_diff_resolved:
        return LambdaCase.UNDETERMINED
    d_err = err_a4 - err_ref
    d_abst = abst_a4 - abst_ref
    if d_err == 0 and d_abst == 0:
        return LambdaCase.NO_DIFFERENCE
    if d_err <= 0 and d_abst <= 0:
        return LambdaCase.A4_DOMINATES
    if d_err >= 0 and d_abst >= 0:
        return LambdaCase.A4_DOMINATED
    if d_err < 0:
        return LambdaCase.TIPPING_ABOVE
    return LambdaCase.TIPPING_BELOW


def lambda_star(
    err_a4: float, err_ref: float, abst_a4: float, abst_ref: float
) -> float:
    """Tipping point λ* = (abst_A4 − abst_ref) / (err_ref − err_A4).

    Only meaningful in the two tipping cases, where it is positive.

    Args:
        err_a4: Error rate of A4.
        err_ref: Error rate of the reference arm.
        abst_a4: Abstention rate of A4.
        abst_ref: Abstention rate of the reference arm.

    Returns:
        The value of λ at which A4 and the reference arm have equal expected
        cost.

    Raises:
        ZeroDivisionError: If the error rates are equal.
    """
    return (abst_a4 - abst_ref) / (err_ref - err_a4)
