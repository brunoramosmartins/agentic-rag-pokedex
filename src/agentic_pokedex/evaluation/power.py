"""Power and sizing for E-001 (measurability gates 3, 5 and 8).

Normal-approximation power for a **paired mean difference** D, where each
question contributes D = C(reference) − C(treatment) with C ∈ {0, 1, λ}. Only
the standard deviation of D enters, so the same functions serve a binary
outcome (SD² = discordance rate) and the expected-cost outcome of this project.

Before it produces any number for this project, the module must reproduce a
known answer (measurability gate 7): the detectability table of E-026 in the
previous project (`graphrag-mtg-rules`, commit ``b3f293e``,
`scripts/detectability.py`), whose method this module generalizes.
``reproduce_e026()`` does that check.

Run as a script to print the gate tables, the E-026 reproduction, or the
Phase 6 sizing decision:

    python -m agentic_pokedex.evaluation.power
    python -m agentic_pokedex.evaluation.power --reproduce-e026
    python -m agentic_pokedex.evaluation.power --sd-h1 1.7 --sd-h2 1.9 --n-max 440
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from statistics import NormalDist

_Z = NormalDist()

TARGET_POWER = 0.80
ALPHA_FAMILY = 0.05
ALPHA_PER_CONTRAST = 0.025
"""Bonferroni over the two primary contrasts (H1, H2); two-sided."""
ACTION_THRESHOLD = 0.25
DELTA_DESIGN = 0.35
PLANNED_POOLED_N = 320
N_LIMIT = 100_000


def z_crit(alpha: float) -> float:
    """Two-sided critical value for a significance level."""
    return _Z.inv_cdf(1 - alpha / 2)


def se_paired(n: int, sd: float) -> float:
    """Standard error of a paired mean difference over n questions."""
    return sd / math.sqrt(n)


def se_interaction(n_per_group: int, sd: float) -> float:
    """SE of a difference between two paired differences, **n per group**.

    Twice the variance of one group, so an interaction needs about four times
    the questions of the simple contrast it is built from.
    """
    return math.sqrt(2) * sd / math.sqrt(n_per_group)


def power_two_sided(delta: float, se: float, alpha: float = ALPHA_FAMILY) -> float:
    """Two-sided power to reject D = 0 at a true effect ``delta``.

    Both tails are counted, so power at ``delta = 0`` equals ``alpha``.
    """
    z = abs(delta) / se
    c = z_crit(alpha)
    return 1 - _Z.cdf(c - z) + _Z.cdf(-c - z)


def mde(
    n: int,
    sd: float,
    *,
    alpha: float = ALPHA_FAMILY,
    target: float = TARGET_POWER,
    interaction: bool = False,
) -> float:
    """Smallest |effect| detectable at the target power, by bisection.

    Args:
        n: Questions (total for a simple contrast, **per group** for an
            interaction).
        sd: Standard deviation of D.
        alpha: Two-sided significance level.
        target: Target power.
        interaction: Use the interaction standard error.

    Returns:
        The minimum detectable effect, in the units of D.
    """
    se = se_interaction(n, sd) if interaction else se_paired(n, sd)
    low, high = 0.0, 50.0 * sd
    for _ in range(80):
        mid = (low + high) / 2
        if power_two_sided(mid, se, alpha) < target:
            low = mid
        else:
            high = mid
    return high


def n_for(
    delta: float,
    sd: float,
    *,
    alpha: float = ALPHA_FAMILY,
    target: float = TARGET_POWER,
    interaction: bool = False,
) -> int | None:
    """Smallest n reaching the target power at ``delta``.

    Returns:
        The n (per group for an interaction), or None for a zero effect or
        beyond ``N_LIMIT``.
    """
    if delta == 0:
        return None
    for n in range(2, N_LIMIT + 1):
        se = se_interaction(n, sd) if interaction else se_paired(n, sd)
        if power_two_sided(delta, se, alpha) >= target:
            return n
    return None


# ---------------------------------------------------------------------------
# The E-001 verdict: supported / refuted
# ---------------------------------------------------------------------------


def p_supported(
    delta: float,
    sd: float,
    n: int,
    *,
    alpha: float = ALPHA_PER_CONTRAST,
    threshold: float = ACTION_THRESHOLD,
) -> float:
    """P(verdict = supported) = P(point ≥ threshold and lower limit > 0).

    With a symmetric interval, lower > 0 ⇔ point > z·SE, so the event is
    point ≥ max(threshold, z·SE).
    """
    se = se_paired(n, sd)
    bar = max(threshold, z_crit(alpha) * se)
    return 1 - _Z.cdf((bar - delta) / se)


def p_refuted(
    delta: float,
    sd: float,
    n: int,
    *,
    alpha: float = ALPHA_PER_CONTRAST,
    threshold: float = ACTION_THRESHOLD,
) -> float:
    """P(verdict = refuted) = P(upper limit < threshold)."""
    se = se_paired(n, sd)
    return _Z.cdf((threshold - z_crit(alpha) * se - delta) / se)


def n_star(
    sd: float,
    *,
    delta_design: float = DELTA_DESIGN,
    target: float = TARGET_POWER,
    alpha: float = ALPHA_PER_CONTRAST,
    threshold: float = ACTION_THRESHOLD,
) -> int | None:
    """Smallest pooled n with P(supported | delta_design) ≥ target (gate 8).

    Returns:
        The n, or None beyond ``N_LIMIT`` (including delta_design ≤ threshold,
        where the target is unreachable at any n).
    """
    for n in range(2, N_LIMIT + 1):
        if p_supported(delta_design, sd, n, alpha=alpha, threshold=threshold) >= target:
            return n
    return None


def n_noninferiority(
    sd: float,
    margin: float = ACTION_THRESHOLD,
    *,
    alpha_one_sided: float = 0.05,
    target: float = TARGET_POWER,
    true_diff: float = 0.0,
) -> int:
    """n for a one-sided non-inferiority test (H3), normal approximation."""
    z = _Z.inv_cdf(1 - alpha_one_sided) + _Z.inv_cdf(target)
    return math.ceil((z * sd / (margin - true_diff)) ** 2)


def n_max(
    cap_usd: float,
    committed_usd: float,
    cost_per_extra_question_usd: float,
    planned_n: int = PLANNED_POOLED_N,
) -> int:
    """Largest pooled S1–S4 n the cap pays for (gate 8).

    Args:
        cap_usd: v1.0 spending cap.
        committed_usd: Projected v1.0 cost after the cut order, at the planned
            n, from Phase 3 measured costs.
        cost_per_extra_question_usd: Cost of one more pooled question across
            every arm that runs on S1–S4.
        planned_n: The planned pooled n.

    Returns:
        planned_n plus the extra questions the remaining budget pays for;
        below planned_n when the committed cost already exceeds the cap.
    """
    remaining = cap_usd - committed_usd
    return planned_n + math.floor(remaining / cost_per_extra_question_usd)


@dataclass(frozen=True)
class SizingDecision:
    """Gate 8 branch for the Phase 6 dress rehearsal."""

    n_star_h1: int | None
    n_star_h2: int | None
    n_star: int | None
    n_max: int
    branch: str

    def render(self) -> str:
        """One-paragraph summary for the decision journal."""
        return (
            f"n* H1 = {self.n_star_h1}, n* H2 = {self.n_star_h2} → n* = "
            f"{self.n_star} (the larger governs); n_max = {self.n_max}; "
            f"branch: {self.branch}"
        )


def sizing_decision(
    sd_sup_h1: float, sd_sup_h2: float, n_max_value: int
) -> SizingDecision:
    """Apply gate 8 to the dress-rehearsal SD upper limits.

    Args:
        sd_sup_h1: Upper 80% limit of the SD of D(A3 − A4) on dev S1–S4.
        sd_sup_h2: Same for D(A2 − A4).
        n_max_value: n_max logged before the dress rehearsal.

    Returns:
        The registered branch: keep the plan, draw more, or row 0.
    """
    a, b = n_star(sd_sup_h1), n_star(sd_sup_h2)
    governing = None if a is None or b is None else max(a, b)
    if governing is None or governing > n_max_value:
        branch = "row 0 — descriptive (n* > n_max)"
    elif governing <= PLANNED_POOLED_N:
        branch = f"keep the plan (n = {PLANNED_POOLED_N})"
    else:
        branch = f"draw more questions up to n* = {governing}, balanced by stratum"
    return SizingDecision(a, b, governing, n_max_value, branch)


# ---------------------------------------------------------------------------
# Gate 7: the known answer (E-026 of graphrag-mtg-rules)
# ---------------------------------------------------------------------------

E026_SOURCE = "graphrag-mtg-rules@b3f293e, experiments/registry.md, E-026"
E026_DISCORDANCE = 17 / 57
"""Pooled discordance of P2's E-001; SD of a binary paired D = sqrt(discordance)."""

