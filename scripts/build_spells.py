"""Step 6b + 7: turn the raw HS6 panel into a survival dataset.

The exporter is Viet Nam. A spell is therefore the life of a
(importer j, product family k) relationship for Vietnamese goods, and every
non-Vietnamese row found in the raw files is dropped on the way in - the files
pulled under the earlier multi-exporter design are still readable, they simply
contribute their VNM rows only.

Three problems have to be solved before a spell means anything:

1. HS revisions. Countries report under whichever HS revision they have
   adopted (H1..H6 all appear inside our window). A code that is renumbered
   between revisions looks like a relationship that died and a new one that was
   born. Every code is therefore mapped into a *product family* - see
   families.py, which owns that definition for every script in the pipeline.

2. Existence threshold. A relationship counts as alive in a year when the
   recorded import value clears USD 10,000 - the same cut-off WITS uses in its
   Trade Outcomes indicators. Below that, values are dominated by noise and
   one-off shipments.

3. Censoring. A death is only an event when it was *seen*: with the gap rule a
   spell ending in year E is dead only if E+1 .. E+1+GAP_TOLERANCE were all
   published at HS6 by that importer and the family could be reported in each
   of them (confirm_end). Anything else - the end of the record, an unpublished
   or aggregate-only year, a revision the family cannot be expressed in - is
   right-censoring, and `censor_reason` says which. Starts are read the same way
   (confirm_start): a spell whose preceding years were not all observed, or
   that begins where an HS revision switch dumps another family's goods, has an
   unknown true start and is flagged `left_trunc` with `start_reason`.

Outputs, in data/interim/:
  spells.csv    - one row per (importer, exporter, family) spell
  episodes.csv  - one row per spell-year, for Cox models with time-varying
                  covariates (tariff, RCA, HHI, shares, growth, GDP)
  family_map.csv, family_members.csv, family_merges.csv - the product key
  importer_year_revision.csv - the HS revision each importer filed each year

Usage: python3 build_spells.py
"""

import csv
import glob
import gzip
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
RAW_TRADE = os.path.join(HERE, "data", "raw", "trade")
RAW_WORLD = os.path.join(HERE, "data", "raw", "trade_world")
CONC = os.path.join(HERE, "data", "raw", "concordance")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "data", "interim")

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
# B0 (Stage1_Research_Framework.md) chốt quy tắc gap 1 năm, theo chuẩn
# Besedes-Prusa: một năm tụt dưới ngưỡng rồi quay lại KHÔNG phải là một cái
# chết cộng một lần tái sinh. Đặt 0 làm vỡ quan hệ liên tục thành nhiều spell
# ngắn - đo được: 0 -> 21,3% chết/năm, 1 -> 15,1%, 2 -> 12,1% trên EU27.
GAP_TOLERANCE = 1          # years below threshold that still break a spell
EXPORTER = "VNM"


# --- product families -------------------------------------------------------
# Defined once, in families.py. Re-exported here because merge_panel.py and the
# EU/EVFTA builders reach them as build_spells.build_families / family_of.
from families import (Union, build_families, family_of,  # noqa: E402,F401
                      families_in_revision, write_family_map)


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


