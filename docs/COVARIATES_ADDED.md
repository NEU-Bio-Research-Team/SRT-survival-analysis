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

*Revised 22/08/2026. Struck-through rows were closed that day; see sections
7-11.*

| Gap | Why it is still open |
|---|---|
| NTM at HS6 x year | ~~needs an Azure AD account~~ — **corrected 23/08: it does not.** The TRAINS data endpoint answers unauthenticated; the blocker is a Cloudflare rate limit. See §13 |
| Antidumping 2016-2023 | TTBD was last updated June 2016; WTO semi-annual reports would have to be scraped |
| Product scope of the 2025 US tariff | The exempt subheadings live in a chapter-99 legal note, not in the REST endpoint. The note PDF is on disk; extracting the HS8 list from it has not been done — section 9 |
| Depth/utilisation of preferences | No public source at HS6 for Viet Nam |
| ~~Tariffs 2022-2023~~ | done 22/08 — section 7 |
| ~~Gravity 2022-2023~~ | done 22/08, carried forward with a source-year stamp — section 11 |
| ~~Five macro variables never merged~~ | done 22/08 — section 11 |
| ~~Product complexity~~ | done 22/08 — section 8 |
| ~~Green LPI inputs~~ | done 22/08 — section 10 |
| ~~US 2025 reciprocal tariffs, WTO I-TIP key needed~~ | done 22/08 **without any account** — the schedule is in the US tariff schedule itself, section 9 |
| ~~Trade data 2022-2024~~ | done, all three passes; see section 6 |
| ~~Panel rebuild~~ | done 21/08; `rca`, `vn_market_share_pct`, `world_growth_pct` now 100% filled with real variance |

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

---

# The 22/08/2026 batch — what the "Sinking Relationships" brief still asked for

*Sections 7-11 answer a different question from sections 1-6. Those closed gaps
the WITS pull left open; these close the gaps between what is on disk and what
the data brief in `Sinking Relationships.md` explicitly lists. Two of them
turned out to need no account after all.*

```bash
python3 scripts/fetch_tariffs.py --pass all      # section 7
python3 scripts/fetch_covariates.py              # sections 8 and 10
python3 scripts/fetch_us_tariffs_2025.py         # section 9
python3 scripts/build_covariates.py              # reshapes all of it
python3 scripts/build_spells.py                  # section 11 (quantity)
python3 scripts/merge_panel.py                   # section 11 (the rest)
```

---

## 7. Tariffs extended to 2023 — the gap that dominated three inventories

**The gap it closes.** `fetch_tariffs.py` was hardcoded to `range(2002, 2022)`.
Nothing on disk covered 2022 or 2023, so the merge carried a 2021 rate forward
for 90,721 episodes and **the last two years of the panel had no measured tariff
at all**. Any finding about policy moving the hazard at the end of the window
would have been an artefact of that.

TRAINS does answer for both years — checked against the USA, the EU and China,
each returning its own `TIME_PERIOD` rather than falling back to an earlier
year. 2024 is still a 404.

| | 21/08 build | 22/08 build |
|---|---|---|
| Episodes with a tariff | 95.7% | **99.6%** |
| Measured in their own year | 81.7% | **96.8%** |
| 2022 measured in-year | **0%** | **96.5%** |
| 2023 measured in-year | **0%** | **95.6%** |
| MFN schedule files | 2,250 | **2,482** (+232) |

**Three things had to be true, and only the first was obvious.**

1. **Ask for the years.** One line.
2. **Rebuild the partner-list cache.** It had been written under the old year
   range, so every 2022-2023 reporter-year looked like a country that files no
   preferences rather than one never asked. It now carries a marker recording
   the window it was built for, and appends per reporter as it goes — the sweep
   is 132 slow calls and an interruption used to throw all of them away.
3. **Extend the EU mapping.** This one nearly slipped through.
   `selection/eu_tariff_mapping.csv` stopped at 2021, so for 2022-2023 the
   twenty-seven EU members mapped to *themselves* — and TRAINS has no individual
   code for them, so `load_targets()` skipped them silently, without even a 404
   to show for it. **All 27 would have carried no tariff for the last two years**
   while every other importer had one, and the pass would have reported "0
   without data". It surfaced only because a smoke test on a three-country
   sample happened to draw Germany. Fixed by adding 2022-2023 rows pointing at
   EUN; Great Britain is deliberately excluded, having left the customs union on
   1 January 2021 and filed its own schedule since.

