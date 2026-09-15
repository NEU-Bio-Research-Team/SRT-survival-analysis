"""B3 - discrete-time proportional hazards with a complementary log-log link.

The trade-survival literature's own model (Lawless & Studnicka 2024), and the
right one for this panel on grounds that have nothing to do with taste. Durations
here are whole years, so ties are not incidental but universal, and Cox's partial
likelihood then rests entirely on a tie-breaking approximation. The grouped-data
model (Prentice-Gloeckner) makes the same proportional-hazards assumption about
data that is genuinely interval-censored, which is what an annual customs filing
is. Its coefficients read as log hazard ratios exactly as Cox's do.

    h(a, x) = 1 - exp(-exp( gamma_a + x'beta ))

with `gamma_a` a free dummy per year of relationship age, collapsed at 10+. The
baseline is therefore unrestricted, which matters when more than half the mass
sits at age one and no smooth function of age would fit it.

The training data is the person-period panel itself: each prediction origin is
one Bernoulli trial for "does this relationship fail in the coming year", which
is precisely the panel's `event` flag. Survival over several years is the product
of the fitted one-year hazards, walking the age dummy forward while the
covariates are held at their origin values - the standard landmark convention,
and the honest one, since the future covariates are not in F_t either.

**Shared gamma frailty.** Fitted on one-year outcomes and then multiplied out
over several years, a hazard model without unobserved heterogeneity
systematically over-predicts long-run mortality, and on this panel it does so
badly: the population hazard falls from 15% in the first year to 6% in the
second, which is mostly the frail dying first rather than any individual
becoming safer. Lawless & Studnicka answer this with random effects, and the
cloglog link makes the same correction available in closed form. With a
multiplicative frailty nu ~ Gamma(mean 1, variance theta),

    S(u | x) = (1 + theta * H(u | x)) ^ (-1/theta),
    H(u | x) = sum_{k=0}^{u-1} exp( gamma_{a+k} + x'beta ),

which collapses to exp(-H) as theta -> 0. Beta is estimated first from the
one-year likelihood; theta is then profiled on the training block's observed
remaining lifetimes over a grid. That two-stage estimator is not full maximum
likelihood and is labelled as such - what it buys is a classical baseline whose
probabilities are usable at three and five years, which is the horizon Stage 2
needs and the horizon a straw-man baseline would fail at.

`enhanced=True` is the theory-enhanced variant of plan section 16.1: splines on
the two variables Nitsch and Lawless-Studnicka argue are nonlinear, plus their
experience x diversification interactions. It exists so that the classical
baseline in this benchmark is the best classical model, not the weakest one.
"""

from __future__ import annotations

import numpy as np

from .base import FitContext, SurvivalModel

MAX_AGE_DUMMY = 10


