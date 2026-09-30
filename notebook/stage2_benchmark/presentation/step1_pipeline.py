"""Step 1 — how raw Comtrade rows become model inputs, captured at every stage.

Two views of the same pipeline:
  * one worked relation (AUT x H0_080110) followed from the raw customs rows to
    the standardised feature matrix, one CSV per stage (out/captures/);
  * the whole EU27 sample as a funnel, the fold timeline, the effect of the
    information cutoff on labels, and what the fold-fitted preprocessor does to
    missing values and skewed features (out/figures/, out/tables/).

Run from notebook/:
    $PY -m stage2_benchmark.presentation.step1_pipeline
"""

from __future__ import annotations

import os

from stage2_benchmark.presentation.common import (
    AXIS, CAP, CENSOR, EU27, EVENT, EXAMPLE_FAMILY, EXAMPLE_IMPORTER,
    EXAMPLE_RELATION, INK, INK2, MUTED, SEQ, SLOT, TAB, fmt_int, plt, save,
    write_csv)
from stage2_benchmark import paths
from stage2_benchmark.data import views as V
from stage2_benchmark.features.preprocess import Preprocessor, registry, resolve_set

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

RAW_TRADE = os.path.join(paths.NOTEBOOK, "data", "raw", "trade")
THRESHOLD = 10_000
SPLITS = paths.load_yaml("splits.yaml")
BLOCK_NAME = {"D": "Duration", "R": "Relationship", "M": "Market/gravity",
              "E": "Experience", "P": "Policy/tariff", "N": "NTM",
              "C": "Complexity", "L": "Logistics", "H": "Deep history"}


# ------------------------------------------------------------------ inputs
def family_map() -> pd.DataFrame:
    return pd.read_csv(os.path.join(paths.INTERIM, "family_map.csv"), dtype=str)


def read_raw(importer: str, year: int) -> pd.DataFrame | None:
    f = os.path.join(RAW_TRADE, f"{importer}_{year}.csv.gz")
    if not os.path.exists(f):
        return None
    d = pd.read_csv(f, dtype={"hs6": str}, usecols=[
        "year", "importer", "exporter", "hs6", "import_value_usd",
        "net_weight_kg", "hs_revision"])
    return d[d["exporter"] == "VNM"]


def unobserved_years() -> set[tuple[str, int]]:
    p = pd.read_csv(os.path.join(paths.NOTEBOOK, "selection", "hs6_unobserved_years.csv"))
    return set(zip(p["importer"], p["year"]))


def spells() -> pd.DataFrame:
    return pd.read_csv(os.path.join(paths.INTERIM, "spells.csv"))


def base() -> pd.DataFrame:
    return pd.read_parquet(os.path.join(paths.VIEWS, "base_eu27.parquet"))


