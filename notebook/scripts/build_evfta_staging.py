"""Parse EVFTA Annex 2-A into a machine-readable staging schedule.

Appendix 2-A-1 is the Union's tariff schedule: one row per CN8 line, carrying
the base rate (the Common Customs Tariff in force on 26 June 2012) and a
staging category. Nobody publishes it as data, so this is where the project's
treatment variable comes from.

Three outputs, in data/interim/:

  evfta_eu_schedule_cn8.csv - the parse itself, one row per CN8 line
  evfta_staging_hs6.csv     - staging category aggregated to HS6, with a flag
                              where the CN8 lines under one HS6 disagree
  evfta_tariff_path_hs6.csv - (hs6, year) applied preferential ad-valorem rate
                              2020-2035, i.e. what the schedule commits the EU
                              to charge Vietnamese goods
  evfta_staging_family.csv  - the same, keyed by the *product family* the panel
                              is built on, so it joins onto panel_final.csv
                              without anyone having to redo a concordance

The schedule is written in the CN, which for the six-digit part is HS2012 -
revision H4 in WITS's naming. The panel is keyed to H0 families, so the last
step runs the schedule's HS6 codes through the same union-find
`build_spells.py` uses. Doing it anywhere else would risk two different
mappings of the same code.

The staging rules are read off Annex 2-A Section A:

  A     duty free from entry into force
  B3    removed in  4 equal annual stages
  B5    removed in  6 equal annual stages
  B7    removed in  8 equal annual stages
  B10   removed in 11 equal annual stages
  A+EP  ad-valorem part removed at entry into force, the entry-price specific
        duty is *kept* - so the ad-valorem path is A's, and a flag marks that
        the line is not actually duty free
  R75   not a staging category at all: a fixed EUR/tonne scale by calendar
        year (120 in 2016 falling to 75 from 2025), handled separately

Convention used for the equal-stage categories, stated so it can be argued
with: N equal cuts of base/N, the first on the date of entry into force
(1 August 2020), each later one on 1 January. So for a category with N stages
the rate in calendar year y is base * (N - k) / N with k = y - 2019, and the
line is duty free from year 2019 + N onwards. B3 therefore reaches zero in
2023, B5 in 2025, B7 in 2027, B10 in 2030.

2020 is the one year this cannot get exactly right: the first cut lands on
1 August, so five months of 2020 were charged at the pre-agreement rate. The
column `stage_1_partial_year` marks it; anyone building a yearly average
should weight 7/12 base + 5/12 stage-1.

Usage: python3 build_evfta_staging.py
"""

import csv
import os
import re
import sys
from collections import Counter, defaultdict

try:
    import pdfplumber
except ImportError:                                          # pragma: no cover
    sys.exit("pip install pdfplumber")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data", "raw", "evfta")
OUT = os.path.join(HERE, "data", "interim")

EIF_YEAR = 2020          # EVFTA entered into force 1 August 2020
LAST_YEAR = 2035

# Number of equal annual stages per category, from Annex 2-A Section A.
STAGES = {"A": 1, "A+EP": 1, "B3": 4, "B5": 6, "B7": 8,
          "B9": 10, "B10": 11, "B15": 16}

# Annex 2-A Section A(l): the R75 scale, EUR per tonne, by calendar year.
R75 = {y: v for y, v in [(2016, 120), (2017, 115), (2018, 110), (2019, 105),
                         (2020, 100), (2021, 95), (2022, 90), (2023, 85),
                         (2024, 80)]}

# Header x-positions on the reference page; every page is within 3px of these,
# and the offset is measured per page rather than assumed.
REF = {"Description": 277.0, "Base": 543.0, "Category": 648.0, "Comment": 721.0}
COL_CODE_END = 120.0     # a word starting left of this is in the code column
COL_DESC_END = 500.0
COL_RATE_END = 640.0
COL_CAT_END = 718.0


