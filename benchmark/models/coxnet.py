"""B2 - Elastic-Net penalised Cox.

This model exists to answer one question and it is a question about the OTHER
models: when a flexible learner beats plain Cox on a panel with eighty-odd
correlated columns, is the gain nonlinearity, or is it merely shrinkage and
variable selection that Cox never got? CoxNet is linear and proportional, so
whatever it recovers over CoxPH is regularisation and nothing else. Only the gap
above CoxNet is evidence for representation learning.
"""

from __future__ import annotations

import numpy as np
from sksurv.linear_model import CoxnetSurvivalAnalysis

from .base import FitContext, SurvivalModel, breslow_baseline, ph_survival
from .cox import to_structured


class CoxNet(SurvivalModel):
    name = "CoxNet"
    family = "classical"
    nonlinear = False
    ph = True
    budget = "cheap"

    def param_space(self, rng, n):
        l1 = [0.1, 0.5, 0.9, 1.0]
        alphas = [0.001, 0.01, 0.05]
        space = [{"l1_ratio": a, "alpha": b} for a in l1 for b in alphas]
        idx = rng.choice(len(space), size=min(n, len(space)), replace=False)
        return [space[i] for i in idx]

    def fit(self, ctx: FitContext, params: dict) -> "CoxNet":
        a = params["alpha"]
        self.model_ = CoxnetSurvivalAnalysis(
            l1_ratio=params["l1_ratio"], alphas=[a], fit_baseline_model=False,
            max_iter=20000, tol=1e-6, normalize=False)
        self.model_.fit(ctx.Z_train.astype("float64"),
                        to_structured(ctx.dur_train, ctx.ev_train))
        self._risk_train = self.model_.predict(ctx.Z_train.astype("float64"))
        self._dur, self._ev = ctx.dur_train, ctx.ev_train
        return self

    def predict_survival(self, Z, grid, age=None):
        H0 = breslow_baseline(self._risk_train, self._dur, self._ev, grid)
        return ph_survival(self.model_.predict(Z.astype("float64")), H0)
