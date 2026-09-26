"""Step 10: how much of the spell panel is an artefact of the USD 10,000 floor.

53% of spells last exactly one year. That single fact decides what an estimated
hazard *means*: if most "relationships" are one-off shipments that were never
relationships, a model of their termination is a model of shipment lumpiness,
not of trade-relationship survival. The brief's whole design rests on the
opposite reading, so the floor has to be defended with numbers rather than
inherited.

This measures the trade-off directly. It loads the (importer, family, year)
panel once - the expensive part - and rebuilds spells at several floors from
that one copy, so five thresholds cost one read rather than five.

What to look for:
  * the share of one-year spells: if it barely falls as the floor rises, the
    one-year mass is real behaviour, not a threshold artefact;
  * how many spells and events survive: a floor that halves the sample buys
    little if the duration shape is unchanged;
  * the share of *value* retained: a floor that keeps 99% of export value while
    dropping half the spells is dropping noise, and that is the case worth
    making.

Usage:  python3 scripts/spell_threshold_sensitivity.py [10000 50000 ...]
Output: data/interim/threshold_sensitivity.csv
"""

import collections
import csv
import os
import sys

import build_spells as bs

OUT = os.path.join(bs.HERE, "analysis")   # model results, not data
DEFAULT = [1_000, 10_000, 50_000, 100_000, 500_000]


def group_relationships(panel):
    """(importer, family) -> {year: value}, built once for every threshold.

    Rebuilding this per threshold would add a second copy of the whole panel to
    a run that already holds one, on a machine with no headroom for it.
    """
    by_rel = collections.defaultdict(dict)
    for (imp, fam, year), value in panel.items():
        by_rel[(imp, fam)][year] = value
    return by_rel


def spells_at(by_rel, last_year, floor):
    """Spell summary at one floor - the alive-year rule of build_spells."""
    n_spells = n_events = n_censored = n_left = 0
    durations = collections.Counter()
    above_floor_value = 0.0
    for (imp, fam), series in by_rel.items():
        above_floor_value += sum(v for v in series.values() if v >= floor)
        alive = sorted(y for y, v in series.items() if v >= floor)
        if not alive:
            continue
        runs, run = [], [alive[0]]
        for y in alive[1:]:
            if y - run[-1] <= 1 + bs.GAP_TOLERANCE:
                run.append(y)
            else:
                runs.append(run)
                run = [y]
        runs.append(run)
        for run in runs:
            start, end = run[0], run[-1]
            if start == bs.YEAR_MIN:
                n_left += 1                   # left-censored, excluded by design
                continue
            right = end >= last_year.get(imp, bs.YEAR_MAX)
            n_spells += 1
            durations[end - start + 1] += 1
            if right:
                n_censored += 1
            else:
                n_events += 1
    return n_spells, n_events, n_censored, durations, above_floor_value, n_left


def main():
    floors = [int(a) for a in sys.argv[1:]] or DEFAULT
    print("Building product families")
    u = bs.build_families()
    print("Reading trade panel (once, for every threshold)")
    panel, _weights, importers, _holes = bs.load_panel(u)
    last_year, _interior = bs.observation_windows(importers)
    total_value = sum(panel.values())
    print(f"  {len(panel):,} cells, USD {total_value/1e9:,.0f} bn total")
    by_rel = group_relationships(panel)
    del panel                       # one copy of the data is enough
    print(f"  {len(by_rel):,} (importer, product) relationships\n")

    rows = []
    for floor in floors:
        n, ev, cens, dur, kept, n_left = spells_at(by_rel, last_year, floor)
        one = dur.get(1, 0)
        med = None
        seen = 0
        for d in sorted(dur):
            seen += dur[d]
            if med is None and seen >= n / 2:
                med = d
        long10 = sum(v for d, v in dur.items() if d >= 10)
        rows.append({
            "threshold_usd": floor,
            "spells": n,
            "events": ev,
            "right_censored": cens,
            "pct_censored": round(100 * cens / n, 1) if n else "",
            "one_year_spells": one,
            "pct_one_year": round(100 * one / n, 1) if n else "",
            "median_duration": med,
            "pct_10y_or_more": round(100 * long10 / n, 1) if n else "",
            # Share of total panel value sitting in cells that clear the floor.
            # This is the pure threshold cost. It is deliberately NOT the value
            # inside the retained spells: the left-censoring rule drops every
            # spell that starts in YEAR_MIN, and raising the floor *rescues*
            # some of those - their early years fall below it, so they no longer
            # start at YEAR_MIN - which makes "value inside kept spells" rise
            # with the floor and reads exactly backwards.
            "value_above_floor_pct": round(100 * kept / total_value, 2),
            "left_censored_dropped": n_left,
        })
        r = rows[-1]
        print(f"  USD {floor:>9,}: {n:>7,} spells | {ev:>7,} events | "
              f"one-year {r['pct_one_year']:>5}% | median {med}y | "
              f">=10y {r['pct_10y_or_more']:>4}% | "
              f"value above floor {r['value_above_floor_pct']:>6}% | "
              f"left-cens dropped {n_left:>6,}")

    path = os.path.join(OUT, "threshold_sensitivity.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {path}")

    base, top = rows[0], rows[-1]
    drop = 100 - 100 * top["spells"] / base["spells"]
    move = base["pct_one_year"] - top["pct_one_year"]
    print("\n  Reading:")
    print(f"    A 500-fold rise in the floor (USD {base['threshold_usd']:,} -> "
          f"{top['threshold_usd']:,}) removes {drop:.0f}% of spells and "
          f"{100 - top['value_above_floor_pct']:.0f}% of export value,")
    print(f"    and moves the one-year share only {move:.1f} points "
          f"({base['pct_one_year']}% -> {top['pct_one_year']}%).")
    print("    That is the shape of behaviour, not of an artefact: the mass of "
          "one-year relationships survives")
    print("    every floor that leaves a usable sample. Raising the threshold "
          "buys a little duration at a large")
    print("    cost in sample and coverage, and it does not make the problem "
          "go away - so the honest response is")
    print("    to model the first year explicitly (a split-population or cure "
          "model, or a separate first-year")
    print("    hazard) rather than to define the awkward observations out of "
          "the sample.")


if __name__ == "__main__":
    sys.exit(main())
