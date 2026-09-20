"""Turn a run's cells into the tables the paper is written from.

The organising principle is plan section 15: a leaderboard alone confounds two
different things. A model can look good because the algorithm is better or
because the feature block it was given is richer, and only the feature x model
grid separates

    Delta_feature   - what the economics contributed
    Delta_algorithm - what the learner contributed.

So the outputs here are not "who won". They are:

  leaderboard.csv        every metric, averaged over folds, per cell
  feature_ablation.csv   IBS as feature blocks are added, per model
  contrasts.csv          the four designed contrasts of plan section 10.1
  ph_vs_nonph.csv        the diagnostic of plan section 16.2
  subgroups.csv          performance by relationship age and by shock period
  delta_ibs_bootstrap.csv  paired spell-block CIs on the differences that matter
  figures/*.png

Usage:  python benchmark/reports/make_reports.py --run-id v1
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from benchmark.evaluation import ibs, paired_bootstrap, summarise_differences
from benchmark.splits.rolling_origin import load_yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REPORTS = os.path.join(ROOT, "legacy", "benchmark", "reports")

METRICS = ["ibs_1_3", "ibs_1_5", "brier_1y", "brier_3y", "brier_5y",
           "antolini_c", "auc_1y", "auc_3y", "auc_5y",
           "ece_1y", "ece_3y", "ece_5y"]

# The four contrasts the model set was designed to support. Each isolates ONE
# modelling assumption; a difference read off any other pair is confounded.
CONTRASTS = [
    ("A: nonlinearity, PH held fixed", "CoxPH", "BoostedCox"),
    ("A: nonlinearity, PH held fixed (neural)", "CoxPH", "DeepSurv"),
    ("B: dropping PH, network held fixed", "DeepSurv", "CoxTime"),
    ("C: dropping PH, trees held fixed", "BoostedCox", "RSF"),
    ("D: time as an explicit input", "DeepHit", "CBNN"),
    ("D: time as an explicit input (vs CoxTime)", "CoxTime", "CBNN"),
    ("E: regularisation alone", "CoxPH", "CoxNet"),
    ("F: the classical baseline, strengthened", "Cloglog", "Cloglog-theory"),
]

FS_ORDER = ["F0", "F0F1", "F0F1F2", "F0F1F2F3", "F0F1F2F3F4", "F0F1F2F3F4F5"]


def leaderboard(df: pd.DataFrame, primary: str = "ibs_1_3") -> pd.DataFrame:
    g = (df.groupby(["feature_set", "model", "family", "nonlinear", "ph"],
                    dropna=False)[METRICS + ["fit_seconds"]]
           .agg(["mean", "std"]))
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    g = g.reset_index()
    g["feature_set"] = pd.Categorical(g["feature_set"], FS_ORDER, ordered=True)
    return g.sort_values(["feature_set", f"{primary}_mean"])


def ablation(df: pd.DataFrame, primary: str = "ibs_1_3") -> pd.DataFrame:
    piv = df.pivot_table(index="model", columns="feature_set", values=primary,
                         aggfunc="mean")
    piv = piv.reindex(columns=[c for c in FS_ORDER if c in piv.columns])
    out = piv.copy()
    if "F0" in out.columns:
        for c in out.columns:
            out[f"gain_vs_F0_{c}"] = piv["F0"] - piv[c]
    return out.reset_index()


def contrasts(df: pd.DataFrame, primary: str = "ibs_1_3") -> pd.DataFrame:
    """Paired over (feature set, fold): both models saw identical rows.

    The `*_delta_ibs` columns hold the difference in `primary` (named in the
    `metric` column), so a one-year-only run can reuse the same table."""
    rows = []
    piv = df.pivot_table(index=["feature_set", "fold"], columns="model",
                         values=primary)
    pivc = df.pivot_table(index=["feature_set", "fold"], columns="model",
                          values="antolini_c")
    for label, a, b in CONTRASTS:
        if a not in piv.columns or b not in piv.columns:
            continue
        d = (piv[b] - piv[a]).dropna()
        dc = (pivc[b] - pivc[a]).dropna()
        if d.empty:
            continue
        rows.append({"contrast": label, "metric": primary,
                     "from": a, "to": b, "n_cells": len(d),
                     "mean_delta_ibs": d.mean(), "sd_delta_ibs": d.std(ddof=1),
                     "cells_improved": int((d < 0).sum()),
                     "mean_delta_antolini": dc.mean() if not dc.empty else np.nan})
    return pd.DataFrame(rows)


def ph_diagnostic(df: pd.DataFrame, primary: str = "ibs_1_3") -> pd.DataFrame:
    d = df[df["model"] != "KM"].copy()
    d["ph_family"] = np.where(d["ph"].astype(str) == "True", "PH", "non-PH")
    out = (d.groupby(["feature_set", "ph_family"])[
              [primary, "antolini_c", "ece_3y"]].mean().reset_index())
    piv = out.pivot(index="feature_set", columns="ph_family", values=primary)
    if {"PH", "non-PH"} <= set(piv.columns):
        piv["nonPH_minus_PH"] = piv["non-PH"] - piv["PH"]
    return piv.reset_index()


def subgroups(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in df.columns if c.startswith("ibs_age")
            or c in ("ibs_gfc", "ibs_pre_covid", "ibs_covid", "ibs_post_covid",
                     "ibs_early", "ibs_pre_evfta", "ibs_post_evfta")]
    return (df.groupby(["feature_set", "model"])[cols].mean()
              .reset_index().sort_values(["feature_set", "model"]))


def bootstrap_deltas(run_dir: str, hz: dict, cfg: dict,
                     feature_set: str, reference: str = "CoxPH",
                     integrate_over: list[int] | None = None) -> pd.DataFrame:
    """Spell-block paired CIs on IBS differences, on the stored predictions."""
    pdir = os.path.join(run_dir, "predictions")
    if not os.path.isdir(pdir):
        return pd.DataFrame()
    files = [f for f in os.listdir(pdir) if f.startswith(f"{feature_set}__")]
    by_fold: dict[int, dict[str, str]] = {}
    for f in files:
        fs, fold, model = f[:-4].split("__")
        by_fold.setdefault(int(fold[4:]), {})[model] = os.path.join(pdir, f)

    grid, ig = hz["grid"], integrate_over or hz["ibs_integrate_over"]
    nb, seed = cfg["evaluation"]["bootstrap"]["n_boot"], \
        cfg["evaluation"]["bootstrap"]["seed"]
    rows = []
    for fold, models in sorted(by_fold.items()):
        if reference not in models:
            continue
        ref = np.load(models[reference], allow_pickle=False)
        S_ref, dur, ev, sid = ref["S"], ref["duration"], ref["event"], ref["spell_id"]
        for m, path in sorted(models.items()):
            if m == reference:
                continue
            cur = np.load(path, allow_pickle=False)
            S = cur["S"]
            if S.shape != S_ref.shape:
                continue

            def diff(idx, S=S, S_ref=S_ref):
                return (ibs(S[idx], dur[idx], ev[idx], ig, grid)
                        - ibs(S_ref[idx], dur[idx], ev[idx], ig, grid))

            b = paired_bootstrap(diff, sid, n_boot=nb, seed=seed + fold)
            rows.append({"feature_set": feature_set, "fold": fold, "model": m,
                         "reference": reference, "delta_ibs": diff(np.arange(len(dur))),
                         "boot_mean": b["mean"], "ci_lo": b["lo"], "ci_hi": b["hi"],
                         "significant": bool(b["hi"] < 0 or b["lo"] > 0)})
    return pd.DataFrame(rows)


def figures(lb: pd.DataFrame, abl: pd.DataFrame, out_dir: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(out_dir, exist_ok=True)
    full = lb[lb["feature_set"] == FS_ORDER[-1]].sort_values("ibs_1_3_mean")
    if not full.empty:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        ax.barh(full["model"], full["ibs_1_3_mean"],
                xerr=full["ibs_1_3_std"].fillna(0), color="#4C72B0")
        ax.set_xlabel("Integrated Brier Score, 1-3 years (lower is better)")
        ax.set_title(f"Full feature set {FS_ORDER[-1]}, mean over rolling-origin folds")
        ax.invert_yaxis()
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "leaderboard_ibs.png"), dpi=150)
        plt.close(fig)

    cols = [c for c in FS_ORDER if c in abl.columns]
    if cols:
        fig, ax = plt.subplots(figsize=(7.5, 4.6))
        for _, r in abl.iterrows():
            ax.plot(range(len(cols)), [r[c] for c in cols], marker="o",
                    label=r["model"])
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels(cols, rotation=20)
        ax.set_ylabel("IBS 1-3y")
        ax.set_title("Feature ablation: what the economics adds, per algorithm")
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "feature_ablation.png"), dpi=150)
        plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="v1")
    ap.add_argument("--benchmark-config", default="benchmark.yaml")
    ap.add_argument("--horizons-config", default="horizons.yaml")
    ap.add_argument("--out-dir", default=REPORTS,
                    help="where CSVs and figures go (default: benchmark/reports)")
    ap.add_argument("--primary", default="ibs_1_3", choices=["ibs_1_3", "brier_1y"],
                    help="brier_1y for a run whose test block has one year of "
                         "follow-up, where IBS 1-3 is unobservable")
    args = ap.parse_args()
    out, primary = args.out_dir, args.primary
    run_dir = os.path.join(ROOT, "legacy", "benchmark", "runs", args.run_id)
    df = pd.read_parquet(os.path.join(run_dir, "metrics.parquet"))
    cfg = load_yaml(args.benchmark_config)
    hz = load_yaml(args.horizons_config)
    os.makedirs(out, exist_ok=True)

    lb = leaderboard(df, primary)
    abl = ablation(df, primary)
    lb.to_csv(os.path.join(out, "leaderboard.csv"), index=False)
    abl.to_csv(os.path.join(out, "feature_ablation.csv"), index=False)
    contrasts(df, primary).to_csv(os.path.join(out, "contrasts.csv"), index=False)
    ph_diagnostic(df, primary).to_csv(os.path.join(out, "ph_vs_nonph.csv"), index=False)
    subgroups(df).to_csv(os.path.join(out, "subgroups.csv"), index=False)
    ig = [1] if primary == "brier_1y" else None
    boots = [bootstrap_deltas(run_dir, hz, cfg, fs, integrate_over=ig)
             for fs in ("F0F1F2F3", "F0F1F2F3F4")]
    boots = [b for b in boots if not b.empty]
    if boots:
        pd.concat(boots).to_csv(
            os.path.join(out, "delta_ibs_bootstrap.csv"), index=False)
    if primary == "ibs_1_3":
        figures(lb, abl, os.path.join(out, "figures"))
    print(f"wrote reports to {out}")
    print(lb[lb.feature_set == FS_ORDER[-1]][
        ["model", f"{primary}_mean", "antolini_c_mean", "ece_1y_mean"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
