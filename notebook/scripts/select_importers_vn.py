"""Step 3-4 (Viet Nam design): fix the exporter to VNM and list every importer
that has enough information to be usable.

The earlier design compared 82 exporters across 53 hand-balanced importers. The
study now has a single exporter - **Viet Nam** - and the importer side is no
longer a quota: every country that can support the model is listed, and the
reason each one is in or out is written down.

A country qualifies as an importer when all three hold:

  1. it files annual HS data to UN Comtrade inside 2002-2021 (`getDA`), so its
     imports from Viet Nam exist at HS6;
  2. it has a tariff schedule in TRAINS (its own, or the EU common external
     tariff via `EUN`), so the Tariff covariate is not structurally missing;
  3. it actually reports importing from Viet Nam - screened here with one
     Comtrade call per reporter batch at `cmdCode=TOTAL`, so a country with a
     perfect filing record but no trade with Viet Nam does not enter the panel
     as an all-zero row.

Countries are then tiered rather than cut:

  A - full: 20/20 Comtrade years, >=15 tariff years, >=15 years of trade with VN
  B - usable: >=15 Comtrade years, >=10 tariff years, >=10 years of trade
  C - thin: reports trade with VN but fails A and B; kept in the candidate file
      with the reason, excluded from the panel list

Outputs in ./selection/:
  exporter_selected.csv  - one row: Viet Nam
  importers_vn.csv       - tier A + B, the panel's importer list
  importer_vn_all.csv    - every candidate with its numbers and its tier/reason
  vn_partner_screen.csv  - raw screen: imports from VN by reporter-year, both
                           sides of the mirror (importer-reported and VN-reported)

Usage:
    python3 select_importers_vn.py            # uses cached screen if present
    python3 select_importers_vn.py --refresh  # re-pulls the Comtrade screen
"""

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict

from select_countries import EU_ACCESSION, UK_EU_LAST_YEAR, YEARS

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án
SEL = os.path.join(HERE, "selection")
API = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
REF = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"

VN_ISO = "VNM"
VN_CODE = 704
REPORTER_BATCH = 20        # reporters per call; TOTAL rows stay far under the cap
# Several reporters return the same TOTAL split by customs procedure, transport
# mode and second partner. Summing those rows multiplies the trade value - it is
# what made Germany look like a larger buyer of Vietnamese goods than the United
# States - so the request is pinned to the single consolidated row.
AGGREGATE = "customsCode=C00&motCode=0&partner2Code=0"
YEAR_BATCH = 5
SLEEP = 1.5

# Tier thresholds: (min Comtrade years, min tariff years, min years trading with VN)
TIER_A = (20, 15, 15)
TIER_B = (15, 10, 10)


