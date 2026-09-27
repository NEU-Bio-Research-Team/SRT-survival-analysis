"""Feature-set resolution, per-fold eligibility and the fitted preprocessor.

Set specs understood by `resolve_set`:
    "S4"          a set from feature_sets.yaml
    "S8-N"        S8 without block N          (leave-one-block-out)
    "S4+H"        S4 plus block H
    "S4@lagonly"  S4 with current-year trade values removed (C06a)
    "S4@hist5"    S4 with the 5-year history variants (C06b; see HIST5)
Modifiers combine left to right, e.g. "S8-N@lagonly".

Everything statistical here (medians, means, SDs, constant-column drops) is
fitted on the training rows of one fold and frozen; nothing ever sees the
validation or test rows while fitting.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from stage2_benchmark import paths

_REG = None
_SETS = None

CURRENT_YEAR_COLS = ["log_value"]


def registry() -> dict:
    global _REG
    if _REG is None:
        _REG = paths.load_yaml("feature_registry.yaml")
    return _REG


def set_config() -> dict:
    global _SETS
    if _SETS is None:
        _SETS = paths.load_yaml("feature_sets.yaml")
    return _SETS


def blocks_of(spec: str) -> tuple[list[str], list[str]]:
    """(blocks, modifiers) of a set spec."""
    cfg = set_config()
    head, *mods = spec.split("@")
    m = re.match(r"^(S\d+H?)((?:[+-][A-Z])*)$", head)
    if not m:
        raise ValueError(f"bad feature-set spec {spec!r}")
    base = m.group(1)
    blocks = list(cfg["sets"].get(base) or cfg["aux"][base])
    for op, b in re.findall(r"([+-])([A-Z])", m.group(2)):
        if op == "-":
            blocks = [x for x in blocks if x != b]
        elif b not in blocks:
            blocks.append(b)
    order = cfg["blocks_order"]
    return sorted(blocks, key=order.index), mods


def resolve_set(spec: str) -> list[str]:
    blocks, mods = blocks_of(spec)
    feats = registry()["features"]
    cols = [c for c, s in feats.items() if s["block"] in blocks and not s.get("optional")]
    for mod in mods:
        if mod == "lagonly":
            cols = [c for c in cols if c not in CURRENT_YEAR_COLS]
        elif mod == "hist5":
            cols = cols + [c for c in ("volatility_5y_lag1", "trend_5y_lag1")
                           if c not in cols]
        else:
            raise ValueError(f"unknown modifier {mod!r}")
    return cols


def eligibility(train: pd.DataFrame, spec: str) -> dict:
    """Per secondary block: as-of share on train and whether it varies."""
    cfg = set_config()["eligibility"]
    blocks, _ = blocks_of(spec)
    out = {"eligible": True, "blocks": {}, "reasons": []}
    for b in blocks:
        if b not in cfg["secondary_blocks"]:
            continue
        keys = [c for c in cfg["key_columns"][b] if c in train.columns]
        X = train[keys]
        share = float(X.notna().any(axis=1).mean()) if len(X) else 0.0
        varies = bool((X.std(skipna=True).fillna(0) > 1e-12).any())
        ok = share >= cfg["min_asof_share"] and varies
        out["blocks"][b] = {"asof_share": round(share, 4), "varies": varies,
                            "eligible": ok}
        if not ok:
            out["eligible"] = False
            out["reasons"].append(
                f"block {b}: as-of share {share:.1%} < {cfg['min_asof_share']:.0%}"
                if share < cfg["min_asof_share"] else f"block {b}: constant in train")
    return out


class Preprocessor:
    """Median-impute + missing indicator + standardise, fitted on train."""

    def __init__(self, cols: list[str], standardise: bool = True):
        self.cols = list(cols)
        self.standardise = standardise

    def fit(self, df: pd.DataFrame) -> "Preprocessor":
        X = df[self.cols].astype("float64")
        self.median_ = X.median().fillna(0.0).to_dict()
        self.flag_cols_ = [c for c in self.cols if X[c].isna().any()]
        Z = self._assemble(df)
        sd = Z.std(axis=0)
        self.keep_ = sd > 1e-12
        names = self.cols + [f"{c}_isna" for c in self.flag_cols_]
        self.names_ = [n for n, k in zip(names, self.keep_) if k]
        self.dropped_constant_ = [n for n, k in zip(names, self.keep_) if not k]
        Z = Z[:, self.keep_]
        self.mean_ = Z.mean(axis=0)
        s = Z.std(axis=0)
        self.sd_ = np.where(s > 1e-12, s, 1.0)
        return self

    def _assemble(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.cols].to_numpy(dtype="float64", copy=True)
        flags = np.column_stack([df[c].isna().to_numpy(dtype="float64")
                                 for c in self.flag_cols_]) if self.flag_cols_ \
            else np.empty((len(df), 0))
        for j, c in enumerate(self.cols):
            bad = ~np.isfinite(X[:, j])
            if bad.any():
                X[bad, j] = self.median_[c]
        return np.hstack([X, flags])

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        Z = self._assemble(df)[:, self.keep_]
        if self.standardise:
            Z = (Z - self.mean_) / self.sd_
        return np.ascontiguousarray(Z, dtype="float32")

    @property
    def names(self) -> list[str]:
        return self.names_

    def state(self) -> dict:
        return {"cols": self.cols, "flag_cols": self.flag_cols_,
                "dropped_constant": self.dropped_constant_, "names": self.names_}