# ------------------------------------------------- worked example: captures
def example_captures(fm, sp, b):
    imp, fam = EXAMPLE_IMPORTER, EXAMPLE_FAMILY
    members = fm[fm["family"] == fam]
    unobs = unobserved_years()

    # stage 1: the customs rows exactly as downloaded
    raw, years = [], []
    for y in range(2002, 2026):
        d = read_raw(imp, y)
        observed = d is not None and (imp, y) not in unobs
        if d is None:
            years.append({"year": y, "importer_filed_hs6": False})
            continue
        m = d.merge(members, left_on=["hs_revision", "hs6"],
                    right_on=["revision", "hs6"])
        raw.append(m[["year", "importer", "exporter", "hs_revision", "hs6",
                      "import_value_usd", "net_weight_kg"]])
        years.append({"year": y, "importer_filed_hs6": observed,
                      "hs_revision": d["hs_revision"].iloc[0],
                      "codes_reported": " + ".join(sorted(m["hs6"])),
                      "n_vnm_lines_in_file": len(d)})
    raw = pd.concat(raw, ignore_index=True)
    write_csv(raw, CAP, "01_raw_comtrade_rows.csv")

    # stage 2: codes of every HS revision summed into one product family
    fy = pd.DataFrame(years)
    val = raw.groupby("year")["import_value_usd"].sum().rename("family_value_usd")
    fy = fy.merge(val, on="year", how="left")
    fy["active_ge_10k"] = fy["family_value_usd"] >= THRESHOLD

    # stage 3: spells, from the Stage 1 panel (gap rule + confirmation)
    p = pq.read_table(paths.PANEL, columns=[
        "spell_id", "importer", "product_family", "year", "import_value_usd",
        "gap_filled", "event", "t_start", "t_stop", "left_trunc",
        "right_censored", "censor_reason", "start_reason"],
        filters=[("importer", "==", imp), ("product_family", "==", fam)]).to_pandas()
    p = p.sort_values("year")
    fy = fy.merge(p[["year", "spell_id", "gap_filled", "t_start", "event"]],
                  on="year", how="left")
    fy["panel_row"] = fy["spell_id"].notna()
    fy["status"] = np.select(
        [fy["gap_filled"] == 1, fy["event"] == 1, fy["panel_row"],
         ~fy["importer_filed_hs6"]],
        ["gap year bridged (below threshold, spell continues)",
         "last active year (exit confirmed by 2 empty observed years)",
         "active", "importer did not file HS6"],
        "inactive")
    write_csv(fy, CAP, "02_family_year_series.csv")
    write_csv(p, CAP, "03_panel_spell_years.csv")
    s = sp[(sp["importer"] == imp) & (sp["product_family"] == fam)]
    write_csv(s, CAP, "04_spells.csv")

    # stage 4: base-table rows (active origins), outcome kept apart as _y_*
    br = b[b["relation"] == EXAMPLE_RELATION].sort_values("year")
    keep = ["spell_id", "year", "age_obs", "known_start", "meta_recurrent",
            "_y_E", "_y_died", "import_value_usd", "log_value", "log_value_lag",
            "log_initial_value", "vn_market_share_lag1", "volatility_3y_lag1",
            "log_gdp_d_lag1", "log_n_products_to_c_lag1", "hs2_share_lag1",
            "log_rca_lag", "tariff_applied_lag", "pref_margin_lag",
            "evfta_cut_cum_pp_lag", "pci", "importer_eci"]
    write_csv(br[keep], CAP, "05_base_table_rows.csv")

    # stage 5: the same rows read at different information cutoffs
    recs = []
    for C in (2015, 2018, 2020, 2025):
        v = V.recensor(br, C)
        for _, r in br.iterrows():
            hit = v[(v["year"] == r["year"]) & (v["spell_id"] == r["spell_id"])]
            if hit.empty:
                recs.append({"cutoff": C, "spell_id": r["spell_id"], "origin": r["year"],
                             "in_view": False, "duration": None, "event": None, "y_D": None})
            else:
                h = hit.iloc[0]
                recs.append({"cutoff": C, "spell_id": r["spell_id"], "origin": r["year"],
                             "in_view": True, "duration": int(h["duration"]),
                             "event": int(h["event"]),
                             "y_D": int(h["event"] == 1 and h["duration"] == 1)})
    lab = pd.DataFrame(recs)
    write_csv(lab, CAP, "06_labels_by_cutoff.csv")

    # stage 6: fold F1 Task L, feature set S6: raw -> imputed -> standardised
    train, ev = V.fold_views(b, SPLITS, "F1", "L", "test")
    cols = resolve_set("S6")
    pre = Preprocessor(cols).fit(train)
    ex = pd.concat([train[train["relation"] == EXAMPLE_RELATION],
                    ev[ev["relation"] == EXAMPLE_RELATION]]).sort_values("year")
    Z = pre.transform(ex)
    names = pre.names
    long = []
    for i, (_, r) in enumerate(ex.iterrows()):
        role = "test (origin 2019)" if r["year"] == 2019 else "train"
        flags = [f"{c}_isna" for c in pre.flag_cols_]
        for c in cols + flags:
            is_flag = c.endswith("_isna")
            src = c[:-5] if is_flag else c
            rawv = float(pd.isna(r[src])) if is_flag else r[c]
            imputed = pre.median_[c] if not is_flag and pd.isna(rawv) else rawv
            long.append({"origin": int(r["year"]), "role": role, "column": c,
                         "block": registry()["features"][src]["block"],
                         "raw": rawv, "after_impute": imputed,
                         "model_input": float(Z[i, names.index(c)]) if c in names else None,
                         "note": ("dropped: constant in train" if c not in names else
                                  "missing indicator" if c.endswith("_isna") else
                                  "imputed with train median" if pd.isna(rawv) else "")})
    write_csv(pd.DataFrame(long), CAP, "07_features_raw_to_model_input.csv")
    wide = pd.DataFrame(Z, columns=names)
    wide.insert(0, "origin", ex["year"].to_numpy())
    write_csv(wide, CAP, "08_model_matrix_rows.csv")
    return fy, s, br, lab, pre


