"""Step 5: pull HS6 tariffs from WITS/TRAINS for the selected importers.

The exporter is Viet Nam, so the tariff that matters is the one each importer
levies on Vietnamese goods. Two passes:

  A. MFN   - one call per (tariff reporter, year) with product=ALL, partner=000.
             Each call returns the country's whole HS6 schedule.
  B. PREF  - the preferential schedule the importer grants **Viet Nam**
             (TRAINS partner code 704). The `dataavailability` response lists,
             per reporter-year, which partners have a schedule (`partnerlist`);
             only reporter-years that actually list Viet Nam are requested, so
             the pass is a few hundred calls instead of thousands.

Caveat that survives this pass: an importer can grant Viet Nam a rate through an
agreement filed under a *group* code (ASEAN, AANZFTA, RCEP) rather than under
704. Those rows are not fetched here - the group-to-member mapping is not in the
API - so such an episode falls back to MFN, which overstates the rate faced.
`tariff_type` marks which of the two applied.

Everything is cached as gzipped CSV under data_raw/tariffs/, so the run is
resumable: re-running skips whatever is already on disk.

Usage:
    python3 fetch_tariffs.py --pass mfn
    python3 fetch_tariffs.py --pass pref
    python3 fetch_tariffs.py --pass all
"""

import argparse
import csv
import gzip
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
SEL = os.path.join(HERE, "selection")
RAW = os.path.join(HERE, "data_raw", "tariffs")
WITS = "https://wits.worldbank.org/API/V1"
UA = "Mozilla/5.0 (compatible; trade-survival-research/1.0)"
SLEEP = 0.8                     # polite gap between calls
# 2023, not 2021: TRAINS answers with real schedules for 2022 and 2023 (checked
# 22/08/2026 against USA, EU and China - every one carries its own
# TIME_PERIOD, not a fallback to an earlier year), and 2024 is still a 404.
# Left at 2021 the last two panel years carried a 2021 rate forward, so the
# tail of the window had no real tariff variation at all.
YEARS = list(range(2002, 2024))
VN_TRAINS_CODE = "704"          # Viet Nam, the only exporter in this design

# A 404 from TRAINS is definitive - the reporter filed no schedule that year -
# and 224 reporter-years answer that way. Without a record of it, every restart
# pays for all of them again, which on a flaky connection is most of the run.
# Delete data_raw/tariffs/_no_schedule.csv to ask again after TRAINS updates.
NO_DATA = "_no_schedule.csv"

COLS = ["reporter", "partner", "year", "product", "tariff_type", "rate_simple_avg",
        "min_rate", "max_rate", "total_lines", "nbr_mfn_lines", "nbr_pref_lines",
        "nomen"]


def fetch(url, timeout=600, retries=4):
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 413, 400):        # no data / too big: definitive
                return e.code, b""
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return e.code, b""
        except Exception:
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return 0, b""
    return 0, b""


def parse_tariff(payload):
    root = ET.fromstring(payload)
    ns = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message}"
    rows = []
    for ds in root.iter(f"{ns}DataSet"):
        for series in ds:
            if not series.tag.endswith("Series"):
                continue
            s = series.attrib
            for obs in series:
                o = obs.attrib
                rows.append({
                    "reporter": s.get("REPORTER"), "partner": s.get("PARTNER"),
                    "year": o.get("TIME_PERIOD"), "product": s.get("PRODUCTCODE"),
                    "tariff_type": o.get("TARIFFTYPE"),
                    "rate_simple_avg": o.get("OBS_VALUE"),
                    "min_rate": o.get("MIN_RATE"), "max_rate": o.get("MAX_RATE"),
                    "total_lines": o.get("TOTALNOOFLINES"),
                    "nbr_mfn_lines": o.get("NBR_MFN_LINES"),
                    "nbr_pref_lines": o.get("NBR_PREF_LINES"),
                    "nomen": o.get("NOMENCODE"),
                })
    return rows


