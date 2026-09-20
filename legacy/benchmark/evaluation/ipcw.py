"""The censoring distribution, which every other metric in this folder needs.

Right-censoring is not missing data that can be ignored: a relationship still
alive when the panel ends is informative about survival and uninformative about
failure, and scoring it as either would bias the comparison. Inverse-probability-
of-censoring weighting restores the balance by reweighting the observations that
*are* fully observed by how likely they were to be observed at all.

Durations here are whole years, so the censoring survivor function is a discrete
Kaplan-Meier over integer times and `G(t) = P(C > t)` is a step function.

**What a duration means** (benchmark/splits/rolling_origin.py, censor_block):

    event = 1, duration = D   the relationship fails in year D after the origin
    event = 0, duration = c   it is KNOWN to survive c years: T > c

So a row censored at exactly u is alive at u, and a failure at D is observed
only when follow-up reached D, i.e. C >= D. Every metric in this folder reads
durations through `known_alive` / `observed_failure` below, so that the scores
use the same convention as the models (KM, Breslow and cloglog all keep a row
censored at t in the risk set at t). Scoring `d > u` instead silently drops
every row censored at u - on a block with one year of follow-up that is every
survivor, and the Brier score then penalises only failures and rewards the most
pessimistic model.
"""

from __future__ import annotations

import numpy as np


class CensoringKM:
    """Kaplan-Meier of the CENSORING distribution: events and censorings swapped."""

    def __init__(self, duration: np.ndarray, event: np.ndarray):
        d = np.asarray(duration, dtype="int64")
        cens = (np.asarray(event) == 0).astype("int64")     # censoring is the "event"
        times = np.arange(0, d.max() + 1)
        # A failure at D only says C >= D; whether C == D is never observed, so
        # it leaves the censoring risk set after D - 1. Keeping it in at D
        # counts it as "not censored at D" and understates the censoring hazard,
        # which biases every IPCW score beyond the first horizon downward.
        n_at_risk = np.array([(((cens == 1) & (d >= t)) |
                               ((cens == 0) & (d > t))).sum() for t in times],
                             dtype="float64")
        n_cens = np.array([((d == t) & (cens == 1)).sum() for t in times],
                          dtype="float64")
        with np.errstate(divide="ignore", invalid="ignore"):
            frac = np.where(n_at_risk > 0, 1.0 - n_cens / n_at_risk, 1.0)
        self.times = times
        self.G = np.cumprod(frac)
        # A zero weight denominator would blow up a Brier score on a handful of
        # late observations; floor it and record that the floor was used.
        self.floor = 1e-3
        self.G = np.maximum(self.G, self.floor)

    def __call__(self, t) -> np.ndarray:
        """G(t) = P(C > t), evaluated at integer times, clipped to the grid."""
        t = np.clip(np.asarray(t, dtype="int64"), 0, self.times[-1])
        return self.G[t]


def known_alive(duration: np.ndarray, event: np.ndarray, u: int) -> np.ndarray:
    """Rows whose survival past horizon u is known: T > u."""
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    return (d > u) | ((e == 0) & (d == u))


def observed_failure(duration: np.ndarray, event: np.ndarray, u: int) -> np.ndarray:
    """Rows observed to fail by horizon u: T <= u."""
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    return (d <= u) & (e == 1)
