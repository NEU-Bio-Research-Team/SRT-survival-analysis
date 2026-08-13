"""Step 6e: turn the WITS public NTM files into covariates the panel can use.

The public files cannot give what the design asks for - a coverage x year x
product panel - so this script extracts the most that is actually in them and
labels the limits instead of hiding them:

1. Type breakdown. `NTM-Indicators-Measure-Sector.csv` carries an `NTMCode`
   column whose one-letter values are the UNCTAD MAST chapters (A = SPS,
   B = TBT, E = quantity control, ...); four-letter values are individual
   measures nested inside them. Only the one-letter rows are read, because
   those are the chapter aggregates. Keeping the chapters apart is the point:
   Cali et al. (2021) find protectionist chapters cut export survival while
   standard-setting ones do not, so a single pooled NTM variable averages two
   opposite effects into noise.

2. Sector-level "any NTM". Coverage ratios of different chapters overlap (one
   product line can carry SPS and TBT at once), so they cannot be summed. The
   share of lines facing at least one measure comes instead from
   `NTM-Prevalence-Sector.csv`, whose shares split every sector into
   No NTMs / 1 type / 2 types / 3+ types and add to 100%. `100 - No NTMs` is
   therefore a genuine sector frequency ratio, and `3+ types` is a usable
   intensity measure.

3. Time. None of these files has a usable year dimension, so the values are a
   single snapshot per country. `analysis/ntm_country.csv` does record which
   year each country was surveyed (one year per country, 2012-2017), and that
   year is carried into the panel as `ntm_survey_year` so every regression can
   state exactly what it is conditioning on. This is the time-invariant
   fallback the literature accepts when NTM data is too thin for a panel.

4. The EU. NTM measures are filed once under `EUN`, exactly like the common
   external tariff, so EU members read the EUN record through the same
   `selection/eu_tariff_mapping.csv` the tariff merge uses.

Outputs, in analysis/:
  ntm_by_type.csv  - importer x sector x MAST chapter, coverage and frequency
  ntm_sector.csv   - importer x sector, merge-ready row used by merge_panel.py

Usage: python3 build_ntm.py
"""

import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
RAW = os.path.join(HERE, "data_raw", "ntm")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "analysis")

# WITS product groups, as HS2 chapter ranges. Same grouping the NTM files and
# the tradestats product list use, so the sector label matches on both sides.
SECTOR_RANGES = [
    ((1, 5), "Animal"),
    ((6, 15), "Vegetable"),
    ((16, 24), "Food Products"),
    ((25, 26), "Minerals"),
    ((27, 27), "Fuels"),
    ((28, 38), "Chemicals"),
    ((39, 40), "Plastic or Rubber"),
    ((41, 43), "Hides and Skins"),
    ((44, 49), "Wood"),
    ((50, 63), "Textiles and Clothing"),
    ((64, 67), "Footwear"),
    ((68, 71), "Stone and Glass"),
    ((72, 83), "Metals"),
    ((84, 85), "Mach and Elec"),
    ((86, 89), "Transportation"),
    ((90, 99), "Miscellaneous"),
]

# UNCTAD MAST chapters as they appear in the file. A-C are the technical /
# standard-setting measures, D-O the non-technical ones that the literature
# treats as protectionist, P applies to the reporter's own exports and is kept
# out of the import-side aggregates.
CHAPTERS = {
    "A": ("sps", "technical"),
    "B": ("tbt", "technical"),
    "C": ("inspection", "technical"),
    "D": ("price_control", "nontechnical"),
    "E": ("quantity", "nontechnical"),
    "F": ("para_tariff", "nontechnical"),
    "G": ("finance", "nontechnical"),
    "H": ("competition", "nontechnical"),
    "I": ("investment", "nontechnical"),
    "J": ("distribution", "nontechnical"),
    "L": ("subsidies", "nontechnical"),
    "N": ("intellectual_property", "nontechnical"),
    "O": ("rules_of_origin", "nontechnical"),
    "P": ("export_related", "export"),
}

# Prevalence uses a different label for the country total than the measures
# file; both are normalised away so only real sectors survive.
SECTOR_ALIASES = {"All Import Products": None, "All sectors": None}

