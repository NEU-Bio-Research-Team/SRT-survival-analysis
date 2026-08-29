"""Step 7b: turn the raw covariate downloads into panels keyed the same way as
analysis/panel_final.csv, so merge_panel.py can join them on (importer, year).

Four outputs, each answering a gap the WITS pull leaves open:

  analysis/fta_vn.csv       Which importers had a trade agreement in force with
                            Viet Nam, and since when. This is the repair for the
                            group-code problem in the tariff data: TRAINS files
                            ASEAN/AANZFTA/GSP preferences under codes whose
                            membership it will not publish, so 92% of episodes
                            fall back to MFN. A dated FTA dummy recovers the
                            treatment those episodes actually received, even
                            though the rate itself stays unobserved.

  analysis/ttbd_vn.csv      Antidumping, countervailing and safeguard actions,
                            by importer and year, with the in-force window. This
                            is the only *time-varying* trade barrier in the whole
                            project - the NTM tables are a cross-section - which
                            makes it the natural shock driver for a dynamic
                            model. It stops in 2015 (see the caveat printed at
                            the end).

  analysis/gravity_vn.csv   Distance, contiguity, shared language, colonial ties.
                            Standard controls in the trade-duration literature
                            and absent here until now.

  analysis/macro_panel_v2.csv  The four existing WITS macro series re-pulled from
                            the World Bank directly - which is what fills
                            Romania's 20 empty country-years - plus exchange
                            rate, inflation, population, LPI and imports/GDP.

  analysis/complexity_*.csv  Product complexity (PCI) by HS92 four-digit
                            product-year and economic complexity (ECI) by
                            country-year, from the Atlas of Economic
                            Complexity. PCI is the product-side covariate
                            the data brief asks for and nothing else here
                            supplies.

Output: analysis/{fta_vn,ttbd_vn,ttbd_vn_cases,gravity_vn,macro_panel_v2,
        complexity_product,complexity_country}.csv
"""

import csv
import datetime
import glob
import io
import json
import os
import re
import sys
import zipfile
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data_raw")
SEL = os.path.join(HERE, "selection")
OUT = os.path.join(HERE, "analysis")
YEARS = list(range(2002, 2026))
TTBD_LAST_YEAR = 2015   # TTBD was last updated June 2016 (data through 2015Q4)
VN_ISO3, VN_NUM = "VNM", 704


# ---------------------------------------------------------------- helpers

def importers():
    """The 147 importing countries the panel is built on."""
    with open(os.path.join(SEL, "importers_vn.csv"), encoding="utf-8") as f:
        return [r["iso3"] for r in csv.DictReader(f)]


