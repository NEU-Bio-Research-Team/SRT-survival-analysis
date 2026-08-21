# The covariates added on 19-21/08/2026, and what each one repairs

*Everything here was fetched the same day from sources that need no account.
That constraint is the point: it is what separates this batch from the two items
still waiting on the user (TRAINS Online and WTO I-TIP), and it means the whole
batch reproduces with two commands.*

```bash
python3 scripts/fetch_covariates.py    # downloads, resumable, skips what exists
python3 scripts/build_covariates.py    # reshapes into (importer, year) panels
```

---

## 1. Trade agreements — `analysis/fta_vn.csv`

**The gap it closes.** TRAINS files most of Viet Nam's preferential access under
group codes (ASEAN, AANZFTA, GSP beneficiary lists) whose membership WITS does
not publish. Only 13 reporters file a schedule naming Viet Nam directly, so
**92% of episodes fell back to MFN** and the rate faced was overstated. The rate
itself is still unobservable — but *whether an agreement applied* no longer is.

| | before | after |
|---|---|---|
| Episodes known to be preferential | 43,427 (8.0%) | **211,415 (38.8%)** |
| Importers with preferential access at some point | 39 | **52** |
| Importers whose status switches inside 2002-2021 | — | **44** |

Those 44 switches are the identifying variation: ACFTA 2005, AKFTA 2007, AJCEP
2008, AANZFTA + AIFTA 2010, VCFTA 2014, VN-EAEU 2016, CPTPP 2018, AHKFTA 2019,
EVFTA 2020 (28 importers at once), UKVFTA 2021.

**Validation.** 19 of 19 known entry-into-force dates reproduce exactly, and
after the two overrides below there are **zero** episodes where TRAINS reports a
preferential rate but the agreement panel says no agreement was in force. The
two sources are independent, so their agreement is worth something.

**Three judgement calls, all reversible in the script:**

* **GSTP is not counted as an FTA.** The 1989 Global System of Trade Preferences
  is a shallow scheme covering 47 of Viet Nam's partners. Counted, it sets
  `first_fta_year` to 2002 for all of them and flattens the variation the dummy
  exists to capture. It is kept in `gstp_in_force`.
* **The 2001 US-Viet Nam BTA is not counted as an FTA.** It granted normal trade
  relations, not tariff preferences. Counting it would mislabel Viet Nam's
  largest market for the entire window. It is inside `any_agreement_in_force`.
* **Two bloc memberships DESTA misses were added**, each checked against the
  primary source first:
  * **ASEAN** — DESTA dates Viet Nam's ASEAN goods access from ATIGA (2010), but
    Viet Nam signed the CEPT accession protocol on 15 Dec 1995 and began CEPT
    tariff reduction on 1 Jan 1996. Uncorrected, this mislabels Malaysia,
    Singapore, Thailand, Indonesia, the Philippines and Cambodia — which
    together carry more spells than any other group of importers.
  * **EAEU** — the FTA entered into force 5 Oct 2016 for all five members;
    DESTA files only three dyads. Armenia and Kyrgyzstan were missing, and
    TRAINS carries preferential schedules for both from 2017, which is how the
    omission surfaced.

**Limit to state plainly:** the dummy says an agreement applied, not what rate it
granted. Depth of preference and utilisation remain unobserved.

---

## 2. Temporary trade barriers — `analysis/ttbd_vn.csv`, `ttbd_vn_cases.csv`, `ttbd_vn_products.csv`

**The gap it closes.** Until now the only time-varying trade barrier in the
project was the tariff, and 92% of it was a fallback. The NTM tables are a
cross-section by construction. A dynamic model needs a barrier that *moves*, and
this is one: antidumping, countervailing and safeguard actions carry an
initiation date, a measure date and a revocation date.

* **69 bilateral AD/CVD cases naming Viet Nam** — the US frozen fish fillet case
  (2002), US shrimp (2004), the EU leather footwear case (2005), EU bicycles
  (2004), US steel nails (2014), and 64 others across 14 imposing jurisdictions.
* **Global safeguards** are included too: they name no target, so they reach
  Vietnamese goods like everyone else's.
* **711 case-importer rows** after expanding bloc filings — TTBD files an EU case
  once under "European Union"; the panel is by member state, so it is expanded.
* **3,231 HS codes** attached to those cases, so the barrier can be matched to
  product families rather than applied at the country level.
* **70 of 147 importers** are touched by some measure.

**Two limits, both material:**

* **The data stops at 2015Q4.** The last six years of the panel have no
  antidumping coverage. Treat 2016-2021 as **missing, not zero** — coding it
  zero would manufacture a spurious de-escalation exactly where the panel is
  busiest.
* Six Turkish cases carry no usable initiation date and so contribute to the
  case list but not to the in-force counts.

---

## 3. Gravity — `analysis/gravity_vn.csv`

Distance (simple, capital-to-capital and population-weighted), contiguity,
common official and ethnic language, shared colonial history, common religion,
shared legal origin, diplomatic disagreement, GATT/WTO/EU membership, and the
cost, procedure count and days needed to start a business in the destination —
the closest thing CEPII carries to a fixed cost of entering a market, which the
`enter` action at Level 3 will need. 147 of 147 importers, 2002-2021.

