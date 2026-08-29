# What is actually on disk for Viet Nam

*Recounted by reading the files themselves on **22/08/2026**, after the 2025
trade pull, the tariff extension and the covariate batch that closed the last
items in the `Sinking Relationships.md` data brief. The exporter is fixed to
Viet Nam; the importer list is the 147 countries chosen in
[THIET_KE_VIET_NAM.md](THIET_KE_VIET_NAM.md). Which parts of the research
architecture each of these serves:
[MAPPING_IDEA_DATA.md](MAPPING_IDEA_DATA.md); the brief itself, item by item:
[BRIEF_SINKING_COVERAGE.md](BRIEF_SINKING_COVERAGE.md).*

---

## 1. The one-line answer

Viet Nam's exports are on disk as **1.47 million HS6 cells covering all 147
importing countries over 2002-2024, plus 2025 for the 89 importers that have
filed it**, alongside the world-import denominators, the tariff schedules those
importers levy **through 2023**, macro series, non-tariff-measure tables, six
covariate panels, the 2025 US reciprocal tariff schedule, and Viet Nam's own
export filing as a mirror check. **Every pull has finished.**

The panel built from them - `analysis/panel_final.csv`, **747,719 episodes x
128 columns** over **2003-2025** (extended 23/08 on the team's decision) -
carries a tariff in 96.9% of episodes. **83.8% were measured in their own year**;
the shortfall is entirely 2024 and 2025, for which TRAINS publishes nothing at
all and the rate is carried from 2023.

**The collection phase is done and the tariff gap is closed.** What remains is
not a downloading problem:

* **NTM at HS6 x year** needs a TRAINS Online account - user action;
* **preferential rates stop at 2021** because TRAINS files none for 2022-2023,
  which no amount of downloading changes (§3);
* **2024 and 2025 carry no tariff of their own** - TRAINS answers 404 for both,
  so the only genuinely 2025 tariff variation in the workspace is the US
  schedule in `analysis/us_tariffs_2025.csv`, at country level.

**The window now reaches 2025**, which is what makes the 2025 US tariff shock
observable at all: **7,157 relationships are observed to die during 2025**, 157
of them into the United States. Note the dating convention - an `event` at year
Y means the last year alive was Y, so the relationship died in **Y+1**, and
`event` is 0 throughout 2025 by construction. Anything that joins a tariff to an
event has to respect that one-year offset.

---

## 2. Trade: Viet Nam's exports as the importers report them

| Measure | Value |
|---|---|
| Files (one per importer-year) | **3,305** (3,216 through 2024 + **89 for 2025**) |
| HS6 records for Vietnamese goods | **1,687,841** |
| Distinct cells (importer x HS6 x year) | **1,473,471** |
| Distinct HS6 product codes seen | **6,225** (27,801 counting revisions separately; 27,800 mapped to a family) |
| Stable product families after concordance | **4,599** |
| Importing countries with data | **147 of 147** ✅ |
| Importers with a download hole | **0** (checked against the partner screen at 2021, 2023 and 2024) |
| Years | **2002-2024** complete, **2025** for the 89 importers that filed |
| Total value | **USD 4,366 bn** through 2024, plus **USD 524.1 bn** in 2025 |

3,216 files against a nominal 147 x 23 = 3,381 is not a shortfall: the
difference is importer-years in which the country genuinely bought nothing from
Viet Nam, or filed no report at all. The completeness check in
`build_spells.py` compares what is on disk against the years the screen says
really carried trade, and finds no gaps.

**By year** (billion USD, as the importers filed it; last column = importers
that filed at all):

| Year | Value | n | Year | Value | n | Year | Value | n |
|---|---|---|---|---|---|---|---|---|
| 2002 | 16.2 | 127 | 2010 | 71.7 | 144 | 2018 | 278.4 | 144 |
| 2003 | 21.5 | 132 | 2011 | 95.1 | 142 | 2019 | 307.6 | 143 |
| 2004 | 27.6 | 133 | 2012 | 126.5 | 144 | 2020 | 337.4 | 142 |
| 2005 | 33.8 | 139 | 2013 | 143.3 | 145 | 2021 | 405.1 | 142 |
| 2006 | 41.2 | 135 | 2014 | 161.7 | 142 | 2022 | 456.9 | **138** |
| 2007 | 50.8 | 141 | 2015 | 208.2 | 144 | 2023 | 446.6 | **139** |
| 2008 | 65.6 | 139 | 2016 | 228.6 | 146 | **2024** | 495.9 | **126** |
| 2009 | 58.3 | 139 | 2017 | 287.7 | 146 | | | |

**2025 was pulled on 22/08 and is not in the panel.** Comtrade now answers for
2025, and 89 of the 147 importers have filed - **including the United States**,
which reports USD 199.0 bn of Vietnamese goods for the year, 42% above 2024.
Only the importers Comtrade's own availability endpoint listed were requested,
so nothing was recorded as a confirmed-empty year that had simply not been filed
yet: **zero rows were added to `_empty_years.csv`**, which is what keeps the
build from manufacturing deaths at the trailing edge.

| Year | Importers that filed worldwide | Of our 147 | On disk |
|---|---|---|---|
| 2023 | 167 | 147 | ✅ all |
| 2024 | 140 | 126 | ✅ all 126 |
| 2025 | 98 | **89** | ✅ pulled 22/08 |

**The reporter count is why the spell window still stops at 2023.** At 2024
seventeen importers that filed in 2021 have not filed yet, and Viet Nam itself
has filed neither 2024 nor 2025 - so the mirror check disappears too. Whether to
buy 2025 anyway, for the sake of the one year in which the US tariff shock is
observable, is the open design decision in
[BRIEF_SINKING_COVERAGE.md](BRIEF_SINKING_COVERAGE.md) §4.1. Raising `YEAR_MAX`
in `build_spells.py` is the switch; the world-import denominators for 2024-2025
would have to be pulled with it.

**Two of the absences are permanent, not a lag.** Russia stopped publishing
detailed customs data in April 2022 and Belarus followed. Both are VN-EAEU
partners, so left alone every spell into them dies in 2022 *while the agreement
is in force* - which a hazard model reads as "the FTA killed the relationship".
`build_spells.py` now administratively censors six such reporters (RUS and BLR
at 2021, BGD and SLB at 2018, LCA at 2020, KNA at 2017), covering **1,504
spells**, and does not count those endings as deaths.

The series tracks Viet Nam's known export take-off (a 25-fold rise across the
window, with the 2009 dip and the 2012 jump when Samsung's phone assembly came
on stream). It runs above Viet Nam's own export statistics because these are
importer filings: CIF rather than FOB, and China in particular records more
arriving from Viet Nam than Viet Nam records leaving for China.

