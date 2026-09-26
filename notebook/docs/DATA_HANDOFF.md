# Data handoff: the `Sinking Relationships` brief, item by item

*Audited **25/08/2026** by reading the files on disk, not by trusting the
earlier notes. Four requirements the brief names were closed that day; two
turned out to be already done; three cannot be closed by any amount of
downloading, and this document says exactly why. Companions:
`TIEN_DO_SO_VOI_SINKING.md` (Vietnamese progress tracker, removed from the tree
on 20/09/2026 — `git show dbae191:legacy/docs/TIEN_DO_SO_VOI_SINKING.md`),
[BRIEF_SINKING_COVERAGE.md](BRIEF_SINKING_COVERAGE.md),
[DATA_INVENTORY_VN.md](DATA_INVENTORY_VN.md).*

**The panel:** `analysis/panel_final.csv`, 747,719 episodes x 158
columns, 2003-2025, 147 importers, 4,599 product families, 228,175 spells of
which 57,689 are right-censored.

---

## 1. The brief's requirements, scored

| Brief | Requirement | Status |
|---|---|---|
| §1 | Exports, Viet Nam x importer x HS6 x year, 2002-2024 | ✅ 2002-2025, 147 importers |
| §1 | Volume as well as value | ✅ `net_weight_kg`, `unit_value_usd_per_kg` |
| §1 | Spells: start, end, right-censoring | ✅ 228,175 spells |
| §2 | MFN tariffs | ⚠️ 96.9% of episodes carry one, 83.8% measured in their own year. **2024-2025 have none of their own** |
| §2 | Preferential (FTA) tariffs | ⚠️ 13 reporters file a schedule naming Viet Nam; none at all for 2022-2023 |
| §2 | **US 2025 reciprocal tariff, monthly, by product** | ✅ **closed 25/08** — rate path by month, product scope from the chapter-99 legal note, and finally merged into the panel |
| §3 | Distance, GDP, GDP per capita, FTA/RTA | ✅ all four at 100% |
| §3 | Product complexity | ✅ 100% |
| §4 | Green LPI | ✅ four published constructions built; **which one to use is a research decision** |
| §4 | **NTM (UNCTAD TRAINS)** | ✅ **closed 25/08** — HS6 x NTM code x year, replacing a sector-level cross-section |
| §4 | **EU CBAM shock** | ✅ **closed 25/08** — the brief names it; nothing had ever been collected |
| §4 | NTM on a tariff scale | ✅ **added 25/08** — ad-valorem equivalents, the only NTM variable comparable with `tariff_rate` |
| §5 | Clean panel with the named columns | ✅ every one present |
| §5 | Documented coverage and gaps | ✅ this document and its companions |

---

## 2. What was closed on 25/08

### 2.1. NTM at HS6 x year — the scripted pull had been trying the wrong door

The project's standing conclusion was that this data could not be pulled from
this machine. That was correct about the route it had tried and wrong about the
data. `POST /denormalisedMeasures` caps `pageSize` at 20 and sits behind a
Cloudflare rule that answered 429 six times across 31 minutes of backoff - so a
few thousand pages was never going to happen.

**The same database is published as a single file over a plain GET that is not
rate-limited at all.** `https://api-trains2.unctad.org/get-researcher-file/2`
returns `NTMs_HS2012ver_Researcher.csv`, 10,548,645,866 bytes, no login. The
column documentation is file `/3`.

Its unit is exactly what the brief needs: imposing country x affected country x
HS6 x NTM code x year of data collection. `scripts/fetch_ntm_researcher.py`
streams it and filters as it goes - the host offers no gzip and honours no Range
header, so there is no resuming and no reason to store 10.5 GB.

**What the pass produced:** 58.4 minutes, one request, no rate limiting.
153,058,539 rows read; 18,686,715 kept (12.2%) once narrowed to `WLD`, Viet Nam
and the brief's competitor set; 66.8 MB gzipped on disk against 10.5 GB at
source. After mapping HS 2012 to the panel's H0 families and dropping the
export-side chapters, 12,918,392 rows are usable, filed by **126 reporters** -
including China, Korea and the United States, none of which the sector-level
WITS files covered at all.