These are the standard controls of the trade-duration literature (Besedeš &
Prusa; Nitsch; Fugazza & Molina) and were absent from this project entirely.

**Two traps in the archive, both hit and both fixed in the script:**

* It ships twelve CSVs. Taking the first one alphabetically gets
  `Countries_V202211.csv` and yields **zero** matching rows without erroring.
* CEPII carries Viet Nam twice — `VNM.1` is the pre-1975 North and has no
  post-reunification geography, `VNM.2` is the country that exists now. Keeping
  both duplicates every key and leaves half the rows empty. The build filters on
  `country_exists_o/d == 1` and asserts the key is unique before writing.

**Independent validation of the FTA panel.** CEPII carries its own WTO-notified
agreement flag, built from a different source than DESTA. Against our dummy:

| | our `fta_in_force` = 0 | = 1 |
|---|---|---|
| CEPII `fta_wto` = 0 | 2,609 | 64 |
| CEPII `fta_wto` = 1 | **0** | 267 |

CEPII never asserts an agreement we deny. The 64 country-years where we are
broader are the CEPT/AFTA years and the non-WTO-notified deals — exactly the
direction the overrides were meant to add.

**Limit:** CEPII V202211 stops at 2021. Geography and tie variables are
time-invariant and carry forward; `entry_*`, `wto_d` and `fta_wto` do not.

---

## 4. Common shocks — `analysis/shocks_annual.csv`

**The gap it closes.** Level 5 of the ladder asks what happens when relationships
do *not* fail independently. Nothing in the WITS pull can answer that: tariffs,
NTMs and GDP all vary by country, so conditioning on them still leaves each
relationship failing on its own. These series are common by construction.

* **World Bank Pink Sheet**, 17 annual price indices (all commodities, energy,
  food, grains, metals, raw materials, fertilizers …), 2010 = 100.
* **Global Economic Policy Uncertainty** (Baker-Bloom-Davis), monthly averaged
  to annual. It reads 101 in 2002, 121 in 2008, 187 in 2018 and **303 in 2020**.

---

## 5. Macro — `analysis/macro_panel_v2.csv`

Pulled from the World Bank API directly rather than through WITS, which does not
answer to `rou`.

* **Romania's 20 empty country-years are filled.** It was a real importer in the
  spell panel with no GDP at all.
* GDP, GDP growth, GDP per capita and population are **100% complete** across
  147 importers plus Viet Nam.
* New: exchange rate (100%), inflation (97%), imports/GDP (89%), and the
  Logistics Performance Index (25% — it is only surveyed in 2007, 2010, 2012,
  2014, 2016 and 2018, so it is an interpolation candidate, not a yearly series).

`macro_panel.csv` is left in place; `macro_panel_v2.csv` is the superset.

---

## How these join

All four panels are keyed `(importer, year)`, 3,381 rows each = 147 x 23
(2002-2024; gravity stops at 2021). `shocks_annual.csv` is keyed on `year`
alone, 23 rows.

**Merged for real on 21/08/2026**, after `build_spells.py` and `merge_panel.py`
were rerun on the complete data. Match rates measured in that run:

| Panel | Episodes matched | Note |
|---|---|---|
| `fta_vn.csv` | 647,014 / 647,014 (**100%**) | |
| `ttbd_vn.csv` | 647,014 / 647,014 (**100%**) | in-force flags after 2015 are extrapolation, see below |
| `shocks_annual.csv` | 647,014 / 647,014 (**100%**) | |
| `gravity_vn.csv` | 544,780 / 647,014 (**84.2%**) | misses exactly 2022 and 2023 - CEPII stops at 2021 |

Two follow-ups this left open:

* **Gravity should be carried forward.** `dist`, `contig`, `comlang_off`,
  `comcol` do not change between 2021 and 2023; leaving them blank drops 102,234
  episodes from any model that controls for distance. A carry-forward in
  `merge_panel.py` fixes it.
* **Five macro variables never made it across.** `macro_panel_v2.csv` carries
  `inflation_pct`, `exchange_rate_lcu_per_usd`, `lpi_overall`, `population` and
  `exports_pct_gdp`; `panel_final.csv` takes only the four GDP columns. Exchange
  rate and LPI are standard controls in the trade-duration literature.
* **`ttb_any_in_force` after 2015 is not observed.** `ad_initiated` is positive
  in 2004-2015 and silent thereafter, yet the in-force flag stays non-zero to
  2023 (9,644 episodes) because a measure with no recorded revocation is treated
  as still running. Do not interpret this variable's coefficient for 2016-2023.

---

## Still missing after this batch

