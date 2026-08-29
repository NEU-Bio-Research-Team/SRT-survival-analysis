"""Step 6b + 7: turn the raw HS6 panel into a survival dataset.

The exporter is Viet Nam. A spell is therefore the life of a
(importer j, product family k) relationship for Vietnamese goods, and every
non-Vietnamese row found in the raw files is dropped on the way in - the files
pulled under the earlier multi-exporter design are still readable, they simply
contribute their VNM rows only.

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
RAW_WORLD = os.path.join(HERE, "data_raw", "trade_world")
CONC = os.path.join(HERE, "data_raw", "concordance")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "analysis")

# 2025, extended 23/08 on the team's decision. The reason to stop at 2023 was
# that coverage thins - 147 importers file 2023, 126 file 2024, 89 file 2025 -
# and Viet Nam files neither 2024 nor 2025, so the mirror check ends at 2023.
# What makes the extension safe is observation_windows(): an importer is
# observed only to its own last filing, and a spell running to that year is
# administratively right-censored rather than counted as a death. Thinning
# therefore produces *fewer observed events*, not fake ones. The prize is the
# only year in which the 2025 US tariff shock is observable at all.
YEAR_MIN, YEAR_MAX = 2002, 2025
THRESHOLD_USD = 10_000
GAP_TOLERANCE = 0          # years below threshold that still break a spell
EXPORTER = "VNM"


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
    # H6 (HS2022) matters as much as the rest: from 2022 onward it carries
    # almost the entire panel - 96k of 109k rows in 2022, 111k of 115k in 2023.
    # Without its table every H6 code becomes its own singleton family, so a
    # relationship running since 2002 dies in 2021 and an identical one is born
    # in 2022. That is the exact failure the families exist to prevent.
    # Tables come from wits.worldbank.org/data/public/concordance/
    # Concordance_<REV>_to_H0.zip
    for rev in ("H1", "H2", "H3", "H4", "H5", "H6"):
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
def selected_importers():
    path = os.path.join(SEL, "importers_vn.csv")
    if not os.path.exists(path):
        return None                      # no list yet: take whatever is on disk
    with open(path, encoding="utf-8") as f:
        return {r["iso3"] for r in csv.DictReader(f)}


def complete_importers(folder):
    """Importers whose download has no holes in it.

    A missing importer-year on disk is indistinguishable, once the panel is
    built, from a year in which the relationship did not exist - so an
    unfinished download would manufacture spell deaths and births. The screen
    in selection/vn_partner_screen.csv says which importer-years really do have
    trade with Viet Nam; every one of those must have a file, or the importer
    is held back until its download finishes.

    Returns (usable importers, {importer: missing years}).
    """
    selected = selected_importers()
    screen = os.path.join(SEL, "vn_partner_screen.csv")
    if not os.path.exists(screen):
        print("  no screen file: cannot verify download completeness")
        return selected, {}
    needed = defaultdict(set)
    with open(screen, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            year = int(r["year"])
            if float(r["imports_from_vn_usd"] or 0) > 0 \
                    and YEAR_MIN <= year <= YEAR_MAX \
                    and (selected is None or r["iso3"] in selected):
                needed[r["iso3"]].add(year)
    on_disk = defaultdict(set)
    for path in glob.glob(os.path.join(folder, "*.csv.gz")):
        iso, year = os.path.basename(path)[:-7].rsplit("_", 1)
        on_disk[iso].add(int(year))
    # years the fetcher asked for and found genuinely empty at HS6 - the
    # reporter filed only an aggregate, or only the unclassified 999999 line.
    # Those count as settled, not as holes.
    empty = os.path.join(folder, "_empty_years.csv")
    if os.path.exists(empty):
        with open(empty, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                on_disk[r["importer"]].add(int(r["year"]))
    # The screen only runs to 2021. For anything after it there is no external
    # statement of which importer-years ought to exist, so the record itself is
    # the authority: a year is required when the importer is *still filing
    # later on*. A gap in the middle of a record is a hole; a record that simply
    # ends is an exit, and observation_windows() censors it instead.
    screen_max = max((y for ys in needed.values() for y in ys), default=YEAR_MIN)
    for iso, ys in on_disk.items():
        if selected is not None and iso not in selected:
            continue
        after = {y for y in ys if screen_max < y <= YEAR_MAX}
        if not after:
            continue
        needed[iso] |= set(range(screen_max + 1, max(after) + 1))

    usable, holes = set(), {}
    for iso, years in needed.items():
        gap = sorted(years - on_disk.get(iso, set()))
        if gap:
            holes[iso] = gap
        else:
            usable.add(iso)
    return usable, holes


def read_folder(u, folder, keep_exporter, importers, label):
    """(importer, family, year) -> value in USD, summed over HS6 lines.

    Net weight is summed the same way and returned beside it. The data brief
    asks for quantity as well as value, and the importer filings carry it on
    98.7% of Vietnamese lines - enough to divide into a unit value, which is
    how the trade-duration literature separates a relationship dying because
    the buyer left from one dying because the price collapsed.
    """
    panel = defaultdict(float)
    weights = defaultdict(float)
    files = sorted(glob.glob(os.path.join(folder, "*.csv.gz")))
    if not files:
        return panel, weights, set(), set()
    codes_seen, codes_mapped = set(), set()
    for n, path in enumerate(files, 1):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    year = int(r["year"])
                    value = float(r["import_value_usd"] or 0)
                except (TypeError, ValueError):
                    continue
                if not (YEAR_MIN <= year <= YEAR_MAX):
                    continue
                if r["exporter"] != keep_exporter:
                    continue             # legacy files carry 82 exporters
                if importers and r["importer"] not in importers:
                    continue
                rev, code = r["hs_revision"] or "H0", r["hs6"]
                codes_seen.add((rev, code))
                fam = family_of(u, rev, code)
                if (rev, code) in u.parent:
                    codes_mapped.add((rev, code))
                panel[(r["importer"], fam, year)] += value
                try:
                    kg = float(r.get("net_weight_kg") or 0)
                except (TypeError, ValueError):
                    kg = 0.0
                if kg > 0:
                    weights[(r["importer"], fam, year)] += kg
        if n % 200 == 0:
            print(f"  {label}: read {n}/{len(files)} files, "
                  f"{len(panel):,} cells", flush=True)
    print(f"  {label}: {len(files)} files, {len(panel):,} cells, "
          f"{len(codes_seen):,} distinct codes ({len(codes_mapped):,} mapped), "
          f"weight on {len(weights):,} cells")
    return panel, weights, codes_seen, codes_mapped


def load_panel(u):
    """Viet Nam's side of the panel: (importer, family, year) -> USD."""
    importers, holes = complete_importers(RAW_TRADE)
    if holes:
        worst = sorted(holes.items(), key=lambda kv: -len(kv[1]))[:8]
        print(f"  HELD BACK: {len(holes)} importers have download gaps and are "
              f"excluded so they cannot fake spell deaths")
        for iso, gap in worst:
            span = f"{gap[0]}-{gap[-1]}" if len(gap) > 1 else str(gap[0])
            print(f"    {iso}: {len(gap)} missing year(s) [{span}]")
        if len(holes) > len(worst):
            print(f"    ... and {len(holes) - len(worst)} more")
    panel, weights, _, _ = read_folder(u, RAW_TRADE, EXPORTER, importers,
                                       "VNM imports")
    if not panel:
        sys.exit(f"No Vietnamese rows in {RAW_TRADE}. Run fetch_trade.py first.")
    return panel, weights, importers, holes


