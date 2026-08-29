"""Step 11: the CBAM product scope, which the brief names and the project lacked.

`Sinking Relationships.md` gives the EU a specific job: it is the source of the
*other* shock, the carbon border adjustment, so that the hazard from a
conventional tariff can be compared against the hazard from a carbon measure.
Nothing in this project had ever collected it - "CBAM" appears in no script, no
document and no column.

The scope is legislated, not estimated: Annex I of Regulation (EU) 2023/956
lists the CN codes covered, sector by sector, with explicit exception blocks.
This reads that annex from the Publications Office's CELLAR service, which
serves the consolidated text over content negotiation (eur-lex.europa.eu itself
answers a JavaScript challenge and cannot be read by a script).

**One finding belongs at the top, because it changes what the variable means.**
Article 32 sets the transitional period at **1 October 2023 to 31 December
2025**, during which the importer's obligations are *reporting only* - no
certificates, no payment. The definitive regime starts 1 January 2026, which is
one year past the end of this panel. So inside the observation window CBAM is a
compliance and anticipation cost, not a price. Any table comparing it with the
2025 US tariff has to say so, or it is comparing a duty with a filing duty.

Granularity: CN is the EU's 8-digit extension of HS6, and the annex mixes
2-digit chapters ("72"), 4-digit headings ("2814") and full 8-digit codes. An
exception written below HS6 - `7202 99 10 Ferro-phosphorus` - cannot be
subtracted cleanly from a 6-digit panel, so those HS6 are marked partial and
carry the share of their CN lines that survive, the same treatment the US
exemption list gets.

    python3 fetch_cbam_scope.py

Output: data_raw/cbam/reg_2023_956.xhtml   (the source text, kept for audit)
        analysis/cbam_products.csv         (product_family level, H0)
        analysis/cbam_products_cn.csv      (the CN lines, audit trail)
"""

import csv
import os
import re
import sys
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data_raw", "cbam")
CONC = os.path.join(HERE, "data_raw", "concordance", "H6_to_H0")
OUT = os.path.join(HERE, "analysis")
CELLAR = "http://publications.europa.eu/resource/celex/32023R0956"
SECTORS = {"Cement", "Electricity", "Fertilisers", "Iron and steel",
           "Aluminium", "Chemicals"}
# "2507 00 80  – Other kaolinic clays" / "72 –" / "7202 2 – Ferro-silicon"
CODE = re.compile(r"^(\d[\d ]*?)\s*[–-]\s*(.*)$")
GHG = re.compile(r"^(Carbon dioxide|Nitrous oxide|Perfluorocarbons)")