def fig_example(fy, s, lab):
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(11, 8.6), sharex=True,
                                     gridspec_kw={"height_ratios": [2.3, 1.1, 2.2],
                                                  "hspace": 0.28})
    y = fy["year"].to_numpy()
    v = fy["family_value_usd"].fillna(0).to_numpy()
    col = np.where(fy["gap_filled"] == 1, SLOT[3],
                   np.where(fy["active_ge_10k"], SLOT[0], AXIS))
    a1.bar(y, np.maximum(v, 1), width=0.72, color=col, zorder=3)
    a1.set_yscale("log")
    a1.axhline(THRESHOLD, color=INK, lw=1)
    a1.text(2007.6, THRESHOLD * 1.2, "threshold\nUSD 10,000", color=INK,
            fontsize=8.5, va="bottom")
    a1.set_ylabel("family import value, USD (log)")
    a1.set_title("① Raw Comtrade value of AUT ← VNM, product family H0_080110 "
                 "(codes of every HS revision summed)")
    prev = None
    for _, r in fy.iterrows():
        rev = r.get("hs_revision")
        if isinstance(rev, str) and rev != prev:
            if prev is not None:
                a1.axvline(r["year"] - 0.5, color=AXIS, lw=0.8, zorder=1)
            a1.text(r["year"] - 0.4, 1.3e6, f"reported in {rev}", fontsize=8,
                    color=INK2)
            prev = rev
    a1.set_ylim(80, 3e7)
    from matplotlib.patches import Patch
    a1.legend(handles=[Patch(color=SLOT[0], label="active (≥ 10k)"),
                       Patch(color=SLOT[3], label="below 10k, bridged by 1-year gap rule"),
                       Patch(color=AXIS, label="below 10k, inactive")],
              loc="upper left", ncol=3, fontsize=8.5)

    a2.set_title("② Spells (importer × family relationship lives)")
    for i, (_, r) in enumerate(s.sort_values("start_year").iterrows()):
        yy = 0
        a2.plot([r["start_year"] - 0.4, r["end_year"] + 0.4], [yy, yy],
                color=SLOT[0], lw=9, solid_capstyle="butt", zorder=2)
        a2.text((r["start_year"] + r["end_year"]) / 2, 0.42,
                f"spell {r['start_year']}–{r['end_year']}", ha="center",
                fontsize=8.5, color=INK2)
        if r["left_trunc"] == 1:
            a2.annotate("left-truncated\n(start before window)",
                        (r["start_year"] - 0.4, -0.05), (r["start_year"] - 0.4, -0.95),
                        fontsize=8, color=INK2, ha="left")
        if r["event"] == 1:
            a2.plot(r["end_year"] + 0.4, 0, marker="X", ms=11, color=EVENT, zorder=4)
            a2.text(r["end_year"] + 0.4, -0.75, "exit confirmed", fontsize=8,
                    color=EVENT, ha="center")
        else:
            a2.annotate("", (r["end_year"] + 0.9, 0), (r["end_year"] + 0.4, 0),
                        arrowprops=dict(arrowstyle="->", color=CENSOR, lw=1.5))
            a2.text(r["start_year"] - 0.4, -0.95, "right-censored\n(window end)",
                    fontsize=8, color=INK2)
    gap = fy[fy["gap_filled"] == 1]["year"]
    for g in gap:
        a2.plot([g - 0.4, g + 0.4], [0, 0], color=SLOT[3], lw=9,
                solid_capstyle="butt", zorder=3)
    a2.set_ylim(-1.1, 0.9)
    a2.set_yticks([])
    a2.grid(False)

    a3.set_title("③ The same origins as labelled rows, read at two information cutoffs")
    for k, (C, off, c) in enumerate(((2018, 0.18, SEQ[2]), (2025, -0.18, INK))):
        d = lab[(lab["cutoff"] == C) & lab["in_view"]]
        for _, r in d.iterrows():
            t = r["origin"]
            a3.plot([t, t + r["duration"]], [t + off, t + off], color=c, lw=1.8)
            if r["event"] == 1:
                a3.plot(t + r["duration"], t + off, "X", color=EVENT, ms=7)
            else:
                a3.plot(t + r["duration"], t + off, "o", mfc="white", mec=c, ms=5)
        a3.axvline(C - 1, color=c, lw=1)
        a3.text(C - 1 + 0.15, 2023.2, f"cutoff C = {C}\ncensor at H = C − 1 = {C - 1}",
                color=c, fontsize=8.5)
    a3.set_ylabel("origin year t")
    a3.set_ylim(2001.5, 2026)
    a3.set_xlim(2001.3, 2026.7)
    a3.set_xticks(range(2002, 2026, 2))
    a3.plot([], [], color=SEQ[2], label="as seen by the F1 refit (C = 2018)")
    a3.plot([], [], color=INK, label="as seen at the end of the data (C = 2025)")
    a3.plot([], [], "X", color=EVENT, ls="none", label="event")
    a3.plot([], [], "o", mfc="white", mec=INK2, ls="none", label="censored")
    a3.legend(loc="center left", bbox_to_anchor=(0, 0.52), fontsize=8.5)
    a3.text(2002.1, 2022.3, "2016 (bridged gap year) is not an origin.\n"
            "Origins 2024–25 have no follow-up at C = 2025 → dropped.",
            fontsize=8.5, color=INK2)
    a3.set_xlabel("calendar year")
    save(fig, "01_example_raw_to_labels.png")


