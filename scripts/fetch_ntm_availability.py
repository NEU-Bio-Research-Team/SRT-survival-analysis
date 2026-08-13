"""Step 8a: read UNCTAD TRAINS Online's own coverage map for NTM data.

The WITS public NTM files are a dead end for a panel: 75 countries, one survey
year each, no product dimension. Before paying the cost of registering for
TRAINS Online and pulling files by hand, it is worth knowing exactly what is
behind that login. TRAINS Online is an Angular front end talking to
`api-trains2.unctad.org`, and its reference endpoints answer without a token:

  /countriesWithYearsOfDataCollection  which country was collected in which year
  /ntmTypes                            the MAST chapter list actually in use
  /imposingCountries                   country ids, needed for any later pull

The measure-level endpoints (`/denormalisedMeasures`) do *not*: they answer 200
with an empty array unless the caller is signed in, so the actual HS6 records
still require an account. What this script produces is therefore the decision
input, not the data - it says how many of our importers TRAINS covers, and in
how many distinct years, so the value of registering is a number rather than a
guess.

Output: selection/ntm_availability.csv, selection/ntm_types.csv
"""

import csv
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
SEL = os.path.join(HERE, "selection")
API = "https://api-trains2.unctad.org"
# the default urllib agent is refused by the endpoint; the site's own is not
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) " \
     "Chrome/120.0 Safari/537.36"

YEAR_MIN, YEAR_MAX = 2002, 2021        # the panel window
EU_MEMBERS = set(
    "AUT BEL BGR CYP CZE DEU DNK ESP EST FIN FRA GBR GRC HRV HUN IRL ITA LTU "
    "LUX LVA MLT NLD POL PRT ROU SVK SVN SWE".split())


def get(path):
    req = urllib.request.Request(f"{API}/{path}", headers={
        "User-Agent": UA, "Accept": "application/json",
        "Origin": "https://trainsonline.unctad.org"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def importers():
    with open(os.path.join(SEL, "importers_selected.csv"),
              encoding="utf-8") as f:
        return [r["iso3"] for r in csv.DictReader(f)]


def main():
    print("Reading TRAINS Online coverage map")
    rows = get("countriesWithYearsOfDataCollection")
    years = sorted(k for k in rows[0] if k.isdigit())
    by_iso = {r["countryISO"]: r for r in rows}
    print(f"  {len(rows)} countries, collection years {years[-1]}-{years[0]}")

    types = get("ntmTypes")
    with open(os.path.join(SEL, "ntm_types.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ntmCode", "ntmDescription"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(types)
    print(f"  wrote ntm_types.csv ({len(types)} MAST chapters)")

    out, covered, in_window, missing = [], 0, 0, []
    for iso in importers():
        rec = by_iso.get(iso)
        source = iso
        if rec is None and iso in EU_MEMBERS:
            rec, source = by_iso.get("EUN"), "EUN"
        if rec is None:
            missing.append(iso)
            continue
        collected = [int(y) for y in years if rec.get(y) == "Y"]
        inside = [y for y in collected if YEAR_MIN <= y <= YEAR_MAX]
        covered += 1
        in_window += bool(inside)
        out.append({
            "iso3": iso, "trains_reporter": source,
            "years_collected": ";".join(str(y) for y in sorted(collected)),
            "n_years": len(collected),
            "years_in_window": ";".join(str(y) for y in sorted(inside)),
            "n_years_in_window": len(inside),
        })

    path = os.path.join(SEL, "ntm_availability.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "iso3", "trains_reporter", "years_collected", "n_years",
            "years_in_window", "n_years_in_window"])
        w.writeheader()
        w.writerows(sorted(out, key=lambda r: -r["n_years_in_window"]))
    print(f"  wrote {path}")

    total = covered + len(missing)
    multi = sum(1 for r in out if r["n_years_in_window"] > 1)
    print(f"\n  importers TRAINS covers:      {covered}/{total}")
    print(f"  with >=1 collection in {YEAR_MIN}-{YEAR_MAX}: {in_window}")
    print(f"  with >=2 collections in window:  {multi} "
          f"(these could carry a time-varying NTM variable)")
    if missing:
        print(f"  not covered at all: {', '.join(missing)}")
    print("\n  NOTE: measure-level endpoints need a TRAINS Online account; "
          "this script only maps what is available.")


if __name__ == "__main__":
    main()
