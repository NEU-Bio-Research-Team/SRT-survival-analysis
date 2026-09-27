"""D task (one-year exit risk): reference, D01-D04.

Design for D01-D04: free age dummies (1..10+, the grouped-time baseline of
Prentice-Gloeckler) + the preprocessed features. No intercept (the dummies
span it). Ridge penalties are scaled by n and never touch the baseline.
"""

from __future__ import annotations

import numpy as np

from stage2_benchmark.inference.glm import fit_glm, predict

from .base import MAX_AGE_DUMMY, FitData, Model, age_dummies


class AgeOnlyHazard(Model):
    """Reference: empirical one-year exit rate by observed age (1..10+)."""
    id, name, task, family = "D00", "AgeOnly", "D", "reference"

    def fit(self, data: FitData, params, seed=1):
        a = np.clip(data.age, 1, MAX_AGE_DUMMY)
        self.rate_ = np.array([data.y[a == k].mean() if (a == k).any() else data.y.mean()
                               for k in range(1, MAX_AGE_DUMMY + 1)])
        return self

    def predict_proba(self, Z, age):
        return self.rate_[np.clip(np.asarray(age), 1, MAX_AGE_DUMMY) - 1]


def _cloglog_init(y, age, link):
    a = np.clip(age, 1, MAX_AGE_DUMMY)
    r = np.array([np.clip(y[a == k].mean() if (a == k).any() else y.mean(), 1e-4, 1 - 1e-4)
                  for k in range(1, MAX_AGE_DUMMY + 1)])
    if link == "cloglog":
        return np.log(-np.log1p(-r))
    if link == "logit":
        return np.log(r / (1 - r))
    from scipy.special import ndtri
    return ndtri(r)


class LinkGLM(Model):
    task, family = "D", "linear"
    tuning = "grid"
    link = "cloglog"

    def grid(self):
        return [{"ridge": r} for r in (0.0, 1e-3, 1e-2)]

    def _design(self, Z, age):
        return np.hstack([age_dummies(age), np.asarray(Z, dtype="float64")])

    def fit(self, data: FitData, params, seed=1):
        X = self._design(data.Z, data.age)
        n, k = X.shape
        pen = np.r_[np.zeros(MAX_AGE_DUMMY),
                    np.full(k - MAX_AGE_DUMMY, params.get("ridge", 0.0) * n)]
        pen[MAX_AGE_DUMMY:] += 1e-8 * n          # numerical floor only
        b0 = np.r_[_cloglog_init(data.y, data.age, self.link), np.zeros(k - MAX_AGE_DUMMY)]
        self.fit_ = fit_glm(X, data.y, self.link, penalty=pen, beta0=b0)
        return self

    def predict_proba(self, Z, age):
        return predict(self._design(Z, age), self.fit_["beta"], self.link)

    def info(self):
        return {"converged": bool(self.fit_["converged"]), "iter": self.fit_["iter"]}


class Cloglog(LinkGLM):
    id, name, link, ph = "D01", "Cloglog", "cloglog", True


class Logit(LinkGLM):
    id, name, link, ph = "D02", "Logit", "logit", False


class Probit(LinkGLM):
    id, name, link, ph = "D03", "Probit", "probit", False


# ------------------------------------------------------------ D04
def rcs_basis(x, knots):
    """Restricted cubic spline basis (Harrell), len(knots)-1 columns incl. x."""
    k = np.asarray(knots, dtype="float64")
    K = len(k)
    norm = (k[-1] - k[0]) ** 2 if k[-1] > k[0] else 1.0
    cols = [x]
    for j in range(K - 2):
        t = (np.maximum(x - k[j], 0) ** 3
             - np.maximum(x - k[-2], 0) ** 3 * (k[-1] - k[j]) / (k[-1] - k[-2])
             + np.maximum(x - k[-1], 0) ** 3 * (k[-2] - k[j]) / (k[-1] - k[-2]))
        cols.append(t / norm)
    return np.column_stack(cols)


INTERACT_WITH_AGE = ["log_value", "log_value_lag", "vn_market_share_lag1",
                     "tariff_applied_lag", "pref_margin_lag"]


class FlexibleCloglog(LinkGLM):
    """Spline covariates (df in {3, 5}) and optional X x log(age) for five R/P
    variables. Linear in parameters, so still a grouped-PH model unless the
    interactions are switched on (then effects vary with spell age)."""
    id, name, link = "D04", "FlexCloglog", "cloglog"
    nonlinear, ph = True, False

    def grid(self):
        return [{"df": df, "age_x": ax, "ridge": 1e-4}
                for df in (3, 5) for ax in (False, True)]

    def _basis(self, Z, age):
        Z = np.asarray(Z, dtype="float64")
        parts = []
        for j in range(Z.shape[1]):
            if j in self.knots_:
                parts.append(rcs_basis(Z[:, j], self.knots_[j]))
            else:
                parts.append(Z[:, j:j + 1])
        if self.age_x_:
            la = np.log(np.clip(np.asarray(age, dtype="float64"), 1, None))
            la = (la - self.la_mean_)
            for j in self.ix_:
                parts.append((Z[:, j] * la)[:, None])
        return np.hstack(parts)

    def _design(self, Z, age):
        return np.hstack([age_dummies(age), self._basis(Z, age)])

    def fit(self, data: FitData, params, seed=1):
        Z = np.asarray(data.Z, dtype="float64")
        nk = params["df"] + 1
        self.knots_ = {}
        for j, name in enumerate(data.names):
            if name.endswith("_isna"):
                continue
            x = Z[:, j]
            if len(np.unique(x[: min(len(x), 20000)])) <= 10:
                continue
            q = np.quantile(x, np.linspace(0.05, 0.95, nk))
            if len(np.unique(q)) == nk:
                self.knots_[j] = q
        self.age_x_ = params["age_x"]
        self.ix_ = [data.names.index(c) for c in INTERACT_WITH_AGE if c in data.names]
        self.la_mean_ = float(np.mean(np.log(np.clip(data.age, 1, None))))
        return super().fit(data, {"ridge": params.get("ridge", 1e-4)}, seed)

    def info(self):
        d = super().info()
        d.update(n_spline_vars=len(self.knots_), age_x=self.age_x_)
        return d
