"""Step 3-4: pick the 53 importers and 82 exporters from data, not by hand.

Three availability sources are joined:
  1. UN Comtrade `getDA`  - which reporter actually filed annual HS data, per year.
     This is the binding criterion for importers: a country that never filed
     cannot contribute import observations.
  2. WITS TRAINS `dataavailability` - which country has a tariff schedule, per
     year. Importers without tariffs would leave the Tariff covariate missing.
  3. World Bank API - income group and region, so the 53 importers span
     low / lower-middle / upper-middle / high income as the design requires.

Exporters are ranked by merchandise export value (WDI TX.VAL.MRCH.CD.WT),
because exporters enter the panel as *partners* in the importers' filings and
therefore do not need to report anything themselves.

Outputs land in ./selection/.
"""

import csv
import json
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
OUT = os.path.join(HERE, "selection")
# 20-year window. Upper bound is set by TRAINS: 2022 and 2023 have zero
# countries with a tariff schedule, so the panel would lose the Tariff
# covariate entirely in those years. Lower bound follows from 20 years back.
YEARS = list(range(2002, 2022))
MIN_YEARS_IMPORTER = 20                  # must file every year of the window
N_IMPORTERS = 53
N_EXPORTERS = 82

# TRAINS files the common external tariff once, under EUN (code 918); every
# member state shows zero tariff years of its own. Without this mapping the
# whole EU market drops out of the importer pool. Values are the first year
# the country is inside the customs union, within our window.
EU_ACCESSION = {
    "AUT": 2002, "BEL": 2002, "DNK": 2002, "FIN": 2002, "FRA": 2002,
    "DEU": 2002, "GRC": 2002, "IRL": 2002, "ITA": 2002, "LUX": 2002,
    "NLD": 2002, "PRT": 2002, "ESP": 2002, "SWE": 2002,
    "CYP": 2004, "CZE": 2004, "EST": 2004, "HUN": 2004, "LVA": 2004,
    "LTU": 2004, "MLT": 2004, "POL": 2004, "SVK": 2004, "SVN": 2004,
    "BGR": 2007, "ROU": 2007, "HRV": 2013,
}
# The UK applied the EU tariff through the end of the 2020 transition and its
# own schedule from 2021.
UK_EU_LAST_YEAR = 2020

COMTRADE = "https://comtradeapi.un.org/data/v1"
WITS = "https://wits.worldbank.org/API/V1"
WB = "https://api.worldbank.org/v2"


