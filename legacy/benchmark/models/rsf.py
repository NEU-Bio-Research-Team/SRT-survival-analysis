"""B4 - Random Survival Forest (Ishwaran et al. 2008).

Nonlinear and free of any proportionality assumption: each terminal node carries
its own Nelson-Aalen estimate, so two relationships' risk orderings may cross as
the years pass. On a large tabular panel with interaction-heavy economics this is
the strongest non-deep comparator, and the one the plan calls "very high"
relevance.

Its position in the 2x2 is what earns it a slot: the gap between it and
gradient-boosted Cox isolates the proportional-hazards assumption inside the tree
family, exactly as Cox-Time minus DeepSurv does inside the neural family. Two
independent readings of the same contrast is what makes plan section 16.2's
diagnostic worth running.

**The tree cap.** Both tree models train on 8,000 rows where the rest of the
benchmark gets 40,000. The binding constraint is gradient-boosted Cox, whose
partial-likelihood loss is quadratic in the sample (measured on this panel: 12s
at 4k rows, 49s at 8k, 215s at 16k). RSF is given the SAME cap even though it
could afford more, and that is deliberate: contrast C - the within-tree reading
of whether dropping proportional hazards helps - is only clean if both trees saw
the same number of rows.

The handicap cuts against the tree family as a whole, so a tree model that still
wins under it has won comfortably, and one that loses narrowly has not been shown
to lose. The contrast that the cap DOES confound - CoxPH against BoostedCox, for
nonlinearity - has a second, unconfounded reading through DeepSurv, which is also
nonlinear-and-PH and runs at the full 40,000. Read those two together.
"""

from __future__ import annotations

import numpy as np
from sksurv.ensemble import RandomSurvivalForest

from .base import FitContext, SurvivalModel
from .cox import to_structured


class RSF(SurvivalModel):
    name = "RSF"
    family = "tree"
    nonlinear = True
    ph = False
    budget = "tree"
    max_train_rows = 8000

    def param_space(self, rng, n):
        space = [{"n_estimators": ne, "min_samples_leaf": ml, "max_features": mf}
                 for ne in (100,)
                 for ml in (20, 50, 100)
                 for mf in ("sqrt",)]
        idx = rng.choice(len(space), size=min(n, len(space)), replace=False)
        return [space[i] for i in idx]

    def fit(self, ctx: FitContext, params: dict) -> "RSF":
        self.model_ = RandomSurvivalForest(
            n_estimators=params["n_estimators"],
            min_samples_leaf=params["min_samples_leaf"],
            max_features=params["max_features"],
            n_jobs=-1, random_state=ctx.seed, oob_score=False)
        self.model_.fit(ctx.Z_train, to_structured(ctx.dur_train, ctx.ev_train))
        return self

    def predict_survival(self, Z, grid, age=None):
        times = self.model_.unique_times_
        out = np.empty((len(Z), len(grid)))
        # chunked: the ensemble's per-row survival matrix is the memory peak
        for s in range(0, len(Z), 20000):
            S = self.model_.predict_survival_function(Z[s:s + 20000],
                                                      return_array=True)
            for k, u in enumerate(grid):
                j = np.searchsorted(times, u, side="right") - 1
                out[s:s + len(S), k] = 1.0 if j < 0 else S[:, j]
        return np.clip(out, 1e-12, 1.0)
