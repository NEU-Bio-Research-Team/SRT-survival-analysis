"""The contract every model in this benchmark signs.

A benchmark is only a benchmark if the models are interchangeable at the point of
scoring. So each one, whatever its internal representation - a partial
likelihood, an ensemble of trees, a discrete hazard, a neural network with time
as an input - must hand back the same object:

    predict_survival(Z, grid, age=None) -> (n_rows, len(grid)) array of S(u | X)

`age` is the relationship's age in whole years at the prediction origin, passed
raw and unstandardised. Only the discrete-time hazard models need it - they walk
the baseline forward one year at a time - but it is on the signature for every
model so that the runner never has to know which family it is calling.

with `grid` in whole years after the prediction origin. Everything downstream -
IBS, Antolini concordance, dynamic AUC, calibration - reads only that array, so
no metric can accidentally be computed on a different quantity for a different
model family.

`nonlinear` and `ph` are declared rather than inferred. They are what plan
sections 10.1 and 16.2 group the leaderboard by, and the contrasts (does
nonlinearity help? does relaxing proportional hazards help?) are only readable if
each model states where it sits in that 2x2.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class FitContext:
    """Everything a model may look at while fitting. Nothing else exists."""
    Z_train: np.ndarray
    dur_train: np.ndarray
    ev_train: np.ndarray
    Z_valid: np.ndarray
    dur_valid: np.ndarray
    ev_valid: np.ndarray
    age_train: np.ndarray = None
    age_valid: np.ndarray = None
    names: list[str] = field(default_factory=list)
    seed: int = 1


class SurvivalModel:
    name = "base"
    family = "base"          # null | classical | tree | deep
    nonlinear = False
    ph = True
    budget = "cheap"         # which tuning budget in benchmark.yaml applies
    max_train_rows = None    # per-model cap, applied on top of the shared cap

    def param_space(self, rng: np.random.Generator, n: int) -> list[dict]:
        """n sampled hyperparameter draws. Default: nothing to tune."""
        return [{}]

    def fit(self, ctx: FitContext, params: dict) -> "SurvivalModel":
        raise NotImplementedError

    def predict_survival(self, Z: np.ndarray, grid: list[int],
                         age: np.ndarray = None) -> np.ndarray:
        raise NotImplementedError


# --------------------------------------------------------------------------
# Shared machinery for the proportional-hazards family.
#
# CoxPH, CoxNet, gradient-boosted Cox and DeepSurv differ only in how they build
# the linear predictor f(x); they share one baseline hazard estimator and one way
# of turning a risk score into a survival curve. Estimating that baseline once,
# here, is not only faster than asking each library for per-sample step functions
# - it guarantees the four models are compared on the same baseline convention
# rather than on three libraries' differing defaults.
# --------------------------------------------------------------------------

def breslow_baseline(risk: np.ndarray, duration: np.ndarray, event: np.ndarray,
                     grid: list[int]) -> np.ndarray:
    """Breslow cumulative baseline hazard H0(u), evaluated on `grid`.

    H0(u) = sum over event times t <= u of  d_t / sum_{i in risk set at t} e^{f_i}
    """
    r = np.exp(np.clip(np.asarray(risk, dtype="float64"), -30, 30))
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    tmax = max(int(d.max()), max(grid))
    H, h = np.zeros(tmax + 1), 0.0
    for t in range(1, tmax + 1):
        at_risk = d >= t
        denom = r[at_risk].sum()
        deaths = int(((d == t) & (e == 1)).sum())
        if deaths and denom > 0:
            h += deaths / denom
        H[t] = h
    return H[np.asarray(grid, dtype="int64")]


def ph_survival(risk: np.ndarray, H0_grid: np.ndarray) -> np.ndarray:
    """S(u | x) = exp(-H0(u) * exp(f(x))) for every row and every grid point."""
    r = np.exp(np.clip(np.asarray(risk, dtype="float64"), -30, 30))
    S = np.exp(-np.outer(r, H0_grid))
    return np.clip(S, 1e-12, 1.0)


def interp_survival(times: np.ndarray, surv: np.ndarray,
                    grid: list[int]) -> np.ndarray:
    """Step-interpolate a model's own time grid onto whole years.

    `surv` is (n_times, n_rows) as pycox returns it. A survival function is a
    right-continuous step function, so the value at u is the last value at a time
    <= u - never a linear blend between two of them, which would invent survival
    the model never predicted.
    """
    times = np.asarray(times, dtype="float64")
    out = np.empty((surv.shape[1], len(grid)), dtype="float64")
    for k, u in enumerate(grid):
        idx = np.searchsorted(times, u, side="right") - 1
        if idx < 0:
            out[:, k] = 1.0
        else:
            out[:, k] = surv[idx, :]
    return np.clip(out, 1e-12, 1.0)