**What did not improve, and cannot.** TRAINS publishes **no preferential
schedule at all for 2022 or 2023** — asked directly of Japan (392), Korea (410),
India (152) and the EU (918) with partner 704: every one returns 404 where 2021
returns real data. In the panel, 2022-2023 carry **101,280 MFN episodes against
239 PREF**, where 2020 and 2021 had 11,703 and 12,640 PREF.

So the tariff variable **overstates the rate actually faced** in the last two
years, for the roughly 39% of episodes with an agreement in force. That is a
Limitations paragraph, not a bug: `fta_in_force` marks exactly which episodes,
so the bias is identifiable — but no public source can correct it.

**Two caches make the pull restartable**, which mattered because WITS leaves
sockets open that never answer and the fetcher waits 600s x 4 on each:
`_no_schedule.csv` records the 901 reporter-years TRAINS answers 404 for, so a
restart skips them instead of re-asking; and the partner-list cache now appends
per reporter. With both, a restart costs seconds rather than the whole run.

---

## 8. Product complexity — `analysis/complexity_product.csv`, `complexity_country.csv`

**The gap it closes.** The brief lists product complexity among the four
required gravity/survival covariates, alongside distance, GDP and the RTA dummy.
It was the only one of the four with **nothing at all on disk** — not a partial
series, not a stale one, nothing.

Source: **Harvard Growth Lab, Atlas of Economic Complexity v18**, Harvard
Dataverse `doi:10.7910/DVN/T4CHWJ`. Public, no account.

| File | Contents | Coverage |
|---|---|---|
| `complexity_product.csv` | PCI by HS92 four-digit product-year | 1,242 products x 2002-2024, **no gaps** |
| `complexity_country.csv` | ECI, COI, diversity by country-year | 148 of 148 countries |

**Why the four-digit level costs nothing here.** The Atlas publishes PCI at HS92
**4** digits while the panel is built on six-digit families — but those families
are keyed to **H0, which *is* HS1992**, so the join is the first four characters
of the family code and involves no concordance and no revision mapping. Measured
against the panel: **all 1,216 four-digit groups present in the episodes match a
PCI value, so coverage is 100.0%** of 647,014 episodes.

ECI comes along at country-year and gives the importer side of a relationship a
complexity control to sit beside its GDP — `importer_eci`, `importer_coi`,
`importer_diversity`, and `exporter_eci` for Viet Nam itself.

---

## 9. The 2025 US reciprocal tariff — `analysis/us_tariffs_2025.csv`

**The gap it closes.** The brief calls this "the most important covariate of the
whole topic" and describes it as `46% -> 10% -> 20%/40%`. Until today the
project had none of it, and the standing note said it needed a **WTO I-TIP
subscription key**. That turns out to be wrong: the measure is written into the
**US tariff schedule itself**, in chapter 99, and both places that publish it
are open.

| Source | What it gives | Account needed |
|---|---|---|
| USITC HTS REST (`hts.usitc.gov/reststop`) | 166 chapter-99 headings: country, rate, effective date, and the Federal Register citation when a provision was superseded | **no** |
| Federal Register API | the 70 executive orders and annexes behind them, dated | **no** |

**What the table holds:** 166 headings, of which **109 carry a country rate
covering 85 countries**, plus 12 exemption and definition provisions. Both
subchapters are in it — 9903.01 for the April action, 9903.02 for the August
one.

**Viet Nam, exactly as the brief describes it:**

| Heading | Rate | From | Status |
|---|---|---|---|
| 9903.01.72 | **+46%** | 9 April 2025 | terminated (90 Fed. Reg. 37963) |
| 9903.01.25 | +10% | universal floor, all countries | in force |
| 9903.02.69 | **+20%** | 7 August 2025 | in force |
| 9903.02.01 | **+40%** | transshipment penalty, any country | in force |

**Every competitor is in it too**, which is what the brief's trade-diversion
control group needs — the rate a Vietnamese relationship faces means little
without the rate its rival faces:

| | April | August | | | April | August |
|---|---|---|---|---|---|---|
| Cambodia | 49% | 19% | | Indonesia | 32% | 19% |
| Bangladesh | 37% | 20% | | Malaysia | 24% | 19% |
| Thailand | 36% | 19% | | India | 26% | 25% |
| Taiwan | 32% | 20% | | Korea | 25% | 15% |
| China | 34% (10 Apr) | — | | Japan | 24% | 15% |

