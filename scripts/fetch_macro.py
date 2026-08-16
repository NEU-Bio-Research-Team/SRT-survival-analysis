"""Step 6c: country-level covariates for both sides of every relationship.

GDP growth and the other macro controls come from WITS Trade Stats -
Development, which republishes WDI. One call per country covers all years.
NTM indicators are downloaded from the WITS public NTM files and reshaped;
see the caveat printed at the end - they are a cross-section, not a panel.

Output: analysis/macro_panel.csv, analysis/ntm_country.csv
"""

import csv
import io
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # gốc dự án (thư mục cha của scripts/)
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "analysis")
RAW = os.path.join(HERE, "data_raw", "ntm")
WITS = "https://wits.worldbank.org/API/V1"
UA = "Mozilla/5.0 (compatible; trade-survival-research/1.0)"

INDICATORS = {
    "NY-GDP-MKTP-KD-ZG": "gdp_growth_pct",
    "NY-GDP-MKTP-CD": "gdp_current_usd",
    "NY-GDP-PCAP-CD": "gdp_per_capita_usd",
    "NE-EXP-GNFS-ZS": "exports_pct_gdp",
}
NTM_FILES = {
    "NTM-Trade-Frequency-Coverage-Ratio": "coverage",
    "NTM-Prevalence-Sector": "prevalence",
    "NTM-Indicators-Measure-Sector": "measures",
}
YEARS = range(2002, 2022)


def fetch(url, timeout=300, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, b""
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return e.code, b""
        except Exception:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            return 0, b""
    return 0, b""


def countries():
    out = set()
    for name in ("importers_vn.csv", "exporter_selected.csv"):
        with open(os.path.join(SEL, name), encoding="utf-8") as f:
            out.update(r["iso3"] for r in csv.DictReader(f))
    return sorted(out)


def macro():
    ns = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message}"
    values = {}
    isos = countries()
    for i, iso in enumerate(isos, 1):
        for code, label in INDICATORS.items():
            status, payload = fetch(
                f"{WITS}/SDMX/V21/datasource/tradestats-development/"
                f"reporter/{iso.lower()}/year/ALL/indicator/{code}")
            if status != 200 or not payload:
                continue
            root = ET.fromstring(payload)
            for ds in root.iter(f"{ns}DataSet"):
                for series in ds:
                    for obs in series:
                        y = int(obs.attrib.get("TIME_PERIOD", 0))
                        if y in YEARS:
                            values.setdefault((iso, y), {})[label] = \
                                obs.attrib.get("OBS_VALUE")
            time.sleep(0.4)
        print(f"  [{i}/{len(isos)}] {iso}", flush=True)

    rows = [{"iso3": iso, "year": y, **vals}
            for (iso, y), vals in sorted(values.items())]
    os.makedirs(OUT, exist_ok=True)
    cols = ["iso3", "year"] + list(INDICATORS.values())
    with open(os.path.join(OUT, "macro_panel.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote macro_panel.csv ({len(rows):,} country-years)")


def ntm():
    os.makedirs(RAW, exist_ok=True)
    frames = {}
    for name, label in NTM_FILES.items():
        status, payload = fetch(
            f"https://wits.worldbank.org/data/public/NTM/{name}.zip")
        if status != 200 or not payload:
            print(f"  {name}: download failed ({status})")
            continue
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            inner = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
            text = z.read(inner).decode("utf-8-sig", errors="replace")
        path = os.path.join(RAW, f"{name}.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        rows = list(csv.DictReader(io.StringIO(text)))
        frames[label] = rows
        print(f"  {name}: {len(rows):,} rows -> {path}")

    cov = frames.get("coverage", [])
    out = []
    for r in cov:
        year = r.get("year", "")
        if not year.isdigit() or not (1990 <= int(year) <= 2025):
            continue                       # the file contains junk rows
        out.append({
            "iso3": r.get("CountryISO3"), "survey_year": int(year),
            "trade_flow": r.get("TradeFlow"),
            "ntm_coverage_ratio": r.get("NTM Coverage ratio"),
            "ntm_frequency_ratio": r.get("NTM Frequency ratio"),
            "products_total": r.get("Traded products - total"),
            "products_ntm_affected": r.get("NTM affected product - count"),
        })
    with open(os.path.join(OUT, "ntm_country.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "iso3", "survey_year", "trade_flow", "ntm_coverage_ratio",
            "ntm_frequency_ratio", "products_total", "products_ntm_affected"])
        w.writeheader()
        w.writerows(out)
    years = sorted({r["survey_year"] for r in out})
    isos = {r["iso3"] for r in out}
    print(f"  wrote ntm_country.csv ({len(out)} rows, {len(isos)} countries, "
          f"survey years {years})")
    print("  NOTE: this is a cross-section per country, not an annual panel, "
          "and has no product dimension.")


if __name__ == "__main__":
    print("Macro covariates (WITS Development / WDI)")
    macro()
    print("NTM indicators (WITS public files)")
    ntm()
