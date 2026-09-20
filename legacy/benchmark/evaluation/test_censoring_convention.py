"""The metrics must read durations the way rolling_origin.censor_block writes them.

A censored row with duration c is known to survive c years. Scoring it as
"outcome unknown" at horizon c turns every one-year block (each validation block,
and a test block at the end of the data) into a failures-only Brier score that a
model predicting S = 0 wins. These tests pin the convention against a simulated
panel whose uncensored truth is known.

Run: python -m pytest benchmark/evaluation/test_censoring_convention.py
"""

from __future__ import annotations

import numpy as np

from benchmark.evaluation import (antolini_concordance, brier_at, dynamic_auc,
                                  ibs)

GRID = list(range(1, 9))


def _panel(max_follow_up: tuple[int, int], n: int = 100_000, seed: int = 0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    h = 1 / (1 + np.exp(-(-1.7 + 0.8 * x)))
    T = rng.geometric(h)                                   # fails in year T >= 1
    C = rng.integers(max_follow_up[0], max_follow_up[1] + 1, size=n)
    died = T <= C
    d, e = np.where(died, T, C), died.astype(int)
    S = np.stack([(1 - h) ** u for u in GRID], axis=1)
    return T, d, e, S


def _truth(T, S, u):
    return float(np.mean(((T > u).astype(float) - S[:, GRID.index(u)]) ** 2))


def test_one_year_block_is_a_proper_score():
    T, d, e, S = _panel((1, 1))
    assert abs(brier_at(S, d, e, 1, GRID) - _truth(T, S, 1)) < 1e-9
    # a pessimistic model must lose, not win
    assert brier_at(S * 0.5, d, e, 1, GRID) > brier_at(S, d, e, 1, GRID)
    # horizons beyond the follow-up are unobservable, not failures-only sums
    assert np.isnan(brier_at(S, d, e, 2, GRID))
    assert np.isnan(ibs(S, d, e, [1, 2, 3], GRID))
    assert np.isfinite(dynamic_auc(S, d, e, 1, GRID))
    assert np.isfinite(antolini_concordance(S, d, e, GRID))


def test_ipcw_brier_is_unbiased_under_mixed_follow_up():
    for fu in ((1, 5), (2, 3)):
        T, d, e, S = _panel(fu)
        for u in (1, 2, 3):
            assert abs(brier_at(S, d, e, u, GRID) - _truth(T, S, u)) < 0.003, (fu, u)
