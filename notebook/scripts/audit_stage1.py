"""Audit the Stage 1 panel against the checks in docs/STAGE1_PANEL_FIX_PLAN.md §6.

Every check is recomputed from the parquet and, where it matters, from the raw
files - never read back from a column the build wrote about itself. That is the
point of the harness: a build can only claim a fix if an independent reading of
its output agrees.

The product-family key is the one thing the audit has to take from the build,
because it is a definition, not a measurement. Without --family-map the WITS
many-to-one reading of v1 is rebuilt here from the concordance tables; with it,
the (revision, hs6) -> family table the v2 build wrote is used.

Usage:
    python3 scripts/audit_stage1.py --tag v1
    python3 scripts/audit_stage1.py --tag v2 --family-map data/interim/family_map.csv
    python3 scripts/audit_stage1.py --tag v2 --family-map ... --compare other.parquet

Output: docs/audit/stage1_<tag>.md and docs/audit/stage1_<tag>.json
"""

import argparse
import csv
import glob
import gzip
import json
import os
from collections import Counter, defaultdict

import polars as pl

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_TRADE = os.path.join(HERE, "data", "raw", "trade")
RAW_MFN = os.path.join(HERE, "data", "raw", "tariffs", "mfn")
CONC = os.path.join(HERE, "data", "raw", "concordance")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "docs", "audit")
# the EU schedule the eu_family lags are checked against; --eu-panel points it
# at the copy that matches the panel's own family key (v1: data/v1_backup)
EU_PANEL = [os.path.join(HERE, "data", "interim", "eu_tariff_panel.csv")]
KEYS = ["importer", "product_family", "year"]
REVS = ["H1", "H2", "H3", "H4", "H5", "H6"]
THRESHOLD = 10_000
GAP_TOLERANCE = 1
# Reason text fetch_trade.py writes when a multi-year request answered for the
# other years only: the year was not published, not found empty.
BATCH_EMPTY = "no HS6 rows in a batch that returned data for other years"
# Source-year columns that describe a single static estimate by design; a
# source year after the row year is documented, not a leak.
STATIC_SOURCE_COLS = {"ntm_ave_source_year", "ntm_survey_year"}
MASS_DEATH_SHARE, MASS_DEATH_MIN_N = 0.6, 30
VALUE_CHECK_IMPORTERS = ["DEU", "USA", "FRA", "ARE"]
MFN_CHECK_REPORTERS = ["USA", "BRA", "ZAF", "IND", "CAN"]
TTB_COLS = ["ad_initiated", "ad_in_force", "cvd_initiated", "cvd_in_force",
            "sg_initiated", "sg_in_force", "ttb_any_in_force"]

# (lag column, source column, grain). "eu_family" means the family grain over
# EU rows only, which is where attach_evfta() writes those columns.
LAGS = [
    ("log_value_lag", "log_value", "rel"),
    ("vn_market_share_pct_lag1", "vn_market_share_pct", "rel"),
    ("unit_value_usd_per_kg_lag1", "unit_value_usd_per_kg", "rel"),
    ("tariff_rate_lag1", "tariff_rate", "rel"),
    ("log_total_import_cp_lag1", "log_total_import_cp", "rel"),
    ("log_gdp_d_lag1", "log_gdp_d", "imp"),
    ("log_gdpcap_d_lag1", "log_gdpcap_d", "imp"),
    ("log_pop_d_lag1", "log_pop_d", "imp"),
    ("importer_gdp_growth_pct_lag1", "importer_gdp_growth_pct", "imp"),
    ("importer_inflation_pct_lag1", "importer_inflation_pct", "imp"),
    ("importer_exchange_rate_lcu_per_usd_lag1",
     "importer_exchange_rate_lcu_per_usd", "imp"),
    ("importer_imports_pct_gdp_lag1", "importer_imports_pct_gdp", "imp"),
    ("importer_exports_pct_gdp_lag1", "importer_exports_pct_gdp", "imp"),
    ("n_products_to_c_lag1", "n_products_to_c", "imp"),
    ("world_growth_pct_lag1", "world_growth_pct", "fam"),
    ("growth_lag_pct", "country_growth_pct", "fam"),
    ("rca_lag", "rca", "fam"),
    ("n_markets_for_p_lag1", "n_markets_for_p", "fam"),
    ("tariff_applied_lag", "tariff_applied_pct", "eu_family"),
    ("tariff_mfn_pct_lag1", "tariff_mfn_pct", "eu_family"),
    ("pref_margin_lag", "pref_margin_pp", "eu_family"),
    ("evfta_cut_cum_pp_lag", "evfta_cut_cum_pp", "eu_family"),
    ("evfta_cut_cum_share_lag", "evfta_cut_cum_share", "eu_family"),
    ("hs2_share_lag1", "hs2_share", "hs2"),
]