def numeric_to_iso3():
    """UN M49 numeric -> ISO3, read off the Comtrade availability table the
    selection step already wrote. DESTA keys its dyads by numeric code."""
    m = {}
    with open(os.path.join(SEL, "comtrade_da.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                m[int(r["code"])] = r["iso3"]
            except (ValueError, KeyError):
                pass
    m.update(ISO_NUMERIC_FIX)
    m[VN_NUM] = VN_ISO3
    return m


ALIASES = {
    # TTBD spellings
    "USA": "USA", "Korea": "KOR", "South Korea": "KOR", "Taiwan": "TWN",
    "Turkey": "TUR", "Russia": "RUS", "Vietnam": "VNM", "Venezuela": "VEN",
    "Egypt": "EGY", "Czech Republic": "CZE",
    # DESTA spellings
    "United States": "USA", "Brunei": "BRN", "Congo - Kinshasa": "COD",
    "Hong Kong SAR China": "HKG", "Iran": "IRN", "Laos": "LAO",
    "Myanmar (Burma)": "MMR", "North Korea": "PRK", "Slovakia": "SVK",
    "Trinidad & Tobago": "TTO", "Macao SAR China": "MAC",
    "Cote d'Ivoire": "CIV", "Congo - Brazzaville": "COG",
}

# UN Comtrade keeps a handful of custom reporter codes where it aggregates
# territories; DESTA uses plain ISO 3166 numeric. Without these four, India,
# the United States, France and Switzerland silently drop out of the FTA panel.
ISO_NUMERIC_FIX = {356: "IND", 840: "USA", 250: "FRA", 756: "CHE",
                   578: "NOR", 710: "ZAF"}

# Agreements that are not reciprocal tariff-preference deals, kept in a column
# of their own rather than in the headline dummy:
#   GSTP  a shallow 1989 preference scheme among developing countries. Left in,
#         it sets first_fta_year to 2002 for 47 partners and flattens the
#         variation the dummy exists to capture.
#   US Vietnam  the 2001 Bilateral Trade Agreement granted normal trade
#         relations, not preferential tariffs, so calling it an FTA would
#         mislabel Viet Nam's single largest market for the whole window.
# DESTA misses two memberships that matter a great deal here, both checked
# against the primary source before being written in:
#
#   ASEAN  DESTA dates Viet Nam's ASEAN goods access from ATIGA (2010), but
#          Viet Nam signed the CEPT accession protocol on 15 Dec 1995 and began
#          CEPT tariff reduction on 1 Jan 1996 - before this panel opens - so
#          every ASEAN partner is preferential for the whole 2002-2021 window.
#          Left uncorrected this mislabels Malaysia, Singapore, Thailand,
#          Indonesia, the Philippines and Cambodia, which between them carry
#          more spells than any other group of importers.
#          asean.org, "Agreement on the CEPT Scheme for AFTA"
#
#   EAEU   the Viet Nam-EAEU FTA entered into force 5 Oct 2016 for all five
#          members, but DESTA files only three dyads. Armenia and Kyrgyzstan
#          are missing - and TRAINS does carry preferential schedules for both
#          from 2017, which is how the omission surfaced.
#          eurasiancommission.org, 19 Aug 2016; WTO RTA-IS rtaid=973
BLOC_OVERRIDES = [
    (["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA"], 1996,
     "ASEAN Free Trade Area (CEPT/AFTA)"),
    (["ARM", "KGZ"], 2016, "Eurasian Economic Union (EAEU) Vietnam"),
]

NOT_PREFERENTIAL = {
    "Global System of Trade Preferences (GSTP)",
    "US Vietnam",
}
# TTBD files a bloc's cases once under the bloc name; the panel is by member.
BLOCS = {
    "Gulf Cooperation Council": ["BHR", "KWT", "OMN", "QAT", "SAU", "ARE"],
}


def name_to_iso3():
    """TTBD names its imposing countries in English, not ISO3."""
    m = {}
    with open(os.path.join(SEL, "country_meta.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m[r["name"].strip()] = r["iso3"]
    m.update(ALIASES)
    return m


def eu_members():
    """Whoever the selection step routed through the EUN tariff reporter."""
    path = os.path.join(SEL, "eu_tariff_mapping.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return sorted({r["iso3"] for r in csv.DictReader(f)
                       if r["tariff_reporter"] == "EUN"})


def write(name, rows, cols):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  -> {name}: {len(rows):,} rows")


def excel_date(v):
    """TTBD stores dates as Excel serials; '.', 'MI', 'IF', 'NA' are not dates."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n < 10000 or n > 60000:
        return None
    return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(n))


# ---------------------------------------------------------------- 1. FTA

def build_fta(imps, num2iso):
    """DESTA dyads -> one row per (importer, year) with the agreement state.

    DESTA lists every agreement a pair belongs to, including the plurilateral
    ones (ASEAN Goods, ASEAN-China, CPTPP, EVFTA) that TRAINS hides behind group
    codes. Three decisions shape the output:

      * a partner is resolved by name first and by ISO numeric second, because
        Comtrade's custom codes for India, the US, France and Switzerland do not
        match the ISO numerics DESTA uses;
      * `entryforceyear` is the year the treaty entered into force. A row
        without one is signed-but-never-ratified and is dropped, not counted;
      * DESTA carries the amended text of an agreement as a separate row
        ("... (consolidated)") sharing the original's `base_treaty` number, so
        rows are deduplicated on that number and the earliest entry-into-force
        year wins. Otherwise ASEAN-China alone counts twice.

    Non-preferential agreements (see NOT_PREFERENTIAL) are reported in their own
    columns rather than in `fta_in_force`.
    """
    path = os.path.join(RAW, "rta", "desta_dyads_v0203.csv")
    if not os.path.exists(path):
        print("  DESTA not on disk - skipped")
        return
    n2i = name_to_iso3()

    # importer -> base_treaty -> (entry_year, name, preferential?)
    deals = defaultdict(dict)
    unmapped = set()
    with open(path, encoding="latin-1") as f:
        for r in csv.DictReader(f):
            c1, c2 = r["country1"].strip(), r["country2"].strip()
            if "Vietnam" not in (c1, c2):
                try:
                    if VN_NUM not in (int(r["iso1"]), int(r["iso2"])):
                        continue
                except (ValueError, TypeError):
                    continue
            other_name = c2 if c1 == "Vietnam" else c1
            other = n2i.get(other_name)
            if other is None:
                try:
                    a, b = int(r["iso1"]), int(r["iso2"])
                    other = num2iso.get(b if a == VN_NUM else a)
                except (ValueError, TypeError):
                    other = None
            if other is None:
                unmapped.add(other_name)
                continue
            if other == VN_ISO3 or other not in set(imps):
                continue
            try:
                ey = int(float(r["entryforceyear"]))
            except (ValueError, TypeError):
                continue                       # signed but never in force
            name = r["name"].strip()
            base = r.get("base_treaty") or r.get("number") or name
            pref = not any(name.startswith(x) for x in NOT_PREFERENTIAL)
            prev = deals[other].get(base)
            if prev is None or ey < prev[0]:
                deals[other][base] = (ey, name.replace(" (consolidated)", ""), pref)

    if unmapped:
        print(f"     unresolved DESTA partners (dropped): {sorted(unmapped)}")

    for isos, eif, label in BLOC_OVERRIDES:
        for iso in isos:
            if iso not in set(imps):
                continue
            cur = deals[iso].get(label)
            if cur is None or eif < cur[0]:
                deals[iso][label] = (eif, label, True)

    rows = []
    for iso in imps:
        ds = sorted(deals.get(iso, {}).values())
        pref = [d for d in ds if d[2]]
        first = pref[0][0] if pref else None
        for y in YEARS:
            live = [d for d in pref if d[0] <= y]
            allive = [d for d in ds if d[0] <= y]
            rows.append({
                "importer": iso, "year": y,
                "fta_in_force": int(bool(live)),
                "n_agreements": len(live),
                "first_fta_year": first if first and first <= y else "",
                "years_since_fta": (y - first) if first and first <= y else "",
                "gstp_in_force": int(any(
                    d[0] <= y and d[1].startswith("Global System") for d in ds)),
                "any_agreement_in_force": int(bool(allive)),
                "fta_names": " | ".join(sorted(d[1] for d in live)),
            })
    write("fta_vn.csv", rows,
          ["importer", "year", "fta_in_force", "n_agreements", "first_fta_year",
           "years_since_fta", "gstp_in_force", "any_agreement_in_force",
           "fta_names"])

    covered = sum(1 for iso in imps
                  if any(d[2] for d in deals.get(iso, {}).values()))
    switch = sum(1 for iso in imps
                 if 0 < len({r["fta_in_force"] for r in rows
                             if r["importer"] == iso}) > 1)
    print(f"     {covered} of {len(imps)} importers hold a preferential "
          f"agreement with Viet Nam at some point")
    print(f"     {switch} importers switch state inside 2002-2021 - that "
          f"switching is the identifying variation")
    return deals


# ---------------------------------------------------------------- 2. TTBD

def build_ttbd(imps):
    """Antidumping / CVD / safeguard actions that reach Vietnamese goods.

    Three of TTBD's families apply:
      GAD   antidumping, bilateral   - keep the rows naming Viet Nam
      GCVD  countervailing, bilateral - same filter
      GSGD  global safeguards, which by construction name no target: a
            safeguard applies to every source, Viet Nam included, so every
            case counts against the imposing country
    CSGD is the China-specific safeguard and cannot hit Viet Nam; DSUD is a
    table of WTO disputes about these measures, not the measures themselves.
    Both are skipped.

    Two decoding details the file forces:
      * the imposing country is an English name, not ISO3 ("European Union",
        "South Korea"), so it goes through name_to_iso3();
      * a bloc files once for all its members. An EU case is expanded to every
        EU member in the panel, which is the level the trade data is at.

    A case is in force from its final-measure date - or its initiation date if
    provisional duties were the only measure - until revocation or expiry.
    'IF' in REVOKE_DATE means still in force at the 2015Q4 cut-off.
    """
    zpath = os.path.join(RAW, "ttbd", "TTBD_2016.zip")
    if not os.path.exists(zpath):
        print("  TTBD not on disk - skipped")
        return
    try:
        import xlrd
    except ImportError:
        print("  TTBD needs `pip install xlrd` - skipped")
        return

    n2i = name_to_iso3()
    blocs = dict(BLOCS)
    blocs["European Union"] = eu_members()
    want = set(imps)
    fam_of = {"GAD": "ad", "GCVD": "cvd", "GSGD": "sg"}

    cases, prods, unmapped = [], [], set()
    with zipfile.ZipFile(zpath) as z:
        members = [n for n in z.namelist()
                   if n.endswith(".xls") and n.split("/")[0] in fam_of]
        for name in sorted(members):
            family = name.split("/")[0]
            wb = xlrd.open_workbook(file_contents=z.read(name))
            master = next((s for s in wb.sheet_names() if s.endswith("-Master")), None)
            if master is None:
                continue
            sh = wb.sheet_by_name(master)
            idx = {c: i for i, c in enumerate(sh.row_values(0))}
            imp_col = next((c for c in idx
                            if c.endswith("CTY_NAME") and not c.startswith("INV")), None)
            if imp_col is None:
                continue

            def col(row, *cands):
                for c in cands:
                    if c in idx:
                        return row[idx[c]]
                return None

            for r in range(1, sh.nrows):
                row = sh.row_values(r)
                target = str(col(row, "INV_CTY_CODE") or "").strip()
                if family != "GSGD" and target != VN_ISO3:
                    continue
                raw = str(row[idx[imp_col]]).strip()
                isos = blocs.get(raw) or ([n2i[raw]] if raw in n2i else [])
                if not isos:
                    unmapped.add(raw)
                    continue
                isos = [i for i in isos if i in want and i != VN_ISO3]
                if not isos:
                    continue
                init = excel_date(col(row, "INIT_DATE", "WTO_INIT_DATE", "PET_DATE"))
                final = excel_date(col(row, "F_AD_DATE", "F_CVD_DATE", "F_SG_DATE"))
                revoke_raw = str(col(row, "REVOKE_DATE") or "").strip()
                revoke = excel_date(revoke_raw) or excel_date(
                    col(row, "EXP_DATE", "TERM_DATE"))
                case_id = str(col(row, "CASE_ID") or "").strip()
                for iso in isos:
                    cases.append({
                        "case_id": case_id, "family": family, "importer": iso,
                        "imposer_filed_as": raw,
                        "target": target or "ALL",
                        "product": str(col(row, "PRODUCT") or "").strip(),
                        "init_year": init.year if init else "",
                        "measure_year": final.year if final else "",
                        "revoke_year": revoke.year if revoke else "",
                        "still_in_force_2015": int(revoke_raw.upper() == "IF"),
                    })

            ours = {c["case_id"] for c in cases if c["family"] == family}
            psheet = next((s for s in wb.sheet_names()
                           if s.endswith("-Products")), None)
            if psheet and ours:
                ps = wb.sheet_by_name(psheet)
                pidx = {c: i for i, c in enumerate(ps.row_values(0))}
                if "CASE_ID" in pidx and "HS_CODE" in pidx:
                    for r in range(1, ps.nrows):
                        pr = ps.row_values(r)
                        cid = str(pr[pidx["CASE_ID"]]).strip()
                        if cid not in ours:
                            continue
                        hs = str(pr[pidx["HS_CODE"]]).strip()
                        if hs in ("", ".", "MI", "NA"):
                            continue
                        prods.append({
                            "case_id": cid, "family": family,
                            "hs_code": hs.replace(".", "").split(",")[0].strip(),
                            "hs_digits": str(pr.__getitem__(
                                pidx["HS_DIGITS"])).strip() if "HS_DIGITS" in pidx else "",
                        })

    if unmapped:
        print(f"     unmapped imposer names (dropped): {sorted(unmapped)}")
    write("ttbd_vn_cases.csv", cases,
          ["case_id", "family", "importer", "imposer_filed_as", "target",
           "product", "init_year", "measure_year", "revoke_year",
           "still_in_force_2015"])
    if prods:
        write("ttbd_vn_products.csv", prods,
              ["case_id", "family", "hs_code", "hs_digits"])

    counts = defaultdict(lambda: defaultdict(int))
    for c in cases:
        fam = fam_of[c["family"]]
        if c["init_year"]:
            counts[(c["importer"], int(c["init_year"]))][f"{fam}_initiated"] += 1
        start = c["measure_year"] or c["init_year"]
        if not start:
            continue
        start = int(start)
        end = int(c["revoke_year"]) if c["revoke_year"] else (
            YEARS[-1] if c["still_in_force_2015"] else start)
        for y in range(max(start, YEARS[0]), min(end, YEARS[-1]) + 1):
            counts[(c["importer"], y)][f"{fam}_in_force"] += 1

    fields = ["ad_initiated", "ad_in_force", "cvd_initiated", "cvd_in_force",
              "sg_initiated", "sg_in_force"]
    rows = []
    for iso in imps:
        for y in YEARS:
            d = counts.get((iso, y), {})
            row = {"importer": iso, "year": y}
            row.update({k: d.get(k, 0) for k in fields})
            row["ttb_any_in_force"] = int(any(
                d.get(k, 0) for k in ("ad_in_force", "cvd_in_force", "sg_in_force")))
            # TTBD was last updated in June 2016. Past 2015 the counts are not
            # measurements: they are whatever was still in force at the cut-off,
            # carried forward, with no new case ever arriving. Left unflagged
            # that reads as a genuine collapse in trade remedies exactly where
            # the panel is busiest, so the flag travels with the data rather
            # than living only in the documentation.
            row["ttbd_observed"] = int(y <= TTBD_LAST_YEAR)
            rows.append(row)
    write("ttbd_vn.csv", rows,
          ["importer", "year"] + fields + ["ttb_any_in_force", "ttbd_observed"])

    bilateral = {c["case_id"] for c in cases if c["family"] in ("GAD", "GCVD")}
    hit = {c["importer"] for c in cases}
    print(f"     {len(bilateral)} bilateral AD/CVD cases naming Viet Nam; "
          f"{len(hit)} of {len(imps)} importers touched by some measure")
    return cases


# ---------------------------------------------------------------- 3. gravity

# Column names are V202211's own. There is no `rta` or `comcur` column in this
# release - the agreement variables are fta_wto / rta_coverage / rta_type - and
# the entry_* block is the cost, procedure count and days needed to start a
# business in the destination, which is the closest thing CEPII carries to a
# fixed cost of entering a market.
GRAV_KEEP = ["dist", "distw_harmonic", "distcap", "contig", "comlang_off",
             "comlang_ethno", "comcol", "col45", "comrelig",
             "comleg_posttrans", "diplo_disagreement", "gatt_d", "wto_d",
             "eu_d", "fta_wto", "rta_coverage", "rta_type",
             "entry_cost_d", "entry_proc_d", "entry_time_d"]


def build_gravity(imps):
    """CEPII rows where Viet Nam is the origin and the importer the destination."""
    zpath = os.path.join(RAW, "gravity", "Gravity_csv_V202211.zip")
    if not os.path.exists(zpath):
        print("  CEPII gravity not on disk yet - skipped (rerun once it lands)")
        return
    if not zipfile.is_zipfile(zpath):
        print(f"  CEPII gravity is still downloading "
              f"({os.path.getsize(zpath):,} bytes so far) - skipped, "
              f"rerun this script when the download finishes")
        return
    want = set(imps)
    rows = []
    with zipfile.ZipFile(zpath) as z:
        # the archive ships a dozen CSVs - the country table, a label table per
        # coded column, and the panel itself. Taking the first .csv gets
        # Countries_V202211.csv and silently yields nothing.
        member = next(n for n in z.namelist()
                      if os.path.basename(n).lower().startswith("gravity")
                      and n.lower().endswith(".csv"))
        with z.open(member) as fh:
            reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8"))
            have = [c for c in GRAV_KEEP if c in reader.fieldnames]
            for r in reader:
                if r.get("iso3_o") != VN_ISO3 or r.get("iso3_d") not in want:
                    continue
                # CEPII carries Viet Nam twice: VNM.1 is the pre-1975 North and
                # has no post-reunification geography, VNM.2 is the country that
                # exists now. Keeping both duplicates every key and half the
                # rows come back empty.
                if r.get("country_exists_o") != "1" or r.get("country_exists_d") != "1":
                    continue
                try:
                    y = int(r["year"])
                except (ValueError, TypeError):
                    continue
                if y < YEARS[0] or y > YEARS[-1]:
                    continue
                row = {"importer": r["iso3_d"], "year": y}
                row.update({c: r.get(c, "") for c in have})
                rows.append(row)
    rows.sort(key=lambda r: (r["importer"], r["year"]))
    write("gravity_vn.csv", rows, ["importer", "year"] + have)
    keys = {(r["importer"], r["year"]) for r in rows}
    if len(keys) != len(rows):
        print(f"     WARNING: {len(rows) - len(keys):,} duplicate (importer, "
              f"year) keys - do not merge until this is resolved")
    yrs = {r["year"] for r in rows}
    print(f"     {len({r['importer'] for r in rows})} of {len(imps)} importers, "
          f"{min(yrs)}-{max(yrs)}")
    if max(yrs) < YEARS[-1]:
        print(f"     note: CEPII stops at {max(yrs)}. The geography and tie "
              f"variables are time-invariant so they carry forward; the "
              f"year-varying ones (entry_*, wto_d, fta_wto) do not.")


# ---------------------------------------------------------------- 3b. shocks

def build_shocks():
    """Year-level series that move every relationship at once.

    Level 5 of the research ladder asks what happens when failures are not
    independent. Nothing in the WITS pull can answer that: tariffs, NTMs and GDP
    all vary by country, so conditioning on them still leaves each relationship
    failing on its own. These two series are common by construction - one price
    channel, one uncertainty channel - and are the minimum a correlated-failure
    or stress-test specification needs.

    Annual means are taken over the monthly EPU series so both line up with the
    annual panel.
    """
    try:
        import openpyxl
    except ImportError:
        print("  shocks need `pip install openpyxl` - skipped")
        return
    out = {y: {"year": y} for y in YEARS}

    pink = os.path.join(RAW, "shocks", "CMO-Historical-Data-Annual.xlsx")
    if os.path.exists(pink):
        wb = openpyxl.load_workbook(pink, read_only=True, data_only=True)
        sh = wb["Annual Indices (Nominal)"]
        grid = list(sh.iter_rows(values_only=True))
        # the sheet stacks four header rows; flatten whichever one names a column
        head = {}
        for c in range(len(grid[5])):
            parts = [str(grid[r][c]).replace("\n", " ").strip()
                     for r in (5, 6, 7, 8)
                     if grid[r][c] not in (None, "", " ")]
            if parts:
                head[c] = (parts[-1].lower().replace(" & ", "_")
                           .replace(" ", "_").replace(".", "")
                           .replace("(", "").replace(")", ""))
        head[1] = "cmo_all_commodities"
        for row in grid[9:]:
            try:
                y = int(row[0])
            except (TypeError, ValueError):
                continue
            if y not in out:
                continue
            for c, name in head.items():
                v = row[c]
                if isinstance(v, (int, float)):
                    out[y][f"price_{name}" if c != 1 else name] = round(v, 4)

    epu = os.path.join(RAW, "shocks", "Global_Policy_Uncertainty_Data.xlsx")
    if os.path.exists(epu):
        wb = openpyxl.load_workbook(epu, read_only=True, data_only=True)
        sh = wb[wb.sheetnames[0]]
        acc = defaultdict(list)
        for row in list(sh.iter_rows(values_only=True))[1:]:
            try:
                y, v = int(row[0]), float(row[2])
            except (TypeError, ValueError):
                continue
            if y in out:
                acc[y].append(v)
        for y, vs in acc.items():
            out[y]["gepu_current"] = round(sum(vs) / len(vs), 4)
            out[y]["gepu_months"] = len(vs)

    cols = ["year"] + sorted({k for r in out.values() for k in r} - {"year"})
    rows = [out[y] for y in YEARS]
    write("shocks_annual.csv", rows, cols)
    filled = sum(1 for r in rows if r.get("gepu_current"))
    print(f"     {len(cols) - 1} series, EPU present for {filled}/{len(YEARS)} years")


# ---------------------------------------------------------------- 4. macro

def build_macro(imps):
    """WDI straight from the World Bank, which unlike WITS answers to `rou`."""
    d = os.path.join(RAW, "wdi")
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    if not files:
        print("  WDI not on disk - skipped")
        return
    series = {}
    for path in files:
        name = re.sub(r"_\d{4}_\d{4}$", "", os.path.basename(path)[:-5])
        with open(path) as f:
            for r in json.load(f):
                if r["value"] is not None:
                    series.setdefault(name, {})[(r["iso3"], r["year"])] = r["value"]
    names = sorted(series)
    keep = set(imps) | {VN_ISO3}
    rows = []
    for iso in sorted(keep):
        for y in YEARS:
            row = {"iso3": iso, "year": y}
            for n in names:
                v = series[n].get((iso, y))
                row[n] = "" if v is None else v
            rows.append(row)
    write("macro_panel_v2.csv", rows, ["iso3", "year"] + names)
    for n in names:
        filled = sum(1 for r in rows if r[n] != "")
        print(f"     {n}: {100 * filled / len(rows):5.1f}% filled")
    rou = [r for r in rows if r["iso3"] == "ROU" and r["gdp_current_usd"] != ""]
    print(f"     Romania: {len(rou)} of {len(YEARS)} country-years now have GDP")


# ------------------------------------------------------- 5. complexity

def build_complexity(imps):
    """Atlas of Economic Complexity: PCI per product-year, ECI per country-year.

    The data brief lists product complexity among the required covariates and it
    was the one item with nothing at all on disk. The Growth Lab publishes PCI
    at HS92 **four** digits, so a six-digit family joins on its first four
    characters - and because the panel's families are keyed to H0, which *is*
    HS1992, that join needs no concordance and loses nothing: all 1,216
    four-digit groups present in the panel are covered.

    ECI/COI come along for the ride at country-year, which gives the importer
    side of a relationship a complexity control to sit beside its GDP.
    """
    d = os.path.join(RAW, "complexity")
    prod = os.path.join(d, "hs92_product_year_4.csv")
    ctry = os.path.join(d, "hs92_country_year.csv")
    if not os.path.exists(prod):
        print("  Atlas files not on disk - skipped "
              "(run fetch_covariates.py)")
        return

    rows, seen_years = [], set()
    with open(prod, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            y = int(r["year"])
            if y not in YEARS:
                continue
            code = r["product_hs92_code"].strip()
            if not (len(code) == 4 and code.isdigit()):
                continue          # services and the unspecified residual
            seen_years.add(y)
            rows.append({"hs4": code, "year": y, "pci": r["pci"],
                         "world_export_value_usd": r["export_value"]})
    rows.sort(key=lambda r: (r["hs4"], r["year"]))
    write("complexity_product.csv", rows,
          ["hs4", "year", "pci", "world_export_value_usd"])
    codes = {r["hs4"] for r in rows}
    print(f"     {len(codes):,} HS92 four-digit products x "
          f"{min(seen_years)}-{max(seen_years)}")

    if not os.path.exists(ctry):
        return
    keep = set(imps) | {VN_ISO3}
    crows = []
    for r in csv.DictReader(open(ctry, encoding="utf-8")):
        y = int(r["year"])
        if y in YEARS and r["country_iso3_code"] in keep:
            crows.append({"iso3": r["country_iso3_code"], "year": y,
                          "eci": r["eci"], "coi": r["coi"],
                          "diversity": r["diversity"]})
    crows.sort(key=lambda r: (r["iso3"], r["year"]))
    write("complexity_country.csv", crows,
          ["iso3", "year", "eci", "coi", "diversity"])
    have = len({r["iso3"] for r in crows})
    print(f"     ECI for {have} of {len(keep)} countries")


# ------------------------------------------------- 6. US 2025 tariffs

# The wording is formulaic across all 167 headings, which is what makes it
# parseable at all: a rate in the `general` field, a country at the end of the
# description, an effective date in the in-transit exception, and - when the
# provision has been superseded - a compiler's note citing the Federal Register.
US_RATE = re.compile(r"\+\s*(\d+(?:\.\d+)?)\s*%")
# Stop at the first clause boundary, not just the first comma: some headings
# read "...the product of Brazil that are entered for consumption...", and a
# comma-only rule swallows the clause and matches no country at all. `or` is a
# real case too - eleven headings cover two countries at one rate - so the
# capture is split afterwards rather than assumed singular.
US_COUNTRY = re.compile(
    r"articles the product of (.+?)"
    r"(?=\s+that\b|\s*,?\s*as provided|\s+classified\b|$)", re.I)
US_DATE = re.compile(r"on ([A-Z][a-z]+ \d{1,2}, \d{4})")
US_TERMINATED = re.compile(r"provision terminated", re.I)
US_ALIASES = {
    "Vietnam": "VNM", "Syria": "SYR", "Laos": "LAO", "Burma (Myanmar)": "MMR",
    "Myanmar (Burma)": "MMR", "Bosnia and Herzegovina": "BIH",
    "Falkland Islands": "FLK", "Cote d'Ivoire": "CIV", "Ivory Coast": "CIV",
    "Democratic Republic of the Congo": "COD", "Republic of the Congo": "COG",
    "Taiwan": "TWN", "Turkey": "TUR", "Brunei": "BRN",
    "European Union": "EUN", "China and Hong Kong": "CHN",
    "North Macedonia": "MKD", "Trinidad and Tobago": "TTO",
    "United Kingdom": "GBR", "South Africa": "ZAF", "South Korea": "KOR",
    "Korea": "KOR", "New Zealand": "NZL", "Sri Lanka": "LKA",
    "Costa Rica": "CRI", "Papua New Guinea": "PNG", "Equatorial Guinea": "GNQ",
    "Saudi Arabia": "SAU", "United Arab Emirates": "ARE",
    "Dominican Republic": "DOM", "Czech Republic": "CZE",
    # HTS spellings that no other source in this project uses. The two Côte
    # d'Ivoire entries differ by apostrophe character - a backtick in one
    # heading, a typographic quote in another - and matching on one alone
    # silently drops the other.
    "Cote d`Ivoire": "CIV", "C\u00f4te d`Ivoire": "CIV",
    "C\u00f4te d\u2019Ivoire": "CIV", "C\u00f4te d'Ivoire": "CIV",
    "Nauru": "NRU", "Philippines": "PHL", "Zimbabwe": "ZWE",
    "Nicaragua": "NIC", "Namibia": "NAM", "Jordan": "JOR", "Norway": "NOR",
    "Chad": "TCD", "Cameroon": "CMR", "Brazil": "BRA", "India": "IND",
    "Falkland Islands": "FLK", "Sri Lanka": "LKA", "Burma (Myanmar)": "MMR",
}


def build_us_2025(name2iso):
    """The 2025 US reciprocal tariff, from the HTS headings that carry it.

    The brief calls this the most important covariate in the design and TRAINS
    does not have it - WITS answers 404 for 2024 and 2025 - so it is read out of
    chapter 99 of the US tariff schedule instead. Two subchapters matter:
    9903.01 for the April action (Viet Nam at 46%, then suspended to the 10%
    universal floor) and 9903.02 for the August one (Viet Nam at 20%, with a
    separate 40% penalty for goods found to be transshipped).

    Every country the United States named is kept, not just Viet Nam: the rate
    faced by Bangladesh, Cambodia, India, Mexico and China is what separates a
    Vietnamese relationship dying from a tariff from one dying because a
    competitor got a better one.
    """
    path = os.path.join(RAW, "us_tariffs_2025", "hts_9903.json")
    if not os.path.exists(path):
        print("  HTS chapter 99 not on disk - skipped "
              "(run fetch_us_tariffs_2025.py)")
        return
    with open(path, encoding="utf-8") as f:
        headings = json.load(f)

    rows, unmatched = [], set()
    for h in headings:
        hts = (h.get("htsno") or "").strip()
        desc = (h.get("description") or "").strip()
        general = (h.get("general") or "").strip()
        if not hts or not desc:
            continue
        rate = US_RATE.search(general)
        country = US_COUNTRY.search(desc)
        date = US_DATE.search(desc)
        # Headings with no country and no rate are the exemption and definition
        # provisions (in-transit, US content, donations, Annex II). They are
        # kept, flagged, because an exemption is as much part of the schedule as
        # a rate - but they carry no iso3 and no percentage.
        iso, names = "", []
        if country:
            raw = country.group(1).strip()
            # "the European Union or Jordan" -> two countries at one rate.
            # "any country" is the universal floor and has no iso3 by design.
            parts = [x.strip()
                     for x in re.split(r",|\bor\b", raw) if x.strip()]
            for nm in parts:
                nm = re.sub(r"^(the|articles)\s+", "", nm).strip(" .;")
                if nm.lower() in ("any country", "any other country"):
                    continue
                # A few headings run on past the country list into the duty
                # arithmetic ("...rate of duty under column 1 less than 15
                # percent"). Those fragments are not countries and reporting
                # them as unmatched names would bury the ones that are.
                if (not nm or not nm[:1].isupper() or len(nm) > 40
                        or any(ch.isdigit() for ch in nm)):
                    continue
                code = US_ALIASES.get(nm) or name2iso.get(nm, "")
                if code:
                    names.append(code)
                else:
                    unmatched.add(nm)
            iso = ";".join(names)
        rows.append({
            "hts_heading": hts,
            "subchapter": "III (April)" if hts.startswith("9903.01")
                          else "IV (August)",
            "iso3": iso,
            "country_as_written": country.group(1).strip() if country else "",
            "rate_pct": rate.group(1) if rate else "",
            "effective_from": date.group(1) if date else "",
            "terminated": int(bool(US_TERMINATED.search(desc))),
            "is_exemption": int(not rate and not country),
            "duty_text": general,
            "description": desc,
        })
    rows.sort(key=lambda r: r["hts_heading"])
    write("us_tariffs_2025.csv", rows,
          ["hts_heading", "subchapter", "iso3", "country_as_written",
           "rate_pct", "effective_from", "terminated", "is_exemption",
           "duty_text", "description"])

    rated = [r for r in rows if r["rate_pct"] and r["iso3"]]
    isos = {r["iso3"] for r in rated}
    print(f"     {len(rows)} headings; {len(rated)} carry a country rate, "
          f"{len(isos)} distinct countries")
    vn = [r for r in rows if r["iso3"] == "VNM"]
    for r in vn:
        end = " (terminated)" if r["terminated"] else ""
        print(f"     Viet Nam: {r['hts_heading']} +{r['rate_pct']}% from "
              f"{r['effective_from']}{end}")
    if unmatched:
        print(f"     {len(unmatched)} country names without an iso3: "
              f"{', '.join(sorted(unmatched)[:8])}")


# ---------------------------------------------------------------- main

def main():
    os.makedirs(OUT, exist_ok=True)
    imps = importers()
    num2iso = numeric_to_iso3()
    print(f"{len(imps)} importers, {len(num2iso)} numeric country codes mapped\n")

    print("1. Trade agreements (DESTA)")
    build_fta(imps, num2iso)
    print("\n2. Temporary trade barriers (TTBD)")
    build_ttbd(imps)
    print("\n3. Gravity (CEPII)")
    build_gravity(imps)
    print("\n3b. Common shocks (World Bank Pink Sheet, EPU)")
    build_shocks()
    print("\n4. Macro (World Bank WDI)")
    build_macro(imps)
    print("\n5. Complexity (Harvard Growth Lab, Atlas)")
    build_complexity(imps)
    print("\n6. US 2025 reciprocal tariffs (USITC HTS chapter 99)")
    build_us_2025(name_to_iso3())

    print("\nCaveats to carry into the Discussion:")
    print(f"  * TTBD stops at {TTBD_LAST_YEAR}Q4 - the last "
          f"{YEARS[-1] - TTBD_LAST_YEAR} years of the panel have no antidumping")
    print(f"    coverage. Treat {TTBD_LAST_YEAR + 1}-{YEARS[-1]} as missing, "
          f"not as zero; the ttbd_observed column carries the flag.")
    print("  * DESTA records entry into force, not the depth of the preference:")
    print("    the dummy says an agreement applied, not what rate it granted.")
    print("  * CEPII `rta` is its own agreement dummy; it and DESTA disagree at")
    print("    the margin. fta_vn.csv is the one built for this panel.")


if __name__ == "__main__":
    sys.exit(main())