In the panel: **95.2% of episodes now carry an HS6 NTM count**, against 79.9%
for the sector-level columns it replaces.

⚠️ **But 95.2% is the coverage, not the measurement.** Only **36.6%** of
episodes sit in a year their importer actually filed, and **29.0%** carry a
count borrowed forward from a *later* collection year - which is every episode
from 2003 to 2009, since the file starts in 2010. By year:

| Years | Filed that year | Borrowed from later |
|---|---|---|
| 2003-2009 | 0% | ~95% |
| 2010-2014 | 26-37% | 58-70% |
| 2015-2019 | 24-60% | 5-32% |
| 2020-2025 | 30-61% | 0-3.5% |

`ntm6_observed` and `ntm6_source_year` separate the three cases in every row.
Any specification that uses the NTM count before roughly 2015 is reading the
collection calendar as much as the policy.

**Three properties of this source that change how the variable must be read.**

1. **The file starts in 2010.** Checked directly: `Year` is sorted ascending
   with zero violations across 5.41m rows and the first row is 2010. The panel
   runs from 2003, so **seven of its twenty-three years can hold no NTM at all**
   — a structural zero, not a low value.
2. **`Year` is the year of data collection, not a calendar year.** The metadata
   is explicit. The United States filed in 2014, 2017, 2018 and 2019 only; the
   EU filed in most years from 2010 on. So NTMs vary over time for the EU,
   Indonesia and Latin America, and are near-constant for the single market the
   brief cares most about.
3. **Most measures are filed against `WLD`, not against Viet Nam.** In the
   sample the EU filed 8,075 rows naming VNM against 1,282,130 naming WLD.
   Filtering on `VNM` alone would have discarded almost everything that applies
   to Viet Nam. Both are counted; `ntm6_bilateral_survey` isolates the rarer,
   sharper set that names Viet Nam.

An undocumented pair of columns, `MinStartYear` and `MaxEndYear`, turned out to
be the useful part. They are absent from the 2023 metadata paper but present in
the file, and they hold: `MinStartYear <= Year <= MaxEndYear` in **100.0%** of
5.41m rows checked, with **87.9%** of cells carrying `ntm_all == 1`, so for most
cells the pair is one measure's own in-force window rather than an envelope over
several. That is what makes `ntm6_*_inforce` possible between collection years.

### 2.2. The 2025 US tariff had never actually entered the panel

`analysis/us_tariffs_2025.csv` had been on disk since 22/08. **None of it was in
`panel_final.csv`** — the brief's central covariate was absent from the
deliverable. Three things were needed.

**The rate path.** The rate moved four times in 2025 and the schedule records
only the end state, so the dates were read out of the orders themselves, now
archived under `data_raw/us_tariffs_2025/fr_text/`:

| From | Rate | Authority |
|---|---|---|
| 5 Apr 2025 | 10% | EO 14257 s.3(a), first paragraph - the universal floor |
| 9 Apr 2025 | 46% | EO 14257 s.3(a), second paragraph - Annex I |
| 10 Apr 2025 | 10% | EO 14266 s.2 suspends Annex I rates until 9 Jul 2025 |
| 7 Aug 2025 | 20% | EO of 31 Jul 2025, effective 7 days after signature |

EO 14316 extended the suspension from 9 July to 1 August, so the 10% band runs
unbroken from 10 April to 6 August. Viet Nam is named in no order after EO
14257: the September, November and December orders address China, Switzerland
and a list of agricultural goods.

**The day-weighted 2025 rate is therefore 11.55%, not 46% and not 20%.** A model
that writes either headline onto the whole year overstates the exposure by two
to four times. `analysis/us_tariff_2025_monthly.csv` carries the month-by-month
path the brief asks for; the panel carries `us_recip_rate_yearend` (20),
`us_recip_rate_peak` (46) and `us_recip_rate_days_wt` (11.55) so the annual
convention stays a visible choice.

