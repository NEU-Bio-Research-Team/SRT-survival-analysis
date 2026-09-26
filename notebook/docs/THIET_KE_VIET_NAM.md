# Design change: Viet Nam as the only exporter

*Written 16/08/2026, when the study was narrowed from "82 exporters x 53
importers" to "Viet Nam x every importer with enough data".*

---

## 1. What changed and why it matters

| Dimension | Before (13/08) | Now |
|---|---|---|
| Exporter | 82 countries, ranked by export size | **Viet Nam only** |
| Importer | 53, capped and income-stratified by hand | **every country that qualifies — 147** |
| Unit of observation | spell of (exporter i, importer j, family k) | spell of **(importer j, family k)** for Vietnamese goods |
| Comtrade pull | 1,060 importer-years x 82 partners, ~150 hours | 147 importers x 20 years, **partner = Viet Nam**, ~2 hours |
| Preferential tariffs | 8,078 reporter-partner-years | reporter-years whose schedule names **704**, a few hundred |

The narrowing is not only a scope cut. Three things get *better*:

1. **The panel becomes affordable.** The old design's binding constraint was
   downloading every exporter's HS6 lines for every importer-year. Fixing the
   exporter removes two orders of magnitude of traffic, which is why the whole
   collection now finishes in an afternoon instead of a week.
2. **The importer side stops being a judgement call.** With no quota to fill
   there is no reason to drop a qualifying country, so the rule is stated once
   and applied mechanically. Every country is either in the panel or listed in
   `importer_vn_all.csv` with the number that disqualified it.
3. **The denominators can be real.** The freed budget pays for a second pull -
   each importer's imports *from the whole world* at HS6 - so Balassa RCA,
   world growth and Viet Nam's market-penetration share are computed against
   actual world trade instead of the in-sample total of 82 exporters.

What is lost: no between-exporter comparison. Questions like "do Vietnamese
relationships die faster than Chinese ones in the same market" are out of reach.
Everything identifying now comes from variation **across importers, products and
time**, which is the standard single-exporter export-survival design.

---

## 2. The rule that decides who is an importer

A country enters the panel when all three hold inside 2002-2021:

| # | Condition | Source | Why it is binding |
|---|---|---|---|
| 1 | files annual HS data to UN Comtrade | `getDA` | its imports from Viet Nam must exist at HS6, filed by itself |
| 2 | has a tariff schedule in TRAINS (its own, or the EU's via `EUN`) | `dataavailability` | otherwise the Tariff covariate is structurally missing, not missing at random |
| 3 | actually reports importing from Viet Nam | `cmdCode=TOTAL` screen | a perfect filer with no Vietnamese trade would enter as an all-zero row |

Tiers, instead of a cut-off:

| Tier | Comtrade years | Tariff years | Years trading with VN | Count | In the panel |
|---|---|---|---|---|---|
| **A** | 20 | >= 15 | >= 15 | 102 | yes |
| **B** | >= 15 | >= 10 | >= 10 | 45 | yes |
| **C** | fails A and B | | | 46 | no — reason recorded per country |

Tier B is separated rather than merged so a robustness check can re-run on
tier A alone; `tier` is a column, not a filter applied upstream.

---

## 3. The mirror screen, and one trap inside it

Screening used `cmdCode=TOTAL` for every candidate reporter against partner 704,
both directions of the mirror:

* **importer-reported**: reporter = candidate, partner = Viet Nam, flow = M;
* **Viet-Nam-reported**: reporter = Viet Nam, partner = candidate, flow = X.

The panel is built from the first. The second is kept in
`selection/vn_partner_screen.csv` as the mirror check - the two sides differ by
CIF/FOB, transit and re-export, and a country whose two sides disagree wildly is
worth a second look before its coefficients are believed.

**The trap:** several reporters return the same TOTAL split by customs procedure
(`C00`, `C01`, `C04`...), mode of transport and second partner. Summing those
rows multiplies the value - in the first screen it made Germany look like a
bigger buyer of Vietnamese goods than the United States, which is false. Every
Comtrade request in this project now pins
`customsCode=C00&motCode=0&partner2Code=0`, and the parsers drop any row that is
not the consolidated one. The same fix removed a silent inflation risk from the
HS6 pull, where Germany was also returning ~20 rows per HS6 line.

---

## 4. Covariates that had to be redefined

With one exporter, three of the original variables would have collapsed:

| Variable | Old definition | Problem with one exporter | New definition |
|---|---|---|---|
| `country_growth_pct` | growth of the exporter's total exports | one number per year, collinear with any year effect | growth of **Viet Nam's exports of family k** |
| `world_growth_pct` | growth of the in-sample total | same, and "world" was 82 countries | growth of **world imports of family k** (from the world pull) |
| `rca` | Balassa against the in-sample total | denominator was not the world | Balassa against **world imports** |

One variable is new: `vn_market_share_pct`, Viet Nam's share of importer j's
imports of family k in that year. It is the most direct measure of how much of
the market a relationship holds, and it only becomes computable because the
world pull exists.

`product_share_pct`, `partner_share_pct`, `hhi_market` and `hhi_product` keep
their meaning; they are now Viet-Nam-specific by construction and vary across
products (the first two) or across years (the HHIs).

---

## 5. Tariffs: what is still approximate

The tariff faced is the lower of MFN and the preferential rate the importer
grants Viet Nam. Two caveats survive:

1. **Group-filed preferences.** An importer can file its ASEAN / AANZFTA / RCEP
   schedule under a *group* partner code rather than under 704. Those rows are
   not fetched - the group-to-member mapping is not exposed by the API - so such
   an episode falls back to MFN and the rate faced is **overstated**. The
   `tariff_type` column marks which of the two applied, so the affected episodes
   are identifiable rather than hidden.
2. **A bug that was hiding all preferences.** `merge_panel.py` keyed
   preferential rates by the TRAINS numeric partner code taken from the file
   name (`704`) but looked them up with an iso3 exporter (`VNM`), so no
   preferential rate could ever match - every episode silently fell back to MFN.
   Fixed by translating the code before keying.

---

## 6. Files this design writes

| File | What it holds |
|---|---|
| `selection/exporter_selected.csv` | one row: Viet Nam |
| `selection/importers_vn.csv` | the 147 importers in the panel, with tier |
| `selection/importer_vn_all.csv` | all 193 candidates, including the 46 excluded and why |
| `selection/vn_partner_screen.csv` | both sides of the mirror, by country-year |
| `data_raw/trade/` | importer's imports from Viet Nam, HS6, one file per importer-year |
| `data_raw/trade_world/` | the same importers' imports from the world, HS6 |
| `data_raw/trade_mirror/` | Viet Nam's own export filing towards them |

The 119 files pulled under the old design are kept as they are: Viet Nam was one
of the 82 partners requested, so they already contain the rows this design
needs, and `build_spells.py` simply drops every non-VNM row on the way in.