**The twelve largest markets in what has been collected:**

| Importer | Total 2002-2024 (bn USD) | Years on disk |
|---|---|---|
| USA | 1,015.8 | 23 |
| CHN | 811.7 | 23 |
| JPN | 319.6 | 23 |
| KOR | 243.2 | 23 |
| DEU | 170.1 | 23 |
| HKG | 151.8 | 23 |
| GBR | 97.9 | 23 |
| AUS | 90.3 | 23 |
| FRA | 89.6 | 23 |
| MYS | 85.2 | 23 |
| NLD | 82.5 | 23 |
| THA | 82.1 | 23 |

**HS revisions present:** H5 472,901 records · H4 412,485 · **H6 320,917** ·
H3 267,312 · H2 197,309 · H1 15,693 · H0 1,224. **Seven** revisions inside one
panel is exactly the problem the product-family mapping exists to solve - see
trap 5 in the README. H6 (HS2022) arrived with the 2022-2024 extension and
carries almost the entire tail of the panel, so the H6->H0 concordance had to be
added; without it a relationship running since 2002 would appear to die in 2021
and a new one to be born in 2022.

---

## 3. Tariffs: what the importers levy

| Measure | Value |
|---|---|
| MFN schedules (reporter-year files) | **2,482** across **134 reporters** |
| Of those, added 22/08 for 2022-2023 | **232** (115 + 117) |
| Reporter-years TRAINS answers 404 for | 901, now recorded in `_no_schedule.csv` |
| **Preferential schedules naming Viet Nam** | **72 reporter-years**, unchanged |
| **Years covered** | **2002-2023** ✅ |

