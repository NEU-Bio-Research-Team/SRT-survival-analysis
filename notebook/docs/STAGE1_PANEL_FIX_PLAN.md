# Stage 1 panel: fix plan (v1 → v2)

*Written 19/09/2026. Based on an independent audit of
`data/final/stage1_panel.parquet` (949,537 rows × 205 columns). The audit
measured the data directly. Its figures are the baseline below.*

**Status 20/09/2026:** implemented on branch `fix/stage1-panel-v2`; see §8 for
what was done, what changed, and the one open decision (benchmark splits).

Related: [KHOA_GHEP_STAGE1_PANEL.md](KHOA_GHEP_STAGE1_PANEL.md) describes the
join keys and lists some of these defects. The audit found several that it
does not list, and corrects two of its figures (§1).

---

## 0. Goal and definition of done

The v2 panel is done when all of the following hold:

1. **The target is right.** No `event = 1` is produced by a measurement
   artefact: HS revision switches, unpublished years, or the edge of the
   observation window.
2. **Every feature the benchmark reads is right at its declared grain.** Lags
   match the variable's own value in `year − 1`, and nothing is borrowed from
   another importer.
3. **No stamped value comes from the future.** A `*_source_year > year` is
   allowed only where the variable is documented as static.
4. **The build is deterministic and audited.** Two builds give identical
   files, and `scripts/audit_stage1.py` passes every check in §6.

---

## 1. Defects to fix (baseline v1)

| ID | Defect | Where | Measured on v1 | Hits | Severity |
|---|---|---|---|---|---|
| T1 | **HS orphan false deaths.** The WITS tables are many-to-one. When a revision merges H0 codes, only one keeps a successor, and relationships in the others "die" at the switch. The receiving family gets a false birth or a value jump. | `build_spells.py::build_families` | 1,982 of 1,983 exposed rows die (every importer, every switch). About 1,671 excess deaths: 444 in EU27, 1,227 outside. EU B0: 145/145 in both 2016 and 2021. Example: H0_620213 (21 EU importers) dies in 2021 while H0_620293 rises +74% in 2022. | target | HIGH |
| T2 | **Unpublished year read as observed.** `_empty_years.csv` rows with reason "no HS6 rows in a batch that returned data for other years" count as observed years. | `build_spells.py::observed_years`, `complete_importers` | 15 importers (2024). 1,814 false deaths in 2023, ARE alone 1,064. | target (global) | HIGH |
| T3 | **Death rule differs at T−1.** With `GAP_TOLERANCE = 1` a death needs two absent years, but at `T_i − 1` only one can be seen. | `build_spells.py:433` | Hazard 15.1% at T−1 vs 11.5–12.6% at T−2…T−5. EU: 2024 = 13.3% vs 2023 = 11.0%. | target (fold 3, EVFTA-1y fold) | HIGH |
| F1 | **`log_total_import_cp_lag1` taken from a random importer.** The variable is importer-specific but is lagged at `(family, year)` via an arbitrary `.unique()`. The result is also non-deterministic. | `build_stage1_df.py:250-253` | Wrong on 94.6% of rows. Used in every registry, including `eu27_v3`. | feature | HIGH |
| F2 | **Group-coded preferences dropped.** Preference schedules filed under TRAINS group codes (`N52`, `C02`, `G27`…) are never fetched or matched, because `partner_groups()` is a stub. | `fetch_tariffs.py`, `merge_panel.py:154-161` | `tariff_rate` is 100% MFN for MYS, SGP, THA, IDN, PHL, KHM, BRN, IND, NZL, CAN, MEX, PER, HKG. EU: MFN before 2020 (GSP ignored), PREF 2020–21, back to MFN in 2022. | feature | HIGH |
| F3 | **Fake EU tariff shock.** A consequence of F2. | derived `tariff_change` | EU mean `tariff_change`: −3.91 pp in 2020, **+4.14 pp in 2022**, while the true applied rate falls from 1.31% to 0.90%. | feature (fold 3 test) | HIGH |
| F4 | **EU reporter lookup stops at 2023.** `attach_tariff` has no `min(year, 2023)` guard, unlike the CBAM and EVFTA attachers. | `merge_panel.py:322`, `selection/eu_tariff_mapping.csv` | EU rows in 2024: 70.5% null `tariff_rate` (old members). New members read their *own* 2023 file instead of EUN. | feature | MEDIUM |
| F5 | **MFN running mean.** `(old + new) / 2` in read order. PREF uses `min` instead, and the two are then compared with each other. | `merge_panel.py:131-134, 149-150` | 2.2% of cells have ≥3 lines, and 0.21% of cells are off by ≥1 pp. EUN p90 is 0.7 pp. | feature | LOW |
| F6 | **Future-dated fills.** Years before the first survey take the first survey. | `build_ntm6.py:279`, `merge_panel.py::lpi_source_year`, `ntm_ave` | Full panel: NTM6 35.1%, `ntm_ave` 47.6%, `ntm_survey_year` 40.6%, LPI 9.7%. B0: `ntm_ave` 31.1%, `ntm_survey_year` 24.3%. | feature | LOW (B0) / MEDIUM (global) |
| F7 | **TTBD ends in 2015, yet later years are written as values.** Cases initiated after 2015 silently read as 0, the registry uses `missing: zero`, and `ttbd_observed` is not in the model. | `build_covariates.py::build_ttbd` | `ttbd_observed = 0` from 2016 on, but `ttb_any_in_force` is non-null. | feature | MEDIUM |
| F8 | **Structural NTM zeros.** Families with no H4 successor can never receive an NTM. Counts before a reporter's first collection year are structurally zero. | `build_ntm6.py` | 493 B0 rows are 100% zero. | feature | LOW |
| F9 | **NTM EU mapping is not year-specific.** The last row wins, so HRV reads EUN for 2002–2012 and GBR reads GBR for every year. | `build_ntm6.py::reporter_of` | Not in B0. | feature | LOW |
| K1 | **The family key has three implementations.** `fetch_cbam_scope.py`, `extract_us_exemptions.py` and `build_ntm6.py` read the concordance themselves instead of calling `family_of`. | those three scripts | Harmless today. It would silently misalign keys as soon as families change (T1). | key | prerequisite for T1 |

