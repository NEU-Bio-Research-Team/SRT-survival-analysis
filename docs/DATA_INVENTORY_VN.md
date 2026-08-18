# What is actually on disk for Viet Nam

*Every number below was counted by reading the files themselves on 19/08/2026,
not carried over from an earlier document. The exporter is fixed to Viet Nam;
the importer list is the 147 countries chosen in
[THIET_KE_VIET_NAM.md](THIET_KE_VIET_NAM.md).*

---

## 1. The one-line answer

Viet Nam's exports are on disk as **1.35 million HS6 records covering all 147
importing countries over 2002-2021**, worth **USD 2,966 billion** in total -
together with the tariff schedules those importers levy, their macro series, the
non-tariff-measure tables, and Viet Nam's own export filing as a mirror check.
The importer side is complete and verified hole-free. The one pull still running
is the world denominator, which affects three variables and nothing else.

---

## 2. Trade: Viet Nam's exports as the importers report them

| Measure | Value |
|---|---|
| Files (one per importer-year) | **2,813** |
| HS6 records for Vietnamese goods | **1,347,561** |
| Distinct cells (importer x HS6 x year) | **1,324,894** |
| Cells clearing the USD 10,000 spell threshold | **710,496** |
| Distinct HS6 product codes seen | **5,904** |
| Importing countries with data | **147 of 147** ✅ |
| Importers with a download hole | **0** (checked against the partner screen) |
| Years | 2002-2021, complete |
| Total value | **USD 2,966 bn** |

2,813 files against a nominal 147 x 20 = 2,940 is not a shortfall: the
difference is importer-years in which the country genuinely bought nothing from
Viet Nam, or filed no report at all. The completeness check in
`build_spells.py` compares what is on disk against the years the screen says
really carried trade, and finds no gaps.

**By year** (billion USD, as the importers filed it):

| Year | Value | Year | Value | Year | Value | Year | Value |
|---|---|---|---|---|---|---|---|
| 2002 | 16.2 | 2007 | 50.8 | 2012 | 126.5 | 2017 | 287.7 |
| 2003 | 21.5 | 2008 | 65.6 | 2013 | 143.3 | 2018 | 278.4 |
| 2004 | 27.6 | 2009 | 58.3 | 2014 | 161.7 | 2019 | 307.6 |
| 2005 | 33.8 | 2010 | 71.7 | 2015 | 208.2 | 2020 | 337.4 |
| 2006 | 41.2 | 2011 | 95.1 | 2016 | 228.6 | 2021 | 405.1 |

The series tracks Viet Nam's known export take-off (a 25-fold rise across the
window, with the 2009 dip and the 2012 jump when Samsung's phone assembly came
on stream). It runs above Viet Nam's own export statistics because these are
importer filings: CIF rather than FOB, and China in particular records more
arriving from Viet Nam than Viet Nam records leaving for China.

**The ten largest markets in what has been collected:**

| Importer | Total 2002-2021 (bn USD) | Years on disk |
|---|---|---|
| USA | 622.6 | 20 |
| CHN | 547.2 | 20 |
| JPN | 241.8 | 20 |
| KOR | 162.1 | 20 |
| DEU | 125.1 | 20 |
| HKG | 95.3 | 20 |
| AUS | 69.1 | 20 |
| GBR | 68.9 | 20 |
| FRA | 67.5 | 20 |
| MYS | 65.8 | 20 |
| NLD | 57.9 | 20 |
| THA | 57.3 | 20 |

**HS revisions present:** H5 456,254 records · H4 410,305 · H3 266,776 ·
H2 197,309 · H1 15,693 · H0 1,224. Six revisions inside one panel is exactly the
problem the product-family mapping exists to solve - see trap 5 in the README.

---

## 3. Tariffs: what the importers levy

| Measure | Value |
|---|---|
| MFN schedules (reporter-year files) | **2,250** across **134 reporters** |
| Reporter-years with no schedule filed | 224 (a genuine 404, not a failure) |
| **Preferential schedules naming Viet Nam** | **72 reporter-years**, 237,414 tariff lines |
| Reporter-years checked for a VN preference | 2,435 (every one) |

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
| **Macro** (`analysis/macro_panel.csv`) | 2,940 country-years, 147 countries incl. Viet Nam; GDP growth, GDP, GDP per capita 100% filled, exports %GDP 90.5% | ✅ (Romania missing - WITS does not answer to `rou`) |
| **NTM sector** (`analysis/ntm_sector.csv`) | 1,200 rows, 75 countries | ✅ cross-section only |
| **NTM by MAST chapter** (`analysis/ntm_by_type.csv`) | 3,944 rows | ✅ cross-section only |
| **NTM country** (`analysis/ntm_country.csv`) | 150 rows, 75 countries, survey years 2012-2017 | ✅ cross-section only |
| **Screen** (`selection/vn_partner_screen.csv`) | 3,569 country-years; 3,256 importer-reported, 2,786 Viet-Nam-reported; **190 countries** trade with Viet Nam in at least one year | ✅ complete |
| **HS concordance** | 5 tables H1→H0 … H5→H0 | ✅ complete |
| **Mirror** (`data_raw/trade_mirror/`) | 32 of 32 files, 656,336 rows - Viet Nam's own export filing | ✅ complete |
| **World denominators** (`data_raw/trade_world/`) | 1,006 of 2,940 importer-years | ⏳ running |

---

## 5. What is missing, and why

| Gap | Size | Cause | Fix |
|---|---|---|---|
| World imports at HS6 | ~1,930 of 2,940 importer-years | Comtrade **daily call quota** (HTTP 403); this pull is the heavy one at ~5,000 HS6 lines per importer-year | `fetch_trade.py --pass world`, one batch per day until it finishes |
| Preferences filed under group codes | unquantifiable | TRAINS does not publish group membership | none available; documented as a limitation |
| Romania macro | 20 country-years | WITS Development does not answer to `rou` | fill from the World Bank API directly if the variable matters |

Nothing else is outstanding. The importer side of the trade panel is complete
for all 147 countries and verified against the partner screen: **zero download
holes**.

Two operational notes worth keeping:

* Comtrade's daily quota answers **403** with the time until replenishment -
  not 429, which is a few-second throttle. The fetcher stops on 403 and says
  when to come back, instead of marking hundreds of importer-years failed.
* A long download must be started with **`setsid`**, not plain `nohup ... &`.
  Without it the process stays in the session's process group and is killed
  when the terminal or agent session ends - which is what silently truncated
  the world pull twice.

## 6. What this supports right now, and what it does not

**Can be built today, on all 147 importers:**

* spells and episodes for (importer, product family) pairs of Vietnamese goods;
* duration, event and right-censoring flags;
* product share, partner share, both Herfindahl indices, product-level growth
  rates for Viet Nam;
* tariff faced (MFN throughout, preferential where one of the 13 reporters
  filed it), GDP controls, and the 13 NTM columns.

**Cannot be built until the world pull runs:**

* Balassa RCA with a true world denominator (the fallback computes it against
  the in-sample Vietnamese total, which is a within-Viet-Nam specialisation
  index and should not be reported as RCA);
* world growth per product;
* `vn_market_share_pct`, Viet Nam's share of each importer-product market.

**A guard sits in `build_spells.py`:** an importer-year that was never
downloaded is indistinguishable, once spells are built, from a year in which the
relationship did not exist - so an unfinished download would manufacture spell
deaths and rebirths. The build cross-checks each importer against the screen and
**holds back every importer that still has a hole**, printing which ones and
which years, rather than silently producing a plausible-looking wrong answer.
As of 19/08/2026 it holds back nothing: all 147 importers pass.
