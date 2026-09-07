"""Step 9 (B3 + B9 prep): turn panel_final.csv into the Stage 1 modelling frame.

panel_final.csv already carries every raw and contemporaneous column B1/B2
produce. Two things are still missing before B4-B9 can run on it:

1. Five B3 covariates that need a group-by over the panel rather than a
   straight column join: volatility_3y, n_products_to_c, n_markets_for_p,
   hs2_share, log_total_import_cp.
2. The t-1 lag of every covariate that goes into the hazard model. B3 is
   explicit: "Moi covariate lay tai t-1" - using the same-year value creates
   simultaneity, since a relationship about to die has already seen its trade
   value collapse.

Lagging is NOT a row shift. A (importer, product_family) pair can carry
several spells with a real calendar gap between them (spell ends 2009, next
one starts 2014), and even within one spell, GAP_TOLERANCE=1 now inserts a
sub-threshold year as its own row. `.shift(1)` after sorting would silently
pull the wrong year's value across either kind of gap. Every lag here is
therefore a join on the true calendar year (t-1), at the grain the variable
actually lives at:

  * relationship-level (value, market share, unit value, the importer's own
    tariff schedule, volatility): joined on (importer, product_family,
    year-1). A brand-new spell's first row has no year-1 row for that pair
    and correctly gets a null lag - that is what "we have no history for this
    relationship" means, and duration dummies in B5 absorb it.
  * importer-year level (GDP, population, portfolio breadth n_products_to_c):
    joined on (importer, year-1) against a *deduplicated* importer-year
    table, so a brand-new relationship still inherits its market's own known
    macro history - only the relationship-level variables should go null on
    a spell's first row, not the country's GDP.
  * product_family-year level (rca, VN's own growth in the product, world
    demand, EVFTA/tariff policy, n_markets_for_p): joined on (product_family,
    year-1). rca and country_growth_pct look relationship-level because they
    sit on every episode row, but build_spells.py computes both as Balassa-
    style indices keyed by (product_family, year) alone - Viet Nam's global
    position in a product, broadcast onto every importer that buys it. Lagged
    at the importer x product_family grain instead, they would wrongly go
    null on a spell's first row for any importer new to the product.
  * importer x HS2-year level (hs2_share, the portfolio-clustering variable):
    joined on (importer, hs2, year-1).

Time-invariant columns (distance, contiguity, common language, staging
category) get no _lag1 twin - there is nothing to lag, and B0's identification
design in B6 reads staging_cat as a pre-determined treatment assignment, not
an outcome.

MEMORY DESIGN - read this before changing anything.

panel_final.csv is ~900 MB / 171 columns / 950k rows. This machine has 7.8 GB
of RAM and no swap headroom to spare, and an earlier version of this script
that read the file once with pl.read_csv() and then chained a dozen eager
.join() calls onto the resulting 171-column frame was OOM-killed (several
full-width copies of a 950k-row frame alive at once). The fix has two parts:

  1. Phase 1 reads only the ~20 columns feature engineering actually needs
     (a `pl.scan_csv(...).select([...])` - polars still has to parse every
     row of a CSV, but never materialises the other ~150 columns), computes
     every side table and every lag on that narrow frame, and collects the
     result as one small "features" table (950k rows x ~30 columns of floats
     and a few strings - tens of MB, not gigabytes).
  2. Phase 2 opens panel_final.csv again, this time as a full-width *lazy*
     scan, joins it against the small in-memory features table from phase 1,
     and writes the result with `sink_parquet()` - which streams row batches
     to disk and never holds the whole 171+30-column result in memory at
     once, unlike `.collect().write_parquet()`.

Two passes over the CSV cost extra wall-clock time; they cost far less
memory, which is the constraint that actually matters here. Do not collapse
this back into a single eager pass without re-checking memory headroom.

Output: data/final/stage1_panel.parquet - the single dataframe B4 through B9
read. Nothing upstream of this script is touched; rerunning it after
merge_panel.py changes reproduces the file from panel_final.csv alone.
"""

import os

import polars as pl

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN_PATH = os.path.join(HERE, "data", "interim", "panel_final.csv")
OUT_DIR = os.path.join(HERE, "data", "final")
OUT_PATH = os.path.join(OUT_DIR, "stage1_panel.parquet")