def observed_years(folder):
    """Every importer-year the fetcher actually settled.

    Two things count as observed: a file on disk, and an entry in the
    empty-years registry, which means the reporter did file but carried no HS6
    line above zero. Anything else was never seen at all - and the difference
    matters enormously at the trailing edge, where "reported nothing" and "was
    never asked" look identical in the panel but mean opposite things.
    """
    seen = defaultdict(set)
    for path in glob.glob(os.path.join(folder, "*.csv.gz")):
        iso, year = os.path.basename(path)[:-7].rsplit("_", 1)
        seen[iso].add(int(year))
    empty = os.path.join(folder, "_empty_years.csv")
    if os.path.exists(empty):
        with open(empty, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                seen[r["importer"]].add(int(r["year"]))
    return seen


def observation_windows(importers):
    """When each importer's record actually ends, and where it has holes.

    Russia stopped publishing detailed customs data in April 2022 and Belarus
    with it. Their files simply stop. Read naively that is every Vietnamese
    relationship into Russia dying at once in 2022 - while the VN-EAEU
    agreement is in force, so a hazard model would read the FTA as the thing
    that killed them and the sign would flip.

    Nothing about that is specific to Russia. An importer that files nothing at
    all in a year cannot be distinguished from one whose every relationship
    ended that year, and simultaneous mass death is never the right reading. So
    each importer is observed only up to its last settled year, and spells
    running to that year are **administratively right-censored** rather than
    counted as events. This is ordinary staggered exit, and it is the same
    reasoning complete_importers() already applies to interior holes.

    Returns (last_year_by_importer, interior_holes).
    """
    seen = observed_years(RAW_TRADE)
    last, holes = {}, {}
    for iso in sorted(importers or seen):
        ys = {y for y in seen.get(iso, ()) if YEAR_MIN <= y <= YEAR_MAX}
        if not ys:
            continue
        lo, hi = min(ys), max(ys)
        last[iso] = hi
        gap = sorted(set(range(lo, hi + 1)) - ys)
        if gap:
            holes[iso] = gap
    return last, holes


def load_world(u, importers, vn_panel):
    """World denominators, accumulated without ever holding the world panel.

    read_folder() would build one dict entry per (importer, family, year) in
    data_raw/trade_world - on the order of 15 million against the 1.3 million
    the Vietnamese side has. On a 5.6 GB machine that is exactly what killed
    the 19/08 rebuild, silently, halfway through the folder.

    Only three things are ever read off the world panel downstream, and two of
    them are small:

        wld_prod[(family, year)]    world imports of that family   ~100k keys
        wld_tot[year]               world imports that year        ~20 keys
        wld_cell[(imp, fam, year)]  needed only where Viet Nam also sells

    so the folder is streamed and only those are kept. The third is capped by
    the Vietnamese panel rather than by the world's, which is the whole saving.

    A *partially* downloaded world folder is worse than an empty one: the RCA
    denominator would be the sum over whichever importers finished first, so
    the index would mean something different for each country. Either the world
    side covers every importer-year the Vietnamese side has, or none of it is
    used.
    """
    vn_years = defaultdict(set)
    for path in glob.glob(os.path.join(RAW_TRADE, "*.csv.gz")):
        iso, year = os.path.basename(path)[:-7].rsplit("_", 1)
        if iso in importers and YEAR_MIN <= int(year) <= YEAR_MAX:
            vn_years[iso].add(int(year))
    world_years = defaultdict(set)
    for path in glob.glob(os.path.join(RAW_WORLD, "*.csv.gz")):
        iso, year = os.path.basename(path)[:-7].rsplit("_", 1)
        world_years[iso].add(int(year))
    missing = sum(len(ys - world_years.get(iso, set()))
                  for iso, ys in vn_years.items())
    if missing:
        have = sum(len(ys) for ys in world_years.values())
        print(f"  world imports: only {have:,} importer-years on disk, "
              f"{missing:,} short of the Vietnamese panel - NOT USED. RCA and "
              f"world growth fall back to the in-sample total and "
              f"vn_market_share_pct stays empty. Finish "
              f"fetch_trade.py --pass world, then rebuild.")
        return None

    wld_prod = defaultdict(float)
    wld_tot = defaultdict(float)
    wld_cell = defaultdict(float)
    files = sorted(glob.glob(os.path.join(RAW_WORLD, "*.csv.gz")))
    for n, path in enumerate(files, 1):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    year = int(r["year"])
                    value = float(r["import_value_usd"] or 0)
                except (TypeError, ValueError):
                    continue
                if not (YEAR_MIN <= year <= YEAR_MAX):
                    continue
                if r["exporter"] != "WLD":
                    continue
                imp = r["importer"]
                if importers and imp not in importers:
                    continue
                fam = family_of(u, r["hs_revision"] or "H0", r["hs6"])
                wld_prod[(fam, year)] += value
                wld_tot[year] += value
                key = (imp, fam, year)
                if key in vn_panel:          # the cap that keeps this in RAM
                    wld_cell[key] += value
        if n % 400 == 0:
            print(f"  world imports: read {n}/{len(files)} files, "
                  f"{len(wld_cell):,} matched cells", flush=True)
    print(f"  world imports: {len(files)} files, {len(wld_prod):,} family-years,"
          f" {len(wld_cell):,} cells matched to the Vietnamese panel")
    return {"prod": wld_prod, "tot": wld_tot, "cell": wld_cell}


# --- spells -----------------------------------------------------------------
def build_spells(panel, last_year=None, weights=None):
    """last_year maps importer -> the final year that importer was observed.
    A spell running to that year is right-censored: the record ends, the
    relationship need not have. Absent the map every importer ends at YEAR_MAX,
    which is the old behaviour."""
    last_year = last_year or {}
    weights = weights or {}
    by_rel = defaultdict(dict)
    for (imp, fam, year), value in panel.items():
        by_rel[(imp, EXPORTER, fam)][year] = value

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
            right_censored = end >= last_year.get(imp, YEAR_MAX)
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
                kg = weights.get((imp, fam, y), 0.0)
                episodes.append({
                    "spell_id": spell_id, "importer": imp, "exporter": exp,
                    "product_family": fam, "year": y,
                    # The counting-process pair (t_start, t_stop) is what Cox
                    # reads; the three columns beside it restate the same spell
                    # in the form the data brief asks for, so a reader does not
                    # have to join back to spells.csv to see when a
                    # relationship began, when it ended, and whether the ending
                    # was observed at all.
                    "spell_start_year": start, "spell_end_year": end,
                    "right_censored": int(right_censored),
                    "t_start": k - 1, "t_stop": k,
                    "event": 1 if (y == end and not right_censored) else 0,
                    "import_value_usd": round(series[y], 2),
                    "net_weight_kg": round(kg, 2) if kg else "",
                    "unit_value_usd_per_kg": round(series[y] / kg, 4)
                    if kg else "",
                })
    return spells, episodes


# --- derived covariates at HS6 ---------------------------------------------
def derived(panel, world):
    """Balassa RCA, Herfindahl indices and growth rates at family level.

    With one exporter, a growth rate measured on Viet Nam's total exports would
    be one number per year - collinear with any year effect and useless in a
    Cox model. Growth is therefore product-specific, as WITS defines it in the
    Trade Outcomes indicators: `country_growth` is how fast Viet Nam's exports
    of family k grew, `world_growth` how fast world imports of family k grew.

    The world denominators come from the importers' imports from the whole
    world (data_raw/trade_world). Without that folder the same quantities are
    approximated by the in-sample Vietnamese totals, which makes RCA a
    within-Viet-Nam specialisation index rather than a Balassa index - the
    fallback is reported so the difference is never silent.
    """
    vn_prod = defaultdict(float)      # family, year
    vn_tot = defaultdict(float)       # year
    vn_part = defaultdict(float)      # importer, year

    for (imp, fam, year), v in panel.items():
        vn_prod[(fam, year)] += v
        vn_tot[year] += v
        vn_part[(imp, year)] += v

    using_world = world is not None
    if using_world:
        wld_prod, wld_tot, wld_cell = world["prod"], world["tot"], world["cell"]
    else:
        wld_prod, wld_tot, wld_cell = vn_prod, vn_tot, {}

    rca, prod_share = {}, {}
    for (fam, year), v in vn_prod.items():
        vt, wp, wt = vn_tot[year], wld_prod.get((fam, year), 0), wld_tot.get(year, 0)
        if vt > 0:
            prod_share[(fam, year)] = 100 * v / vt
            if wp > 0 and wt > 0:
                rca[(fam, year)] = (v / vt) / (wp / wt)

    partner_share, hhi_market = {}, defaultdict(float)
    for (imp, year), v in vn_part.items():
        vt = vn_tot[year]
        if vt > 0:
            s = v / vt
            partner_share[(imp, year)] = 100 * s
            hhi_market[year] += s ** 2

    hhi_product = defaultdict(float)
    for (fam, year), v in vn_prod.items():
        vt = vn_tot[year]
        if vt > 0:
            hhi_product[year] += (v / vt) ** 2

    def growth_of(series, label):
        """Percent growth, but only off a base that means something.

        A family-year whose total is a few hundred dollars is below the very
        threshold that decides a relationship exists at all, and dividing by it
        produces growth rates in the millions of percent: before this floor,
        1.6% of country_growth exceeded 1,000% and the maximum was 1.4e8. Those
        are not fast-growing products, they are near-zero denominators, and
        they would dominate any regression that used the variable. A base below
        THRESHOLD_USD therefore yields no growth rate rather than a spurious
        one.
        """
        out, suppressed = {}, 0
        for (fam, year), v in series.items():
            prev = series.get((fam, year - 1))
            if not prev:
                continue
            if prev < THRESHOLD_USD:
                suppressed += 1
                continue
            out[(fam, year)] = 100 * (v - prev) / prev
        if suppressed:
            print(f"  {label}: {suppressed:,} family-years have a base below "
                  f"USD {THRESHOLD_USD:,} - growth left empty, not computed")
        return out

    # Viet Nam's share of the importer's own market for that product: the
    # single most direct measure of how exposed the relationship is
    market_share = {}
    if using_world:
        for (imp, fam, year), v in panel.items():
            w = wld_cell.get((imp, fam, year), 0)
            if w > 0:
                market_share[(imp, fam, year)] = 100 * min(v / w, 1.0)

    return {"rca": rca, "product_share": prod_share,
            "partner_share": partner_share, "hhi_market": dict(hhi_market),
            "hhi_product": dict(hhi_product),
            "country_growth": growth_of(vn_prod, "country growth"),
            "world_growth": growth_of(wld_prod, "world growth"),
            "market_share": market_share, "using_world": using_world}


def attach(episodes, d):
    for e in episodes:
        imp, fam, y = e["importer"], e["product_family"], e["year"]
        e["rca"] = round(d["rca"].get((fam, y), float("nan")), 4)
        e["product_share_pct"] = round(
            d["product_share"].get((fam, y), float("nan")), 4)
        e["partner_share_pct"] = round(
            d["partner_share"].get((imp, y), float("nan")), 4)
        e["vn_market_share_pct"] = round(
            d["market_share"].get((imp, fam, y), float("nan")), 4)
        e["hhi_market"] = round(d["hhi_market"].get(y, float("nan")), 6)
        e["hhi_product"] = round(d["hhi_product"].get(y, float("nan")), 6)
        e["country_growth_pct"] = round(
            d["country_growth"].get((fam, y), float("nan")), 4)
        e["world_growth_pct"] = round(
            d["world_growth"].get((fam, y), float("nan")), 4)
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
    panel, weights, importers, holes = load_panel(u)
    print(f"  panel cells: {len(panel):,} from {len(importers)} importers")

    last_year, interior = observation_windows(importers)
    stopped = sorted((iso, y) for iso, y in last_year.items() if y < YEAR_MAX)
    if stopped:
        print(f"  reporting stops early for {len(stopped)} importer(s) - their "
              f"spells are right-censored there, not counted as deaths:")
        for iso, y in stopped:
            print(f"    {iso}: last filed {y}")
    if interior:
        print(f"  NOTE: {len(interior)} importer(s) have an interior gap; "
              f"complete_importers() decides whether they are held back")
        for iso, gap in sorted(interior.items())[:8]:
            print(f"    {iso}: {gap}")

    world = load_world(u, importers, panel)
    print("Building spells")
    spells, episodes = build_spells(panel, last_year, weights)
    print(f"  spells: {len(spells):,}  episodes: {len(episodes):,}")
    print("Computing HS6-level covariates")
    d = derived(panel, world)
    episodes = attach(episodes, d)
    if not d["using_world"]:
        print("  WARNING: RCA / world growth computed without world imports")

    write("spells.csv", spells,
          ["spell_id", "importer", "exporter", "product_family", "start_year",
           "end_year", "duration", "event", "right_censored",
           "first_year_value_usd", "mean_value_usd"])
    write("episodes.csv", episodes,
          ["spell_id", "importer", "exporter", "product_family", "year",
           "spell_start_year", "spell_end_year", "right_censored",
           "t_start", "t_stop", "event", "import_value_usd", "net_weight_kg",
           "unit_value_usd_per_kg", "rca",
           "product_share_pct", "partner_share_pct", "vn_market_share_pct",
           "hhi_market", "hhi_product", "country_growth_pct",
           "world_growth_pct"])

    if spells:
        admin = {iso for iso, y in last_year.items() if y < YEAR_MAX}
        n_admin = sum(1 for s in spells
                      if s["right_censored"] and s["importer"] in admin)
        n_cens = sum(s["right_censored"] for s in spells)
        if n_admin:
            print(f"\nAdministratively censored (reporter stopped filing): "
                  f"{n_admin:,} spells across {len(admin)} importers")
        durations = sorted(s["duration"] for s in spells)
        print(f"\nRight-censored: {n_cens:,} of {len(spells):,} "
              f"({100 * n_cens / len(spells):.1f}%)")
        print(f"Median duration: {durations[len(durations) // 2]} years")
        one_year = sum(1 for d in durations if d == 1)
        print(f"One-year spells: {one_year:,} "
              f"({100 * one_year / len(durations):.1f}%)")


if __name__ == "__main__":
    main()
