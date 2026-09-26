"""Assemble one EU tariff panel: what Vietnamese goods actually pay, 2002-2035.

Four sources, none of which covers the window on its own:

  MFN 2002-2023      TRAINS, already on disk (data/raw/tariffs/mfn/EUN_*.csv.gz)
  MFN 2024-2026      the EU's own CN regulations, parsed by build_eu_mfn_cn.py
                     - TRAINS answers 404 for both years
  GSP 2000-2014      TRAINS group schedules pulled by fetch_eu_gsp.py. Before
                     EVFTA this, not MFN, is what Viet Nam faced
  EVFTA 2020-2035    the staging schedule parsed by build_evfta_staging.py

The applied rate follows the rule an exporter follows - take the lowest rate
you are entitled to:

  year <= 2019   GSP where a schedule exists, otherwise MFN
  year >= 2020   min(EVFTA staged rate, MFN); EVFTA entered into force
                 1 August 2020, so `applied_partial_year` marks 2020

`pref_margin_pp = mfn - applied` is the variable B6 needs, and every row says
which source produced it and whether the value was carried from another year,
so nothing has to be taken on trust.

Output: data/interim/eu_tariff_panel.csv, one row per (product_family, year).

Usage: python3 build_eu_tariff_panel.py
"""

import csv
import gzip
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import build_spells                                          # noqa: E402

ANALYSIS = os.path.join(HERE, "data", "interim")
MFN_DIR = os.path.join(HERE, "data", "raw", "tariffs", "mfn")
PREF_DIR = os.path.join(HERE, "data", "raw", "tariffs", "pref")

YEAR_MIN, YEAR_MAX = 2002, 2035
EIF_YEAR = 2020
GSP_LAST_FILED = 2014          # the EU files no GSP group for 2015-2019
STAGES = {"A": 1, "A+EP": 1, "B3": 4, "B5": 6, "B7": 8, "B10": 11}

# GSP group code actually filed by the EU, per year
GSP_GROUPS = {**{y: "G26" for y in range(2002, 2004)},
              **{y: "G27" for y in range(2004, 2014) if y != 2010},
              2010: "P24", 2014: "A34"}


def read_trains(path, u):
    """family -> mean simple-average rate in a TRAINS schedule file."""
    if not os.path.exists(path):
        return {}
    acc = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rate = float(r["rate_simple_avg"])
            except (TypeError, ValueError):
                continue
            if rate != rate:                       # TRAINS writes NaN
                continue
            fam = build_spells.family_of(u, r["nomen"] or "H0", r["product"])
            acc[fam].append(rate)
    return {k: round(sum(v) / len(v), 4) for k, v in acc.items()}


def read_cn_mfn():
    """(year, family) -> MFN from the EU's own CN regulation."""
    path = os.path.join(ANALYSIS, "eu_mfn_family.csv")
    if not os.path.exists(path):
        print("  note: eu_mfn_family.csv absent - 2024+ MFN will be carried "
              "forward from 2023")
        return {}
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(int(r["year"]), r["product_family"])] = \
                float(r["mfn_simple_avg_pct"])
    return out


def read_evfta():
    path = os.path.join(ANALYSIS, "evfta_staging_family.csv")
    if not os.path.exists(path):
        sys.exit("run build_evfta_staging.py first")
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["base_ad_valorem_pct"] == "":
                continue
            out[r["product_family"]] = {
                "cat": r["staging_cat"],
                "cat_slowest": r["staging_cat_slowest"],
                "mixed": int(r["staging_mixed"]),
                "base": float(r["base_ad_valorem_pct"]),
            }
    return out


def staged(base, cat, year):
    n = STAGES.get(cat)
    if n is None:
        return None
    k = year - (EIF_YEAR - 1)
    return 0.0 if k >= n else round(base * (n - k) / n, 4)


