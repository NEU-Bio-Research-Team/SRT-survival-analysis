"""Feasibility probe for the WITS data pipeline.

Pulls one small slice of every variable listed in requirements.txt through the
WITS SDMX REST API and reports, per variable, whether the endpoint actually
returns data. Writes a tidy CSV per block into ./probe_out/.

Usage: python3 wits_probe.py
"""

import csv
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://wits.worldbank.org/API/V1/SDMX/V21/datasource"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probe_out")

EXPORTERS = ["vnm", "tha"]          # ISO3 alpha, TradeStats reporters
IMPORTERS = ["usa", "jpn"]          # ISO3 alpha, TradeStats partners
YEARS = [2015, 2019, 2023]
TRN_REPORTERS = {"vnm": "704", "tha": "764"}   # TRAINS uses numeric codes
TRN_PARTNERS = {"usa": "840", "jpn": "392", "world": "000"}
HS6_SAMPLE = ["610910", "854231", "090111"]

session_log = []


def get(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": "wits-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001 - network probe, report and continue
        return 0, str(e).encode()


def parse_obs(payload):
    """Flatten SDMX StructureSpecificData into dicts of Series+Obs attributes."""
    root = ET.fromstring(payload)
    ns = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message}"
    rows = []
    for ds in root.iter(f"{ns}DataSet"):
        for series in ds:
            if not series.tag.endswith("Series"):
                continue
            base = dict(series.attrib)
            for obs in series:
                row = dict(base)
                row.update(obs.attrib)
                rows.append(row)
    return rows


def write_csv(name, rows):
    if not rows:
        return None
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    cols = sorted({k for r in rows for k in r})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path


def probe(label, url, out_name):
    code, payload = get(url)
    rows = parse_obs(payload) if code == 200 else []
    path = write_csv(out_name, rows) if rows else None
    sample = rows[0].get("OBS_VALUE") if rows else ""
    session_log.append((label, code, len(rows), sample, path or "", url))
    print(f"[{'OK ' if rows else 'FAIL'}] {label:<38} http={code:<4} rows={len(rows):<6} "
          f"sample={sample}")
    time.sleep(0.4)
    return rows


# --- Block 1: Trade Stats - Trade -------------------------------------------
# indicator -> (partner value, product value); 999/999999 means "not applicable"
TRADE_INDICATORS = {
    "XPRT-TRD-VL": ("partner", "Total"),          # export value  (US$ thousand)
    "MPRT-TRD-VL": ("partner", "Total"),          # import value
    "RCA": ("partner", "50-63_TextCloth"),        # revealed comparative advantage
    "XPRT-PRDCT-SHR": ("partner", "50-63_TextCloth"),   # product share
    "XPRT-PRTNR-SHR": ("partner", "999999"),      # partner share
    "CNTRY-GRWTH": ("partner", "50-63_TextCloth"),
    "WRLD-GRWTH": ("partner", "50-63_TextCloth"),
    "HH-MKT-CNCNTRTN-NDX": ("999", "999999"),     # Herfindahl-Hirschman
    "NDX-XPRT-MKT-PNRTTN": ("999", "999999"),
    "NMBR-XPRT-HS6-PRDCT": ("partner", "999999"),  # products traded, HS6 count
    "NMBR-XPRT-PRTNR": ("999", "999999"),
    "NMBR-PRDCT-XPRTD": ("999", "999999"),
}


def block_tradestats():
    print("\n=== Block 1: Trade Stats - Trade ===")
    for ind, (p_rule, prod) in TRADE_INDICATORS.items():
        partner = IMPORTERS[0] if p_rule == "partner" else p_rule
        url = (f"{BASE}/tradestats-trade/reporter/{EXPORTERS[0]}/year/ALL/"
               f"partner/{partner}/product/{prod}/indicator/{ind}")
        probe(f"trade/{ind}", url, f"trade_{ind}.csv")


# --- Block 2: Trade Stats - Development (WDI) -------------------------------
DEV_INDICATORS = ["NY-GDP-MKTP-KD-ZG", "NY-GDP-MKTP-CD", "NY-GDP-PCAP-CD",
                  "NY-GNP-PCAP-CD"]


