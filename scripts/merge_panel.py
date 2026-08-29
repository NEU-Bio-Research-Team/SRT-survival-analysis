"""Step 6d: attach tariffs and macro controls to the spell-year episodes.

Tariff matching mirrors how the trade panel was built:

  * the tariff is the one the *importer* levies on the product, so the TRAINS
    reporter is the importer (with EU members reading the EUN schedule);
  * TRAINS reports under its own HS revision, so codes are folded into the same
    product families as the trade data before matching;
  * the applied rate is the preferential rate when the exporter has one that
    year, otherwise MFN - which is what an exporter actually faces.

TRAINS has gaps (no schedule filed in a given year). Rather than leaving those
episodes blank, the nearest earlier year within 3 years is carried forward and
flagged in `tariff_source_year`, so the gap is visible in the analysis instead
of silently dropping observations.

NTM columns come from build_ntm.py and are time-invariant by construction: the
public files hold one survey year per country at sector level, so every episode
of a given importer-sector carries the same value, stamped with the year it was
measured in `ntm_survey_year`. See build_ntm.py for why that is the most the
public data supports.

Three joins here are deliberately *not* exact-year:

  * tariffs, as above;
  * gravity, because CEPII V202211 stops at 2021 while the panel runs to 2023 -
    and the columns that matter most in it (distance, contiguity, language) are
    time-invariant, so the alternative to carrying 2021 forward is throwing away
    every control for the last two years;
  * the Logistics Performance Index, which is a survey run in waves rather than
    an annual series - a year between waves has no value of its own.

Each carries a `*_source_year` column, so an episode on a carried value is
always separable from one measured in its own year. Nothing is filled silently.

Output: analysis/panel_final.csv
"""

import csv
import glob
import gzip
import os
from collections import defaultdict

import build_ntm as bn
import build_ntm6 as bn6
import build_spells as bs

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
TARIFFS = os.path.join(HERE, "data_raw", "tariffs")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "analysis")
MAX_CARRY_FORWARD = 3
# CEPII Gravity V202211 ends at 2021 and the panel now at 2025, so four years of
# controls hang on this. Kept separate from the tariff limit because it answers
# a different question: a tariff four years stale may be simply wrong, whereas
# distance and contiguity do not change at all. `gravity_source_year` keeps the
# carried rows separable, and the time-varying columns in that table (entry_*,
# wto_d, fta_wto) should not be read for 2022-2025.
MAX_GRAVITY_CARRY = 4

# Macro series carried onto every episode. The importer side takes everything
# macro_panel_v2.csv holds - which is where the five downloaded-but-unmerged
# variables (inflation, exchange rate, LPI, population, exports/GDP) finally
# arrive - while the exporter side, being Viet Nam in every row, would add only
# year-level variation and so takes the standard controls alone.
MACRO_RENAME = {"gdp_current_usd": "gdp_usd"}
MACRO_IMPORTER = [
    "gdp_growth_pct", "gdp_current_usd", "gdp_per_capita_usd",
    "exports_pct_gdp", "imports_pct_gdp", "exchange_rate_lcu_per_usd",
    "inflation_pct", "population", "co2_per_capita_t", "renewable_energy_pct",
]
MACRO_EXPORTER = [
    "gdp_growth_pct", "gdp_current_usd", "gdp_per_capita_usd",
    "exchange_rate_lcu_per_usd", "inflation_pct", "population",
]
# The six sub-indices plus the headline. The robustness question in the brief
# asks for a Green LPI, and every published construction of one is a
# transformation of these seven columns - so they are merged raw and combined
# later, once the team fixes which construction it is following.
LPI_COLS = [
    "lpi_overall", "lpi_customs", "lpi_infrastructure", "lpi_intl_shipments",
    "lpi_logistics_competence", "lpi_tracking_tracing", "lpi_timeliness",
]
# TRAINS numeric partner code -> iso3. Only the exporter of this design needs a
# translation; everything else is already stored as iso3.
TRAINS_PARTNER_ISO = {"704": "VNM"}