E026_FLOOR_TABLE: tuple[tuple[int, float, float], ...] = (
    # (n, simple contrast with n total, interaction with n per group)
    (20, 0.342, 0.484),
    (40, 0.242, 0.342),
    (57, 0.203, 0.287),
    (120, 0.140, 0.198),
    (200, 0.108, 0.153),
    (400, 0.077, 0.108),
)

E026_CONTRASTS: tuple[tuple[str, int, int, int, float, int | None], ...] = (
    # (label, treatment wins, control wins, n, published floor, published n needed)
    ("E-001 overall, B vs A", 9, 8, 57, 0.203, None),
    ("E-001 legality_1hop", 3, 1, 15, 0.395, 132),
    ("E-001 definition_1hop", 3, 1, 11, 0.461, 71),
    ("E-001 negative_temporal", 1, 0, 7, 0.578, 115),
    ("E-001 interaction_multihop", 2, 5, 22, 0.326, 126),
    ("E-001 keyword_rule_2hop", 0, 1, 2, 1.082, 10),
    ("E-018 treatment vs control", 8, 6, 20, 0.342, 235),
    ("E-018 placebo vs control", 5, 6, 20, 0.342, 937),
    ("E-020 order vs floor", 2, 1, 19, 0.351, 846),
)
"""E-026 published "n needed" is omitted (None) where the published table shows —."""

