"""Uno-style cumulative/dynamic time-dependent AUC, censoring-adjusted.

At horizon u a subject is a case if it has already failed by u and a control if
it is known to be alive at u (including rows censored at exactly u - see
ipcw.py); subjects censored before u belong to neither and are
reweighted away rather than guessed at. The score is the IPCW-weighted
probability that a case is ranked riskier than a control, with risk read off the
model's own curve as 1 - S(u), so the ranking being tested is the one at that
horizon rather than a static summary.

Computed by sorting rather than by enumerating case-control pairs: 60k rows would
otherwise be a billion comparisons per horizon per model.
"""

from __future__ import annotations

import numpy as np

from .ipcw import CensoringKM, known_alive, observed_failure


def dynamic_auc(surv: np.ndarray, duration: np.ndarray, event: np.ndarray,
                u: int, grid: list[int], G: CensoringKM | None = None) -> float:
    S = np.clip(surv[:, grid.index(u)].astype("float64"), 0.0, 1.0)
    risk = 1.0 - S
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    G = G or CensoringKM(d, e)

    case = observed_failure(d, e, u)
    ctrl = known_alive(d, e, u)
    if case.sum() == 0 or ctrl.sum() == 0:
        return float("nan")
    wc = 1.0 / G(d[case] - 1)
    wk = np.full(int(ctrl.sum()), 1.0 / G(u - 1))
    rc, rk = risk[case], risk[ctrl]

    # weighted P(risk_case > risk_ctrl) + 0.5 P(=), by sorting the controls once
    order = np.argsort(rk, kind="mergesort")
    rk_s, wk_s = rk[order], wk[order]
    cum = np.concatenate([[0.0], np.cumsum(wk_s)])
    lo = np.searchsorted(rk_s, rc, side="left")     # controls strictly below
    hi = np.searchsorted(rk_s, rc, side="right")    # controls at or below
    below = cum[lo]
    ties = cum[hi] - cum[lo]
    num = float(np.sum(wc * (below + 0.5 * ties)))
    den = float(wc.sum() * wk_s.sum())
    return num / den if den > 0 else float("nan")
