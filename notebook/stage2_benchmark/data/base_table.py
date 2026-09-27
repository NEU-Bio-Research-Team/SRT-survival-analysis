"""Build the EU27 base table: one row per active origin (importer, family, year).

Everything here is a function of the Stage 1 panel only and is prefix-safe: a
value on the row for year t reads nothing dated after t. Fold-specific work
(re-censoring at a cutoff, imputation, scaling) happens later, in views.py and
features/preprocess.py.

Steps
  1. Spell facts on the FULL panel (147 importers): last active year E, whether
     the spell died, start year. These carry outcome information and are kept
     under `_y_` names that no feature list may contain; views.py uses them to
     re-censor at a cutoff.
  2. Constructed features that need history across importers or spells (H block,
     EU27 market counts, initial value), computed on the full panel BEFORE the
     EU27 filter so no history is undercounted.
  3. The EU27 filter (27 post-Brexit members, fixed for every year - the
     definition scripts/audit_stage1.py uses for B0) on active rows
     (gap_filled == 0), years 2002-2025.
  4. Registry transforms and as-of rules. No imputation.

Output: artifacts/views/base_eu27.parquet  (+ base_eu27.meta.json)

Run:  python -m stage2_benchmark.data.base_table
"""

from __future__ import annotations

import gc
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from stage2_benchmark import paths  # noqa: E402  (sets thread limits first)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

OUT = os.path.join(paths.VIEWS, "base_eu27.parquet")
META = os.path.join(paths.VIEWS, "base_eu27.meta.json")
EU_MAPPING = os.path.join(paths.NOTEBOOK, "selection", "eu_tariff_mapping.csv")

CORE_COLS = ["spell_id", "importer", "product_family", "hs2", "year",
             "spell_start_year", "gap_filled", "event", "start_reason",
             "censor_reason", "import_value_usd"]
STR_COLS = ["spell_id", "importer", "product_family", "hs2", "start_reason",
            "censor_reason"]


def eu27_members(mapping_path: str = EU_MAPPING) -> list[str]:
    eu = pd.read_csv(mapping_path)
    eun = eu[eu["tariff_reporter"] == "EUN"]
    last = eun["year"].max()
    members = sorted(eun.loc[eun["year"] == last, "iso3"].unique())
    if len(members) != 27 or "GBR" in members:
        raise ValueError(f"expected 27 post-Brexit members, got {members}")
    return members


def read_panel(columns, filters=None, panel_path=None) -> pd.DataFrame:
    t = pq.read_table(panel_path or paths.PANEL, columns=columns,
                      filters=filters,
                      read_dictionary=[c for c in columns if c in STR_COLS])
    df = t.to_pandas()
    for c in df.columns:
        if df[c].dtype == "float64":
            df[c] = df[c].astype("float32")
    return df


# --------------------------------------------------------------- spell facts
def spell_facts(p: pd.DataFrame) -> pd.DataFrame:
    act = p[p["gap_filled"] == 0]
    g = act.groupby("spell_id", observed=True)
    first_year = g["year"].min()
    s = pd.DataFrame({
        "E": g["year"].max(),
        "first_active_year": first_year,
    })
    s["died"] = p.groupby("spell_id", observed=True)["event"].max()
    s["spell_start_year"] = p.groupby("spell_id", observed=True)["spell_start_year"].first()
    first = act.merge(first_year.rename("fy"), left_on="spell_id",
                      right_index=True)
    first = first[first["year"] == first["fy"]].set_index("spell_id")
    s["initial_value"] = first["import_value_usd"]
    rel = p.drop_duplicates("spell_id").set_index("spell_id")
    s["importer"] = rel["importer"].astype(str)
    s["product_family"] = rel["product_family"].astype(str)
    return s


