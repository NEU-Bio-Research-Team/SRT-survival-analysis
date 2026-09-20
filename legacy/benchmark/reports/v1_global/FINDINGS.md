# Benchmark v1 — what the run found

Run `v1`: 11 models × 6 feature sets × 4 rolling-origin folds = **264 cells, no
failures**. Primary metric is the Integrated Brier Score over 1–3 years (lower is
better); every model in a cell saw the identical rows, the identical columns and
the identical tuning budget.

Read this against the caps in `../README.md`. They bound what follows: 40,000
training origins per fold (8,000 for the two tree models), 2–3 tuning trials, one
seed. The comparison is protected because the caps are applied identically; the
absolute level of every number is not.

---

## 1. The headline: no universal ML dominance

Full feature set, averaged over the four folds:

| Model | IBS 1–3y | Antolini C | ECE 3y | Family |
|---|---:|---:|---:|---|
| **RSF** | **0.1122** | 0.811 | **0.0388** | tree, non-PH |
| BoostedCox | 0.1146 | 0.814 | 0.0620 | tree, PH |
| CoxNet | 0.1149 | 0.817 | 0.0512 | linear, PH |
| Cloglog | 0.1153 | **0.819** | 0.0492 | linear, PH |
| Cloglog-theory | 0.1161 | 0.820 | 0.0567 | nonlinear, PH |
| CoxPH | 0.1166 | 0.819 | 0.0586 | linear, PH |
| CBNN | 0.1170 | 0.813 | 0.0642 | deep, non-PH |
| CoxTime | 0.1174 | 0.811 | 0.0678 | deep, non-PH |
| DeepHit | 0.1265 | 0.807 | 0.0824 | deep, non-PH |
| DeepSurv | 0.1299 | 0.809 | 0.1124 | deep, PH |
| Kaplan–Meier | 0.1510 | 0.500 | 0.0489 | null |

Every covariate model beats the null by a wide margin — roughly 0.035 of IBS,
against a spread of 0.018 across the covariate models themselves. **The
information is in the covariates, not in the algorithm.**

RSF wins on average, and the paired spell-block bootstrap says the average is
not noise — but it also says the win is not uniform. At `F0F1F2F3F4`, ΔIBS versus
CoxPH is −0.0033 on average, with RSF significantly BETTER in folds 1, 2 and 4
(−0.0080, −0.0051, −0.0015) and significantly WORSE in fold 3 (+0.0014). Fold 3
is the COVID test block. Three wins and a loss is a weaker claim than a clean
sweep, and it is the correct one: a bootstrap flag of "significant" only says the
difference is distinguishable from zero, not that it favours the flexible model.

The margin is also about 4% of the covariate-model spread, delivered by the model
that was handicapped hardest (8,000 training rows against 40,000). This is plan
hypothesis **H7**, and it is a result rather than a failed experiment: the 2025
Birolo and 2026 Burk benchmarks predict exactly this.

Every deep model is beaten by plain CoxNet.

## 2. Which assumption actually mattered

The contrasts the model set was designed to isolate (negative = the second model
is better):

| Contrast | ΔIBS | Cells improved | Reading |
|---|---:|---:|---|
| A. CoxPH → BoostedCox (nonlinearity, PH fixed) | +0.0001 | 7/24 | nothing |
| A. CoxPH → DeepSurv (nonlinearity, neural) | +0.0029 | 16/24 | worse |
| B. DeepSurv → CoxTime (drop PH, net fixed) | −0.0018 | 9/24 | weak, inconsistent |
| **C. BoostedCox → RSF (drop PH, trees fixed)** | **−0.0021** | **21/24** | **the one consistent gain** |
| D. DeepHit → CBNN (time as input) | −0.0144 | 23/24 | large, but see §4 |
| E. CoxPH → CoxNet (regularisation alone) | +0.0007 | 8/24 | nothing |
| F. Cloglog → Cloglog-theory (strengthened baseline) | +0.0003 | 8/24 | nothing |

**Nonlinearity buys nothing here.** Contrast A is flat in the tree family and
negative in the neural one. Contrast F says the same thing from the other
direction: adding splines and the literature's experience × diversification
interactions to the cloglog does not improve it, so the theory-motivated
nonlinearities that ML might have been "discovering" are not there to discover.

**Relaxing proportional hazards is the only assumption whose relaxation pays**,
and only in the tree family, where it improved 21 of 24 cells.

That reading needs one caveat, because the aggregate table disagrees with it:
averaged over models, the non-PH family is *worse* than the PH family in all six
feature sets (`ph_vs_nonph.csv`, +0.0004 to +0.0028). The two are reconcilable —
the non-PH average is dragged down by DeepHit and CoxTime, whose problem is
calibration rather than proportionality. Contrast C holds the architecture fixed
and is the cleaner instrument; the family average confounds the assumption with
which library implements it.

## 3. More economics did not help

IBS by feature block (mean over folds):

