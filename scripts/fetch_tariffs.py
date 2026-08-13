"""Step 5: pull HS6 tariffs from WITS/TRAINS for the selected importers.

Two passes:
  A. MFN   - one call per (tariff reporter, year) with product=ALL, partner=000.
             ~1,060 calls, each returning the country's whole HS6 schedule.
  B. PREF  - preferential schedules. Instead of trying every importer-exporter
             pair (86,920 calls), the TRAINS `dataavailability` response lists,
             per reporter-year, exactly which partners have a schedule
             (`partnerlist`). Only those are requested.

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
YEARS = list(range(2002, 2022))

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


def load_targets():
    """(iso3, tariff reporter numeric code) for every selected importer."""
    imp = list(csv.DictReader(open(os.path.join(SEL, "importers_selected.csv"),
                                   encoding="utf-8")))
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
    if os.path.exists(cache):
        for r in csv.DictReader(open(cache, encoding="utf-8")):
            out[r["reporter"]][int(r["year"])] = [p for p in r["partners"].split(";") if p]
        return out
    os.makedirs(RAW, exist_ok=True)
    rows = []
    ns = "{http://wits.worldbank.org}"
    for i, code in enumerate(sorted(set(codes)), 1):
        status, payload = fetch(
            f"{WITS}/wits/datasource/trn/dataavailability/country/{code}/year/ALL")
        if status == 200 and payload:
            root = ET.fromstring(payload)
            for rep in root.iter(f"{ns}reporter"):
                y = rep.findtext(f"{ns}year")
                pl = rep.findtext(f"{ns}partnerlist") or ""
                if y and int(y) in YEARS:
                    partners = [p for p in pl.split(";") if p]
                    out[code][int(y)] = partners
                    rows.append({"reporter": code, "year": y,
                                 "partners": ";".join(partners)})
        print(f"  availability {i}/{len(set(codes))}: {code} "
              f"({len(out[code])} years)", flush=True)
        time.sleep(SLEEP)
    with open(cache, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["reporter", "year", "partners"])
        w.writeheader()
        w.writerows(rows)
    return out


def pass_mfn(targets):
    done = skipped = failed = 0
    total = len(targets)
    for i, (iso, code, year) in enumerate(targets, 1):
        path = os.path.join(RAW, "mfn", f"{iso}_{year}.csv.gz")
        if os.path.exists(path):
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
            print(f"[{i}/{total}] MFN {iso} {year}: no data (http {status})",
                  flush=True)
        time.sleep(SLEEP)
    print(f"\nMFN pass: {done} downloaded, {skipped} already on disk, "
          f"{failed} without data")


def pass_pref(targets):
    codes = {code for _, code, _ in targets}
    print("Reading TRAINS partner lists...")
    lists = availability_partnerlists(codes)

    jobs = []
    for iso, code, year in targets:
        for p in lists.get(code, {}).get(year, []):
            if p != "000":                      # 000 is MFN, done in pass A
                jobs.append((iso, code, year, p))
    print(f"Preferential schedules to pull: {len(jobs)} "
          f"(vs {len(targets) * 82} if every pair were tried)\n")

    done = skipped = failed = 0
    for i, (iso, code, year, partner) in enumerate(jobs, 1):
        path = os.path.join(RAW, "pref", f"{iso}_{year}_{partner}.csv.gz")
        if os.path.exists(path):
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
        time.sleep(SLEEP)
    print(f"\nPREF pass: {done} downloaded, {skipped} already on disk, "
          f"{failed} without data")


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