**Found while implementing (20/09/2026), fixed in v2:**

| ID | Defect | Measured | Fix |
|---|---|---|---|
| T4 | **Interior holes read as deaths.** Years missing at HS6 inside an importer's record - no file (DZA 2018-2021, KEN 2011-2012, NGA 2004-2005) or an `_empty_years.csv` entry of any kind (ARE 2009 "only the 999999 aggregate") - counted as observed. | 31 importer-years lose >60% of their relationships at once in v1, 14 of them at 100% (ARE 2008: 455 of 455). | One rule for T2-T4: a death in E is an event only if E+1 .. E+1+GAP were all published at HS6 (`censor_reason`); starts mirror it (`start_reason`, `left_trunc`). |
| T5 | **Double-counted trade.** 12 legacy files (BRA 2002-2007, CHN 2015-2017, NIC 2016-2017, BDI 2010) carry the customs-procedure breakdown *and* its total: every value is exactly 2x. | HS6 / reporter TOTAL = 2.00 for BRA and NIC, 1.5-1.6 for CHN. | Re-fetched with the aggregate filter; the old files are in `v1_backup/raw_trade_double_counted/`. |
| T6 | **HS6 detail far below the reporter's own total.** | 13 importer-years with coverage < 50% (ALB 2014: 7 lines, 47%). | `scripts/screen_hs6_coverage.py` writes `selection/hs6_unobserved_years.csv`; those years count as unobserved. CHN from 2015 (0.73-0.94) is persistent partial coverage and stays observed. |
| T7 | **No build-time check against mass deaths.** | - | `build_spells.py` stops when >60% of an importer's live relationships (n >= 30) die in one year, unless `selection/mass_death_allowlist.csv` gives a verified reason. 16 such cases remain; each was checked against the reporter's TOTAL and the VN mirror and is genuine. |

**Verified clean on v1 (keep these as regression checks):**
- key uniqueness;
- spell contiguity, `event` only on the last row, and `event = 1 − right_censored`;
- threshold vs `gap_filled`;
- calendar-year lags for `log_value_lag` and `tariff_rate_lag1` (0 mismatches);
- ISO3 ↔ numeric codes (no expired codes);
- 100% of raw trade value inside the concordance graph;
- DEU value re-aggregation from raw (0 mismatches);
- DESTA/TTBD name mapping (0 unmapped names).