def eu_mapping():
    path = os.path.join(SEL, "eu_tariff_mapping.csv")
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[(r["iso3"], int(r["year"]))] = r["tariff_reporter"]
    return out


def tariff_files(kind, reporters):
    """Paths of the tariff schedules one importer can read, or all of them."""
    folder = os.path.join(TARIFFS, kind)
    if reporters is None:
        return sorted(glob.glob(os.path.join(folder, "*.csv.gz")))
    out = []
    for rep in sorted(reporters):
        out.extend(glob.glob(os.path.join(folder, f"{rep}_*.csv.gz")))
    return sorted(out)


def load_tariffs(families, reporters=None):
    """(reporter iso, year, family) -> mfn rate, and pref keyed by partner.

    `reporters` limits the load to the schedules one importer can read. Loading
    every schedule at once builds an 11.6-million-entry dictionary which,
    together with the episode list held in memory, took this step past 5 GB -
    enough to bring down a 5.6 GB machine. One importer reads about 120,000
    cells, so the same work done a country at a time fits in a few hundred
    megabytes and the result is identical.
    """
    mfn, pref = {}, {}
    for path in tariff_files("mfn", reporters):
        iso, year = os.path.basename(path)[:-7].rsplit("_", 1)
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rate = r["rate_simple_avg"]
                if rate in (None, ""):
                    continue
                fam = bs.family_of(families, r["nomen"] or "H0", r["product"])
                key = (iso, int(year), fam)
                # several HS6 lines can fold into one family: keep the mean
                prev = mfn.get(key)
                mfn[key] = float(rate) if prev is None else \
                    (prev + float(rate)) / 2
    for path in tariff_files("pref", reporters):
        base = os.path.basename(path)[:-7]
        iso, year, partner = base.rsplit("_", 2)
        # the file name carries the TRAINS numeric partner code; episodes carry
        # an iso3 exporter, so translate before keying or nothing ever matches
        partner_iso = TRAINS_PARTNER_ISO.get(partner, partner)
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rate = r["rate_simple_avg"]
                if rate in (None, ""):
                    continue
                fam = bs.family_of(families, r["nomen"] or "H0", r["product"])
                key = (iso, int(year), partner_iso, fam)
                prev = pref.get(key)
                pref[key] = float(rate) if prev is None else \
                    min(prev, float(rate))
    return mfn, pref


def partner_groups():
    """TRAINS partner codes that stand for a group -> member iso3 codes.

    Preferential schedules are often filed against an agreement (ASEAN, EFTA)
    rather than a single country. Without the membership list those rows cannot
    be matched to an exporter, so they are reported and skipped.
    """
    return {}


def load_macro():
    """macro_panel_v2.csv when it exists: it comes from the World Bank API
    directly rather than through WITS, which never answered to `rou`, so it is
    the only version that has Romania - a real importer in the spell panel that
    otherwise carries no GDP at all. It also runs to 2024."""
    for name in ("macro_panel_v2.csv", "macro_panel.csv"):
        path = os.path.join(OUT, name)
        if os.path.exists(path):
            out = {}
            with open(path, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    out[(r["iso3"], int(r["year"]))] = r
            print(f"  macro: {name}, {len(out):,} country-years")
            return out
    print("  macro_panel.csv missing - run fetch_macro.py")
    return {}


def load_side_panel(name, keys):
    """One of the covariate panels built by build_covariates.py.

    Each is keyed either on (importer, year) or on year alone, and every column
    that is not part of the key is carried onto the episode. Missing files are
    skipped rather than fatal: the trade panel has to stay buildable on a
    machine that has not run the covariate step.
    """
    path = os.path.join(OUT, name)
    if not os.path.exists(path):
        print(f"  {name}: not on disk - skipped")
        return {}, []
    out = {}
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}, []
    cols = [c for c in rows[0] if c not in keys]
    for r in rows:
        out[tuple(r[k] if k != "year" else int(r[k]) for k in keys)] = r
    print(f"  {name}: {len(out):,} rows, {len(cols)} columns")
    return out, cols