REPRODUCTION_TOLERANCE = 0.0015
"""Published floors have 3 decimals; the P2 script used z = 1.96 exactly."""
N_NEEDED_TOLERANCE = 1
"""n needed may move by one question between z = 1.96 and z = 1.95996."""


def reproduce_e026() -> list[str]:
    """Recompute E-026's published numbers and list every mismatch.

    Returns:
        Human-readable mismatches; empty when every number reproduces.
    """
    sd = math.sqrt(E026_DISCORDANCE)
    problems: list[str] = []
    for n, simple, inter in E026_FLOOR_TABLE:
        got_s, got_i = mde(n, sd), mde(n, sd, interaction=True)
        if abs(got_s - simple) > REPRODUCTION_TOLERANCE:
            problems.append(f"floor n={n}: published {simple}, got {got_s:.4f}")
        if abs(got_i - inter) > REPRODUCTION_TOLERANCE:
            problems.append(f"interaction n={n}: published {inter}, got {got_i:.4f}")
    for label, wins_t, wins_c, n, floor, needed in E026_CONTRASTS:
        got_floor = mde(n, sd)
        if abs(got_floor - floor) > REPRODUCTION_TOLERANCE:
            problems.append(f"{label}: floor published {floor}, got {got_floor:.4f}")
        d = abs(wins_t - wins_c) / n
        got_needed = n_for(d, sd)
        if needed is not None and (
            got_needed is None or abs(got_needed - needed) > N_NEEDED_TOLERANCE
        ):
            problems.append(f"{label}: n needed published {needed}, got {got_needed}")
        if d >= got_floor:
            problems.append(f"{label}: clears its floor, E-026 says none does")
    return problems


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------

SDS = (1.0, 1.5, 2.0)


def gate_tables() -> str:
    """The numbers quoted in `docs/measurability-gate.md`, recomputed."""
    out = [
        "Gate 3 — MDE (interval excludes zero), α = 0.025 two-sided, power 0.80",
        f"{'pooled n':>9}" + "".join(f"{f'SD = {s}':>12}" for s in SDS),
    ]
    for n in (240, 320, 400, 480, 640):
        out.append(
            f"{n:>9}"
            + "".join(f"{mde(n, s, alpha=ALPHA_PER_CONTRAST):>12.3f}" for s in SDS)
        )
    needed = [n_for(ACTION_THRESHOLD, s, alpha=ALPHA_PER_CONTRAST) for s in SDS]
    out.append(f"n to detect 0.25: {' / '.join(map(str, needed))}")
    per_stratum = [mde(80, s) for s in SDS]
    out.append(
        "per-stratum MDE (n = 80, α = 0.05): "
        + " / ".join(f"{x:.2f}" for x in per_stratum)
    )
    out.append(
        "H3 non-inferiority n (one-sided α = 0.05, margin 0.25): "
        + " / ".join(str(n_noninferiority(s)) for s in SDS)
    )
    out.append("\nGate 3 — P(supported) at n = 320")
    for delta in (0.25, 0.30, 0.35, 0.40):
        out.append(
            f"  true effect {delta:.2f}: "
            + " / ".join(f"{p_supported(delta, s, 320):.2f}" for s in SDS)
        )
    out.append(
        f"n* at Δ_design = {DELTA_DESIGN}: "
        + " / ".join(str(n_star(s)) for s in SDS)
    )
    out.append("\nGate 3 — P(refuted) at n = 320")
    for delta in (0.0, 0.10):
        out.append(
            f"  true effect {delta:.2f}: "
            + " / ".join(f"{p_refuted(delta, s, 320):.2f}" for s in SDS)
        )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Power and sizing for E-001.")
    parser.add_argument("--reproduce-e026", action="store_true")
    parser.add_argument("--sd-h1", type=float, help="SD_sup of D(A3 − A4)")
    parser.add_argument("--sd-h2", type=float, help="SD_sup of D(A2 − A4)")
    parser.add_argument("--n-max", type=int, help="n_max logged before Phase 6")
    args = parser.parse_args(argv)

    if args.reproduce_e026:
        problems = reproduce_e026()
        print(f"Known answer: {E026_SOURCE}")
        for line in problems:
            print("  MISMATCH", line)
        print("GATE 7 POWER SCRIPT:", "PASS" if not problems else "FAIL")
        return 0 if not problems else 1

    if args.sd_h1 is not None or args.sd_h2 is not None:
        if args.sd_h1 is None or args.sd_h2 is None or args.n_max is None:
            parser.error("--sd-h1, --sd-h2 and --n-max go together")
        print(sizing_decision(args.sd_h1, args.sd_h2, args.n_max).render())
        return 0

    print(gate_tables())
    return 0


if __name__ == "__main__":
    sys.exit(main())