KEYS = ["importer", "product_family", "year"]
# Every source column phase 1 needs, beyond the keys. Kept to the minimum so
# the narrow scan in phase 1 stays cheap.
SOURCE_COLS = [
    "gap_filled", "import_value_usd", "vn_market_share_pct",
    "unit_value_usd_per_kg", "tariff_rate", "world_growth_pct",
    "country_growth_pct", "rca", "total_import_cp_usd", "tariff_applied_pct",
    "tariff_mfn_pct", "pref_margin_pp", "evfta_cut_cum_pp",
    "evfta_cut_cum_share", "importer_gdp_usd", "importer_gdp_per_capita_usd",
    "importer_population", "importer_gdp_growth_pct",
    "importer_inflation_pct", "importer_exchange_rate_lcu_per_usd",
    "importer_imports_pct_gdp", "importer_exports_pct_gdp",
]

# panel_final.csv writes a handful of un-computable ratios (rca,
# product_share_pct, partner_share_pct, vn_market_share_pct,
# country_growth_pct, world_growth_pct) as the literal text "nan" rather than
# leaving the cell empty - str(float("nan")) in Python is the three
# characters "nan", not blank. A CSV reader that infers a column's dtype from
# its contents then finds that text token mixed in with real numbers and
# reads the whole column as strings. build_spells.py's writer is fixed
# (_rnd()) so a fresh run no longer produces this, but panel_final.csv on
# disk right now still has it, so both reads here must treat "nan" as null
# too, or these six columns arrive in stage1_panel.parquet as strings.
CSV_NULLS = ["", "nan"]

# "Alive" for the portfolio-breadth counts means a genuine >= USD 10,000 year,
# not a sub-threshold year kept in the panel only to satisfy the gap rule.
ACTIVE = pl.col("gap_filled") == 0


def log1p(col):
    return (pl.col(col).cast(pl.Float64) + 1).log()


def log_pos(col):
    c = pl.col(col).cast(pl.Float64)
    return pl.when(c > 0).then(c.log()).otherwise(None)


def lag_lookup(df, source_cols, on):
    """A (on..., year) -> <col>_lag1 table: `df`'s own rows shifted forward
    one year, so joining a target on (on..., year) pulls in the year-1
    value. `df` here is always a small, already-narrow frame - never the
    171-column panel."""
    keys = list(on)
    return (
        df.select(keys + ["year"] + source_cols)
        .unique(subset=keys + ["year"])
        .with_columns((pl.col("year") + 1).alias("year"))
        .rename({c: f"{c}_lag1" for c in source_cols})
    )