def page_rows(page):
    """Group a page's words into visual rows, splitting each into columns.

    Column boundaries are the reference ones shifted by however far this
    page's header sits from the reference header. Only the header row itself
    is dropped - the first data row sits barely 20px below it, and cutting a
    fixed band off the top of the page silently loses one tariff line per
    page, which is a thousand lines over the schedule.
    """
    words = page.extract_words()
    if not words:
        return []
    header = {}
    for w in words:
        if w["top"] < 140 and w["text"] in REF and w["text"] not in header:
            header[w["text"]] = w
    if len(header) < 4:
        return []                      # not a schedule page (title, notes)
    dx = sum(header[k]["x0"] - REF[k] for k in header) / len(header)
    header_row = round(min(w["top"] for w in header.values()) / 3)

    lines = defaultdict(list)
    for w in words:
        key = round(w["top"] / 3)
        if key <= header_row:          # the header row and anything above it
            continue
        lines[key].append(w)

    rows = []
    for _, ws in sorted(lines.items()):
        ws.sort(key=lambda w: w["x0"])
        buckets = [[], [], [], [], []]
        for w in ws:
            x = w["x0"] - dx
            if x < COL_CODE_END:
                buckets[0].append(w["text"])
            elif x < COL_DESC_END:
                buckets[1].append(w["text"])
            elif x < COL_RATE_END:
                buckets[2].append(w["text"])
            else:
                buckets[3].append(w["text"])   # category + comment, split later
        cols = [" ".join(b).strip() for b in buckets]
        if any(cols):
            rows.append(cols[:4] + [""])
    return rows


# Longest first: without this "A+EP" is swallowed by the bare "A" branch, and
# every entry-price line is mislabelled as an outright elimination.
CATEGORY = re.compile(
    r"^(A\+EP|B10\*\*|B10\*|B10|B15|B3|B5|B7|B9|R75|TRQ|CKD|A)")


def split_category(text):
    """The category token and whatever comment follows it in the same cell.

    The comment column starts close enough to the category column that
    "See Annex 2-A, ..." leaks into it, producing categories like "B3See".
    """
    t = (text or "").strip()
    if not t:
        return "", ""
    m = CATEGORY.match(t.replace(" ", ""))
    if not m:
        return "", t
    cat = m.group(1)
    # Consume len(cat) non-space characters off the front of the original
    # cell, so a cell written "A + EP See ..." splits as cleanly as "A+EP".
    i = taken = 0
    while i < len(t) and taken < len(cat):
        if not t[i].isspace():
            taken += 1
        i += 1
    return cat, t[i:].strip()


def parse_schedule(pdf_path, label):
    """One row per tariff line that carries a staging category."""
    out = []
    footer = re.compile(r"^EU/VN/Annex", re.I)
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            if i % 200 == 0:
                print(f"  {label}: page {i + 1}/{n}", flush=True)
            for code_txt, desc, rate, cat, comment in page_rows(page):
                if footer.match(code_txt) or footer.match(desc):
                    continue
                digits = re.sub(r"[^0-9]", "", code_txt)
                if len(digits) != 8:
                    continue           # chapter / heading / continuation line
                cat, tail = split_category(cat)
                if not cat:
                    continue
                comment = (comment + " " + tail).strip()
                suffix = re.sub(r"[0-9 ]", "", code_txt)   # the "B" of 6403 91 11B
                out.append({
                    "code8": digits,
                    "hs6": digits[:6],
                    "ex_out": suffix,
                    "description": desc,
                    "base_rate_text": rate,
                    "category": cat,
                    "comment": comment,
                    "page": i + 1,
                })
    return out


def ad_valorem(text):
    """Split a base-rate string into its ad-valorem and specific parts.

    "0"                       -> 0.0, no specific part
    "11,5"                    -> 11.5
    "10,2 + 93,1 EUR/100 kg"  -> 10.2, plus a specific part
    "20,9 EUR/hl"             -> 0.0, purely specific
    """
    s = (text or "").strip()
    has_specific = "EUR" in s.upper()
    m = re.match(r"^(\d+(?:,\d+)?)", s)
    if not m:
        return (0.0 if s in ("", "0") else None), has_specific
    rest = s[m.end():].lstrip()
    if rest[:3].upper() == "EUR" or rest[:1] == "/":
        return 0.0, True               # the number belongs to the specific duty
    return float(m.group(1).replace(",", ".")), has_specific


