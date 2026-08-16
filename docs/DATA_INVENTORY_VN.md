# What is actually on disk for Viet Nam

*Every number below was counted by reading the files themselves on 16/08/2026,
not carried over from an earlier document. The exporter is fixed to Viet Nam;
the importer list is the 147 countries chosen in
[THIET_KE_VIET_NAM.md](THIET_KE_VIET_NAM.md).*

---

## 1. The one-line answer

Viet Nam's exports are on disk as **1.1 million HS6 records covering 87 importing
countries over 2002-2021**, worth **USD 2,810 billion** in total - together with
the tariff schedules those importers levy, their macro series, and the
non-tariff-measure tables. What is missing is 60 further importers, blocked
until the Comtrade daily quota replenishes, not by anything structural.

---

## 2. Trade: Viet Nam's exports as the importers report them

| Measure | Value |
|---|---|
| Files (one per importer-year) | **1,686** |
| HS6 records for Vietnamese goods | **1,101,870** |
| Distinct cells (importer x HS6 x year) | **1,079,203** |
| Cells clearing the USD 10,000 spell threshold | **608,182** |
| Distinct HS6 product codes seen | **5,840** |
| Importing countries with data | **87** of 147 |
| Years | 2002-2021, complete |
| Total value | **USD 2,810 bn** |

**By year** (billion USD, as the importers filed it):

| Year | Value | Year | Value | Year | Value | Year | Value |
|---|---|---|---|---|---|---|---|
| 2002 | 15.7 | 2007 | 42.8 | 2012 | 120.6 | 2017 | 276.8 |
| 2003 | 20.9 | 2008 | 53.9 | 2013 | 136.2 | 2018 | 266.6 |
| 2004 | 26.8 | 2009 | 48.8 | 2014 | 154.4 | 2019 | 296.4 |
| 2005 | 32.3 | 2010 | 60.6 | 2015 | 199.6 | 2020 | 327.3 |
| 2006 | 39.6 | 2011 | 79.5 | 2016 | 219.4 | 2021 | 392.0 |

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
| JPN | 200.6 | **15** ⚠ |
| KOR | 162.1 | 20 |
| DEU | 125.1 | 20 |
| HKG | 95.3 | 20 |
| AUS | 69.1 | 20 |
| GBR | 68.9 | 20 |
| FRA | 67.5 | 20 |
| MYS | 65.8 | 20 |

**HS revisions present:** H5 375,405 records · H4 334,456 · H3 211,706 ·
H2 167,709 · H1 12,172 · H0 422. Six revisions inside one panel is exactly the
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
| **Mirror** (`data_raw/trade_mirror/`) | 2 of 32 files | ⏸ paused |
| **World denominators** (`data_raw/trade_world/`) | 0 of 2,940 | ⏸ not started |

---

## 5. What is missing, and why

| Gap | Size | Cause | Fix |
|---|---|---|---|
| 60 importers with no trade data | 45 tier B + 15 tier A; largest are THA (2.87 bn/yr) and KHM (1.05 bn/yr) | Comtrade **daily call quota** (HTTP 403) hit partway through the run | re-run `fetch_trade.py --pass vn` after the quota replenishes |
| Japan 2007-2011 | 5 importer-years | same quota, mid-country | same |
| World imports at HS6 | 2,940 importer-years | never started - the quota went first | `fetch_trade.py --pass world` |
| Viet Nam's own export filing | 30 of 32 files | paused to free up rate limit | `fetch_trade.py --pass mirror` |
| Preferences filed under group codes | unquantifiable | TRAINS does not publish group membership | none available; documented as a limitation |

The 87 importers already collected carry **89% of Viet Nam's export value**, so
the missing 60 are mostly small markets - but they are exactly the low-income
and lower-middle-income markets, so leaving them out would bias any result that
touches development level. They are worth waiting for.

---

## 6. What this supports right now, and what it does not

**Can be built today, on the 87 complete importers:**

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

**A guard now sits in `build_spells.py`:** an importer-year that was never
downloaded is indistinguishable, once spells are built, from a year in which the
relationship did not exist - so an unfinished download would manufacture spell
deaths and rebirths. The build cross-checks each importer against the screen and
**holds back every importer that still has a hole**, printing which ones and
which years, rather than silently producing a plausible-looking wrong answer.
Japan is currently held back for this reason.