# --------------------------------------------------------- whole-sample funnel
def funnel(fm, sp, b):
    unobs = unobserved_years()
    n_raw = n_raw_all = 0
    agg = []
    for imp in EU27:
        for y in range(2002, 2026):
            d = read_raw(imp, y)
            if d is None:
                continue
            n_raw_all += len(d)
            if (imp, y) in unobs:
                continue
            n_raw += len(d)
            m = d.merge(fm, left_on=["hs_revision", "hs6"], right_on=["revision", "hs6"],
                        how="left")
            m["family"] = m["family"].fillna(m["hs_revision"] + "_" + m["hs6"])
            g = m.groupby("family")["import_value_usd"].sum()
            agg.append(pd.DataFrame({"importer": imp, "year": y, "value": g.values}))
    agg = pd.concat(agg, ignore_index=True)
    p = pq.read_table(paths.PANEL, columns=["importer", "gap_filled", "spell_id"],
                      filters=[("importer", "in", EU27)]).to_pandas()
    s = sp[sp["importer"].isin(EU27)]
    b05 = b[b["year"] >= 2005]
    Dall = V.view(b, (2005, 2024), 2025, task="D")
    rows = [
        ("Raw Comtrade lines, VNM → EU27, 2002–2025", "HS6 line × year", n_raw_all),
        ("… in importer-years observed at HS6", "HS6 line × year", n_raw),
        ("Summed into product families", "importer × family × year", len(agg)),
        ("Active: value ≥ USD 10,000", "importer × family × year",
         int((agg["value"] >= THRESHOLD).sum())),
        ("Spell-years incl. bridged gap years (panel)", "spell × year", len(p)),
        ("Spells (relationship lives)", "spell", len(s)),
        ("  of which exit confirmed", "spell", int(s["event"].sum())),
        ("Base table: active origins", "spell × origin year", len(b)),
        ("Origins 2005–2025 (training-eligible)", "spell × origin year", len(b05)),
        ("Origins with a confirmed 1-year outcome (read at 2025)", "spell × origin year", len(Dall)),
        ("  of which exit in next year (y = 1)", "spell × origin year", int(Dall["y"].sum())),
    ]
    if n_raw == n_raw_all:     # no EU27 importer-year is HS6-unobserved
        rows.pop(1)
    f = pd.DataFrame(rows, columns=["stage", "unit", "count"])
    write_csv(f, TAB, "funnel.csv")

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    yy = np.arange(len(f))[::-1]
    cols = [SLOT[0] if not st.startswith("  ") else SEQ[1] for st in f["stage"]]
    ax.barh(yy, f["count"], color=cols, height=0.62, zorder=3)
    for y_, c, u in zip(yy, f["count"], f["unit"]):
        ax.text(c * 1.02, y_, f"{fmt_int(c)}  ({u})", va="center", fontsize=8.8, color=INK2)
    ax.set_yticks(yy, f["stage"], fontsize=9.3)
    ax.set_xscale("log")
    ax.set_xlim(1e4, 3e6)
    ax.set_xlabel("count (log scale)")
    ax.set_title("From raw customs lines to labelled origins — EU27 sample")
    ax.grid(axis="y", visible=False)
    save(fig, "02_funnel.png")
    return f


