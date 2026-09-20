# Benchmark: survival of Vietnam's export relationships

An implementation of `SRT_Literature_Review_and_Benchmark_Plan.md`. The plan's
central question is not which model wins but which *assumption* has to be
dropped:

> Given the same economically motivated, leakage-safe covariates, do nonlinear
> and/or non-proportional-hazard survival models improve out-of-sample
> discrimination and calibration of Vietnam export-relationship survival relative
> to traditional hazard models?

Everything here is arranged so that the answer separates the contribution of the
*learning algorithm* from the contribution of the *feature set*.

---

## What is frozen before anything is fitted

`config/` and `features/feature_registry.yaml` are Phase 0. They are not
documentation of the code; the code reads them, so a decision that is not written
there does not happen.

**The prediction task.** A row of the panel — (importer, product family, year) —
is a prediction origin. The panel's convention is that `event = 1` in year Y
means the relationship is *last alive* in Y and dies in Y+1, so remaining
lifetime from an origin in year t is

```
duration_u = last_year_alive - t + 1
```

and `duration_u = 1, event = 1` is identical to the panel's own event flag. That
identity is asserted at the end of `features/build_matrix.py`; if the convention
is ever changed upstream, the build fails rather than scoring the wrong thing.

**The window: origins 2003–2023.**

| Year | Why it is excluded |
|---|---|
| 2002 | first year of the data window — every lag is missing, every live spell left-truncated |
| 2024 | no importer's tariff is measured in its own year after 2023 (contemporaneous share falls 0.96 → 0.00) |
| 2025 | carries zero events *by construction* — a death in 2026 is not observable |

2024–2025 are kept for prospective scenario scoring only (`scenarios/`).

**The primary metric is the Integrated Brier Score over 1–3 years**, not a
concordance index. Stage 2 multiplies a survival *probability* by a trade value,
and a model that ranks perfectly while predicting 0.9 where the truth is 0.6
ruins that calculation with a flawless C-index. The grid stops at three years
because the last test block is 2022–2023 against data ending in 2025: a five-year
IBS is undefined there and would not be comparable across folds. It is still
reported for folds 1–3, where it is genuinely observed.

---

## The two leaks this design is built against

**1. Random splitting.** Rows from the same relationship in adjacent years are
the same fact twice. Validation is rolling-origin (`config/splits.yaml`).

**2. The subtler one — future outcomes reaching the training label.** Disjoint
origin years are *not* sufficient. A relationship with origin 2013 that dies in
2018 carries `duration_u = 6, event = 1` in the frozen matrix, but in 2013 nobody
could know that. So every block is re-censored at its own information horizon
(`splits/rolling_origin.py`): a training window ending in 2013 may only know
whether each relationship was alive through 2013, and everything else is
censored. Without this rule the design leaks the test period through the label
while looking perfectly clean.

One consequence is worth stating because it constrains tuning: a validation block
may only read filings up to its own last year, so every validation origin has
exactly one year of observed follow-up. Model selection therefore uses the
one-year IPCW Brier score. No longer horizon is estimable there without leaking.

---

## The model set, and why each one is in it

The set is designed to fill a 2×2, because a name at the top of a leaderboard
answers nothing:

|  | proportional hazards | non-proportional |
|---|---|---|
| **linear** | CoxPH, CoxNet, Cloglog | — |
| **nonlinear** | BoostedCox, DeepSurv, Cloglog-theory | RSF, Cox-Time, DeepHit, CBNN |

The designed contrasts (`reports/contrasts.csv`):

| Contrast | Pair | Isolates |
|---|---|---|
| A | CoxPH → BoostedCox / DeepSurv | nonlinearity, PH held fixed |
| B | DeepSurv → Cox-Time | dropping PH, network held fixed |
| C | BoostedCox → RSF | dropping PH, trees held fixed |
| D | DeepHit / Cox-Time → CBNN | time as an explicit model input |
| E | CoxPH → CoxNet | regularisation alone, no representation learning |
| F | Cloglog → Cloglog-theory | whether the classical baseline was a straw man |

Two models are not off-the-shelf:

