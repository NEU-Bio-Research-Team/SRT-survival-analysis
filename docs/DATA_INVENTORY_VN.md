# What is actually on disk for Viet Nam

*Recounted by reading the files themselves on **21/08/2026**, after the
2022-2024 extension and the panel rebuild. The exporter is fixed to Viet Nam;
the importer list is the 147 countries chosen in
[THIET_KE_VIET_NAM.md](THIET_KE_VIET_NAM.md). Which parts of the research
architecture each of these serves:
[MAPPING_IDEA_DATA.md](MAPPING_IDEA_DATA.md).*

---

## 1. The one-line answer

Viet Nam's exports are on disk as **1.47 million HS6 cells covering all 147
importing countries over 2002-2024**, alongside the world-import denominators,
the tariff schedules those importers levy, macro series, non-tariff-measure
tables, four covariate panels and Viet Nam's own export filing as a mirror
check. **Every pull has finished.** The panel built from them -
`analysis/panel_final.csv`, **647,014 episodes x 91 columns** over 2003-2023 -
passes all five build checks.

**The collection phase is done. The one remaining data gap is tariffs, which
stop at 2021** while the panel runs to 2023 - so the last two years carry a
2021 rate forward rather than a real one. That is now the highest-priority fix,
and it is a one-line change plus a re-pull.

---

## 2. Trade: Viet Nam's exports as the importers report them

| Measure | Value |
|---|---|
| Files (one per importer-year) | **3,216** |
| HS6 records for Vietnamese goods | **1,687,841** |
| Distinct cells (importer x HS6 x year) | **1,473,471** |
| Distinct HS6 product codes seen | **6,225** (27,801 counting revisions separately; 27,800 mapped to a family) |
| Stable product families after concordance | **4,599** |
| Importing countries with data | **147 of 147** ✅ |
| Importers with a download hole | **0** (checked against the partner screen at 2021, 2023 and 2024) |
| Years | **2002-2024**, complete |
| Total value | **USD 4,366 bn** |

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

**The reporter count is why the spell window stops at 2023.** At 2024 seventeen
importers that filed in 2021 have not filed yet, and Viet Nam itself has filed
nothing - so the mirror check disappears too. Buying one year for that much
manufactured mortality is a bad trade. The 2024 files stay on disk; raise
`YEAR_MAX` in `build_spells.py` once Comtrade fills in.

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
| MFN schedules (reporter-year files) | **2,250** across **134 reporters** |
| Reporter-years with no schedule filed | 224 (a genuine 404, not a failure) |
| **Preferential schedules naming Viet Nam** | **72 reporter-years**, 237,414 tariff lines |
| Reporter-years checked for a VN preference | 2,435 (every one) |
| **Years covered** | **2002-2021 only** ⚠️ |

> ⚠️ **Tariffs stop two years short of the panel.** `fetch_tariffs.py:46` is
> still `YEARS = list(range(2002, 2022))`, and nothing on disk covers 2022 or
> 2023. `merge_panel.py` carries a rate forward up to three years, which is why
> those years still show a tariff at all - **75.3% of 2022 episodes and 74.3% of
> 2023 episodes, every one of them a 2021 value**. Across the whole panel that
> is 90,721 carried-forward episodes, 14.0%.
>
> The consequence is not cosmetic: **the last two years of the panel contain no
> real tariff variation**, so any finding about policy shocks moving the hazard
> at the end of the window would be an artefact. Fix is one line plus a re-pull.

| Year band | Episodes | With a tariff |
|---|---|---|
| 2003-2021 | 605,780 | 98.6-100% |
| **2022** | 49,989 | **75.3%**, all carried forward |
| **2023** | 52,245 | **74.3%**, all carried forward |

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

This is the sharpest limitation in the tariff data, and it is a property of
TRAINS, not of the collection: every reporter-year was asked, including the 380
that had no partner list to check, and they returned nothing. The rest of Viet
Nam's preferential access is filed under **group codes** (ASEAN, AANZFTA, GSP
beneficiary lists) whose membership WITS does not publish through the API, so
those episodes fall back to MFN and the rate faced is overstated. The
`tariff_type` column marks which of the two applied, so affected episodes stay
identifiable. The EU is the costliest case: only 3 years of a VN-specific
schedule, although the EU granted Viet Nam GSP for most of the window and
EVFTA preferences from 2020.

---

## 4. Everything else already collected

| Component | What is on disk | Status |
|---|---|---|
| **World denominators** (`data_raw/trade_world/`) | **3,260 files**, 107,022 family-years matched into the Vietnamese panel | ✅ **complete** - this was the last pull |
| **Macro** (`analysis/macro_panel_v2.csv`) | **3,404 country-years**, 147 countries incl. Viet Nam; 9 variables (GDP, GDP growth, GDP per capita, exports/imports %GDP, exchange rate, inflation, population, LPI) | ✅ **Romania now complete** |
| **Agreements** (`analysis/fta_vn.csv`) | 3,381 rows x 7 cols, from DESTA | ✅ time-varying, 100% matched |
| **Trade remedies** (`analysis/ttbd_vn.csv` + 2) | 3,381 rows x 8 cols; 69 AD/CVD cases against VN, 3,231 HS codes | ⚠️ **initiations stop at 2015** - see §5 |
| **Gravity** (`analysis/gravity_vn.csv`) | 2,940 rows x 20 cols, CEPII V202211 | ⚠️ stops at 2021 |
| **Common shocks** (`analysis/shocks_annual.csv`) | 23 rows x 18 cols; 17 World Bank CMO price indices + Global EPU | ✅ complete, 100% matched |
| **NTM sector** (`analysis/ntm_sector.csv`) | 1,200 rows, 75 countries | ✅ cross-section only |
| **NTM by MAST chapter** (`analysis/ntm_by_type.csv`) | 3,944 rows | ✅ cross-section only |
| **NTM country** (`analysis/ntm_country.csv`) | 150 rows, 75 countries, survey years 2012-2017 | ✅ cross-section only |
| **Screen** (`selection/vn_partner_screen.csv`) | 3,569 country-years; 3,256 importer-reported, 2,786 Viet-Nam-reported; **190 countries** trade with Viet Nam in at least one year | ✅ complete |
| **HS concordance** | **6 tables** H1→H0 … **H6→H0** | ✅ complete |
| **Mirror** (`data_raw/trade_mirror/`) | **40 files, 933,834 rows** - Viet Nam's own export filing | ✅ complete through 2023 |

