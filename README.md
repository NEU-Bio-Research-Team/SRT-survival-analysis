# Vietnamese export survival — Stage 1 panel

A spell-level panel of **Viet Nam's export relationships**, built from WITS and
UN Comtrade, for survival analysis of how long a relationship lasts.

One relationship is one **(importer × product family)** pair. A spell starts
the year Viet Nam first exports that family to that importer, and ends the year
the flow stops — provided the years that would confirm the stop were actually
published. The panel is the observation-year expansion of those spells, with
tariffs, non-tariff measures, EVFTA staging, trade-remedy cases and macro
covariates attached.

**The current panel is v2 (20/09/2026).** v1 manufactured deaths and should not
be used; see [§ What changed in v2](#what-changed-in-v2).

```
data/final/stage1_panel.parquet   932,204 rows × 209 columns   178 MB
```

| | |
|---|---:|
| Exporter | Viet Nam only |
| Importers | 147 |
| Product families | 4,365 present (4,522 in the key) |
| Spells | 189,830 |
| Events (confirmed deaths) | 112,885 |
| Window | 2002–2025 |
| B0 sample (EU27, 2012–2024, alive rows) | 146,042 rows / 15,958 events |

---

## Start here

1. **What each column means** —
   [`docs/TU_DIEN_DU_LIEU_FINAL_DF.md`](docs/TU_DIEN_DU_LIEU_FINAL_DF.md).
   Source, grain and formula for all 209 columns.
2. **How the modules are joined** —
   [`docs/KHOA_GHEP_STAGE1_PANEL.md`](docs/KHOA_GHEP_STAGE1_PANEL.md). The six
   join keys, which module attaches at which key, and the traps (country codes,
   `EUN`, HS revisions).
3. **Why the panel looks the way it does** —
   [`docs/STAGE1_PANEL_FIX_PLAN.md`](docs/STAGE1_PANEL_FIX_PLAN.md). Every
   defect found in v1, how it was fixed, and §7 for the limits that remain.
4. **What was collected and from where** —
   [`docs/DATA_HANDOFF.md`](docs/DATA_HANDOFF.md).

The data itself is not in git (5.8 GB). Get it from the team's Drive/USB copy,
or rebuild it — see below. `data/final/README.md` explains the parquet/CSV
choice.

## Rebuilding from raw

In this order. Full details and runtimes in
[`docs/STAGE1_PANEL_FIX_PLAN.md`](docs/STAGE1_PANEL_FIX_PLAN.md) §8.

```
python3 scripts/fetch_concordance_unsd.py        # UNSD correlation tables
python3 scripts/extend_eu_tariff_mapping.py      # EU mapping to 2025
python3 scripts/screen_hs6_coverage.py           # selection/hs6_unobserved_years.csv
python3 scripts/build_spells.py                  # families, spells, episodes
python3 scripts/build_evfta_staging.py
python3 scripts/build_eu_mfn_cn.py --families-only
python3 scripts/build_eu_tariff_panel.py
python3 scripts/fetch_cbam_scope.py
python3 scripts/extract_us_exemptions.py
python3 scripts/build_ntm6.py
python3 -c "import sys; sys.path.insert(0,'scripts'); import build_covariates as b; b.build_ttbd(b.importers())"
python3 scripts/merge_panel.py
python3 scripts/build_stage1_df.py features
python3 scripts/build_stage1_df.py join
```

Then confirm the result:

```
python3 scripts/audit_stage1.py --tag v2 --family-map data/interim/family_map.csv
```

All 18 checks must pass. The report lands in `docs/audit/`. The same script
fails 11 checks on the v1 panel, which is how we know the checks bite.

## Layout

| Path | What it holds |
|---|---|
| `scripts/` | The whole Stage 1 pipeline: `fetch_*` pull from APIs, `build_*` construct interim tables, `merge_panel.py` joins them, `build_stage1_df.py` writes the final panel, `audit_stage1.py` checks it. |
| `selection/` | Hand-maintained inputs the build reads: importer screens, the EU tariff-reporter mapping, the unobserved-year list, the mass-death allowlist. Tracked in git. |
| `docs/` | Why each decision was made. Data dictionary, join keys, fix plan, audit reports, collection log. |
| `data/` | Not in git. `raw/` from the APIs, `interim/` the build's intermediate tables, `final/` the panel, `v1_backup/` the frozen v1 files with their sha256. |
| `Stage1_Research_Framework.md` | The advisor's research framework, blocks B0–B9. B0 is the EU27 sample Stage 2 should target. |

## Everything after the panel was removed

On 20/09/2026 the repository was reset to Stage 1 alone. The survival
benchmark, the slide deck, the baseline KM/hazard tables and the v1-era review
documents are gone from the tree. They were built on the v1 panel, and the
team is re-running the modelling stage from the v2 panel rather than
inheriting that work.

Nothing was destroyed. Commit `dbae191` is the last one that contains them:

```
git show dbae191 --stat                      # what was there
git show dbae191:legacy/README.md            # what each piece was
git checkout dbae191 -- legacy/benchmark     # bring a piece back
```

Two things to know before reviving any of it. The benchmark code resolved the
repository root by walking up from `__file__`, and the `legacy/` level was
compensated for in that commit — restore it to the root and each `ROOT` needs
one `dirname` removed again. And of its runs, only `eu27_v4` was scored on the
v2 panel: `v1` and `eu27_v1` used a censoring convention since found to be
wrong, and `eu27_v2`/`eu27_v3` ran on the v1 panel.

## What changed in v2

An audit of all 949,537 v1 rows found seven defects in the target and nine in
the features. The four that changed the most:

- **HS revision orphans.** WITS revision tables are many-to-one. When codes
  merge, only one keeps a successor and the rest "die" at the switch — 1,982 of
  1,983 exposed rows, at every switch of every importer. Families are now built
  by merging each orphan into its receiver within the same HS4, which resolves
  70% of exposed rows; the rest are censored.
- **Unobserved years read as observed.** Unpublished years, interior holes and
  the edge of the window all produced deaths. One rule now covers them: a death
  in year E is an event only if E+1 … E+1+gap were published at HS6. Every
  spell carries `censor_reason` and `start_reason`.
- **`log_total_import_cp_lag1` came from an arbitrary importer** — wrong on
  94.6% of rows, and non-deterministic between builds.
- **EU tariffs ignored preference schedules**, producing a fake +4.1 pp tariff
  shock in 2022 while the true applied rate was falling.

The effect on the target: 131,675 events became 112,885, and EU27 hazard in
2016 fell from 13.4% to 12.1%. Before/after for every figure is in
[`docs/STAGE1_PANEL_FIX_PLAN.md`](docs/STAGE1_PANEL_FIX_PLAN.md) §8; the audit
reports are [`docs/audit/stage1_v1.md`](docs/audit/stage1_v1.md) and
[`docs/audit/stage1_v2.md`](docs/audit/stage1_v2.md).

## What is still open

From [`docs/STAGE1_PANEL_FIX_PLAN.md`](docs/STAGE1_PANEL_FIX_PLAN.md) §7:

- Orphans with no same-HS4 receiver (~30% of exposed rows) are censored, so
  their post-switch history is lost.
- Group-coded preference schedules outside the EU are still unfetched; MYS,
  MEX and others keep MFN as an upper bound, flagged by
  `tariff_pref_observed = 0`.
- The panel uses Comtrade importer-reported CIF values. Reconciliation against
  BACI is not done.
- Partial transfers — an H0 code that keeps a successor but loses part of its
  content — affect the value level only. `revision_switch` lets models absorb
  the break.

## Secrets

`.env` holds `COMTRADE_PRIMARY_KEY` and is never committed. Three scripts read
it: `fetch_trade.py`, `select_countries.py`, `select_importers_vn.py`. The rest
of the pipeline runs without credentials.