def save(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def load_no_data():
    """(pass, reporter iso, year, partner) that TRAINS has answered 404 for."""
    path = os.path.join(RAW, NO_DATA)
    seen = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                seen.add((r["pass"], r["reporter"], int(r["year"]),
                          r["partner"]))
    return seen


def record_no_data(which, iso, year, partner=""):
    path = os.path.join(RAW, NO_DATA)
    os.makedirs(RAW, exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pass", "reporter", "year",
                                          "partner"])
        if new:
            w.writeheader()
        w.writerow({"pass": which, "reporter": iso, "year": year,
                    "partner": partner})


def load_targets():
    """(iso3, tariff reporter numeric code) for every selected importer."""
    path = os.path.join(SEL, "importers_vn.csv")
    if not os.path.exists(path):
        raise SystemExit(f"{path} missing - run select_importers_vn.py first")
    imp = list(csv.DictReader(open(path, encoding="utf-8")))
    eu = {}
    p = os.path.join(SEL, "eu_tariff_mapping.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            eu[(r["iso3"], int(r["year"]))] = r["tariff_reporter"]
    # iso3 -> numeric code, from the TRAINS availability dump
    codes = {}
    for r in csv.DictReader(open(os.path.join(SEL, "trains_avail.csv"),
                                 encoding="utf-8")):
        codes[r["iso3"]] = r["code"]
    codes.setdefault("EUN", "918")
    targets = {}
    for row in imp:
        iso = row["iso3"]
        for y in YEARS:
            src = eu.get((iso, y), iso)
            code = codes.get(src)
            if code:
                targets[(src, code, y)] = True     # dedupe EU members onto EUN
    return sorted(targets), imp


def availability_partnerlists(codes):
    """reporter code -> {year: [partner codes with a schedule]}"""
    out = defaultdict(dict)
    cache = os.path.join(RAW, "_partnerlists.csv")
    # A cache written under a shorter YEARS is stale in a way "which reporters
    # are in it" cannot see: every reporter is present, but none carries the
    # years added afterwards, and each of those then looks like a reporter with
    # no preferential filing rather than one never asked. The availability call
    # is year/ALL, so one re-pull settles every year at once - and the marker
    # records which YEARS the rebuild was for, so a run interrupted halfway
    # resumes instead of truncating what it already fetched.
    marker = os.path.join(RAW, "_partnerlists_builtfor.txt")
    target = str(max(YEARS))
    built_for = ""
    if os.path.exists(marker):
        with open(marker, encoding="utf-8") as f:
            built_for = f.read().strip()
    os.makedirs(RAW, exist_ok=True)
    if os.path.exists(cache) and built_for != target:
        print(f"  partner lists were built for a window ending "
              f"{built_for or 'an earlier year'}; YEARS now runs to {target} - "
              f"re-pulling availability for all reporters")
        os.remove(cache)
        with open(marker, "w", encoding="utf-8") as f:
            f.write(target)

    seen = set()
    if os.path.exists(cache):
        for r in csv.DictReader(open(cache, encoding="utf-8")):
            out[r["reporter"]][int(r["year"])] = [p for p in r["partners"].split(";") if p]
            seen.add(r["reporter"])
    # the cache was built for an earlier, smaller reporter list: top it up
    # instead of either re-pulling everything or silently missing reporters
    todo = sorted(set(codes) - seen)
    if not todo:
        with open(marker, "w", encoding="utf-8") as f:
            f.write(target)
        return out
    ns = "{http://wits.worldbank.org}"
    for i, code in enumerate(todo, 1):
        status, payload = fetch(
            f"{WITS}/wits/datasource/trn/dataavailability/country/{code}/year/ALL")
        got = []
        if status == 200 and payload:
            root = ET.fromstring(payload)
            for rep in root.iter(f"{ns}reporter"):
                y = rep.findtext(f"{ns}year")
                pl = rep.findtext(f"{ns}partnerlist") or ""
                if y:
                    # keep every year the API returns, not just the ones this
                    # run needs - that is what made the cache go stale before
                    partners = [p for p in pl.split(";") if p]
                    out[code][int(y)] = partners
                    got.append({"reporter": code, "year": y,
                                "partners": ";".join(partners)})
        # Append per reporter rather than once at the end. This loop is 132 slow
        # calls and any interruption used to throw all of them away; written as
        # it goes, a restart picks up from the reporter it stopped on.
        fresh = not os.path.exists(cache)
        with open(cache, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["reporter", "year", "partners"])
            if fresh:
                w.writeheader()
            w.writerows(got)
        print(f"  availability {i}/{len(todo)}: {code} "
              f"({len(out[code])} years)", flush=True)
        time.sleep(SLEEP)
    with open(marker, "w", encoding="utf-8") as f:
        f.write(target)
    return out


def pass_mfn(targets):
    done = skipped = failed = 0
    known = load_no_data()
    total = len(targets)
    for i, (iso, code, year) in enumerate(targets, 1):
        path = os.path.join(RAW, "mfn", f"{iso}_{year}.csv.gz")
        if os.path.exists(path) or ("mfn", iso, year, "") in known:
            skipped += 1
            continue
        status, payload = fetch(f"{WITS}/SDMX/V21/datasource/TRN/reporter/{code}"
                                f"/partner/000/product/ALL/year/{year}"
                                f"/datatype/reported")
        if status == 200 and payload:
            rows = parse_tariff(payload)
            save(path, rows)
            done += 1
            print(f"[{i}/{total}] MFN {iso} {year}: {len(rows)} lines", flush=True)
        else:
            failed += 1
            # only a 404 is definitive; a timeout or a 5xx must be retried on
            # the next run, so it is deliberately not written down
            if status == 404:
                record_no_data("mfn", iso, year)
            print(f"[{i}/{total}] MFN {iso} {year}: no data (http {status})",
                  flush=True)
        time.sleep(SLEEP)
    print(f"\nMFN pass: {done} downloaded, {skipped} already on disk or known "
          f"absent, {failed} without data")


def pass_pref(targets):
    codes = {code for _, code, _ in targets}
    print("Reading TRAINS partner lists...")
    lists = availability_partnerlists(codes)

    jobs = []
    listed = skipped_no_vn = unknown = 0
    for iso, code, year in targets:
        partners = lists.get(code, {}).get(year)
        if partners and VN_TRAINS_CODE in partners:
            listed += 1
            jobs.append((iso, code, year, VN_TRAINS_CODE))
        elif partners:
            # the reporter filed preferential schedules that year, just not one
            # naming Viet Nam directly - it may still sit inside a group code
            skipped_no_vn += 1
        else:
            # no availability record at all: "unknown", not "known absent".
            # A 404 costs one cheap call and settles it, so ask rather than
            # assume - a stale partner list would silently lose real rates.
            unknown += 1
            jobs.append((iso, code, year, VN_TRAINS_CODE))
    print(f"Preferential calls to make: {len(jobs)} of {len(targets)} "
          f"reporter-years ({listed} list VNM explicitly, {unknown} have no "
          f"partner list to check); {skipped_no_vn} filed preferences for "
          f"other partners only\n")

    done = skipped = failed = 0
    known = load_no_data()
    for i, (iso, code, year, partner) in enumerate(jobs, 1):
        path = os.path.join(RAW, "pref", f"{iso}_{year}_{partner}.csv.gz")
        if os.path.exists(path) or ("pref", iso, year, partner) in known:
            skipped += 1
            continue
        status, payload = fetch(f"{WITS}/SDMX/V21/datasource/TRN/reporter/{code}"
                                f"/partner/{partner}/product/ALL/year/{year}"
                                f"/datatype/reported")
        if status == 200 and payload:
            rows = parse_tariff(payload)
            save(path, rows)
            done += 1
            if i % 25 == 0 or len(rows) > 0:
                print(f"[{i}/{len(jobs)}] PREF {iso} {year} <- {partner}: "
                      f"{len(rows)} lines", flush=True)
        else:
            failed += 1
            if status == 404:
                record_no_data("pref", iso, year, partner)
        time.sleep(SLEEP)
    print(f"\nPREF pass: {done} downloaded, {skipped} already on disk or known "
          f"absent, {failed} without data")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="which", default="all",
                    choices=["mfn", "pref", "all"])
    args = ap.parse_args()

    targets, importers = load_targets()
    print(f"{len(importers)} importers -> {len(targets)} distinct "
          f"(tariff reporter, year) pairs after EU consolidation\n")

    if args.which in ("mfn", "all"):
        pass_mfn(targets)
    if args.which in ("pref", "all"):
        pass_pref(targets)


if __name__ == "__main__":
    sys.exit(main())
