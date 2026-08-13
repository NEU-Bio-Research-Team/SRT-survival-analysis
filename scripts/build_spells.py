"""Step 6b + 7: turn the raw HS6 panel into a survival dataset.

Three problems have to be solved before a spell means anything:

1. HS revisions. Countries report under whichever HS revision they have
   adopted (H1..H5 all appear inside our window, sometimes in the same year).
   A code that is renumbered between revisions looks like a relationship that
   died and a new one that was born. Every code is therefore mapped into a
   *product family*: the connected component of the graph linking codes across
   revisions through the WITS concordance tables. Families are stable over the
   whole 20 years, which is what a duration needs.

2. Existence threshold. A relationship counts as alive in a year when the
   recorded import value clears USD 10,000 - the same cut-off WITS uses in its
   Trade Outcomes indicators. Below that, values are dominated by noise and
   one-off shipments.

3. Censoring. A spell that is already running in the first year of the window
   is left-censored: its true start is unknown, so it is dropped (per the
   research design). A spell still alive in the last year is right-censored and
   kept with the event flag set to 0.

Outputs, in analysis/:
  spells.csv    - one row per (importer, exporter, family) spell
  episodes.csv  - one row per spell-year, for Cox models with time-varying
                  covariates (tariff, RCA, HHI, shares, growth, GDP)
  products.csv  - the family -> HS6 code mapping actually used

Usage: python3 build_spells.py
"""

import csv
import glob
import gzip
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
RAW_TRADE = os.path.join(HERE, "data_raw", "trade")
CONC = os.path.join(HERE, "data_raw", "concordance")
OUT = os.path.join(HERE, "analysis")

YEAR_MIN, YEAR_MAX = 2002, 2021
THRESHOLD_USD = 10_000
GAP_TOLERANCE = 0          # years below threshold that still break a spell


# --- product families -------------------------------------------------------
class Union:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def build_families():
    """Map (revision, hs6) -> stable family id via the WITS concordances."""
    u = Union()
    pairs = 0
    for rev in ("H1", "H2", "H3", "H4", "H5"):
        folder = os.path.join(CONC, f"{rev}_to_H0")
        files = glob.glob(os.path.join(folder, "*.CSV")) + \
            glob.glob(os.path.join(folder, "*.csv"))
        if not files:
            print(f"  WARNING: no concordance file for {rev}")
            continue
        with open(files[0], encoding="utf-8-sig", errors="replace") as f:
            for row in csv.reader(f):
                if len(row) < 3:
                    continue
                src, dst = row[0].strip(), row[2].strip()
                if len(src) == 6 and len(dst) == 6 and src.isdigit() and dst.isdigit():
                    u.union(("H0", dst), (rev, src))
                    pairs += 1
    print(f"  concordance links: {pairs:,}")
    return u


def family_of(u, rev, code):
    """Family key for a reported code; unmapped codes stand alone."""
    root = u.find((rev, code)) if (rev, code) in u.parent else None
    if root is None:
        # code absent from the concordance (new line, or already H0)
        root = u.find(("H0", code)) if ("H0", code) in u.parent else (rev, code)
    return f"{root[0]}_{root[1]}"


# --- panel ------------------------------------------------------------------
def load_panel(u):
    """(importer, exporter, family, year) -> import value in USD."""
    panel = defaultdict(float)
    files = sorted(glob.glob(os.path.join(RAW_TRADE, "*.csv.gz")))
    if not files:
        sys.exit(f"No trade files in {RAW_TRADE}. Run fetch_trade.py first.")
    codes_seen, codes_mapped = set(), set()
    for n, path in enumerate(files, 1):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    year = int(r["year"])
                    value = float(r["import_value_usd"] or 0)
                except (TypeError, ValueError):
                    continue
                if not (YEAR_MIN <= year <= YEAR_MAX) or not r["exporter"]:
                    continue
                rev, code = r["hs_revision"] or "H0", r["hs6"]
                codes_seen.add((rev, code))
                fam = family_of(u, rev, code)
                if (rev, code) in u.parent:
                    codes_mapped.add((rev, code))
                panel[(r["importer"], r["exporter"], fam, year)] += value
        if n % 50 == 0:
            print(f"  read {n}/{len(files)} files, {len(panel):,} cells",
                  flush=True)
    print(f"  distinct reported codes: {len(codes_seen):,}; "
          f"matched to a family: {len(codes_mapped):,}")
    return panel


# --- spells -----------------------------------------------------------------
def build_spells(panel):
    by_rel = defaultdict(dict)
    for (imp, exp, fam, year), value in panel.items():
        by_rel[(imp, exp, fam)][year] = value

    spells, episodes = [], []
    for (imp, exp, fam), series in by_rel.items():
        alive_years = sorted(y for y, v in series.items() if v >= THRESHOLD_USD)
        if not alive_years:
            continue
        # split into runs of consecutive years
        runs, run = [], [alive_years[0]]
        for y in alive_years[1:]:
            if y - run[-1] <= 1 + GAP_TOLERANCE:
                run.append(y)
            else:
                runs.append(run)
                run = [y]
        runs.append(run)

        for run in runs:
            start, end = run[0], run[-1]
            left_censored = start == YEAR_MIN
            right_censored = end == YEAR_MAX
            if left_censored:
                continue                     # design decision: excluded
            spell_id = f"{imp}_{exp}_{fam}_{start}"
            spells.append({
                "spell_id": spell_id, "importer": imp, "exporter": exp,
                "product_family": fam, "start_year": start, "end_year": end,
                "duration": end - start + 1,
                "event": 0 if right_censored else 1,
                "right_censored": int(right_censored),
                "first_year_value_usd": round(series[start], 2),
                "mean_value_usd": round(
                    sum(series[y] for y in run) / len(run), 2),
            })
            for k, y in enumerate(run, 1):
                episodes.append({
                    "spell_id": spell_id, "importer": imp, "exporter": exp,
                    "product_family": fam, "year": y, "t_start": k - 1,
                    "t_stop": k,
                    "event": 1 if (y == end and not right_censored) else 0,
                    "import_value_usd": round(series[y], 2),
                })
    return spells, episodes


