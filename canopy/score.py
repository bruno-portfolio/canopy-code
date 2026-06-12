"""Composite health score per module.

Replaces raw Maintainability Index as the primary health signal. The score
starts at 100 and loses points for named, auditable factors — each factor
is surfaced in the HTML tooltip so every lost point has a traceable cause.
Calibration follows the classic McCabe CC>10 threshold and CodeScene-style
hotspot prioritisation (churn x unhealthiness).
"""

from __future__ import annotations

import math

from canopy.models import ScoreFactor

_COMPLEXITY_SPREAD_CAP = 40.0
_WORST_FUNCTION_CAP = 20.0
_DEAD_RATIO_CAP = 15.0

_GRADES = (
    (90.0, "A"),
    (80.0, "B"),
    (70.0, "C"),
    (60.0, "D"),
)


def score_factors(
    *,
    funcs: int,
    n_cc_over: int,
    cc_max: int,
    dead: int,
    coverage: float | None,
    cc_threshold: int = 10,
    complexity_spread: float = 1.5,
    worst_function: float = 1.5,
    dead_ratio: float = 0.75,
    coverage_weight: float = 25.0,
) -> tuple[ScoreFactor, ...]:
    factors: list[ScoreFactor] = []

    if funcs > 0 and n_cc_over > 0:
        pct = 100.0 * n_cc_over / funcs
        penalty = min(_COMPLEXITY_SPREAD_CAP, pct * complexity_spread)
        factors.append(
            ScoreFactor(
                label=f"{n_cc_over}/{funcs} functions CC>{cc_threshold}",
                penalty=round(penalty, 1),
            )
        )

    if cc_max > cc_threshold:
        penalty = min(_WORST_FUNCTION_CAP, (cc_max - cc_threshold) * worst_function)
        factors.append(ScoreFactor(label=f"worst function CC {cc_max}", penalty=round(penalty, 1)))

    if funcs > 0 and dead > 0:
        pct = 100.0 * dead / funcs
        penalty = min(_DEAD_RATIO_CAP, pct * dead_ratio)
        factors.append(ScoreFactor(label=f"{dead} dead symbols", penalty=round(penalty, 1)))

    if coverage is not None and coverage < 1.0:
        penalty = (1.0 - coverage) * coverage_weight
        factors.append(ScoreFactor(label=f"coverage {coverage:.0%}", penalty=round(penalty, 1)))

    return tuple(factors)


def compute_score(factors: tuple[ScoreFactor, ...]) -> float:
    return round(max(0.0, 100.0 - sum(f.penalty for f in factors)), 1)


def risk_index(churn: int, churn_max: int, score: float) -> float:
    """Hotspot index: recent change frequency x unhealthiness (0..1).

    High churn on healthy code is normal activity and scores near zero;
    high churn on unhealthy code is where defects cluster. Churn is
    square-root compressed: being actively changed matters more than how
    often, and a single high-churn healthy module must not flatten the
    normalisation for everyone else.
    """
    if churn_max <= 0 or churn <= 0:
        return 0.0
    return round(math.sqrt(churn / churn_max) * (1.0 - score / 100.0), 3)


def grade(score: float) -> str:
    for threshold, letter in _GRADES:
        if score >= threshold:
            return letter
    return "F"
