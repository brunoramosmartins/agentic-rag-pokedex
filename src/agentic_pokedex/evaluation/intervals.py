"""Confidence intervals for proportions reported as N-of-M."""

from __future__ import annotations

import math
from statistics import NormalDist


def wilson(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials.

    Args:
        k: Successes.
        n: Trials.
        confidence: Two-sided confidence level.

    Returns:
        ``(low, high)``; ``(0.0, 1.0)`` when ``n`` is 0.
    """
    if n == 0:
        return 0.0, 1.0
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)