### 4.1. And what was built out of them

| File | Size | Contents |
|---|---|---|
| `analysis/spells.csv` | 15 MB | **205,607 spells** - 151,858 deaths, 53,749 right-censored (26.1%) |
| `analysis/episodes.csv` | 77 MB | 647,014 episode-years, 17 core columns |
| `analysis/panel_final.csv` | 331 MB | **647,014 x 91 columns**, 2003-2023 - the modelling file |

Built 21/08/2026 (`build_spells` 1m40s / 1.8 GB peak; `merge_panel` 25m40s /
5.2 GB peak). All five build checks pass:

| Check | Target | Actual |
|---|---|---|
| Single exporter | `['VNM']` | ✅ |
| Right-censored | > 0 | ✅ 53,749 |
| Importers | 147 | ✅ 147 |
| Episodes with a tariff | > 90% | ✅ 95.7% |
| Episodes with PREF | > 0% | ✅ 7.7% (50,136) |
| `rca` has variance | not all 1.0 | ✅ p25 0.23 / med 0.83 / p75 2.94 |
| `vn_market_share_pct` | populated | ✅ 100% |

**Duration shape, which the modelling has to reckon with:** median spell length
is **1 year** and **53.2% of spells last exactly one year**; 8.4% survive ten
years or more. At a USD 10,000 threshold most "relationships" are one-off
shipments. Whether to keep them, raise the threshold, or model them separately
is a decision that changes what the estimated hazard means.

---

## 5. What is missing, and why

| Gap | Size | Cause | Fix | Who |
|---|---|---|---|---|
| **Tariffs 2022-2023** | 102,234 episodes on a carried-forward rate | `fetch_tariffs.py:46` hardcodes `range(2002, 2022)` | one-line change, re-pull, re-merge | machine, ~2-3h |
| **NTM at HS6 x year** | 20.4% of episodes have no NTM at all, and what exists is one sector-level cross-section | The three public WITS files have no year dimension at product level | TRAINS Online researcher file - needs an Azure AD account | **user** |
| **Trade remedies after 2015** | 8 of 21 panel years | World Bank TTBD stopped updating June 2016. `ttb_any_in_force` stays non-zero to 2023 only because a measure with no recorded revocation is treated as still in force - i.e. **extrapolation** | censor the variable at 2015, or scrape WTO semi-annual reports | machine |
| **Gravity 2022-2023** | 102,234 episodes, `dist` 84.2% filled | CEPII V202211 stops at 2021 - but `dist`, `contig`, `comlang` are time-invariant | carry the 2021 row forward in `merge_panel.py` | machine, ~30 min |
| **5 macro variables downloaded but never merged** | `inflation_pct`, `exchange_rate_lcu_per_usd`, `lpi_overall`, `population`, `exports_pct_gdp` are in `macro_panel_v2.csv` and absent from `panel_final.csv` | the merge only pulls the four GDP columns | widen the column list | machine, ~30 min |
| Preferences filed under group codes | unquantifiable | TRAINS does not publish group membership | none available; documented as a limitation | - |
| ~~World imports at HS6~~ | - | - | ✅ done 19/08 | - |
| ~~Romania macro~~ | - | - | ✅ done, `macro_panel_v2.csv` | - |
| ~~Trade 2022-2024~~ | - | - | ✅ done 21/08, 0 failed | - |

The importer side of the trade panel is complete for all 147 countries and
verified against the partner screen: **zero download holes**. Everything left in
the table above is either a one-line fix or a account registration - no gap
remains that more downloading alone would close.

Two operational notes worth keeping:

* Comtrade's daily quota answers **403** with the time until replenishment -
  not 429, which is a few-second throttle. The fetcher stops on 403 and says
  when to come back, instead of marking hundreds of importer-years failed.
* A long download must be started with **`setsid`**, not plain `nohup ... &`.
  Without it the process stays in the session's process group and is killed
  when the terminal or agent session ends - which is what silently truncated
  the world pull twice.

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
  common-shock indices, and the NTM columns.

**Not supported, and no amount of further collection changes it:**

* comparison across exporting countries - the panel has one exporter by design;
* within-sector variation in NTMs - the source is sector-level;
* anything about the 2025 US tariff shock - the window ends at 2023 and the
  tariff schedules at 2021. See [MAPPING_IDEA_DATA.md](MAPPING_IDEA_DATA.md) §3
  for which research ideas this rules out.

**A guard sits in `build_spells.py`:** an importer-year that was never
downloaded is indistinguishable, once spells are built, from a year in which the
relationship did not exist - so an unfinished download would manufacture spell
deaths and rebirths. The build cross-checks each importer against the screen and
**holds back every importer that still has a hole**, printing which ones and
which years, rather than silently producing a plausible-looking wrong answer.
As of 21/08/2026 it holds back nothing: all 147 importers pass. It also reports
the 27 importers with an interior gap and the 6 that stopped filing early, and
censors the latter administratively rather than recording a death.
