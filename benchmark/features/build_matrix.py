"""Build the frozen benchmark matrix: one row per prediction origin.

Reads benchmark/features/feature_registry.yaml and produces exactly the columns
it names - nothing else reaches a model. Four things happen here and nowhere
else, because each of them is a decision about the *task* rather than about a
model, and the plan (section 11.1) requires the task to be frozen first.

1.  **Origins.** A row of the panel is a prediction origin (importer, product,
    year). Sub-threshold padding years (`gap_filled`) are not live episodes, so
    they are not origins.

2.  **The target.** The panel's convention is that `event = 1` in year Y means
    the relationship is last alive in Y and dies in Y+1. So for an origin in year
    t the remaining lifetime is

        duration_u = last_year_alive - t + 1,

    which makes `duration_u = 1, event_u = 1` identical to `event = 1` on the
    origin row. That identity is asserted at the end of the build.

3.  **Derived features** the panel does not already carry: the spell's launch
    value, the destination's exchange-rate movement, the two Lawless-Studnicka
    experience counters adapted to a country-product panel, and the tariff shock.

4.  **Registry transforms.** Logs and clips only. No imputation and no scaling
    happen here: both are fitted per fold on training rows alone
    (benchmark/features/preprocess.py), because fitting them on the whole panel
    would leak the test period's distribution into the training scaler.

Output: data/interim/benchmark_matrix.parquet

Run:  python benchmark/features/build_matrix.py
"""

from __future__ import annotations

import argparse
import gc
import os
import sys

import numpy as np
import pandas as pd
import yaml

import eu27_scope

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REGISTRY = os.path.join(HERE, "feature_registry.yaml")
CONFIG = os.path.join(ROOT, "benchmark", "config", "benchmark.yaml")
OUT = os.path.join(ROOT, "data", "interim", "benchmark_matrix.parquet")
EU_MAPPING = os.path.join(ROOT, "selection", "eu_tariff_mapping.csv")

KEYS = ["spell_id", "importer", "product_family", "hs2", "year", "t_stop",
        "spell_start_year", "right_censored", "event"]
# left_trunc is a KEY column in the panel but a registered F0 feature here, so it
# is read through the registry and must not be duplicated into the key block.

# Columns needed only to construct derived features.
DERIVED_INPUTS = ["import_value_usd", "importer_exchange_rate_lcu_per_usd",
                  "tariff_rate", "tariff_rate_lag1", "gap_filled"]


def load_registry(path=REGISTRY):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config(path=CONFIG):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def transform(name: str, s: pd.Series) -> pd.Series:
    """The registry's transform vocabulary. Deliberately tiny."""
    # float32: rolling_origin.load_matrix() downcasts to float32 immediately
    # after this file is read anyway, so float64 here is a wasted peak - and
    # this box only has 8GB total.
    x = pd.to_numeric(s, errors="coerce").astype("float32")
    if name in ("identity", "precomputed"):
        return x
    if name == "log1p":
        return np.log1p(x.clip(lower=0))
    if name == "log1p_clip0":
        return np.log1p(x.clip(lower=0))
    if name == "log_clip1":
        return np.log(x.clip(lower=1))
    if name == "clip_pct":
        # growth/inflation series carry hyperinflation and division artefacts;
        # winsorising at +-500% keeps them from dominating a standardiser
        return x.clip(lower=-500, upper=500)
    raise ValueError(f"unknown transform {name!r}")


def build_derived(panel: pd.DataFrame) -> pd.DataFrame:
    """The five columns the panel does not already carry."""
    out = pd.DataFrame(index=panel.index)

    # --- launch value of the spell (Nitsch's initial trade value)
    first = (panel.sort_values(["spell_id", "year"])
                  .groupby("spell_id", sort=False)["import_value_usd"].first())
    out["log_initial_value"] = np.log1p(
        panel["spell_id"].map(first).clip(lower=0))

    # --- destination exchange-rate movement between t-2 and t-1
    fx = (panel[["importer", "year", "importer_exchange_rate_lcu_per_usd"]]
          .drop_duplicates(["importer", "year"])
          .sort_values(["importer", "year"]))
    fx["lfx"] = np.log(fx["importer_exchange_rate_lcu_per_usd"].clip(lower=1e-9))
    fx["fx_change"] = fx.groupby("importer", sort=False)["lfx"].diff()
    # value dated t-1 is the change from t-2 to t-1
    fx["year"] = fx["year"] + 1
    out["fx_change_lag"] = panel.merge(
        fx[["importer", "year", "fx_change"]], on=["importer", "year"],
        how="left")["fx_change"].to_numpy()

    # --- experience counters, adapted from Lawless & Studnicka to a country-
    # product panel: the firm dimension does not exist here, so "the firm has
    # exported before" becomes "Vietnam has been present in this destination /
    # this product before". Counted on live episodes only.
    for col, name in (("importer", "exp_dest"), ("product_family", "exp_prod")):
        present = (panel[[col, "year"]].drop_duplicates()
                                       .sort_values([col, "year"]))
        # number of distinct earlier years in which the unit was present
        present["n_prior"] = present.groupby(col, sort=False).cumcount()
        out[name] = panel.merge(present, on=[col, "year"],
                                how="left")["n_prior"].to_numpy()

    # --- tariff shock
    out["tariff_change"] = (pd.to_numeric(panel["tariff_rate"], errors="coerce")
                            - pd.to_numeric(panel["tariff_rate_lag1"],
                                            errors="coerce"))
    return out


