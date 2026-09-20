"""B1 - Cox proportional hazards. Nitsch's specification, and the reference point.

Linear in the covariates, proportional in the hazards. Every other model in the
benchmark is defined by which of those two assumptions it drops, so this is not a
straw man to be knocked down - it is the axis the results are read against. If it
stays competitive, plan hypothesis H7 is the finding.

Fitted through scikit-survival's Newton-Raphson on the partial likelihood with a
whisker of ridge for numerical stability; the survival curve comes from the
shared Breslow baseline in base.py so that all four PH models use one convention.
"""

from __future__ import annotations

import numpy as np
from sksurv.linear_model import CoxPHSurvivalAnalysis

from .base import FitContext, SurvivalModel, breslow_baseline, ph_survival


def to_structured(duration, event):
    y = np.empty(len(duration), dtype=[("event", "?"), ("time", "<f8")])
    y["event"] = np.asarray(event).astype(bool)
    y["time"] = np.asarray(duration, dtype="float64")
    return y


class CoxPH(SurvivalModel):
    name = "CoxPH"
    family = "classical"
    nonlinear = False
    ph = True
    budget = "cheap"

    def param_space(self, rng, n):
        return [{"alpha": 1e-6}]

    def fit(self, ctx: FitContext, params: dict) -> "CoxPH":
        self.model_ = CoxPHSurvivalAnalysis(alpha=params.get("alpha", 1e-6),
                                            n_iter=100, tol=1e-7)
        self.model_.fit(ctx.Z_train, to_structured(ctx.dur_train, ctx.ev_train))
        self._risk_train = self.model_.predict(ctx.Z_train)
        self._dur, self._ev = ctx.dur_train, ctx.ev_train
        return self

    def predict_survival(self, Z, grid, age=None):
        H0 = breslow_baseline(self._risk_train, self._dur, self._ev, grid)
        return ph_survival(self.model_.predict(Z), H0)