def read_folder(u, folder, keep_exporter, importers, label, revisions=None):
    """(importer, family, year) -> value in USD, summed over HS6 lines.

    Net weight is summed the same way and returned beside it. The data brief
    asks for quantity as well as value, and the importer filings carry it on
    98.7% of Vietnamese lines - enough to divide into a unit value, which is
    how the trade-duration literature separates a relationship dying because
    the buyer left from one dying because the price collapsed.

    `revisions`, when given, is filled with (importer, year) -> {revision:
    value}: the HS revision each filing used, which build_spells() needs to
    tell a death from a family the new revision cannot express.
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
                if revisions is not None:
                    revisions.setdefault((r["importer"], year),
                                         defaultdict(float))[rev] += value
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


def load_panel(u, revisions=None):
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
                                       "VNM imports", revisions)
    if not panel:
        sys.exit(f"No Vietnamese rows in {RAW_TRADE}. Run fetch_trade.py first.")
    return panel, weights, importers, holes


def observed_years(folder):
    """Every importer-year observed *at HS6*: a file on disk, nothing else.

    The empty-years registry is deliberately not counted. Its three reasons -
    "reporter filed no HS6 detail", "only the unclassified 999999 aggregate",
    and "no HS6 rows in a batch that returned data for other years" - all say
    the product detail is missing, not that Viet Nam sold nothing. v1 counted
    them as observed and read every relationship alive before them as dead:
    ARE's 1,064 relationships in 2023 (2024 not yet published), all 455 in 2008
    (2009 aggregate-only), and so on for 31 importer-years. A year that was
    never seen at HS6 can confirm neither a death nor a birth.
    """
    seen = defaultdict(set)
    for path in glob.glob(os.path.join(folder, "*.csv.gz")):
        iso, year = os.path.basename(path)[:-7].rsplit("_", 1)
        seen[iso].add(int(year))
    # Files whose HS6 lines cover under half the reporter's own TOTAL are
    # missing their product detail just as surely (screen_hs6_coverage.py).
    partial = os.path.join(SEL, "hs6_unobserved_years.csv")
    if os.path.exists(partial):
        with open(partial, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                seen[r["importer"]].discard(int(r["year"]))
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
    data/raw/trade_world - on the order of 15 million against the 1.3 million
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
def build_spells(panel, last_year=None, weights=None, observed=None,
                 revision_of=None, fam_in_rev=None, receivers=None):
    """last_year maps importer -> the final year that importer was observed.

    The optional maps turn on the v2 reading of both ends of a spell:
      observed     importer -> years published at HS6 (observed_years)
      revision_of  (importer, year) -> HS revision of that filing
      fam_in_rev   revision -> families expressible in it (families.py)
      receivers    revision -> families that absorbed an unmerged orphan
    Without them the old rule applies: only the last year censors."""
    last_year = last_year or {}
    weights = weights or {}
    revision_of = revision_of or {}
    fam_in_rev = fam_in_rev or {}
    receivers = receivers or {}

    def end_reason(imp, fam, end):
        """Why a spell's end is not a confirmed death ("" when it is one).

        With GAP_TOLERANCE = g a relationship absent for g years and then back
        is one spell, so a death at `end` needs end+1 .. end+1+g to be seen
        empty. Each of those years must lie inside the record, be published at
        HS6, and be a revision the family can be reported in at all."""
        T = last_year.get(imp, YEAR_MAX)
        if end >= T:
            return "window_end"
        need = range(end + 1, end + 2 + GAP_TOLERANCE)
        seen = observed.get(imp, set()) if observed is not None else None
        for y in need:
            if y > T:
                return "window_edge"
            if seen is not None and y not in seen:
                return "unobserved_year"
        for y in need:
            r = revision_of.get((imp, y))
            if r and fam_in_rev and fam not in fam_in_rev.get(r, ()):
                return "hs_revision"
        return ""

    def start_reason(imp, fam, start):
        """Why a spell's start is not a confirmed birth ("" when it is one).
        The mirror image of end_reason(), plus the receiving side of an
        orphan: goods an unmerged orphan hands over at a revision switch look
        like a new relationship in the family that absorbs them."""
        if start <= YEAR_MIN:
            return "window_start"
        if observed is None:
            return ""
        need = range(start - 1 - GAP_TOLERANCE, start)
        seen = observed.get(imp, set())
        for y in need:
            if y < YEAR_MIN:
                return "window_start"
            if y not in seen:
                return "unobserved_year"
        for y in need:
            r = revision_of.get((imp, y))
            if r and fam_in_rev and fam not in fam_in_rev.get(r, ()):
                return "hs_revision"
        r0, r1 = revision_of.get((imp, start - 1)), revision_of.get((imp, start))
        if r0 and r1 and r0 != r1 and fam in receivers.get(r1, ()):
            return "hs_revision_receiver"
        return ""

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
            # A spell whose true start is unknown is kept and flagged rather
            # than dropped (B0): the window of analysis is 2012-2024 while the
            # data reach back to 2002, so most ages are *observed*. What makes
            # a start unknown is spelled out in start_reason().
            s_reason = start_reason(imp, fam, start)
            c_reason = end_reason(imp, fam, end)
            left_trunc = bool(s_reason)
            right_censored = bool(c_reason)
            spell_id = f"{imp}_{exp}_{fam}_{start}"
            # With GAP_TOLERANCE > 0 a run spans calendar years that sit below
            # the threshold. They belong to the spell - that is the whole point
            # of the gap rule - so they are emitted as episodes carrying their
            # true (sub-threshold) value and flagged, and the counting-process
            # clock is read off the calendar rather than off the row number.
            span = list(range(start, end + 1))
            alive_set = set(run)
            spells.append({
                "spell_id": spell_id, "importer": imp, "exporter": exp,
                "product_family": fam, "start_year": start, "end_year": end,
                "duration": end - start + 1,
                "event": 0 if right_censored else 1,
                "right_censored": int(right_censored),
                "left_trunc": int(left_trunc),
                "censor_reason": c_reason, "start_reason": s_reason,
                "n_gap_years": len(span) - len(run),
                "first_year_value_usd": round(series[start], 2),
                "mean_value_usd": round(
                    sum(series[y] for y in run) / len(run), 2),
            })
            for y in span:
                k = y - start + 1
                kg = weights.get((imp, fam, y), 0.0)
                val = series.get(y, 0.0)
                episodes.append({
                    "spell_id": spell_id, "importer": imp, "exporter": exp,
                    "product_family": fam, "year": y,
                    "left_trunc": int(left_trunc),
                    "gap_filled": int(y not in alive_set),
                    # The counting-process pair (t_start, t_stop) is what Cox
                    # reads; the three columns beside it restate the same spell
                    # in the form the data brief asks for, so a reader does not
                    # have to join back to spells.csv to see when a
                    # relationship began, when it ended, and whether the ending
                    # was observed at all.
                    "spell_start_year": start, "spell_end_year": end,
                    "right_censored": int(right_censored),
                    "censor_reason": c_reason, "start_reason": s_reason,
                    "t_start": k - 1, "t_stop": k,
                    "event": 1 if (y == end and not right_censored) else 0,
                    "import_value_usd": round(val, 2),
                    "net_weight_kg": round(kg, 2) if kg else "",
                    "unit_value_usd_per_kg": round(val / kg, 4)
                    if kg and val else "",
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
    world (data/raw/trade_world). Without that folder the same quantities are
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
            # The importer's total imports of that product from the whole
            # world. B3 calls it log_total_import_cp and uses it as the demand
            # proxy that separates market-wide movement from Viet Nam's own
            # performance. It was already computed here for market_share and
            # simply never written out.
            "total_import_cp": dict(wld_cell) if using_world else {},
            "partner_share": partner_share, "hhi_market": dict(hhi_market),
            "hhi_product": dict(hhi_product),
            "country_growth": growth_of(vn_prod, "country growth"),
            "world_growth": growth_of(wld_prod, "world growth"),
            "market_share": market_share, "using_world": using_world}


def _rnd(value, ndigits):
    """round(), but missing stays "" (an empty CSV cell) instead of the
    literal text "nan". csv.DictWriter has no concept of a numeric NaN - it
    calls str() on whatever it is given, and str(float("nan")) is the four
    characters "nan", not an empty field. A reader (pandas, polars, R) that
    infers a column's dtype from the file then sees that text token mixed in
    with genuine numbers and falls back to reading the whole column as
    strings, silently - this bit rca, product_share_pct, partner_share_pct,
    vn_market_share_pct, country_growth_pct and world_growth_pct before this
    fix. total_import_cp_usd already used the "" convention two lines below
    where this is called; the others are brought in line with it here."""
    if value is None:
        return ""
    r = round(value, ndigits)
    return "" if r != r else r  # r != r is true only for float("nan")


def attach(episodes, d):
    for e in episodes:
        imp, fam, y = e["importer"], e["product_family"], e["year"]
        e["rca"] = _rnd(d["rca"].get((fam, y)), 4)
        e["product_share_pct"] = _rnd(d["product_share"].get((fam, y)), 4)
        e["partner_share_pct"] = _rnd(d["partner_share"].get((imp, y)), 4)
        e["vn_market_share_pct"] = _rnd(
            d["market_share"].get((imp, fam, y)), 4)
        e["hhi_market"] = _rnd(d["hhi_market"].get(y), 6)
        e["hhi_product"] = _rnd(d["hhi_product"].get(y), 6)
        e["country_growth_pct"] = _rnd(d["country_growth"].get((fam, y)), 4)
        e["world_growth_pct"] = _rnd(d["world_growth"].get((fam, y)), 4)
        tot = d["total_import_cp"].get((imp, fam, y))
        e["total_import_cp_usd"] = round(tot, 2) if tot else ""
    return episodes


def write(name, rows, cols):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path} ({len(rows):,} rows)")


MASS_DEATH_SHARE, MASS_DEATH_MIN_N = 0.6, 30
MASS_DEATH_ALLOWLIST = os.path.join(SEL, "mass_death_allowlist.csv")


def mass_deaths(episodes):
    """Importer-years where more than MASS_DEATH_SHARE of the live relationships
    end in a confirmed death. That is never a market signal: every case found in
    v1 was a filing artefact (an unpublished year, an aggregate-only filing, a
    record that simply stops). A genuine one - a war, an embargo - has to be
    written into selection/mass_death_allowlist.csv with its reason."""
    allow = set()
    if os.path.exists(MASS_DEATH_ALLOWLIST):
        with open(MASS_DEATH_ALLOWLIST, encoding="utf-8") as f:
            allow = {(r["importer"], int(r["year"])) for r in csv.DictReader(f)}
    alive, dead = defaultdict(int), defaultdict(int)
    for e in episodes:
        if e["gap_filled"]:
            continue
        k = (e["importer"], e["year"])
        alive[k] += 1
        dead[k] += e["event"]
    return sorted((k, alive[k], dead[k] / alive[k]) for k in alive
                  if alive[k] >= MASS_DEATH_MIN_N
                  and dead[k] / alive[k] > MASS_DEATH_SHARE and k not in allow)


def write_revisions(revisions):
    """(importer, year) -> the revision carrying most of that filing's value.
    Every importer-year in the raw folder uses a single revision (measured), so
    the choice of rule only matters as a guard."""
    out = {k: max(c, key=c.get) for k, c in revisions.items()}
    path = os.path.join(OUT, "importer_year_revision.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["importer", "year", "hs_revision", "n_revisions"])
        for (imp, y) in sorted(out):
            w.writerow([imp, y, out[(imp, y)],
                        sum(1 for v in revisions[(imp, y)].values() if v > 0)])
    print(f"  wrote {path} ({len(out):,} importer-years)")
    return out


def main():
    print("Building product families (families.py)")
    u = build_families()
    write_family_map(u, OUT)
    fam_in_rev = families_in_revision(u)
    print("Reading trade panel")
    revisions = {}
    panel, weights, importers, holes = load_panel(u, revisions)
    print(f"  panel cells: {len(panel):,} from {len(importers)} importers")
    revision_of = write_revisions(revisions)
    observed = observed_years(RAW_TRADE)

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
    spells, episodes = build_spells(panel, last_year, weights, observed,
                                    revision_of, fam_in_rev, u.receivers)
    print(f"  spells: {len(spells):,}  episodes: {len(episodes):,}")
    for label, key in (("censor_reason", "censor_reason"),
                       ("start_reason", "start_reason")):
        counts = defaultdict(int)
        for s in spells:
            counts[s[key] or "(confirmed)"] += 1
        print(f"  {label}: " + ", ".join(f"{k} {v:,}" for k, v in sorted(counts.items())))
    print("Computing HS6-level covariates")
    d = derived(panel, world)
    episodes = attach(episodes, d)
    if not d["using_world"]:
        print("  WARNING: RCA / world growth computed without world imports")

    write("spells.csv", spells,
          ["spell_id", "importer", "exporter", "product_family", "start_year",
           "end_year", "duration", "event", "right_censored", "left_trunc",
           "censor_reason", "start_reason",
           "n_gap_years", "first_year_value_usd", "mean_value_usd"])
    write("episodes.csv", episodes,
          ["spell_id", "importer", "exporter", "product_family", "year",
           "spell_start_year", "spell_end_year", "right_censored",
           "left_trunc", "censor_reason", "start_reason", "gap_filled",
           "t_start", "t_stop", "event", "import_value_usd", "net_weight_kg",
           "unit_value_usd_per_kg", "rca",
           "product_share_pct", "partner_share_pct", "vn_market_share_pct",
           "total_import_cp_usd",
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

    bad = mass_deaths(episodes)
    if bad:
        print(f"\nMASS-DEATH GUARD: {len(bad)} importer-year(s) lose more than "
              f"{MASS_DEATH_SHARE:.0%} of their live relationships at once "
              f"(n >= {MASS_DEATH_MIN_N}):")
        for (imp, y), n, share in bad:
            print(f"    {imp} {y}: {share:.0%} of {n}")
        sys.exit("Fix the observation record or allowlist each case, with its "
                 f"reason, in {MASS_DEATH_ALLOWLIST}.")


if __name__ == "__main__":
    main()