def load_key():
    with open(os.path.join(HERE, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("COMTRADE_PRIMARY_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("COMTRADE_PRIMARY_KEY not found in .env")


KEY = load_key()


def fetch_json(url, timeout=600, retries=4):
    for attempt in range(retries):
        req = urllib.request.Request(
            url, headers={"Ocp-Apim-Subscription-Key": KEY,
                          "User-Agent": "trade-survival-research/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(20 if e.code == 429 else 15 * (attempt + 1))
                continue
            print(f"    http {e.code} (giving up)", flush=True)
            return None
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
                continue
            print(f"    {type(exc).__name__} (giving up)", flush=True)
            return None
    return None


def country_codes():
    """iso3 -> current Comtrade numeric code (same rule as fetch_trade.py)."""
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


def read_csv(name):
    path = os.path.join(SEL, name)
    if not os.path.exists(path):
        raise SystemExit(f"{path} missing - run select_countries.py first")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(name, rows, cols):
    os.makedirs(SEL, exist_ok=True)
    with open(os.path.join(SEL, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote selection/{name} ({len(rows):,} rows)")


# --- availability, recomputed from the raw dumps ----------------------------
def availability():
    """iso3 -> (Comtrade years filed, tariff years available)."""
    da_years = defaultdict(set)
    records = defaultdict(int)
    for r in read_csv("comtrade_da.csv"):
        if r["iso3"] and int(r["year"]) in YEARS:
            da_years[r["iso3"]].add(int(r["year"]))
            records[r["iso3"]] += int(r["total_records"] or 0)

    trains_years = defaultdict(set)
    for r in read_csv("trains_avail.csv"):
        trains_years[r["iso3"]].add(int(r["year"]))
    # TRAINS files the EU common external tariff once under EUN; without this
    # every member state would show zero tariff years of its own.
    eun = trains_years.get("EUN", set())
    for iso, since in EU_ACCESSION.items():
        trains_years[iso] |= {y for y in eun if y >= since}
    trains_years["GBR"] |= {y for y in eun if y <= UK_EU_LAST_YEAR}
    return da_years, trains_years, records


# --- Comtrade screen: who trades with Viet Nam ------------------------------
def aggregate_total_rows(rows, key_reporter=True):
    """(code, year) -> total trade value, from the consolidated rows only."""
    out = defaultdict(float)
    for r in rows:
        if (r.get("customsCode") or "C00").strip() != "C00" \
                or (r.get("motCode") or 0) != 0 \
                or (r.get("partner2Code") or 0) != 0:
            continue
        code = r.get("reporterCode") if key_reporter else r.get("partnerCode")
        year = r.get("refYear")
        val = r.get("primaryValue")
        if code is None or year is None or not val:
            continue
        out[(int(code), int(year))] += float(val)
    return out


def screen(codes, iso_list):
    """Both sides of the mirror, keyed (iso3, year) -> value in USD."""
    code_of = {i: codes[i] for i in iso_list if i in codes}
    iso_of = {c: i for i, c in code_of.items()}
    importer_side, vn_side = {}, {}

    targets = sorted(code_of.values())
    batches = [targets[i:i + REPORTER_BATCH]
               for i in range(0, len(targets), REPORTER_BATCH)]
    year_batches = [YEARS[i:i + YEAR_BATCH]
                    for i in range(0, len(YEARS), YEAR_BATCH)]
    total = len(batches) * len(year_batches)
    n = 0
    for yb in year_batches:
        period = ",".join(str(y) for y in yb)
        for batch in batches:
            n += 1
            rep = ",".join(str(c) for c in batch)
            # side 1: the importer's own filing of what it bought from Viet Nam
            body = fetch_json(f"{API}?reporterCode={rep}&period={period}"
                              f"&partnerCode={VN_CODE}&cmdCode=TOTAL"
                              f"&flowCode=M&includeDesc=false"
                              f"&{AGGREGATE}")
            got = aggregate_total_rows((body or {}).get("data") or [])
            for (code, year), v in got.items():
                if code in iso_of:
                    importer_side[(iso_of[code], year)] = v
            time.sleep(SLEEP)
            # side 2: Viet Nam's own filing of what it sold to them
            body = fetch_json(f"{API}?reporterCode={VN_CODE}&period={period}"
                              f"&partnerCode={rep}&cmdCode=TOTAL"
                              f"&flowCode=X&includeDesc=false"
                              f"&{AGGREGATE}")
            got = aggregate_total_rows((body or {}).get("data") or [],
                                       key_reporter=False)
            for (code, year), v in got.items():
                if code in iso_of:
                    vn_side[(iso_of[code], year)] = v
            time.sleep(SLEEP)
            print(f"  screen {n}/{total}: {period} x {len(batch)} reporters "
                  f"-> {len(importer_side):,} importer-year cells", flush=True)

    rows = []
    for key in sorted(set(importer_side) | set(vn_side)):
        iso, year = key
        rows.append({"iso3": iso, "year": year,
                     "imports_from_vn_usd": round(importer_side.get(key, 0), 2),
                     "vn_reported_exports_usd": round(vn_side.get(key, 0), 2)})
    write_csv("vn_partner_screen.csv", rows,
              ["iso3", "year", "imports_from_vn_usd", "vn_reported_exports_usd"])
    return rows


def load_screen():
    path = os.path.join(SEL, "vn_partner_screen.csv")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --- tiering ----------------------------------------------------------------
def tier_of(comtrade_years, tariff_years, vn_years):
    got = (comtrade_years, tariff_years, vn_years)
    if all(g >= t for g, t in zip(got, TIER_A)):
        return "A", "full: 20 filing years, tariff and VN trade throughout"
    if all(g >= t for g, t in zip(got, TIER_B)):
        return "B", "usable: filing/tariff/VN-trade coverage has gaps"
    reasons = []
    if comtrade_years < TIER_B[0]:
        reasons.append(f"only {comtrade_years} Comtrade years")
    if tariff_years < TIER_B[1]:
        reasons.append(f"only {tariff_years} tariff years")
    if vn_years < TIER_B[2]:
        reasons.append(f"only {vn_years} years trading with VN")
    return "C", "thin: " + ", ".join(reasons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="re-pull the Comtrade screen instead of using the cache")
    args = ap.parse_args()

    meta = {m["iso3"]: m for m in read_csv("country_meta.csv")}
    da_years, trains_years, records = availability()

    # candidates: anything the World Bank calls a country and Comtrade knows
    iso_list = sorted(i for i in da_years if i in meta and i != VN_ISO)
    print(f"Candidate reporters with any Comtrade filing: {len(iso_list)}")

    cached = None if args.refresh else load_screen()
    if cached is None:
        print("Screening Comtrade for trade with Viet Nam "
              f"({len(iso_list)} reporters x {len(YEARS)} years)")
        codes = country_codes()
        cached = screen(codes, iso_list)
    else:
        print(f"Using cached screen ({len(cached):,} rows) - "
              f"pass --refresh to re-pull")

    vn_years = defaultdict(int)
    vn_value = defaultdict(float)
    vn_latest = {}
    vn_mirror = defaultdict(int)
    for r in cached:
        iso, year = r["iso3"], int(r["year"])
        imp_val = float(r["imports_from_vn_usd"] or 0)
        vn_val = float(r["vn_reported_exports_usd"] or 0)
        if imp_val > 0:
            vn_years[iso] += 1
            vn_value[iso] += imp_val
            if iso not in vn_latest or year > vn_latest[iso][0]:
                vn_latest[iso] = (year, imp_val)
        if vn_val > 0:
            vn_mirror[iso] += 1

    rows = []
    for iso in iso_list:
        cy = len(da_years.get(iso, ()))
        ty = len(trains_years.get(iso, ()))
        vy = vn_years.get(iso, 0)
        tier, reason = tier_of(cy, ty, vy)
        rows.append({
            "iso3": iso,
            "name": meta[iso]["name"],
            "income_group": meta[iso]["income_group"],
            "region": meta[iso]["region"],
            "comtrade_years": cy,
            "tariff_years": ty,
            "vn_trade_years": vy,
            "vn_mirror_years": vn_mirror.get(iso, 0),
            "vn_imports_latest_year": vn_latest.get(iso, ("", ""))[0],
            "vn_imports_latest_usd": round(vn_latest.get(iso, ("", 0))[1]),
            "vn_imports_mean_usd": round(vn_value.get(iso, 0) / vy) if vy else 0,
            "avg_records_per_year": round(records[iso] / max(cy, 1)),
            "tier": tier,
            "reason": reason,
        })

    rows.sort(key=lambda r: (r["tier"], -r["vn_imports_mean_usd"]))
    cols = ["iso3", "name", "income_group", "region", "comtrade_years",
            "tariff_years", "vn_trade_years", "vn_mirror_years",
            "vn_imports_latest_year", "vn_imports_latest_usd",
            "vn_imports_mean_usd", "avg_records_per_year", "tier", "reason"]
    write_csv("importer_vn_all.csv", rows, cols)
    panel = [r for r in rows if r["tier"] in ("A", "B")]
    write_csv("importers_vn.csv", panel, cols)

    vn_meta = meta.get(VN_ISO, {"name": "Viet Nam", "region": "",
                                "income_group": ""})
    write_csv("exporter_selected.csv", [{
        "iso3": VN_ISO, "name": vn_meta["name"],
        "income_group": vn_meta["income_group"], "region": vn_meta["region"],
        "comtrade_code": VN_CODE,
        "files_own_data_years": len(da_years.get(VN_ISO, ())),
    }], ["iso3", "name", "income_group", "region", "comtrade_code",
         "files_own_data_years"])

    by_tier = defaultdict(list)
    for r in rows:
        by_tier[r["tier"]].append(r)
    print(f"\nExporter: Viet Nam only")
    for t in ("A", "B", "C"):
        n = len(by_tier[t])
        print(f"Tier {t}: {n:>3} countries")
    print(f"Importers in the panel (A+B): {len(panel)}")
    dist = defaultdict(int)
    for r in panel:
        dist[r["income_group"]] += 1
    for g, n in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {g:<22} {n}")


if __name__ == "__main__":
    main()