# --- derived covariates at HS6 ---------------------------------------------
def derived(panel):
    """Balassa RCA and Herfindahl indices computed at family level."""
    exp_prod = defaultdict(float)     # exporter, family, year
    exp_tot = defaultdict(float)      # exporter, year
    wld_prod = defaultdict(float)     # family, year
    wld_tot = defaultdict(float)      # year
    exp_part = defaultdict(float)     # exporter, importer, year

    for (imp, exp, fam, year), v in panel.items():
        exp_prod[(exp, fam, year)] += v
        exp_tot[(exp, year)] += v
        wld_prod[(fam, year)] += v
        wld_tot[year] += v
        exp_part[(exp, imp, year)] += v

    rca, prod_share = {}, {}
    for (exp, fam, year), v in exp_prod.items():
        et, wp, wt = exp_tot[(exp, year)], wld_prod[(fam, year)], wld_tot[year]
        if et > 0:
            prod_share[(exp, fam, year)] = 100 * v / et
            if wp > 0 and wt > 0:
                rca[(exp, fam, year)] = (v / et) / (wp / wt)

    partner_share, hhi_market = {}, defaultdict(float)
    for (exp, imp, year), v in exp_part.items():
        et = exp_tot[(exp, year)]
        if et > 0:
            s = v / et
            partner_share[(exp, imp, year)] = 100 * s
            hhi_market[(exp, year)] += s ** 2

    hhi_product = defaultdict(float)
    for (exp, fam, year), v in exp_prod.items():
        et = exp_tot[(exp, year)]
        if et > 0:
            hhi_product[(exp, year)] += (v / et) ** 2

    growth = {}
    for (exp, year), v in exp_tot.items():
        prev = exp_tot.get((exp, year - 1))
        if prev:
            growth[(exp, year)] = 100 * (v - prev) / prev
    world_growth = {}
    for year, v in wld_tot.items():
        prev = wld_tot.get(year - 1)
        if prev:
            world_growth[year] = 100 * (v - prev) / prev

    return {"rca": rca, "product_share": prod_share,
            "partner_share": partner_share, "hhi_market": dict(hhi_market),
            "hhi_product": dict(hhi_product), "country_growth": growth,
            "world_growth": world_growth}


def attach(episodes, d):
    for e in episodes:
        exp, imp, fam, y = (e["exporter"], e["importer"],
                            e["product_family"], e["year"])
        e["rca"] = round(d["rca"].get((exp, fam, y), float("nan")), 4)
        e["product_share_pct"] = round(
            d["product_share"].get((exp, fam, y), float("nan")), 4)
        e["partner_share_pct"] = round(
            d["partner_share"].get((exp, imp, y), float("nan")), 4)
        e["hhi_market"] = round(d["hhi_market"].get((exp, y), float("nan")), 6)
        e["hhi_product"] = round(d["hhi_product"].get((exp, y), float("nan")), 6)
        e["country_growth_pct"] = round(
            d["country_growth"].get((exp, y), float("nan")), 4)
        e["world_growth_pct"] = round(
            d["world_growth"].get(y, float("nan")), 4)
    return episodes


def write(name, rows, cols):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path} ({len(rows):,} rows)")


def main():
    print("Building product families from WITS concordances")
    u = build_families()
    print("Reading trade panel")
    panel = load_panel(u)
    print(f"  panel cells: {len(panel):,}")
    print("Building spells")
    spells, episodes = build_spells(panel)
    print(f"  spells: {len(spells):,}  episodes: {len(episodes):,}")
    print("Computing HS6-level covariates")
    episodes = attach(episodes, derived(panel))

    write("spells.csv", spells,
          ["spell_id", "importer", "exporter", "product_family", "start_year",
           "end_year", "duration", "event", "right_censored",
           "first_year_value_usd", "mean_value_usd"])
    write("episodes.csv", episodes,
          ["spell_id", "importer", "exporter", "product_family", "year",
           "t_start", "t_stop", "event", "import_value_usd", "rca",
           "product_share_pct", "partner_share_pct", "hhi_market",
           "hhi_product", "country_growth_pct", "world_growth_pct"])

    if spells:
        n_cens = sum(s["right_censored"] for s in spells)
        durations = sorted(s["duration"] for s in spells)
        print(f"\nRight-censored: {n_cens:,} of {len(spells):,} "
              f"({100 * n_cens / len(spells):.1f}%)")
        print(f"Median duration: {durations[len(durations) // 2]} years")
        one_year = sum(1 for d in durations if d == 1)
        print(f"One-year spells: {one_year:,} "
              f"({100 * one_year / len(durations):.1f}%)")


if __name__ == "__main__":
    main()