| Model | F0 | +F1 | +F2 | +F3 | +F4 | +F5 |
|---|---:|---:|---:|---:|---:|---:|
| RSF | 0.1207 | 0.1116 | 0.1117 | 0.1122 | **0.1111** | 0.1122 |
| CoxPH | 0.1224 | **0.1126** | 0.1121 | 0.1130 | 0.1144 | 0.1166 |
| BoostedCox | 0.1234 | 0.1128 | **0.1126** | 0.1140 | 0.1143 | 0.1146 |
| Cloglog | 0.1246 | 0.1150 | **0.1146** | 0.1207 | 0.1213 | 0.1153 |
| DeepSurv | 0.1220 | **0.1117** | 0.1117 | 0.1187 | 0.1145 | 0.1299 |

**F1 does all the work.** Relationship scale, momentum, market share and
volatility take every model from ~0.123 to ~0.112. Gravity (F2) adds nothing.
Experience and portfolio structure (F3), trade policy (F4) and complexity/shocks
(F5) make most models *worse* out of sample — for CoxPH the full set is worse
than F0F1 by 0.004, which is the entire size of the best model's advantage.

RSF is the exception: it is the only model that still improves at F4, which is
consistent with a flexible learner being better able to ignore a block that hurts
a linear model. That is also the fold where its bootstrap margin over CoxPH is
largest — though fold 3 is also where it loses to CoxPH, so the F4 gain is not
uniform either.

## 4. Two findings that are about measurement, not economics

**The policy block carries almost no predictive signal.** Permutation importance
for CoxPH at the three-year horizon (`permutation_importance_CoxPH_h3.csv`) puts
destination GDP first (0.038), current trade value second (0.025), then spell age
and market breadth. `tariff_rate` does not appear in the top twenty at all; the
only policy-adjacent entry is `tariff_rate_lag_isna` (0.0022) — the *missingness
flag*, not the tariff.

The winning model agrees, which matters because it could have disagreed: RSF is
free to use the policy block nonlinearly and is the one model F4 still helps.
Its ranking (`permutation_importance_RSF_h3.csv`) is current trade value
(0.0057), the destination's share of Vietnam's exports of the product (0.0028),
lagged value, and spell age — with `tariff_rate_lag_isna` at 0.0008 and no tariff
level anywhere near the top. Both a linear and a fully flexible learner, given
the same columns, decline to use the tariffs.

**So the US-2025 tariff scenario is uninformative, and that is the honest
result.** Scoring the 2024–2025 origins under the year-end (20%), peak (46%) and
day-weighted (11.55%) conventions moves mean three-year survival for US
relationships by 0.00007, 0.00009 and 0.00006 respectively — and in the *wrong*
direction, higher tariffs implying slightly higher survival. That sign is not a
finding about tariffs; it is what a coefficient indistinguishable from zero
produces. The table is written to
`us2025_prospective_scenarios_NOT_A_RESULT.csv` and should not be reported as an
effect. Plan §11.3 anticipated the framing problem; this run adds the reason the
exercise cannot work yet — the panel's tariff variation does not predict survival
strongly enough to extrapolate from.

## 5. Where the models actually differ

By relationship age (`subgroups.csv`, F0F1F2F3F4):

| Model | age 1 | age 2–3 | age 4+ |
|---|---:|---:|---:|
| RSF | **0.2162** | 0.1798 | **0.0670** |
| CBNN | 0.2216 | 0.1786 | 0.0683 |
| DeepSurv | 0.2256 | 0.1805 | 0.0691 |
| CoxPH | 0.2339 | 0.1793 | 0.0673 |
| Cloglog | 0.2486 | 0.1930 | 0.0700 |
| DeepHit | 0.3078 | 0.2030 | 0.0711 |

Mature relationships are easy for everyone (IBS ~0.067, and the spread across
models is 0.004). **All of the separation is in first-year relationships**, where
the spread is 0.09 — twenty times larger. Plan §16.3 asked for this split for a
different reason (that a model might merely be learning the high first-year
hazard); the answer is the mirror image, that first-year relationships are the
only place the model choice matters at all.

The COVID block (fold 3 test, 2020–2021) does not separate the models either:
every model sits between 0.106 and 0.116, and CoxPH is second best. There is no
evidence here that flexible models are more robust under the shock.

---

## Caveats that limit these conclusions

1. **Budget.** 2–3 tuning trials and one seed. Deep models are the most
   budget-sensitive family and they finish last; a larger budget could reorder
   them. It is unlikely to overturn §2 or §3, both of which are about linear
   versus nonlinear structure rather than about tuning.
2. **The tree handicap.** RSF and BoostedCox trained on 8,000 rows against
   40,000 for everyone else, because the boosted Cox loss is quadratic in the
   sample (measured: 12s at 4k rows, 215s at 16k). This cuts *against* the
   winner, so RSF's margin is a lower bound, not an upper one.
3. **Validation is one-year only.** A leak-free validation block has exactly one
   year of observed follow-up, so every model was selected on its one-year Brier
   score and then scored at 1–3 years. A model that is good at three years and
   mediocre at one is systematically disadvantaged by this design.
4. **Adapted features.** `proximity_hs2_lag` is an HS2 share, not a product-space
   proximity, and Nitsch's two-way trade variable could not be built at all. F3
   is therefore a weakened version of the Lawless-Studnicka block, and its poor
   showing in §3 should not be read as a refutation of their finding.
5. **The NTM calendar.** Before roughly 2015 the NTM counts read the collection
   calendar as much as the policy, which is one reason F4 may be adding noise.