# ------------------------------------------------------------- fold design
def fold_tables(b):
    rec = []
    for task in ("D", "L"):
        for fold in ("F1", "F2", "F3"):
            for stage in ("valid", "test"):
                tr, ev = V.fold_views(b, SPLITS, fold, task, stage)
                evk = "y" if task == "D" else "event"
                rec.append({"task": task, "fold": fold, "stage": stage,
                            "train_origins": f"{tr['year'].min()}–{tr['year'].max()}",
                            "train_rows": len(tr), "train_events": int(tr[evk].sum()),
                            "eval_origin": int(ev["year"].iloc[0]),
                            "eval_rows": len(ev), "eval_events": int(ev[evk].sum()),
                            "eval_event_rate": round(float(ev[evk].mean()), 4),
                            "eval_max_duration": int(ev["duration"].max())})
    t = pd.DataFrame(rec)
    write_csv(t, TAB, "fold_sizes.csv")
    return t


def fig_folds():
    fig, axes = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True,
                             gridspec_kw={"hspace": 0.35})
    for ax, task in zip(axes, ("D", "L")):
        h = 1 if task == "D" else 3
        for i, fold in enumerate(("F1", "F2", "F3")):
            f = SPLITS["folds"][fold]
            sp_ = f[task]
            y0 = 2 - i
            # tuning stage (upper sub-row)
            ic, vo, rc, to = sp_["inner_cutoff"], sp_["valid_origin"], sp_["refit_cutoff"], f["test_origin"]
            ax.barh(y0 + 0.18, ic - 2 - 2005 + 1, left=2005 - 0.5, height=0.28,
                    color=SEQ[1], zorder=3)
            ax.barh(y0 + 0.18, 1, left=vo - 0.5, height=0.28, color=SLOT[1], zorder=3)
            ax.plot([vo + 0.5, vo + h + 0.5], [y0 + 0.18] * 2, color=SLOT[1], lw=1,
                    ls=(0, (1, 1.5)))
            ax.plot(ic + 0.5, y0 + 0.18, "|", color=INK, ms=16, mew=2.2, zorder=5)
            # refit + test stage (lower sub-row)
            ax.barh(y0 - 0.18, rc - 2 - 2005 + 1, left=2005 - 0.5, height=0.28,
                    color=SLOT[0], zorder=3)
            ax.barh(y0 - 0.18, 1, left=to - 0.5, height=0.28, color=EVENT, zorder=3)
            ax.plot([to + 0.5, 2025.5], [y0 - 0.18] * 2, color=EVENT, lw=1, ls=(0, (1, 1.5)))
            ax.plot(rc + 0.5, y0 - 0.18, "|", color=INK, ms=16, mew=2.2, zorder=5)
            ax.text(2026.2, y0, f"{fold}: tune ≤{ic} → valid {vo}; refit ≤{rc} → test {to}",
                    va="center", fontsize=8.5, color=INK2)
        ax.set_yticks([2, 1, 0], ["F1", "F2", "F3"])
        ax.set_ylim(-0.6, 2.6)
        ax.grid(axis="y", visible=False)
        ax.set_title(f"Task {task}: temporal folds (horizon {h} year{'s' if h > 1 else ''} "
                     f"must be confirmable for the validation origin)")
    axes[1].set_xlim(2004, 2036)
    axes[1].set_xticks(range(2005, 2026, 2))
    axes[1].set_xlabel("origin year / calendar year")
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    fig.legend(handles=[
        Patch(color=SEQ[1], label="tuning train origins"),
        Patch(color=SLOT[1], label="validation origin"),
        Patch(color=SLOT[0], label="refit train origins"),
        Patch(color=EVENT, label="test origin"),
        Line2D([], [], color=INK, marker="|", ls="none", ms=12, mew=2.2, label="information cutoff C"),
        Line2D([], [], color=MUTED, ls=(0, (1, 1.5)), label="outcome follow-up")],
        loc="lower left", ncol=6, fontsize=8.3, bbox_to_anchor=(0.06, -0.04))
    save(fig, "03_fold_timeline.png")


