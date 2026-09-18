"""Fold-wise preprocessing. Fitted on training rows only, applied everywhere.

Plan section 13.1: the scaler, the encoder and the imputer are part of the model,
not part of the data. Fitting a median on the whole panel would hand the training
period a summary of the test period, which is a quiet leak that no split can
undo. So every statistic here is estimated inside `fit` on the training block and
frozen.

Two rules from the registry are enforced:

*   `median+flag` - impute the training median and append a companion `_isna`
    column. The flag is not decoration. A fifth of the panel is age-1 rows, where
    every lagged covariate is structurally absent, and those rows carry half of
    all failures; imputing them silently would tell the model that a launch year
    looks like an average mature year.
*   `zero` / `zero+flag` - for concepts whose absence is a structural zero rather
    than an unknown (a non-EU importer has no CBAM scope; a dyad with no
    agreement has no years since one).

Feature sets are cumulative, so F0F1F2 means F0 + F1 + F2, and every model in a
cell receives that exact matrix.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# The incremental ablation of plan section 8.
FEATURE_SETS = {
    "F0":           ["F0"],
    "F0F1":         ["F0", "F1"],
    "F0F1F2":       ["F0", "F1", "F2"],
    "F0F1F2F3":     ["F0", "F1", "F2", "F3"],
    "F0F1F2F3F4":   ["F0", "F1", "F2", "F3", "F4"],
    "F0F1F2F3F4F5": ["F0", "F1", "F2", "F3", "F4", "F5"],
}


def load_registry(path: str | None = None) -> dict:
    with open(path or os.path.join(HERE, "feature_registry.yaml"),
             encoding="utf-8") as f:
        return yaml.safe_load(f)


class Preprocessor:
    """Impute, flag and standardise - fitted on train, frozen thereafter."""

    def __init__(self, feature_set: str, registry: dict | None = None,
                 standardise: bool = True):
        reg = registry or load_registry()
        blocks = FEATURE_SETS[feature_set]
        self.spec = {k: v for k, v in reg["features"].items()
                     if v["set"] in blocks}
        self.cols = list(self.spec)
        self.standardise = standardise
        self.fitted = False

    def fit(self, train: pd.DataFrame) -> "Preprocessor":
        X = train[self.cols]
        self.median_ = {}
        self.flag_cols_ = []
        for c in self.cols:
            rule = self.spec[c]["missing"]
            if rule.startswith("median"):
                m = X[c].median()
                self.median_[c] = 0.0 if pd.isna(m) else float(m)
            else:
                self.median_[c] = 0.0
            if rule.endswith("flag"):
                self.flag_cols_.append(c)

        Z = self._assemble(train)
        # A column that never varies inside a training block carries nothing and
        # makes a Cox design matrix singular; drop it and remember the decision.
        sd = Z.std(axis=0)
        self.keep_ = sd > 1e-12
        self.names_ = [n for n, k in zip(self._names(), self.keep_) if k]
        Z = Z[:, self.keep_]
        self.mean_ = Z.mean(axis=0)
        self.sd_ = np.where(Z.std(axis=0) > 1e-12, Z.std(axis=0), 1.0)
        self.fitted = True
        return self

    def _names(self) -> list[str]:
        return self.cols + [f"{c}_isna" for c in self.flag_cols_]

    def _assemble(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.cols].to_numpy(dtype="float64", copy=True)
        flags = np.empty((len(df), len(self.flag_cols_)), dtype="float64")
        for i, c in enumerate(self.flag_cols_):
            flags[:, i] = df[c].isna().to_numpy(dtype="float64")
        for j, c in enumerate(self.cols):
            col = X[:, j]
            bad = ~np.isfinite(col)
            if bad.any():
                col[bad] = self.median_[c]
                X[:, j] = col
        return np.hstack([X, flags]) if flags.shape[1] else X

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if not self.fitted:
            raise RuntimeError("Preprocessor.transform before .fit")
        Z = self._assemble(df)[:, self.keep_]
        if self.standardise:
            Z = (Z - self.mean_) / self.sd_
        return np.ascontiguousarray(Z, dtype="float32")

    @property
    def names(self) -> list[str]:
        return self.names_


def theory_interactions(reg: dict, names: list[str], Z: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """The F3x block of plan section 16.1 - classical models only.

    These are handed to the theory-enhanced cloglog so that the econometric
    baseline is not a straw man. No ML model ever receives them: the whole point
    of the contrast is whether a flexible learner recovers them unaided.
    """
    idx = {n: i for i, n in enumerate(names)}
    cols, out_names = [], []
    for a, b in reg.get("interactions_F3x", []):
        if a in idx and b in idx:
            cols.append(Z[:, idx[a]] * Z[:, idx[b]])
            out_names.append(f"{a}_x_{b}")
    if not cols:
        return Z, list(names)
    return np.hstack([Z, np.column_stack(cols).astype("float32")]), list(names) + out_names
