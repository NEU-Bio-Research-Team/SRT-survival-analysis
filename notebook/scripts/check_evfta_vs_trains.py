"""Check the parsed EVFTA schedule against what TRAINS reports for 2020-2021.

The staging schedule is a legal text turned into numbers by a PDF parser, and
everything downstream leans on it. TRAINS happens to file the EU's actual
preferential schedule for Viet Nam in exactly two years - 2020 and 2021 - and
nothing else. Those two years are therefore the only independent check that
exists, so they are worth spending: if the parse and the convention are right,
the rate this project derives should land on the rate the EU reported.

Both sides are mapped to the panel's H0 product family first, because the
schedule is written in HS2012 and TRAINS answers in HS2017.

Usage: python3 check_evfta_vs_trains.py
"""

import csv
import gzip
import os
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import build_spells                                          # noqa: E402

ANALYSIS = os.path.join(HERE, "data", "interim")
PREF = os.path.join(HERE, "data", "raw", "tariffs", "pref")


def load_derived(u):
    """family -> {year: derived EVFTA ad-valorem rate}"""
    out = defaultdict(dict)
    path = os.path.join(ANALYSIS, "evfta_tariff_path_hs6.csv")
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            year = int(r["year"])
            if year not in (2020, 2021):
                continue
            fam = build_spells.family_of(u, "H4", r["hs6"])
            out[fam].setdefault(year, []).append(float(r["evfta_rate_pct"]))
    return {fam: {y: sum(v) / len(v) for y, v in d.items()}
            for fam, d in out.items()}


def load_trains(u, year):
    """family -> reported preferential rate"""
    path = os.path.join(PREF, f"EUN_{year}_704.csv.gz")
    if not os.path.exists(path):
        return {}
    acc = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rate = float(r["rate_simple_avg"])
            except (TypeError, ValueError):
                continue
            if rate != rate:                     # TRAINS writes NaN for some lines
                continue
            fam = build_spells.family_of(u, r["nomen"] or "H5", r["product"])
            acc[fam].append(rate)
    return {k: sum(v) / len(v) for k, v in acc.items()}


def main():
    u = build_spells.build_families()
    derived = load_derived(u)
    print(f"derived schedule: {len(derived):,} product families")

    for year in (2020, 2021):
        trains = load_trains(u, year)
        if not trains:
            print(f"\n{year}: no TRAINS preferential file on disk")
            continue
        both = sorted(set(derived) & set(trains))
        diffs = [derived[f][year] - trains[f] for f in both
                 if year in derived[f]]
        if not diffs:
            continue
        exact = sum(1 for d in diffs if abs(d) < 0.01)
        close = sum(1 for d in diffs if abs(d) <= 0.5)
        within2 = sum(1 for d in diffs if abs(d) <= 2.0)
        print(f"\n{year}: TRAINS files {len(trains):,} families, "
              f"{len(diffs):,} overlap with the derived schedule")
        print(f"  identical (<0.01pp): {exact:,} ({100 * exact / len(diffs):.1f}%)")
        print(f"  within 0.5pp:        {close:,} ({100 * close / len(diffs):.1f}%)")
        print(f"  within 2.0pp:        {within2:,} ({100 * within2 / len(diffs):.1f}%)")
        print(f"  mean signed gap:     {statistics.mean(diffs):+.3f}pp")
        print(f"  mean absolute gap:   "
              f"{statistics.mean(abs(d) for d in diffs):.3f}pp")
        worst = sorted(((abs(derived[f][year] - trains[f]), f) for f in both
                        if year in derived[f]), reverse=True)[:8]
        print("  largest gaps (family, derived, TRAINS):")
        for gap, f in worst:
            print(f"    {f}  derived {derived[f][year]:6.2f}  "
                  f"TRAINS {trains[f]:6.2f}  gap {gap:5.2f}")


if __name__ == "__main__":
    main()