def build_features():
    """Phase 1: the narrow read. Returns one small DataFrame, one row per
    (importer, product_family, year), holding every new B3 covariate and
    every _lag1 column - nothing else."""
    print(f"Phase 1 - narrow read of {IN_PATH} "
          f"({len(SOURCE_COLS) + len(KEYS)} of 171 columns)")
    df = (
        pl.scan_csv(IN_PATH, infer_schema_length=None, null_values=CSV_NULLS)
        .select(KEYS + SOURCE_COLS)
        .with_columns(pl.col("product_family").str.slice(3, 2).alias("hs2"))
        .collect()
    )
    print(f"  {df.height:,} rows x {df.width} columns "
          f"({df.estimated_size('mb'):.0f} MB in memory)")

    # --- B3 group 4: portfolio structure (contemporaneous) -----------------
    print("Portfolio structure: n_products_to_c, n_markets_for_p, hs2_share")
    active = df.filter(ACTIVE)
    n_products = active.group_by(["importer", "year"]).agg(
        pl.col("product_family").n_unique().alias("n_products_to_c"))
    n_markets = active.group_by(["product_family", "year"]).agg(
        pl.col("importer").n_unique().alias("n_markets_for_p"))
    hs2_value = active.group_by(["importer", "hs2", "year"]).agg(
        pl.col("import_value_usd").sum().alias("hs2_value_usd"))
    importer_total = active.group_by(["importer", "year"]).agg(
        pl.col("import_value_usd").sum().alias("importer_total_value_usd"))
    hs2_share = (
        hs2_value.join(importer_total, on=["importer", "year"], how="left")
        .with_columns(
            (pl.col("hs2_value_usd") / pl.col("importer_total_value_usd"))
            .alias("hs2_share")
        ).select(["importer", "hs2", "year", "hs2_share"])
    )
    del active, hs2_value, importer_total

    df = df.join(n_products, on=["importer", "year"], how="left")
    df = df.join(n_markets, on=["product_family", "year"], how="left")
    df = df.join(hs2_share, on=["importer", "hs2", "year"], how="left")
    # A row that is itself sub-threshold (gap_filled=1) is not "active" and so
    # never appears on the left side of these aggregates as its own family -
    # but it still needs the market's own n_products_to_c etc for that year,
    # which the join above already supplies from the *other*, active families.

    # --- B3 group 1: volatility_3y (trailing 3y SD of ln value, ending t-1) -
    print("volatility_3y (trailing SD of ln value, ending at t-1)")
    val_lut = df.select(KEYS + ["import_value_usd"])
    vol = val_lut.select(KEYS)
    for k in (1, 2, 3):
        shifted = val_lut.with_columns(
            (pl.col("year") + k).alias("year"),
            log1p("import_value_usd").alias(f"lnv_m{k}"),
        ).select(KEYS + [f"lnv_m{k}"])
        vol = vol.join(shifted, on=KEYS, how="left")
    del val_lut
    vol = (
        vol.with_columns(pl.concat_list(["lnv_m1", "lnv_m2", "lnv_m3"])
                          .list.drop_nulls().alias("_lnv3"))
        .with_columns(
            pl.when(pl.col("_lnv3").list.len() >= 2)
            .then(pl.col("_lnv3").list.std())
            .otherwise(None)
            .alias("volatility_3y_lag1")
        ).select(KEYS + ["volatility_3y_lag1"])
    )
    df = df.join(vol, on=KEYS, how="left")
    del vol

    # --- log transforms needed before/alongside lagging ---------------------
    df = df.with_columns(
        log1p("import_value_usd").alias("log_value"),
        log1p("total_import_cp_usd").alias("log_total_import_cp"),
        log_pos("importer_gdp_usd").alias("log_gdp_d"),
        log_pos("importer_gdp_per_capita_usd").alias("log_gdpcap_d"),
        log_pos("importer_population").alias("log_pop_d"),
    )

    # --- lag joins, grouped by grain -----------------------------------
    print("Lagging relationship-level covariates "
          "(importer x product_family x year-1)")
    df = df.join(
        lag_lookup(df, [
            "log_value", "vn_market_share_pct", "unit_value_usd_per_kg",
            "tariff_rate",
        ], on=["importer", "product_family"]),
        on=["importer", "product_family", "year"], how="left",
    ).rename({"log_value_lag1": "log_value_lag"})

    print("Lagging importer-year covariates (importer x year-1)")
    importer_year = df.select([
        "importer", "year", "log_gdp_d", "log_gdpcap_d", "log_pop_d",
        "importer_gdp_growth_pct", "importer_inflation_pct",
        "importer_exchange_rate_lcu_per_usd", "importer_imports_pct_gdp",
        "importer_exports_pct_gdp", "n_products_to_c",
    ]).unique(subset=["importer", "year"])
    df = df.join(
        lag_lookup(importer_year, [
            "log_gdp_d", "log_gdpcap_d", "log_pop_d",
            "importer_gdp_growth_pct", "importer_inflation_pct",
            "importer_exchange_rate_lcu_per_usd", "importer_imports_pct_gdp",
            "importer_exports_pct_gdp", "n_products_to_c",
        ], on=["importer"]),
        on=["importer", "year"], how="left",
    )
    del importer_year

    print("Lagging product_family-year covariates (product_family x year-1)")
    # These five are constant across every importer for a given
    # (product_family, year) - VN's own global position in the product, not
    # anything about who is buying it - so .unique() may keep whichever
    # importer's row it happens to land on; the value is the same either way.
    broadcast_cols = ["world_growth_pct", "country_growth_pct", "rca",
                       "log_total_import_cp", "n_markets_for_p"]
    family_year = df.select(["product_family", "year"] + broadcast_cols) \
        .unique(subset=["product_family", "year"])

    # These five are the opposite: attach_evfta() in merge_panel.py writes
    # them ONLY on EU27 importer rows and leaves every non-EU row blank -
    # 120 of 147 importers, so an arbitrary .unique() over all importers
    # picks a non-EU (null) row roughly 120/147 of the time and the lag comes
    # out null even when a real EU value exists for that (family, year).
    # drop_nulls() first so only an EU row (which carries the one value all
    # 27 EU27 members share, per attach_evfta()) can be the survivor.
    eu_policy_cols = ["tariff_applied_pct", "tariff_mfn_pct", "pref_margin_pp",
                       "evfta_cut_cum_pp", "evfta_cut_cum_share"]
    eu_policy_year = (
        df.select(["product_family", "year"] + eu_policy_cols)
        .drop_nulls(subset=["tariff_applied_pct"])
        .unique(subset=["product_family", "year"])
    )

    df = df.join(
        lag_lookup(family_year, broadcast_cols, on=["product_family"]),
        on=["product_family", "year"], how="left",
    ).join(
        lag_lookup(eu_policy_year, eu_policy_cols, on=["product_family"]),
        on=["product_family", "year"], how="left",
    ).rename({
        "country_growth_pct_lag1": "growth_lag_pct",
        "rca_lag1": "rca_lag",
        "tariff_applied_pct_lag1": "tariff_applied_lag",
        "pref_margin_pp_lag1": "pref_margin_lag",
        "evfta_cut_cum_pp_lag1": "evfta_cut_cum_pp_lag",
        "evfta_cut_cum_share_lag1": "evfta_cut_cum_share_lag",
    })
    del family_year, eu_policy_year

    print("Lagging importer x HS2-year covariates (hs2_share)")
    hs2_year = df.select(["importer", "hs2", "year", "hs2_share"]) \
        .unique(subset=["importer", "hs2", "year"])
    df = df.join(
        lag_lookup(hs2_year, ["hs2_share"], on=["importer", "hs2"]),
        on=["importer", "hs2", "year"], how="left",
    )
    del hs2_year

    # Only the newly built columns are kept - everything else in SOURCE_COLS
    # was scaffolding to compute them and already lives, unlagged, in
    # panel_final.csv, which phase 2 reads separately.
    new_cols = [c for c in df.columns
                if c not in SOURCE_COLS and c not in ("hs2",)]
    keep = KEYS + [c for c in new_cols if c not in KEYS] + ["hs2"]
    df = df.select(keep)
    print(f"  features table: {df.height:,} rows x {df.width} columns "
          f"({df.estimated_size('mb'):.0f} MB in memory)")
    return df


