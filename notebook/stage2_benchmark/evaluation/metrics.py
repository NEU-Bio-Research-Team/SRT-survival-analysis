"""Scoring (design doc §8.4). Ported from legacy/benchmark/evaluation, audited.

Duration convention (views.py):
    event = 1, duration = d   the relationship fails in remaining year d
    event = 0, duration = c   it is KNOWN to survive c years: T > c
Every metric reads outcomes through `known_alive` / `observed_failure`.

Primary metrics are written as a mean of PER-ROW contributions, so the paired
relation bootstrap (bootstrap.py) can resample relations without refitting or
recomputing anything but sums. The censoring weights G are estimated once on
the whole scored cohort and held fixed inside the bootstrap.
"""

from __future__ import annotations

import numpy as np

G_FLOOR = 1e-3


# ------------------------------------------------------------------ IPCW
class CensoringKM:
    """Kaplan-Meier of the censoring distribution, on integer years.

    A failure at D only says C >= D, so it leaves the censoring risk set after
    D - 1; a row censored at c is at risk of censoring at c.
    """

    def __init__(self, duration, event):
        d = np.asarray(duration, dtype="int64")
        cens = np.asarray(event) == 0
        tmax = int(d.max()) if len(d) else 0
        times = np.arange(0, tmax + 1)
        at_risk = np.array([((cens & (d >= t)) | (~cens & (d > t))).sum()
                            for t in times], dtype="float64")
        n_c = np.array([(cens & (d == t)).sum() for t in times], dtype="float64")
        with np.errstate(divide="ignore", invalid="ignore"):
            frac = np.where(at_risk > 0, 1.0 - n_c / at_risk, 1.0)
        self.times = times
        self.G_raw = np.cumprod(frac)
        self.G = np.maximum(self.G_raw, G_FLOOR)

    def __call__(self, t):
        t = np.clip(np.asarray(t, dtype="int64"), 0, self.times[-1])
        return self.G[t]

    def support(self, u: int) -> float:
        """G(u-1): the probability of still being under observation at u."""
        if u - 1 > self.times[-1]:
            return 0.0
        return float(self.G_raw[max(u - 1, 0)])


def known_alive(d, e, u):
    d = np.asarray(d, dtype="int64")
    e = np.asarray(e, dtype="int64")
    return (d > u) | ((e == 0) & (d == u))


def observed_failure(d, e, u):
    d = np.asarray(d, dtype="int64")
    e = np.asarray(e, dtype="int64")
    return (d <= u) & (e == 1)


def brier_rows(S_u, d, e, u, G: CensoringKM):
    """Per-row IPCW Brier contribution at horizon u (NaN column if unobservable)."""
    S = np.clip(np.asarray(S_u, dtype="float64"), 0, 1)
    fail = observed_failure(d, e, u)
    alive = known_alive(d, e, u)
    if not alive.any():
        return np.full(len(S), np.nan)
    wf = np.where(fail, 1.0 / G(np.asarray(d) - 1), 0.0)
    wa = np.where(alive, 1.0 / G(u - 1), 0.0)
    return wf * S ** 2 + wa * (1.0 - S) ** 2


def trapezoid_weights(us):
    us = np.asarray(us, dtype="float64")
    if len(us) == 1:
        return np.ones(1)
    w = np.zeros(len(us))
    for k in range(len(us) - 1):
        h = us[k + 1] - us[k]
        w[k] += h / 2
        w[k + 1] += h / 2
    return w / (us[-1] - us[0])


def ibs_rows(surv, grid, d, e, us, G=None):
    """Per-row contributions whose mean is the IBS over horizons `us`."""
    G = G or CensoringKM(d, e)
    w = trapezoid_weights(us)
    tot = np.zeros(len(d))
    for wk, u in zip(w, us):
        b = brier_rows(surv[:, grid.index(u)], d, e, u, G)
        if np.isnan(b).all():
            return np.full(len(d), np.nan)
        tot += wk * b
    return tot


# ---------------------------------------------------------- concordance
def antolini(surv, grid, d, e, n_pairs=2_000_000, seed=7):
    S = np.asarray(surv, dtype="float64")
    d = np.asarray(d, dtype="int64")
    e = np.asarray(e, dtype="int64")
    g = np.asarray(grid, dtype="int64")
    cases = np.flatnonzero(e == 1)
    if cases.size == 0:
        return float("nan")
    rng = np.random.default_rng(seed)
    i = rng.choice(cases, size=n_pairs)
    j = rng.integers(0, len(d), size=n_pairs)
    ok = (d[i] < d[j]) | ((d[i] == d[j]) & (e[j] == 0))
    i, j = i[ok], j[ok]
    if not len(i):
        return float("nan")
    col = np.clip(np.searchsorted(g, d[i], side="right") - 1, 0, len(g) - 1)
    si, sj = S[i, col], S[j, col]
    return float(((si < sj).sum() + 0.5 * (si == sj).sum()) / len(i))


