"""Step 7: the covariates the survival and optimisation models need but the
WITS pull does not carry.

Four sources, all public and none needing an account - which is the whole point:
they can be fetched today, unlike TRAINS Online (Azure AD login) or WTO I-TIP
(subscription key).

  CEPII Gravity V202211  distance, contiguity, common language, colony, RTA
  DESTA v2.03            trade-agreement dyads with entry-into-force years
  TTBD (Bown 2016)       antidumping / CVD / safeguard cases, bilateral, to 2015
  World Bank WDI         Romania's missing macro, plus exchange rate, inflation,
                         population, the Logistics Performance Index and its
                         six sub-indices, and two environmental series
  Atlas (Growth Lab)     product complexity (PCI) and economic complexity (ECI)

Everything lands in data_raw/. Re-running skips what is already on disk, so an
interrupted pull is resumed by running the same command again.

Output: data_raw/gravity/, data_raw/rta/, data_raw/ttbd/, data_raw/wdi/,
        data_raw/shocks/, data_raw/complexity/
"""

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data_raw")
UA = "Mozilla/5.0 (compatible; trade-survival-research/1.0)"

DOWNLOADS = [
    ("gravity/Gravity_csv_V202211.zip",
     "https://www.cepii.fr/DATA_DOWNLOAD/gravity/data/Gravity_csv_V202211.zip",
     "CEPII Gravity V202211"),
    # HS2022. The other five revisions were fetched by hand earlier; this one
    # was missing and is what the 2022+ years are almost entirely reported in.
    ("concordance/H6_to_H0.zip",
     "https://wits.worldbank.org/data/public/concordance/Concordance_H6_to_H0.zip",
     "WITS concordance H6 (HS2022) -> H0"),
    ("rta/desta_dyads_v0203.csv",
     "https://www.designoftradeagreements.org/media/filer_public/6a/45/"
     "6a454835-eef1-44c4-8af2-5557a9552167/desta_list_of_treaties_02_03_dyads.csv",
     "DESTA v2.03 dyadic treaty list"),
    ("ttbd/TTBD_2016.zip",
     "https://www.chadpbown.com/wp-content/uploads/2019/02/TTBD_2016.zip",
     "Temporary Trade Barriers Database (Bown, June 2016)"),
    # Level-5 common-shock candidates: one price series and one uncertainty
    # series that move for every relationship at once, which is what a
    # correlated-failure model needs and a country-year covariate cannot give.
    ("shocks/CMO-Historical-Data-Annual.xlsx",
     "https://thedocs.worldbank.org/en/doc/"
     "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/"
     "CMO-Historical-Data-Annual.xlsx",
     "World Bank Pink Sheet, annual commodity prices"),
    ("shocks/Global_Policy_Uncertainty_Data.xlsx",
     "https://www.policyuncertainty.com/media/Global_Policy_Uncertainty_Data.xlsx",
     "Global Economic Policy Uncertainty index (Baker-Bloom-Davis)"),
    # Harvard Growth Lab, Atlas of Economic Complexity v18 (Dataverse
    # doi:10.7910/DVN/T4CHWJ). Product complexity is named in the data brief as
    # a required gravity/survival covariate and was the one item on that list
    # with nothing at all on disk. PCI is published at HS92 **4-digit**, which
    # joins to the panel's HS0 six-digit families on the first four characters -
    # H0 *is* HS1992, so no concordance is involved. 1995-2024, no gaps.
    ("complexity/hs92_product_year_4.csv",
     "https://dataverse.harvard.edu/api/access/datafile/13685116",
     "Atlas of Economic Complexity: PCI by HS92 4-digit product-year"),
    # ECI/COI per country-year, for the importer-side complexity control.
    ("complexity/hs92_country_year.csv",
     "https://dataverse.harvard.edu/api/access/datafile/13685109",
     "Atlas of Economic Complexity: ECI, COI, diversity by country-year"),
    ("complexity/hs92_data_dictionary.csv",
     "https://dataverse.harvard.edu/api/access/datafile/13685113",
     "Atlas of Economic Complexity: data dictionary"),
]