def staged_rate(base, category, year):
    """Applied ad-valorem rate under the schedule, or None if not on a path."""
    n = STAGES.get(category)
    if n is None or base is None:
        return None
    if year < EIF_YEAR:
        return None                    # before the agreement: MFN/GSP applies
    k = year - (EIF_YEAR - 1)          # k = 1 in the year of entry into force
    if k >= n:
        return 0.0
    return round(base * (n - k) / n, 4)


def write_csv(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"  wrote {path}  ({len(rows):,} rows)")


def main():
    os.makedirs(OUT, exist_ok=True)
    eu_pdf = os.path.join(RAW, "appendix-2a1.pdf")
    if not os.path.exists(eu_pdf):
        sys.exit(f"missing {eu_pdf} - run fetch_evfta_annex.py first")

    print("Parsing Appendix 2-A-1 (Tariff Schedule of the Union)")
    lines = parse_schedule(eu_pdf, "EU")
    print(f"  {len(lines):,} CN8 lines with a staging category")

    cats = Counter(r["category"] for r in lines)
    print("  categories:", dict(cats.most_common()))

    for r in lines:
        av, spec = ad_valorem(r["base_rate_text"])
        r["base_ad_valorem_pct"] = "" if av is None else av
        r["has_specific_duty"] = int(spec)
        r["on_staging_path"] = int(r["category"] in STAGES)

    write_csv(os.path.join(OUT, "evfta_eu_schedule_cn8.csv"), lines,
              ["code8", "hs6", "ex_out", "description", "base_rate_text",
               "base_ad_valorem_pct", "has_specific_duty", "category",
               "on_staging_path", "comment", "page"])

    # ---- HS6 aggregation -------------------------------------------------
    by6 = defaultdict(list)
    for r in lines:
        by6[r["hs6"]].append(r)

    hs6_rows = []
    for hs6, rs in sorted(by6.items()):
        c = Counter(r["category"] for r in rs)
        modal, modal_n = c.most_common(1)[0]
        avs = [r["base_ad_valorem_pct"] for r in rs
               if r["base_ad_valorem_pct"] != ""]
        # slowest = the category that takes longest to reach zero; that is the
        # conservative reading when CN8 lines under one HS6 disagree.
        slowest = max(rs, key=lambda r: STAGES.get(r["category"], 0))["category"]
        hs6_rows.append({
            "hs6": hs6,
            "n_cn8_lines": len(rs),
            "staging_cat": modal,
            "staging_cat_share": round(modal_n / len(rs), 4),
            "staging_cat_slowest": slowest,
            "staging_mixed": int(len(c) > 1),
            "categories_present": "|".join(f"{k}:{v}" for k, v in
                                           sorted(c.items())),
            "base_ad_valorem_mean": round(sum(avs) / len(avs), 4) if avs else "",
            "base_ad_valorem_max": max(avs) if avs else "",
            "any_specific_duty": int(any(r["has_specific_duty"] for r in rs)),
            "any_entry_price": int(any(r["category"] == "A+EP" for r in rs)),
        })
    write_csv(os.path.join(OUT, "evfta_staging_hs6.csv"), hs6_rows,
              ["hs6", "n_cn8_lines", "staging_cat", "staging_cat_share",
               "staging_cat_slowest", "staging_mixed", "categories_present",
               "base_ad_valorem_mean", "base_ad_valorem_max",
               "any_specific_duty", "any_entry_price"])

    # ---- the year-by-year path ------------------------------------------
    path_rows = []
    for h in hs6_rows:
        base = h["base_ad_valorem_mean"]
        if base == "":
            continue
        for year in range(EIF_YEAR, LAST_YEAR + 1):
            rate = staged_rate(base, h["staging_cat"], year)
            slow = staged_rate(base, h["staging_cat_slowest"], year)
            if rate is None:
                continue
            path_rows.append({
                "hs6": h["hs6"],
                "year": year,
                "staging_cat": h["staging_cat"],
                "base_ad_valorem_pct": base,
                "evfta_rate_pct": rate,
                "evfta_rate_pct_slowest_cat": "" if slow is None else slow,
                "evfta_cut_cum_pp": round(base - rate, 4),
                "evfta_cut_cum_share": round((base - rate) / base, 4) if base else "",
                "years_since_evfta": year - EIF_YEAR,
                "stage_1_partial_year": int(year == EIF_YEAR),
                "staging_mixed": h["staging_mixed"],
                "any_specific_duty": h["any_specific_duty"],
            })
    write_csv(os.path.join(OUT, "evfta_tariff_path_hs6.csv"), path_rows,
              ["hs6", "year", "staging_cat", "base_ad_valorem_pct",
               "evfta_rate_pct", "evfta_rate_pct_slowest_cat",
               "evfta_cut_cum_pp", "evfta_cut_cum_share", "years_since_evfta",
               "stage_1_partial_year", "staging_mixed", "any_specific_duty"])

    # ---- what the parse looks like, so it can be sanity-checked ----------
    print("\nSanity:")
    print(f"  distinct HS6 in the Union's schedule: {len(by6):,}")
    print(f"  HS6 whose CN8 lines disagree on category: "
          f"{sum(h['staging_mixed'] for h in hs6_rows):,}")
    nonzero = [h for h in hs6_rows if h["base_ad_valorem_mean"] not in ("", 0.0)]
    print(f"  HS6 with a non-zero base ad-valorem rate: {len(nonzero):,}")
    free = sum(1 for h in hs6_rows
               if h["staging_cat"] == "A" and h["base_ad_valorem_mean"] == 0.0)
    print(f"  HS6 already duty free at the base rate (category A, base 0): {free:,}")

    print("\nLinking the schedule to the panel's product families")
    fam_rows = link_to_panel_families(hs6_rows)
    print(f"  {len(fam_rows):,} product families carry an EVFTA staging category")


