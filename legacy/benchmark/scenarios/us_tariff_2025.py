"""Phase 5 - prospective scoring of the 2025 US reciprocal tariff.

This is deliberately NOT part of the leaderboard, and the reason is in the
panel's own event convention. `event = 1` in year Y means the relationship is
last alive in Y and dies in Y+1, so a relationship alive through 2025 can only
reveal its post-2025 fate in data that does not exist yet. Any number produced
here is therefore a MODEL EXTRAPOLATION under an assumed tariff, not an estimate
of a realised effect (plan section 11.3). The output filename says so.

What is actually computed: a model trained only on origins through 2023 - where
tariffs are contemporaneously measured - is asked to score the 2024 and 2025
origins under four tariff conventions for the United States:

    observed      the panel's own tariff_rate, unchanged
    yearend       plus the rate in force at the end of 2025 (20%)
    peak          plus the highest rate reached during 2025 (46%)
    day_weighted  plus the day-weighted average across the four rate changes

The three conventions are all in the panel because the data handoff records that
choosing between them is a research decision, not a data question. Scoring all
three is what makes the choice visible instead of silently baked in.

The counterfactual is applied to `tariff_rate` itself rather than to the
`us_recip_*` columns, which are banned from every feature set. That is the point:
the model learned a tariff-to-hazard relationship from twenty years of ordinary
tariff variation, and the scenario asks what that relationship implies at a rate
outside the historical range. Extrapolation of exactly that kind is the weakest
part of the exercise and is the reason the exposure table below reports how far
outside the training support each scenario sits.

Usage:  python benchmark/scenarios/us_tariff_2025.py --model Cloglog
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from benchmark.features.preprocess import Preprocessor
from benchmark.models import FitContext, build_registry
from benchmark.splits.rolling_origin import (censor_block, load_matrix,
                                             load_yaml, subsample)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "legacy", "benchmark", "reports")
US_CODES = {"USA", "US", "United States", "United States of America", "840"}


def us_scenarios(panel_path: str, years: list[int]) -> pd.DataFrame:
    """The three published conventions for the 2025 rate, from the panel."""
    cols = ["spell_id", "year", "us_recip_rate_yearend", "us_recip_rate_peak",
            "us_recip_rate_days_wt"]
    df = pd.read_parquet(panel_path, columns=cols)
    return df[df["year"].isin(years)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Cloglog")
    ap.add_argument("--feature-set", default="F0F1F2F3F4")
    args = ap.parse_args()

    cfg, hz = load_yaml("benchmark.yaml"), load_yaml("horizons.yaml")
    grid = hz["grid"]
    m = load_matrix()

    w = cfg["window"]
    train = censor_block(m[m.in_leaderboard_window == 1], w["first_origin_year"],
                         w["last_origin_year"], w["last_origin_year"])
    train = subsample(train, cfg["sampling"]["train_max_rows"],
                      cfg["sampling"]["seed"])
    future = m[m["year"].isin(w["prospective_years"])].copy()
    if future.empty:
        print("no prospective origins in the matrix")
        return 1

    prep = Preprocessor(args.feature_set).fit(train)
    reg = build_registry(cfg)
    model = reg[args.model]
    rng = np.random.default_rng(cfg["sampling"]["seed"])
    ctx = FitContext(prep.transform(train), train["duration"].to_numpy(),
                     train["event"].to_numpy(),
                     prep.transform(train), train["duration"].to_numpy(),
                     train["event"].to_numpy(),
                     age_train=train["t_stop"].to_numpy(),
                     age_valid=train["t_stop"].to_numpy(),
                     names=prep.names, seed=1)
    fitted = model.fit(ctx, model.param_space(rng, 1)[0])

    scen = us_scenarios(os.path.join(ROOT, cfg["panel"]["path"]),
                        w["prospective_years"])
    future = future.merge(scen, on=["spell_id", "year"], how="left")
    is_us = future["importer"].astype(str).isin(US_CODES)
    print(f"prospective origins {w['prospective_years']}: {len(future):,} "
          f"({int(is_us.sum()):,} to the United States)")
    if is_us.sum() == 0:
        print("  the panel's importer codes do not match the US code list; "
              "widen US_CODES before reading the table below")

    # the historical support the extrapolation is leaving
    trained_max = float(np.nanmax(train["tariff_rate"]))
    rows, base_S = [], None
    for name, col in (("observed", None),
                      ("yearend", "us_recip_rate_yearend"),
                      ("peak", "us_recip_rate_peak"),
                      ("day_weighted", "us_recip_rate_days_wt")):
        f = future.copy()
        if col is not None:
            add = pd.to_numeric(f[col], errors="coerce").fillna(0.0)
            # tariff_rate is stored as log1p of the percentage rate
            raw = np.expm1(f["tariff_rate"].fillna(0.0))
            f.loc[is_us, "tariff_rate"] = np.log1p(
                (raw + add).clip(lower=0))[is_us]
        S = fitted.predict_survival(prep.transform(f), grid,
                                    age=f["t_stop"].to_numpy())
        if base_S is None:
            base_S = S
        for label, mask in (("all", np.ones(len(f), bool)), ("us_only", is_us.to_numpy())):
            if mask.sum() == 0:
                continue
            rows.append({
                "scenario": name, "group": label, "n_origins": int(mask.sum()),
                "mean_S1": float(S[mask, 0].mean()),
                "mean_S3": float(S[mask, grid.index(3)].mean()),
                "delta_S1_vs_observed": float((S[mask, 0] - base_S[mask, 0]).mean()),
                "delta_S3_vs_observed": float(
                    (S[mask, grid.index(3)] - base_S[mask, grid.index(3)]).mean()),
                "max_tariff_pct_in_scenario": float(
                    np.nanmax(np.expm1(f.loc[mask, "tariff_rate"]))),
                "max_tariff_pct_in_training": float(np.expm1(trained_max)),
            })
    out = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "us2025_prospective_scenarios_NOT_A_RESULT.csv")
    out.to_csv(path, index=False)
    print(out.to_string(index=False))
    print(f"\nwrote {path}")
    print("These are extrapolations under an assumed tariff. No post-2025 "
          "outcome exists, so none of them is an estimated effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
