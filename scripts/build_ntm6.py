"""Step 8d: non-tariff measures at HS6, from the TRAINS researcher file.

`build_ntm.py` reads the three public WITS files, which are one sector-level
cross-section: every product in a 16-way sector grouping carries the same value
in every year, and 20% of episodes get nothing at all - China and Korea among
them. This module replaces that with the researcher file's own unit (imposing
country x affected country x HS6 x NTM code x year of data collection) and
produces two different kinds of variable, because the source supports two and
they must not be confused.

**Direction.** The panel's `importer` is the market Vietnamese goods enter, so
the barrier they meet is imposed by that country: `Reporter == importer`. NTM
chapter P is a country's rules on its *own* exports, so it is dropped here; it
survives in the raw file for `Reporter == VNM`, where it is a different variable
about Viet Nam's export administration.

**Partners.** Most measures are erga omnes and are filed against `WLD`, not
against Viet Nam by name - in the sample, the EU filed 8,075 rows naming VNM
against 1.28m naming WLD. Both are counted; `ntm6_bilateral_survey` isolates
the measures that name Viet Nam, which is the sharper variable and the rarer.

**The two time variables, and why both exist.**

`ntm6_*_survey` counts what was collected in the nearest earlier collection
year, stamped in `ntm6_source_year` - the conservative reading, and the same
shape `importer_lpi_source_year` already uses for the LPI waves.

`ntm6_*_inforce` counts measures whose recorded `[MinStartYear, MaxEndYear]`
window covers the panel year, pooled over every collection year for that
reporter and deduplicated on (family, NTM code, start, end). This one moves
between collection years - but it moves for a reason that belongs in any table
built on it: **the researcher file starts in 2010, and a measure is only ever
seen if some collection year caught it**, so counts before a reporter's first
collection year are structurally zero rather than genuinely low. `ntm6_observed`
marks the years a reporter filed at all.

**Why this shards to disk.** The full filtered file is ~22m rows and the
aggregate does not fit in the ~1 GB this machine has spare - holding it cost
0.9 GB at a quarter of the file. The researcher file is sorted by year and then
by reporter, so every (year, reporter) block is contiguous and can be totalled
and flushed as it goes. `merge_panel.py` then reads one reporter at a time,
which is how it already handles tariff schedules.

    python3 build_ntm6.py            # build the shards

Input:  data_raw/ntm/researcher/ntm_researcher_filtered.csv.gz
        data_raw/concordance/H4_to_H0   (the file is HS 2012; the panel is H0)
        selection/eu_tariff_mapping.csv (EUN files once for its members)
Output: analysis/_ntm6/{REPORTER}.csv.gz, analysis/ntm6_observed.csv
"""

import csv
import gzip
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "data_raw", "ntm", "researcher",
                   "ntm_researcher_filtered.csv.gz")
CONC = os.path.join(HERE, "data_raw", "concordance", "H4_to_H0")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "analysis")
SHARDS = os.path.join(OUT, "_ntm6")
OBSERVED = os.path.join(OUT, "ntm6_observed.csv")

# Import-side chapters. P (export-related) is the reporter's own export regime.
IMPORT_CHAPTERS = set("ABCDEFGHIJKLMNO")
GROUPS = {"sps": "A", "tbt": "B", "quantity": "E", "price": "F"}
COUNTS = ["all", "nonh", "bilateral"] + list(GROUPS)
COLS = ([f"ntm6_{c}_survey" for c in COUNTS]
        + ["ntm6_all_inforce", "ntm6_sps_inforce", "ntm6_tbt_inforce",
           "ntm6_source_year", "ntm6_observed"])

I_YEAR, I_REP, I_PARTNER, I_HS, I_ALL, I_NONH, I_CODE, I_MIN, I_MAX = (
    0, 2, 4, 7, 8, 9, 18, 19, 20)


