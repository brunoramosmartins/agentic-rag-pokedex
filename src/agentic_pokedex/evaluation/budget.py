"""The v1.0 budget re-estimated with Phase 3's measured costs, and n_max.

Gate 8: n_max is the largest pooled S1–S4 n the US$ 20 cap pays for after the
cut order's first three cuts (A6, the cue ablation, A3′), computed with Phase
3's measured costs and logged before the dress rehearsal; n_max_eff =
min(n_max, 448) (PI-021). No cap increase after the rehearsal.

Measured (E-004, dev): A0, A1 and A2 per question by stratum; A3 per question
by stratum, S1–S4. Arms not yet built are priced as multiples of what was
measured, each a declared assumption (``ASSUMED``), chosen to err high; every
projected cost then carries ``MARGIN``. What has been spent is read from the
runs and the registry.

Usage::

    python -m agentic_pokedex.evaluation.budget
"""

from __future__ import annotations

import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from agentic_pokedex.evaluation.power import PLANNED_POOLED_N, n_max

CAP_USD = 20.0
BALANCED_GROWTH_CEILING = 448
"""Pooled S1–S4 n where balanced growth stops (material S1; PI-019, PI-021)."""

MARGIN = 1.5
"""Every projected (not yet spent) cost is multiplied by this."""

STRATA = ("S0", "S1", "S2", "S3", "S4")

MEASURED: Mapping[str, Mapping[str, float]] = {
    # US$ per question, E-004 on dev (runs/e004, 2026-10-08), Batch prices.
    "A0": {"S0": 0.00014, "S1": 0.00015, "S2": 0.00011, "S3": 0.00011, "S4": 0.00012},
    "A1": {"S0": 0.00012, "S1": 0.00029, "S2": 0.00019, "S3": 0.00037, "S4": 0.00034},
    "A2": {"S0": 0.00052, "S1": 0.00056, "S2": 0.00053, "S3": 0.00091, "S4": 0.00071},
    # A3 ran on S1–S4 only; S0 (one search, answer) is priced as S2.
    "A3": {"S0": 0.00054, "S1": 0.00070, "S2": 0.00054, "S3": 0.00211, "S4": 0.00133},
}

ASSUMED: Mapping[str, tuple[str, float, str]] = {
    "A3'": ("A3", 1.0, "the same loop run again"),
    "A4": ("A3", 2.5, "a judge call per proposal, about one more call of the "
                      "same input per step, plus the steps vetoes add"),
    "A4p": ("A3", 1.5, "A3's loop held to A4's step counts"),
    "O2": ("A3", 1.5, "A3's loop, vetoed until the gold label is sufficient"),
    "O1": ("A1", 1.0, "one call on the gold units, about A1's evidence"),
}

A6_PER_QUESTION = 0.0081
"""16 × B = 64,000 evidence tokens in one call at US$ 0.125 / M, plus output."""

SPENT: Mapping[str, float] = {
    "E-003 identity probe, runs 1 and 2": 0.1614 + 0.0905,
    "token meter check": 0.0014,
    "E-004 smoke on train": 0.0088,
    "E-004 pilot": 0.1912,
    "E-005 G2 closed-book": 0.2798,
}

EVAL_L1 = {"S0": 80, "S1": 80, "S2": 80, "S3": 80, "S4": 80}
BENIGN_SLICE = 40
REHEARSAL = 60
DEV_S1_S4 = 120
DEV = 150


def per_question(arm: str, stratum: str) -> float:
    """US$ per question of an arm on a stratum (measured or assumed)."""
    if arm in MEASURED:
        return MEASURED[arm][stratum]
    if arm == "A6":
        return A6_PER_QUESTION if stratum == "S3" else 0.0
    base, factor, _ = ASSUMED[arm]
    return factor * MEASURED[base][stratum]


def mean_cost(arm: str, strata: tuple[str, ...]) -> float:
    """Mean US$ per question over equally weighted strata."""
    return sum(per_question(arm, s) for s in strata) / len(strata)


ARMS_EVAL = ("A0", "A1", "A2", "A3", "A4", "O2")
"""Arms on all of eval-L1 after the three cuts; A4p runs S1–S4, O1 S0–S3."""


def eval_question_cost(stratum: str) -> float:
    """Every committed arm's cost for one eval-L1 question of a stratum."""
    cost = sum(per_question(a, stratum) for a in ARMS_EVAL)
    if stratum != "S0":
        cost += per_question("A4p", stratum)
    if stratum != "S4":
        cost += per_question("O1", stratum)
    return cost