def prior_spell_features(s: pd.DataFrame) -> pd.DataFrame:
    """Per spell: confirmed earlier deaths of the same relation, and the last
    active year of the most recent earlier spell. Earlier spells end before this
    spell starts, and a confirmed death needs E_prev + 2 <= start, so none of
    this reads past the spell's own start year."""
    s = s.sort_values(["importer", "product_family", "spell_start_year"]).copy()
    grp = s.groupby(["importer", "product_family"], sort=False)
    s["n_prior_any"] = grp.cumcount()
    s["n_prior_confirmed"] = grp["died"].cumsum() - s["died"]
    s["prev_E"] = grp["E"].shift(1)
    # a confirmed earlier death must be confirmed by the start year
    return s


# ------------------------------------------------------ relation value history
def relation_history(p: pd.DataFrame) -> pd.DataFrame:
    """Per (relation, year) of the panel: bilateral growth, 3y trend and active
    years so far. Values come only from years present in the panel; a missing
    year is missing, never zero."""
    v = p[["importer", "product_family", "year", "import_value_usd",
           "gap_filled"]].copy()
    v["rel"] = (v["importer"].astype(str) + "|" +
                v["product_family"].astype(str))
    v["rel"] = v["rel"].astype("category").cat.codes.astype("int32")
    v = v.sort_values(["rel", "year"]).reset_index(drop=True)
    v["lv"] = np.log1p(v["import_value_usd"].clip(lower=0).astype("float64"))
    key = pd.MultiIndex.from_arrays([v["rel"], v["year"]])
    lv = pd.Series(v["lv"].to_numpy(), index=key)
    lag = {}
    for k in (1, 2, 3):
        idx = pd.MultiIndex.from_arrays([v["rel"], v["year"] - k])
        lag[k] = lv.reindex(idx).to_numpy()
    out = pd.DataFrame({"importer": v["importer"], "product_family": v["product_family"],
                        "year": v["year"]})
    out["bilateral_growth_lag1"] = lag[1] - lag[2]
    # OLS slope over x = -3,-2,-1 using the years that are present (>= 2)
    Y = np.column_stack([lag[3], lag[2], lag[1]])
    X = np.array([-3.0, -2.0, -1.0])
    m = np.isfinite(Y)
    n = m.sum(1)
    xm = np.where(n > 0, (m * X).sum(1) / np.maximum(n, 1), np.nan)
    ym = np.where(n > 0, np.where(m, Y, 0).sum(1) / np.maximum(n, 1), np.nan)
    dx = np.where(m, X - xm[:, None], 0.0)
    dy = np.where(m, np.nan_to_num(Y) - ym[:, None], 0.0)
    sxx = (dx * dx).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        slope = np.where((n >= 2) & (sxx > 0), (dx * dy).sum(1) / sxx, np.nan)
    out["trend_3y_lag1"] = slope.astype("float32")
    act = (v["gap_filled"] == 0).astype("int32")
    out["active_years_prefix"] = act.groupby(v["rel"]).cumsum().to_numpy()
    return out