**The gap that dominated the previous two inventories is closed.** On the 21/08
build the last two panel years carried a 2021 rate forward and had no real
tariff variation at all. Measured on the 22/08 panel:

| Year | Episodes | With a tariff | **Measured in its own year** |
|---|---|---|---|
| 2019 | 44,975 | 99.5% | 98.5% |
| 2020 | 44,489 | 99.7% | 98.3% |
| 2021 | 48,358 | 99.7% | 95.2% |
| **2022** | 49,989 | **99.7%** | **96.5%** (was 0%) |
| **2023** | 52,245 | **98.9%** | **95.6%** (was 0%) |
| whole panel | 647,014 | **99.6%** | **96.8%** |

Three things had to be true for that, and only the first was obvious:

1. **`fetch_tariffs.py` had to ask for the years.** It was hardcoded to
   `range(2002, 2022)`. TRAINS does answer for 2022 and 2023 - checked against
   the USA, the EU and China, each returning its own `TIME_PERIOD` rather than
   falling back to an earlier year. 2024 is still a 404.
2. **The partner-list cache had to be rebuilt.** It had been written under the
   old year range, so every 2022-2023 reporter-year looked like a country with
   no preferential filing rather than one never asked. It is now stamped with
   the window it was built for.
3. **The EU mapping had to be extended.** `selection/eu_tariff_mapping.csv`
   stopped at 2021, so for 2022-2023 the twenty-seven EU members mapped to
   themselves - and TRAINS has no code for them individually, so they were
   dropped from the target list silently, without even a 404 to show for it.
   **All 27 would have had no tariff for the last two years** while every other
   reporter had one. Fixed by adding 2022-2023 rows pointing at EUN; Great
   Britain is deliberately excluded, since it left the customs union on 1
   January 2021 and files its own schedule.

> ⚠️ **What did *not* improve: preferential rates.** TRAINS publishes **no
> preferential schedule at all for 2022 or 2023** - asked directly of Japan
> (392), Korea (410), India (152) and the EU (918) with partner 704, every one
> returns 404 while 2021 returns real data. In the panel, 2022-2023 carry
> **101,280 MFN episodes against 239 PREF**, where 2020 and 2021 had 11,703 and
> 12,640 PREF respectively.
>
> The consequence is precise and must be stated in Limitations: **for the last
> two years the tariff variable overstates the rate actually faced** by the
> roughly 39% of episodes that had an agreement in force. `fta_in_force` marks
> exactly which ones, so the bias is identifiable rather than hidden - but it
> cannot be corrected from any public source.

Only **13 countries** file a preferential schedule against Viet Nam directly:

| Reporter | Years | | Reporter | Years |
|---|---|---|---|---|
| JPN | 2010-2021 (12) | | KAZ | 2017-2021 (5) |
| AUS | 2010-2019 (10) | | KGZ | 2017-2021 (5) |
| CHN | 2005-2014 (8) | | RUS | 2017-2021 (5) |
| CHL | 2015-2021 (6) | | BLR | 2017-2021 (5) |
| KOR | 2014-2021 (6) | | EUN | 3 years in 2002-2021 |
| ARM | 2017-2021 (5) | | GBR | 2021 (1) |
| IDN | 2009 (1) | | | |

This is a property of TRAINS, not of the collection: every reporter-year was
asked. The rest of Viet Nam's preferential access is filed under **group codes**
(ASEAN, AANZFTA, GSP beneficiary lists) whose membership WITS does not publish
through the API, so those episodes fall back to MFN and the rate faced is
overstated. The `tariff_type` column marks which of the two applied. In the
panel as built, **43,666 episodes (6.8%) carry a preferential rate**, led by the
EU (17,238, almost all EVFTA years), Japan (5,862), Korea (5,298) and Australia
(5,143).

---

## 3b. The 2025 US reciprocal tariff - `analysis/us_tariffs_2025.csv`

New on 22/08, and the item the data brief calls its most important covariate.
It was believed to need a WTO I-TIP subscription; it does not. The measure is
written into **chapter 99 of the US tariff schedule**, which USITC publishes
over an open REST endpoint, with the executive orders behind it in the Federal
Register API.