**The limit, stated plainly: this is country-level, not product-level.** The
exempt subheadings — pharmaceuticals, semiconductors, critical minerals, energy,
and the section-232 goods already carrying steel/aluminium/auto duties — are
enumerated in *U.S. note 2(v)(iii)(a)*, a legal note the REST endpoint does not
return. The note PDF is on disk at
`data_raw/us_tariffs_2025/hts_chapter99_notes.pdf` (14 MB); extracting the HS8
list out of it has **not** been done. Until it is, treat the rate as applying to
the country, not to a particular HS6 line — and for Viet Nam that matters,
because electronics is both its largest export to the US and the category most
likely to be exempt.

**The second limit is the panel, not the source:** the spell window ends in
2023. Nothing in `panel_final.csv` can currently meet this table. Section 12
below is about whether that should change.

---

## 10. Green LPI inputs — six LPI sub-indices plus two environmental series

**The gap it closes.** The brief's robustness question asks whether the results
survive controlling for a **Green Logistics Performance Index**, "built from the
World Bank LPI components". What was on disk was `lpi_overall` — the headline
score only. No published GLPI construction starts from the headline; they all
start from the components, so the robustness check was not runnable.

Added to `macro_panel_v2.csv`, all from the World Bank API:

| Column | Series |
|---|---|
| `lpi_customs` | LP.LPI.CUST.XQ |
| `lpi_infrastructure` | LP.LPI.INFR.XQ |
| `lpi_intl_shipments` | LP.LPI.ITRN.XQ |
| `lpi_logistics_competence` | LP.LPI.LOGS.XQ |
| `lpi_tracking_tracing` | LP.LPI.TRAC.XQ |
| `lpi_timeliness` | LP.LPI.TIME.XQ |
| `co2_per_capita_t` | EN.GHG.CO2.PC.CE.AR5 — 100% filled |
| `renewable_energy_pct` | EG.FEC.RNEW.ZS — 88% filled |

The six sub-indices are **25.2% filled**, and that is not a defect: the LPI is a
survey run in waves — 2007, 2010, 2012, 2014, 2016, 2018 and 2022 — not an
annual series. How they enter the panel is section 11.

**One decision is left open deliberately.** Which environmental series enter the
index, and with what weights, differs across the published GLPI papers. Naming
the paper this project follows is a research decision, not a data one, so the
components are merged raw and combined later. The two environmental series are
fetched so that whichever construction is chosen, the inputs are already here.

---

## 11. Panel plumbing — four things the merge was dropping

| Fix | Before | After |
|---|---|---|
| **Quantity** | the brief asks for volume as well as value; `net_weight_kg` sat unused in the raw files | `net_weight_kg` and `unit_value_usd_per_kg` on every episode — **96.5% coverage** |
| **Gravity 2022-2023** | 102,234 episodes with no distance at all | carried forward from 2021 with a `gravity_source_year` stamp, so a carried row is never mistaken for a measured one |
| **Five macro variables** | downloaded, never merged | the importer side now takes the whole macro table; the exporter side the standard controls |
| **LPI waves** | not merged at all | nearest **earlier** wave, stamped in `importer_lpi_source_year` |

**Why the LPI is joined to the earlier wave and not the nearest one.** The
nearest wave to 2015 is 2016, and using it would let a relationship's 2015
hazard depend on a survey run after the year in question. Backward-looking is
the only reading a hazard model can defend. Years before the first wave (2003-
2006) take the 2007 wave, since the alternative is dropping four years — and the
stamp makes those rows identifiable, since `importer_lpi_source_year` equals
`year` only in the wave years themselves.

**Unit value is worth more than it looks.** With value alone, a relationship
that ends looks the same whether the buyer walked away or the price collapsed
under a volume that held. Value over weight separates them, and that distinction
is standard in the trade-duration literature.

---

## 12. What the merge cost, and why that had to change

The first attempt at the 22/08 merge **took the machine down**. `merge_panel.py`
held every tariff cell (11.6 million dictionary entries) and every episode
(647,014 dictionaries of 120-odd keys) in memory at once, and peaked at **5.2 GB
on a 5.6 GB machine**.

It now works one importer at a time:

* episodes are **sharded by importer** in a single streaming pass, then read
  back a country at a time;
* tariffs are loaded **only for the schedules that importer can read** — about
  120,000 cells instead of 11.6 million. The EU schedule is shared by 27
  importers, so that one is cached between iterations and nothing else is;
* each importer's rows are enriched and **written out immediately**.

| | before | after |
|---|---|---|
| Peak memory | 5.2 GB | **371 MB** |
| Wall time | 25m 40s | **71 seconds** |
| Output | identical | identical |

