"""Carry selection/eu_tariff_mapping.csv forward to the panel's last year.

The mapping says which TRAINS schedule each importer reads in each year (EUN
for EU members, the importer itself otherwise). It stopped at 2023 while the
panel runs to 2025, and every reader handled the gap differently: the CBAM and
EVFTA attachers clamped the year to 2023, the tariff attacher did not - so in
2024-2025 DEU, FRA, NLD and the other long-standing members looked up their
own (non-existent) schedules and 70% of EU27 rows lost their tariff, while the
newer members read their own 2023 files instead of EUN.

Extending the file once, here, gives every reader the same answer. Membership
is held at the last listed year: no country joined or left the EU customs
union in 2024-2025. Re-running is harmless.

Usage: python3 scripts/extend_eu_tariff_mapping.py
"""

import csv
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(HERE, "selection", "eu_tariff_mapping.csv")
LAST_YEAR = 2025


def main():
    with open(PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    have = {(r["iso3"], int(r["year"])) for r in rows}
    top = max(int(r["year"]) for r in rows)
    base = [r for r in rows if int(r["year"]) == top]
    added = 0
    for y in range(top + 1, LAST_YEAR + 1):
        for r in base:
            if (r["iso3"], y) not in have:
                rows.append({"iso3": r["iso3"], "year": str(y),
                             "tariff_reporter": r["tariff_reporter"]})
                added += 1
    rows.sort(key=lambda r: (r["iso3"], int(r["year"])))
    with open(PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["iso3", "year", "tariff_reporter"])
        w.writeheader()
        w.writerows(rows)
    print(f"  {PATH}: +{added} rows, membership of {top} carried to {LAST_YEAR}")


if __name__ == "__main__":
    main()
