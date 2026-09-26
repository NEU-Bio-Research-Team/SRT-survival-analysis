# The "Sinking Relationships" data brief, item by item

*A direct audit of `Sinking Relationships.md` against what is on disk, counted
by reading the files themselves on **22/08/2026**. Where the brief asks for
something the project did not have, this says what was fetched that day, what is
still open, and which of the open items need a decision from the team rather
than more downloading.*

Companion documents: [DATA_INVENTORY_VN.md](DATA_INVENTORY_VN.md) counts what is
on disk; [COVARIATES_ADDED.md](COVARIATES_ADDED.md) explains each source and how
it was built; [MAPPING_IDEA_DATA.md](MAPPING_IDEA_DATA.md) maps the L0-L5 ladder.

---

## 1. The brief's five requirements, scored

| Brief | Requirement | Status 22/08 |
|---|---|---|
| §1 | Exports, Viet Nam x importer x HS6 x year, 2002-2024, with quantity | ✅ 1.47m cells, 147 importers, 2002-2024; **quantity added 22/08** |
| §1 | Export spells: start, end, right-censoring | ✅ 205,607 spells, 53,749 right-censored |
| §2 | MFN and preferential tariffs | ✅ **extended to 2023 on 22/08** — 99.6% of episodes carry a tariff, 96.8% measured in their own year. Preference coverage stops at 2021, a TRAINS limit |
| §2 | **US 2025 reciprocal tariff history** | ✅ **collected 22/08** at country level; product scope still open |
| §3 | Distance, GDP, GDP per capita, RTA | ✅ all four, and GDP per capita now reaches the panel |
| §3 | **Product complexity** | ✅ **collected 22/08**, 100% join |
| §4 | Green LPI inputs | ✅ **six sub-indices collected 22/08**; the index itself needs a formula decision |
| §4 | NTM (UNCTAD TRAINS) | ⚠️ public cross-section only — needs an account |
| §5 | A clean panel with the six named columns | ✅ all six present, each at 99.6-100% |
| §5 | `spell_start`, `spell_end`, `censored` as columns | ✅ added 22/08 — `spell_start_year`, `spell_end_year`, `right_censored` sit beside the counting-process pair |
| §5 | Documented coverage and gaps | ✅ this document and its two companions |

**One-line answer: the collection is complete except for the NTM detail, which
needs an account, and the product scope of the 2025 US tariff, which needs work
on a PDF. Everything else the brief names is on disk and in the panel.**

The panel as rebuilt on 22/08: **647,014 episodes x 123 columns**, 2003-2023,
147 importers, 4,599 product families, 205,607 spells of which 53,749 are
right-censored.

| Column the brief names | Coverage |
|---|---|
| `import_value_usd` | 100% |
| `net_weight_kg` / `unit_value_usd_per_kg` | 96.5% |
| `tariff_rate` | **99.6%** (96.8% measured in-year) |
| `dist` | **100%** (carried forward past 2021, stamped) |
| `importer_gdp_usd`, `importer_gdp_per_capita_usd` | 100% |
| `fta_in_force` | 100% |
| `pci` | **100%** |
| `importer_lpi_*` (7 columns) | 99.2%, stamped with the survey wave |

---

## 2. What the brief asked for that the project did not have

Four items. Three were fetched on 22/08; the fourth cannot be.

### 2.1. Product complexity — was missing entirely, now complete

The brief lists it beside distance, GDP and the RTA dummy as a required
covariate. It was the only one of the four with nothing at all on disk.

Harvard Growth Lab, Atlas of Economic Complexity v18. PCI at HS92 four digits,
1995-2024. Because the panel's product families are keyed to H0 — which *is*
HS1992 — the join is the family code's first four characters, with no
concordance in between: **1,216 of 1,216 four-digit groups matched, 100.0% of
episodes**.

### 2.1b. Tariffs for 2022-2023 — and a trap that would have silently emptied the EU