def h4_to_h0():
    path = next((os.path.join(CONC, f) for f in os.listdir(CONC)
                 if f.upper().endswith(".CSV")), None)
    if path is None:
        return {}
    m = {}
    # The WITS concordance exports are not all UTF-8: H4_to_H0 carries Latin-1
    # accents in its descriptions and dies on strict decoding.
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f):
            keys = {k.lower().strip(): v for k, v in row.items()}
            src = next((v for k, v in keys.items()
                        if "2012" in k and "code" in k), None)
            dst = next((v for k, v in keys.items()
                        if ("1988" in k or "1992" in k) and "code" in k), None)
            if src and dst:
                # The panel writes families as `H0_090122`, so the prefix goes
                # on here rather than at every call site.
                m.setdefault(src.strip().zfill(6), set()).add(
                    "H0_" + dst.strip().zfill(6))
    return m


def reporter_of():
    """panel importer -> the TRAINS reporter that files its measures.

    Everyone files for themselves except EU members, whose measures are filed
    once under EUN - the same arrangement the tariff pull already handles, so
    the mapping is read from that file rather than restated here.
    """
    path = os.path.join(SEL, "eu_tariff_mapping.csv")
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            iso, rep = r["iso3"].strip(), r["tariff_reporter"].strip()
            if iso and rep:
                out[iso] = rep
    return out


def panel_families():
    """The H0 families the panel actually uses, to keep the shards small."""
    path = os.path.join(OUT, "spells.csv")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return {r["product_family"] for r in csv.DictReader(f)}


def _flush(handles, rep, cells, spans):
    """Write one (year, reporter) block. Opened in append mode, one per reporter."""
    if rep not in handles:
        handles[rep] = gzip.open(
            os.path.join(SHARDS, f"{rep}.csv.gz"), "wt", newline="",
            compresslevel=6)
        w = csv.writer(handles[rep])
        w.writerow(["kind", "family", "year_or_start", "end", "code_or_counts"])
    w = csv.writer(handles[rep])
    for (fam, year), c in cells.items():
        w.writerow(["s", fam, year, "",
                    "|".join(str(c.get(k, 0)) for k in COUNTS)])
    for fam, start, end, code in spans:
        w.writerow(["f", fam, start, end, code])
    cells.clear()
    spans.clear()


def build_shards(verbose=True):
    if not os.path.exists(SRC):
        raise SystemExit(f"{SRC} missing - run fetch_ntm_researcher.py first")
    os.makedirs(SHARDS, exist_ok=True)
    for f in os.listdir(SHARDS):
        os.remove(os.path.join(SHARDS, f))

    conc = h4_to_h0()
    families = panel_families()
    if verbose:
        print(f"  concordance H4->H0: {len(conc):,} HS6 | "
              f"panel families: {len(families) if families else 'all'}")

    handles = {}
    observed = defaultdict(set)
    cells, spans = defaultdict(lambda: defaultdict(int)), set()
    block = None
    n = kept = 0

    with gzip.open(SRC, "rt", newline="") as f:
        f.readline()
        try:
            for line in f:
                n += 1
                r = line.rstrip("\n").split(",")
                if len(r) < 21:
                    continue
                code = r[I_CODE]
                if code[:1] not in IMPORT_CHAPTERS:
                    continue
                partner = r[I_PARTNER]
                if partner not in ("WLD", "VNM"):
                    continue
                fams = conc.get(r[I_HS].zfill(6))
                if not fams:
                    continue
                if families is not None:
                    fams = [x for x in fams if x in families]
                    if not fams:
                        continue
                try:
                    year = int(r[I_YEAR])
                    start, end = int(r[I_MIN]), int(r[I_MAX])
                    n_all, n_nonh = int(r[I_ALL] or 0), int(r[I_NONH] or 0)
                except ValueError:
                    continue
                rep = r[I_REP]
                # The file is sorted by year then reporter, so a change of
                # either means the previous block is complete.
                if block != (year, rep):
                    if block is not None:
                        _flush(handles, block[1], cells, spans)
                    block = (year, rep)
                kept += 1
                observed[rep].add(year)
                for fam in fams:
                    c = cells[(fam, year)]
                    c["all"] += n_all
                    c["nonh"] += n_nonh
                    if partner == "VNM":
                        c["bilateral"] += n_all
                    for g, ch in GROUPS.items():
                        if code[:1] == ch:
                            c[g] += n_all
                    spans.add((fam, start, end, code))
                if verbose and n % 5_000_000 == 0:
                    print(f"    {n:,} rows read, {kept:,} usable, "
                          f"{len(handles)} reporters", flush=True)
        except EOFError:
            print("  ntm6: WARNING - gzip stream truncated mid-file; "
                  "the shards cover only what was read")
    if block is not None:
        _flush(handles, block[1], cells, spans)
    for h in handles.values():
        h.close()

    with open(OBSERVED, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["reporter", "years"])
        for rep in sorted(observed):
            w.writerow([rep, ";".join(str(y) for y in sorted(observed[rep]))])

    size = sum(os.path.getsize(os.path.join(SHARDS, f))
               for f in os.listdir(SHARDS))
    if verbose:
        print(f"  ntm6: {n:,} rows read, {kept:,} usable -> "
              f"{len(handles)} reporter shards, {size/1e6:.1f} MB gzipped")
        print(f"  -> {OBSERVED} ({len(observed)} reporters)")
    return observed


