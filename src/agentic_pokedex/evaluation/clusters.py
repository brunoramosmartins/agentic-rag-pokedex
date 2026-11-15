"""Cluster resampling (E-001, amendment of 2026-09-30, item 2; PI-021).

Questions that share a cluster (a withheld pair, a move, an evolution line,
…; E-001's keys) are not independent, so intervals resample **clusters within
each stratum** rather than questions. This module holds the stratified cluster
bootstrap; E-004 uses it for the proxy SD of D, and Phase 6 for every interval.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """One question's value, with its stratum and cluster."""

    stratum: str
    cluster: str
    value: float


def sd(values: Sequence[float]) -> float:
    """Sample standard deviation (n − 1); 0 for fewer than two values."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))


def grouped(items: Sequence[Item]) -> dict[str, dict[str, list[float]]]:
    """Values by stratum, then by cluster."""
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        out[it.stratum][it.cluster].append(it.value)
    return {s: dict(c) for s, c in out.items()}


def resample(
    groups: Mapping[str, Mapping[str, Sequence[float]]], rng: random.Random
) -> list[float]:
    """One stratified cluster-bootstrap replicate: within each stratum, as many
    clusters as it has, drawn with replacement; every value of a drawn cluster
    enters."""
    out: list[float] = []
    for stratum in sorted(groups):
        clusters = sorted(groups[stratum])
        for _ in clusters:
            out.extend(groups[stratum][rng.choice(clusters)])
    return out


def bootstrap_interval(
    items: Sequence[Item], stat: Callable[[Sequence[float]], float], *,
    level: float = 0.80, replicates: int = 2_000, seed: int = 0,
) -> tuple[float, float, float]:
    """Statistic with its percentile interval under the stratified cluster
    bootstrap.

    Returns:
        (statistic on the sample, lower limit, upper limit).
    """
    groups = grouped(items)
    rng = random.Random(seed)
    draws = sorted(stat(resample(groups, rng)) for _ in range(replicates))
    tail = (1 - level) / 2
    lo = draws[int(math.floor(tail * (replicates - 1)))]
    hi = draws[int(math.ceil((1 - tail) * (replicates - 1)))]
    return stat([it.value for it in items]), lo, hi
