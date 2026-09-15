"""The censoring distribution, which every other metric in this folder needs.

Right-censoring is not missing data that can be ignored: a relationship still
alive when the panel ends is informative about survival and uninformative about
failure, and scoring it as either would bias the comparison. Inverse-probability-
of-censoring weighting restores the balance by reweighting the observations that
*are* fully observed by how likely they were to be observed at all.

Durations here are whole years, so the censoring survivor function is a discrete
Kaplan-Meier over integer times and `G(t) = P(C > t)` is a step function.
"""

from __future__ import annotations

import numpy as np


class CensoringKM:
    """Kaplan-Meier of the CENSORING distribution: events and censorings swapped."""

    def __init__(self, duration: np.ndarray, event: np.ndarray):
        d = np.asarray(duration, dtype="int64")
        cens = (np.asarray(event) == 0).astype("int64")     # censoring is the "event"
        times = np.arange(0, d.max() + 1)
        n_at_risk = np.array([(d >= t).sum() for t in times], dtype="float64")
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