# --- reference data ---------------------------------------------------------
def wits_tables():
    out = {}
    for rev in REVS:
        path = glob.glob(os.path.join(CONC, f"{rev}_to_H0", "*.CSV"))[0]
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            out[rev] = {r[0].strip(): r[2].strip() for r in csv.reader(f)
                        if len(r) >= 3 and len(r[0].strip()) == 6
                        and r[0].strip().isdigit() and r[2].strip().isdigit()}
    return out


class Families:
    """(revision, hs6) -> family, and the set of families each revision can
    express. v1: the WITS many-to-one reading. v2: the build's own map."""

    def __init__(self, map_path=None):
        self.code = {}
        if map_path:
            with open(map_path, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    self.code[(r["revision"], r["hs6"])] = r["family"]
        else:
            for rev, tab in wits_tables().items():
                for src, dst in tab.items():
                    self.code[(rev, src)] = f"H0_{dst}"
                    self.code[("H0", dst)] = f"H0_{dst}"
        self.in_rev = defaultdict(set)
        for (rev, _), fam in self.code.items():
            self.in_rev[rev].add(fam)
        self.in_rev["H0"] = set(self.code.values())
        self.source = "family map" if map_path else "WITS many-to-one (v1)"

    def of(self, rev, code):
        """None when the code is outside the map; the build then keeps it as a
        singleton family, which scan_raw_trade() mirrors for the value check."""
        fam = self.code.get((rev, code))
        if fam is None:
            fam = self.code.get(("H0", code))
        return fam


def eu27_members():
    m = pl.read_csv(os.path.join(SEL, "eu_tariff_mapping.csv"))
    eun = m.filter(pl.col("tariff_reporter") == "EUN")
    last = eun["year"].max()
    return sorted(eun.filter(pl.col("year") == last)["iso3"].to_list())


def observed_years():
    """importer -> (observed years, batch-empty years), read off the raw folder."""
    seen, batch = defaultdict(set), defaultdict(set)
    for path in glob.glob(os.path.join(RAW_TRADE, "*.csv.gz")):
        iso, year = os.path.basename(path)[:-7].rsplit("_", 1)
        seen[iso].add(int(year))
    with open(os.path.join(RAW_TRADE, "_empty_years.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            batch[r["importer"]].add(int(r["year"]))
    partial = os.path.join(SEL, "hs6_unobserved_years.csv")
    if os.path.exists(partial):
        with open(partial, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                seen[r["importer"]].discard(int(r["year"]))
                batch[r["importer"]].add(int(r["year"]))
    return seen, batch


def scan_raw_trade(fams):
    """One pass over the Viet Nam rows: revision per importer-year, value outside
    the family map, and (importer, family, year) sums for the value check."""
    rev_value = defaultdict(Counter)
    total = unmapped = 0.0
    sums = defaultdict(float)
    for path in sorted(glob.glob(os.path.join(RAW_TRADE, "*.csv.gz"))):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["exporter"] != "VNM":
                    continue
                year = int(r["year"])
                if not 2002 <= year <= 2025:
                    continue
                v = float(r["import_value_usd"] or 0)
                rev = r["hs_revision"] or "H0"
                rev_value[(r["importer"], year)][rev] += v
                total += v
                fam = fams.of(rev, r["hs6"])
                if fam is None:
                    unmapped += v
                    fam = f"{rev}_{r['hs6']}"
                if r["importer"] in VALUE_CHECK_IMPORTERS:
                    sums[(r["importer"], fam, year)] += v
    revision = {k: max(c, key=c.get) for k, c in rev_value.items()}
    return revision, (unmapped / total if total else 0.0), sums


# --- checks -------------------------------------------------------------------
def spell_checks(df):
    g = df.group_by("spell_id").agg(
        pl.len().alias("n"), pl.col("year").min().alias("ymin"),
        pl.col("year").max().alias("ymax"),
        pl.col("spell_start_year").first().alias("s"),
        pl.col("spell_end_year").first().alias("e"),
        pl.col("event").sum().alias("ev"),
        pl.col("right_censored").n_unique().alias("rcu"),
        pl.col("right_censored").first().alias("rc"))
    return {
        "non_contiguous": g.filter(pl.col("n") != pl.col("ymax") - pl.col("ymin") + 1).height,
        "start_end_mismatch": g.filter((pl.col("s") != pl.col("ymin")) | (pl.col("e") != pl.col("ymax"))).height,
        "event_ne_1_minus_rc": g.filter(pl.col("ev") != 1 - pl.col("rc")).height,
        "rc_not_constant": g.filter(pl.col("rcu") > 1).height,
        "event_not_last_row": df.filter((pl.col("event") == 1) & (pl.col("year") != pl.col("spell_end_year"))).height,
        "t_stop_wrong": df.filter(pl.col("t_stop") != pl.col("year") - pl.col("spell_start_year") + 1).height,
        "alive_below_threshold": df.filter((pl.col("gap_filled") == 0) & (pl.col("import_value_usd") < THRESHOLD)).height,
        "gap_at_or_above_threshold": df.filter((pl.col("gap_filled") == 1) & (pl.col("import_value_usd") >= THRESHOLD)).height,
        "gap_row_at_spell_edge": df.filter((pl.col("gap_filled") == 1) & ((pl.col("year") == pl.col("spell_start_year")) | (pl.col("year") == pl.col("spell_end_year")))).height,
    }


def revision_frame(revision):
    return pl.DataFrame({"importer": [k[0] for k in revision],
                         "year": [k[1] for k in revision],
                         "rev": list(revision.values())})


def orphan_checks(df, fams, revision):
    """A5: rows whose family cannot be expressed in the importer's next-year
    revision. A6: births in the first year of a new revision."""
    rv = revision_frame(revision)
    nxt = rv.with_columns(pl.col("year") - 1).rename({"rev": "rev_next"})
    prv = rv.with_columns(pl.col("year") + 1).rename({"rev": "rev_prev"})
    d = (df.select(["importer", "product_family", "year", "gap_filled", "event",
                    "spell_start_year", "left_trunc"])
         .join(rv, on=["importer", "year"], how="left")
         .join(nxt, on=["importer", "year"], how="left")
         .join(prv, on=["importer", "year"], how="left"))
    combos = d.select(["product_family", "rev", "rev_next"]).unique().drop_nulls()
    flags = [int(r["rev"] != r["rev_next"]
                 and r["product_family"] in fams.in_rev[r["rev"]]
                 and r["product_family"] not in fams.in_rev[r["rev_next"]])
             for r in combos.iter_rows(named=True)]
    combos = combos.with_columns(pl.Series("exposed", flags, dtype=pl.Int8))
    d = d.join(combos, on=["product_family", "rev", "rev_next"], how="left") \
         .with_columns(pl.col("exposed").fill_null(0))
    alive = d.filter(pl.col("gap_filled") == 0)
    exp = alive.filter(pl.col("exposed") == 1)
    out = {"exposed_rows": exp.height, "exposed_events": int(exp["event"].sum())}

    # A6, within importer: first year of a new revision vs +-2 other years
    b = alive.filter(pl.col("rev_prev").is_not_null() & (pl.col("left_trunc") == 0)) \
        .with_columns((pl.col("rev_prev") != pl.col("rev")).alias("first_new"),
                      (pl.col("spell_start_year") == pl.col("year")).alias("birth"))
    sw = b.filter(pl.col("first_new")).select(["importer", "year"]).unique() \
        .rename({"year": "sy"})
    w = b.join(sw, on="importer").filter((pl.col("year") - pl.col("sy")).abs() <= 2)
    w = w.filter((pl.col("year") == pl.col("sy")) | ~pl.col("first_new"))
    r = (w.group_by(["importer", "sy", (pl.col("year") == pl.col("sy")).alias("at")])
         .agg(pl.col("birth").mean().alias("b"))
         .pivot(on="at", index=["importer", "sy"], values="b").drop_nulls())
    out["birth_share_switch"] = float(r["true"].mean())
    out["birth_share_neighbours"] = float(r["false"].mean())
    out["birth_excess_pp"] = 100 * (out["birth_share_switch"] - out["birth_share_neighbours"])
    return out


def window_checks(df, seen, batch):
    alive = df.filter(pl.col("gap_filled") == 0)
    # A7 mass deaths
    allow = set()
    path = os.path.join(SEL, "mass_death_allowlist.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            allow = {(r["importer"], int(r["year"])) for r in csv.DictReader(f)}
    iy = alive.group_by(["importer", "year"]).agg(pl.len().alias("n"),
                                                  pl.col("event").mean().alias("share"))
    mass = iy.filter((pl.col("n") >= MASS_DEATH_MIN_N) & (pl.col("share") > MASS_DEATH_SHARE))
    mass_rows = [(r["importer"], r["year"], r["n"], round(r["share"], 3))
                 for r in mass.sort(["year", "importer"]).iter_rows(named=True)]
    not_allowed = [m for m in mass_rows if (m[0], m[1]) not in allow]
    # A8 events not confirmed: with the gap rule a death in E needs every year
    # E+1 .. E+1+GAP_TOLERANCE published at HS6 (a file with enough coverage)
    ev = alive.filter(pl.col("event") == 1).select(["importer", "year"])
    a8 = sum(1 for imp, y in ev.iter_rows()
             if any(z not in seen.get(imp, ()) for z in range(y + 1, y + 2 + GAP_TOLERANCE)))
    # A9 hazard at T-1 against T-2..T-5, T = last published year
    last = pl.DataFrame({"importer": list(seen),
                         "T": [max(y for y in ys if y <= 2025) for ys in seen.values()]})
    k = alive.join(last, on="importer").with_columns((pl.col("T") - pl.col("year")).alias("k"))
    hz = k.filter(pl.col("k").is_between(1, 6 + GAP_TOLERANCE)).group_by("k").agg(
        pl.len().alias("n"), pl.col("event").mean().alias("h")).sort("k")
    h = dict(zip(hz["k"].to_list(), hz["h"].to_list()))
    edge = 1 + GAP_TOLERANCE                 # last year a death can be confirmed
    base = sum(h.get(i, 0) for i in range(edge + 1, edge + 5)) / 4
    unconfirmable = int(k.filter(pl.col("k").is_between(1, GAP_TOLERANCE)
                                 & (pl.col("event") == 1)).height)
    return {"mass_death_importer_years": mass_rows,
            "mass_death_not_allowlisted": len(not_allowed),
            "events_not_confirmed": a8,
            "hazard_by_years_before_T": {int(a): round(b, 4) for a, b in h.items()},
            "events_in_last_gap_years": unconfirmable,
            "hazard_edge_minus_base_pp": 100 * (h.get(edge, 0) - base)}


def eu_member_years():
    """(importer, year) pairs that read the EUN schedule, GBR excluded."""
    m = pl.read_csv(os.path.join(SEL, "eu_tariff_mapping.csv"))
    return m.filter((pl.col("tariff_reporter") == "EUN") & (pl.col("iso3") != "GBR")) \
        .select(pl.col("iso3").alias("importer"), pl.col("year").cast(pl.Int64))


def eu_policy_table():
    """(product_family, year) -> the five EU policy columns, computed from
    data/interim/eu_tariff_panel.csv exactly as merge_panel.load_evfta() does."""
    t = pl.read_csv(EU_PANEL[0], infer_schema_length=0)
    f = lambda c: pl.col(c).cast(pl.Float64, strict=False)
    cut = pl.when((f("evfta_base_pct") > 0) & f("evfta_pct").is_not_null()) \
        .then(f("evfta_base_pct") - f("evfta_pct")).otherwise(0.0)
    return t.select(
        pl.col("product_family"), pl.col("year").cast(pl.Int64),
        f("applied_pct").alias("tariff_applied_pct"),
        f("mfn_pct").alias("tariff_mfn_pct"),
        f("pref_margin_pp").alias("pref_margin_pp"),
        cut.round(4).alias("evfta_cut_cum_pp"),
        pl.when(f("evfta_base_pct") > 0).then((cut / f("evfta_base_pct")).round(4))
        .otherwise(0.0).alias("evfta_cut_cum_share"))


def lag_checks(panel_path, eu):
    """A10 (lag equals own year-1 value at the declared grain) and A11 (every
    family-grain source is constant within (family, year))."""
    schema = pl.scan_parquet(panel_path).collect_schema().names()
    res, const = {}, {}
    for lag, src, grain in LAGS:
        if lag not in schema or src not in schema:
            res[lag] = "column missing"
            continue
        d = pl.read_parquet(panel_path, columns=KEYS + ["hs2", lag, src]
                            if grain == "hs2" else KEYS + [lag, src])
        if grain == "rel":
            on = ["importer", "product_family"]
            prev = d.select(on + ["year", src])
        elif grain == "imp":
            on = ["importer"]
            prev = d.select(on + ["year", src]).drop_nulls(src).unique(subset=on + ["year"], keep="first")
        elif grain == "hs2":
            on = ["importer", "hs2"]
            prev = d.select(on + ["year", src]).drop_nulls(src).unique(subset=on + ["year"], keep="first")
        elif grain == "eu_family":
            # the declared source is the EU-wide schedule itself, not the rows
            # that happen to trade: a tariff exists whether or not anyone
            # imported the family last year
            on = ["product_family"]
            prev = eu_policy_table().select(on + ["year", src]).drop_nulls(src)
            nu = d.filter(pl.col("importer").is_in(eu)).drop_nulls(src) \
                .group_by(on + ["year"]).agg(pl.col(src).n_unique().alias("nu"))
            const[src] = float((nu["nu"] > 1).mean()) if nu.height else 0.0
        else:
            on = ["product_family"]
            prev = d.select(on + ["year", src]).drop_nulls(src)
            nu = prev.group_by(on + ["year"]).agg(pl.col(src).n_unique().alias("nu"))
            const[src] = float((nu["nu"] > 1).mean()) if nu.height else 0.0
            prev = prev.unique(subset=on + ["year"], keep="first")
        prev = prev.with_columns(pl.col("year") + 1).rename({src: "_expect"})
        x = d.join(prev, on=on + ["year"], how="left")
        if grain == "eu_family":
            # members only in the years they read the EU schedule: before
            # accession (HRV to 2012, BGR/ROU to 2006...) there is no EU tariff
            x = x.join(eu_member_years(), on=["importer", "year"], how="semi")
        both = x.filter(pl.col(lag).is_not_null() | pl.col("_expect").is_not_null())
        bad = both.filter(~((pl.col(lag).cast(pl.Float64) - pl.col("_expect").cast(pl.Float64)).abs() <= 1e-6).fill_null(False))
        res[lag] = {"grain": grain, "rows": both.height, "mismatch": bad.height,
                    "mismatch_share": round(bad.height / both.height, 4) if both.height else 0.0}
    # log_total_import_cp is reported here too: v1 lagged it at family grain
    if "log_total_import_cp" in schema:
        d = pl.read_parquet(panel_path, columns=KEYS + ["log_total_import_cp"]).drop_nulls()
        nu = d.group_by(["product_family", "year"]).agg(pl.col("log_total_import_cp").n_unique().alias("nu"))
        const["log_total_import_cp (importer-specific, info)"] = float((nu["nu"] > 1).mean())
    return res, const


def source_year_checks(panel_path, b0_filter):
    cols = [c for c in pl.scan_parquet(panel_path).collect_schema().names()
            if c.endswith("_source_year") or c == "ntm_survey_year"]
    d = pl.read_parquet(panel_path, columns=["importer", "year", "gap_filled"] + cols)
    out = {}
    for scope, frame in (("full", d), ("b0", b0_filter(d))):
        for c in cols:
            s = frame.filter(pl.col(c).is_not_null())
            fut = s.filter(pl.col(c) > pl.col("year")).height
            out[f"{scope}:{c}"] = {"future_rows": fut,
                                   "future_share": round(fut / s.height, 4) if s.height else 0.0,
                                   "static_allowlisted": c in STATIC_SOURCE_COLS}
    return out


def tariff_checks(panel_path, eu, fams):
    d = pl.read_parquet(panel_path, columns=["importer", "year", "gap_filled", "tariff_rate",
                                             "tariff_rate_lag1", "tariff_type",
                                             "tariff_source_year", "tariff_reporter",
                                             "product_family", "fta_in_force"])
    e = d.filter(pl.col("importer").is_in(eu) & (pl.col("gap_filled") == 0))
    null_2425 = e.filter(pl.col("year") >= 2024)["tariff_rate"].is_null().mean()
    ch = e.filter(pl.col("year") >= 2003).group_by("year").agg(
        (pl.col("tariff_rate") - pl.col("tariff_rate_lag1")).mean().alias("dt")).sort("year")
    changes = {int(y): round(v, 3) for y, v in zip(ch["year"], ch["dt"]) if v is not None}
    worst = max((abs(v) for y, v in changes.items() if y != 2020), default=0.0)
    # A15: family MFN rate against the true mean of its lines, sample reporters
    mism = checked = 0
    for rep in MFN_CHECK_REPORTERS:
        truth = {}
        for path in glob.glob(os.path.join(RAW_MFN, f"{rep}_*.csv.gz")):
            year = int(os.path.basename(path)[:-7].rsplit("_", 1)[1])
            acc = defaultdict(list)
            with gzip.open(path, "rt", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r["rate_simple_avg"] in (None, ""):
                        continue
                    fam = fams.of(r["nomen"] or "H0", r["product"])
                    if fam:
                        acc[fam].append(float(r["rate_simple_avg"]))
            for fam, v in acc.items():
                truth[(fam, year)] = sum(v) / len(v)
        rows = d.filter((pl.col("importer") == rep) & (pl.col("tariff_type") == "MFN")
                        & (pl.col("tariff_source_year") == pl.col("year"))
                        & (pl.col("tariff_reporter") == rep))
        for fam, year, rate in rows.select(["product_family", "year", "tariff_rate"]).iter_rows():
            t = truth.get((fam, year))
            if t is None or rate is None:
                continue
            checked += 1
            if abs(t - rate) > 0.01:
                mism += 1
    # A19 report: PREF share on rows with an FTA in force
    pref = (d.filter((pl.col("gap_filled") == 0) & (pl.col("fta_in_force") == 1))
            .group_by("importer").agg(pl.len().alias("n"),
                                      (pl.col("tariff_type") != "MFN").mean().round(3).alias("non_mfn_share"))
            .sort("n", descending=True).head(20))
    return {"eu27_tariff_null_share_2024_2025": round(float(null_2425), 4),
            "eu27_mean_tariff_change_by_year": changes,
            "eu27_max_abs_mean_change_excl_2020": worst,
            "mfn_rows_checked": checked, "mfn_rows_mismatch": mism,
            "non_mfn_share_on_fta_rows_top20": [tuple(r) for r in pref.iter_rows()]}


def value_check(panel_path, sums):
    d = pl.read_parquet(panel_path, columns=KEYS + ["import_value_usd"]).filter(
        pl.col("importer").is_in(VALUE_CHECK_IMPORTERS))
    bad = sum(1 for imp, fam, y, v in d.iter_rows()
              if abs(v - sums.get((imp, fam, y), 0.0)) > 1)
    return {"rows": d.height, "mismatch": bad}


def ttb_check(panel_path):
    names = pl.scan_parquet(panel_path).collect_schema().names()
    cols = [c for c in TTB_COLS if c in names]
    d = pl.read_parquet(panel_path, columns=["year", "ttbd_observed"] + cols)
    last = d.filter(pl.col("ttbd_observed") == 1)["year"].max()
    after = d.filter(pl.col("year") > last)
    return {"last_ttbd_year": last,
            "non_null_after": {c: int(after[c].is_not_null().sum()) for c in cols}}


def determinism(a, b):
    """Order-independent per-column hash comparison, one column at a time."""
    ca = pl.scan_parquet(a).collect_schema().names()
    cb = pl.scan_parquet(b).collect_schema().names()
    if ca != cb:
        return {"same_columns": False}
    diff = []
    for c in ca:
        h = []
        for p in (a, b):
            cols = KEYS + ([c] if c not in KEYS else [])
            s = pl.read_parquet(p, columns=cols).select(pl.struct(cols).hash(seed=0).alias("h"))
            h.append(int(s["h"].cast(pl.UInt64).sum()) if s.height else 0)
        if h[0] != h[1]:
            diff.append(c)
    return {"same_columns": True, "columns_differing": diff}


# --- report -------------------------------------------------------------------
def summary(df, eu):
    b0 = df.filter(pl.col("importer").is_in(eu) & (pl.col("gap_filled") == 0)
                   & pl.col("year").is_between(2012, 2024))
    by = (df.filter(pl.col("gap_filled") == 0)
          .with_columns(pl.col("importer").is_in(eu).alias("eu27"))
          .group_by(["year", "eu27"]).agg(pl.len().alias("alive"), pl.col("event").sum().alias("events"))
          .sort(["year", "eu27"]))
    return {"rows": df.height, "spells": df["spell_id"].n_unique(),
            "importers": df["importer"].n_unique(), "families": df["product_family"].n_unique(),
            "events": int(df["event"].sum()),
            "b0_rows": b0.height, "b0_events": int(b0["event"].sum()),
            "events_by_year": [tuple(r) for r in by.iter_rows()]}


def verdicts(r):
    a = r["checks"]
    return [
        ("A1", "duplicate keys", a["A1_duplicate_keys"] == 0, a["A1_duplicate_keys"]),
        ("A2", "spell invariants", all(v == 0 for v in a["A2_spells"].values()), a["A2_spells"]),
        ("A3", "raw value outside family map", a["A3_unmapped_value_share"] < 1e-6, a["A3_unmapped_value_share"]),
        ("A4", "families whose H0 members span >1 HS4", a["A4_multi_hs4_h0_families"] == 0, a["A4_multi_hs4_h0_families"]),
        ("A5", "orphan-exposed rows with event=1", a["A5_A6_orphans"]["exposed_events"] == 0,
         f"{a['A5_A6_orphans']['exposed_events']}/{a['A5_A6_orphans']['exposed_rows']}"),
        ("A6", "birth excess at first year of new revision (pp)", a["A5_A6_orphans"]["birth_excess_pp"] <= 0.5,
         round(a["A5_A6_orphans"]["birth_excess_pp"], 2)),
        ("A7", "mass-death importer-years not allowlisted", a["A7_A8_A9_window"]["mass_death_not_allowlisted"] == 0,
         a["A7_A8_A9_window"]["mass_death_not_allowlisted"]),
        ("A8", "events not confirmed by observed HS6 years", a["A7_A8_A9_window"]["events_not_confirmed"] == 0,
         a["A7_A8_A9_window"]["events_not_confirmed"]),
        ("A9", "events in T-1..T-gap / hazard at last confirmable year minus the 4 before (pp)",
         a["A7_A8_A9_window"]["events_in_last_gap_years"] == 0
         and abs(a["A7_A8_A9_window"]["hazard_edge_minus_base_pp"]) <= 1.5,
         f"{a['A7_A8_A9_window']['events_in_last_gap_years']} / "
         f"{round(a['A7_A8_A9_window']['hazard_edge_minus_base_pp'], 2)}"),
        ("A10", "lag mismatches", all(isinstance(v, dict) and v["mismatch"] == 0 for v in a["A10_lags"].values()),
         {k: v["mismatch"] if isinstance(v, dict) else v for k, v in a["A10_lags"].items()
          if not isinstance(v, dict) or v["mismatch"]}),
        ("A11", "family-grain sources not constant", all(v == 0 for k, v in a["A11_constancy"].items() if "info" not in k),
         {k: round(v, 4) for k, v in a["A11_constancy"].items()}),
        ("A12", "future-dated source years (non-static)",
         all(v["future_rows"] == 0 for v in a["A12_source_years"].values() if not v["static_allowlisted"]),
         {k: v["future_share"] for k, v in a["A12_source_years"].items() if v["future_rows"]}),
        ("A13", "EU27 tariff_rate null share 2024-25", a["A13_A15_A19_tariffs"]["eu27_tariff_null_share_2024_2025"] == 0,
         a["A13_A15_A19_tariffs"]["eu27_tariff_null_share_2024_2025"]),
        ("A14", "EU27 max abs(mean tariff_change) excl. 2020 (pp)", a["A13_A15_A19_tariffs"]["eu27_max_abs_mean_change_excl_2020"] <= 1,
         a["A13_A15_A19_tariffs"]["eu27_max_abs_mean_change_excl_2020"]),
        ("A15", "MFN family rate != true mean of lines", a["A13_A15_A19_tariffs"]["mfn_rows_mismatch"] == 0,
         f"{a['A13_A15_A19_tariffs']['mfn_rows_mismatch']}/{a['A13_A15_A19_tariffs']['mfn_rows_checked']}"),
        ("A16", "value re-aggregation mismatches", a["A16_values"]["mismatch"] == 0,
         f"{a['A16_values']['mismatch']}/{a['A16_values']['rows']}"),
        ("A17", "TTBD values after last TTBD year", all(v == 0 for v in a["A17_ttbd"]["non_null_after"].values()),
         sum(a["A17_ttbd"]["non_null_after"].values())),
        ("A18", "deterministic rebuild", None if a.get("A18_determinism") is None
         else not a["A18_determinism"].get("columns_differing", ["?"]),
         a.get("A18_determinism") or "not run"),
    ]


def write_report(tag, res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"stage1_{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    lines = [f"# Stage 1 panel audit: {tag}", "",
             f"Panel: `{res['panel']}` - family key: {res['family_source']}.",
             "Generated by `scripts/audit_stage1.py`; the checks are defined in "
             "[STAGE1_PANEL_FIX_PLAN.md](../STAGE1_PANEL_FIX_PLAN.md) §6.", "",
             "| # | Check | Pass | Value |", "|---|---|---|---|"]
    for cid, name, ok, val in verdicts(res):
        mark = "n/a" if ok is None else ("yes" if ok else "**NO**")
        v = json.dumps(val, default=str) if not isinstance(val, (int, float, str)) else val
        lines.append(f"| {cid} | {name} | {mark} | {v} |")
    s = res["summary"]
    lines += ["", "## Summary", "",
              f"- rows {s['rows']:,}, spells {s['spells']:,}, importers {s['importers']}, "
              f"families {s['families']:,}, events {s['events']:,}",
              f"- B0 (EU27, 2012-2024, alive rows): {s['b0_rows']:,} rows, {s['b0_events']:,} events", "",
              "| year | EU27 alive | EU27 events | non-EU alive | non-EU events |", "|---|---|---|---|---|"]
    by = defaultdict(dict)
    for y, eu, alive, ev in s["events_by_year"]:
        by[y][eu] = (alive, ev)
    for y in sorted(by):
        e, n = by[y].get(True, (0, 0)), by[y].get(False, (0, 0))
        lines.append(f"| {y} | {e[0]:,} | {e[1]:,} | {n[0]:,} | {n[1]:,} |")
    w = res["checks"]["A7_A8_A9_window"]
    lines += ["", "## Detail", "",
              f"- A7 mass-death importer-years (n >= {MASS_DEATH_MIN_N}, share > {MASS_DEATH_SHARE}): "
              f"{w['mass_death_importer_years']}",
              f"- A9 hazard by years before last published year: {w['hazard_by_years_before_T']}",
              f"- A14 EU27 mean tariff_change by year: {res['checks']['A13_A15_A19_tariffs']['eu27_mean_tariff_change_by_year']}",
              f"- A19 non-MFN share on FTA rows (top 20 importers by rows): "
              f"{res['checks']['A13_A15_A19_tariffs']['non_mfn_share_on_fta_rows_top20']}",
              f"- A5/A6 detail: {res['checks']['A5_A6_orphans']}", ""]
    with open(os.path.join(OUT, f"stage1_{tag}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=os.path.join(HERE, "data", "final", "stage1_panel.parquet"))
    ap.add_argument("--tag", required=True)
    ap.add_argument("--family-map", default=None)
    ap.add_argument("--compare", default=None, help="second parquet for A18")
    ap.add_argument("--eu-panel", default=EU_PANEL[0])
    args = ap.parse_args()
    EU_PANEL[0] = args.eu_panel

    fams = Families(args.family_map)
    eu = eu27_members()
    print("scanning raw trade ...", flush=True)
    revision, unmapped, sums = scan_raw_trade(fams)
    seen, batch = observed_years()

    df = pl.read_parquet(args.panel, columns=["spell_id", "importer", "product_family", "year",
                                              "spell_start_year", "spell_end_year", "right_censored",
                                              "left_trunc", "gap_filled", "t_start", "t_stop", "event",
                                              "import_value_usd"])

    def b0_filter(frame):
        return frame.filter(pl.col("importer").is_in(eu) & (pl.col("gap_filled") == 0)
                            & pl.col("year").is_between(2012, 2024))

    h0_members = defaultdict(set)
    for (rev, code), fam in fams.code.items():
        if rev == "H0":
            h0_members[fam].add(code[:4])
    checks = {
        "A1_duplicate_keys": df.height - df.select(KEYS).unique().height,
        "A2_spells": spell_checks(df),
        "A3_unmapped_value_share": unmapped,
        "A4_multi_hs4_h0_families": sum(1 for v in h0_members.values() if len(v) > 1),
    }
    print("orphans ...", flush=True)
    checks["A5_A6_orphans"] = orphan_checks(df, fams, revision)
    checks["A7_A8_A9_window"] = window_checks(df, seen, batch)
    res_summary = summary(df, eu)
    del df
    print("lags ...", flush=True)
    checks["A10_lags"], checks["A11_constancy"] = lag_checks(args.panel, eu)
    checks["A12_source_years"] = source_year_checks(args.panel, b0_filter)
    print("tariffs ...", flush=True)
    checks["A13_A15_A19_tariffs"] = tariff_checks(args.panel, eu, fams)
    checks["A16_values"] = value_check(args.panel, sums)
    checks["A17_ttbd"] = ttb_check(args.panel)
    checks["A18_determinism"] = determinism(args.panel, args.compare) if args.compare else None
    res = {"tag": args.tag, "panel": os.path.relpath(args.panel, HERE),
           "family_source": fams.source, "checks": checks, "summary": res_summary}
    for line in write_report(args.tag, res)[:30]:
        print(line)


if __name__ == "__main__":
    main()
