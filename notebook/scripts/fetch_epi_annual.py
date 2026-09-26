"""Step 10: the Yale EPI as an annual series, not a single cross-section.

The GLPI variants in `build_glpi.py` all lean on the EPI, and until now the only
EPI on disk was `epi2026results.xlsx` - one cross-section, which is why
`importer_glpi_*` cannot move over time and why the earlier note recorded the
archive as unreachable (a 500 from Yale's archive endpoint). The 500 is real,
but it was the wrong door: **past-year EPI *scores* are not published at all**,
by anyone. What Yale publishes instead, in the release archives, is every
underlying indicator as an annual series back to 1996 - which is the raw
material a time-varying environmental index has to be built from anyway.

    epi2026indicatorsna.zip    ~50 indicators, one CSV each, wide by year
    epi2026indicatorsmvc.zip   the same, carrying missing-value reason codes
    epi2026methods*.xlsx       the weight tree that turns indicators into scores

This script downloads all three and reshapes the indicator archive into one long
table. It deliberately stops there. Collapsing ~50 indicators into an annual EPI
means applying the weight tree, and the project already has one unsettled
question about how to build a composite - which GLPI construction to follow.
Stacking a second bespoke composite underneath the first would hide a research
decision inside a data step. The ingredients are on disk and documented; the
weighting is the team's to choose.

    python3 fetch_epi_annual.py

Output: data/raw/epi/{epi2026indicatorsna.zip,epi2026indicatorsmvc.zip,methods}
        data/interim/epi_indicators_annual.csv  (iso3, year, indicator, value)
"""

import csv
import io
import os
import re
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data", "raw", "epi")
OUT = os.path.join(HERE, "data", "interim")
BASE = "https://epi.yale.edu/downloads/"
FILES = [
    "epi2026indicatorsna.zip",
    "epi2026indicatorsmvc.zip",
    "epi2026methods2026-07-08.xlsx",
]
UA = {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"}
# "RLI.ind.2004" -> ("RLI", 2004)
COL = re.compile(r"^([A-Z0-9]+)\.ind\.(\d{4})$")


def fetch(name):
    dest = os.path.join(RAW, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  {name}: already on disk ({os.path.getsize(dest):,} bytes)")
        return dest
    req = urllib.request.Request(BASE + name, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
        f.write(r.read())
    print(f"  {name}: {os.path.getsize(dest):,} bytes")
    return dest


def main():
    os.makedirs(RAW, exist_ok=True)
    paths = {name: fetch(name) for name in FILES}

    zpath = paths["epi2026indicatorsna.zip"]
    rows = []
    inds, years, isos = set(), set(), set()
    with zipfile.ZipFile(zpath) as z:
        members = [n for n in z.namelist() if n.lower().endswith(".csv")]
        for name in sorted(members):
            text = z.read(name).decode("utf-8", "replace")
            rdr = csv.DictReader(io.StringIO(text))
            cols = [(c, COL.match(c)) for c in (rdr.fieldnames or [])]
            cols = [(c, m.group(1), int(m.group(2))) for c, m in cols if m]
            if not cols:
                continue
            for r in rdr:
                iso = (r.get("iso") or "").strip()
                if not iso:
                    continue
                isos.add(iso)
                for col, ind, year in cols:
                    v = (r.get(col) or "").strip()
                    if v in ("", "NA", "NaN"):
                        continue
                    rows.append((iso, year, ind, v))
                    inds.add(ind)
                    years.add(year)

    path = os.path.join(OUT, "epi_indicators_annual.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["iso3", "year", "indicator", "value"])
        w.writerows(sorted(rows, key=lambda t: (t[0], t[1], t[2])))

    print(f"\n  -> {path}")
    print(f"     {len(rows):,} values | {len(isos)} economies | "
          f"{len(inds)} indicators | {min(years)}-{max(years)}")
    print("     the weight tree is in "
          f"{os.path.basename(paths[FILES[2]])} - composing an annual EPI "
          "from these is a research decision, not a download")


if __name__ == "__main__":
    sys.exit(main())
