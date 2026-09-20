"""Flag importer-years whose HS6 detail covers too little of their own total.

A reporter can file its imports from Viet Nam in full at the TOTAL level while
leaving most of it out of the HS6 lines - confidential lines, or a year filed
mostly under unallocated codes. Such a year is not "Viet Nam sold little": its
product detail is simply missing, and reading it as observed kills every
relationship that happened to fall outside the few lines filed. ALB 2014 is
the case that surfaced it - 7 HS6 lines against 164 the year before, 47% of
the reporter's own TOTAL, and 66% of ALB's relationships "died" in 2013.

Rule: coverage = (sum of HS6 lines) / (TOTAL imports from VN, same reporter,
same year) from selection/vn_partner_screen.csv. A year with TOTAL >= USD 1m
and coverage < 0.5 is written to selection/hs6_unobserved_years.csv, which
build_spells.observed_years() treats exactly like a missing file.

The screen only covers 2002-2021, so later years are not tested here.
Persistent partial coverage (CHN from 2015 at 0.73-0.94) shifts value levels
but not deaths, and stays observed.

Usage: python3 scripts/screen_hs6_coverage.py
"""

import csv
import glob
import gzip
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data", "raw", "trade")
SEL = os.path.join(HERE, "selection")
MIN_TOTAL_USD = 1_000_000
MIN_COVERAGE = 0.5


def main():
    hs6, lines = defaultdict(float), defaultdict(int)
    for path in glob.glob(os.path.join(RAW, "*.csv.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["exporter"] == "VNM":
                    k = (r["importer"], int(r["year"]))
                    hs6[k] += float(r["import_value_usd"] or 0)
                    lines[k] += 1
    rows = []
    with open(os.path.join(SEL, "vn_partner_screen.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            k = (r["iso3"], int(r["year"]))
            total = float(r["imports_from_vn_usd"] or 0)
            if k in hs6 and total >= MIN_TOTAL_USD and hs6[k] / total < MIN_COVERAGE:
                rows.append({"importer": k[0], "year": k[1],
                             "hs6_lines": lines[k],
                             "hs6_value_usd": round(hs6[k], 2),
                             "total_value_usd": round(total, 2),
                             "coverage": round(hs6[k] / total, 4),
                             "reason": f"HS6 lines cover < {MIN_COVERAGE:.0%} of the "
                                       f"reporter's TOTAL imports from VNM"})
    rows.sort(key=lambda r: (r["importer"], r["year"]))
    path = os.path.join(SEL, "hs6_unobserved_years.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["importer", "year", "hs6_lines", "hs6_value_usd",
                                          "total_value_usd", "coverage", "reason"])
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path}: {len(rows)} importer-years")
    for r in rows:
        print(f"    {r['importer']} {r['year']}: {r['hs6_lines']} lines, "
              f"coverage {r['coverage']:.2f} of USD {r['total_value_usd'] / 1e6:.1f}m")


if __name__ == "__main__":
    main()
