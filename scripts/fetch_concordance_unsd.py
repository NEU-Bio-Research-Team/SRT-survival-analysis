"""Fetch the UNSD HS correlation tables that families.py needs.

The WITS tables in data/raw/concordance/ are *conversions*: every code of a
newer revision points at exactly one HS1992 code. When a revision merges several
HS1992 codes into one new code, the WITS table keeps one of them and the others
lose every successor - which is what produced the orphan deaths described in
docs/STAGE1_PANEL_FIX_PLAN.md (T1). The UNSD workbooks carry a *correlation*
sheet beside the conversion sheet, listing every n:n link between the two
editions, and that is the only place the lost links survive.

Output: data/raw/concordance/unsd/<file> plus SHA256SUMS.

Usage: python3 scripts/fetch_concordance_unsd.py
"""

import hashlib
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "raw", "concordance", "unsd")
BASE = "https://unstats.un.org/unsd/classifications/Econ/tables/"
UA = "Mozilla/5.0 (compatible; trade-survival-research/1.0)"

# revision -> file name on the UNSD server (spelling varies between editions)
FILES = {
    "H1": "HS1996 to HS1992 - Correlation and conversion tables.xls",
    "H2": "HS2002 to HS1992 - Correlation and conversion tables.xls",
    "H3": "HS 2007 to HS 1992 Correlation and conversion tables.xls",
    "H4": "HS 2012 to HS 1992 Correlation and conversion tables.xls",
    "H5": "HS2017toHS1992ConversionAndCorrelationTables.xlsx",
    "H6": "HS2022toHS1992ConversionAndCorrelationTables.xlsx",
}


def local_name(rev):
    ext = os.path.splitext(FILES[rev])[1]
    return f"{rev}_to_H0_unsd{ext}"


def main():
    os.makedirs(OUT, exist_ok=True)
    sums = []
    for rev, name in FILES.items():
        path = os.path.join(OUT, local_name(rev))
        if not os.path.exists(path):
            url = BASE + urllib.parse.quote(name)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            if body[:2] not in (b"PK", b"\xd0\xcf"):      # xlsx zip / xls OLE
                raise SystemExit(f"{rev}: {url} did not return a workbook")
            with open(path, "wb") as f:
                f.write(body)
            print(f"  fetched {rev}: {len(body):,} bytes")
        with open(path, "rb") as f:
            sums.append(f"{hashlib.sha256(f.read()).hexdigest()}  {local_name(rev)}")
    with open(os.path.join(OUT, "SHA256SUMS"), "w", encoding="utf-8") as f:
        f.write("\n".join(sums) + "\n")
    print(f"  {len(sums)} tables in {OUT}")


if __name__ == "__main__":
    main()
