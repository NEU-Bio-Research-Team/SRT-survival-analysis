"""D05 boosted discrete hazard and L06 gradient-boosted Cox, both on XGBoost.

L06 uses XGBoost's `survival:cox` objective (Breslow partial likelihood,
O(n log n) per round). Legacy used sksurv's GradientBoostingSurvivalAnalysis,
whose cost grew quadratically with rows and forced an 8,000-row cap; here both
tree models run on `full_eligible`, as plan §2 requires.

Boosting rounds are chosen by early stopping on the inner holdout (base.py).
Row/column subsampling make both models stochastic: they get 3 seeds at refit.
"""

from __future__ import annotations

import numpy as np
import xgboost as xgb

from stage2_benchmark import paths

from .base import FitData, Model, breslow_H0, inner_split, ph_survival

MAX_ROUNDS = 2000
EARLY = 50


def _space(trial):
    return {
        "max_depth": trial.suggest_int("max_depth", 2, 8),
        "eta": trial.suggest_float("eta", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
        "min_child_weight": trial.suggest_float("min_child_weight", 1, 100, log=True),
        "lambda": trial.suggest_float("lambda", 1e-3, 30, log=True),
        "alpha": trial.suggest_float("alpha", 1e-3, 10, log=True),
    }


class _XGB(Model):
    family, nonlinear, stochastic, tuning = "tree", True, True, "optuna"
    uses_inner_holdout = True
    objective = None
    eval_metric = None

    def suggest(self, trial):
        return _space(trial)

    def _labels(self, data):
        raise NotImplementedError

    def fit(self, data: FitData, params, seed=1):
        tr, ho = inner_split(data.relation, seed=11)
        lab = self._labels(data)
        dtr = xgb.DMatrix(data.Z[tr], label=lab[tr])
        dho = xgb.DMatrix(data.Z[ho], label=lab[ho])
        p = dict(params, objective=self.objective, eval_metric=self.eval_metric,
                 tree_method="hist", nthread=paths.N_THREADS, seed=seed,
                 verbosity=0)
        self.bst_ = xgb.train(p, dtr, MAX_ROUNDS, evals=[(dho, "ho")],
                              early_stopping_rounds=EARLY, verbose_eval=False)
        self.best_iter_ = int(self.bst_.best_iteration)
        return self

    def _margin(self, Z):
        return self.bst_.predict(xgb.DMatrix(Z), output_margin=True,
                                 iteration_range=(0, self.best_iter_ + 1))

    def info(self):
        return {"best_iteration": self.best_iter_}


class BoostedHazard(_XGB):
    id, name, task, ph = "D05", "BoostedHazard", "D", False
    objective, eval_metric = "binary:logistic", "logloss"

    def _labels(self, data):
        return data.y.astype("float32")

    def predict_proba(self, Z, age):
        m = self._margin(Z)
        return 1.0 / (1.0 + np.exp(-np.clip(m, -30, 30)))


class GBCox(_XGB):
    id, name, task, ph = "L06", "GBCox", "L", True
    objective, eval_metric = "survival:cox", "cox-nloglik"

    def _labels(self, data):
        d = data.duration.astype("float32")
        return np.where(data.event == 1, d, -d)

    def fit(self, data, params, seed=1):
        super().fit(data, params, seed)
        risk = self._margin(data.Z)
        self.H0_ = breslow_H0(risk, data.duration, data.event, 5)
        return self

    def predict_survival(self, Z, grid, age):
        return ph_survival(self._margin(Z), self.H0_, grid)
