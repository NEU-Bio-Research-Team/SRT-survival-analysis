"""Step 8e: non-tariff measures as a percentage, not a count.

Every other NTM variable in this project counts measures - `ntm6_all_survey`,
`ntm_frequency_ratio`, and so on. A count cannot be compared with a tariff. This
one can: the UNCTAD-GTAP 11 satellite database holds **ad-valorem equivalents**
of border NTMs, the uniform tariff that would have the same trade effect as the
non-tariff measures a market actually applies, estimated by the method of Kee
and Nicita (2022) and made consistent with the GTAP 11 Data Base.

It ships from the same endpoint as the researcher file
(`get-researcher-file/4`), and it is the only NTM source in this project
denominated in tariff points. That is what makes the brief's comparison between
a tariff shock and a non-tariff shock arithmetically possible.

**Two limits, both structural, both stamped in the output.**

1. **One cross-section, 2017.** The README is explicit: AVEs are built from NTM
   data collected 2015-2021 "under the assumption that these measures were in
   effect in 2017", against 2017 trade. The value is therefore repeated across
   every panel year with `ntm_ave_source_year` fixed at 2017 - the same shape
   `gravity_source_year` and `importer_lpi_source_year` already use. It is a
   market characteristic, not a time-varying regressor, and any specification
   with importer fixed effects will absorb it entirely.
2. **46 GTAP sectors, not HS6.** AVEs are estimated at HS6 and then aggregated
   away; recovering the product dimension needs the GTAP concordance, which sits
   behind registration at Purdue and is not on disk. So the sector detail is
   collapsed here rather than joined.

**The collapse is a choice, so both versions are published.** `gtaptrade`, the
2017 trade weights, ships inside the file, and weighting by it answers "what
does the average dollar of Vietnamese exports to this market meet at its
border". The simple mean answers "how NTM-costly is the average sector here",
which gives small sectors equal say. They differ, and neither is obviously
right, so the panel carries both exactly as it carries four Green LPI variants.

    python3 build_ntm_ave.py

Input:  data_raw/ntm/ave_gtap/UNCTADGTAP11_AVEborder.csv
Output: analysis/ntm_ave_vn.csv, keyed (importer, year)
"""

import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "data_raw", "ntm", "ave_gtap",
                   "UNCTADGTAP11_AVEborder.csv")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "analysis")
EXPORTER = "VNM"
SOURCE_YEAR = 2017
FIRST_YEAR, LAST_YEAR = 2003, 2025


def eu_members(year=SOURCE_YEAR):
    """The economies whose border the AVE file scores under the code EUN.

    Read at the AVE's own reference year, which matters: the file's README notes
    that because the data is 2017 levels, its European Union still includes the
    United Kingdom. Taking membership from any later year would silently drop
    the UK's rows.
    """
    path = os.path.join(SEL, "eu_tariff_mapping.csv")
    out = set()
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["tariff_reporter"].strip() == "EUN" and int(r["year"]) == year:
                out.add(r["iso3"].strip())
    return out


def main():
    if not os.path.exists(SRC):
        raise SystemExit(f"{SRC} missing - see DATA_HANDOFF.md 2.6")

    num, den, simple = defaultdict(float), defaultdict(float), defaultdict(list)
    for r in csv.DictReader(open(SRC, encoding="utf-8")):
        if r["regexporter"] != EXPORTER:
            continue
        try:
            ave, w = float(r["AVEgtap"]), float(r["gtaptrade"])
        except ValueError:
            continue
        imp = r["regimporter"]
        num[imp] += ave * w
        den[imp] += w
        simple[imp].append(ave)

    eu = eu_members()
    rows = {}
    for imp in simple:
        wt = num[imp] / den[imp] if den[imp] else None
        sm = sum(simple[imp]) / len(simple[imp])
        targets = eu if imp == "EUN" else {imp}
        for t in targets:
            rows[t] = (wt, sm, len(simple[imp]))

    print(f"{EXPORTER}: {len(simple)} AVE regions -> {len(rows)} panel importers "
          f"({len(eu)} of them EU members reading the EUN row)")
    got = [v[0] for v in rows.values() if v[0] is not None]
    if got:
        print(f"  trade-weighted AVE across markets: min {min(got):.2f}%  "
              f"mean {sum(got)/len(got):.2f}%  max {max(got):.2f}%")
    for m in ("USA", "DEU", "JPN", "KOR", "CHN"):
        if m in rows:
            wt, sm, n = rows[m]
            print(f"  {m}: weighted {wt:.2f}%  simple {sm:.2f}%  ({n} sectors)")

    cols = ["ntm_ave_border_pct", "ntm_ave_border_simple_pct",
            "ntm_ave_n_sectors", "ntm_ave_source_year"]
    path = os.path.join(OUT, "ntm_ave_vn.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["importer", "year"] + cols)
        for imp in sorted(rows):
            wt, sm, n = rows[imp]
            for year in range(FIRST_YEAR, LAST_YEAR + 1):
                w.writerow([imp, year,
                            "" if wt is None else round(wt, 4),
                            round(sm, 4), n, SOURCE_YEAR])
    print(f"  -> {path}  ({len(rows) * (LAST_YEAR - FIRST_YEAR + 1):,} rows, "
          f"{len(cols)} columns)")


if __name__ == "__main__":
    sys.exit(main())