# WDI indicators. The first four already exist in macro_panel.csv via WITS, but
# WITS does not answer to `rou`, so they are re-pulled here from the World Bank
# directly - that is what fills Romania's 20 missing country-years.
WDI = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
    "NY.GDP.MKTP.CD": "gdp_current_usd",
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    "NE.EXP.GNFS.ZS": "exports_pct_gdp",
    "PA.NUS.FCRF": "exchange_rate_lcu_per_usd",
    "FP.CPI.TOTL.ZG": "inflation_pct",
    "SP.POP.TOTL": "population",
    "LP.LPI.OVRL.XQ": "lpi_overall",          # 2007,2010,2012,2014,2016,2018 only
    "NE.IMP.GNFS.ZS": "imports_pct_gdp",
    # The six LPI sub-indices. The robustness question in the brief asks for a
    # Green LPI, and every published construction of one starts from these
    # components rather than from the headline score - so the headline alone,
    # which is all that was on disk, cannot produce it. Same survey years as
    # lpi_overall: 2007, 2010, 2012, 2014, 2016, 2018, 2023.
    "LP.LPI.CUST.XQ": "lpi_customs",
    "LP.LPI.INFR.XQ": "lpi_infrastructure",
    "LP.LPI.ITRN.XQ": "lpi_intl_shipments",
    "LP.LPI.LOGS.XQ": "lpi_logistics_competence",
    "LP.LPI.TRAC.XQ": "lpi_tracking_tracing",
    "LP.LPI.TIME.XQ": "lpi_timeliness",
    # The environmental half of a Green LPI. Which of these enters, and with
    # what weights, depends on the reference paper the team picks - so they are
    # fetched, not yet combined. See docs/COVARIATES_ADDED.md.
    "EN.GHG.CO2.PC.CE.AR5": "co2_per_capita_t",
    "EG.FEC.RNEW.ZS": "renewable_energy_pct",
}
YEAR_FROM, YEAR_TO = 2002, 2025


def fetch(url, timeout=600, retries=4):
    ctx = ssl.create_default_context()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
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
                time.sleep(5 * (attempt + 1))
                continue
            return 0, b""
    return 0, b""


def download_files():
    print("Bulk files")
    for rel, url, label in DOWNLOADS:
        path = os.path.join(RAW, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            # a half-downloaded zip is bigger than 1 KB and looks finished, so
            # the archive itself has to say whether it is whole
            whole = zipfile.is_zipfile(path) if path.endswith(
                (".zip", ".xlsx")) else True
            if whole:
                print(f"  {label}: already on disk "
                      f"({os.path.getsize(path):,} bytes)")
                continue
            print(f"  {label}: on disk but truncated "
                  f"({os.path.getsize(path):,} bytes) - refetching")
        print(f"  {label}: downloading ...", flush=True)
        status, body = fetch(url)
        if status != 200 or len(body) < 1024:
            print(f"    FAILED (http {status}, {len(body)} bytes) - {url}")
            continue
        with open(path, "wb") as f:
            f.write(body)
        print(f"    {len(body):,} bytes -> {rel}")


def download_wdi():
    """One call per indicator for every country at once, not one per country."""
    out = os.path.join(RAW, "wdi")
    os.makedirs(out, exist_ok=True)
    print("\nWorld Bank WDI")
    for code, name in WDI.items():
        path = os.path.join(out, f"{name}_{YEAR_FROM}_{YEAR_TO}.json")
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            print(f"  {name}: already on disk")
            continue
        rows, page, pages = [], 1, 1
        while page <= pages:
            url = (f"https://api.worldbank.org/v2/country/all/indicator/{code}"
                   f"?format=json&per_page=20000&date={YEAR_FROM}:{YEAR_TO}"
                   f"&page={page}")
            status, body = fetch(url, timeout=180)
            if status != 200:
                print(f"  {name}: FAILED (http {status})")
                rows = None
                break
            payload = json.loads(body)
            if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
                break
            pages = payload[0].get("pages", 1)
            rows.extend(payload[1])
            page += 1
            time.sleep(0.3)
        if rows is None:
            continue
        keep = [{"iso3": r.get("countryiso3code"), "year": int(r["date"]),
                 "value": r["value"]}
                for r in rows if r.get("countryiso3code") and r.get("date")]
        with open(path, "w") as f:
            json.dump(keep, f)
        filled = sum(1 for r in keep if r["value"] is not None)
        print(f"  {name}: {len(keep):,} country-years, {filled:,} non-null")


def main():
    download_files()
    download_wdi()
    print("\nDone. Next: scripts/build_covariates.py")


if __name__ == "__main__":
    sys.exit(main())
