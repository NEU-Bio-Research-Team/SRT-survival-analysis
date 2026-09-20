# legacy/ — frozen work from before the v2 panel

Everything here was built on the **v1 Stage 1 panel**. That panel manufactured
deaths: HS revision orphans died at every switch, unpublished years counted as
observed, and `log_total_import_cp_lag1` was read from an arbitrary importer.
The defects and their measured sizes are in
[`docs/STAGE1_PANEL_FIX_PLAN.md`](../docs/STAGE1_PANEL_FIX_PLAN.md) §1.

**Nothing in this directory is a current result.** The numbers in the reports
and review documents were computed on data we now know to be wrong, and the
slides present those numbers. Keep them for provenance — to show what was run,
when, and how the conclusions moved — not to cite.

The one exception is `benchmark/runs/eu27_v4` and `benchmark/reports/eu27_v4`,
which *were* run on the v2 panel (20/09/2026) with the corrected fold rule.
They are here because the whole modelling stage is frozen while Stage 1
restarts, not because they are stale.

---

## What is in here

| Path | What it is |
|---|---|
| `benchmark/` | The survival benchmark: 10 models, IPCW metrics, rolling-origin folds, feature registry, permutation importance. Runs `v1`, `eu27_v1` … `eu27_v4`. |
| `deck/` | The slide pipeline (`src/*.py` → `out/*.pptx`) for the data presentation. Figures and output are gitignored; rebuild with the scripts in `deck/src/`. |
| `analysis/` | KM survival, baseline hazard and threshold-sensitivity tables from `scripts/survival_baseline.py`. Gitignored; rebuild by running that script. |
| `docs/SRT_Literature_Review_and_Benchmark_Plan.md` | Literature review of the four seed papers and the benchmark plan built from it. |
| `docs/SRT_Benchmark_Structured_Review.md` | Structured review of the global `v1` benchmark run. |
| `docs/SRT_Benchmark_EU27_B0_Structured_Review.md` | Structured review of `eu27_v3`, the run closest to the advisor's B0 block. |
| `docs/KE_HOACH_THUYET_TRINH_DATA.md` | Plan for the 25-minute data presentation. |
| `docs/TIEN_DO_SO_VOI_SINKING.md` | Progress against the "Sinking Relationships" brief as of 25/08/2026. Superseded by [`docs/DATA_HANDOFF.md`](../docs/DATA_HANDOFF.md). |
| `docs/README_v1_2026-08-25.md` | The repository README as it stood on 25/08/2026, describing the v1 panel (747,719 episodes). Kept because several documents still cite its section numbers. |

## Reading the benchmark numbers

Three separate things invalidate cross-run comparison, so check which applies
before putting two leaderboards side by side:

1. **`v1` and `eu27_v1` used a broken censoring convention.** With mixed 1–5
   year follow-up the old 3-year Brier read 0.1851 against a true 0.2039.
   Fixed and pinned by `benchmark/evaluation/test_censoring_convention.py`.
   Do not cite those two runs at all.
2. **`eu27_v2` and `eu27_v3` ran on the v1 panel.** Their event counts include
   the manufactured deaths. The clearest symptom: the F4 policy feature block
   *hurt* every model, which traces to a fake +4.1 pp EU tariff shock in 2022
   (defect F3).
3. **`eu27_v4` ran on the v2 panel with new folds.** Only rankings and
   directions can be compared with v3 — the panel, the folds and the censoring
   rule all changed at once.

## Running any of it again

Paths were rewritten when this directory was created, so the code still
resolves the repository root correctly. Run the benchmark with `legacy/` on the
import path:

```
cd legacy
python3 -m pytest benchmark/splits/test_censor_gap.py benchmark/evaluation/test_censoring_convention.py
python3 benchmark/run_benchmark.py --help
```

The benchmark needs `pyarrow`; the conda env `drug-tox-env` has it, the default
`python3` does not.

The deck scripts read paths relative to the repository root, so run them from
there:

```
python3 legacy/deck/src/make_figs.py
python3 legacy/deck/src/build_deck.py
```
