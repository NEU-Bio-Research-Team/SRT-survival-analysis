"""B0 - Kaplan-Meier. The null model, and the one that is hardest to beat badly.

It ignores every covariate and returns the training block's marginal survival
curve to every relationship alike. Its whole job is to set the price of
admission: a covariate model that cannot beat this has not learned anything about
which relationship dies, only about how many do.
"""

from __future__ import annotations

import numpy as np

from .base import FitContext, SurvivalModel


class KaplanMeier(SurvivalModel):
    name = "KM"
    family = "null"
    nonlinear = False
    ph = None
    budget = "cheap"

    def fit(self, ctx: FitContext, params: dict) -> "KaplanMeier":
        d = np.asarray(ctx.dur_train, dtype="int64")
        e = np.asarray(ctx.ev_train, dtype="int64")
        tmax = int(d.max())
        s, curve = 1.0, np.ones(tmax + 1)
        for t in range(1, tmax + 1):
            at_risk = (d >= t).sum()
            if at_risk == 0:
                break
            s *= 1.0 - ((d == t) & (e == 1)).sum() / at_risk
            curve[t] = s
        self.curve_ = curve
        return self

    def predict_survival(self, Z: np.ndarray, grid: list[int],
                         age: np.ndarray = None) -> np.ndarray:
        idx = np.clip(np.asarray(grid, dtype="int64"), 0, len(self.curve_) - 1)
        return np.tile(self.curve_[idx], (len(Z), 1))