def lpi_waves(macro):
    """iso3 -> sorted survey years in which the LPI was actually measured.

    The LPI is a survey, run in 2007, 2010, 2012, 2014, 2016, 2018 and 2023, not
    an annual series - so three quarters of the country-years in the panel have
    no value of their own and never will. The reading applied here is the
    nearest *earlier* wave, which keeps the covariate backward-looking: a
    relationship's 2015 hazard is not allowed to depend on a survey run in 2016.
    Years before the first wave take the earliest wave, since the alternative is
    dropping 2003-2006 outright; `importer_lpi_source_year` says which wave a
    row is on, and equals `year` only for the waves themselves.
    """
    waves = defaultdict(list)
    for (iso, year), row in macro.items():
        if any(row.get(c) not in (None, "") for c in LPI_COLS):
            waves[iso].append(year)
    for iso in waves:
        waves[iso].sort()
    return waves


def lpi_source_year(years, year):
    earlier = [y for y in years if y <= year]
    if earlier:
        return earlier[-1]
    return years[0] if years else None


def side_panel_index(table, keys):
    """(non-year key parts) -> sorted years present, for carry-forward."""
    idx = defaultdict(list)
    if "year" not in keys:
        return idx
    pos = keys.index("year")
    for k in table:
        idx[k[:pos] + k[pos + 1:]].append(k[pos])
    for k in idx:
        idx[k].sort()
    return idx


def load_glpi():
    """(iso3, year) -> the four Green LPI variants built by build_glpi.py.

    All four are carried, not one: they disagree - the ratio form ranks
    countries almost opposite to the PCA form (Spearman -0.46) - so which one a
    robustness check uses is itself a finding, and hard-coding a choice here
    would hide it. See build_glpi.py for the constructions and their sources.
    """
    path = os.path.join(OUT, "glpi.csv")
    if not os.path.exists(path):
        print("  glpi.csv: not on disk - skipped (run build_glpi.py)")
        return {}, []
    out = {}
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = [c for c in rows[0] if c not in ("iso3", "year")]
    for r in rows:
        out[(r["iso3"], int(r["year"]))] = r
    print(f"  glpi.csv: {len(out):,} country-years, {len(cols)} variants")
    return out, cols


def load_complexity():
    """PCI by HS92 four-digit product-year, ECI by country-year."""
    prod, ctry = {}, {}
    p = os.path.join(OUT, "complexity_product.csv")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                prod[(r["hs4"], int(r["year"]))] = r["pci"]
        print(f"  complexity_product.csv: {len(prod):,} product-years")
    else:
        print("  complexity_product.csv: not on disk - skipped")
    p = os.path.join(OUT, "complexity_country.csv")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ctry[(r["iso3"], int(r["year"]))] = r
        print(f"  complexity_country.csv: {len(ctry):,} country-years")
    return prod, ctry