PANEL_COLS = [
    "ntm_reporter", "ntm_survey_year", "ntm_sector",
    "ntm_coverage_ratio", "ntm_frequency_ratio",
    "ntm_sector_freq_any", "ntm_sector_share_3plus",
    "ntm_sps_coverage", "ntm_tbt_coverage", "ntm_quantity_coverage",
    "ntm_technical_coverage", "ntm_nontechnical_coverage", "ntm_n_types",
]


def sector_of_chapter(hs2):
    for (lo, hi), name in SECTOR_RANGES:
        if lo <= hs2 <= hi:
            return name
    return None


def sector_of_family(fam):
    """`H0_010121` -> the WITS sector its HS2 chapter falls in."""
    code = fam.split("_", 1)[-1]
    if len(code) < 2 or not code[:2].isdigit():
        return None
    return sector_of_chapter(int(code[:2]))


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read(name):
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        raise SystemExit(f"{path} missing - run fetch_macro.py first")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in list(r):
            if k != k.strip():
                r[k.strip()] = r.pop(k)
    return rows


def eu_mapping():
    """iso3 -> EUN, for the years the country files under the EU schedule.

    NTM records carry no year, so a member is treated as reading the EUN
    record whenever it did so for tariffs at any point in the window. The UK
    left in 2021, i.e. one year of the 20, which is not worth a separate NTM
    record that does not exist anyway.
    """
    path = os.path.join(SEL, "eu_tariff_mapping.csv")
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["tariff_reporter"] == "EUN":
                    out[r["iso3"]] = "EUN"
    return out


def country_snapshot():
    """iso3 -> import-side coverage/frequency plus the year it was surveyed."""
    path = os.path.join(OUT, "ntm_country.csv")
    if not os.path.exists(path):
        raise SystemExit(f"{path} missing - run fetch_macro.py first")
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["trade_flow"] != "Import":
                continue
            out[r["iso3"]] = {
                "survey_year": r["survey_year"],
                "coverage": _num(r["ntm_coverage_ratio"]),
                "frequency": _num(r["ntm_frequency_ratio"]),
            }
    return out


def by_type():
    """(iso, sector, chapter) -> coverage / frequency, chapter rows only."""
    out = {}
    for r in _read("NTM-Indicators-Measure-Sector.csv"):
        code = (r.get("NTMCode") or "").strip()
        if len(code) != 1 or code not in CHAPTERS:
            continue                      # four-letter rows are sub-measures
        sector = (r.get("Sector") or "").strip()
        sector = SECTOR_ALIASES.get(sector, sector)
        if not sector:
            continue
        out[(r["ReporterIS03"], sector, code)] = {
            "coverage": _num(r.get("NTM Coverage ratio")),
            "frequency": _num(r.get("NTM Frequency ratio")),
            "affected": _num(r.get("NTM affected product - count")),
            "total": _num(r.get("Traded products - total")),
        }
    return out


def prevalence():
    """(iso, sector) -> share of lines with >=1 NTM, and with 3+ types."""
    buckets = defaultdict(dict)
    for r in _read("NTM-Prevalence-Sector.csv"):
        sector = (r.get("Sector") or "").strip()
        sector = SECTOR_ALIASES.get(sector, sector)
        if not sector:
            continue
        label = (r.get("NTM Type Count") or "").strip()
        buckets[(r["ReporterIS03"], sector)][label] = _num(r.get("Share %"))

    # The four buckets add to 100% within a sector, so a bucket that is absent
    # is an empty one, not a missing value: no "No NTMs" row means every traded
    # line carries at least one measure.
    out = {}
    for key, b in buckets.items():
        none = b.get("No NTMs") or 0.0
        out[key] = {
            "freq_any": round(100 - none, 4),
            "share_3plus": b.get("3+ types") or 0.0,
        }
    return out


