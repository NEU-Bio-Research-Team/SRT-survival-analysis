"""C05 - nested feature selection (design doc §10.1 tier 4; plan §7).

Every selector is fitted on the fold's TRAINING rows only; the validation
cohort then scores a model refit on the selected columns. Selection is over
registry columns: a column is kept when the column or its missing flag is
chosen. The D block (spell age, known start) is structural and always kept.

  enet_stability  CoxNet (l1 = 0.5) at a mid-path alpha on 20 half-samples of
                  relations; keep columns chosen in >= 60% of them
  consensus       4 selectors, keep columns with >= 3 votes (Asghar et al.'s
                  majority rule, adapted: "3 of 4" is written out explicitly):
                    CoxNet nonzero (l1 = 0.5, mid-path alpha, full train)
                    RSF permutation importance > 0 (C-index, inner holdout)
                    XGBoost survival:cox gain share >= 1/p
                    Wald |z| > 1.96 in the one-year cloglog with age dummies
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from stage2_benchmark.features.preprocess import Preprocessor
from stage2_benchmark.models.base import inner_split

ALWAYS = ["age_obs", "log_age", "known_start"]


def _pre(df, cols):
    pre = Preprocessor(cols).fit(df)
    return pre, pre.transform(df)


def _to_cols(names, mask, cols):
    """Map selected design names (incl. *_isna flags) back to registry columns."""
    keep = set()
    for n, m in zip(names, mask):
        if m:
            keep.add(n[:-5] if n.endswith("_isna") else n)
    return [c for c in cols if c in keep]


def _surv(df):
    from sksurv.util import Surv
    return Surv.from_arrays(event=df["event"].to_numpy().astype(bool),
                            time=df["duration"].to_numpy().astype(float))


def _coxnet_mask(Z, y, n_alphas=30, idx=15):
    from sksurv.linear_model import CoxnetSurvivalAnalysis
    m = CoxnetSurvivalAnalysis(l1_ratio=0.5, n_alphas=n_alphas, alpha_min_ratio=1e-3,
                               normalize=False, max_iter=100000)
    m.fit(Z.astype("float64"), y)
    i = min(idx, m.coef_.shape[1] - 1)
    return np.abs(m.coef_[:, i]) > 0


def enet_stability(df, cols, n_sub=20, frac=0.5, thr=0.6, seed=5):
    rng = np.random.default_rng(seed)
    rels = df["relation"].unique()
    counts = {}
    for b in range(n_sub):
        pick = set(rng.choice(rels, size=int(len(rels) * frac), replace=False))
        sub = df[df["relation"].isin(pick)]
        pre, Z = _pre(sub, cols)
        sel = _to_cols(pre.names, _coxnet_mask(Z, _surv(sub)), cols)
        for c in sel:
            counts[c] = counts.get(c, 0) + 1
    freq = {c: counts.get(c, 0) / n_sub for c in cols}
    chosen = [c for c in cols if freq[c] >= thr or c in ALWAYS]
    return chosen, {"frequency": freq}


def consensus(df, cols, task, seed=5, min_votes=3):
    pre, Z = _pre(df, cols)
    names = pre.names
    y = _surv(df)
    votes = {}
    # 1. CoxNet
    votes["coxnet"] = _to_cols(names, _coxnet_mask(Z, y), cols)
    # 2. RSF permutation importance on an inner holdout
    from sklearn.inspection import permutation_importance
    from sksurv.ensemble import RandomSurvivalForest
    rel = df["relation"].to_numpy()
    tr, ho = inner_split(rel, frac=0.2, seed=seed)
    rng = np.random.default_rng(seed)
    tr_s = rng.choice(tr, size=min(len(tr), 20000), replace=False)
    ho_s = rng.choice(ho, size=min(len(ho), 5000), replace=False)
    rsf = RandomSurvivalForest(n_estimators=50, min_samples_leaf=50, max_features="sqrt",
                               max_samples=0.5, n_jobs=4, random_state=seed)
    rsf.fit(Z[tr_s], y[tr_s])
    pi = permutation_importance(rsf, Z[ho_s], y[ho_s], n_repeats=3, random_state=seed, n_jobs=1)
    votes["rsf_permutation"] = _to_cols(names, pi.importances_mean > 0, cols)
    # 3. XGBoost gain
    import xgboost as xgb
    d = df["duration"].to_numpy().astype(float)
    lab = np.where(df["event"].to_numpy() == 1, d, -d)
    bst = xgb.train({"objective": "survival:cox", "max_depth": 4, "eta": 0.05,
                     "subsample": 0.8, "nthread": 4, "seed": seed, "verbosity": 0},
                    xgb.DMatrix(Z, label=lab), 200)
    gain = bst.get_score(importance_type="total_gain")
    g = np.array([gain.get(f"f{j}", 0.0) for j in range(Z.shape[1])])
    share = g / g.sum() if g.sum() > 0 else g
    votes["xgb_gain"] = _to_cols(names, share >= 1.0 / Z.shape[1], cols)
    # 4. Wald in the one-year cloglog
    from stage2_benchmark.inference.glm import fit_glm
    from stage2_benchmark.models.base import age_dummies
    X = np.hstack([age_dummies(df["age_obs"].to_numpy()), Z.astype("float64")])
    y1 = ((df["duration"] == 1) & (df["event"] == 1)).to_numpy().astype(float)
    f = fit_glm(X, y1, "cloglog", penalty=np.r_[np.zeros(10), np.full(Z.shape[1], 1e-6 * len(y1))])
    z = f["beta"][10:] / np.sqrt(np.maximum(np.diag(f["cov"])[10:], 1e-300))
    votes["wald_cloglog"] = _to_cols(names, np.abs(z) > 1.96, cols)
    n_votes = {c: sum(c in v for v in votes.values()) for c in cols}
    chosen = [c for c in cols if n_votes[c] >= min_votes or c in ALWAYS]
    return chosen, {"votes": votes, "n_votes": n_votes}


def select(df, cols, method, task):
    if method == "enet_stability":
        return enet_stability(df, cols)
    if method == "consensus":
        return consensus(df, cols, task)
    raise ValueError(method)