**The product scope**, which the REST endpoint does not return, is in U.S. note
2(v)(iii) to subchapter III of chapter 99 - a PDF that had been sitting unparsed
since 22/08. `scripts/extract_us_exemptions.py` reads **1,087 exempt HTS8
subheadings**, covering 667 HS6 and 547 H0 product families, of which 472 are
wholly exempt and 75 straddle the line.

**This changes the shock's size materially.** Only 6.7% of Viet Nam's US
episodes sit on a family with exempt tariff lines - but those families carry
**39.0% of Viet Nam's export value to the United States**. The reason is
concentrated in four families: smartphones (`8517.13`), integrated circuits
(`8542.31`-`8542.39`), photovoltaic and light-emitting semiconductor devices
(`8541.41`, `8541.49`, `8541.51`, `8541.59`). The separate semiconductor
carve-out at heading 9903.79.01 is *not* a general electronics exemption - it
covers only 8471.50, 8471.80 and 8473.30 and only above specific processing and
memory-bandwidth thresholds, so it does not reach Viet Nam's exports.

⚠️ **The roll-up is not clean and the column says so.** HS 1992 is coarser than
HS 2022 exactly where this matters: `H0_852520` holds thirteen HS 2022
subheadings, of which four are exempt. `us_recip_exempt_share` is the fraction
of a family's subheadings that are exempt, and `us_recip_exempt_full` marks the
472 families where it is all of them. Treating the share as a binary will
overstate the exemption for high-value electronics.

### 2.3. CBAM — the brief names it, and the project had never collected it

The brief gives the EU a specific job: to be the *other* shock, so the hazard
from a conventional tariff can be compared with the hazard from a carbon
measure. "CBAM" appeared in no script, no document and no column of this project.

`scripts/fetch_cbam_scope.py` reads Annex I of Regulation (EU) 2023/956 from the
Publications Office's CELLAR service (eur-lex.europa.eu answers a JavaScript
challenge and cannot be read by a script). The annex gives **42 included CN
lines and 14 exceptions across six sectors**, which resolve to 292 HS6 and
**269 H0 families**: iron and steel 209, aluminium 31, fertilisers 21, cement 6,
electricity 1, chemicals 1.

Against the panel: **4.2% of Viet Nam's EU episodes and 3.84% of its EU export
value** are in scope. Small, but concentrated and identifiable.

⚠️ **The finding that decides what this variable can be asked to do.** Article
32 sets the transitional period at **1 October 2023 to 31 December 2025**, and
during it the importer's obligation is **reporting only** - no certificates, no
payment. The definitive regime starts 1 January 2026, one year past the end of
this panel. **Inside the observation window CBAM is a compliance and
anticipation cost, not a price.** A table that puts it beside the 2025 US tariff
without saying so is comparing a duty with a filing duty. `cbam_definitive` is
in the panel and is zero in every row, so that the zero is visible rather than
implied.

### 2.4. EPI as an annual series — the archive was reachable after all

The earlier note recorded Yale's archive as returning 500, which is true, and
concluded the EPI could only ever be one 2026 cross-section - which is why
`importer_glpi_*` cannot move over time. The 500 was the wrong door again.
**Past-year EPI *scores* are published by nobody**; what Yale does publish, in
the release archives, is every underlying indicator as an annual series.

`scripts/fetch_epi_annual.py` pulls those and reshapes them into
`analysis/epi_indicators_annual.csv`: **184,827 values, 220 economies, 52
indicators, 1996-2025**, plus the weight tree in
`data_raw/epi/epi2026methods2026-07-08.xlsx`.

It deliberately stops there. Collapsing 52 indicators into an annual EPI means
applying that weight tree, and this project already has one unsettled question
about how to build a composite - which Green LPI construction to follow.
Stacking a second bespoke composite underneath the first would bury a research
decision inside a data step. **The ingredients are on disk; the weighting is the
team's to choose.**

### 2.5. Two open items were checked and found already closed

- **Trade remedies censored at 2015.** `ttbd_observed` is 1 for every episode
  through 2015 and 0 from 2016 on, exactly as intended. `ad_in_force` and
  `ttb_any_in_force` still carry non-zero values after 2016 because a measure
  with no recorded revocation is treated as still running - that is
  extrapolation, and `ttbd_observed` is the flag that makes it visible. Filter
  on it before reading any trade-remedy coefficient.