def td_auc(risk_u, d, e, u, G=None):
    """IPCW cumulative/dynamic AUC at u: cases fail by u, controls known alive."""
    G = G or CensoringKM(d, e)
    d = np.asarray(d, dtype="int64")
    case = observed_failure(d, e, u)
    ctrl = known_alive(d, e, u)
    if not case.any() or not ctrl.any():
        return float("nan")
    rc, wc = risk_u[case], 1.0 / G(d[case] - 1)
    rk = np.sort(risk_u[ctrl])
    # weighted share of (case, control) pairs with case risk > control risk
    lo = np.searchsorted(rk, rc, side="left")
    hi = np.searchsorted(rk, rc, side="right")
    conc = (lo + 0.5 * (hi - lo)) / len(rk)
    return float((wc * conc).sum() / wc.sum())


# ---------------------------------------------------------------- L task
def score_L(surv, grid, d, e, horizons=(1, 2, 3)):
    grid = list(grid)
    G = CensoringKM(d, e)
    out = {"n": int(len(d)), "events": int(np.sum(e))}
    for u in range(1, max(grid) + 1):
        out[f"ipcw_support_{u}"] = G.support(u)
    for u in horizons:
        b = brier_rows(surv[:, grid.index(u)], d, e, u, G)
        out[f"brier_{u}"] = float(np.mean(b)) if not np.isnan(b).all() else float("nan")
    r = ibs_rows(surv, grid, d, e, list(horizons), G)
    out[f"ibs_{horizons[0]}_{horizons[-1]}"] = float(np.mean(r))
    if max(grid) >= 5 and G.support(5) > 0:
        r5 = ibs_rows(surv, grid, d, e, [1, 2, 3, 4, 5], G)
        out["ibs_1_5"] = float(np.mean(r5))
    out["antolini_ctd"] = antolini(surv, grid, d, e)
    for u in (1, 3):
        if u in grid:
            out[f"td_auc_{u}"] = td_auc(1 - surv[:, grid.index(u)], d, e, u, G)
    # calibration-in-the-large at 1 and 3 years: predicted vs KM
    for u in (1, 3):
        if u in grid:
            out[f"mean_pred_S{u}"] = float(np.mean(surv[:, grid.index(u)]))
            out[f"km_S{u}"] = km_at(d, e, u)
    return out


def km_at(d, e, u):
    d = np.asarray(d, dtype="int64")
    e = np.asarray(e, dtype="int64")
    s = 1.0
    for t in range(1, u + 1):
        at = (d >= t).sum()
        ev = ((d == t) & (e == 1)).sum()
        if at:
            s *= 1 - ev / at
    return float(s)


# ---------------------------------------------------------------- D task
def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def calibration_slope_intercept(p, y):
    """Logistic recalibration y ~ a + b*logit(p): returns (b, a) and the
    intercept with slope fixed at 1 (calibration-in-the-large)."""
    x = _logit(np.asarray(p, dtype="float64"))
    y = np.asarray(y, dtype="float64")
    beta = np.zeros(2)
    X = np.column_stack([np.ones_like(x), x])
    for _ in range(50):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-eta))
        W = mu * (1 - mu)
        H = (X.T * W) @ X + 1e-9 * np.eye(2)
        step = np.linalg.solve(H, X.T @ (y - mu))
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    a0 = 0.0
    for _ in range(50):
        mu = 1 / (1 + np.exp(-(x + a0)))
        step = (y - mu).sum() / max((mu * (1 - mu)).sum(), 1e-12)
        a0 += step
        if abs(step) < 1e-10:
            break
    return float(beta[1]), float(beta[0]), float(a0)


def score_D(p, y):
    from sklearn.metrics import average_precision_score, roc_auc_score
    p = np.clip(np.asarray(p, dtype="float64"), 1e-7, 1 - 1e-7)
    y = np.asarray(y, dtype="int64")
    out = {"n": int(len(y)), "events": int(y.sum()),
           "brier_1y": float(np.mean((p - y) ** 2)),
           "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
           "mean_pred": float(p.mean()), "event_rate": float(y.mean())}
    if 0 < y.sum() < len(y):
        out["roc_auc"] = float(roc_auc_score(y, p))
        out["pr_auc"] = float(average_precision_score(y, p))
        b, a, citl = calibration_slope_intercept(p, y)
        out.update(calib_slope=b, calib_intercept=a, calib_in_large=citl)
    return out


def D_rows(p, y):
    p = np.asarray(p, dtype="float64")
    return (p - np.asarray(y)) ** 2


def check_survival(surv) -> list[str]:
    """Contract checks (design doc §10.3): in [0,1], non-increasing, finite."""
    bad = []
    if not np.isfinite(surv).all():
        bad.append("non-finite survival")
    if (surv < -1e-9).any() or (surv > 1 + 1e-9).any():
        bad.append("survival outside [0,1]")
    if surv.shape[1] > 1 and (np.diff(surv, axis=1) > 1e-7).any():
        bad.append("survival increases with horizon")
    return bad