def load_observed():
    if not os.path.exists(OBSERVED):
        return {}
    out = {}
    with open(OBSERVED, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["reporter"]] = [int(y) for y in r["years"].split(";") if y]
    return out


def load_reporter(rep):
    """(survey, inforce) for one reporter. Blocks are re-totalled and spans
    deduplicated here, which is where the cross-year dedup finally happens."""
    path = os.path.join(SHARDS, f"{rep}.csv.gz")
    survey, inforce = defaultdict(lambda: [0] * len(COUNTS)), defaultdict(set)
    if not os.path.exists(path):
        return {}, {}
    with gzip.open(path, "rt", newline="") as f:
        for r in csv.reader(f):
            if not r or r[0] == "kind":
                continue
            if r[0] == "s":
                acc = survey[(r[1], int(r[2]))]
                for i, v in enumerate(r[4].split("|")):
                    acc[i] += int(v)
            else:
                inforce[r[1]].add((int(r[2]), int(r[3]), r[4]))
    return dict(survey), {k: sorted(v) for k, v in inforce.items()}


def attach(rows, survey, inforce, years):
    """Write the NTM6 columns onto one importer's episodes. Returns hits."""
    hits = 0
    for e in rows:
        if not years:
            for c in COLS:
                e[c] = ""
            continue
        fam, year = e.get("product_family"), int(e["year"])
        earlier = [y for y in years if y <= year]
        src = earlier[-1] if earlier else years[0]
        acc = survey.get((fam, src))
        for i, c in enumerate(COUNTS):
            e[f"ntm6_{c}_survey"] = acc[i] if acc else 0
        live = [t for t in inforce.get(fam, ()) if t[0] <= year <= t[1]]
        e["ntm6_all_inforce"] = len(live)
        e["ntm6_sps_inforce"] = sum(1 for t in live if t[2][:1] == "A")
        e["ntm6_tbt_inforce"] = sum(1 for t in live if t[2][:1] == "B")
        e["ntm6_source_year"] = src
        e["ntm6_observed"] = int(year in years)
        hits += 1
    return hits


if __name__ == "__main__":
    import resource
    obs = build_shards()
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    print(f"  peak RSS {peak:.2f} GB")
    for rep in ("USA", "EUN", "JPN", "KOR", "CHN"):
        if rep in obs:
            print(f"    {rep}: {sorted(obs[rep])}")
    sys.exit(0)