- **TRAINS tariffs for 2024-2025.** Re-probed on 25/08 for the United States,
  Japan, Korea and the EU: the availability endpoint still reports 2021 as the
  last year, and the 2024-2025 schedules still are not there. Unchanged.

---

### 2.6. One more file sits at the same endpoint, and it is worth having

Probing `get-researcher-file/{1..6}` on 25/08 found four live ids, not two:

| id | File | Size | Status |
|---|---|---|---|
| 1 | `NTMs_HS2012ver_Researcher.dta` | 6.4 GB | The same data in STATA format — no reason to take it |
| 2 | `NTMs_HS2012ver_Researcher.csv` | 10.5 GB | ✅ pulled and filtered |
| 3 | `MetadataForTheResearcherFile2023.pdf` | 567 KB | ✅ on disk |
| 4 | **`UNCTADGTAP11_AVEborder.zip`** | **2.8 MB** | ✅ **pulled 25/08** — a different variable entirely |
| 5, 6 | — | — | HTTP 400, nothing there |

**Id 4 is not more of the same.** It holds **ad-valorem equivalents of border
NTMs** — the uniform tariff that would have the same trade effect as the NTMs a
country actually applies — estimated by the method of Kee and Nicita (2022) and
made consistent with the GTAP 11 Data Base. 162,174 observations, bilateral, in
`data_raw/ntm/ave_gtap/`.

**Why it matters here:** every other NTM variable in this project is a *count*.
This one is a **percentage on the same scale as `tariff_rate`**, which is what a
hazard model needs if the NTM effect is ever to be compared with the tariff
effect rather than just signed. Viet Nam appears as an exporter in **2,401 rows
across 89 importing markets and 45 sectors**, mean AVE **7.81%**, and
**9.94%** into the United States. The importer codes are ISO3 plus `EUN` for the
European Union — the same convention this project already uses for tariffs and
NTMs, so no country mapping is needed.

⚠️ **Two limits decide how it can be used, and neither is fixable.**

1. **It is one cross-section, 2017.** The README is explicit: AVEs are built
   from NTM data collected 2015-2021 "under the assumption that these measures
   were in effect in 2017", against 2017 trade. There is no year dimension, so
   it can enter as a time-invariant market characteristic and nothing more.
2. **Products are 46 GTAP sectors, not HS6.** AVEs are estimated at HS6 and then
   aggregated away. Going back to HS6 needs the GTAP concordance, which lives
   behind registration at Purdue and is **not on disk** — so the sector
   dimension cannot currently be joined to the panel's 4,599 families.

**What that leaves is still useful, and it is now in the panel.** Collapsing the
sectors gives one number per importing market — how NTM-costly that market is
for Vietnamese goods, in tariff points. `build_ntm_ave.py` writes it, and
because the collapse is a choice, **both versions ship** rather than one:

| Column | Meaning |
|---|---|
| `ntm_ave_border_pct` | Weighted by `gtaptrade`, the 2017 trade weights inside the file — "what the average dollar of Vietnamese exports to this market meets at its border" |
| `ntm_ave_border_simple_pct` | Unweighted sector mean — gives small sectors equal say |
| `ntm_ave_n_sectors` | How many sectors the average is over |
| `ntm_ave_source_year` | Always 2017 |

The two differ enough to matter: into the United States the weighted figure is
**3.91%** and the simple mean **9.94%**, because Viet Nam's US exports are
concentrated in sectors that happen to be cheap to clear. Coverage is **94.4%**
of episodes, across 116 importers.

⚠️ **It cannot survive importer fixed effects.** One value per market, repeated
across years, is collinear with an importer dummy by construction. It is a
between-market variable — useful in a specification without importer effects, or
interacted with something that does vary, and useless as a within estimator.

---

## 3. What no amount of downloading will fix

