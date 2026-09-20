"""Parse the EU Combined Nomenclature regulations into an MFN tariff panel.

What this closes: TRAINS publishes no schedule at all for 2024 or 2025, so the
last two years of the panel carry a 2023 rate forward with no variation of
their own. The EU's own Common Customs Tariff does exist for those years - it
is Annex I of the annual CN regulation - and column 3 of its duty table is the
conventional rate, which is the MFN rate.

Layout of the duty table, stable across all three regulations:

    CN code        Description                     Conventional      Suppl.
                                                   rate of duty (%)  unit
    0401 10 10     -- In immediate packings ...    13,8 EUR/100 kg     -
    2208 30 11     --- 2 litres or less .......    Free              l alc.

Only rows whose code column carries a full eight digits are kept; the rest are
headings. "Free" is a zero rate. A rate written "13,8 EUR/100 kg/net" is
specific, not ad valorem, and contributes 0 to the ad-valorem column with
`has_specific` set - the same convention build_evfta_staging.py uses, so the
two are subtractable.

One nomenclature note that matters downstream: the six-digit part of CN 2024
onwards is HS2022 (revision H6), while the EVFTA schedule is HS2012 (H4).
Neither is the panel's key, which is the H0 product family, so both are run
through the same union-find from build_spells.py.

Outputs, in data/interim/:
  eu_mfn_cn8.csv     - one row per (year, CN8 line)
  eu_mfn_hs6.csv     - simple average ad-valorem MFN per (year, HS6)
  eu_mfn_family.csv  - the same keyed by the panel's product family

Usage: python3 build_eu_mfn_cn.py
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
RAW = os.path.join(HERE, "data", "raw", "eu_cn")
OUT = os.path.join(HERE, "data", "interim")

YEARS = (2024, 2025, 2026)

# Reference x-positions of the duty-table header; every page is matched to
# these and the small per-page shift is measured rather than assumed.
REF = {"CN": 56.0, "Description": 230.0, "Supplementary": 482.0}
COL_CODE_END = 100.0
COL_DESC_END = 400.0
COL_DUTY_END = 485.0

DOTS = re.compile(r"\.{3,}")


def page_rows(page):
    words = page.extract_words()
    if not words:
        return []
    header = {}
    for w in words:
        if w["top"] < 140 and w["text"] in REF and w["text"] not in header:
            header[w["text"]] = w
    if len(header) < 3:
        return []                       # a notes page, not the duty table
    dx = sum(header[k]["x0"] - REF[k] for k in header) / len(header)
    header_row = round(max(w["top"] for w in header.values()) / 3)

    lines = defaultdict(list)
    for w in words:
        key = round(w["top"] / 3)
        if key <= header_row + 1:       # header, its wrapped second line, "1 2 3 4"
            continue
        lines[key].append(w)

    rows = []
    for _, ws in sorted(lines.items()):
        ws.sort(key=lambda w: w["x0"])
        buckets = [[], [], [], []]
        for w in ws:
            x = w["x0"] - dx
            if x < COL_CODE_END:
                buckets[0].append(w["text"])
            elif x < COL_DESC_END:
                buckets[1].append(w["text"])
            elif x < COL_DUTY_END:
                buckets[2].append(w["text"])
            else:
                buckets[3].append(w["text"])
        cols = [" ".join(b).strip() for b in buckets]
        cols[1] = DOTS.sub(" ", cols[1]).strip()
        if any(cols):
            rows.append(cols)
    return rows


def ad_valorem(text):
    """(ad-valorem percent, has a specific component) from a duty cell.

    The CN writes duties five ways that matter here:

      "Free"                -> 0, nothing specific
      "6,5"  /  "15(3)"     -> 6,5 and 15; the bracket is a footnote marker
      "41,2 EUR/100 kg/net" -> purely specific, 0 ad valorem
      "(9 + EA) MAX 24,2 %" -> 9 ad valorem plus an agricultural component
      "(4)"                 -> no rate at all in the cell: the duty is
                               seasonal and lives in a footnote. Returning 0
                               here would invent a duty-free line, so this
                               returns None and the row is dropped.
    """
    s = (text or "").strip()
    if not s:
        return None, False
    if s.lower().startswith("free"):
        return 0.0, False
    if re.fullmatch(r"(\(\d+\)\s*)+", s):
        return None, False                 # footnote marker only
    has_specific = bool(re.search(r"EUR|€|\bEA\b|AD S/Z|AD F/M", s, re.I))
    core = s[1:] if re.match(r"^\(\s*\d", s) else s
    m = re.match(r"^(\d+(?:,\d+)?)", core)
    if not m:
        return 0.0, has_specific
    rest = core[m.end():].lstrip()
    if rest[:1] == "€" or rest[:3].upper() == "EUR" or rest[:1] == "/":
        return 0.0, True                   # the number belongs to the specific duty
    return float(m.group(1).replace(",", ".")), has_specific


dropped = Counter()


def parse_year(year):
    path = os.path.join(RAW, f"cn{year}.pdf")
    if not os.path.exists(path):
        print(f"  cn{year}: not on disk, skipped")
        return []
    out = []
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            if i % 200 == 0:
                print(f"  cn{year}: page {i + 1}/{n}", flush=True)
            # A long description pushes the duty onto the next visual line,
            # leaving the code's own row with an empty rate cell. Roughly one
            # line in eight of the CN looks like that, so a parser that
            # insists on code and duty sharing a row silently loses them.
            pending = None
            for code_txt, desc, duty, supp in page_rows(page):
                digits = re.sub(r"[^0-9]", "", code_txt)
                if len(digits) == 8:
                    if pending is not None:
                        dropped[year] += 1
                    pending = {"code": digits, "desc": desc}
                    if not duty:
                        continue
                elif pending is None or not duty:
                    continue
                av, spec = ad_valorem(duty)
                if av is None:
                    pending = None
                    continue
                out.append({
                    "year": year,
                    "code8": pending["code"],
                    "hs6": pending["code"][:6],
                    "description": (pending["desc"] + " " + desc).strip()[:160],
                    "duty_text": duty,
                    "mfn_ad_valorem_pct": av,
                    "has_specific_duty": int(spec),
                    "supplementary_unit": supp,
                    "page": i + 1,
                })
                pending = None
            if pending is not None:
                dropped[year] += 1
    return out


def write_csv(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"  wrote {path}  ({len(rows):,} rows)")


def read_hs6():
    """eu_mfn_hs6.csv back as rows, for --families-only."""
    with open(os.path.join(OUT, "eu_mfn_hs6.csv"), encoding="utf-8") as f:
        return [{"year": int(r["year"]), "hs6": r["hs6"],
                 "n_cn8_lines": int(r["n_cn8_lines"]),
                 "mfn_simple_avg_pct": float(r["mfn_simple_avg_pct"]),
                 "mfn_max_pct": float(r["mfn_max_pct"]),
                 "any_specific_duty": int(r["any_specific_duty"])}
                for r in csv.DictReader(f)]


def main():
    os.makedirs(OUT, exist_ok=True)
    # The HS6 table does not depend on the product key, only the family table
    # does - and re-parsing 20 years of CN PDFs costs ~10 minutes and ~6 GB.
    # After a change to families.py, --families-only re-keys from the HS6 file.
    if "--families-only" in sys.argv:
        write_families(read_hs6())
        return
    lines = []
    for year in YEARS:
        print(f"Parsing the CN {year} duty table")
        got = parse_year(year)
        print(f"  {len(got):,} CN8 lines with a conventional rate")
        lines += got
    if not lines:
        sys.exit("nothing parsed - run fetch_eu_cn.py first")

    write_csv(os.path.join(OUT, "eu_mfn_cn8.csv"), lines,
              ["year", "code8", "hs6", "description", "duty_text",
               "mfn_ad_valorem_pct", "has_specific_duty",
               "supplementary_unit", "page"])

    # ---- HS6, the level TRAINS reports and the panel joins on -------------
    by6 = defaultdict(list)
    for r in lines:
        by6[(r["year"], r["hs6"])].append(r)
    hs6_rows = []
    for (year, hs6), rs in sorted(by6.items()):
        avs = [r["mfn_ad_valorem_pct"] for r in rs]
        hs6_rows.append({
            "year": year,
            "hs6": hs6,
            "n_cn8_lines": len(rs),
            "mfn_simple_avg_pct": round(sum(avs) / len(avs), 4),
            "mfn_max_pct": max(avs),
            "any_specific_duty": int(any(r["has_specific_duty"] for r in rs)),
        })
    write_csv(os.path.join(OUT, "eu_mfn_hs6.csv"), hs6_rows,
              ["year", "hs6", "n_cn8_lines", "mfn_simple_avg_pct",
               "mfn_max_pct", "any_specific_duty"])

    write_families(hs6_rows)
    report(lines)


def write_families(hs6_rows):
    """The HS6 table keyed by the panel's product family."""
    sys.path.insert(0, os.path.join(HERE, "scripts"))
    import build_spells                                     # noqa: PLC0415
    u = build_spells.build_families()

    by_fam = defaultdict(list)
    for h in hs6_rows:
        fam = build_spells.family_of(u, "H6", h["hs6"])
        by_fam[(h["year"], fam)].append(h)
    fam_rows = []
    for (year, fam), hs in sorted(by_fam.items()):
        avs = [h["mfn_simple_avg_pct"] for h in hs]
        fam_rows.append({
            "year": year,
            "product_family": fam,
            "n_hs6": len(hs),
            "mfn_simple_avg_pct": round(sum(avs) / len(avs), 4),
            "mfn_max_pct": max(h["mfn_max_pct"] for h in hs),
            "any_specific_duty": int(any(h["any_specific_duty"] for h in hs)),
        })
    write_csv(os.path.join(OUT, "eu_mfn_family.csv"), fam_rows,
              ["year", "product_family", "n_hs6", "mfn_simple_avg_pct",
               "mfn_max_pct", "any_specific_duty"])


def report(lines):
    print("\nSanity:")
    for year in YEARS:
        rs = [r for r in lines if r["year"] == year]
        if not rs:
            continue
        if dropped.get(year):
            print(f"  {year}: {dropped[year]:,} code lines had no rate to "
                  f"attach and were dropped")
        avs = [r["mfn_ad_valorem_pct"] for r in rs]
        zero = sum(1 for a in avs if a == 0.0)
        print(f"  {year}: {len(rs):,} CN8 lines · {len(set(r['hs6'] for r in rs)):,}"
              f" HS6 · mean ad valorem {sum(avs) / len(avs):.2f}%"
              f" · duty-free lines {zero:,} ({100 * zero / len(rs):.1f}%)"
              f" · lines with a specific duty "
              f"{sum(r['has_specific_duty'] for r in rs):,}")
    print("  duty-text shapes seen:",
          dict(Counter(re.sub(r"\d+(,\d+)?", "#", r["duty_text"])[:24]
                       for r in lines).most_common(6)))


if __name__ == "__main__":
    main()