def load_key():
    path = os.path.join(HERE, ".env")
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("COMTRADE_PRIMARY_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("COMTRADE_PRIMARY_KEY not found in .env")


KEY = load_key()


UA = "Mozilla/5.0 (compatible; trade-survival-research/1.0)"


def fetch(url, headers=None, timeout=300, retries=3):
    hdrs = {"User-Agent": UA}          # WITS returns 403 without a User-Agent
    hdrs.update(headers or {})
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            raise
    return b""


def write_csv(name, rows, cols):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# --- 1. Comtrade: who filed annual HS data, and how big is it ---------------
def comtrade_availability():
    rows = []
    for i in range(0, len(YEARS), 5):
        chunk = ",".join(str(y) for y in YEARS[i:i + 5])
        payload = fetch(f"{COMTRADE}/getDA/C/A/HS?period={chunk}",
                        {"Ocp-Apim-Subscription-Key": KEY})
        data = json.loads(payload).get("data") or []
        for r in data:
            rows.append({"iso3": r.get("reporterISO"), "code": r.get("reporterCode"),
                         "name": r.get("reporterDesc"), "year": r.get("period"),
                         "classification": r.get("classificationCode"),
                         "total_records": r.get("totalRecords")})
        print(f"  Comtrade DA {chunk}: {len(data)} reporter-years")
        time.sleep(1)
    write_csv("comtrade_da.csv", rows,
              ["iso3", "code", "name", "year", "classification", "total_records"])
    return rows


# --- 2. TRAINS: who has a tariff schedule ----------------------------------
def trains_availability():
    rows = []
    for y in YEARS:
        payload = fetch(f"{WITS}/wits/datasource/trn/dataavailability/country/ALL/year/{y}")
        root = ET.fromstring(payload)
        ns = "{http://wits.worldbank.org}"
        seen = set()
        for rep in root.iter(f"{ns}reporter"):
            iso = rep.attrib.get("iso3Code")
            if iso and iso not in seen:
                seen.add(iso)
                rows.append({"iso3": iso, "code": rep.attrib.get("countrycode"),
                             "year": y})
        print(f"  TRAINS {y}: {len(seen)} countries with tariffs")
        time.sleep(0.5)
    write_csv("trains_avail.csv", rows, ["iso3", "code", "year"])
    return rows


# --- 3. World Bank: income group + region ----------------------------------
def wb_country_meta():
    payload = fetch(f"{WB}/country?format=json&per_page=400")
    data = json.loads(payload)[1]
    rows = []
    for c in data:
        if c["region"]["id"] == "NA":      # drops aggregates
            continue
        rows.append({"iso3": c["id"], "name": c["name"],
                     "region": c["region"]["value"],
                     "income_group": c["incomeLevel"]["value"]})
    write_csv("country_meta.csv", rows, ["iso3", "name", "region", "income_group"])
    print(f"  World Bank: {len(rows)} countries with income group")
    return rows


# --- 4. World Bank: merchandise exports, to rank exporters -----------------
def wb_merch_exports():
    vals = defaultdict(dict)
    page = 1
    while True:
        payload = fetch(f"{WB}/country/all/indicator/TX.VAL.MRCH.CD.WT"
                        f"?format=json&per_page=20000&date=2015:2023&page={page}")
        body = json.loads(payload)
        meta, data = body[0], body[1]
        for r in data or []:
            if r["value"] is not None:
                vals[r["countryiso3code"]][int(r["date"])] = r["value"]
        if page >= meta["pages"]:
            break
        page += 1
    # rank on the most recent year each country actually reports
    latest = {iso: yv[max(yv)] for iso, yv in vals.items() if yv}
    print(f"  World Bank exports: {len(latest)} countries ranked")
    return latest


# --- 5. Join and choose -----------------------------------------------------
def main():
    os.makedirs(OUT, exist_ok=True)
    print("Step 1/4  Comtrade data availability")
    da = comtrade_availability()
    print("Step 2/4  TRAINS tariff availability")
    trains = trains_availability()
    print("Step 3/4  World Bank country metadata")
    meta = wb_country_meta()
    print("Step 4/4  World Bank merchandise exports")
    exports = wb_merch_exports()

    meta_by_iso = {m["iso3"]: m for m in meta}
    da_years = defaultdict(set)
    records = defaultdict(int)
    for r in da:
        if r["iso3"] and r["year"] in YEARS:
            da_years[r["iso3"]].add(r["year"])
            records[r["iso3"]] += r["total_records"] or 0
    trains_years = defaultdict(set)
    for r in trains:
        trains_years[r["iso3"]].add(r["year"])

    # credit EU members with the years the common external tariff exists
    eun_years = trains_years.get("EUN", set())
    for iso, since in EU_ACCESSION.items():
        trains_years[iso] |= {y for y in eun_years if y >= since}
    trains_years["GBR"] |= {y for y in eun_years if y <= UK_EU_LAST_YEAR}

    def tariff_source(iso, year):
        """Which TRAINS reporter carries this country's tariff in this year."""
        if iso == "GBR":
            return "EUN" if year <= UK_EU_LAST_YEAR else "GBR"
        if iso in EU_ACCESSION and year >= EU_ACCESSION[iso]:
            return "EUN"
        return iso

    tariff_map = [{"iso3": iso, "year": y, "tariff_reporter": tariff_source(iso, y)}
                  for iso in sorted(set(list(EU_ACCESSION) + ["GBR"]))
                  for y in YEARS]
    write_csv("eu_tariff_mapping.csv", tariff_map,
              ["iso3", "year", "tariff_reporter"])

    # --- importers: must file every year, must have tariffs, must be a country
    cand = []
    for iso, yrs in da_years.items():
        if iso not in meta_by_iso:            # drops EUR, S19, groupings
            continue
        cand.append({
            "iso3": iso,
            "name": meta_by_iso[iso]["name"],
            "income_group": meta_by_iso[iso]["income_group"],
            "region": meta_by_iso[iso]["region"],
            "comtrade_years": len(yrs),
            "tariff_years": len(trains_years.get(iso, ())),
            "avg_records_per_year": round(records[iso] / max(len(yrs), 1)),
            "merch_exports_usd": exports.get(iso, 0),
        })
    write_csv("importer_candidates.csv", sorted(
        cand, key=lambda x: (-x["comtrade_years"], -x["tariff_years"])),
        ["iso3", "name", "income_group", "region", "comtrade_years",
         "tariff_years", "avg_records_per_year", "merch_exports_usd"])

    full = [c for c in cand if c["comtrade_years"] >= MIN_YEARS_IMPORTER]
    print(f"\nCountries filing all {MIN_YEARS_IMPORTER} years: {len(full)}")
    with_tariff = [c for c in full if c["tariff_years"] >= 15]
    print(f"  ... of which >=15 years of tariff data: {len(with_tariff)}")

    # stratify: keep income-group spread, rank by trade size inside each group
    by_group = defaultdict(list)
    for c in with_tariff:
        by_group[c["income_group"]].append(c)
    for g in by_group:
        by_group[g].sort(key=lambda x: -x["merch_exports_usd"])

    groups = sorted(by_group, key=lambda g: -len(by_group[g]))
    chosen, idx = [], defaultdict(int)
    while len(chosen) < N_IMPORTERS and any(idx[g] < len(by_group[g]) for g in groups):
        for g in groups:                      # round-robin keeps the spread
            if len(chosen) >= N_IMPORTERS:
                break
            if idx[g] < len(by_group[g]):
                chosen.append(by_group[g][idx[g]])
                idx[g] += 1
    write_csv("importers_selected.csv", chosen,
              ["iso3", "name", "income_group", "region", "comtrade_years",
               "tariff_years", "avg_records_per_year", "merch_exports_usd"])

    # --- exporters: ranked by export size; they only need to be partners
    exp_rank = sorted((m for m in meta if exports.get(m["iso3"], 0) > 0),
                      key=lambda m: -exports[m["iso3"]])[:N_EXPORTERS]
    exp_rows = [{"iso3": m["iso3"], "name": m["name"],
                 "income_group": m["income_group"], "region": m["region"],
                 "merch_exports_usd": exports[m["iso3"]],
                 "files_own_data_years": len(da_years.get(m["iso3"], ()))}
                for m in exp_rank]
    write_csv("exporters_selected.csv", exp_rows,
              ["iso3", "name", "income_group", "region", "merch_exports_usd",
               "files_own_data_years"])

    # --- report
    print(f"\nImporters selected: {len(chosen)}")
    dist = defaultdict(int)
    for c in chosen:
        dist[c["income_group"]] += 1
    for g, n in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {g:<22} {n}")
    print(f"Exporters selected: {len(exp_rows)}")

    est = sum(c["avg_records_per_year"] for c in chosen) * len(YEARS)
    print(f"\nEstimated Comtrade records for the full pull (all partners): "
          f"{est:,.0f}")
    print(f"Files written to {OUT}/")


if __name__ == "__main__":
    main()