def build():
    """(importer iso, sector) -> the NTM columns attached to every episode."""
    eu = eu_mapping()
    snap = country_snapshot()
    types = by_type()
    prev = prevalence()

    reporters = {iso for iso, _, _ in types} | set(snap)
    sectors = [name for _, name in SECTOR_RANGES]

    lookup = {}
    for rep in reporters:
        for sector in sectors:
            chapters = {c: types[(rep, sector, c)] for c in CHAPTERS
                        if (rep, sector, c) in types}
            if not chapters and (rep, sector) not in prev:
                continue

            # A chapter absent from a country-sector that *is* in the survey
            # means no measure of that type was recorded, i.e. zero coverage -
            # unlike a country absent from the survey altogether, which stays
            # blank. This is the one place Carrere's (2011) "missing or none?"
            # ambiguity is resolved, and it is resolved the way UNCTAD reads
            # its own files.
            def cov(code):
                cell = chapters.get(code)
                return 0.0 if cell is None else cell["coverage"]

            def group_max(kind):
                vals = [v["coverage"] for c, v in chapters.items()
                        if CHAPTERS[c][1] == kind and v["coverage"] is not None]
                return max(vals) if vals else 0.0

            p = prev.get((rep, sector), {})
            s = snap.get(rep, {})
            lookup[(rep, sector)] = {
                "ntm_reporter": rep,
                "ntm_survey_year": s.get("survey_year", ""),
                "ntm_sector": sector,
                "ntm_coverage_ratio": s.get("coverage"),
                "ntm_frequency_ratio": s.get("frequency"),
                "ntm_sector_freq_any": p.get("freq_any"),
                "ntm_sector_share_3plus": p.get("share_3plus"),
                "ntm_sps_coverage": cov("A"),
                "ntm_tbt_coverage": cov("B"),
                "ntm_quantity_coverage": cov("E"),
                # coverage ratios of different chapters overlap, so the union
                # is unknown; the largest chapter is a lower bound on it
                "ntm_technical_coverage": group_max("technical"),
                "ntm_nontechnical_coverage": group_max("nontechnical"),
                "ntm_n_types": sum(
                    1 for c, v in chapters.items()
                    if CHAPTERS[c][1] != "export"
                    and (v["coverage"] or 0) > 0),
            }
    return lookup, eu


def attach(rows, lookup, eu, importer_key="importer",
           family_key="product_family"):
    """Write the NTM columns onto episode rows. Returns a match count."""
    matched = 0
    for e in rows:
        rep = eu.get(e[importer_key], e[importer_key])
        sector = sector_of_family(e[family_key])
        cell = lookup.get((rep, sector)) if sector else None
        if cell is None:
            for col in PANEL_COLS:
                e[col] = ""
            e["ntm_sector"] = sector or ""
        else:
            for col in PANEL_COLS:
                v = cell.get(col)
                e[col] = "" if v is None else v
            matched += 1
    return matched


def write(name, rows, cols):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path} ({len(rows):,} rows)")


def main():
    print("Reading WITS NTM files")
    types = by_type()
    lookup, eu = build()

    rows = []
    for (rep, sector, code), v in sorted(types.items()):
        label, group = CHAPTERS[code]
        rows.append({
            "reporter": rep, "sector": sector, "ntm_chapter": code,
            "ntm_label": label, "ntm_group": group,
            "coverage_ratio": v["coverage"], "frequency_ratio": v["frequency"],
            "products_affected": v["affected"], "products_total": v["total"],
        })
    write("ntm_by_type.csv", rows,
          ["reporter", "sector", "ntm_chapter", "ntm_label", "ntm_group",
           "coverage_ratio", "frequency_ratio", "products_affected",
           "products_total"])
    write("ntm_sector.csv", sorted(lookup.values(),
                                   key=lambda r: (r["ntm_reporter"],
                                                  r["ntm_sector"])),
          PANEL_COLS)

    # coverage report: which of the selected importers can actually be served
    with open(os.path.join(SEL, "importers_selected.csv"),
              encoding="utf-8") as f:
        importers = [r["iso3"] for r in csv.DictReader(f)]
    served, via_eu, missing = [], [], []
    for iso in importers:
        rep = eu.get(iso, iso)
        if any((rep, s) in lookup for _, s in SECTOR_RANGES):
            (via_eu if rep != iso else served).append(iso)
        else:
            missing.append(iso)
    total = len(served) + len(via_eu)
    print(f"\n  importers with NTM data: {total}/{len(importers)} "
          f"({len(served)} direct + {len(via_eu)} through EUN)")
    print(f"  via EUN: {', '.join(sorted(via_eu))}")
    print(f"  no NTM record ({len(missing)}): {', '.join(sorted(missing))}")
    print("\n  NOTE: one snapshot year per country (2012-2017), sector level, "
          "no HS6. Time-invariant by construction.")


if __name__ == "__main__":
    main()