@dataclass(frozen=True)
class Line:
    """One item of the projected v1.0 spend."""

    phase: str
    item: str
    usd: float


def projected() -> list[Line]:
    """What v1.0 still spends after the three cuts, before ``MARGIN``."""
    s14 = ("S1", "S2", "S3", "S4")
    every = ("S0", *s14)
    a3, a4 = mean_cost("A3", s14), mean_cost("A4", s14)
    lines = [
        Line("4", "A1 k sweep: 3 values × dev 150", 3 * DEV * mean_cost("A1", every)),
        Line("4", "A2 sweep stage 2: 3 configurations × dev S1–S4",
             3 * DEV_S1_S4 * mean_cost("A2", s14)),
        Line("4", "A2 prompt: 3 iterations × dev S1–S4",
             3 * DEV_S1_S4 * mean_cost("A2", s14)),
        Line("4", "O1 on dev S0–S3", DEV * mean_cost("O1", every[:4])),
        Line("4", "A6 on dev S3 (30)", 30 * A6_PER_QUESTION),
        Line("5", "agent prompt: 3 iterations × dev S1–S4", 3 * DEV_S1_S4 * a3),
        Line("5", "judge prompt: 3 iterations × dev S1–S4", 3 * DEV_S1_S4 * a4),
        Line("5", "dev report: A3, A4, A4p, O2 on dev 150",
             DEV * sum(mean_cost(a, every) for a in ("A3", "A4", "A4p", "O2"))),
        Line("6", "dress rehearsal: every v1.0 arm on 60",
             REHEARSAL * (sum(mean_cost(a, every) for a in
                              ("A0", "A1", "A2", "A3", "A3'", "A4", "A4p", "O1",
                               "O2")) + mean_cost("A6", every))),
        Line("6", "eval-L1 at the planned 400, every committed arm",
             sum(n * eval_question_cost(s) for s, n in EVAL_L1.items())),
        Line("6", "benign S1 slice: A3, A4, A4p on 40",
             BENIGN_SLICE * sum(per_question(a, "S1") for a in ("A3", "A4", "A4p"))),
    ]
    return lines


def extra_question_cost() -> float:
    """One more pooled S1–S4 question, with the S0 share balanced growth adds
    (80 S0 per 320 S1–S4), across every committed arm, with ``MARGIN``."""
    s14 = ("S1", "S2", "S3", "S4")
    per_s14 = sum(eval_question_cost(s) for s in s14) / len(s14)
    return MARGIN * (per_s14 + 0.25 * eval_question_cost("S0"))


@dataclass(frozen=True)
class Budget:
    """The v1.0 budget and gate 8's n_max."""

    spent: float
    projected: float
    committed: float
    extra_question: float
    n_max: int
    n_max_eff: int


def budget() -> Budget:
    """Spent + projected (with ``MARGIN``) → n_max and n_max_eff."""
    spent = sum(SPENT.values())
    proj = MARGIN * sum(line.usd for line in projected())
    committed = spent + proj
    extra = extra_question_cost()
    nm = n_max(CAP_USD, committed, extra, PLANNED_POOLED_N)
    return Budget(spent, proj, committed, extra, nm,
                  min(nm, BALANCED_GROWTH_CEILING))


def main(argv: list[str] | None = None) -> int:
    """Print the re-estimated budget and n_max."""
    b = budget()
    print(f"Spent so far: US$ {b.spent:.3f}")
    for name, usd in SPENT.items():
        print(f"  {name}: {usd:.4f}")
    print(f"\nProjected v1.0 spend after cuts (1)–(3), ×{MARGIN} margin: "
          f"US$ {b.projected:.2f}")
    for line in projected():
        print(f"  Phase {line.phase} — {line.item}: {MARGIN * line.usd:.3f}")
    print(f"\nCommitted: US$ {b.committed:.2f} of the US$ {CAP_USD:.0f} cap")
    print(f"One more pooled S1–S4 question (with its S0 share): "
          f"US$ {b.extra_question:.4f}")
    print(f"n_max = {b.n_max}; n_max_eff = min(n_max, "
          f"{BALANCED_GROWTH_CEILING}) = {b.n_max_eff}")
    if not math.isfinite(b.extra_question):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
