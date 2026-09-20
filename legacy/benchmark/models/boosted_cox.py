"""B5 - gradient-boosted Cox. The model that splits the difference.

Its risk function is a sum of regression trees, so it is thoroughly nonlinear -
but the loss is Cox's partial likelihood, so the hazards it produces are still
proportional. That combination is the reason it is in the benchmark:

    CoxPH -> BoostedCox   prices NONLINEARITY, proportionality held fixed
    BoostedCox -> RSF     prices dropping PROPORTIONALITY, nonlinearity held fixed

Without it, a win for RSF over Cox would be two changes at once and attributable
to neither. Plan section 4.4 puts the point plainly: if boosting beats Cox and a
non-PH model adds little on top of boosting, the story is nonlinear covariate
structure, not time-varying risk ordering.

Because the loss is Cox's, the survival curve comes from the same shared Breslow
baseline as CoxPH, CoxNet and DeepSurv - one convention across the PH family.
"""

from __future__ import annotations

import numpy as np
from sksurv.ensemble import GradientBoostingSurvivalAnalysis

from .base import FitContext, SurvivalModel, breslow_baseline, ph_survival
from .cox import to_structured


class BoostedCox(SurvivalModel):
    name = "BoostedCox"
    family = "tree"
    nonlinear = True
    ph = True
    budget = "tree"
    max_train_rows = 8000   # see the tree-cap note in rsf.py

    def param_space(self, rng, n):
        space = [{"n_estimators": ne, "learning_rate": lr, "max_depth": md,
                  "subsample": ss}
                 for ne in (100,)
                 for lr in (0.1,)
                 for md in (2, 3)
                 for ss in (0.7,)]
        idx = rng.choice(len(space), size=min(n, len(space)), replace=False)
        return [space[i] for i in idx]

    def fit(self, ctx: FitContext, params: dict) -> "BoostedCox":
        self.model_ = GradientBoostingSurvivalAnalysis(
            loss="coxph", n_estimators=params["n_estimators"],
            learning_rate=params["learning_rate"], max_depth=params["max_depth"],
            subsample=params["subsample"], random_state=ctx.seed)
        self.model_.fit(ctx.Z_train, to_structured(ctx.dur_train, ctx.ev_train))
        self._risk_train = self.model_.predict(ctx.Z_train)
        self._dur, self._ev = ctx.dur_train, ctx.ev_train
        return self

    def predict_survival(self, Z, grid, age=None):
        H0 = breslow_baseline(self._risk_train, self._dur, self._ev, grid)
        return ph_survival(self.model_.predict(Z), H0)
