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

Output: analysis/panel_final.csv
"""

import csv
import glob
import gzip
import os
from collections import defaultdict

import build_ntm as bn
import build_spells as bs

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
TARIFFS = os.path.join(HERE, "data_raw", "tariffs")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "analysis")
MAX_CARRY_FORWARD = 3
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


def load_tariffs(families):
    """(reporter iso, year, family) -> mfn rate, and pref keyed by partner."""
    mfn, pref = {}, {}
    for path in glob.glob(os.path.join(TARIFFS, "mfn", "*.csv.gz")):
        iso, year = os.path.basename(path)[:-7].rsplit("_", 1)
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                fam = bs.family_of(families, r["nomen"] or "H0", r["product"])
                key = (iso, int(year), fam)
                rate = r["rate_simple_avg"]
                if rate not in (None, ""):
                    # several HS6 lines can fold into one family: keep the mean
                    prev = mfn.get(key)
                    mfn[key] = float(rate) if prev is None else \
                        (prev + float(rate)) / 2
    for path in glob.glob(os.path.join(TARIFFS, "pref", "*.csv.gz")):
        base = os.path.basename(path)[:-7]
        iso, year, partner = base.rsplit("_", 2)
        # the file name carries the TRAINS numeric partner code; episodes carry
        # an iso3 exporter, so translate before keying or nothing ever matches
        partner_iso = TRAINS_PARTNER_ISO.get(partner, partner)
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                fam = bs.family_of(families, r["nomen"] or "H0", r["product"])
                key = (iso, int(year), partner_iso, fam)
                rate = r["rate_simple_avg"]
                if rate not in (None, ""):
                    prev = pref.get(key)
                    pref[key] = float(rate) if prev is None else \
                        min(prev, float(rate))
    print(f"  MFN cells: {len(mfn):,} | PREF cells: {len(pref):,}")
    return mfn, pref


def partner_groups():
    """TRAINS partner codes that stand for a group -> member iso3 codes.

    Preferential schedules are often filed against an agreement (ASEAN, EFTA)
    rather than a single country. Without the membership list those rows cannot
    be matched to an exporter, so they are reported and skipped.
    """
    return {}


def load_macro():
    path = os.path.join(OUT, "macro_panel.csv")
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[(r["iso3"], int(r["year"]))] = r
    else:
        print("  macro_panel.csv missing - run fetch_macro.py")
    return out


def main():
    print("Rebuilding product families")
    families = bs.build_families()
    print("Loading tariffs")
    mfn, pref = load_tariffs(families)
    macro = load_macro()
    eu = eu_mapping()

    ep_path = os.path.join(OUT, "episodes.csv")
    if not os.path.exists(ep_path):
        raise SystemExit("episodes.csv missing - run build_spells.py first")
    with open(ep_path, encoding="utf-8") as f:
        episodes = list(csv.DictReader(f))
    print(f"  episodes: {len(episodes):,}")

    matched = carried = missing = 0
    for e in episodes:
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
            missing += 1
        elif source_year == year:
            matched += 1
        else:
            carried += 1

        e["tariff_rate"] = "" if rate is None else round(rate, 4)
        e["tariff_type"] = kind or ""
        e["tariff_source_year"] = source_year or ""
        e["tariff_reporter"] = reporter

        me, mi = macro.get((exp, year), {}), macro.get((imp, year), {})
        e["exporter_gdp_growth_pct"] = me.get("gdp_growth_pct", "")
        e["exporter_gdp_usd"] = me.get("gdp_current_usd", "")
        e["importer_gdp_growth_pct"] = mi.get("gdp_growth_pct", "")
        e["importer_gdp_usd"] = mi.get("gdp_current_usd", "")

    print("Attaching NTM covariates")
    ntm_lookup, ntm_eu = bn.build()
    ntm_matched = bn.attach(episodes, ntm_lookup, ntm_eu)

    cols = list(episodes[0].keys())
    path = os.path.join(OUT, "panel_final.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(episodes)

    total = len(episodes)
    print(f"\n  tariff matched in-year: {matched:,} ({100*matched/total:.1f}%)")
    print(f"  carried forward <= {MAX_CARRY_FORWARD}y: {carried:,} "
          f"({100*carried/total:.1f}%)")
    print(f"  no tariff found:        {missing:,} ({100*missing/total:.1f}%)")
    print(f"  NTM attached:           {ntm_matched:,} "
          f"({100*ntm_matched/total:.1f}%)")
    print(f"  wrote {path}")


if __name__ == "__main__":
    main()
