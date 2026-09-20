"""Block bootstrap over spells, for differences between models.

Plan section 17. Resampling rows would treat the eight annual observations of one
relationship as eight independent facts, which they are not - they share an
importer, a product and a launch decision - and would therefore produce
confidence intervals several times too narrow. Whole spells are resampled
instead, so the correlation inside a relationship survives the resampling.

What is bootstrapped is the PAIRED difference on the same resampled rows, not two
independent intervals: the models are being compared on identical test data, and
the paired difference has far less variance than either metric alone. A 0.002 gap
in IBS is not a result until this says it is.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def paired_bootstrap(metric_fn, spell_ids: np.ndarray, n_boot: int = 200,
                     seed: int = 4242) -> dict:
    """metric_fn(row_index) -> float, evaluated on each resampled row set."""
    rng = np.random.default_rng(seed)
    spells, inverse = np.unique(spell_ids, return_inverse=True)
    order = np.argsort(inverse, kind="mergesort")
    starts = np.searchsorted(inverse[order], np.arange(len(spells)))
    ends = np.searchsorted(inverse[order], np.arange(len(spells)), side="right")

    draws = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(spells), size=len(spells))
        idx = np.concatenate([order[starts[p]:ends[p]] for p in pick])
        v = metric_fn(idx)
        if np.isfinite(v):
            draws.append(v)
    if not draws:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "n_boot": 0}
    a = np.asarray(draws)
    return {"mean": float(a.mean()),
            "lo": float(np.percentile(a, 2.5)),
            "hi": float(np.percentile(a, 97.5)),
            "n_boot": int(len(a))}


def summarise_differences(per_fold: pd.DataFrame, metric: str,
                          reference: str) -> pd.DataFrame:
    """Across-fold mean and spread of (model - reference) on the same folds."""
    piv = per_fold.pivot_table(index=["feature_set", "fold"], columns="model",
                               values=metric)
    if reference not in piv.columns:
        return pd.DataFrame()
    out = []
    for m in piv.columns:
        diff = (piv[m] - piv[reference]).dropna()
        if diff.empty:
            continue
        out.append({"model": m, "reference": reference, "metric": metric,
                    "n_folds": int(len(diff)), "mean_diff": float(diff.mean()),
                    "sd_diff": float(diff.std(ddof=1)) if len(diff) > 1 else np.nan,
                    "min_diff": float(diff.min()), "max_diff": float(diff.max()),
                    "wins": int((diff < 0).sum())})
    return pd.DataFrame(out).sort_values("mean_diff")
