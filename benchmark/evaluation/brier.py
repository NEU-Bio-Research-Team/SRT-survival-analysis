"""IPCW Brier score and the Integrated Brier Score - the primary metric.

Plan section 14.1 makes IBS primary rather than a concordance index, and the
reason is what Stage 2 does with the output: it multiplies a survival PROBABILITY
by a trade value. A model that ranks relationships perfectly but predicts 0.9
where the truth is 0.6 ruins that calculation while scoring a flawless C-index.
The Brier score is a proper scoring rule, so it is minimised only by the true
probability, and it penalises exactly the failure a ranking metric forgives.

At horizon u, with G the censoring survivor function:

    BS(u) = 1/n * sum_i [ 1{T_i <= u, d_i = 1} * (0 - S_i(u))^2 / G(T_i - 1)
                        + 1{T_i >  u}          * (1 - S_i(u))^2 / G(u) ]

Subjects censored before u contribute nothing: their outcome at u is genuinely
unknown, and the weights above are what redistributes their mass onto the
observations that survived to speak for them.
"""

from __future__ import annotations

import numpy as np

from .ipcw import CensoringKM


def brier_at(surv: np.ndarray, duration: np.ndarray, event: np.ndarray,
             u: int, grid: list[int], G: CensoringKM | None = None) -> float:
    """Brier score at horizon u. `surv` is (n, len(grid)) of S(u | X)."""
    if u not in grid:
        raise ValueError(f"horizon {u} not on the prediction grid {grid}")
    S = np.clip(surv[:, grid.index(u)].astype("float64"), 0.0, 1.0)
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    G = G or CensoringKM(d, e)

    failed = (d <= u) & (e == 1)
    alive = d > u
    if not (failed.any() or alive.any()):
        return float("nan")
    w_fail = np.where(failed, 1.0 / G(d - 1), 0.0)
    w_alive = np.where(alive, 1.0 / G(u), 0.0)
    loss = w_fail * (0.0 - S) ** 2 + w_alive * (1.0 - S) ** 2
    return float(loss.sum() / len(S))


def ibs(surv: np.ndarray, duration: np.ndarray, event: np.ndarray,
        integrate_over: list[int], grid: list[int]) -> float:
    """Integrated Brier Score over the requested horizons (trapezoid in u).

    Returns NaN when any horizon on the requested grid is unobservable in this
    block - which is the honest answer for a five-year score on a test window
    that has three years of follow-up, and the reason the primary grid is 1-3.
    """
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    G = CensoringKM(d, e)
    vals = [brier_at(surv, d, e, u, grid, G) for u in integrate_over]
    if any(not np.isfinite(v) for v in vals):
        return float("nan")
    if len(vals) == 1:
        return float(vals[0])
    us = np.asarray(integrate_over, dtype="float64")
    return float(np.trapezoid(vals, us) / (us[-1] - us[0]))