def build_target(panel: pd.DataFrame) -> pd.DataFrame:
    """Remaining lifetime from each origin, plus the spell's own end facts.

    Administrative censoring at a fold's training horizon is NOT applied here -
    it depends on the fold and is applied in benchmark/splits/rolling_origin.py.
    What is stored is the fully-observed truth, read forward to the end of the
    data window.
    """
    g = panel.groupby("spell_id", sort=False)
    last_alive = g["year"].max().rename("last_alive_year")
    died = g["event"].max().rename("spell_died")
    out = panel[["spell_id", "year"]].merge(
        pd.concat([last_alive, died], axis=1), on="spell_id", how="left")
    out["duration_u"] = out["last_alive_year"] - out["year"] + 1
    out["event_u"] = out["spell_died"].astype("int8")
    return out[["last_alive_year", "spell_died", "duration_u", "event_u"]]


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--registry", default=REGISTRY)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--eu27-only", action="store_true",
                    help="restrict origins to the B0 EU-27 main sample (by "
                         "year, GBR excluded - see eu27_scope.py) - applied AFTER "
                         "exp_dest/exp_prod are computed on the full panel, "
                         "so global VN export experience is never undercounted")
    ap.add_argument("--eu-mapping", default=EU_MAPPING)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    reg = load_registry(args.registry)
    cfg = load_config(args.config)
    feats = reg["features"]

    src_cols = sorted({v["source"] for v in feats.values()
                       if v["source"] != "derived"})
    need = sorted(set(KEYS) | set(src_cols) | set(DERIVED_INPUTS))

    print(f"Reading {cfg['panel']['path']}  ({len(need)} columns)")
    panel = pd.read_parquet(os.path.join(ROOT, cfg["panel"]["path"]),
                            columns=need)
    # Halve the resident footprint immediately - this machine has 8GB total
    # and build_matrix.py has previously been OOM-killed at this scale.
    f64 = panel.select_dtypes("float64").columns
    panel[f64] = panel[f64].astype("float32")
    print(f"  {len(panel):,} episode-years, {panel.spell_id.nunique():,} spells")

    # --- origins ------------------------------------------------------------
    if cfg["exclusions"]["drop_gap_filled_rows"]:
        n0 = len(panel)
        panel = panel[panel["gap_filled"] == 0].copy()
        print(f"  dropped {n0 - len(panel):,} gap-filled padding rows")

    panel = panel.sort_values(["spell_id", "year"]).reset_index(drop=True)

    # --- target -------------------------------------------------------------
    tgt = build_target(panel)

    # --- features -----------------------------------------------------------
    derived = build_derived(panel)
    cols = {}
    for name, spec in feats.items():
        src = derived[name] if spec["source"] == "derived" else panel[spec["source"]]
        cols[name] = transform(spec["transform"], src)
    X = pd.DataFrame(cols)
    keys_only = panel[KEYS].reset_index(drop=True)

    out = pd.concat([keys_only, tgt.reset_index(drop=True),
                     X.reset_index(drop=True)], axis=1)

    # This box has 8GB total and has OOM-killed this script before at this
    # scale; panel/derived/X/cols are fully absorbed into `out` by this point
    # and are never read again, so free them before the window/EU27 filters
    # and the write, rather than let them idle until the function returns.
    del panel, derived, X, cols, keys_only
    gc.collect()

    # --- window -------------------------------------------------------------
    w = cfg["window"]
    keep = (out["year"] >= w["first_origin_year"]) & \
           (out["year"] <= max(w["last_origin_year"], max(w["prospective_years"])))
    out = out[keep].copy()
    out["in_leaderboard_window"] = (out["year"] <= w["last_origin_year"]).astype("int8")

    # --- EU27 scope (applied AFTER derived features, never before - see
    # eu27_scope.py docstring and the module docstring above) --------------
    if args.eu27_only:
        n0 = len(out)
        out = eu27_scope.filter_eu27(out, args.eu_mapping)
        print(f"  --eu27-only: kept {len(out):,}/{n0:,} rows "
              f"(importer in the B0 EU-27 sample that origin year)")

    # --- assertions the whole benchmark rests on ---------------------------
    lead = out[out["in_leaderboard_window"] == 1]
    one_year = lead["duration_u"] == 1
    bad = int(((one_year & (lead["event_u"] == 1)) != (lead["event"] == 1)).sum())
    assert bad == 0, (
        f"{bad} rows where 'duration_u==1 and event_u==1' disagrees with the "
        "panel's own event flag - the target convention is wrong")
    assert (out["duration_u"] >= 1).all(), "non-positive remaining lifetime"
    assert out.groupby("spell_id")["last_alive_year"].nunique().max() == 1

    print(f"\n  matrix: {len(out):,} origins x {len(feats)} features")
    print(f"  leaderboard window {w['first_origin_year']}-{w['last_origin_year']}: "
          f"{len(lead):,} origins, {int(lead['event_u'].sum()):,} eventually fail, "
          f"{int(((lead['duration_u'] == 1) & (lead['event_u'] == 1)).sum()):,} "
          f"fail within one year")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    out.to_parquet(args.out, index=False, compression="zstd")
    print(f"  wrote {args.out}  ({os.path.getsize(args.out)/1e6:.0f} MB)")

    miss = out[list(feats)].isna().mean().sort_values(ascending=False)
    print("\n  missingness of the ten sparsest features (imputed per fold, "
          "never here):")
    for k, v in miss.head(10).items():
        print(f"    {k:<28} {v:6.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