**Corrections to KHOA_GHEP §7.2:**
- The 2016 figure is 145/145 (100%), not 58%. The 58% came from using the H6 orphan set instead of the H5 one.
- The problem is not limited to EU 2016/2021: it occurs at every switch of every importer.

---

## 2. Decisions needed before coding

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | How to fix T1 | (a) merge families with UNSD n:n correlations; (b) censor at the switch; (c) drop affected families; (d) change trade source | **Hybrid: (a) constrained to the same HS4, then (b) for the rest.** Measured: pure connected components create a 1,368-code family spanning dozens of chapters, which is unusable. A targeted orphan → receiver merge without a constraint still yields families of 228 and 36 codes. **Restricted to the same HS4, the largest family has 10 codes and 70% of exposed rows are resolved (EU 73%).** The remaining 30% are censored. Within-HS2 resolves 88% but allows families of 64 codes. |
| D2 | How to fix T3 | censor spells ending at `T_i − GAP_TOLERANCE`; or keep them and add an `event_unconfirmed` flag | **Censor.** It is the only choice that keeps the event definition identical across years. |
| D3 | Tariff scope | EU now (from `eu_tariff_panel`), global group preferences later; or everything now | **EU now, global later.** B0 only needs the EU. The group-code work is large, and MYS and MEX have no preference schedules in TRAINS at all. |
| D4 | TTBD after 2015 | null after the last TTBD year; or find a newer release | **Null now** and keep `ttbd_observed`. Any newer source must be verified before use. |
| D5 | Years before the first survey (NTM6, LPI) | null; or keep the first-wave value | **Null.** Keep `ntm_ave` as an explicitly static trait: it is one 2017 estimate per importer, and on EU27 it is constant within importer. |
| D6 | Trade source (pending the advisor's B0 decision on BACI HS2012) | stay on Comtrade with the fixed families; or switch to BACI | Fix on Comtrade now. Do **not** assume BACI removes T1: if CEPII converts revisions with one-to-one tables, the same orphans appear. Check CEPII's documentation first. |

---

## 3. Work plan

Work on a new branch (for example `fix/stage1-panel-v2`). Each phase ends with
an audit run whose report is committed under `docs/audit/`.

### Phase 0: freeze the baseline and build the audit harness (before any fix)

1. **Back up v1.** The data is not in git, so copy these into `data/final/v1/`
   and `data/interim/v1/`, and record their sha256:
   - `stage1_panel.parquet`
   - `spells.csv`, `episodes.csv`, `panel_final.csv`
   - `benchmark_matrix_eu27_v2.parquet`

   There is 905 GB free, so size is not a concern.
2. **Write `scripts/audit_stage1.py`.** It encodes every check in §6. It reads
   the parquet column-group by column-group (8 GB machine) and writes
   `docs/audit/stage1_<version>.md` plus a JSON with the raw numbers.
3. **Run it on v1.** The report must reproduce the baseline column of §6. That
   proves the checks detect the defects before we trust them to confirm the
   fixes.

### Phase 1: one family module (K1), then the target (T1, T2, T3)

**1.1 Centralise the family key (K1).**
- Create `scripts/families.py` with `build_families()` and `family_of()`,
  moved out of `build_spells.py`.
- It also writes `data/interim/family_map.csv` with the columns
  `revision, hs6, family, h0_codes, merge_reason`.
- Refactor `build_ntm6.py::h4_to_h0`, `fetch_cbam_scope.py` and
  `extract_us_exemptions.py` to use it.
- Done when the rebuilt v1-equivalent outputs are byte-identical. This step
  changes structure only, not behaviour.

**1.2 Orphan fix (T1, hybrid per D1).**
1. **Fetch the UNSD tables.** Add a fetcher for the six UNSD "Correlation and
   conversion" tables into `data/raw/concordance/unsd/` and record their
   sha256. Sources, all verified reachable on 19/09 at
   `unstats.un.org/unsd/classifications/Econ/tables/`:
   - HS1996→HS1992
   - HS2002→HS1992
   - HS2007→HS1992
   - HS2012→HS1992
   - HS2017→HS1992
   - HS2022→HS1992

   Only the *Correlations* sheets are needed; the HS2022 one has 18,900 links.
2. **Merge orphans into receivers.** In `build_families()`, after the WITS
   unions: for each revision `r` and each H0 code `h` with no WITS successor in
   `r`, take the `r`-codes that UNSD correlates with `h`, map each to its WITS
   H0 target `d`, and union `h` with `d` **only if `d[:4] == h[:4]`**.
3. **Name families deterministically.** The family id is the smallest H0 code
   in the family. Because merges stay inside one HS4, `hs2`, `product_hs4` and
   the PCI key stay valid without further change.
4. **Record the revision in force.** Persist a per-importer-year HS revision
   table, `data/interim/importer_year_revision.csv`, built from the raw
   `hs_revision` values.
5. **Censor what cannot be merged.** In `build_spells()`, when an importer's
   revision changes between `Y` and `Y+1` and the family has no code in the new
   revision, a spell ending in `Y` becomes right-censored with
   `censor_reason = "hs_revision"`. The rule is symmetric, so it also covers
   the backward switches (BWA, LSO, DMA, RWA, QAT).
6. **Expose the result.** Add the columns `family_n_h0`, `family_merged` and
   `censor_reason`.

**1.3 Unpublished years (T2).**
1. First, re-query Comtrade for the 15 importer × 2024 cells
   (`fetch_trade.py`). They may have been published since August.
2. Split the `_empty_years.csv` reasons into two kinds:
   - `filed_no_hs6` counts as observed;
   - `batch_empty` counts as **unobserved**.

   Apply the split in `observed_years()` and `complete_importers()`.
3. Add a build-time **mass-death guard**. It fails the build when more than 60%
   of an importer's alive relationships end in the same year, unless that
   importer-year is allowlisted with a written reason.

**1.4 Window edge (T3).**
1. Set `right_censored = end >= last_year[imp] - GAP_TOLERANCE`, with
   `censor_reason = "window_edge"`.
2. Downstream effect: the last confirmable event year for the EU becomes 2023.
   `benchmark_eu27_v2.yaml`'s `outcome_observed_through` and the fold/horizon
   observability comments must be re-derived (§5).

### Phase 2: features (F1–F9)

**2.1 Lags (F1).**
1. Move `log_total_import_cp` to the relationship-level lag, at grain
   `(importer, product_family, year − 1)`.
2. Before any family-grain lag, assert that the column is constant within
   `(product_family, year)`. The EU policy columns must be constant within the
   EU rows.
3. Replace every bare `.unique(subset=…)` with `maintain_order=True` plus that
   assertion.

**2.2 Tariffs (F2–F5, EU scope per D3).**
1. Extend `selection/eu_tariff_mapping.csv` through 2025, carrying the 2023
   membership, and drop the `min(year, 2023)` guards. This fixes F4 at the
   source and lets F9 use the same table year by year.
2. For EU27 rows, fill the generic `tariff_rate` / `tariff_type` from
   `eu_tariff_panel` (`applied_pct`, `applied_source` ∈ {gsp, evfta, mfn}).
   Recompute `tariff_rate_lag1` and `tariff_change` from it. In the EU27
   registry, keep **one** tariff level variable, not both `tariff_rate` and
   `tariff_applied_*`.
3. Fix the aggregation per HS6 line:
   - applied = min(pref, mfn) where a preference exists;
   - family rate = true simple mean of the lines;
   - add `tariff_n_lines`.

   This matters more once T1 merges families.
4. **Deferred global step (after B0).** Decode the TRAINS group codes (names
   from the WITS metadata) and build `selection/trains_groups_vn.csv`: group,
   name, whether VN is a member, entry-into-force year, and a verification
   source. Fetch those group schedules, and cross-check them against DESTA
   `fta_in_force`. Where no schedule exists (MYS, MEX…), keep MFN and add
   `tariff_pref_observed = 0`.

**2.3 Fills and zeros (F6–F9).**
1. NTM6 and LPI before the first survey → null.
2. `ntm6_*_inforce` before the first collection year → null.
3. TTBD columns after 2015 → null.
4. Families that are still H4 orphans after 1.2 → null NTM plus a flag.
5. `reporter_of` → keyed by `(iso3, year)`.
6. Registry: add `ttbd_observed`, or drop the TTBD features for B0.

### Phase 3: rebuild and validate

Rebuild in dependency order. Each step is its own process, as the 8 GB
constraints documented in the scripts require.

```
1. fetch UNSD concordances; re-fetch the 15 × 2024 trade cells
2. build_spells.py                    -> spells, episodes, family_map, importer_year_revision
3. build_evfta_staging.py, build_eu_mfn_cn.py, build_eu_tariff_panel.py
4. build_ntm6.py, fetch_cbam_scope.py (rebuild only), extract_us_exemptions.py
5. merge_panel.py                     -> panel_final.csv
6. build_stage1_df.py features ; build_stage1_df.py join
7. audit_stage1.py                    -> must pass every check in §6
8. v1 vs v2 diff report               -> rows, spells, events by year x EU/non-EU,
                                         B0 sample size, feature distributions
```

For the determinism check, run step 6 twice and compare the hashes.

### Phase 4: benchmark and docs

1. **Rebuild the matrix.** Re-derive `benchmark_eu27_v2.yaml`
   (`outcome_observed_through`, `last_origin_year`, fold observability) after
   T3. Then rebuild the matrix with `--eu27-only`.
2. **Re-run the leaderboard.** Mark the existing v1 reports as produced on
   flawed labels and features; do not delete them.
3. **Update the docs:**
   - `KHOA_GHEP_STAGE1_PANEL.md` §3.2, §7 and §8;
   - `TU_DIEN_DU_LIEU_FINAL_DF.md` (the new columns);
   - `README.md` counts;
   - `data/final/README.md`.

---

## 4. Order and relative size

| Step | Size | Blocks |
|---|---|---|
| Phase 0 (backup + audit harness) | M | everything |
| 1.1 family module | S | 1.2 |
| 1.2 orphan hybrid | L | Phase 3 |
| 1.3 unpublished years | S | — |
| 1.4 window edge | S | benchmark config |
| 2.1 lags | S | — |
| 2.2 EU tariffs (items 1–3) | M | — |
| 2.3 fills/zeros | S | — |
| 2.2 item 4 (global group preferences) | L | not needed for B0 |
| Phase 3–4 | M | — |

The critical path for B0 is: Phase 0 → 1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2 (items 1–3) → 2.3 → Phase 3 → Phase 4.

---

## 5. Knock-on effects to expect

- **Fewer events and more censoring.** T1, T2 and T3 all turn artefactual
  deaths into censoring. Hazard by year becomes smoother around 2006, 2011,
  2016, 2021 and at each importer's last year. B0 event counts for 2016, 2021
  and 2024 fall.
- **Family count falls** from 4,954 H0 codes to about 4,522 families. Merged
  families carry the combined value, so spell histories for coats,
  sound-recording apparatus and similar products become continuous across
  2022.
- **Benchmark windows shrink by one year at the end.** With the EU observed
  through 2025 and a one-year gap rule, deaths are confirmable only through
  event-year 2023. The EVFTA one-year fold on 2024 origins has no confirmable
  events and needs to be redesigned or dropped.
- **Tariff features change meaning on EU rows.** They go from MFN-with-a-gap to
  GSP → EVFTA → applied, so v1 coefficients and importances on F4 are not
  comparable with v2.

---

## 6. Audit checks (`scripts/audit_stage1.py`)

| # | Check | v1 baseline | v2 target |
|---|---|---|---|
| A1 | duplicate `(importer, product_family, year)` | 0 | 0 |
| A2 | spell invariants (contiguous; event on the last row only; `event = 1 − right_censored`; `t_stop`; gap rows interior and below threshold) | all pass | all pass |
| A3 | raw `(revision, hs6)` outside the family map | 0% of value | 0% |
| A4 | families whose member codes span more than one HS4 | 110 (KHOA_GHEP figure, not re-measured) | no increase; merges never cross HS4 |
| A5 | exposed-orphan rows with `event = 1` at a revision switch | 1,982 / 1,983 | 0 |
| A6 | within-importer birth share, first year of a new revision vs ±2 years | +2.0 pp | ≤ +0.5 pp |
| A7 | importer-years where more than 60% of alive relationships die (not allowlisted) | 14 importers in 2023 | 0 |
| A8 | last observed year per importer falls on a `batch_empty` year | 15 | 0 |
| A9 | hazard at `T_i − 1` minus the mean hazard at `T_i − 2…5` | +2.9 pp | within ±1.5 pp |
| A10 | every `*_lag`/`*_lag1` equals its own value at `year − 1` at the declared grain | `log_total_import_cp_lag1` 94.6% wrong | 0 mismatches |
| A11 | family-grain lag sources constant within `(family, year)` | `log_total_import_cp` varies in 79.8% of groups | constant, or moved to relationship grain |
| A12 | `*_source_year > year`, outside the static allowlist | NTM6 35.1%, LPI 9.7%, `ntm_survey_year` 40.6% | 0 (`ntm_ave` allowlisted as static) |
| A13 | EU27 `tariff_rate` null in 2024–2025 | 70.5% | 0% |
| A14 | EU27 mean `tariff_change` per year, excluding 2020 | +4.14 pp in 2022 | ≤ 1 pp in absolute value |
| A15 | family MFN rate equals the true mean of its lines (sample of reporters) | 0.21% of cells off by ≥1 pp | 0 |
| A16 | value re-aggregation from raw (DEU, USA, FRA, ARE) | DEU 0 mismatches | 0 |
| A17 | non-null TTBD values after the last TTBD year | non-null | null |
| A18 | two builds, identical hash | not deterministic (F1) | identical |
| A19 | report only: PREF share on `fta_in_force` rows per importer | 0% on ASEAN, IND, NZL… | reported; must be > 0 wherever a VN-containing group schedule exists (after the global step) |

---

## 7. Known limits that remain after v2

- **Partial transfers are not repaired.** Where an H0 code keeps a successor
  but loses part of its content, only the value level is affected (the audit
  found no hazard excess for these). A `revision_switch` indicator lets models
  absorb the break.
- **Orphans without a same-HS4 receiver.** These are about 30% of exposed rows.
  They are censored, not continued, so their post-switch history is lost.
- **Markets with no preference schedule in TRAINS.** MYS, MEX and others keep
  MFN as an upper bound, flagged by `tariff_pref_observed = 0`.
- **Mirror data.** The panel uses Comtrade importer-reported CIF values.
  Reconciliation against BACI is still open
  ([DOI_CHIEU_B0_VOI_DU_LIEU.md](DOI_CHIEU_B0_VOI_DU_LIEU.md) §5.1).

---

## 8. Execution record (20/09/2026)

All of Phases 0-3 and the data side of Phase 4 are done on branch
`fix/stage1-panel-v2`. The v1 files are kept in `v1_backup/` (with
`SHA256SUMS`). Audit reports: [audit/stage1_v1.md](audit/stage1_v1.md) (11
checks fail) and [audit/stage1_v2.md](audit/stage1_v2.md) (all 18 pass,
including A18: two consecutive builds are identical in every column).

### v1 → v2

| | v1 | v2 |
|---|---:|---:|
| episode-years | 949,537 | 932,204 |
| spells | 194,461 | 189,830 |
| families present | 4,637 | 4,365 (4,522 in the key) |
| events | 131,675 | 112,885 |
| B0 (EU27, 2012-2024, alive) rows / events | 148,475 / 18,516 | 146,042 / 15,958 |
| EU27 hazard 2006 / 2016 / 2021 / 2024 | 0.167 / 0.134 / 0.122 / 0.133 | 0.145 / 0.121 / 0.112 / 0 (unconfirmable) |
| benchmark matrix EU27 (leaderboard window) origins / events | 148,260 / 18,401 | 145,836 / 15,850 |

Censoring in v2: `window_end` 63,920 spells, `window_edge` 9,500,
`unobserved_year` 2,983, `hs_revision` 542. Unknown starts: `window_start`
17,711, `unobserved_year` 5,502, `hs_revision_receiver` 896, `hs_revision` 253.

### Deviations from the plan

- **T4-T7 were found during the work** (section 1) and fixed with the same
  observation rule as T2/T3.
- **The 15 importer-years of 2024 were not re-fetched**: Comtrade still
  returns only 2023 for them (queried 19/09/2026). They are treated as
  unobserved.
- **12 raw trade files were re-fetched** (T5). The data is now different from
  the Drive/USB copy of 25/08.
- **The global group-coded preferences (step 2.2 item 4) are deferred**, as
  decided in D3.
- **The EU27 registry changed.** `feature_registry_eu27_v4.yaml` is v3 minus
  `tariff_rate_lag`, `ttb_any_in_force` and `ad_in_force`. The matrix
  `data/interim/benchmark_matrix_eu27_v4.parquet` was built with the v2 config.
- **Benchmark splits redesigned (decision (a), 20/09/2026).** Under the gap
  rule a death in D is confirmable only once D+1 and D+2 are seen, but
  `rolling_origin.censor_block` counted D <= observed_through - 1, so every
  train/valid label read one year past its block. It also credited a spell
  whose importer stopped filing with survival up to the horizon.
  `censor_block_gap` (switched on by `target.gap_tolerance` in the config;
  pinned by `benchmark/splits/test_censor_gap.py`) counts an event only for
  D <= horizon - 1 - g and censors at the last year actually alive. New
  config files: `benchmark_eu27_v3.yaml`, `splits_eu27_v3.yaml`,
  `horizons_eu27_v3.yaml`. The folds are: train to 2015/2016/2017, three-year
  validation blocks, single-year tests 2019/2020/2021 (IBS 1-3 observable in
  all three). The v2 EVFTA-1y supplementary fold cannot be built under the
  rule and is dropped. Run: `benchmark/runs/eu27_v4`.

### Rebuild from raw, in order

```
python3 scripts/fetch_concordance_unsd.py        # UNSD correlation tables
python3 scripts/extend_eu_tariff_mapping.py      # EU mapping to 2025
python3 scripts/screen_hs6_coverage.py           # selection/hs6_unobserved_years.csv
python3 scripts/build_spells.py                  # families, spells, episodes (mass-death guard)
python3 scripts/build_evfta_staging.py
python3 scripts/build_eu_mfn_cn.py --families-only   # full run re-parses CN PDFs (~10 min, ~6 GB)
python3 scripts/build_eu_tariff_panel.py
python3 scripts/fetch_cbam_scope.py ; python3 scripts/extract_us_exemptions.py
python3 scripts/build_ntm6.py
python3 -c "import sys; sys.path.insert(0,'scripts'); import build_covariates as b; b.build_ttbd(b.importers())"
python3 scripts/merge_panel.py
python3 scripts/build_stage1_df.py features ; python3 scripts/build_stage1_df.py join
python3 scripts/audit_stage1.py --tag v2 --family-map data/interim/family_map.csv
```

The benchmark scripts need pyarrow. The conda env `drug-tox-env` has it;
the default `python3` does not.

### Benchmark eu27_v4 (panel v2, splits eu27_v3), 20/09/2026

> **The benchmark was removed from the tree later the same day**, when the
> repository was reset to Stage 1 alone. The paths below are as they stood in
> commit `dbae191`, prefixed there with `legacy/`. The numbers are kept because
> they are the evidence that the v2 fixes changed the modelling result, not
> only the data.

198/198 cells, no failures. Reports are in `benchmark/reports/eu27_v4/`.
Scores are **not** directly comparable with eu27_v3: the panel, the folds and
the censoring rule all changed. Only rankings and directions can be compared.

- Full feature set, IBS 1-3 (lower is better):
  - CBNN 0.102
  - RSF 0.104
  - Cloglog 0.106
  - DeepSurv 0.110
  - CoxPH 0.113
  - BoostedCox 0.116
  - KM 0.129

  Antolini C sits at 0.83-0.84 for every model except KM and DeepHit (v3:
  0.81-0.84). RSF beats CoxPH by a significant margin in folds 1 and 2
  (paired spell bootstrap); by fold 3 the gaps between the top models are
  0.001-0.003.
- Effect of adding the F4 policy block (IBS, F0F1F2F3F4 minus F0F1F2F3):
  - v3: +0.024 for CBNN and +0.047 for DeepHit. The block *hurt*, consistent
    with the fake +4.1 pp tariff shock in 2022.
  - v4: between -0.017 and +0.003. The block is neutral or helps for every
    model.