def shard_episodes(ep_path, tmp):
    """Split episodes.csv into one file per importer, streaming.

    Holding all 647,014 episodes in memory as dictionaries is the other half of
    what made this step take 5 GB. Sharding costs one sequential pass and a
    directory of small files, and lets everything downstream work on one
    importer at a time.
    """
    os.makedirs(tmp, exist_ok=True)
    for old in glob.glob(os.path.join(tmp, "*.csv")):
        os.remove(old)
    handles, writers, counts = {}, {}, defaultdict(int)
    with open(ep_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for row in reader:
            imp = row["importer"]
            if imp not in handles:
                h = open(os.path.join(tmp, f"{imp}.csv"), "w", newline="",
                         encoding="utf-8")
                w = csv.DictWriter(h, fieldnames=header)
                w.writeheader()
                handles[imp], writers[imp] = h, w
            writers[imp].writerow(row)
            counts[imp] += 1
    for h in handles.values():
        h.close()
    return sorted(counts), sum(counts.values())


def attach_tariff(e, mfn, pref, eu, stats):
    imp, exp, fam, year = (e["importer"], e["exporter"],
                           e["product_family"], int(e["year"]))
    reporter = eu.get((imp, year), imp)
    rate = source_year = kind = None
    for back in range(0, MAX_CARRY_FORWARD + 1):
        y = year - back
        p = pref.get((reporter, y, exp, fam))
        m = mfn.get((reporter, y, fam))
        if p is not None or m is not None:
            if p is not None and (m is None or p <= m):
                rate, kind = p, "PREF"
            else:
                rate, kind = m, "MFN"
            source_year = y
            break
    if rate is None:
        stats["missing"] += 1
    elif source_year == year:
        stats["matched"] += 1
    else:
        stats["carried"] += 1
    e["tariff_rate"] = "" if rate is None else round(rate, 4)
    e["tariff_type"] = kind or ""
    e["tariff_source_year"] = source_year or ""
    e["tariff_reporter"] = reporter


def attach_macro(e, macro, lpi_years, stats, glpi=None, glpi_cols=()):
    imp, exp, year = e["importer"], e["exporter"], int(e["year"])
    me, mi = macro.get((exp, year), {}), macro.get((imp, year), {})
    for c in MACRO_EXPORTER:
        e["exporter_" + MACRO_RENAME.get(c, c)] = me.get(c, "")
    for c in MACRO_IMPORTER:
        e["importer_" + MACRO_RENAME.get(c, c)] = mi.get(c, "")
    # LPI: the nearest earlier survey wave, stamped so it stays visible
    wave = lpi_source_year(lpi_years.get(imp, []), year)
    wrow = macro.get((imp, wave), {}) if wave else {}
    for c in LPI_COLS:
        e["importer_" + c] = wrow.get(c, "")
    e["importer_lpi_source_year"] = wave or ""
    if wrow:
        stats["lpi"] += 1
    # The Green LPI is built on the LPI, so it exists exactly where the LPI wave
    # does and is read off the same wave - not off the calendar year, which
    # would leave it blank for four years in five.
    grow = glpi.get((imp, wave), {}) if (glpi and wave) else {}
    for c in glpi_cols:
        e["importer_" + c] = grow.get(c, "")
    if grow and any(grow.get(c) not in (None, "") for c in glpi_cols):
        stats["glpi"] += 1


def attach_sides(e, sides, stats):
    for name, keys, table, cols, carry, index, stamp in sides:
        year = int(e["year"])
        k = tuple(e[x] if x != "year" else year for x in keys)
        row = table.get(k)
        src = year if row else None
        if row is None and carry:
            pos = keys.index("year")
            rest = k[:pos] + k[pos + 1:]
            earlier = [y for y in index.get(rest, ()) if y < year]
            if earlier and year - earlier[-1] <= carry:
                src = earlier[-1]
                row = table[k[:pos] + (src,) + k[pos + 1:]]
                stats[name + ":carried"] += 1
        if row:
            stats[name] += 1
        for c in cols:
            e[c] = row.get(c, "") if row else ""
        if stamp:
            e[stamp] = src or ""


def load_us_exempt():
    """product_family -> the two exemption columns, from extract_us_exemptions.py.

    Only the 2025 US reciprocal duty has a product scope of this kind, so the
    columns are written on `importer == "USA"` rows and left blank everywhere
    else. A blank therefore means "no such duty applies to this market", while a
    0 on a USA row means "this duty applies and this family is not exempt" -
    a distinction that matters, because 39% of Viet Nam's export value to the
    United States sits in families that are at least partly exempt.
    """
    path = os.path.join(OUT, "us_exempt_products.csv")
    if not os.path.exists(path):
        print("  us_exempt_products.csv: not on disk - skipped")
        return {}, []
    cols = ["us_recip_exempt_share", "us_recip_exempt_full"]
    table = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            table[r["product_family"]] = [r["us_exempt_share_h6"],
                                          r["us_exempt_full"]]
    print(f"  us_exempt_products.csv: {len(table):,} families, {len(cols)} columns")
    return table, cols


def attach_us_exempt(e, table, cols, stats):
    if not cols:
        return
    if e.get("importer") != "USA":
        for c in cols:
            e[c] = ""
        return
    hit = table.get(e.get("product_family"))
    for c, v in zip(cols, hit or ["0.0000", "0"]):
        e[c] = v
    if hit:
        stats["us_exempt"] += 1


# Regulation (EU) 2023/956 Article 32: the transitional period runs 1 Oct 2023
# to 31 Dec 2025 and carries reporting obligations only. The definitive regime
# starts 1 Jan 2026, one year past this panel - so `cbam_definitive` is zero in
# every row here, and that zero is structural, not measured.
CBAM_START = (2023, 92 / 365)          # 1 October 2023, 92 days of that year


def load_cbam():
    """product_family -> (sector, partial), from fetch_cbam_scope.py."""
    path = os.path.join(OUT, "cbam_products.csv")
    cols = ["cbam_in_scope", "cbam_sector", "cbam_partial",
            "cbam_reporting_share", "cbam_definitive"]
    if not os.path.exists(path):
        print("  cbam_products.csv: not on disk - skipped")
        return {}, []
    table = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            table[r["product_family"]] = (r["cbam_sector"], r["cbam_partial"])
    print(f"  cbam_products.csv: {len(table):,} families, {len(cols)} columns")
    return table, cols


def attach_cbam(e, table, cols, eu, stats):
    """CBAM binds on imports into the EU, so the columns are written on EU
    importers and left blank elsewhere - the same convention the US reciprocal
    columns use. Membership is read year by year from the tariff mapping, which
    is why the United Kingdom stops counting after 2020; that mapping ends in
    2023, so 2024-2025 are held at the 2023 membership."""
    if not cols:
        return
    year = int(e["year"])
    is_eu = eu.get((e.get("importer"), min(year, 2023))) == "EUN"
    if not is_eu:
        for c in cols:
            e[c] = ""
        return
    hit = table.get(e.get("product_family"))
    e["cbam_in_scope"] = int(bool(hit))
    e["cbam_sector"] = hit[0] if hit else ""
    e["cbam_partial"] = hit[1] if hit else 0
    if year > CBAM_START[0]:
        share = 1.0
    elif year == CBAM_START[0]:
        share = round(CBAM_START[1], 4)
    else:
        share = 0.0
    e["cbam_reporting_share"] = share if hit else 0.0
    e["cbam_definitive"] = 0
    if hit:
        stats["cbam"] += 1


def attach_complexity(e, pci, eci, stats, pci_last=None, eci_last=None):
    year = int(e["year"])
    # H0 is HS1992, which is the classification the Atlas publishes PCI in, so
    # the four-digit group is simply the family code's first four digits
    hs4 = e["product_family"].split("_", 1)[-1][:4]
    v = pci.get((hs4, year), "")
    src = year if v != "" else ""
    if v == "" and pci_last:
        # The Atlas stops at 2024 and the panel now runs to 2025. Complexity is
        # a slow-moving property of a product, so the last published year is a
        # far better guess than a blank - but it is stamped, like every other
        # carried value here.
        y = pci_last.get(hs4)
        if y is not None and 0 < year - y <= MAX_GRAVITY_CARRY:
            v, src = pci.get((hs4, y), ""), y
    e["pci"] = v
    e["pci_source_year"] = src
    e["product_hs4"] = hs4
    if v != "":
        stats["pci"] += 1
    row = eci.get((e["importer"], year), {})
    if not row and eci_last:
        y = eci_last.get(e["importer"])
        if y is not None and 0 < year - y <= MAX_GRAVITY_CARRY:
            row = eci.get((e["importer"], y), {})
    e["importer_eci"] = row.get("eci", "")
    e["importer_coi"] = row.get("coi", "")
    e["importer_diversity"] = row.get("diversity", "")
    exp_row = eci.get((e["exporter"], year), {})
    if not exp_row and eci_last:
        y = eci_last.get(e["exporter"])
        if y is not None and 0 < year - y <= MAX_GRAVITY_CARRY:
            exp_row = eci.get((e["exporter"], y), {})
    e["exporter_eci"] = exp_row.get("eci", "")
    if row:
        stats["eci"] += 1


def main():
    print("Rebuilding product families")
    families = bs.build_families()
    macro = load_macro()
    eu = eu_mapping()
    lpi_years = lpi_waves(macro)
    print(f"  LPI survey waves on disk: "
          f"{sorted({y for ys in lpi_years.values() for y in ys})}")

    ep_path = os.path.join(OUT, "episodes.csv")
    if not os.path.exists(ep_path):
        raise SystemExit("episodes.csv missing - run build_spells.py first")

    print("Loading the covariate panels")
    sides = []
    for name, keys in (("fta_vn.csv", ("importer", "year")),
                       ("ttbd_vn.csv", ("importer", "year")),
                       ("gravity_vn.csv", ("importer", "year")),
                       ("us_tariff_vn.csv", ("importer", "year")),
                       ("ntm_ave_vn.csv", ("importer", "year")),
                       ("shocks_annual.csv", ("year",))):
        table, cols = load_side_panel(name, keys)
        if not table:
            continue
        # Only gravity is carried: CEPII stops at 2021 and the geography in it
        # does not move. fta and ttbd are built to the panel's own last year, so
        # a miss there is a real absence and must stay one.
        carry = MAX_GRAVITY_CARRY if name == "gravity_vn.csv" else 0
        sides.append((name, keys, table, cols, carry,
                      side_panel_index(table, keys) if carry else {},
                      "gravity_source_year" if carry else None))
    pci, eci = load_complexity()
    glpi, glpi_cols = load_glpi()
    # last published year per key, for the carry-forward past the Atlas's end
    pci_last, eci_last = {}, {}
    for (hs4, y) in pci:
        if y > pci_last.get(hs4, 0):
            pci_last[hs4] = y
    for (iso, y) in eci:
        if y > eci_last.get(iso, 0):
            eci_last[iso] = y
    us_exempt, us_exempt_cols = load_us_exempt()
    cbam, cbam_cols = load_cbam()
    ntm_lookup, ntm_eu = bn.build()
    # HS6 NTMs come off disk one reporter at a time - the aggregate does not fit
    # in this machine's spare memory. EUN is read once and kept, exactly as the
    # shared EU tariff schedule is.
    ntm6_years = bn6.load_observed()
    ntm6_rep_of = bn6.reporter_of()
    ntm6_cache = {}
    print(f"  ntm6 shards: {len(ntm6_years)} reporters with collection years")

    tmp = os.path.join(OUT, "_merge_shards")
    print("Sharding episodes by importer")
    importers, total = shard_episodes(ep_path, tmp)
    print(f"  episodes: {total:,} across {len(importers)} importers")

    # An importer reading the EU schedule shares it with 26 others, so that one
    # is worth keeping between iterations; everything else is read once.
    reporters_of = {imp: {imp} for imp in importers}
    for (imp, _year), rep in eu.items():
        if imp in reporters_of:
            reporters_of[imp].add(rep)
    shared = defaultdict(int)
    for reps in reporters_of.values():
        for rep in reps:
            shared[rep] += 1
    keep = {rep for rep, n in shared.items() if n > 1}
    cached = {}
    for rep in sorted(keep):
        cached[rep] = load_tariffs(families, {rep})
        print(f"  cached shared schedule {rep}: "
              f"{len(cached[rep][0]):,} MFN cells")

    stats = defaultdict(int)
    path = os.path.join(OUT, "panel_final.csv")
    header = None
    with open(path, "w", newline="", encoding="utf-8") as out:
        writer = None
        for n, imp in enumerate(importers, 1):
            own = reporters_of[imp] - keep
            mfn, pref = load_tariffs(families, own) if own else ({}, {})
            for rep in reporters_of[imp] & keep:
                mfn.update(cached[rep][0])
                pref.update(cached[rep][1])
            ntm6_rep = ntm6_rep_of.get(imp, imp)
            if ntm6_rep in ntm6_cache:
                ntm6_survey, ntm6_inforce = ntm6_cache[ntm6_rep]
            else:
                ntm6_survey, ntm6_inforce = bn6.load_reporter(ntm6_rep)
                # Only the shared EU shard is worth keeping between importers.
                if ntm6_rep == "EUN":
                    ntm6_cache[ntm6_rep] = (ntm6_survey, ntm6_inforce)
            with open(os.path.join(tmp, f"{imp}.csv"), encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            for e in rows:
                attach_tariff(e, mfn, pref, eu, stats)
                attach_macro(e, macro, lpi_years, stats, glpi, glpi_cols)
                attach_sides(e, sides, stats)
                attach_complexity(e, pci, eci, stats, pci_last, eci_last)
                attach_us_exempt(e, us_exempt, us_exempt_cols, stats)
                attach_cbam(e, cbam, cbam_cols, eu, stats)
            stats["ntm"] += bn.attach(rows, ntm_lookup, ntm_eu)
            if bn6.attach(rows, ntm6_survey, ntm6_inforce,
                          ntm6_years.get(ntm6_rep, [])):
                stats["ntm6"] += len(rows) if ntm6_years.get(ntm6_rep) else 0
            if writer is None:
                header = list(rows[0].keys())
                writer = csv.DictWriter(out, fieldnames=header)
                writer.writeheader()
            writer.writerows(rows)
            del mfn, pref, rows
            if n % 20 == 0 or n == len(importers):
                print(f"  {n}/{len(importers)} importers merged", flush=True)

    for f in glob.glob(os.path.join(tmp, "*.csv")):
        os.remove(f)
    os.rmdir(tmp)

    print(f"\n  tariff matched in-year: {stats['matched']:,} "
          f"({100*stats['matched']/total:.1f}%)")
    print(f"  carried forward <= {MAX_CARRY_FORWARD}y: {stats['carried']:,} "
          f"({100*stats['carried']/total:.1f}%)")
    print(f"  no tariff found:        {stats['missing']:,} "
          f"({100*stats['missing']/total:.1f}%)")
    for name, keys, table, cols, carry, index, stamp in sides:
        extra = (f", {stats[name + ':carried']:,} carried forward"
                 if stats[name + ":carried"] else "")
        print(f"  {name}: {stats[name]:,} of {total:,} "
              f"({100*stats[name]/total:.1f}%){extra}")
    print(f"  pci: {stats['pci']:,} ({100*stats['pci']/total:.1f}%) | "
          f"eci: {stats['eci']:,} ({100*stats['eci']/total:.1f}%)")
    if glpi_cols:
        print(f"  GLPI ({len(glpi_cols)} variants): {stats['glpi']:,} "
              f"({100*stats['glpi']/total:.1f}%) - joined on the LPI wave")
    if us_exempt_cols:
        print(f"  US exempt families:     {stats['us_exempt']:,} USA episodes "
              f"on a family with exempt tariff lines")
    print(f"  NTM attached:           {stats['ntm']:,} "
          f"({100*stats['ntm']/total:.1f}%)")
    if cbam_cols:
        print(f"  CBAM in scope:          {stats['cbam']:,} EU episodes on a "
              f"family in Annex I of Regulation (EU) 2023/956")
    print(f"  NTM at HS6 attached:    {stats['ntm6']:,} "
          f"({100*stats['ntm6']/total:.1f}%) - see ntm6_source_year "
          f"and ntm6_observed")
    print(f"  LPI wave attached:      {stats['lpi']:,} "
          f"({100*stats['lpi']/total:.1f}%) - see importer_lpi_source_year")
    print(f"  wrote {path} ({len(header)} columns)")


if __name__ == "__main__":
    main()
