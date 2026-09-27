"""C09 - rebuild EU27 spells at other thresholds / gap tolerances (plan §7).

The Stage 1 spell rule lives in scripts/build_spells.py with THRESHOLD_USD and
GAP_TOLERANCE as module constants. This module imports that code unchanged,
sets the two constants, and calls build_spells() on the raw EU27 trade - so
the variant targets use exactly the Stage 1 rule (window ends, unobserved
years, HS revisions). Nothing is written under data/: the helpers that write
interim files (write_revisions, write_family_map) are not called.

Gate: the (10,000, gap 1) rebuild must reproduce the panel's EU27 spells
exactly (spell ids, active rows, events) before any variant is used.

Covariates of a variant row:
  * spell structure (age, known start, initial value, E, died) and the
    relation's own trade (log value, lag, 3y volatility) come from the rebuild;
  * importer-year, family-year and (importer, HS2)-year covariates are looked
    up from the Stage 1 panel at their own grain (they do not depend on the
    target), as are relation-year world-market columns where that relation-year
    is in the panel (at 5k, rows between 5k and 10k are not: those columns are
    then missing and flagged - recorded in the report);
  * counts that depend on the threshold (products per importer, EU27 markets
    per family) are recounted on the variant's active rows.
Only the S1 and S4 packages are needed (plan §7 C09).

    python -m stage2_benchmark.data.target_variants
"""

from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from stage2_benchmark import paths  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from stage2_benchmark.data import base_table  # noqa: E402

sys.path.insert(0, os.path.join(paths.NOTEBOOK, "scripts"))

VARIANTS = {            # name: (threshold_usd, gap)
    "t10k_g1": (10_000, 1),     # reproduction gate only
    "t5k_g1": (5_000, 1),
    "t50k_g1": (50_000, 1),
    "t10k_g0": (10_000, 0),
    "t10k_g2": (10_000, 2),
}

IMPORTER_YEAR = ["log_gdp_d_lag1", "log_gdpcap_d_lag1", "importer_gdp_growth_pct_lag1",
                 "importer_inflation_pct_lag1", "dist"]
FAMILY_YEAR = ["rca_lag", "growth_lag_pct", "world_growth_pct_lag1", "n_markets_for_p_lag1",
               "tariff_applied_lag", "pref_margin_lag", "evfta_cut_cum_pp_lag"]
REL_YEAR = ["vn_market_share_pct_lag1", "log_total_import_cp_lag1"]
IMP_HS2_YEAR = ["hs2_share_lag1"]


def load_raw_eu27():
    import build_spells as bs
    members = set(base_table.eu27_members())
    t0 = time.time()
    u = bs.build_families()
    fam_in_rev = bs.families_in_revision(u)
    importers, holes = bs.complete_importers(bs.RAW_TRADE)
    eu = sorted(i for i in importers if i in members)
    revisions = {}
    panel, weights, _, _ = bs.read_folder(u, bs.RAW_TRADE, bs.EXPORTER, set(eu),
                                          "VNM->EU27", revisions)
    revision_of = {k: max(c, key=c.get) for k, c in revisions.items()}
    observed = bs.observed_years(bs.RAW_TRADE)
    last_year, _ = bs.observation_windows(set(eu))
    print(f"raw EU27: {len(panel):,} cells from {len(eu)} importers in "
          f"{time.time() - t0:.0f}s, rss {paths.rss_mb():.0f} MB", flush=True)
    return dict(bs=bs, u=u, fam_in_rev=fam_in_rev, panel=dict(panel), weights=dict(weights),
                revision_of=revision_of, observed=observed, last_year=last_year, eu=eu)


def spells_at(raw, threshold, gap) -> pd.DataFrame:
    bs = raw["bs"]
    bs.THRESHOLD_USD, bs.GAP_TOLERANCE = threshold, gap
    try:
        _, episodes = bs.build_spells(raw["panel"], raw["last_year"], raw["weights"],
                                      raw["observed"], raw["revision_of"],
                                      raw["fam_in_rev"], raw["u"].receivers)
    finally:
        bs.THRESHOLD_USD, bs.GAP_TOLERANCE = 10_000, 1
    cols = ["spell_id", "importer", "product_family", "year", "spell_start_year",
            "gap_filled", "event", "start_reason", "import_value_usd"]
    ep = pd.DataFrame(episodes)[cols]
    ep["start_reason"] = ep["start_reason"].replace("", np.nan)
    return ep


