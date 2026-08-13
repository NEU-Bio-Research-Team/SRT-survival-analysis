"""Step 6a: pull HS6 bilateral trade values from UN Comtrade.

The panel is built from the *importer's* filing (flowCode=M): a country that
reports its imports gives us, for every exporter and every HS6 line, the value
that crossed the border. Import-side reporting is the reliable side, which is
why the 53 importers were selected on their filing record.

The API caps a response at 100,000 records. Rather than guessing a safe batch
size, this script asks for all 82 exporters at once and splits the partner list
in half whenever a response comes back at exactly the cap (i.e. truncated).
Most importer-years fit in a single call.

Output: one gzipped CSV per importer-year in data_raw/trade/, keeping only the
columns the survival dataset needs. Re-running skips finished files.

Usage:
    python3 fetch_trade.py                 # everything
    python3 fetch_trade.py --importers USA,VNM --years 2018,2019
"""

import argparse
import csv
import gzip
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
SEL = os.path.join(HERE, "selection")
RAW = os.path.join(HERE, "data_raw", "trade")
API = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
REF = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"
RECORD_CAP = 100000
# Asking for all 82 exporters at once produces a ~90 MB response that takes ~110s
# and silently comes back empty often enough to be untrustworthy. Batches of 20
# stay well under the cap (~50k records for the largest importer-year) and each
# response arrives in well under a minute.
PARTNER_BATCH = 20
SLEEP = 2.0
YEARS = list(range(2002, 2022))

COLS = ["year", "importer", "importer_code", "exporter", "exporter_code",
        "hs6", "import_value_usd", "cif_value", "fob_value", "net_weight_kg",
        "hs_revision"]