The tariff pull was extended to 2023 on 22/08, which took the last two panel
years from **no measured tariff at all** to 96.5% and 95.6% measured in-year.

One finding is worth carrying into any future extension: the EU tariff mapping
stopped at 2021, so for 2022-2023 the **twenty-seven EU importers mapped to
themselves**, and since TRAINS has no individual code for them they were dropped
from the target list *without even a 404*. The pass reported "0 without data"
while a fifth of the panel had no tariff. It surfaced only because a smoke test
on three countries happened to draw Germany.

TRAINS files **no preferential schedule for 2022 or 2023** — verified directly
against Japan, Korea, India and the EU. So the last two years read MFN for
everyone, and the rate is **overstated** for the ~39% of episodes with an
agreement in force. `fta_in_force` marks them.

### 2.2. The 2025 US reciprocal tariff — was believed to need a paid key; it does not

The standing note in this project said this needed a **WTO I-TIP subscription
key**, and that was wrong. The measure is written into the **US tariff schedule
itself**, chapter 99, and the USITC publishes that over an open REST endpoint.
So does the Federal Register for the orders behind it.

Collected: 166 headings, **109 carrying a country rate across 85 countries**.
Viet Nam appears exactly as the brief describes: **+46% from 9 April 2025**
(since terminated), the **+10%** universal floor, **+20% from 7 August 2025**,
and the **+40%** transshipment penalty. Every competitor the brief names is in
the same table — Cambodia 49→19%, Bangladesh 37→20%, Indonesia 32→19%, India
26→25%, China 34% — which is what a trade-diversion control needs.

**Still open: product scope.** The exempt subheadings sit in a chapter-99 legal
note the REST endpoint does not return. The note PDF is on disk; the HS8 list
has not been extracted from it. Until it is, the rate is a country-level
variable. For Viet Nam this is not a footnote — electronics is both its largest
export to the US and among the most likely categories to be exempt.

### 2.3. Green LPI — the headline score was on disk, the components were not

No published GLPI construction starts from the headline LPI; they all start from
the six sub-indices. Those, plus CO2 per capita and renewable-energy share, were
fetched on 22/08. They are merged raw and stamped with the survey wave they came
from. **Which construction to follow is a research decision** — see §4.

### 2.4. Quantity — asked for in the brief, present in the raw files, never carried through

The brief asks for volume as well as value. `net_weight_kg` was in every raw
Comtrade file and had never been carried into the panel. It is now, along with
`unit_value_usd_per_kg`, at **96.5% coverage** — which is what separates a
relationship that died because the buyer left from one that died because the
price collapsed.

---

## 3. What the brief asked for that remains partly unmet

| Item | What is short | Can more downloading fix it? |
|---|---|---|
| **Preferential tariffs** | Only 13 reporters file a schedule naming Viet Nam, and **none at all for 2022-2023**. The rest of its preferential access sits under group codes (ASEAN, AANZFTA, GSP) whose membership WITS will not publish, so those episodes fall back to MFN and the rate faced is **overstated** | **No.** `fta_vn.csv` recovers *whether* a preference applied for 38.8% of episodes; the rate itself stays unobserved |
| **NTM at HS6 x year** | The three public WITS files are one sector-level cross-section. 20.4% of episodes have no NTM at all, and China and Korea have no record | **Yes, and no account is needed** - corrected 23/08. `POST api-trains2.unctad.org/denormalisedMeasures` answers unauthenticated; what looked like an auth wall was a malformed body. The constraint is a Cloudflare rate limit, not a login |
| **Trade remedies after 2015** | TTBD stopped in June 2016. The in-force flag stays non-zero to 2023 only because a measure with no recorded revocation is treated as still running — i.e. extrapolation | Partly: the WTO semi-annual reports could be scraped |
| **Product scope of the 2025 US tariff** | Country-level only; see §2.2 | Yes, but it means parsing a 14 MB legal PDF |