def block_development():
    print("\n=== Block 2: Trade Stats - Development (WDI) ===")
    for ind in DEV_INDICATORS:
        url = (f"{BASE}/tradestats-development/reporter/{EXPORTERS[0]}/"
               f"year/ALL/indicator/{ind}")
        probe(f"dev/{ind}", url, f"dev_{ind}.csv")


# --- Block 3: UNCTAD TRAINS tariffs at HS6 ----------------------------------
def block_tariff():
    print("\n=== Block 3: UNCTAD TRAINS tariff (HS6) ===")
    rep = TRN_REPORTERS[EXPORTERS[0]]
    # MFN: partner 000
    probe("tariff/MFN one HS6",
          f"{BASE}/TRN/reporter/{rep}/partner/000/product/{HS6_SAMPLE[0]}/"
          f"year/2019/datatype/reported", "tariff_mfn_one.csv")
    # MFN: whole HS6 schedule for one year
    probe("tariff/MFN all HS6 (1 year)",
          f"{BASE}/TRN/reporter/{rep}/partner/000/product/ALL/"
          f"year/2019/datatype/reported", "tariff_mfn_all.csv")
    # Preferential: named partner
    probe("tariff/PREF vs CHN",
          f"{BASE}/TRN/reporter/{rep}/partner/156/product/{HS6_SAMPLE[0]}/"
          f"year/2019/datatype/reported", "tariff_pref.csv")
    # Importer-side tariff facing our exporter (what the survival model needs)
    probe("tariff/USA MFN all HS6",
          f"{BASE}/TRN/reporter/840/partner/000/product/ALL/"
          f"year/2019/datatype/reported", "tariff_usa_all.csv")
    # Known limit: two ALL dimensions on TRAINS
    probe("tariff/ALL products x ALL years (expected 413)",
          f"{BASE}/TRN/reporter/{rep}/partner/000/product/ALL/"
          f"year/ALL/datatype/reported", "tariff_overload.csv")


# --- Block 4: what the API cannot do ----------------------------------------
def block_limits():
    print("\n=== Block 4: known limits ===")
    probe("trade value at HS6 (expected fail)",
          f"{BASE}/tradestats-trade/reporter/{EXPORTERS[0]}/year/2019/"
          f"partner/{IMPORTERS[0]}/product/{HS6_SAMPLE[0]}/indicator/XPRT-TRD-VL",
          "trade_hs6.csv")


# --- Block 5: mini panel, the shape the survival dataset needs --------------
def block_panel():
    print("\n=== Block 5: mini panel (exporter x importer x year) ===")
    rows = []
    for exp in EXPORTERS:
        for imp in IMPORTERS:
            url = (f"{BASE}/tradestats-trade/reporter/{exp}/year/ALL/"
                   f"partner/{imp}/product/Total/indicator/XPRT-TRD-VL")
            code, payload = get(url)
            if code != 200:
                print(f"  {exp}->{imp}: http={code}")
                continue
            for r in parse_obs(payload):
                if int(r["TIME_PERIOD"]) in YEARS:
                    rows.append({"exporter": exp.upper(), "importer": imp.upper(),
                                 "year": r["TIME_PERIOD"],
                                 "export_value_usd_thousand": r["OBS_VALUE"]})
            time.sleep(0.4)
    path = write_csv("panel_demo.csv", rows)
    print(f"  panel rows={len(rows)} -> {path}")
    for r in rows:
        print("   ", r)


def main():
    block_tradestats()
    block_development()
    block_tariff()
    block_limits()
    block_panel()

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "_probe_log.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "http", "rows", "sample_value", "csv", "url"])
        w.writerows(session_log)

    ok = sum(1 for r in session_log if r[2] > 0)
    print(f"\nSummary: {ok}/{len(session_log)} probes returned data. "
          f"Details in {OUT}/_probe_log.csv")


if __name__ == "__main__":
    main()