* **`Cloglog`** — the trade literature's own discrete-time model
  (Lawless & Studnicka), with an unrestricted age baseline, **plus a shared gamma
  frailty**. Fitted on one-year outcomes and multiplied out over several years, a
  hazard model without unobserved heterogeneity over-predicts long-run mortality
  badly here: the population hazard falls from 15% in year one to 6% in year two,
  which is mostly the frail dying first. The cloglog link gives the correction in
  closed form, `S(u|x) = (1 + θH(u|x))^(-1/θ)`. On fold 1 this moved the IBS from
  0.154 to 0.124 — from barely better than Kaplan–Meier to level with Cox.
* **`CBNN`** — the Case-Base Neural Network of Islam et al. (2024), implemented
  here because no library ships it. Case-base sampling with the `log(B/b)` offset
  that makes the fitted logit a hazard, and follow-up time as a network input so
  that `x_j × g(t)` terms can be learned without anyone specifying `g`.

**`Cloglog-theory`** exists to satisfy plan section 23.7. Comparing a purely
linear Cox against deep networks and declaring the networks nonlinear is a
straw-man experiment; this variant gets splines on the two variables the trade
literature argues are nonlinear plus the experience × diversification
interactions, and no ML model is ever handed those interactions.

---

## Layout

```
config/          frozen task definition (benchmark, splits, horizons)
features/        registry + matrix builder + per-fold preprocessing
splits/          rolling origin, administrative censoring, spell-level sampling
models/          one file per model, all satisfying predict_survival(Z, grid, age)
evaluation/      IPCW, Brier/IBS, Antolini C, dynamic AUC, calibration, bootstrap
scenarios/       Phase 5 — prospective US-2025 tariff scoring (NOT a leaderboard)
explain/         Phase 18 — permutation importance for a NAMED horizon
runs/<id>/       config snapshot, one JSON per cell, metrics.parquet, predictions
reports/         leaderboard, ablation, contrasts, subgroups, bootstrap, figures
```

## Running it

```bash
PY=/home/minhquang/miniconda3/envs/drug-tox-env/bin/python

$PY benchmark/features/build_matrix.py            # Phase 0, ~1 min
$PY benchmark/splits/rolling_origin.py            # inspect the folds
$PY benchmark/run_benchmark.py --run-id v1 --resume
$PY benchmark/reports/make_reports.py --run-id v1
```

`--resume` skips cells that already have a JSON, so a crash in one model on one
fold costs that cell and nothing else. Restrict a run with
`--models`, `--feature-sets`, `--folds`.

The environment is the existing `drug-tox-env` conda environment (it already had
torch, scikit-learn, scipy and pyarrow); `scikit-survival`, `lifelines`, `pycox`
and `torchtuples` were added to it without changing any of the heavy pins.

---

## What this run can and cannot claim

The caps in `config/benchmark.yaml` are set by the hardware — one laptop with a
6 GB GPU — not by statistics, and they bound the claims:

* **40,000 training origins per fold**, sampled at spell level, against 779k
  available. Every model in a cell is capped identically, so the *comparison*
  holds; the absolute level of every metric does not, and a model whose advantage
  only appears at 500k rows would not show it here.
* **2–3 tuning trials per model per fold**, against the 30–50 the plan asks for,
  and a single seed rather than repeated seeds for the neural models. The budget
  is equal across families, which is what protects the contrast (plan section
  23.8), but no cell should be read as that model's ceiling.
* **Trees are capped harder still** (RSF 20k, BoostedCox 25k) because forest fit
  time grows faster than linearly in rows. This cuts *against* the tree family:
  an RSF that wins under the handicap has won comfortably; one that loses
  narrowly has not been shown to lose.

Raising any of these requires no code change — only the config.

Three further limits are properties of the data, not of the budget:

* **Product-space proximity is adapted and coarse.** `proximity_hs2_lag` is the
  HS2 chapter's share of Vietnam's exports, not a co-export proximity. Labelled
  as adapted in the registry and it should be labelled as adapted in the paper.
* **Two-way trade could not be built.** Nitsch's reciprocal-trade variable needs
  Vietnam's *imports* of the same product from the same partner, which this panel
  does not carry.
* **NTM variables read the collection calendar as much as the policy** before
  roughly 2015. `ntm6_observed` is in the feature set as a measurement flag for
  exactly this reason, and its `*_source_year` twin is banned outright
  (plan section 23.5).