FEATURES_PATH = os.path.join(OUT_DIR, "_features_tmp.parquet")


def phase1():
    """Runs as its own process (see __main__ below) so its peak memory is
    fully released before phase 2 starts - `del` inside one long-lived
    process is not a guarantee the allocator hands pages back to the OS."""
    os.makedirs(OUT_DIR, exist_ok=True)
    features = build_features()
    features.write_parquet(FEATURES_PATH)
    print(f"  wrote {FEATURES_PATH} ({features.width - len(KEYS)} new cols)")


def phase2():
    """Streaming join of the full 171-column panel against phase 1's small
    features table. sink_parquet() writes batches as they are produced and
    never holds the whole ~200-column result in memory at once."""
    if not os.path.exists(FEATURES_PATH):
        raise SystemExit("Run phase1 first (it writes _features_tmp.parquet)")
    print(f"Phase 2 - streaming join of the full 171-column panel "
          f"against {FEATURES_PATH}")
    full = pl.scan_csv(IN_PATH, infer_schema_length=None, null_values=CSV_NULLS)
    joined = full.join(pl.scan_parquet(FEATURES_PATH), on=KEYS, how="left")
    joined.sink_parquet(OUT_PATH, compression="zstd")
    os.remove(FEATURES_PATH)

    size_mb = os.path.getsize(OUT_PATH) / 1e6
    result = pl.scan_parquet(OUT_PATH)
    n_rows = result.select(pl.len()).collect().item()
    cols = result.collect_schema().names()
    print(f"\nWrote {OUT_PATH}")
    print(f"  {n_rows:,} rows, {len(cols)} columns, {size_mb:.1f} MB")
    lag_cols = [c for c in cols if c.endswith(("_lag", "_lag1"))]
    print(f"  {len(lag_cols)} lagged covariate columns: {sorted(lag_cols)}")


if __name__ == "__main__":
    import sys
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase in ("features", "all"):
        phase1()
    if phase in ("join", "all"):
        phase2()