def check_reproduction(ep: pd.DataFrame) -> dict:
    members = base_table.eu27_members()
    p = base_table.read_panel(["spell_id", "importer", "year", "gap_filled", "event"],
                              filters=[("importer", "in", members)])
    p["spell_id"] = p["spell_id"].astype(str)
    a = p.sort_values(["spell_id", "year"]).reset_index(drop=True)
    b = ep[["spell_id", "year", "gap_filled", "event"]].sort_values(["spell_id", "year"]) \
        .reset_index(drop=True)
    same_rows = len(a) == len(b) and (a["spell_id"].values == b["spell_id"].values).all() \
        and (a["year"].values == b["year"].values).all()
    out = {"panel_rows": len(a), "rebuild_rows": len(b), "same_keys": bool(same_rows)}
    if same_rows:
        out["same_gap_filled"] = bool((a["gap_filled"].values == b["gap_filled"].values).all())
        out["same_event"] = bool((a["event"].values == b["event"].values).all())
    out["pass"] = bool(same_rows and out.get("same_gap_filled") and out.get("same_event"))
    return out


def variant_base(ep: pd.DataFrame, name: str) -> pd.DataFrame:
    """A base table (same columns as base_eu27 for D/R/M/E/P) for one variant."""
    feats = paths.load_yaml("feature_registry.yaml")["features"]
    s = base_table.prior_spell_features(base_table.spell_facts(ep.assign(hs2="")))
    hist = base_table.relation_history(ep)
    act = ep[ep["gap_filled"] == 0].copy()
    act = act.merge(s[["E", "died", "initial_value", "n_prior_any"]], left_on="spell_id",
                    right_index=True, how="left")
    hist["importer"] = hist["importer"].astype(str)
    hist["product_family"] = hist["product_family"].astype(str)
    act = act.merge(hist, on=["importer", "product_family", "year"], how="left")
    # threshold-dependent counts, recounted on the variant's active rows
    npc = act.groupby(["importer", "year"])["product_family"].nunique().rename("npc").reset_index()
    npc["year"] += 1
    act = act.merge(npc, on=["importer", "year"], how="left")
    neu = base_table.eu27_market_counts(ep, base_table.eu27_members())
    act = act.merge(neu, on=["product_family", "year"], how="left")
    # target-independent covariates from the panel at their own grain
    members = base_table.eu27_members()
    src = base_table.read_panel(["importer", "product_family", "hs2", "year", "log_value_lag"]
                                + IMPORTER_YEAR + FAMILY_YEAR + REL_YEAR + IMP_HS2_YEAR,
                                filters=[("importer", "in", members)])
    for c in ("importer", "product_family", "hs2"):
        src[c] = src[c].astype(str)
    fam_hs2 = src.drop_duplicates("product_family").set_index("product_family")["hs2"]
    act["hs2"] = act["product_family"].map(fam_hs2).fillna(act["product_family"].str[3:5])
    iy = src.groupby(["importer", "year"])[IMPORTER_YEAR].first().reset_index()
    fy = src.groupby(["product_family", "year"])[FAMILY_YEAR].first().reset_index()
    ry = src.groupby(["importer", "product_family", "year"])[REL_YEAR].first().reset_index()
    hy = src.groupby(["importer", "hs2", "year"])[IMP_HS2_YEAR].first().reset_index()
    act = act.merge(iy, on=["importer", "year"], how="left") \
             .merge(fy, on=["product_family", "year"], how="left") \
             .merge(ry, on=["importer", "product_family", "year"], how="left") \
             .merge(hy, on=["importer", "hs2", "year"], how="left")
    # the relation's own trade, from the rebuild (ln, as the panel's log_value)
    v = act["import_value_usd"].astype("float64")
    lv = np.log1p(v.clip(lower=0))
    key = ep.assign(lv=np.log(ep["import_value_usd"].where(ep["import_value_usd"] > 0)))
    lagv = key.set_index(["importer", "product_family", "year"])["lv"]
    idx = pd.MultiIndex.from_arrays([act["importer"], act["product_family"], act["year"] - 1])
    log_value_lag = lagv.reindex(idx).to_numpy()
    # 3y volatility of ln value over t-3..t-1 (>= 2 of 3), the Stage 1 definition
    lags = np.column_stack([lagv.reindex(pd.MultiIndex.from_arrays(
        [act["importer"], act["product_family"], act["year"] - k])).to_numpy() for k in (1, 2, 3)])
    n = np.isfinite(lags).sum(1)
    with np.errstate(invalid="ignore"):
        vol = np.where(n >= 2, np.nanstd(lags, axis=1, ddof=1), np.nan)

    out = pd.DataFrame({
        "spell_id": act["spell_id"].astype(str), "importer": act["importer"].astype(str),
        "product_family": act["product_family"].astype(str), "hs2": act["hs2"],
        "year": act["year"].astype("int16"),
        "relation": act["importer"].astype(str) + "|" + act["product_family"].astype(str),
        "spell_start_year": act["spell_start_year"].astype("int16"),
        "_y_E": act["E"].astype("int16"), "_y_died": act["died"].astype("int8"),
        "meta_known_start": act["start_reason"].isna().astype("int8"),
        "meta_recurrent": (act["n_prior_any"] > 0).astype("int8"),
        "import_value_usd": v.astype("float32"),
    })
    age = (act["year"] - act["spell_start_year"] + 1).astype("float64")
    raw = {
        "age_obs": age, "log_age": np.log(age), "known_start": act["start_reason"].isna().astype(float),
        "log_value": lv, "log_value_lag": log_value_lag,
        "log_initial_value": np.log1p(act["initial_value"].clip(lower=0)),
        "vn_market_share_lag1": np.log1p(act["vn_market_share_pct_lag1"].clip(lower=0)),
        "volatility_3y_lag1": vol,
        "log_gdp_d_lag1": act["log_gdp_d_lag1"], "log_gdpcap_d_lag1": act["log_gdpcap_d_lag1"],
        "importer_gdp_growth_lag1": act["importer_gdp_growth_pct_lag1"].clip(-500, 500),
        "importer_inflation_lag1": act["importer_inflation_pct_lag1"].clip(-500, 500),
        "log_total_import_cp_lag1": act["log_total_import_cp_lag1"],
        "log_dist": np.log(act["dist"].where(act["dist"] > 0)),
        "log_n_products_to_c_lag1": np.log1p(act["npc"]),
        "log_n_markets_for_p_lag1": np.log1p(act["n_markets_for_p_lag1"].clip(lower=0)),
        "log_n_markets_eu27_for_p_lag1": np.where(act["year"] - 1 >= 2002,
                                                  np.log1p(act["n_eu"].fillna(0)), np.nan),
        "hs2_share_lag1": act["hs2_share_lag1"],
        "log_rca_lag": np.log1p(act["rca_lag"].clip(lower=0)),
        "vn_product_growth_lag": act["growth_lag_pct"].clip(-500, 500),
        "world_growth_lag1": act["world_growth_pct_lag1"].clip(-500, 500),
        "tariff_applied_lag": act["tariff_applied_lag"], "pref_margin_lag": act["pref_margin_lag"],
        "evfta_cut_cum_pp_lag": act["evfta_cut_cum_pp_lag"],
    }
    s14 = [c for c, sp in feats.items() if sp["block"] in "DRMEP" and not sp.get("optional")]
    missing = set(s14) - set(raw)
    if missing:
        raise AssertionError(f"variant base lacks {missing}")
    for c in s14:
        out[c] = pd.to_numeric(pd.Series(np.asarray(raw[c])), errors="coerce").astype("float32").to_numpy()
    out = out[out["year"] >= 2002].sort_values(["spell_id", "year"]).reset_index(drop=True)
    assert not out.duplicated(["spell_id", "year"]).any()
    return out


