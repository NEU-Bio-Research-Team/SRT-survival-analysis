"""Paired bootstrap over relations (importer x product_family), design doc §8.4.

Every landmark and every spell of one relation moves together. Metrics are
means of per-row contributions (metrics.py), so a bootstrap replicate is just
a reweighting of per-relation sums: for draw counts c_r,

    metric* = sum_r c_r * s_r / sum_r c_r * n_r.

The paired difference is computed on the SAME draws for both models.
"""

from __future__ import annotations

import numpy as np


def _relation_sums(rows: np.ndarray, rel: np.ndarray):
    codes, inv = np.unique(rel, return_inverse=True)
    s = np.bincount(inv, weights=rows, minlength=len(codes))
    n = np.bincount(inv, minlength=len(codes)).astype("float64")
    return s, n


def draw_counts(n_rel: int, B: int, seed: int, chunk: int = 100):
    rng = np.random.default_rng(seed)
    for start in range(0, B, chunk):
        b = min(chunk, B - start)
        idx = rng.integers(0, n_rel, size=(b, n_rel))
        yield np.stack([np.bincount(r, minlength=n_rel) for r in idx]).astype("float64")


def paired_diff(rows_a, rows_b, relation, B=1000, seed=20260927, alpha=0.05):
    """Bootstrap of mean(rows_a) - mean(rows_b), resampling relations."""
    rows_a = np.asarray(rows_a, dtype="float64")
    rows_b = np.asarray(rows_b, dtype="float64")
    ok = np.isfinite(rows_a) & np.isfinite(rows_b)
    if not ok.any():
        return {"diff": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "p_le_0": float("nan"), "B": 0}
    sa, n = _relation_sums(rows_a[ok], np.asarray(relation)[ok])
    sb, _ = _relation_sums(rows_b[ok], np.asarray(relation)[ok])
    sd = sa - sb
    point = sd.sum() / n.sum()
    reps = []
    for C in draw_counts(len(n), B, seed):
        reps.append((C @ sd) / (C @ n))
    reps = np.concatenate(reps)
    return {"diff": float(point),
            "lo": float(np.quantile(reps, alpha / 2)),
            "hi": float(np.quantile(reps, 1 - alpha / 2)),
            "p_le_0": float((reps <= 0).mean()),
            "B": int(len(reps))}


def mean_ci(rows, relation, B=1000, seed=20260927, alpha=0.05):
    rows = np.asarray(rows, dtype="float64")
    s, n = _relation_sums(rows, np.asarray(relation))
    reps = np.concatenate([(C @ s) / (C @ n) for C in draw_counts(len(n), B, seed)])
    return {"mean": float(s.sum() / n.sum()),
            "lo": float(np.quantile(reps, alpha / 2)),
            "hi": float(np.quantile(reps, 1 - alpha / 2))}