| Gap | Why it is still open |
|---|---|
| **Tariffs 2022-2023** | `fetch_tariffs.py:46` still hardcodes `range(2002, 2022)` — **machine, one-line fix, highest priority**. Until then the last two panel years carry a 2021 rate forward and contain no real tariff variation |
| NTM at HS6 x year | TRAINS Online needs an Azure AD account — **user action** |
| Tariff actions 2025, retaliation timing | WTO I-TIP needs a subscription key — **user action** |
| Antidumping 2016-2023 | TTBD was last updated June 2016; WTO semi-annual reports would have to be scraped |
| Gravity 2022-2023 | CEPII V202211 stops at 2021; the time-invariant columns can simply be carried forward |
| ~~Trade data 2022-2024~~ | done, all three passes; see section 6 |
| ~~Panel rebuild~~ | done 21/08; `rca`, `vn_market_share_pct`, `world_growth_pct` now 100% filled with real variance |
| Depth/utilisation of preferences | No public source at HS6 for Viet Nam |

---

## 6. Trade extended to 2022-2024 — and why the window should stop at 2023

Pulled 21/08/2026 with `scripts/pull_2022_2024.sh` (vn -> mirror -> world).
All three passes finished clean and the daily quota was never hit:

| Pass | Result |
|---|---|
| `vn` | 400 importer-years written, 38 empty, **0 failed**, 332,395 rows |
| `mirror` | 8 files, **0 failed**, 120,645 rows |
| `world` | 404 importer-years written, 37 empty, **0 failed**, 1,803,285 rows |

On disk: **3,216 trade files, 3,260 world files.**

**The `load_world` guard passes for every candidate window.** Checking each
importer-year the Vietnamese side has against the world side finds **zero** gaps
at 2021, 2023 *and* 2024 — so RCA, `world_growth_pct` and `vn_market_share_pct`
become computable as soon as the panel is rebuilt, whichever end year is chosen.
That was the open question; it is closed.

| Year | Importers with data | HS6 rows | Value (bn USD, importer-filed) |
|---|---|---|---|
| 2021 | 142 | 106,028 | 405.1 |
| 2022 | 138 | 109,528 | 456.9 |
| 2023 | 139 | 115,255 | 446.6 |
| **2024** | **126** | 115,497 | 495.9 |

The value path (up in 2022, down in 2023, up in 2024) tracks Viet Nam's actual
export cycle, and the 2021 total reproduces the figure already in the inventory,
so the pull is reading correctly.

### The coverage cliff

Importers present in 2021 that report nothing in the new years:

| Year | Missing | Which |
|---|---|---|
| 2022 | 4 | ALB, BLR, HND, **RUS** |
| 2023 | 3 | BLR, **RUS**, RWA |
| **2024** | **17** | ARE, BDI, BLR, BWA, CMR, COG, COM, DMA, ETH, GAB, MLI, MNG, RUS, RWA, SWZ, TON, VCT |

These are two different problems wearing the same face.

**Russia and Belarus are a permanent loss, not a lag.** Russia stopped
publishing detailed customs data in April 2022. This is the dangerous one:
Russia is an FTA partner under VN-EAEU (in force 2016), so every spell into
Russia dies in 2022 *while the agreement is in force*. Left alone, a hazard
model reads that as "the FTA killed the relationship" — the sign flips.
**RUS and BLR must be right-censored at 2021 by hand**, whatever end year is
chosen, and the Limitations section has to say so.

**The other fifteen 2024 absences are reporting lag** and will fill in over the
next six to twelve months. Until they do they manufacture spell deaths exactly
the way an unfinished download would — the failure mode `build_spells.py`
already guards against for downloads, but the guard compares against the partner
screen, which has no opinion about 2022-2024.

### Recommendation: end the window at 2023

* 2023 costs 3 missing importers; 2024 costs 17.
* Viet Nam has **not filed 2024** to Comtrade at all, so `trade_mirror` stops at
  2023 and the CIF/FOB cross-check disappears for that year.
* CEPII gravity stops at 2021 and TTBD at 2015 regardless.

The 2024 files stay on disk. Re-run the pull once Comtrade fills in and the year
can be added without refetching anything.

### Code that still hardcodes 2021

Extending the window is **not** just a data question — three constants gate it,
and one of them changes what the results mean:

| Where | Constant | Consequence | Status 21/08 |
|---|---|---|---|
| `build_spells.py:56` | `YEAR_MIN, YEAR_MAX = 2002, 2021` | Without it, 2022-2024 is silently ignored | ✅ raised to `2002, 2023` |
| `build_spells.py:402` | `right_censored = end == YEAR_MAX` | **All currently-censored spells get re-classified.** Some become deaths. This is a change of meaning, not a refresh | ✅ now `end >= last_year.get(imp, YEAR_MAX)`, so the six early-stopping reporters are censored at their own last filing rather than counted as deaths - 1,504 spells |
| `fetch_tariffs.py:46` | `YEARS = range(2002, 2022)` | Tariffs would be blank for the new years | ❌ **still unchanged** - this is the one outstanding item |

The panel that came out of the rerun: **205,607 spells** (151,858 deaths,
53,749 right-censored) and **647,014 episodes x 91 columns** over 2003-2023,
across 147 importers and 4,599 product families.

The covariate panels in this document already run to 2024, so they are not the
blocker.