The result is byte-for-byte the same panel. Anything added to the merge later
should keep this shape — the machine has no headroom for the old one.

---

## 13. NTM from TRAINS Online — the login that was never there

**What was believed.** Every document in this project said the same thing: NTM
at HS6 × year needs a TRAINS Online account, UNCTAD's front end runs on Azure
AD, and `POST /denormalisedMeasures` answers `200` with an empty array unless
the caller is signed in. It was listed as the one remaining item only the user
could unblock.

**What is true.** The endpoint answers **without any authentication at all**.
A request captured from a signed-in browser session carried **no `Authorization`
header and no cookie**; replayed verbatim from a machine that has never logged
in, it returned 157 KB of real measures.

**Why the wrong conclusion held for so long.** The endpoint returns `200` with
`[]` for a malformed body, which is indistinguishable from an auth wall if you
assume one. The specific mistake: `affectedCountries` must carry the **full list
of country ids** even when `allAffectedCountries` is `true`. Send it empty and
the answer is an empty array, every time, signed in or not.

The lesson generalises past this API: **an empty success is not evidence of a
permission problem.** It was worth one deliberate test with a known-good body
before writing the limitation into four documents.

### What the records contain

Each record is a *measure*, not a product line, and carries the time dimension
the public WITS files lack:

| Field | Example |
|---|---|
| `hsCode` | `010121, 010221, 010229, …` — every HS6 line the measure covers |
| `implementationDate` | `2024-03-11` |
| `repealDate` | `9999-12-31` when still in force |
| `yearsOfDataCollection` | `2024` |
| `ntmCode` / `ntmType` | `A14` / `A` (MAST chapter) |
| `affectedCountriesNames` | `World [Valid From: 11 Mar 2024]` |
| `isHorizontalMeasure`, `isUnilateral`, `objectiveCodes` | present |

An implementation date and a repeal date together are what turn a cross-section
into a panel: an NTM can be dated in force for a given HS6 line in a given year.

### Coverage

`selection/trains_countries.csv`, saved 23/08 from the open `/imposingCountries`
endpoint: **165 imposing countries, 133 of them in this panel**, plus the
**European Union as a bloc** (`trains_id` 279), which is how EU measures are
filed - exactly as tariffs are.

Fifteen panel importers have no TRAINS record at all: AGO, BLZ, BMU, CAF, DOM,
GBR, KNA, LCA, MAC, MDG, MDV, MNG, PYF, UKR, VCT. The United Kingdom's absence
is worth noting separately - post-Brexit UK measures are not filed here.

### The real constraint: a rate limit, not a login

| Limit | Measured |
|---|---|
| `pageSize` | capped at **20**; 50 and above return `400` |
| Rate | **Cloudflare error 1015** after roughly six requests in quick succession, and still returned at a 6-second spacing |
| Backoff | 45s, 90s and 135s waits all still met `429` |

### Settled: the scripted pull is not viable from this machine

The probe was allowed to run its full backoff schedule so the answer would be a
measurement rather than an impression:

| Attempt | Wait before it | Spacing after | Result |
|---|---|---|---|
| 1 | - | 8s | 429 |
| 2 | 60s | 12s | 429 |
| 3 | 120s | 18s | 429 |
| 4 | 240s | 27s | 429 |
| 5 | 480s | 40s | 429 |
| 6 | 960s | 61s | 429 - gave up |

**Six consecutive refusals across roughly 31 minutes of cumulative waiting,
ending at a one-minute spacing.** Throughout, the *GET* reference endpoints kept
answering `200`, so this is a per-route limit on the expensive POST, not a
general block or an outage.

At `pageSize` 20, a full pull is several thousand requests. A route that refuses
the second request after a minute's pause cannot serve that, and continuing to
try would be both futile and rude to a public-good research database.

**So the route is the browser, not the script.** A real session carries the
Cloudflare clearance cookie and a browser fingerprint, and the portal's own
Export button returns a whole country in one action instead of dozens of pages.
[PROMPT_TRAINS_EXPORT_AGENT.md](PROMPT_TRAINS_EXPORT_AGENT.md) is written for
that, and its first step is a two-minute check worth doing before any exporting:
whether the browser's request carries a `cf_clearance` cookie. The captured
request had **no cookie header at all**, which is the most likely reason this
machine is treated as a bot. If a session with that cookie can be captured, the
scripted pull may become viable after all and the 134 manual exports are
unnecessary.