| Measure | Value |
|---|---|
| Chapter-99 headings parsed | **166** |
| Headings carrying a country rate | **109**, across **85 countries** |
| Exemption and definition provisions | 12 |
| Viet Nam | +46% (9 Apr 2025, terminated) · +10% floor · **+20% (7 Aug 2025)** · +40% transshipment |

Competitors are in the same table, which is what a trade-diversion control
needs: Cambodia 49→19%, Bangladesh 37→20%, Thailand 36→19%, Taiwan 32→20%,
Indonesia 32→19%, India 26→25%, Malaysia 24→19%, China 34%.

**Limit:** country-level only. The exempt subheadings live in *U.S. note
2(v)(iii)(a)*, which the REST endpoint does not return. The note PDF is on disk
(`data_raw/us_tariffs_2025/hts_chapter99_notes.pdf`, 14 MB); the HS8 list has
not been extracted from it. For Viet Nam that matters - electronics is both its
largest export to the US and among the likeliest exemptions.

---

## 4. Everything else already collected

| Component | What is on disk | Status |
|---|---|---|
| **World denominators** (`data_raw/trade_world/`) | **3,260 files**, 107,022 family-years matched into the Vietnamese panel | ✅ **complete** - this was the last pull |
| **Macro** (`analysis/macro_panel_v2.csv`) | **3,404 country-years**, 147 countries incl. Viet Nam; **17 variables** - the 9 as before plus the **six LPI sub-indices**, CO2 per capita and renewable-energy share | ✅ all 17 now reach the panel |
| **Complexity** (`analysis/complexity_product.csv`, `complexity_country.csv`) | **28,563 product-years** (PCI, HS92 four-digit, 2002-2024) and 3,404 country-years (ECI, COI, diversity) | ✅ new 22/08, **100% join** |
| **US 2025 tariff** (`analysis/us_tariffs_2025.csv`) | 166 chapter-99 headings; 109 country rates across 85 countries | ✅ new 22/08 - see §3b |
| **Agreements** (`analysis/fta_vn.csv`) | 3,381 rows x 7 cols, from DESTA | ✅ time-varying, 100% matched |
| **Trade remedies** (`analysis/ttbd_vn.csv` + 2) | 3,381 rows x 8 cols; 69 AD/CVD cases against VN, 3,231 HS codes | ⚠️ **initiations stop at 2015** - see §5 |
| **Gravity** (`analysis/gravity_vn.csv`) | 2,940 rows x 20 cols, CEPII V202211 | ⚠️ source stops at 2021; carried forward to 2023 with a `gravity_source_year` stamp, so the panel is **100% covered** and the carried rows stay identifiable |
| **Common shocks** (`analysis/shocks_annual.csv`) | 23 rows x 18 cols; 17 World Bank CMO price indices + Global EPU | ✅ complete, 100% matched |
| **NTM sector** (`analysis/ntm_sector.csv`) | 1,200 rows, 75 countries | ✅ cross-section only |
| **NTM by MAST chapter** (`analysis/ntm_by_type.csv`) | 3,944 rows | ✅ cross-section only |
| **NTM country** (`analysis/ntm_country.csv`) | 150 rows, 75 countries, survey years 2012-2017 | ✅ cross-section only |
| **Screen** (`selection/vn_partner_screen.csv`) | 3,569 country-years; 3,256 importer-reported, 2,786 Viet-Nam-reported; **190 countries** trade with Viet Nam in at least one year | ✅ complete |
| **HS concordance** | **6 tables** H1→H0 … **H6→H0** | ✅ complete |
| **Mirror** (`data_raw/trade_mirror/`) | **40 files, 933,834 rows** - Viet Nam's own export filing | ✅ complete through 2023; Viet Nam has filed neither 2024 nor 2025 |

### 4.1. And what was built out of them

| File | Size | Contents |
|---|---|---|
| `analysis/spells.csv` | 15 MB | **205,607 spells** - 151,858 deaths, 53,749 right-censored (26.1%) |
| `analysis/episodes.csv` | 93 MB | 647,014 episode-years, **22 core columns** |
| `analysis/panel_final.csv` | **505 MB** | **647,014 x 123 columns**, 2003-2023 - the modelling file |

