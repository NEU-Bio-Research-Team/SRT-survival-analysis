"""Đợt 0.5 - reproduce legacy eu27_v4 with the new adapters.

KM, CoxNet, RSF and the legacy landmark cloglog (one-year cloglog with age
dummies, walked forward, with a two-stage gamma-frailty profile) on legacy
folds 1-3 with the F0-equivalent features (spell age, log age, known start),
scored by IBS 1-3 on the legacy test origins 2019/2020/2021.

Each model is run under two training-censoring rules:
  legacy  censor_block_gap of legacy/benchmark/splits/rolling_origin.py:
          train origins [lo, hi] read to hi; an unconfirmed death is censored
          at A - t while survivors run to hi - t
  new     views.recensor (administrative censoring at H = C - g)
so the part of any gap that is due to the censoring fix is visible separately.

    python -m stage2_benchmark.runners.reproduce_legacy
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from stage2_benchmark.data import base_table  # noqa: E402
from stage2_benchmark.data import views as V  # noqa: E402
from stage2_benchmark.evaluation import metrics as M  # noqa: E402
from stage2_benchmark.features.preprocess import Preprocessor  # noqa: E402
from stage2_benchmark.inference.glm import fit_glm  # noqa: E402
from stage2_benchmark.models import get_model  # noqa: E402
from stage2_benchmark.models.base import FitData, Model, age_dummies, MAX_AGE_DUMMY  # noqa: E402
from stage2_benchmark.runners.cell import fit_data  # noqa: E402

OUT = os.path.join(paths.REPORTS, "stage0")
F0 = ["age_obs", "log_age", "known_start"]
GRID = [1, 2, 3, 4, 5]
LEGACY_IBS = {  # legacy/benchmark/runs/eu27_v4/run.log, F0 rows
    ("KM", 1): 0.13587, ("KM", 2): 0.11998, ("KM", 3): 0.13163,
    ("CoxNet", 1): 0.11275, ("CoxNet", 2): 0.09916, ("CoxNet", 3): 0.11087,
    ("RSF", 1): 0.10887, ("RSF", 2): 0.09860, ("RSF", 3): 0.10732,
    ("Cloglog", 1): 0.11196, ("Cloglog", 2): 0.09982, ("Cloglog", 3): 0.10833,
}


def legacy_censor(base, lo, hi, observed_through, gap=1):
    """Port of legacy censor_block_gap (the rule being audited)."""
    b = base[(base.year >= lo) & (base.year <= hi)].copy()
    alive = base[base.year <= observed_through].groupby("spell_id")["year"].max()
    A = b["spell_id"].map(alive).to_numpy()
    E = b["_y_E"].to_numpy()
    confirmed = (b["_y_died"] == 1).to_numpy() & (E <= observed_through - 1 - gap)
    b["duration"] = np.where(confirmed, E - b["year"] + 1, A - b["year"]).astype("int16")
    b["event"] = confirmed.astype("int8")
    return b[b["duration"] >= 1].reset_index(drop=True)


class LegacyLandmarkCloglog(Model):
    """Legacy models/cloglog.py: one-year cloglog on age dummies + X, walked
    forward over age, frailty variance profiled on the training lifetimes."""
    id, name, task = "RCL", "Cloglog", "L"

    def fit(self, data: FitData, params, seed=1):
        y = ((data.duration == 1) & (data.event == 1)).astype("float64")
        X = np.hstack([age_dummies(data.age), data.Z.astype("float64")])
        pen = np.r_[np.zeros(MAX_AGE_DUMMY), np.full(data.Z.shape[1], 1e-6 * len(y))]
        self.beta_ = fit_glm(X, y, "cloglog", penalty=pen)["beta"]
        self.theta_ = self._profile(data)
        return self

    def _H(self, Z, age, umax):
        g = self.beta_[:MAX_AGE_DUMMY]
        eta = Z.astype("float64") @ self.beta_[MAX_AGE_DUMMY:]
        H, out = np.zeros(len(Z)), np.empty((len(Z), umax))
        for k in range(umax):
            a = np.clip(np.asarray(age) + k, 1, MAX_AGE_DUMMY)
            H = H + np.exp(np.clip(g[a - 1] + eta, -30, 10))
            out[:, k] = H
        return out

    @staticmethod
    def _S(H, th):
        return np.exp(-H) if th <= 1e-8 else np.power(1 + th * H, -1 / th)

    def _profile(self, data):
        idx = np.arange(len(data.duration))
        if len(idx) > 40000:
            idx = np.random.default_rng(0).choice(len(idx), 40000, replace=False)
        d, e = data.duration[idx], data.event[idx]
        H = self._H(data.Z[idx], data.age[idx], int(d.max()))
        r = np.arange(len(d))
        best, bl = 0.0, -np.inf
        for th in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0):
            S = self._S(H, th)
            Sa = S[r, d - 1]
            Sp = np.where(d > 1, S[r, np.maximum(d - 2, 0)], 1.0)
            ll = np.sum(np.where(e == 1, np.log(np.clip(Sp - Sa, 1e-12, None)),
                                 np.log(np.clip(Sa, 1e-12, None))))
            if ll > bl:
                bl, best = ll, th
        return best

    def predict_survival(self, Z, grid, age):
        S = self._S(self._H(Z, age, max(grid)), self.theta_)
        return np.clip(S[:, [u - 1 for u in grid]], 1e-12, 1)


def run():
    os.makedirs(OUT, exist_ok=True)
    base = base_table.load_base()
    splits = paths.load_yaml("splits.yaml")
    rows = []
    for fid, f in splits["legacy_folds"].items():
        lo, hi = f["train"]
        te = f["test"][0]
        test = V.view(base, te, 2025)
        for rule in ("legacy", "new"):
            train = (legacy_censor(base, lo, hi, hi) if rule == "legacy"
                     else V.view(base, (lo, hi), hi))
            pre = Preprocessor(F0).fit(train)
            tr = fit_data(train, pre.transform(train), pre.names, "L")
            ev = fit_data(test, pre.transform(test), pre.names, "L")
            cands = {
                "KM": (get_model("L00"), {}),
                "CoxNet": (get_model("L02"), {"l1_ratio": 0.5, "alpha_idx": 29}),
                "Cloglog": (LegacyLandmarkCloglog(), {}),
            }
            for name, (m, p) in cands.items():
                m.fit(tr, p)
                S = m.predict_survival(ev.Z, GRID, ev.age)
                sc = M.score_L(S, GRID, ev.duration, ev.event)
                rows.append({"fold": fid, "rule": rule, "model": name, "rows_train": len(tr.Z),
                             "ibs_1_3": sc["ibs_1_3"], "legacy_logged": LEGACY_IBS[(name, fid)]})
            # RSF: legacy capped training at 8,000 rows (spell draw); run both
            for cap in (8000, None):
                idx = np.arange(len(tr.Z))
                if cap and len(idx) > cap:
                    rng = np.random.default_rng(20260910 + fid)
                    sp = train["spell_id"].unique()
                    rng.shuffle(sp)
                    sizes = train.groupby("spell_id").size()
                    take, tot = [], 0
                    for s in sp:
                        if tot + sizes[s] > cap:
                            continue
                        take.append(s)
                        tot += sizes[s]
                        if tot >= cap * 0.995:
                            break
                    idx = np.flatnonzero(train["spell_id"].isin(set(take)).to_numpy())
                best = None
                for leaf in (20, 50, 100):
                    m = get_model("L05").fit(tr.subset(idx), {"n_estimators": 100,
                                                               "min_samples_leaf": leaf,
                                                               "max_features": "sqrt",
                                                               "max_depth": None})
                    S = m.predict_survival(ev.Z, GRID, ev.age)
                    v = M.score_L(S, GRID, ev.duration, ev.event)["ibs_1_3"]
                    best = v if best is None else min(best, v)
                rows.append({"fold": fid, "rule": rule, "model": f"RSF(cap={cap})",
                             "rows_train": len(idx), "ibs_1_3": best,
                             "legacy_logged": LEGACY_IBS[("RSF", fid)]})
            print(fid, rule, "done", flush=True)
    df = pd.DataFrame(rows)
    df["diff_vs_legacy"] = df["ibs_1_3"] - df["legacy_logged"]
    paths.atomic_write_csv(df, os.path.join(OUT, "0.5_reproduction.csv"))
    return df


if __name__ == "__main__":
    print(run().to_string())