| Item | What is short | Why it cannot be closed |
|---|---|---|
| **Preferential tariff rates** | Only 13 reporters file a schedule naming Viet Nam, and none for 2022-2023. The rest of its preferential access sits under group codes (ASEAN, AANZFTA, GSP) whose membership WITS does not publish | `fta_vn.csv` recovers *whether* a preference applied; the rate itself is unobserved. The rate faced is **overstated** for the ~39% of episodes with an agreement in force |
| **Tariffs for 2024-2025** | TRAINS publishes no schedule for either year | Those years carry 2023 values, stamped in `tariff_source_year`. The only genuinely time-varying tariff in 2025 is the US one |
| **NTMs before 2010** | The researcher file begins in 2010 | No earlier vintage of the file exists. `ntm6_observed` marks it |
| **NTMs for the United States after 2019** | The US filed in 2014, 2017, 2018, 2019 | This is the collection calendar, not a gap in the download |
| **CBAM as a price** | The definitive regime starts 1 Jan 2026 | One year past the panel. No data can move that date |

---

## 4. Reading the new columns without misreading them

**`ntm6_source_year` later than `year` means the count is borrowed.** That is
29.0% of the panel, all of 2003-2009 among it. Treat those rows as unmeasured
rather than as low-NTM.

**Blank is not zero.** `us_recip_*` and `us_recip_exempt_*` are written only on
`importer == "USA"` rows; `cbam_*` only on EU importers, with membership read
year by year (so the United Kingdom stops counting after 2020). A blank means
"this measure does not apply to this market". A zero on a USA row means "this
duty applies and this family is not exempt". They are different claims.

**`ntm6_observed` gates everything else.** Two NTM variables exist on purpose:

- `ntm6_*_survey` counts what was collected in the nearest earlier collection
  year, stamped in `ntm6_source_year` - the conservative reading, and the same
  shape `importer_lpi_source_year` already uses for the LPI waves. For years
  before a reporter's *first* collection year there is no earlier wave, so the
  earliest one is carried backwards; `ntm6_source_year` will then be later than
  `year`, which is the signal that the count is borrowed rather than observed.
- `ntm6_*_inforce` counts measures whose recorded window covers the panel year,
  pooled over all collection years and deduplicated on (family, NTM code, start,
  end). This one moves between collection years, which is what a hazard model
  wants - and it is also the one that will manufacture a spurious upward trend
  if used outside the years a reporter actually filed.

**The old sector-level NTM columns are still there.** `ntm_coverage_ratio`,
`ntm_frequency_ratio` and the rest come from the three public WITS files: one
cross-section, 16 sector groups, no year dimension, and nothing at all for 20.4%
of episodes including China and Korea. They are kept as a fallback for reporters
the researcher file does not cover. Do not mix the two families in one
specification.

**The event-date convention has not changed.** `event = 1` in year Y means the
last year the relationship was alive is Y, so it died in Y+1. The 2025 US tariff
therefore has to be read as a lead against `event` dated 2024, or the year is
wrong by one.

---

## 5. What is a decision, not a download

These block the modelling and none of them is the machine's to settle.

1. **Define "network survivability".** It is the constraint in the title, and
   without it the optimisation cannot be written. Not a data gap.
2. **The twelve definitions in §2.3 of the L0-L5 document.** They block L0.
3. **Which Green LPI construction.** Four are built and they disagree - the
   ratio and PCA variants rank countries almost inversely (Spearman -0.463).
   Naming the paper settles it in an hour.
4. **Whether to build an annual EPI** from the indicator archive, and with what
   weights.
5. **The annual convention for the 2025 US tariff** - year-end 20%, peak 46%, or
   day-weighted 11.55%. All three are in the panel.
6. **The one-year spells.** 52.7% of spells last exactly one year at the USD
   10,000 threshold; raising the threshold 500x removes 85% of spells and only
   13 points of that share, so the recommendation on file is to model them
   rather than define them away.

---

## 6. File map for whoever picks this up

