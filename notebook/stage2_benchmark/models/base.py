"""The adapter contract (design doc §10.2) and shared machinery.

D adapters return a one-year exit probability:   predict_proba(ctx_or_Z, age)
L adapters return survival on the year grid:     predict_survival(Z, grid, age)

Tuning: `grid()` lists the candidate params for deterministic/small families;
`suggest(trial)` samples one optuna trial for the budgeted families. A model
declares which it uses with `tuning = "none" | "grid" | "optuna"`.

Early stopping of boosted and neural models reads an INNER holdout carved out
of the training rows by relation (`inner_split`), never the validation cohort
that the trial is scored on - legacy stopped on the scored block, which tunes
twice on the same outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MAX_AGE_DUMMY = 10


@dataclass
class FitData:
    Z: np.ndarray                  # preprocessed features (float32)
    age: np.ndarray                # observed spell age at origin (int)
    relation: np.ndarray           # for grouped inner splits
    y: np.ndarray | None = None    # D: one-year exit
    duration: np.ndarray | None = None   # L
    event: np.ndarray | None = None      # L
    names: list = field(default_factory=list)
    raw: object = None             # the view frame (for models needing raw cols)

    def subset(self, idx):
        g = lambda a: None if a is None else a[idx]  # noqa: E731
        return FitData(self.Z[idx], self.age[idx], self.relation[idx], g(self.y),
                       g(self.duration), g(self.event), self.names,
                       None if self.raw is None else self.raw.iloc[idx])


class Model:
    id = "X00"
    name = "base"
    task = "L"
    family = "linear"          # reference | linear | tree | neural
    nonlinear = False
    ph = True
    stochastic = False
    tuning = "none"
    uses_inner_holdout = False

    def grid(self) -> list[dict]:
        return [{}]

    def suggest(self, trial) -> dict:
        raise NotImplementedError

    def fit(self, data: FitData, params: dict, seed: int = 1):
        raise NotImplementedError

    def predict_proba(self, Z, age):
        raise NotImplementedError

    def predict_survival(self, Z, grid, age):
        raise NotImplementedError

    def info(self) -> dict:
        return {}


def inner_split(relation: np.ndarray, frac: float = 0.15, seed: int = 11):
    """(train_idx, holdout_idx): whole relations go to the holdout."""
    rels = np.unique(relation)
    rng = np.random.default_rng(seed)
    hold = set(rng.choice(rels, size=max(1, int(len(rels) * frac)), replace=False))
    mask = np.fromiter((r in hold for r in relation), dtype=bool, count=len(relation))
    return np.flatnonzero(~mask), np.flatnonzero(mask)


def age_dummies(age, max_age=MAX_AGE_DUMMY):
    a = np.clip(np.asarray(age, dtype="int64"), 1, max_age)
    D = np.zeros((len(a), max_age), dtype="float64")
    D[np.arange(len(a)), a - 1] = 1.0
    return D


def one_year_label(duration, event):
    return ((np.asarray(duration) == 1) & (np.asarray(event) == 1)).astype("float64")


# ------------------------------------------------------ PH family helpers
def breslow_H0(risk, duration, event, tmax):
    r = np.exp(np.clip(np.asarray(risk, dtype="float64"), -30, 30))
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    # risk-set sums by descending duration
    T = max(int(d.max()), tmax)
    sum_by_d = np.bincount(d, weights=r, minlength=T + 2)
    at_risk = np.cumsum(sum_by_d[::-1])[::-1]       # sum over d >= t
    deaths = np.bincount(d[e == 1], minlength=T + 2)
    H = np.zeros(T + 1)
    h = 0.0
    for t in range(1, T + 1):
        if deaths[t] and at_risk[t] > 0:
            h += deaths[t] / at_risk[t]
        H[t] = h
    return H


def ph_survival(risk, H0, grid):
    r = np.exp(np.clip(np.asarray(risk, dtype="float64"), -30, 30))
    Hg = H0[np.minimum(np.asarray(grid), len(H0) - 1)]
    return np.clip(np.exp(-np.outer(r, Hg)), 1e-12, 1.0)


def interp_survival(times, surv, grid):
    """Step read of (n_times, n_rows) survival onto integer years."""
    times = np.asarray(times, dtype="float64")
    out = np.empty((surv.shape[1], len(grid)))
    for k, u in enumerate(grid):
        idx = np.searchsorted(times, u + 1e-9, side="right") - 1
        out[:, k] = 1.0 if idx < 0 else surv[idx, :]
    return np.clip(out, 1e-12, 1.0)


def monotone(S):
    """Enforce non-increasing survival (guards tiny numeric reversals)."""
    return np.minimum.accumulate(np.clip(S, 1e-12, 1.0), axis=1)
