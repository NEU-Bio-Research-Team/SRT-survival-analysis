"""The benchmark runner: one cell = (feature set x fold x model).

Everything that makes this a fair comparison rather than a leaderboard of
convenience lives in the order of operations here, so it is worth stating:

1.  The fold is cut first, and TRAINING OUTCOMES ARE CENSORED at the end of the
    training window (splits/rolling_origin.py). No model can see a death that had
    not happened yet.
2.  The preprocessor is fitted on the training block ALONE and then frozen. Every
    model in the cell receives the identical matrix - same columns, same
    imputations, same scaling.
3.  Every tunable model gets the same number of trials from its budget class, and
    all of them select on the same validation score (one-year IPCW Brier, the
    only horizon a leak-free validation block can support).
4.  Every model is scored on the identical test rows with the identical metric
    code, reading only S(u | X).

A cell writes one JSON file, so the run is resumable and a crash in DeepHit on
fold 3 does not cost the other 250 cells.

Usage
    python benchmark/run_benchmark.py --run-id v1
    python benchmark/run_benchmark.py --run-id v1 --models CoxPH,RSF --folds 1
    python benchmark/run_benchmark.py --run-id v1 --resume
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
import traceback
import warnings

import numpy as np
import pandas as pd
import yaml

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.evaluation import (antolini_concordance, brier_at,
                                  calibration_table, dynamic_auc,
                                  expected_calibration_error, ibs)
from benchmark.features.preprocess import (FEATURE_SETS, Preprocessor,
                                           load_registry as load_feat_registry)
from benchmark.models import FitContext, build_registry
from benchmark.splits.rolling_origin import load_yaml, make_folds

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS = os.path.join(ROOT, "legacy", "benchmark", "runs")

# The COVID-era test block is fold 3; the shock split of plan section 16.4 is
# read off the origin year rather than off a hand-drawn regime label.
SHOCK_PERIODS = {"gfc": (2008, 2009), "pre_covid": (2010, 2019),
                 "covid": (2020, 2021), "post_covid": (2022, 2023),
                 "early": (2003, 2007)}

# For a window confined to 2012-2024 (the EU27/B0 rescope), gfc/early fall
# entirely outside it and would just produce empty subgroups; this variant
# also gives a first, purely descriptive pre/post-EVFTA split (EVFTA entered
# force 1 Aug 2020) without doing the full B6 causal identification.
SHOCK_PERIODS_EU27 = {"pre_evfta": (2012, 2019), "covid": (2020, 2021),
                      "post_evfta": (2022, 2024)}


def age_group(age: np.ndarray) -> np.ndarray:
    """Plan section 16.3: half of all spells last one year, so a model that only
    learns the first-year hazard can look strong overall. Split the metrics."""
    g = np.full(len(age), "age4plus", dtype=object)
    g[age <= 1] = "age1"
    g[(age >= 2) & (age <= 3)] = "age2_3"
    return g


def score(S, dur, ev, grid, horizons, ibs_grid, ibs_grid_ext, bins):
    out = {}
    out["ibs_1_3"] = ibs(S, dur, ev, ibs_grid, grid)
    out["ibs_1_5"] = ibs(S, dur, ev, ibs_grid_ext, grid)
    for u in horizons:
        out[f"brier_{u}y"] = brier_at(S, dur, ev, u, grid)
        out[f"auc_{u}y"] = dynamic_auc(S, dur, ev, u, grid)
        tab = calibration_table(S, dur, ev, u, grid, bins)
        out[f"ece_{u}y"] = expected_calibration_error(tab)
    out["antolini_c"] = antolini_concordance(S, dur, ev, grid)
    return out


def run_cell(model_name, model, fs, fold_id, tr, va, te, prep, cfg, hz, rng,
            shock_periods=SHOCK_PERIODS):
    grid = hz["grid"]
    Ztr, Zva, Zte = prep.transform(tr), prep.transform(va), prep.transform(te)

    # per-model row cap on top of the shared one; recorded, not hidden
    cap = getattr(model, "max_train_rows", None)
    if cap and len(Ztr) > cap:
        keep = rng.choice(len(Ztr), cap, replace=False)
        Ztr_m, tr_m = Ztr[keep], tr.iloc[keep]
    else:
        Ztr_m, tr_m = Ztr, tr

    ctx = FitContext(Ztr_m, tr_m["duration"].to_numpy(), tr_m["event"].to_numpy(),
                     Zva, va["duration"].to_numpy(), va["event"].to_numpy(),
                     age_train=tr_m["t_stop"].to_numpy(),
                     age_valid=va["t_stop"].to_numpy(),
                     names=prep.names, seed=cfg["tuning"]["seeds"][0])

    n_trials = cfg["tuning"]["n_trials"][model.budget]
    trials = model.param_space(rng, n_trials)
    best, best_score, best_params = None, np.inf, None
    t0 = time.time()
    for params in trials:
        fitted = model.fit(ctx, params)
        Sva = fitted.predict_survival(Zva, grid, age=va["t_stop"].to_numpy())
        s = brier_at(Sva, va["duration"].to_numpy(), va["event"].to_numpy(),
                     1, grid)
        if np.isfinite(s) and s < best_score:
            best_score, best_params = s, params
            best = fitted
        if len(trials) == 1:
            break
    if best is None:
        raise RuntimeError("every tuning trial failed to score")
    fit_seconds = time.time() - t0

    Ste = best.predict_survival(Zte, grid, age=te["t_stop"].to_numpy())
    dur, ev = te["duration"].to_numpy(), te["event"].to_numpy()
    row = {"model": model_name, "feature_set": fs, "fold": fold_id,
           "family": model.family, "nonlinear": bool(model.nonlinear),
           "ph": model.ph, "n_features": Ztr.shape[1],
           "n_train": int(len(Ztr_m)), "n_valid": int(len(Zva)),
           "n_test": int(len(Zte)), "valid_brier_1y": float(best_score),
           "fit_seconds": round(fit_seconds, 1),
           "best_params": json.dumps(best_params, default=str)}
    row.update(score(Ste, dur, ev, grid, hz["calibration_at"],
                     hz["ibs_integrate_over"], hz["ibs_integrate_over_extended"],
                     hz["calibration_bins"]))

    # --- subgroup readings (plan sections 16.3 and 16.4)
    ages = age_group(te["t_stop"].to_numpy())
    for g in ("age1", "age2_3", "age4plus"):
        m = ages == g
        row[f"ibs_{g}"] = ibs(Ste[m], dur[m], ev[m], hz["ibs_integrate_over"],
                              grid) if m.sum() > 200 else np.nan
    yrs = te["year"].to_numpy()
    for nm, (lo, hi) in shock_periods.items():
        m = (yrs >= lo) & (yrs <= hi)
        row[f"ibs_{nm}"] = ibs(Ste[m], dur[m], ev[m], hz["ibs_integrate_over"],
                               grid) if m.sum() > 200 else np.nan
    return row, Ste


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="v1")
    ap.add_argument("--models", default="")
    ap.add_argument("--feature-sets", default="")
    ap.add_argument("--folds", default="")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--benchmark-config", default="benchmark.yaml",
                    help="filename inside benchmark/config/")
    ap.add_argument("--splits-config", default="splits.yaml",
                    help="filename inside benchmark/config/")
    ap.add_argument("--horizons-config", default="horizons.yaml",
                    help="filename inside benchmark/config/")
    ap.add_argument("--registry", default="feature_registry.yaml",
                    help="filename inside benchmark/features/")
    ap.add_argument("--matrix", default=None,
                    help="override path to the frozen matrix parquet "
                         "(default: data/interim/benchmark_matrix.parquet)")
    ap.add_argument("--shock-periods", choices=["global", "eu27"],
                    default="global")
    args = ap.parse_args()

    cfg = load_yaml(args.benchmark_config)
    hz = load_yaml(args.horizons_config)
    shock_periods = SHOCK_PERIODS_EU27 if args.shock_periods == "eu27" else SHOCK_PERIODS
    run_dir = os.path.join(RUNS, args.run_id)
    cells_dir = os.path.join(run_dir, "cells")
    preds_dir = os.path.join(run_dir, "predictions")
    os.makedirs(cells_dir, exist_ok=True)
    os.makedirs(preds_dir, exist_ok=True)

    # config snapshot - a metric is only interpretable against the task that
    # produced it, so the task travels with the numbers
    for f in (args.benchmark_config, args.splits_config, args.horizons_config):
        shutil.copy(os.path.join(ROOT, "legacy", "benchmark", "config", f),
                    os.path.join(run_dir, f"config_{f}"))
    shutil.copy(os.path.join(ROOT, "legacy", "benchmark", "features", args.registry),
                os.path.join(run_dir, "config_feature_registry.yaml"))

    feat_registry = load_feat_registry(
        os.path.join(ROOT, "legacy", "benchmark", "features", args.registry))
    registry = build_registry(cfg)
    models = ([m for m in args.models.split(",") if m] or list(registry))
    fsets = ([f for f in args.feature_sets.split(",") if f] or list(FEATURE_SETS))
    want_folds = {int(x) for x in args.folds.split(",") if x}
    store_preds = {"F0F1F2F3", "F0F1F2F3F4"}

    rng_master = np.random.default_rng(cfg["sampling"]["seed"])
    n_fold_guess = len(load_yaml(args.splits_config)["folds"])
    total = len(models) * len(fsets) * (len(want_folds) or n_fold_guess)
    done = 0
    print(f"run {args.run_id}: {len(models)} models x {len(fsets)} feature sets "
          f"x folds -> {total} cells\n")

    for fold_id, tr, va, te in make_folds(
            benchmark_config=args.benchmark_config,
            splits_config=args.splits_config, matrix_path=args.matrix):
        if want_folds and fold_id not in want_folds:
            continue
        for fs in fsets:
            prep = Preprocessor(fs, registry=feat_registry).fit(tr)
            for mname in models:
                done += 1
                tag = f"{fs}__fold{fold_id}__{mname}"
                out_json = os.path.join(cells_dir, f"{tag}.json")
                if args.resume and os.path.exists(out_json):
                    print(f"[{done:>3}/{total}] {tag:<45} skip (done)")
                    continue
                rng = np.random.default_rng(
                    abs(hash((fs, fold_id, mname))) % (2 ** 32))
                try:
                    row, S = run_cell(mname, registry[mname], fs, fold_id,
                                      tr, va, te, prep, cfg, hz, rng,
                                      shock_periods=shock_periods)
                    with open(out_json, "w") as f:
                        json.dump(row, f)
                    if fs in store_preds:
                        np.savez_compressed(
                            os.path.join(preds_dir, f"{tag}.npz"),
                            S=S.astype("float32"),
                            spell_id=te["spell_id"].to_numpy().astype("U40"),
                            year=te["year"].to_numpy(),
                            age=te["t_stop"].to_numpy(),
                            duration=te["duration"].to_numpy(),
                            event=te["event"].to_numpy())
                    print(f"[{done:>3}/{total}] {tag:<45} "
                          f"IBS {row['ibs_1_3']:.5f}  C {row['antolini_c']:.4f}  "
                          f"{row['fit_seconds']:.0f}s")
                except Exception as exc:
                    print(f"[{done:>3}/{total}] {tag:<45} FAILED {type(exc).__name__}: {exc}")
                    with open(os.path.join(cells_dir, f"{tag}.error"), "w") as f:
                        f.write(traceback.format_exc())

    rows = [json.load(open(os.path.join(cells_dir, f)))
            for f in sorted(os.listdir(cells_dir)) if f.endswith(".json")]
    if rows:
        df = pd.DataFrame(rows)
        df.to_parquet(os.path.join(run_dir, "metrics.parquet"), index=False)
        print(f"\nwrote {run_dir}/metrics.parquet  ({len(df)} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