# ------------------------------------------------------- preprocessing effect
def feature_dictionary(b):
    reg = registry()["features"]
    b05 = b[b["year"] >= 2005]
    rec = []
    for c, spec in reg.items():
        if c not in b.columns:
            continue
        s = b05[c]
        rec.append({"feature": c, "block": spec["block"],
                     "block_name": BLOCK_NAME.get(spec["block"]),
                     "grain": " × ".join(spec.get("grain", [])),
                     "transform": spec.get("transform"),
                     "source": spec.get("source"),
                     "missing_semantics": spec.get("missing_semantics", "unknown_is_not_zero"),
                     "dtype": ("binary" if set(s.dropna().unique()) <= {0, 1} else
                               "integer" if np.allclose(s.dropna() % 1, 0) else "continuous"),
                     "missing_share_origins_2005plus": round(float(s.isna().mean()), 4),
                     "median": s.median(), "p01": s.quantile(0.01), "p99": s.quantile(0.99),
                     "optional": bool(spec.get("optional", False))})
    d = pd.DataFrame(rec)
    order = list(BLOCK_NAME)
    d["_o"] = d["block"].map(order.index)
    d = d.sort_values(["_o", "feature"]).drop(columns="_o")
    write_csv(d, TAB, "feature_dictionary.csv")
    return d


def fig_missing(b):
    train, _ = V.fold_views(b, SPLITS, "F1", "L", "test")
    cols = resolve_set("S8")
    reg = registry()["features"]
    miss = train[cols].isna().mean()
    d = pd.DataFrame({"feature": cols, "block": [reg[c]["block"] for c in cols],
                      "missing": miss.values})
    order = list(BLOCK_NAME)
    d["_o"] = d["block"].map(order.index)
    d = d.sort_values(["_o", "feature"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10.5, 10))
    yy = np.arange(len(d))[::-1]
    ax.barh(yy, d["missing"] * 100, color=SLOT[0], height=0.66, zorder=3)
    for y_, m in zip(yy, d["missing"]):
        if m > 0:
            ax.text(m * 100 + 0.8, y_, f"{m:.0%}", va="center", fontsize=7.8, color=INK2)
    ax.set_yticks(yy, [f"{r.block} · {r.feature}" for r in d.itertuples()], fontsize=8)
    ax.set_xlim(0, 105)
    ax.set_xlabel("share of training rows with no as-of value (%)")
    ax.set_title("Missing (no as-of value) before preprocessing\n"
                 f"F1 refit training rows, origins 2005–2016, n = {fmt_int(len(train))}")
    ax.grid(axis="y", visible=False)
    save(fig, "04_missingness_before_preprocessing.png")
    write_csv(d.drop(columns="_o"), TAB, "missingness_F1_train.csv")


def fig_eligibility():
    e = pd.read_csv(os.path.join(paths.REPORTS, "stage0", "0.3_eligibility.csv"))
    e = e[e["set"] == "S8"].copy()
    e["row"] = "Task " + e["task"] + " · " + e["fold"] + " · " + e["stage"].map(
        {"valid": "tuning train", "test": "refit train"})
    write_csv(e[["task", "fold", "stage", "train_rows", "asof_N", "asof_C", "asof_L",
                 "asof_H", "eligible", "reason"]], TAB, "block_eligibility.csv")
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    yy = np.arange(len(e))[::-1]
    for k, (blk, mk) in enumerate((("N", "o"), ("C", "s"), ("L", "^"), ("H", "D"))):
        ax.scatter(e[f"asof_{blk}"] * 100, yy + 0.24 - 0.16 * k, marker=mk, s=46, color=SLOT[k],
                   edgecolor="white", linewidth=1, zorder=3, label=f"{blk} · {BLOCK_NAME[blk]}")
    ax.axvline(50, color=INK, lw=1)
    ax.text(49, -0.9, "rule: ≥ 50% as-of", ha="right", fontsize=8.5, color=INK)
    ax.set_ylim(-1.2, len(e) - 0.4)
    ax.set_yticks(yy, e["row"], fontsize=9)
    ax.set_xlim(0, 104)
    ax.set_xlabel("share of training rows with ≥ 1 as-of value in the block (%)")
    ax.set_title("Secondary-block eligibility per fold: only NTM (N) falls below the rule")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8.5)
    ax.grid(axis="y", visible=False)
    save(fig, "06_block_eligibility.png")


