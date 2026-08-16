"""Step 6a: pull HS6 trade values from UN Comtrade for the Viet Nam design.

The exporter is fixed to **Viet Nam**; the importers are the countries listed in
selection/importers_vn.csv. That turns the old "every importer x 82 exporters"
pull (~1,060 heavy files) into three cheap passes:

  vn      importer's own filing of its imports *from Viet Nam*, at HS6.
          This is the panel itself. Import-side reporting is the reliable side,
          which is why importers were screened on their filing record.
  world   the same importer's imports *from the world*, at HS6. Needed for the
          denominators: Balassa RCA, world growth, and Viet Nam's penetration
          share inside each importer-product market. Heavier than the vn pass -
          about 5,000 HS6 lines per importer-year - so it runs separately.
  mirror  Viet Nam's own export filing towards the same importers. Not used to
          build spells; kept as the mirror check on the importer-side numbers.

Years are requested five at a time and the response is split back into one file
per importer-year, so a run stays resumable at the same granularity as before.

Files already on disk are skipped. The 119 files pulled under the old design are
kept as-is: they were pulled with Viet Nam among the partners, so they already
contain the rows this design needs.

Output: data_raw/trade/, data_raw/trade_world/, data_raw/trade_mirror/

Usage:
    python3 fetch_trade.py                       # vn pass, all importers
    python3 fetch_trade.py --pass world
    python3 fetch_trade.py --pass mirror
    python3 fetch_trade.py --importers USA,DEU --years 2018,2019
"""

import argparse
import csv
import gzip
import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án
SEL = os.path.join(HERE, "selection")
RAW = os.path.join(HERE, "data_raw", "trade")
RAW_WORLD = os.path.join(HERE, "data_raw", "trade_world")
RAW_MIRROR = os.path.join(HERE, "data_raw", "trade_mirror")
API = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
REF = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"
RECORD_CAP = 100000
# consolidated row only: all customs procedures, all transport modes, no
# second-partner split. Without it a reporter can return ~20 rows per HS6 line.
AGGREGATE = "customsCode=C00&motCode=0&partner2Code=0"
YEAR_BATCH = 5           # 5 years of one importer stays well under the cap
MIRROR_PARTNER_BATCH = 20
SLEEP = 2.0
YEARS = list(range(2002, 2022))

VN_ISO = "VNM"
VN_CODE = 704

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


class QuotaExhausted(RuntimeError):
    """Comtrade's daily call volume is spent; it replenishes on its own clock."""