def link_to_panel_families(hs6_rows):
    """Attach the panel's product-family key to each HS6 of the schedule."""
    sys.path.insert(0, os.path.join(HERE, "scripts"))
    import build_spells                                   # noqa: PLC0415

    u = build_spells.build_families()
    by_fam = defaultdict(list)
    for h in hs6_rows:
        fam = build_spells.family_of(u, "H4", h["hs6"])
        by_fam[fam].append(h)

    rows = []
    for fam, hs in sorted(by_fam.items()):
        c = Counter(h["staging_cat"] for h in hs)
        modal, modal_n = c.most_common(1)[0]
        slowest = max(hs, key=lambda h: STAGES.get(h["staging_cat_slowest"], 0)
                      )["staging_cat_slowest"]
        avs = [h["base_ad_valorem_mean"] for h in hs
               if h["base_ad_valorem_mean"] != ""]
        base = round(sum(avs) / len(avs), 4) if avs else ""
        row = {
            "product_family": fam,
            "n_hs6": len(hs),
            "hs6_codes": "|".join(h["hs6"] for h in hs),
            "staging_cat": modal,
            "staging_cat_share": round(modal_n / len(hs), 4),
            "staging_cat_slowest": slowest,
            "staging_mixed": int(len(c) > 1 or any(h["staging_mixed"] for h in hs)),
            "base_ad_valorem_pct": base,
            "any_specific_duty": int(any(h["any_specific_duty"] for h in hs)),
            "any_entry_price": int(any(h["any_entry_price"] for h in hs)),
        }
        for year in range(EIF_YEAR, LAST_YEAR + 1):
            r = staged_rate(base, modal, year) if base != "" else None
            row[f"evfta_rate_{year}"] = "" if r is None else r
        rows.append(row)

    cols = (["product_family", "n_hs6", "hs6_codes", "staging_cat",
             "staging_cat_share", "staging_cat_slowest", "staging_mixed",
             "base_ad_valorem_pct", "any_specific_duty", "any_entry_price"]
            + [f"evfta_rate_{y}" for y in range(EIF_YEAR, LAST_YEAR + 1)])
    write_csv(os.path.join(OUT, "evfta_staging_family.csv"), rows, cols)
    return rows


if __name__ == "__main__":
    main()