def fig_transform(b):
    train, ev = V.fold_views(b, SPLITS, "F1", "L", "test")
    cols = resolve_set("S6")
    pre = Preprocessor(cols).fit(train)
    Ztr = pre.transform(train)
    names = pre.names
    fig, ax = plt.subplots(2, 3, figsize=(12, 6.6), gridspec_kw={"hspace": 0.55, "wspace": 0.28})
    # row 1: a heavy-tailed value
    v = train["import_value_usd"].astype("float64")
    ax[0, 0].hist(v / 1e6, bins=80, color=SLOT[0], zorder=3)
    ax[0, 0].set_yscale("log")
    ax[0, 0].set_title("raw import value (USD m)")
    ax[0, 1].hist(train["log_value"], bins=60, color=SLOT[0], zorder=3)
    ax[0, 1].set_title("log_value = log(1 + value)")
    ax[0, 2].hist(Ztr[:, names.index("log_value")], bins=60, color=SLOT[0], zorder=3)
    ax[0, 2].set_title("model input: (x − mean) / sd, train-fitted")
    # row 2: a feature with structural missingness
    c = "vn_market_share_lag1"
    raw = train[c].astype("float64")
    ax[1, 0].hist(raw.dropna(), bins=60, color=SLOT[0], zorder=3)
    ax[1, 0].set_title(f"{c}\n(observed rows; {raw.isna().mean():.0%} missing)")
    imp = raw.fillna(pre.median_[c])
    ax[1, 1].hist([imp[raw.notna()], imp[raw.isna()]], bins=60, stacked=True,
                  color=[SLOT[0], SLOT[1]], label=["observed", "imputed = train median"],
                  zorder=3)
    ax[1, 1].legend(fontsize=8)
    ax[1, 1].set_title("after median imputation")
    flag = Ztr[:, names.index(f"{c}_isna")]
    ax[1, 2].bar([0, 1], [(raw.notna()).sum(), raw.isna().sum()], color=[SLOT[0], SLOT[1]],
                 width=0.6, zorder=3)
    ax[1, 2].set_xticks([0, 1], ["0 = observed", "1 = missing"])
    ax[1, 2].set_title(f"+ indicator column {c}_isna\n(so 'unknown' ≠ 'zero')")
    for a in ax.flat:
        a.tick_params(labelsize=8.5)
    fig.suptitle("What the fold-fitted preprocessor does (F1 refit training rows, set S6)",
                 x=0.06, ha="left", fontsize=12.5, fontweight="semibold", color=INK)
    save(fig, "05_preprocessing_before_after.png")
    st = pre.state()
    summary = pd.DataFrame({
        "item": ["input columns (S6)", "missing indicators added",
                 "dropped as constant/duplicate in train", "final model columns"],
        "value": [len(cols), len(st["flag_cols"]), len(st["dropped_constant"]),
                  len(st["names"])],
        "detail": [", ".join(cols), ", ".join(st["flag_cols"]),
                   ", ".join(st["dropped_constant"]), ""]})
    write_csv(summary, TAB, "preprocessor_F1_L_S6.csv")


def main():
    fm, sp, b = family_map(), spells(), base()
    print("worked example", EXAMPLE_RELATION)
    fy, s, br, lab, _ = example_captures(fm, sp, b)
    fig_example(fy, s, lab)
    print("funnel")
    funnel(fm, sp, b)
    print("folds")
    fold_tables(b)
    fig_folds()
    print("preprocessing")
    feature_dictionary(b)
    fig_missing(b)
    fig_eligibility()
    fig_transform(b)


if __name__ == "__main__":
    main()
