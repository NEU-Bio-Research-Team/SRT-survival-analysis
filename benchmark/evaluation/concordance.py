"""Antolini's time-dependent concordance.

Harrell's C-index collapses each subject to one number, which silently assumes
the risk ordering never changes - i.e. proportional hazards. Half the models in
this benchmark are built specifically to violate that. Birolo et al. (2025) make
the point sharply: if relationship i is riskier than j at year 1 and safer at
year 4, no single ranking is a faithful description of either model, and scoring
both families with a static index rewards the family whose assumption the metric
already shares.

Antolini's version compares the survival curves at the moment the earlier event
actually happens:

    C_td = P( S_i(T_i) < S_j(T_i) | T_i < T_j, d_i = 1 )

Exhaustive pair counting is O(n^2), which is 3.6e9 pairs on a 60k test block, so
pairs are sampled. The sampler is seeded and the number of pairs is recorded with
the metric.
"""

from __future__ import annotations

import numpy as np


def antolini_concordance(surv: np.ndarray, duration: np.ndarray,
                         event: np.ndarray, grid: list[int],
                         n_pairs: int = 2_000_000, seed: int = 7) -> float:
    S = np.clip(surv.astype("float64"), 0.0, 1.0)
    d = np.asarray(duration, dtype="int64")
    e = np.asarray(event, dtype="int64")
    g = np.asarray(grid, dtype="int64")

    cases = np.flatnonzero(e == 1)
    if cases.size == 0:
        return float("nan")
    rng = np.random.default_rng(seed)
    n = len(d)

    i = rng.choice(cases, size=n_pairs)
    j = rng.integers(0, n, size=n_pairs)
    # comparable: the case fails first. A row censored at exactly T_i is known
    # to outlive it (ipcw.py), so it is a valid comparator; a tied failure is not.
    ok = (d[i] < d[j]) | ((d[i] == d[j]) & (e[j] == 0))
    if not ok.any():
        return float("nan")
    i, j = i[ok], j[ok]

    # S evaluated at T_i: the grid is integer years, so take the column at or
    # just below T_i, and treat a T_i past the grid as the last column.
    col = np.searchsorted(g, d[i], side="right") - 1
    col = np.clip(col, 0, len(g) - 1)
    si = S[i, col]
    sj = S[j, col]
    concordant = (si < sj).sum() + 0.5 * (si == sj).sum()
    return float(concordant / len(i))
