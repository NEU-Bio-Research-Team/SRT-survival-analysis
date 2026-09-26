"""Step 9b: the product scope of the 2025 US reciprocal tariff.

`fetch_us_tariffs_2025.py` got the rates - 109 headings carrying a country rate
across 85 countries - but only at country level, because the exempt product list
is not in the USITC REST payload. It lives in a legal note, U.S. note 2(v)(iii)
to subchapter III of chapter 99, which the schedule publishes only as a PDF.
That is the gap this file closes.

Two lists matter, and both apply to *any* country, Viet Nam included:

- **(v)(iii)(a)** - a bare column of HTS8 subheadings, several hundred of them,
  exempt from every reciprocal heading in 9903.02.01-9903.02.73. Viet Nam's
  +20% sits at 9903.02.69, inside that range, so this list is the one that
  decides whether a Vietnamese product line was hit or spared.
- **(v)(iii)(b)** - eleven named articles, each naming its subheading in prose.

The output is at HS6 because that is the panel's unit, and the roll-up is not
lossless: an HS6 can hold both exempt and non-exempt HTS8 lines. So the file
carries `n_lines_exempt` and a `partial` flag rather than pretending the
exemption is clean, and the panel column built from it should be read as "this
product family contains exempt tariff lines", not "this product was exempt".

HTS 2026 is HS 2022, i.e. H6 in this project's vocabulary, so the join to the
panel's H0 product families runs through data/raw/concordance/H6_to_H0.

    python3 extract_us_exemptions.py

Output: data/interim/us_tariff_exemptions_2025.csv  (hs6 level, H6 and H0)
        data/interim/us_tariff_exemptions_2025_hs8.csv  (the raw list, audit trail)
"""

import csv
import os
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(HERE, "data", "raw", "us_tariffs_2025", "hts_chapter99_notes.pdf")
OUT = os.path.join(HERE, "data", "interim")

HS8 = re.compile(r"\b(\d{4}\.\d{2}\.\d{2})\b")
# Chapter 98 and 99 codes are cross-references to other headings, never products.
SKIP_CHAPTERS = {"98", "99"}

START_A = re.compile(r"\(a\)\s+As provided for in heading 9903\.01\.32")
START_B = re.compile(r"\(b\)\s+As provided in heading 9903\.02\.78")
END_B = re.compile(r"\(iv\)\s+As provided in 9903\.01\.26")


def pdf_lines():
    txt = subprocess.run(
        ["pdftotext", "-layout", PDF, "-"], capture_output=True, check=True
    ).stdout.decode("utf-8", "replace")
    return txt.split("\n")


def slice_between(lines, start_re, end_re):
    a = b = None
    for i, line in enumerate(lines):
        if a is None:
            if start_re.search(line):
                a = i
            continue
        if end_re.search(line):
            b = i
            break
    if a is None:
        raise SystemExit("could not locate the start of the exemption list")
    return lines[a: b if b is not None else len(lines)]


def codes_in(block):
    """HTS8 codes, in order, skipping the running page furniture."""
    out = []
    for line in block:
        if "Harmonized Tariff Schedule" in line or "Statistical Reporting" in line:
            continue
        for m in HS8.finditer(line):
            code = m.group(1)
            if code[:2] in SKIP_CHAPTERS:
                continue
            out.append(code)
    return out


def h6_to_h0():
    """(h6 -> set of families, family -> set of h6). Both directions are needed.

    The forward map places an exempt subheading in the panel's vocabulary. The
    reverse map is what stops that from overstating: HS 1992 is coarser than HS
    2022 in exactly the places this matters - all of 8517.13 (smartphones),
    8517.14, 8524.xx and 8525.60 collapse into the single family H0_852520 - so
    a family can hold both exempt and non-exempt subheadings, and only the
    reverse map can say in what proportion.
    """
    import families
    u = families.build_families(verbose=False)
    fwd, rev = defaultdict(set), defaultdict(set)
    # Families come from the shared product key (families.py), so a family here
    # is the same set of H0 codes the panel uses - including the orphan merges.
    for h6, fam in families.table_map(u, "H6").items():
        fwd[h6].add(fam)
        rev[fam].add(h6)
    return fwd, rev


def main():
    lines = pdf_lines()

    block_a = slice_between(lines, START_A, START_B)
    block_b = slice_between(lines, START_B, END_B)
    list_a = codes_in(block_a)
    list_b = codes_in(block_b)
    print(f"(v)(iii)(a): {len(list_a):,} HTS8 lines over {len(block_a):,} text lines")
    print(f"(v)(iii)(b): {len(list_b):,} HTS8 lines over {len(block_b):,} text lines")

    rows = [(c, "v_iii_a") for c in list_a] + [(c, "v_iii_b") for c in list_b]
    seen = {}
    for code, src in rows:
        seen.setdefault(code, src)

    hs8_path = os.path.join(OUT, "us_tariff_exemptions_2025_hs8.csv")
    with open(hs8_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hts8", "hs6_h6", "subdivision"])
        for code in sorted(seen):
            w.writerow([code, code.replace(".", "")[:6], seen[code]])
    print(f"  -> {hs8_path}  ({len(seen):,} distinct HTS8)")

    per6 = defaultdict(lambda: {"n": 0, "src": set()})
    for code, src in seen.items():
        h6 = code.replace(".", "")[:6]
        per6[h6]["n"] += 1
        per6[h6]["src"].add(src)

    fwd, rev = h6_to_h0()
    matched = 0
    hs6_path = os.path.join(OUT, "us_tariff_exemptions_2025.csv")
    with open(hs6_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hs6_h6", "product_family_h0", "n_lines_exempt", "subdivision"])
        for h6 in sorted(per6):
            h0s = sorted(fwd.get(h6, []))
            if h0s:
                matched += 1
            src = "+".join(sorted(per6[h6]["src"]))
            for h0 in h0s or [""]:
                w.writerow([h6, h0, per6[h6]["n"], src])
    print(f"  -> {hs6_path}  ({len(per6):,} HS6, {matched:,} mapped to H0)")

    # The family-level file, which is what the panel merges. `exempt_share_h6`
    # is the honest version of the flag: 1.0 means every HS 2022 subheading in
    # the family is exempt, anything less means the family straddles the line
    # and the episode's own composition decides. Nothing here can resolve that
    # further - HS 1992 simply does not distinguish the goods.
    fam_path = os.path.join(OUT, "us_exempt_products.csv")
    fams = sorted({h0 for h6 in per6 for h0 in fwd.get(h6, [])})
    full = 0
    with open(fam_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_family", "us_exempt_share_h6", "us_exempt_full",
                    "n_h6_in_family", "n_h6_exempt"])
        for h0 in fams:
            members = rev.get(h0, set())
            hit = {h6 for h6 in members if h6 in per6}
            share = len(hit) / len(members) if members else 0.0
            is_full = int(bool(members) and len(hit) == len(members))
            full += is_full
            w.writerow([h0, f"{share:.4f}", is_full,
                        len(members), len(hit)])
    print(f"  -> {fam_path}  ({len(fams):,} H0 families, "
          f"{full:,} wholly exempt, {len(fams)-full:,} straddling)")

    chap = defaultdict(int)
    for code in seen:
        chap[code[:2]] += 1
    top = sorted(chap.items(), key=lambda kv: -kv[1])[:12]
    print("  top chapters: " + ", ".join(f"{c}:{n}" for c, n in top))
    for c in ("84", "85", "61", "62", "64", "94"):
        print(f"  chapter {c}: {chap.get(c, 0)} exempt lines")


if __name__ == "__main__":
    sys.exit(main())