def fetch():
    os.makedirs(RAW, exist_ok=True)
    dest = os.path.join(RAW, "reg_2023_956.xhtml")
    if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
        print(f"  regulation already on disk ({os.path.getsize(dest):,} bytes)")
        return dest
    req = urllib.request.Request(CELLAR, headers={
        "Accept": "application/xhtml+xml", "Accept-Language": "eng"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())
    print(f"  CELEX 32023R0956 -> {os.path.getsize(dest):,} bytes")
    return dest


def annex_lines(path):
    s = open(path, encoding="utf-8", errors="replace").read()
    txt = re.sub(r"<[^>]+>", "\n", s)
    # The annex separates the three parts of a CN code with non-breaking
    # spaces, so `2507\xa000\xa080` never matches a pattern written with
    # ordinary spaces. This one substitution is the whole reason an earlier
    # pass found three sectors instead of six.
    txt = txt.replace("\xa0", " ")
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    start = next(i for i, l in enumerate(lines)
                 if l == "ANNEX I" and lines[i + 1].startswith("List of goods"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "ANNEX II")
    return lines[start:end]


def parse(lines):
    """-> [(sector, cn, description, is_exception)] in document order."""
    out = []
    sector, excepting = None, False
    for line in lines:
        if line in SECTORS:
            sector, excepting = line, False
            continue
        if line in ("CN code", "Greenhouse gas"):
            continue
        if line.startswith("Except"):
            excepting = True
            # Fertilisers writes its single exception inline - "Except: 3105 60
            # 00 - ..." - rather than opening a block, so the rest of the line
            # still has to be read.
            line = line.split(":", 1)[-1].strip()
            if not line:
                continue
        if GHG.match(line):
            # A greenhouse-gas cell closes the row, and with it any exception
            # block that was open.
            excepting = False
            continue
        m = CODE.match(line)
        if not m or sector is None:
            continue
        cn = m.group(1).replace(" ", "")
        if not cn:
            continue
        out.append((sector, cn, m.group(2).strip(), int(excepting)))
    return out


def h6_universe():
    path = next((os.path.join(CONC, f) for f in os.listdir(CONC)
                 if f.upper().endswith(".CSV")), None)
    fwd = defaultdict(set)
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f):
            keys = {k.lower().strip(): v for k, v in row.items()}
            src = next((v for k, v in keys.items()
                        if "2022" in k and "code" in k), None)
            dst = next((v for k, v in keys.items()
                        if ("1988" in k or "1992" in k) and "code" in k), None)
            if src and dst:
                fwd[src.strip().zfill(6)].add("H0_" + dst.strip().zfill(6))
    return fwd


def main():
    path = fetch()
    rows = parse(annex_lines(path))
    inc = [(s, c, d) for s, c, d, e in rows if not e]
    exc = [(s, c, d) for s, c, d, e in rows if e]
    print(f"  Annex I: {len(inc)} included CN lines, {len(exc)} exceptions, "
          f"{len({s for s, _, _ in inc})} sectors")

    cn_path = os.path.join(OUT, "cbam_products_cn.csv")
    with open(cn_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sector", "cn_code", "is_exception", "description"])
        for s, c, d, e in rows:
            w.writerow([s, c, e, d])
    print(f"  -> {cn_path}")

    fwd = h6_universe()
    # An HS6 is in scope if some include prefix matches it (or it matches an
    # include code longer than six digits). It drops out if an exception prefix
    # of six digits or fewer covers it; an exception longer than six digits can
    # only make it partial, because CN goes deeper than the panel can follow.
    per_fam = {}
    n_full = n_partial = 0
    for h6, fams in fwd.items():
        sector = None
        for s, c, _ in inc:
            if h6.startswith(c) or (len(c) > 6 and c.startswith(h6)):
                sector = s
                break
        if sector is None:
            continue
        killed = partial = False
        for _, c, _ in exc:
            if len(c) <= 6 and h6.startswith(c):
                killed = True
                break
            if len(c) > 6 and c.startswith(h6):
                partial = True
        if killed:
            continue
        n_partial += partial
        n_full += not partial
        for fam in fams:
            prev = per_fam.get(fam)
            if prev is None or (prev[1] and not partial):
                per_fam[fam] = (sector, partial)

    fam_path = os.path.join(OUT, "cbam_products.csv")
    with open(fam_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_family", "cbam_sector", "cbam_partial"])
        for fam in sorted(per_fam):
            w.writerow([fam, per_fam[fam][0], int(per_fam[fam][1])])
    print(f"  in scope: {n_full} HS6 wholly, {n_partial} partly "
          f"-> {len(per_fam)} H0 families")
    print(f"  -> {fam_path}")
    by_sector = defaultdict(int)
    for fam, (s, _) in per_fam.items():
        by_sector[s] += 1
    print("  families by sector: " + ", ".join(
        f"{s}:{n}" for s, n in sorted(by_sector.items(), key=lambda kv: -kv[1])))
    print("  transitional period 1 Oct 2023 - 31 Dec 2025 (Article 32): "
          "reporting only, no certificates inside this panel's window")


if __name__ == "__main__":
    sys.exit(main())