def concentration_lags(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Product-destination HHI (by family) and importer-product HHI (by
    importer), both dated t-1 so they attach to origin t."""
    v = p[["importer", "product_family", "year", "import_value_usd"]].copy()
    v["x"] = v["import_value_usd"].clip(lower=0).astype("float64")
    v = v[v["x"] > 0]

    def hhi(by):
        tot = v.groupby(by + ["year"], observed=True)["x"].transform("sum")
        sh2 = (v["x"] / tot) ** 2
        h = sh2.groupby([v[c] for c in by] + [v["year"]], observed=True).sum()
        h = h.rename("hhi").reset_index()
        h["year"] = h["year"] + 1          # value dated t-1 attaches to t
        for c in by:
            h[c] = h[c].astype(str)
        return h

    hp = hhi(["product_family"]).rename(columns={"hhi": "hhi_dest_p_lag1"})
    hc = hhi(["importer"]).rename(columns={"hhi": "hhi_prod_c_lag1"})
    return hp, hc


def eu27_market_counts(p: pd.DataFrame, members: list[str]) -> pd.DataFrame:
    a = p[(p["gap_filled"] == 0) & p["importer"].astype(str).isin(members)]
    c = (a.groupby(["product_family", "year"], observed=True)["importer"]
          .nunique().rename("n_eu").reset_index())
    c["product_family"] = c["product_family"].astype(str)
    c["year"] = c["year"] + 1
    return c


# ------------------------------------------------------------- the build
def build(panel_path: str | None = None, max_year: int | None = None,
          out_path: str | None = None, verbose: bool = True) -> pd.DataFrame:
    """`max_year` truncates the panel before anything is computed - used by the
    prefix-safety test (adding future years must not change old rows)."""
    t0 = time.time()
    reg = paths.load_yaml("feature_registry.yaml")
    feats = reg["features"]
    members = eu27_members()

    p = read_panel(CORE_COLS, panel_path=panel_path)
    if max_year is not None:
        p = p[p["year"] <= max_year].reset_index(drop=True)
    if verbose:
        print(f"panel core: {len(p):,} rows, rss {paths.rss_mb():.0f} MB", flush=True)

    s = prior_spell_features(spell_facts(p))
    hist = relation_history(p)
    hp, hc = concentration_lags(p)
    neu = eu27_market_counts(p, members)
    if verbose:
        print(f"history features done, rss {paths.rss_mb():.0f} MB", flush=True)

    # --- EU27 active origins
    b = p[(p["gap_filled"] == 0) & p["importer"].astype(str).isin(members)].copy()
    del p
    gc.collect()
    for c in ("importer", "product_family", "hs2", "spell_id"):
        b[c] = b[c].astype(str)
    b = b.merge(s[["E", "died", "initial_value", "n_prior_any",
                   "n_prior_confirmed", "prev_E"]],
                left_on="spell_id", right_index=True, how="left")
    hist["importer"] = hist["importer"].astype(str)
    hist["product_family"] = hist["product_family"].astype(str)
    b = b.merge(hist, on=["importer", "product_family", "year"], how="left")
    b = b.merge(hp, on=["product_family", "year"], how="left")
    b = b.merge(hc, on=["importer", "year"], how="left")
    b = b.merge(neu, on=["product_family", "year"], how="left")
    del hist, hp, hc, neu, s
    gc.collect()

    # --- panel source columns for the EU27 rows only
    src_cols = sorted({v["source"] for v in feats.values()
                       if v["source"] != "constructed"} |
                      {v["source"] for v in reg["lenient_probe"].values()} |
                      {"ntm6_source_year", "ntm6_all_survey", "pci_source_year",
                       "importer_lpi_source_year"})
    src = read_panel(["spell_id", "year", "gap_filled"] + src_cols,
                     filters=[("importer", "in", members), ("gap_filled", "=", 0)],
                     panel_path=panel_path)
    src["spell_id"] = src["spell_id"].astype(str)
    src = src.drop(columns=["gap_filled"])
    b = b.merge(src, on=["spell_id", "year"], how="left", validate="one_to_one")
    del src
    gc.collect()

    out = pd.DataFrame({
        "spell_id": b["spell_id"], "importer": b["importer"],
        "product_family": b["product_family"], "hs2": b["hs2"],
        "year": b["year"].astype("int16"),
        "relation": b["importer"] + "|" + b["product_family"],
        "spell_start_year": b["spell_start_year"].astype("int16"),
        # outcome facts - prefixed _y_ so no feature list can pick them up
        "_y_E": b["E"].astype("int16"),
        "_y_died": b["died"].astype("int8"),
        "_y_censor_reason": b["censor_reason"].astype(str),
        # stratification metadata (C07), not features
        "meta_known_start": b["start_reason"].isna().astype("int8"),
        "meta_recurrent": (b["n_prior_any"] > 0).astype("int8"),
        "import_value_usd": b["import_value_usd"],
    })

    constructed = {
        "age_obs": (b["year"] - b["spell_start_year"] + 1).astype("float32"),
        "known_start": b["start_reason"].isna().astype("float32"),
        "log_initial_value": np.log1p(b["initial_value"].clip(lower=0)),
        "log_n_markets_eu27_for_p_lag1": np.where(
            b["year"] - 1 >= 2002, np.log1p(b["n_eu"].fillna(0)), np.nan),
        "log_ntm_other_survey": np.log1p(
            (b["ntm6_all_survey"] - b["ntm6_sps_survey"] - b["ntm6_tbt_survey"])
            .clip(lower=0)),
        "ntm_source_age": b["year"] - b["ntm6_source_year"],
        "lpi_age": b["year"] - b["importer_lpi_source_year"],
        "n_prior_spells": b["n_prior_confirmed"],
        "years_since_prior_exit": b["year"] - b["prev_E"],
        "log_active_years_prefix": np.log1p(b["active_years_prefix"]),
        "bilateral_growth_lag1": b["bilateral_growth_lag1"],
        "trend_3y_lag1": b["trend_3y_lag1"],
        "hhi_dest_p_lag1": b["hhi_dest_p_lag1"],
        "hhi_prod_c_lag1": b["hhi_prod_c_lag1"],
    }
    constructed["log_age"] = np.log(constructed["age_obs"])

    def tf(name, x):
        x = pd.to_numeric(pd.Series(x), errors="coerce").astype("float64")
        if name == "identity":
            return x
        if name == "log1p":
            return np.log1p(x.clip(lower=0))
        if name == "log":
            return np.log(x.where(x > 0))
        if name == "clip_pct":
            return x.clip(-500, 500)
        raise ValueError(name)

    for name, spec in feats.items():
        raw = constructed[name] if spec["source"] == "constructed" else b[spec["source"]]
        out[name] = tf(spec["transform"], np.asarray(raw)).astype("float32").to_numpy()
    for name, spec in reg["lenient_probe"].items():
        out["probe_" + name] = tf(spec["transform"], b[spec["source"]].to_numpy()) \
            .astype("float32").to_numpy()

    # --- as-of rules: a source dated after the origin is missing, not zero
    ntm_ok = (b["ntm6_source_year"] <= b["year"]).fillna(False).to_numpy()
    for c in ("log_ntm_sps_survey", "log_ntm_tbt_survey", "log_ntm_other_survey",
              "ntm_source_age"):
        out.loc[~ntm_ok, c] = np.nan
    pci_ok = (b["pci_source_year"] <= b["year"]).fillna(False).to_numpy()
    out.loc[~pci_ok, "pci"] = np.nan
    lpi_ok = (b["importer_lpi_source_year"] <= b["year"]).fillna(False).to_numpy()
    out.loc[~lpi_ok, ["importer_lpi_overall", "lpi_age"]] = np.nan

    out = out.sort_values(["spell_id", "year"]).reset_index(drop=True)
    if out.duplicated(["spell_id", "year"]).any():
        raise AssertionError("duplicate (spell_id, year) in the base table")

    if out_path is not False:
        path = out_path or OUT
        paths.atomic_write_parquet(out, path)
        meta = {"panel_sha256": paths.panel_hash() if panel_path is None else "custom",
                "code_commit": paths.code_commit(),
                "rows": len(out), "max_year": max_year,
                "eu27_members": members, "features": list(feats),
                "build_seconds": round(time.time() - t0, 1),
                "peak_rss_mb": round(paths.peak_rss_mb(), 0)}
        paths.atomic_write_json(META if path == OUT else path + ".meta.json", meta)
    if verbose:
        print(f"base table: {len(out):,} rows x {out.shape[1]} cols in "
              f"{time.time() - t0:.0f}s, peak rss {paths.peak_rss_mb():.0f} MB")
    return out


def load_base(rebuild: bool = False) -> pd.DataFrame:
    if rebuild or not os.path.exists(OUT):
        return build()
    return pd.read_parquet(OUT)


if __name__ == "__main__":
    build()
