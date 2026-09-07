"""Step 9c: put the 2025 US reciprocal tariff into the panel's shape.

`data/interim/us_tariffs_2025.csv` has been on disk since 22/08 and had never been
merged - so the covariate the brief calls its central one was, until now, absent
from `panel_final.csv` entirely. This turns that table into two files the merge
can read.

**Rates** are written as a side panel on (importer, year). The panel's `importer`
is the destination market, so a duty the United States imposes on Vietnamese
goods lands on `importer == "USA"` rows and nowhere else. Rows are emitted for
every panel year so that a zero before 2025 reads as "no such duty", not as a
missing value.

**The within-year path.** The brief asks for the 2025 history by month, and the
rate did move four times. The dates below are read out of the orders themselves,
whose texts are archived under `data/raw/us_tariffs_2025/fr_text/` - not
inferred from the schedule, which records only the end state:

| From | Rate | Authority |
|---|---|---|
| 5 Apr 2025  | 10% | EO 14257 s.3(a) first paragraph, the universal floor |
| 9 Apr 2025  | 46% | EO 14257 s.3(a) second paragraph, Annex I |
| 10 Apr 2025 | 10% | EO 14266 s.2 suspends Annex I rates until 9 Jul 2025 |
| 7 Aug 2025  | 20% | EO of 31 Jul 2025, effective 7 days after signature |

EO 14316 extended the suspension from 9 July to 1 August, so the 10% band runs
unbroken from 10 April to 6 August. Nothing after that touches Viet Nam: the
September, November and December orders address China, Switzerland and a list of
agricultural products, and Viet Nam is named in no order after EO 14257.

So four columns describe the year, and the choice between them is the team's:

    us_recip_rate_yearend    the rate in force at 31 Dec 2025 (VNM: 20)
    us_recip_rate_peak       the highest rate ever scheduled  (VNM: 46)
    us_recip_rate_days_wt    the day-weighted mean over calendar 2025
    us_recip_rate_terminated 1 if the peak heading is marked terminated
    us_recip_floor           the universal floor of heading 9903.01.25 (10)
    us_transship_rate        heading 9903.02.01, goods found transshipped (40)

`us_recip_rate_days_wt` is the honest annual summary of a rate that was in force
for part of a year, and it is much smaller than either headline - which is the
point. A model that reads 46, or even 20, onto the whole of 2025 is overstating
the year's exposure by a factor of two or more.

    python3 build_us_tariff_panel.py

Output: data/interim/us_tariff_vn.csv, data/interim/us_tariff_2025_monthly.csv
"""

import csv
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "interim")
SRC = os.path.join(OUT, "us_tariffs_2025.csv")

EXPORTER = "VNM"          # the one exporter this design has
FIRST_YEAR, LAST_YEAR = 2003, 2025
FLOOR_HEADING = "9903.01.25"
TRANSSHIP_HEADING = "9903.02.01"
# (effective date, additional ad valorem rate, the order that set it). Read from
# the archived order texts, not from memory or from the schedule.
TIMELINE = [
    (dt.date(2025, 1, 1), 0.0, "no reciprocal duty"),
    (dt.date(2025, 4, 5), 10.0, "EO 14257 s.3(a), universal floor"),
    (dt.date(2025, 4, 9), 46.0, "EO 14257 s.3(a), Annex I"),
    (dt.date(2025, 4, 10), 10.0, "EO 14266 s.2, Annex I suspended"),
    (dt.date(2025, 8, 7), 20.0, "EO of 31 Jul 2025, Annex I"),
]


def rate_on(day):
    rate, why = 0.0, ""
    for start, r, w in TIMELINE:
        if day >= start:
            rate, why = r, w
    return rate, why


def days_weighted(year):
    day = dt.date(year, 1, 1)
    end = dt.date(year, 12, 31)
    total = n = 0.0
    while day <= end:
        total += rate_on(day)[0]
        n += 1
        day += dt.timedelta(days=1)
    return total / n


def monthly_rows(year):
    out = []
    for m in range(1, 13):
        day = dt.date(year, m, 1)
        nxt = dt.date(year + (m == 12), m % 12 + 1, 1)
        total = n = 0
        bands = []
        while day < nxt:
            r, why = rate_on(day)
            total += r
            n += 1
            if not bands or bands[-1][0] != r:
                bands.append((r, why))
            day += dt.timedelta(days=1)
        out.append((year, m, round(total / n, 4),
                    max(b[0] for b in bands), min(b[0] for b in bands),
                    " -> ".join(b[1] for b in bands)))
    return out


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def main():
    if not os.path.exists(SRC):
        raise SystemExit(f"{SRC} missing - run fetch_us_tariffs_2025.py first")

    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    floor = next((num(r["rate_pct"]) for r in rows
                  if r["hts_heading"] == FLOOR_HEADING), None)
    transship = next((num(r["rate_pct"]) for r in rows
                      if r["hts_heading"] == TRANSSHIP_HEADING), None)

    mine = [r for r in rows if r["iso3"] == EXPORTER and num(r["rate_pct"])]
    if not mine:
        raise SystemExit(f"no {EXPORTER} row carrying a rate in {SRC}")

    live = [r for r in mine if r["terminated"] != "1"]
    peak = max(mine, key=lambda r: num(r["rate_pct"]))
    yearend = max(live, key=lambda r: num(r["rate_pct"])) if live else None

    print(f"{EXPORTER}: " + "; ".join(
        f"{r['hts_heading']} {num(r['rate_pct']):.0f}% from "
        f"{r['effective_from'] or '?'}"
        f"{' (terminated)' if r['terminated'] == '1' else ''}" for r in mine))
    print(f"  universal floor {FLOOR_HEADING}: {floor}%  |  "
          f"transshipment {TRANSSHIP_HEADING}: {transship}%")

    wt = days_weighted(2025)
    print(f"  day-weighted 2025 mean: {wt:.2f}%  "
          f"(year-end {num(yearend['rate_pct']) if yearend else 0:.0f}%, "
          f"peak {num(peak['rate_pct']):.0f}%)")

    mpath = os.path.join(OUT, "us_tariff_2025_monthly.csv")
    with open(mpath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["iso3", "year", "month", "rate_pct_mean", "rate_pct_max",
                    "rate_pct_min", "authority"])
        for row in monthly_rows(2025):
            w.writerow([EXPORTER] + list(row))
    print(f"  -> {mpath}  (12 rows, the within-year path the brief asks for)")

    cols = ["us_recip_rate_yearend", "us_recip_rate_peak",
            "us_recip_rate_days_wt", "us_recip_rate_terminated",
            "us_recip_floor", "us_transship_rate", "us_recip_effective_from"]
    path = os.path.join(OUT, "us_tariff_vn.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["importer", "year"] + cols)
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            if year < 2025:
                w.writerow(["USA", year, 0, 0, 0, 0, 0, 0, ""])
            else:
                w.writerow([
                    "USA", year,
                    num(yearend["rate_pct"]) if yearend else 0,
                    num(peak["rate_pct"]),
                    round(wt, 4),
                    1 if peak["terminated"] == "1" else 0,
                    floor if floor is not None else "",
                    transship if transship is not None else "",
                    (yearend or peak)["effective_from"],
                ])
    print(f"  -> {path}  ({LAST_YEAR - FIRST_YEAR + 1} rows, {len(cols)} columns)")


if __name__ == "__main__":
    sys.exit(main())