def load_key():
    with open(os.path.join(HERE, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("COMTRADE_PRIMARY_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("COMTRADE_PRIMARY_KEY not found in .env")


KEY = load_key()


def fetch_json(url, timeout=900, retries=4):
    for attempt in range(retries):
        req = urllib.request.Request(
            url, headers={"Ocp-Apim-Subscription-Key": KEY,
                          "User-Agent": "trade-survival-research/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            # 429 = rate limited, 5xx = transient: back off and retry
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                # 429 here is a short-window throttle, not a daily quota:
                # a 20s pause clears it, and retries are cheap
                wait = 20 if e.code == 429 else 15 * (attempt + 1)
                print(f"    http {e.code}, waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            print(f"    http {e.code} (giving up)", flush=True)
            return None
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(15 * (attempt + 1))
                continue
            print(f"    {type(exc).__name__} (giving up)", flush=True)
            return None
    return None


def country_codes():
    """iso3 -> current Comtrade numeric code.

    The reference table carries historical entities under the same ISO3 code
    (USA appears as 840, 841 "USA and Puerto Rico (...1980)" and 842; Germany
    as 280 "Fed. Rep. of Germany (...1990)" and 276). Taking whatever comes
    last silently substitutes a defunct code and the API then returns zero
    rows. Keep only unexpired, non-group entries and prefer the one that came
    into effect most recently - that is the code Comtrade files data under
    today (USA 842, Germany 276, Viet Nam 704, Serbia 688).
    """
    data = fetch_json(REF)["results"]
    best = {}
    for r in data:
        iso = r.get("PartnerCodeIsoAlpha3") or r.get("partnerCodeIsoAlpha3")
        if not iso or len(iso) != 3 or r.get("isGroup"):
            continue
        if r.get("entryExpiredDate"):
            continue
        eff = r.get("entryEffectiveDate") or ""
        if iso not in best or eff > best[iso][0]:
            best[iso] = (eff, r["PartnerCode"])
    return {iso: code for iso, (_, code) in best.items()}


def pull_batch(importer_code, year, partner_codes, retry_empty=True):
    """One request; splits if the cap is hit, retries once if oddly empty."""
    batch = ",".join(str(c) for c in partner_codes)
    url = (f"{API}?reporterCode={importer_code}&period={year}"
           f"&partnerCode={batch}&cmdCode=AG6&flowCode=M&includeDesc=false")
    body = fetch_json(url)
    time.sleep(SLEEP)
    if body is None:
        return None
    rows = body.get("data") or []
    if len(rows) >= RECORD_CAP and len(partner_codes) > 1:
        mid = len(partner_codes) // 2
        print(f"    hit {RECORD_CAP} cap, splitting {len(partner_codes)} "
              f"partners", flush=True)
        left = pull_batch(importer_code, year, partner_codes[:mid])
        right = pull_batch(importer_code, year, partner_codes[mid:])
        if left is None or right is None:
            return None
        return left + right
    if not rows and retry_empty and len(partner_codes) > 1:
        # a large request occasionally returns an empty body instead of an
        # error; one retry distinguishes that from a genuinely empty cell
        time.sleep(20)
        return pull_batch(importer_code, year, partner_codes, retry_empty=False)
    return rows


def pull(importer_code, year, partner_codes):
    """All exporters for one importer-year, in fixed batches."""
    all_rows = []
    for i in range(0, len(partner_codes), PARTNER_BATCH):
        got = pull_batch(importer_code, year,
                         partner_codes[i:i + PARTNER_BATCH])
        if got is None:
            return None
        all_rows.extend(got)
    return all_rows


def tidy(rows, importer_iso, code_to_iso):
    out = []
    for r in rows:
        cmd = r.get("cmdCode")
        if not cmd or len(cmd) != 6 or cmd == "999999":
            continue                     # drop the not-classified aggregate
        out.append({
            "year": r.get("refYear"),
            "importer": importer_iso,
            "importer_code": r.get("reporterCode"),
            "exporter": code_to_iso.get(r.get("partnerCode"), ""),
            "exporter_code": r.get("partnerCode"),
            "hs6": cmd,
            "import_value_usd": r.get("primaryValue"),
            "cif_value": r.get("cifvalue"),
            "fob_value": r.get("fobvalue"),
            "net_weight_kg": r.get("netWgt"),
            "hs_revision": r.get("classificationCode"),
        })
    return out


def save(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with gzip.open(tmp, "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)                # only a complete file appears on disk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--importers", default="")
    ap.add_argument("--years", default="")
    args = ap.parse_args()

    importers = [r["iso3"] for r in csv.DictReader(
        open(os.path.join(SEL, "importers_selected.csv"), encoding="utf-8"))]
    exporters = [r["iso3"] for r in csv.DictReader(
        open(os.path.join(SEL, "exporters_selected.csv"), encoding="utf-8"))]
    years = YEARS
    if args.importers:
        importers = args.importers.split(",")
    if args.years:
        years = [int(y) for y in args.years.split(",")]

    codes = country_codes()
    missing = [c for c in importers + exporters if c not in codes]
    if missing:
        print(f"WARNING: no Comtrade code for {missing}")
    exporter_codes = [codes[e] for e in exporters if e in codes]
    code_to_iso = {codes[i]: i for i in set(importers + exporters) if i in codes}

    jobs = [(imp, y) for imp in importers for y in years]
    print(f"{len(importers)} importers x {len(years)} years = {len(jobs)} "
          f"importer-years, {len(exporter_codes)} exporters each\n")

    started = time.time()
    done = skipped = failed = 0
    consecutive_failures = 0
    total_rows = 0
    for i, (imp, year) in enumerate(jobs, 1):
        path = os.path.join(RAW, f"{imp}_{year}.csv.gz")
        if os.path.exists(path):
            skipped += 1
            continue
        if imp not in codes:
            failed += 1
            continue
        t0 = time.time()
        rows = pull(codes[imp], year, exporter_codes)
        clean = tidy(rows, imp, code_to_iso) if rows is not None else []
        if not clean:
            # never cache an empty importer-year: it is far more likely a
            # throttled response than a country importing nothing all year
            failed += 1
            consecutive_failures += 1
            print(f"[{i}/{len(jobs)}] {imp} {year}: no data, not cached",
                  flush=True)
            if consecutive_failures >= 5:
                # the daily quota is the usual cause; stop instead of burning
                # through the remaining jobs marking everything failed
                print("\nStopping: 5 importer-years failed in a row. Likely the "
                      "API quota. Re-run later - finished files are kept.")
                break
            continue
        consecutive_failures = 0
        save(path, clean)
        done += 1
        total_rows += len(clean)
        elapsed = time.time() - started
        rate = elapsed / max(done, 1)
        left = (len(jobs) - i) * rate / 3600
        print(f"[{i}/{len(jobs)}] {imp} {year}: {len(clean):,} rows "
              f"({time.time() - t0:.0f}s) | total {total_rows:,} | "
              f"~{left:.1f}h left", flush=True)

    print(f"\nDone: {done} pulled, {skipped} cached, {failed} failed, "
          f"{total_rows:,} rows")


if __name__ == "__main__":
    main()