def fetch_json(url, timeout=900, retries=4):
    for attempt in range(retries):
        req = urllib.request.Request(
            url, headers={"Ocp-Apim-Subscription-Key": KEY,
                          "User-Agent": "trade-survival-research/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 403:
                # the daily call quota, not a throttle. Every later request will
                # fail the same way, so say when it comes back and stop the run
                # instead of marking hundreds of importer-years "failed".
                body = e.read().decode("utf-8", "replace")
                raise QuotaExhausted(body.strip())
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


def request(reporter, period, partner):
    """One Comtrade call; None on failure, list of raw rows otherwise.

    Some reporters (Germany is the clearest case) return the same HS6 line
    split by customs procedure, mode of transport and second partner - about
    twenty rows where one is meant. Summing those would multiply the trade
    value, and the extra rows push a four-year request past the 100,000 cap.
    AGGREGATE pins the request to the single consolidated row per HS6 line.
    """
    url = (f"{API}?reporterCode={reporter}&period={period}"
           f"&partnerCode={partner}&cmdCode=AG6&flowCode="
           f"{'X' if reporter == VN_CODE else 'M'}&includeDesc=false"
           f"&{AGGREGATE}")
    body = fetch_json(url)
    time.sleep(SLEEP)
    if body is None:
        return None
    rows = body.get("data") or []
    if len(rows) >= RECORD_CAP:
        # a truncated response would silently lose HS6 lines: split the period
        years = period.split(",")
        if len(years) == 1:
            print(f"    hit the {RECORD_CAP} cap on a single year "
                  f"({reporter}/{period}) - cannot split further", flush=True)
            return None
        print(f"    hit the {RECORD_CAP} cap for {reporter}/{period}, "
              f"splitting", flush=True)
        mid = len(years) // 2
        left = request(reporter, ",".join(years[:mid]), partner)
        right = request(reporter, ",".join(years[mid:]), partner)
        if left is None or right is None:
            return None
        return left + right
    return rows


def tidy(rows, code_to_iso, importer_iso=None):
    """Raw API rows -> the columns the survival dataset needs.

    `importer_iso` is set when the reporter is the importer. On the mirror pass
    Viet Nam is the reporter, so the importer is read from the partner field.
    """
    out = []
    for r in rows:
        cmd = r.get("cmdCode")
        if not cmd or len(cmd) != 6 or cmd == "999999":
            continue                     # drop the not-classified aggregate
        if (r.get("customsCode") or "C00").strip() != "C00" \
                or (r.get("motCode") or 0) != 0 \
                or (r.get("partner2Code") or 0) != 0:
            continue                     # guard: only the consolidated row
        if importer_iso is not None:
            imp, imp_code = importer_iso, r.get("reporterCode")
            exp, exp_code = VN_ISO, r.get("partnerCode")
            if r.get("partnerCode") == 0:
                exp, exp_code = "WLD", 0
        else:
            imp = code_to_iso.get(r.get("partnerCode"), "")
            imp_code = r.get("partnerCode")
            exp, exp_code = VN_ISO, r.get("reporterCode")
        out.append({
            "year": r.get("refYear"),
            "importer": imp,
            "importer_code": imp_code,
            "exporter": exp,
            "exporter_code": exp_code,
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


def by_year(rows):
    out = defaultdict(list)
    for r in rows:
        out[int(r["year"])].append(r)
    return out


def importer_pass(importers, years, codes, code_to_iso, partner, outdir, label):
    """One file per importer-year, requested in batches of years."""
    jobs = [(imp, years[i:i + YEAR_BATCH])
            for imp in importers
            for i in range(0, len(years), YEAR_BATCH)]
    started = time.time()
    done = skipped = failed = empty = 0
    total_rows = 0
    for n, (imp, yb) in enumerate(jobs, 1):
        want = [y for y in yb
                if not os.path.exists(os.path.join(outdir, f"{imp}_{y}.csv.gz"))]
        if not want:
            skipped += len(yb)
            continue
        if imp not in codes:
            print(f"[{n}/{len(jobs)}] {imp}: no Comtrade code, skipped")
            failed += len(want)
            continue
        t0 = time.time()
        rows = request(codes[imp], ",".join(str(y) for y in want), partner)
        if rows is None:
            failed += len(want)
            print(f"[{n}/{len(jobs)}] {label} {imp} {want}: request failed",
                  flush=True)
            continue
        clean = tidy(rows, code_to_iso, importer_iso=imp)
        grouped = by_year(clean)
        for y in want:
            got = grouped.get(y, [])
            if not got:
                # never cache an empty importer-year: far more likely a
                # throttled response than a year with no trade at all
                empty += 1
                continue
            save(os.path.join(outdir, f"{imp}_{y}.csv.gz"), got)
            done += 1
            total_rows += len(got)
        elapsed = time.time() - started
        left = (len(jobs) - n) * (elapsed / n) / 3600
        print(f"[{n}/{len(jobs)}] {label} {imp} {want[0]}-{want[-1]}: "
              f"{len(clean):,} rows ({time.time() - t0:.0f}s) | "
              f"total {total_rows:,} | ~{left:.1f}h left", flush=True)

    print(f"\n{label} pass: {done} importer-years written, {skipped} cached, "
          f"{empty} came back empty, {failed} failed, {total_rows:,} rows")


def mirror_pass(importers, years, codes, code_to_iso):
    """Viet Nam's own export filing, one file per partner batch and year batch."""
    targets = [codes[i] for i in importers if i in codes]
    batches = [targets[i:i + MIRROR_PARTNER_BATCH]
               for i in range(0, len(targets), MIRROR_PARTNER_BATCH)]
    year_batches = [years[i:i + YEAR_BATCH]
                    for i in range(0, len(years), YEAR_BATCH)]
    done = skipped = failed = 0
    total_rows = 0
    n = 0
    for b, batch in enumerate(batches):
        for yb in year_batches:
            n += 1
            name = f"vnx_b{b:02d}_{yb[0]}-{yb[-1]}.csv.gz"
            path = os.path.join(RAW_MIRROR, name)
            if os.path.exists(path):
                skipped += 1
                continue
            rows = request(VN_CODE, ",".join(str(y) for y in yb),
                           ",".join(str(c) for c in batch))
            if rows is None:
                failed += 1
                print(f"[{n}] mirror {name}: request failed", flush=True)
                continue
            clean = tidy(rows, code_to_iso)
            save(path, clean)
            done += 1
            total_rows += len(clean)
            print(f"[{n}] mirror {name}: {len(clean):,} rows", flush=True)
    print(f"\nmirror pass: {done} files written, {skipped} cached, "
          f"{failed} failed, {total_rows:,} rows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="which", default="vn",
                    choices=["vn", "world", "mirror", "all"])
    ap.add_argument("--importers", default="")
    ap.add_argument("--years", default="")
    args = ap.parse_args()

    path = os.path.join(SEL, "importers_vn.csv")
    if not os.path.exists(path):
        raise SystemExit(f"{path} missing - run select_importers_vn.py first")
    with open(path, encoding="utf-8") as f:
        importers = [r["iso3"] for r in csv.DictReader(f)]
    years = YEARS
    if args.importers:
        importers = args.importers.split(",")
    if args.years:
        years = [int(y) for y in args.years.split(",")]

    codes = country_codes()
    missing = [c for c in importers if c not in codes]
    if missing:
        print(f"WARNING: no Comtrade code for {missing}")
    code_to_iso = {codes[i]: i for i in importers if i in codes}
    code_to_iso[VN_CODE] = VN_ISO

    print(f"Exporter: Viet Nam ({VN_CODE}) | importers: {len(importers)} | "
          f"years: {years[0]}-{years[-1]}\n")

    try:
        if args.which in ("vn", "all"):
            importer_pass(importers, years, codes, code_to_iso,
                          partner=VN_CODE, outdir=RAW, label="vn")
        if args.which in ("world", "all"):
            importer_pass(importers, years, codes, code_to_iso,
                          partner=0, outdir=RAW_WORLD, label="world")
        if args.which in ("mirror", "all"):
            mirror_pass(importers, years, codes, code_to_iso)
    except QuotaExhausted as e:
        print(f"\nStopped: {e}\nFinished files are kept; re-run when the quota "
              f"is back and it will pick up where it left off.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