| File | Key | What it holds |
|---|---|---|
| `analysis/panel_final.csv` | spell_id, year | The panel. Everything below is merged into it |
| `analysis/spells.csv` | spell_id | One row per relationship spell |
| `analysis/us_tariff_vn.csv` | importer, year | 2025 US reciprocal rates, four conventions |
| `analysis/us_tariff_2025_monthly.csv` | iso3, year, month | The within-year rate path with its authority |
| `analysis/us_exempt_products.csv` | product_family | Exempt share per family |
| `analysis/us_tariff_exemptions_2025_hs8.csv` | hts8 | The 1,087 raw subheadings, audit trail |
| `analysis/cbam_products.csv` | product_family | CBAM Annex I scope and sector |
| `analysis/cbam_products_cn.csv` | cn_code | The CN lines including exceptions, audit trail |
| `analysis/epi_indicators_annual.csv` | iso3, year, indicator | EPI inputs 1996-2025 |
| `analysis/ntm6_observed.csv` | reporter | Which years each country filed NTM data |
| `analysis/_ntm6/{REPORTER}.csv.gz` | - | Sharded HS6 NTM aggregates, read by the merge |
| `data_raw/ntm/researcher/` | - | The filtered researcher file and its metadata PDF |
| `data_raw/ntm/ave_gtap/` | exporter, importer, gtapcode | NTM ad-valorem equivalents, 2017 cross-section |
| `analysis/ntm_ave_vn.csv` | importer, year | The two collapsed AVE columns merged into the panel — see §2.6 |

Rebuild order is in §7 below, and in [../README.md](../README.md).

---

## 7. Rebuilding this from nothing

**First, the direct answer: nothing is left to download.** Checked on 25/08 by
counting the panel itself — `rca`, `world_growth_pct`, `vn_market_share_pct`,
`country_growth_pct`, `hhi_market`, `dist`, `pci` and the GDP series are at
**100% in every year from 2003 to 2025**, and the raw trade pulls cover 2002-2025
in all three passes. The two columns that are not complete are short for reasons
no download fixes: tariffs in 2024-2025 (81.0% and 78.2%, all carried from 2023
because TRAINS publishes no schedule for those years) and NTMs before 2010 (the
researcher file does not go back further). Both are listed in §3.

**What is missing is not data — it is the fact that the data does not travel
with the repository.** `.gitignore` excludes `data_raw/` and `analysis/`, so a
colleague who clones this repo gets every script and document and **not one row**.
That is deliberate — 735 MB of raw downloads and 828 MB of built outputs do not
belong in git — but it means the handoff has to say which of the two routes below
is being taken.

### 7.1. What travels, and the one thing that must not

| | Send | Why |
|---|---|---|
| `scripts/` | yes | Every fetch and build step, each with its source and limits in the docstring |
| `selection/` | yes | Country lists, the EU mapping, NTM availability — needed to read the sample |
| `docs/`, `README.md` | yes | Why each decision was made |
| `analysis/` | route A | The built data. 828 MB, of which `panel_final.csv` is 640 MB |
| `data_raw/` | route B | 735 MB of downloads. Only needed if they will rebuild |
| **`.env`** | **never** | Two UN Comtrade API keys. A colleague registers their own at `comtradeplus.un.org`; it is free and takes minutes |
| `logs/`, `probe_out/`, `__pycache__/` | no | Working residue |

### 7.2. Route A — send the built data (the usual choice)

They can estimate immediately and never touch an API. They cannot rebuild.

```bash
cd /home/minhquang/wits
tar czf wits_data_$(date +%Y%m%d).tar.gz \
  analysis selection docs scripts README.md "docs/idea/Sinking Relationships.md" \
  data_raw/ntm/ave_gtap
```

**~160 MB** (built 25/08: 158 files under `analysis/`, 38 scripts, 16 documents,
16 selection tables — and verified to contain no `.env` and no credential of any
kind). If that is still too large for the channel, drop
`analysis/episodes.csv` (107 MB) and `analysis/_ntm6/` (56 MB): the first is an
intermediate that `build_spells.py` regenerates, the second is only read by
`merge_panel.py`. `panel_final.csv` and `spells.csv` are the two that matter.

### 7.3. Route B — rebuild from source

Only `fetch_trade.py`, `select_importers_vn.py` and `select_countries.py` need
the Comtrade key; **everything else in this pipeline is keyless and public**.
Comtrade enforces a daily quota, so the trade passes are the ones that stretch
across days. Every fetcher skips files already on disk, so re-running resumes.

**Fetch, in this order:**