Rebuilt 22/08/2026. Both steps are now within reach of a small machine:
`build_spells` 1.8 GB peak, `merge_panel` **371 MB peak and 71 seconds** - down
from 5.2 GB and 25 minutes, which is what took the machine down mid-merge on the
first attempt. The merge now shards the episodes by importer and loads only the
tariff schedules that importer can read, instead of holding all 11.6 million
tariff cells and all 647,014 episode dictionaries at once.

| Check | Target | Actual |
|---|---|---|
| Single exporter | `['VNM']` | ✅ |
| Right-censored | > 0 | ✅ 53,749 |
| Importers | 147 | ✅ 147 |
| Episodes with a tariff | > 90% | ✅ **99.6%** |
| Tariff measured in its own year | - | ✅ **96.8%** |
| Episodes with PREF | > 0% | ✅ 6.8% (43,666) |
| `rca` has variance | not all 1.0 | ✅ p25 0.23 / med 0.83 / p75 2.94 |
| `vn_market_share_pct` | populated | ✅ 100% |
| `pci`, `importer_eci`, `dist` | populated | ✅ **100%** each |
| `net_weight_kg`, `unit_value_usd_per_kg` | populated | ✅ 96.5% |
| LPI wave attached | > 0 | ✅ 99.2% |

**The 32 new columns**, all added 22/08: quantity and unit value; the explicit
`spell_start_year`, `spell_end_year` and `right_censored` the brief asks for;
product complexity and the four ECI columns; the six LPI sub-indices with their
survey-wave stamp; six further macro series on the importer side and three on
the exporter side; CO2 and renewable-energy share; and `gravity_source_year`.

**Duration shape, which the modelling has to reckon with:** median spell length
is **1 year** and **53.2% of spells last exactly one year**; 8.4% survive ten
years or more. At a USD 10,000 threshold most "relationships" are one-off
shipments. Whether to keep them, raise the threshold, or model them separately
is a decision that changes what the estimated hazard means.

---

## 5. What is missing, and why

| Gap | Size | Cause | Fix | Who |
|---|---|---|---|---|
| **NTM at HS6 x year** | 20.4% of episodes have no NTM at all, and what exists is one sector-level cross-section | The three public WITS files have no year dimension at product level. Rechecked 22/08: UNCTAD's open-data API publishes no NTM bulk file either | TRAINS Online researcher file - needs an Azure AD account | **user** |
| **Preferential rates 2022-2023** | 101,280 episodes read MFN where ~39% had an agreement in force | **TRAINS files no preferential schedule for either year** - asked directly of JPN, KOR, IND and EUN, all 404 | none available. `fta_in_force` marks the affected episodes; state it in Limitations | - |
| **Trade remedies after 2015** | 8 of 21 panel years | World Bank TTBD stopped updating June 2016. `ttb_any_in_force` stays non-zero to 2023 only because a measure with no recorded revocation is treated as still in force - i.e. **extrapolation** | censor the variable at 2015, or scrape WTO semi-annual reports | machine |
| **Product scope of the 2025 US tariff** | the rate is country-level | The exempt subheadings are in a chapter-99 legal note the REST endpoint does not return | parse the note PDF already on disk | machine |
| Preferences filed under group codes | unquantifiable | TRAINS does not publish group membership | none available; documented as a limitation | - |
| ~~Tariffs 2022-2023~~ | - | - | ✅ done 22/08 - §3 | - |
| ~~EU tariff mapping stops at 2021~~ | would have left **all 27 EU importers** with no tariff for 2022-2023 | `selection/eu_tariff_mapping.csv` ended at 2021, so EU members mapped to themselves and were dropped from the target list without even a 404 | ✅ found and fixed 22/08 | - |
| ~~Gravity 2022-2023~~ | - | - | ✅ carried forward 22/08, `dist` now 100% | - |
| ~~5 macro variables never merged~~ | - | - | ✅ done 22/08, and eight more with them | - |
| ~~Product complexity~~ | - | - | ✅ done 22/08, 100% join | - |
| ~~Green LPI inputs~~ | - | - | ✅ six sub-indices + two environmental series, 22/08 | - |
| ~~2025 US tariff needs a WTO I-TIP key~~ | - | it never did - the schedule is in the US tariff schedule itself | ✅ done 22/08 without any account | - |
| ~~World imports at HS6~~ · ~~Romania macro~~ · ~~Trade 2022-2024~~ | - | - | ✅ done 19-21/08 | - |

