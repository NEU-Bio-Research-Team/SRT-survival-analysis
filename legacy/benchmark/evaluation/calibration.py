"""Horizon calibration: does a predicted 0.8 actually survive four times in five?

This is the metric Stage 2 depends on. `Value x S` is a number of dollars, and a
model whose probabilities are shifted by ten points produces an expected-value
table that is wrong by ten percent no matter how well it ranks.

Within each decile of predicted S(u) the observed survival is estimated by
Kaplan-Meier rather than by a raw proportion, because the censored members of a
bin would otherwise be counted as failures. The summary is the expected
calibration error - the bin-size-weighted mean absolute gap - and the per-bin
table is kept so the miscalibration can be read as over- or under-confidence
rather than as a single scalar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _km_at(duration: np.ndarray, event: np.ndarray, u: int) -> float:
    """Kaplan-Meier S(u) inside a bin; NaN when follow-up never reaches u.

    Carrying the last estimate forward past the end of follow-up would compare a
    predicted S(3) with an observed S(1) and call the gap miscalibration.
    """
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    s = 1.0
    for t in range(1, u + 1):
        at_risk = (d >= t).sum()
        if at_risk == 0:
            return float("nan")
        deaths = ((d == t) & (e == 1)).sum()
        s *= (1.0 - deaths / at_risk)
    return float(s)


def calibration_table(surv: np.ndarray, duration: np.ndarray, event: np.ndarray,
                      u: int, grid: list[int], n_bins: int = 10) -> pd.DataFrame:
    S = np.clip(surv[:, grid.index(u)].astype("float64"), 0.0, 1.0)
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    # rank-based bins: predicted survival is heavily skewed, so equal-width bins
    # would leave most of them empty
    q = pd.qcut(pd.Series(S).rank(method="first"), n_bins,
                labels=False, duplicates="drop")
    rows = []
    for b in sorted(pd.unique(q)):
        m = (q == b).to_numpy()
        rows.append({"horizon": u, "bin": int(b), "n": int(m.sum()),
                     "predicted": float(S[m].mean()),
                     "observed_km": _km_at(d[m], e[m], u)})
    return pd.DataFrame(rows)


def expected_calibration_error(tab: pd.DataFrame) -> float:
    if tab["observed_km"].isna().any():
        return float("nan")
    w = tab["n"] / tab["n"].sum()
    return float((w * (tab["predicted"] - tab["observed_km"]).abs()).sum())