| # | Command | Key | Cost | Resumes |
|---|---|---|---|---|
| 1 | `select_importers_vn.py --refresh` | yes | ~1h. Skip it — `selection/` is already in the handoff | — |
| 2 | `fetch_trade.py --pass vn` | yes | ~2h, covers 2002-2021 by default | yes |
| 3 | `pull_2022_2024.sh` | yes | runs vn, mirror and world for 2022-2024; usually hits the daily quota at least once | yes |
| 4 | `fetch_trade.py --pass vn --years 2025` then the same for `world` | yes | 2025 is not in any default range | yes |
| 5 | `fetch_trade.py --pass world` | yes | the heaviest pull — this is the RCA/market-share denominator | yes |
| 6 | `fetch_trade.py --pass mirror` | yes | cheap, cross-check only; Viet Nam has not filed 2025 | yes |
| 7 | `fetch_tariffs.py --pass all` | no | long. Two caches make re-runs cheap: `_no_schedule.csv` and `_partnerlists.csv` | yes |
| 8 | `fetch_macro.py` | no | minutes | yes |
| 9 | `fetch_covariates.py` | no | minutes — CEPII gravity, DESTA, WDI, LPI, Atlas | yes |
| 10 | `fetch_us_tariffs_2025.py` | no | seconds. **Also fetches the 14 MB chapter-99 PDF** that step 14 parses | yes |
| 11 | `fetch_cbam_scope.py` | no | seconds — CELLAR, not eur-lex, which blocks scripts | yes |
| 12 | `fetch_epi_annual.py` | no | seconds | yes |
| 13 | `fetch_ntm_researcher.py` | no | **58.4 min measured**, streams 10.5 GB and keeps 67 MB | **no** |

⚠️ **Step 13 is the one that cannot resume.** The host serves no gzip and
ignores `Range` — a partial request is answered `200` with the whole blob — so a
broken transfer starts over. Run it under `setsid` and leave it alone:

```bash
cd /home/minhquang/wits/scripts
setsid nohup python3 -u fetch_ntm_researcher.py \
  > ../logs/ntm_researcher.log 2>&1 < /dev/null &
```

Do **not** use `fetch_ntm_trains.py` for this. It is the page-by-page route,
it is kept only as a reference, and it cannot finish from this network.

**Then build, in this order** — five of these write files `merge_panel.py`
reads, so the order is not cosmetic:

```bash
python3 build_covariates.py         # fta_vn, ttbd_vn, gravity_vn, shocks, macro_v2, complexity
python3 build_glpi.py               # glpi.csv, four constructions
python3 extract_us_exemptions.py    # us_exempt_products.csv        <- merge reads this
python3 build_us_tariff_panel.py    # us_tariff_vn.csv + monthly    <- merge reads this
python3 fetch_cbam_scope.py         # cbam_products.csv             <- merge reads this
python3 build_ntm.py                # the old sector-level NTM columns
python3 build_ntm_ave.py            # ntm_ave_vn.csv                <- merge reads this
python3 build_ntm6.py               # analysis/_ntm6/ shards        <- merge reads this
python3 build_spells.py             # ~1.7 min, 1.8 GB RAM
python3 merge_panel.py              # ~2 min, under 500 MB RAM
```

A missing input is skipped with a printed note rather than a crash, so a merge
run that quietly produced 128 columns instead of 158 means one of the five
marked steps did not run. **Check the column count.**

### 7.4. Verifying a rebuild

Measured on the 25/08 build — a rebuild that does not reproduce these is wrong
somewhere:

| Check | Expected |
|---|---|
| `panel_final.csv` shape | 747,719 x **158** |
| unique exporter | `['VNM']`, 147 importers |
| spells / right-censored | 228,175 / 57,689 |
| tariff measured in its own year | 83.8% |
| HS6 NTM attached | 95.2%, of which 36.6% filed in that same year |
| NTM ad-valorem equivalent attached | 94.4%, 116 importers |
| US reciprocal columns | 24,355 rows (every USA episode) |
| CBAM in scope | 7,823 EU episodes |
| day-weighted 2025 US rate | 11.55% |