The importer side of the trade panel is complete for all 147 countries and
verified against the partner screen: **zero download holes**. What is left is
one account registration and two limitations that no further downloading can
close.

Four operational notes worth keeping:

* Comtrade's daily quota answers **403** with the time until replenishment -
  not 429, which is a few-second throttle. The fetcher stops on 403 and says
  when to come back, instead of marking hundreds of importer-years failed.
* A long download must be started with **`setsid`**, not plain `nohup ... &`.
  Without it the process stays in the session's process group and is killed
  when the terminal or agent session ends - which is what silently truncated
  the world pull twice.
* **Both APIs leave sockets open that never answer.** Comtrade's own timeout is
  900s x 4 retries and WITS's 600s x 4, so one hung request costs an hour of a
  run that is otherwise minutes. Both pulls were finished under a watchdog that
  restarts the fetcher after 150-180s of silence in its log; restarting is free
  because every settled file is already on disk. What made restarts *cheap* was
  adding two caches: `_no_schedule.csv`, which records the 901 reporter-years
  TRAINS answers 404 for so they are never re-asked, and per-reporter appends to
  the partner-list cache so an interrupted availability sweep resumes instead of
  starting over.
* **Memory is a real constraint on this machine.** `merge_panel.py` used to hold
  every tariff cell and every episode at once and peaked at 5.2 GB, which is
  more than the machine has; it now works one importer at a time at 371 MB.
  Anything added to the merge should keep that shape.

## 6. What this supports right now, and what it does not

**Built and verified, on all 147 importers:**

* spells and episodes for (importer, product family) pairs of Vietnamese goods,
  with duration, event and right-censoring flags, in counting-process form
  (`t_start`, `t_stop`, `event`) so Cox runs against it directly;
* product share, partner share, both Herfindahl indices, product-level growth
  rates for Viet Nam - **all at 100% coverage**;
* **Balassa RCA against a true world denominator**, world growth per product,
  and `vn_market_share_pct` - the three variables that were unusable in the
  19/08 build and are now complete;
* tariff faced (MFN throughout, preferential where one of the 13 reporters filed
  it), GDP controls, agreement status, trade-remedy flags, gravity controls,
  common-shock indices, and the NTM columns;
* **quantity and unit value** on 96.5% of episodes, which is what separates a
  relationship dying because the buyer left from one dying because the price
  collapsed;
* **product complexity** at 100%, the covariate the data brief named that the
  project had nothing for until 22/08;
* the **six LPI sub-indices** a Green Logistics Performance Index is built from,
  stamped with the survey wave each value comes from.

**Not supported, and no amount of further collection changes it:**

* comparison across exporting countries - the panel has one exporter by design;
* within-sector variation in NTMs - the source is sector-level;
* **anything estimated about the 2025 US tariff shock.** The schedule itself is
  now on disk (§3b) and the 2025 trade data with it, but the panel window ends
  at **2023**, so no relationship in it can be observed dying under that shock.
  This is the one remaining blocker between the workspace and the central
  question of `Sinking Relationships.md`, and it is a design decision rather
  than a gap - see [BRIEF_SINKING_COVERAGE.md](BRIEF_SINKING_COVERAGE.md) §4.1
  and [MAPPING_IDEA_DATA.md](MAPPING_IDEA_DATA.md) §3;
* **preference utilisation in 2022-2023** - TRAINS files no preferential
  schedule for either year (§3).

**A guard sits in `build_spells.py`:** an importer-year that was never
downloaded is indistinguishable, once spells are built, from a year in which the
relationship did not exist - so an unfinished download would manufacture spell
deaths and rebirths. The build cross-checks each importer against the screen and
**holds back every importer that still has a hole**, printing which ones and
which years, rather than silently producing a plausible-looking wrong answer.
As of 22/08/2026 it holds back nothing: all 147 importers pass. It also reports
the 27 importers with an interior gap and the 6 that stopped filing early, and
censors the latter administratively rather than recording a death.
