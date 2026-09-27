"""L task, non-neural: KM reference, L01 CoxPH, L02 CoxNet, L03/L04 AFT, L05 RSF.

The Cox family shares one Breslow baseline estimator (base.breslow_H0) so the
PH models differ only in their risk score. CoxPH is fit with Efron ties;
sksurv's CoxNet supports Breslow ties only (recorded in `info`).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from stage2_benchmark import paths

from .base import FitData, Model, breslow_H0, monotone, ph_survival


def _structured(d, e):
    from sksurv.util import Surv
    return Surv.from_arrays(event=np.asarray(e).astype(bool),
                            time=np.asarray(d, dtype="float64"))


class KaplanMeier(Model):
    id, name, task, family = "L00", "KM", "L", "reference"

    def fit(self, data: FitData, params, seed=1):
        d, e = data.duration.astype(int), data.event.astype(int)
        s, self.S_ = 1.0, {}
        for t in range(1, 6):
            at = (d >= t).sum()
            if at:
                s *= 1 - ((d == t) & (e == 1)).sum() / at
            self.S_[t] = s
        return self

    def predict_survival(self, Z, grid, age):
        return np.tile([self.S_[u] for u in grid], (len(Z), 1))


class CoxPH(Model):
    id, name, task = "L01", "CoxPH", "L"
    ph = True

    def fit(self, data: FitData, params, seed=1):
        from sksurv.linear_model import CoxPHSurvivalAnalysis
        y = _structured(data.duration, data.event)
        Z = data.Z.astype("float64")
        self.alpha_ = 0.0
        for a in (0.0, 1e-4, 1e-2):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.m_ = CoxPHSurvivalAnalysis(alpha=a, ties="efron", n_iter=200).fit(Z, y)
                if np.isfinite(self.m_.coef_).all():
                    self.alpha_ = a
                    break
            except Exception:  # singular Hessian: add the smallest ridge that works
                continue
        self.H0_ = breslow_H0(self.m_.predict(Z), data.duration, data.event, 5)
        return self

    def predict_survival(self, Z, grid, age):
        return ph_survival(self.m_.predict(Z.astype("float64")), self.H0_, grid)

    def info(self):
        return {"ties": "efron", "ridge_fallback": self.alpha_}


class CoxNet(Model):
    """Elastic-net Cox. Tuning grid = l1_ratio x points on sksurv's automatic
    alpha path; the path is fitted once per l1_ratio and cached."""
    id, name, task = "L02", "CoxNet", "L"
    tuning = "grid"
    N_ALPHAS = 30
    ALPHA_IDX = list(range(0, 30, 3)) + [29]
    _cache: dict = {}

    def grid(self):
        return [{"l1_ratio": l1, "alpha_idx": i}
                for l1 in (0.1, 0.5, 0.9) for i in self.ALPHA_IDX]

    def fit(self, data: FitData, params, seed=1):
        from sksurv.linear_model import CoxnetSurvivalAnalysis
        key = (id(data.Z), data.Z.shape, params["l1_ratio"])
        if key not in CoxNet._cache:
            CoxNet._cache.clear()
            m = CoxnetSurvivalAnalysis(l1_ratio=params["l1_ratio"], n_alphas=self.N_ALPHAS,
                                       alpha_min_ratio=1e-3, normalize=False,
                                       max_iter=100000, tol=1e-7, fit_baseline_model=False)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m.fit(data.Z.astype("float64"), _structured(data.duration, data.event))
            CoxNet._cache[key] = m
        m = CoxNet._cache[key]
        i = min(params["alpha_idx"], len(m.alphas_) - 1)
        self.coef_ = m.coef_[:, i].copy()
        self.alpha_ = float(m.alphas_[i])
        risk = data.Z.astype("float64") @ self.coef_
        self.H0_ = breslow_H0(risk, data.duration, data.event, 5)
        return self

    def predict_survival(self, Z, grid, age):
        return ph_survival(Z.astype("float64") @ self.coef_, self.H0_, grid)

    def info(self):
        return {"ties": "breslow", "alpha": self.alpha_,
                "n_nonzero": int((np.abs(self.coef_) > 0).sum())}


class _AFT(Model):
    task, ph = "L", False
    tuning = "grid"
    fitter = None

    def grid(self):
        return [{"penalizer": p} for p in (0.0, 0.01, 0.1)]

    def _df(self, Z):
        return pd.DataFrame(Z.astype("float64"), columns=[f"x{j}" for j in range(Z.shape[1])])

    def fit(self, data: FitData, params, seed=1):
        import lifelines
        cls = getattr(lifelines, self.fitter)
        df = self._df(data.Z)
        df["T"] = data.duration.astype("float64")
        df["E"] = data.event.astype(int)
        self.penalizer_ = params["penalizer"]
        last = None
        for pen in (params["penalizer"], max(params["penalizer"], 1e-3), 0.05):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.m_ = cls(penalizer=pen).fit(df, "T", "E")
                self.penalizer_ = pen
                return self
            except Exception as ex:  # convergence failure: retry with a ridge
                last = ex
        raise RuntimeError(f"{self.name} failed to converge: {last}")

    def predict_survival(self, Z, grid, age):
        out = []
        for s in range(0, len(Z), 20000):
            sf = self.m_.predict_survival_function(self._df(Z[s:s + 20000]), times=grid)
            out.append(sf.to_numpy().T)
        return monotone(np.vstack(out))

    def info(self):
        return {"penalizer_used": self.penalizer_}


class WeibullAFT(_AFT):
    id, name, fitter = "L03", "WeibullAFT", "WeibullAFTFitter"
    ph = True   # Weibull AFT is also PH


class LogNormalAFT(_AFT):
    id, name, fitter = "L04", "LogNormalAFT", "LogNormalAFTFitter"


class RSF(Model):
    id, name, task = "L05", "RSF", "L"
    family, nonlinear, ph, stochastic, tuning = "tree", True, False, True, "optuna"

    # Pilot 0.6: 200 trees x min_leaf 5 on 58k rows took 308 s per trial with
    # sksurv's log-rank splitter. Rows stay full_eligible; the space is narrowed
    # instead (100 trees, leaf >= 20, max_features in {sqrt, 0.2}, each tree on a
    # 50% bootstrap draw): ~60 s per trial (max_features 0.5 alone cost 208 s). Recorded in reports/stage0/0.6_pilot.md.
    def suggest(self, trial):
        return {"n_estimators": 100,
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 20, 300, log=True),
                "max_features": trial.suggest_categorical("max_features",
                                                          ["sqrt", 0.2]),
                "max_depth": trial.suggest_categorical("max_depth", [None, 8, 12, 20]),
                "max_samples": 0.5}

    def fit(self, data: FitData, params, seed=1):
        from sksurv.ensemble import RandomSurvivalForest
        self.m_ = RandomSurvivalForest(n_jobs=paths.N_THREADS, random_state=seed,
                                       low_memory=False, **params)
        self.m_.fit(data.Z, _structured(data.duration, data.event))
        return self

    def predict_survival(self, Z, grid, age):
        times = self.m_.unique_times_
        out = np.empty((len(Z), len(grid)))
        for s in range(0, len(Z), 10000):
            S = self.m_.predict_survival_function(Z[s:s + 10000], return_array=True)
            for k, u in enumerate(grid):
                j = np.searchsorted(times, u + 1e-9, side="right") - 1
                out[s:s + len(S), k] = 1.0 if j < 0 else S[:, j]
        return monotone(out)