def main():
    u = build_spells.build_families()

    print("Reading TRAINS MFN 2002-2023")
    mfn = {}
    for year in range(2002, 2024):
        d = read_trains(os.path.join(MFN_DIR, f"EUN_{year}.csv.gz"), u)
        if d:
            mfn[year] = d
    print(f"  {len(mfn)} years, "
          f"{sum(len(v) for v in mfn.values()):,} family-years")

    print("Reading the CN regulations for 2024+")
    cn = read_cn_mfn()
    print(f"  {len(cn):,} family-years")

    print("Reading TRAINS GSP group schedules")
    gsp = {}
    for year, group in sorted(GSP_GROUPS.items()):
        d = read_trains(os.path.join(PREF_DIR, f"EUN_{year}_{group}.csv.gz"), u)
        if d:
            gsp[year] = d
    print(f"  {len(gsp)} years, "
          f"{sum(len(v) for v in gsp.values()):,} family-years")

    evfta = read_evfta()
    print(f"EVFTA staging: {len(evfta):,} families")

    families = set(evfta)
    for d in mfn.values():
        families |= set(d)
    for d in gsp.values():
        families |= set(d)
    families |= {f for (_, f) in cn}
    print(f"union: {len(families):,} product families")

    last_mfn_year = max(mfn) if mfn else None
    rows = []
    for fam in sorted(families):
        ev = evfta.get(fam)
        for year in range(YEAR_MIN, YEAR_MAX + 1):
            # ---- MFN, with its provenance ---------------------------------
            m = mfn.get(year, {}).get(fam)
            m_src, m_year = "trains", year
            if m is None and (year, fam) in cn:
                m, m_src = cn[(year, fam)], "eu_cn_regulation"
            if m is None:
                for back in range(year - 1, YEAR_MIN - 1, -1):
                    if back in mfn and fam in mfn[back]:
                        m, m_src, m_year = mfn[back][fam], "carried", back
                        break
                    if (back, fam) in cn:
                        m, m_src, m_year = cn[(back, fam)], "carried", back
                        break
            if m is None:
                continue                    # this family has no EU tariff at all

            # ---- GSP -------------------------------------------------------
            g, g_src, g_year = None, "", ""
            if year <= 2019:
                if year in gsp and fam in gsp[year]:
                    g, g_src, g_year = gsp[year][fam], "trains_group", year
                elif year > GSP_LAST_FILED and GSP_LAST_FILED in gsp \
                        and fam in gsp[GSP_LAST_FILED]:
                    # The EU files no GSP group for 2015-2019, but Regulation
                    # 978/2012 was in force unchanged over those years, so the
                    # 2014 schedule is the right value to carry - flagged.
                    g, g_src, g_year = (gsp[GSP_LAST_FILED][fam],
                                        "carried", GSP_LAST_FILED)

            # ---- EVFTA -----------------------------------------------------
            e = staged(ev["base"], ev["cat"], year) if (ev and year >= EIF_YEAR) \
                else None

            # ---- what was actually paid ------------------------------------
            if year >= EIF_YEAR and e is not None:
                applied, a_src = min(e, m), "evfta"
                if applied == m and m < e:
                    a_src = "mfn"
            elif g is not None:
                applied, a_src = min(g, m), "gsp"
                if applied == m and m < g:
                    a_src = "mfn"
            else:
                applied, a_src = m, "mfn"

            rows.append({
                "product_family": fam,
                "year": year,
                "mfn_pct": m,
                "mfn_source": m_src,
                "mfn_source_year": m_year,
                "gsp_pct": "" if g is None else g,
                "gsp_source": g_src,
                "gsp_source_year": g_year,
                "evfta_pct": "" if e is None else e,
                "staging_cat": ev["cat"] if ev else "",
                "staging_cat_slowest": ev["cat_slowest"] if ev else "",
                "staging_mixed": ev["mixed"] if ev else "",
                "evfta_base_pct": ev["base"] if ev else "",
                "applied_pct": round(applied, 4),
                "applied_source": a_src,
                "applied_partial_year": int(year == EIF_YEAR and a_src == "evfta"),
                "pref_margin_pp": round(m - applied, 4),
                "years_since_evfta": year - EIF_YEAR,
            })

    cols = ["product_family", "year", "mfn_pct", "mfn_source", "mfn_source_year",
            "gsp_pct", "gsp_source", "gsp_source_year", "evfta_pct",
            "staging_cat", "staging_cat_slowest", "staging_mixed",
            "evfta_base_pct", "applied_pct", "applied_source",
            "applied_partial_year", "pref_margin_pp", "years_since_evfta"]
    out = os.path.join(ANALYSIS, "eu_tariff_panel.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out}  ({len(rows):,} rows)")

    # ---- what the panel looks like, year by year --------------------------
    by_year = defaultdict(list)
    for r in rows:
        by_year[r["year"]].append(r)
    print(f"\n{'year':>5}{'families':>10}{'MFN own yr':>12}{'GSP':>8}"
          f"{'EVFTA':>8}{'mean MFN':>10}{'mean applied':>14}{'mean margin':>13}")
    for year in sorted(by_year):
        rs = by_year[year]
        n = len(rs)
        own = sum(1 for r in rs if r["mfn_source"] in ("trains", "eu_cn_regulation"))
        print(f"{year:>5}{n:>10}{100 * own / n:>11.0f}%"
              f"{sum(1 for r in rs if r['gsp_pct'] != ''):>8}"
              f"{sum(1 for r in rs if r['evfta_pct'] != ''):>8}"
              f"{sum(r['mfn_pct'] for r in rs) / n:>10.2f}"
              f"{sum(r['applied_pct'] for r in rs) / n:>14.2f}"
              f"{sum(r['pref_margin_pp'] for r in rs) / n:>13.2f}")


if __name__ == "__main__":
    main()