def main():
    raw = load_raw_eu27()
    report = {}
    for name, (thr, gap) in VARIANTS.items():
        ep = spells_at(raw, thr, gap)
        if name == "t10k_g1":
            rep = check_reproduction(ep)
            report[name] = rep
            print("reproduction gate:", rep, flush=True)
            if not rep["pass"]:
                sys.exit("the rebuild does not reproduce the panel - variants not written")
        vb = variant_base(ep, name)
        if name == "t10k_g1":
            ref = base_table.load_base()
            m = ref.merge(vb, on=["spell_id", "year"], suffixes=("", "_v"))
            diffs = {}
            for c in [c for c in vb.columns if c + "_v" in m.columns and m[c].dtype.kind == "f"]:
                x, y = m[c].to_numpy("float64"), m[c + "_v"].to_numpy("float64")
                same = np.isclose(x, y, atol=1e-4) | (np.isnan(x) & np.isnan(y))
                diffs[c] = float(1 - same.mean())
            report[name]["feature_mismatch_share_vs_base"] = diffs
            report[name]["rows_matched"] = int(len(m))
            print("feature mismatch vs base_eu27:", {k: round(v, 4) for k, v in diffs.items() if v > 0})
        paths.atomic_write_parquet(vb, os.path.join(paths.VIEWS, f"base_{name}.parquet"))
        act = vb[vb["year"].between(2012, 2024)]
        ev1 = ((act["_y_E"] == act["year"]) & (act["_y_died"] == 1))
        report.setdefault(name, {}).update(
            threshold=thr, gap=gap, rows_b0=int(len(act)), events_b0=int(ev1.sum()),
            spells=int(vb["spell_id"].nunique()),
            one_year_spell_share=float((vb.groupby("spell_id")["year"].count() == 1).mean()),
            exit_rate_b0=float(ev1.mean()),
            null_share={c: float(vb[c].isna().mean()) for c in ("vn_market_share_lag1",
                                                               "log_total_import_cp_lag1",
                                                               "log_value_lag")})
        print(name, {k: v for k, v in report[name].items() if k != "null_share"}, flush=True)
        del ep, vb
    paths.atomic_write_json(os.path.join(paths.VIEWS, "target_variants.json"), report)


if __name__ == "__main__":
    main()