---

## 4. What needs a decision before more data helps

These are not download problems. Each changes what gets collected next or what
the estimates mean, and none of them is the machine's to settle.

### 4.1. Does the panel window move to 2024-2025?

**This is the big one, and it is specific to this brief.** The brief's central
covariate is the 2025 US tariff shock. The panel currently ends in **2023**, so
as it stands **no relationship in it can ever be observed dying under that
shock**. The 2025 tariff table is real data with nothing in the panel to meet.

What was found on 22/08: **Comtrade now carries annual HS6 data for 2025**, and
the United States is among the reporters. Viet Nam's 2025 exports to the US, as
the US filed them, are **USD 199.0 bn — up 42% on 2024**, which is the shape
front-running ahead of a tariff would leave.

| Year | Importers that filed | On disk |
|---|---|---|
| 2023 | 167 worldwide, 147 of ours | ✅ all |
| 2024 | 140 worldwide, **126 of ours** | ✅ all 126 |
| 2025 | 98 worldwide, **89 of ours** | ✅ pulled 22/08 — 101,253 HS6 records, USD 524.1 bn, and **zero** false empty-years recorded |

**Against moving the window:** coverage thins from 147 importers to 126 and then
89; Viet Nam has filed neither 2024 nor 2025, so the mirror cross-check
disappears; TRAINS has no tariff schedule for either year (404, checked); CEPII
gravity stops at 2021 and TTBD at 2015.

**For moving it:** `build_spells.py` already censors an importer at its own last
filing rather than recording a death, so the thinning produces *fewer* observed
events, not fake ones — the mechanism that protects Russia and Belarus protects
these too. And without 2025 the brief's central question cannot be asked of the
data at all.

**What it costs if the answer is yes:** the world-imports denominators have to
be pulled for 2024-2025 as well, or `rca`, `world_growth_pct` and
`vn_market_share_pct` go blank for those years — that is the heavy pull, roughly
230 further importer-years. Tariffs would not follow: TRAINS answers 404 for
2024 and 2025, so those years would carry no tariff of their own at all, and the
2025 US schedule in `us_tariffs_2025.csv` would have to stand in for the one
market it covers.

### 4.2. Which Green LPI construction?

The components are on disk. Which environmental series enter and with what
weights differs across the published GLPI papers, and the brief itself says to
take the formula from one of them. **Name the paper and the index can be built
in an hour.**

### 4.3. Comtrade or BACI as the primary source?

The brief recommends CEPII BACI over raw Comtrade, "vì clean hơn". This project
is built on importer-reported Comtrade with Viet Nam's own filing kept as a
mirror check. BACI HS92 V202501 is available, 2.3 GB, and covers 1995-2023.

The trade-off is real: BACI reconciles the CIF/FOB gap and the mirror
discrepancies, but it ends at 2023 — so choosing BACI as the primary source
**forecloses §4.1**, because there is no BACI year in which the 2025 tariff
exists. A defensible middle path is to keep Comtrade as primary and use BACI as
a robustness check on the spell definitions.

### 4.4. The one-year spells

Unchanged from the earlier documents, and still the decision that most changes
what the estimated hazard means: **53.2% of spells last exactly one year** at a
USD 10,000 threshold. Keep them, raise the threshold, or model them separately.

---

## 5. What only the user can unlock

| # | Action | Unlocks |
|---|---|---|
| 1 | ~~Register for **TRAINS Online**~~ | ❌ **NOT NEEDED (23/08).** The endpoint answers without a login; see COVARIATES_ADDED.md §13 |
| 2 | Decide §4.1 (window), §4.2 (GLPI formula), §4.3 (source), §4.4 (one-year spells) | Everything downstream |

WTO I-TIP is **no longer on this list**. It was there for the 2025 US tariff, and
that turned out to be obtainable without it.