class DiscreteCloglog(SurvivalModel):
    name = "Cloglog"
    family = "classical"
    nonlinear = False
    ph = True
    budget = "cheap"

    def __init__(self, enhanced: bool = False, spline_cols: list[str] | None = None,
                 interactions: list[tuple[str, str]] | None = None,
                 frailty: bool = True):
        self.enhanced = enhanced
        self.frailty = frailty
        self.spline_cols = spline_cols or []
        self.interactions = interactions or []
        if enhanced:
            self.name = "Cloglog-theory"
            self.nonlinear = True

    # ---------------------------------------------------------------- design
    def _age_dummies(self, age: np.ndarray) -> np.ndarray:
        a = np.clip(np.asarray(age, dtype="int64"), 1, MAX_AGE_DUMMY)
        D = np.zeros((len(a), MAX_AGE_DUMMY), dtype="float64")
        D[np.arange(len(a)), a - 1] = 1.0
        return D

    def _extra(self, Z: np.ndarray) -> np.ndarray:
        """Splines and interactions, for the theory-enhanced variant only."""
        if not self.enhanced:
            return np.empty((len(Z), 0))
        cols = []
        for j in self._spline_idx:
            x = Z[:, j]
            # a restricted quadratic-plus-hinge basis: enough curvature to test
            # the literature's threshold claims without a knot-selection ritual
            cols += [x ** 2, np.maximum(x - self._knots[j][0], 0.0),
                     np.maximum(x - self._knots[j][1], 0.0)]
        for a, b in self._inter_idx:
            cols.append(Z[:, a] * Z[:, b])
        return np.column_stack(cols) if cols else np.empty((len(Z), 0))

    def _design(self, Z: np.ndarray, age: np.ndarray) -> np.ndarray:
        return np.hstack([self._age_dummies(age), Z.astype("float64"),
                          self._extra(Z)])

    # ------------------------------------------------------------------ fit
    def param_space(self, rng, n):
        return [{"ridge": r} for r in (1e-6, 1e-3, 1e-1)][:max(1, min(n, 3))]

    def fit(self, ctx: FitContext, params: dict) -> "DiscreteCloglog":
        Z = ctx.Z_train.astype("float64")
        if self.enhanced:
            idx = {nm: i for i, nm in enumerate(ctx.names)}
            self._spline_idx = [idx[c] for c in self.spline_cols if c in idx]
            self._knots = {j: tuple(np.percentile(Z[:, j], [33, 67]))
                           for j in self._spline_idx}
            self._inter_idx = [(idx[a], idx[b]) for a, b in self.interactions
                               if a in idx and b in idx]
        X = self._design(Z, ctx.age_train)
        # the one-year failure indicator: remaining lifetime of exactly one year,
        # ending in a death rather than in the end of the observation window
        y = ((np.asarray(ctx.dur_train) == 1) &
             (np.asarray(ctx.ev_train) == 1)).astype("float64")
        self.beta_ = _irls_cloglog(X, y, ridge=params.get("ridge", 1e-6))
        self.theta_ = (self._profile_theta(Z, ctx.age_train, ctx.dur_train,
                                           ctx.ev_train)
                       if self.frailty else 0.0)
        return self

    # ------------------------------------------------------------- frailty
    def _cum_hazard(self, Z: np.ndarray, age, umax: int) -> np.ndarray:
        """H(u | x) for u = 1..umax, walking the age dummy forward."""
        extra = self._extra(Z)
        eta0 = Z @ self.beta_[MAX_AGE_DUMMY:MAX_AGE_DUMMY + Z.shape[1]]
        if extra.shape[1]:
            eta0 = eta0 + extra @ self.beta_[MAX_AGE_DUMMY + Z.shape[1]:]
        gamma = self.beta_[:MAX_AGE_DUMMY]
        a0 = np.asarray(age, dtype="int64")
        H = np.zeros(len(Z))
        out = np.empty((len(Z), umax))
        for k in range(umax):
            a = np.clip(a0 + k, 1, MAX_AGE_DUMMY)
            H = H + np.exp(np.clip(gamma[a - 1] + eta0, -30, 10))
            out[:, k] = H
        return out

    @staticmethod
    def _surv_from_H(H: np.ndarray, theta: float) -> np.ndarray:
        if theta <= 1e-8:
            return np.exp(-H)
        return np.power(1.0 + theta * H, -1.0 / theta)

    def _profile_theta(self, Z, age, dur, ev, grid=(0.0, 0.1, 0.25, 0.5, 0.75,
                                                    1.0, 1.5, 2.0, 3.0, 5.0)):
        """Grid-profile the frailty variance on the training remaining lifetimes."""
        d = np.asarray(dur, dtype="int64")
        e = np.asarray(ev, dtype="int64")
        umax = int(d.max())
        # a large training block makes the profile expensive and no sharper;
        # a fixed subsample is enough to pin one scalar
        if len(Z) > 40000:
            idx = np.random.default_rng(0).choice(len(Z), 40000, replace=False)
            Z, age, d, e = Z[idx], np.asarray(age)[idx], d[idx], e[idx]
        H = self._cum_hazard(Z, age, umax)
        rows = np.arange(len(d))
        best, best_ll = 0.0, -np.inf
        for th in grid:
            S = self._surv_from_H(H, th)
            S_at = S[rows, d - 1]
            S_prev = np.where(d > 1, S[rows, np.maximum(d - 2, 0)], 1.0)
            pmf = np.clip(S_prev - S_at, 1e-12, None)
            ll = float(np.sum(np.where(e == 1, np.log(pmf),
                                       np.log(np.clip(S_at, 1e-12, None)))))
            if ll > best_ll:
                best_ll, best = ll, th
        return best

    # -------------------------------------------------------------- predict
    def predict_survival(self, Z, grid, age=None):
        if age is None:
            raise ValueError("the discrete-time model needs the origin age")
        Zf = Z.astype("float64")
        extra = self._extra(Zf)
        base_part = Zf @ self.beta_[MAX_AGE_DUMMY:MAX_AGE_DUMMY + Zf.shape[1]]
        if extra.shape[1]:
            base_part = base_part + extra @ self.beta_[MAX_AGE_DUMMY + Zf.shape[1]:]
        gamma = self.beta_[:MAX_AGE_DUMMY]

        a0 = np.asarray(age, dtype="int64")
        umax = max(grid)
        H = np.zeros(len(Zf))
        curves = {}
        for k in range(umax):
            a = np.clip(a0 + k, 1, MAX_AGE_DUMMY)
            H = H + np.exp(np.clip(gamma[a - 1] + base_part, -30, 10))
            curves[k + 1] = self._surv_from_H(H, getattr(self, "theta_", 0.0))
        return np.clip(np.column_stack([curves[u] for u in grid]), 1e-12, 1.0)


def _irls_cloglog(X: np.ndarray, y: np.ndarray, ridge: float = 1e-6,
                  max_iter: int = 40, tol: float = 1e-8) -> np.ndarray:
    """Newton-Raphson on the Bernoulli likelihood with a cloglog link.

    h = 1 - exp(-exp(eta)); dh/deta = exp(eta)(1 - h). The Hessian is formed
    explicitly - with a few dozen columns that is cheap.
    """
    n, k = X.shape
    beta = np.zeros(k)
    R = ridge * np.eye(k)
    for _ in range(max_iter):
        eta = np.clip(X @ beta, -30, 10)
        exp_eta = np.exp(eta)
        h = np.clip(-np.expm1(-exp_eta), 1e-12, 1 - 1e-12)
        dh = exp_eta * (1 - h)
        w = dh ** 2 / (h * (1 - h))
        z = (y - h) * dh / (h * (1 - h))
        H = (X.T * w) @ X + R
        g = X.T @ z - ridge * beta
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, g, rcond=None)[0]
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    return beta
