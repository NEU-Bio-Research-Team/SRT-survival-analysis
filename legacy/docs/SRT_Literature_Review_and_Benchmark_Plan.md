# Literature Review and Benchmark Plan
## Survival analysis for Vietnam export-relationship persistence

**Project:** `NEU-Bio-Research-Team/SRT-survival-analysis`  
**Research scope:** Survival of Vietnam's export relationships at importer × product-family level  
**Review updated:** 2026-09-10  
**Purpose:** Synthesize the four seed papers, extend the methodological review to reputable machine-learning survival models, and define a defensible benchmark that compares traditional survival methods and ML under the **same information set**.

---

## 0. Executive summary

The four seed papers play **two different roles** and should not be treated as four equivalent sources of input features.

1. **Nitsch (2007/2009)** and **Lawless & Studnicka (2024)** are primarily **economic / trade-survival papers**. Their key contribution for this project is the construction and economic interpretation of covariates that explain the duration of trade relationships. They also provide traditional survival specifications: stratified Cox proportional hazards in Nitsch and random-effects complementary log-log (cloglog) in Lawless & Studnicka.
2. **Islam et al. (2024)** and **Birolo et al. (2025)** are primarily **survival-method / benchmark papers**. Their covariates are clinical or synthetic and should not be copied into a trade dataset. Their main value is methodological: modeling non-proportional hazards (non-PH), nonlinear/time-varying effects, selecting appropriate metrics, and designing a fair comparison between classical and ML survival methods.

Therefore the benchmark should follow the architecture

\[
\text{trade literature} \rightarrow \text{feature universe}
\]

and

\[
\text{survival-ML literature} \rightarrow \text{model universe + evaluation protocol}.
\]

The central benchmark question should be:

> **Given the same economically motivated, leakage-safe covariates, do nonlinear and/or non-proportional-hazard ML survival models improve out-of-sample discrimination and calibration of Vietnam export-relationship survival relative to traditional hazard models?**

This framing is stronger than a generic “AI vs traditional methods” comparison because it isolates the contribution of the **learning algorithm** from the contribution of the **feature set**.

For the current project, the recommended core benchmark is:

- **Null:** Kaplan–Meier.
- **Traditional / econometric:** CoxPH, CoxNet (Elastic-Net Cox), discrete-time cloglog with duration effects and clustered/frailty structure.
- **Tree / boosting ML:** Random Survival Forest (RSF), gradient-boosted Cox / CoxBoost.
- **Deep survival:** DeepSurv, Cox-Time, DeepHit, Case-Base Neural Network (CBNN).
- **Advanced extension:** Oblique Random Survival Forest (ORSF) and DeepPAMM.

Primary evaluation should emphasize **probability quality**, not only ranking:

- Integrated Brier Score (IBS / ISBS);
- time-dependent concordance appropriate for non-PH models (e.g. Antolini);
- time-dependent AUC with censoring adjustment;
- horizon-specific calibration at 1-, 3-, and 5-year horizons.

The current repository already contains a large panel (`panel_final.csv`, documented as 747,719 episode rows × 158 columns, 147 importers and 228,175 spells in the 25-Aug-2026 handoff). However, the main modeling benchmark should be **frozen before experimentation** because the repository documents different modeling windows in different design snapshots, and because tariff/NTM measurement quality changes sharply near the end of the panel.

---

# 1. Research question and conceptual separation

## 1.1 Prediction and explanation are different tasks

The project should keep two scientific goals separate.

### Econometric / mechanism goal

Estimate interpretable relationships such as

\[
h_{jpt}
=
1-\exp\left[
-\exp\left(
\gamma(d_{jpt})
+\beta^\top X_{jp,t-1}
+u_{jp}
\right)
\right],
\]

where:

- \(j\): importing country;
- \(p\): product family;
- \(t\): calendar year;
- \(d_{jpt}\): duration / spell age;
- \(X_{jp,t-1}\): lagged covariates;
- \(u_{jp}\): unobserved heterogeneity / shared frailty.

This answers **“which factors are associated with relationship failure, and in what direction?”**

### Predictive / ML goal

Estimate the entire conditional survival distribution or risk:

\[
\widehat{S}(u\mid X_t)
=
P(T>u\mid X_t),
\]

or the hazard

\[
\widehat h(u\mid X_t),
\]

and evaluate it on future data.

This answers **“how accurately can we predict which relationship will survive?”**

A model can be excellent for prediction and weak for causal interpretation. The ML leaderboard should therefore not be used as evidence that a variable has a causal policy effect.

---

# 2. Literature review of the four seed papers

## 2.1 Nitsch — *Die Another Day: Duration in German Import Trade*

**Reference**

Volker Nitsch. *Die Another Day: Duration in German Import Trade*. CESifo Working Paper No. 2085 (2007); later published in *Review of World Economics* 145 (2009), 133–154.

- Working paper: https://www.ifo.de/DocDL/cesifo1_wp2085.pdf
- CESifo record: https://www.ifo.de/en/cesifo/publications/2007/working-paper/die-another-day-duration-german-import-trade

### Research objective

Nitsch asks why bilateral product-level import relationships survive for different lengths of time. The empirical unit is approximately

\[
\text{exporting country} \times \text{CN8 product} \times \text{Germany}.
\]

The data cover German imports at highly disaggregated product level over 1995–2005.

The central result is that trade relationships are usually short, while survival is systematically related to:

- exporter characteristics;
- product characteristics;
- transaction scale;
- import-market structure.

### Methodological orientation

This is mainly a **feature/determinants paper**, not a proposal of a new hazard algorithm.

Nitsch first uses descriptive duration / Kaplan–Meier analysis and then estimates a **stratified Cox proportional-hazards model**:

\[
h(t\mid x)=h_0(t)\exp(x^\top\beta).
\]

The baseline hazard \(h_0(t)\) is unspecified. Stratification is used to allow different baseline hazards across broad region and industry groups.

### Covariates proposed by the paper

The covariates can be grouped into four blocks.

#### A. Exporter / gravity variables

- exporter GDP / economic size;
- GDP per capita;
- geographic distance;
- common border;
- common language;
- regional/institutional membership variables;
- exchange-rate movements;
- breadth of the bilateral trade relationship.

Economic interpretation: classic gravity factors affect not only **trade volume** but also **trade persistence**.

#### B. Relationship-scale variables

- initial trade value;
- bilateral unit value.

Large initial transactions survive longer, consistent with search/sunk-cost mechanisms and stronger initial matching.

#### C. Product variables

- elasticity of substitution;
- differentiated-product indicator;
- contract intensity / relationship-specific input intensity.

Low substitution elasticity and differentiated products tend to have lower exit hazards because replacing a supplier is more difficult and relationship-specific investments are more important.

#### D. Market-structure variables

- total import-market size for a product;
- Vietnam/supplier market share in that product market;
- number of competing exporters;
- two-way trade / reciprocal trade value.

Market share is especially important: large suppliers tend to maintain relationships longer.

### Main empirical findings relevant to this project

The strongest transferable results are:

\[
\text{higher initial value}
\Rightarrow
\text{lower failure risk},
\]

\[
\text{higher market share}
\Rightarrow
\text{lower failure risk},
\]

\[
\text{larger / closer destination}
\Rightarrow
\text{longer survival},
\]

\[
\text{lower substitution elasticity}
\Rightarrow
\text{longer survival}.
\]

### What to borrow

**Borrow directly as feature logic:**

- initial trade value;
- lagged trade value;
- market size;
- Vietnam market share;
- unit value;
- GDP/GDPpc;
- distance;
- border/language;
- product differentiation / substitutability if data can be mapped;
- two-way trade if a consistent measure can be constructed.

**Borrow as baseline method:**

- CoxPH / stratified Cox.

### Limitation for the Vietnam project

Nitsch analyzes a **single importer (Germany)** with many suppliers. The current project fixes the exporter (Vietnam) and varies importing countries and products. The direction of the dyad is therefore reversed, but the relationship-level economic mechanisms remain transferable.

---

## 2.2 Lawless & Studnicka — *Old Firms and New Export Flows: Does Experience Increase Survival?*

**Reference**

Martina Lawless and Zuzanna Studnicka. “Old Firms and New Export Flows: Does Experience Increase Survival?” *Open Economies Review* 35 (2024), 215–243.

- DOI: https://doi.org/10.1007/s11079-023-09727-4
- Publisher: https://link.springer.com/article/10.1007/s11079-023-09727-4

### Research objective

This paper asks whether accumulated exporting experience improves survival of **new firm-product-destination export flows**.

Its most important substantive finding is not simply “experience increases survival.” The direct coefficient on experience can initially look adverse because experienced firms are more likely to experiment with marginal products/destinations. Once the model accounts for diversification and proximity to the firm's core competence, the role of experience changes.

This is important for the Vietnam project because it motivates **interaction-aware feature engineering** rather than treating experience as an isolated linear variable.

### Data and unit of analysis

Irish firm-level customs/export data, with unit

\[
\text{firm} \times \text{product} \times \text{destination}.
\]

The long pre-sample history is used to construct genuine **prior exporting experience** before new flows are launched.

### Hazard model

The main model is a **random-effects complementary log-log model** for discrete yearly intervals:

\[
h_{ik}
=
F\left(
x_{ik}^\top\beta
+z_i^\top\delta
+\gamma_k
\right),
\]

where \(F(\cdot)\) is the cloglog link.

- \(x_{ik}\): time-varying characteristics;
- \(z_i\): time-invariant / launch-time characteristics;
- \(\gamma_k\): duration/interval effects.

The paper uses HS6 product-level random effects and reports robustness to exponential, Weibull and Gompertz models.

This is highly aligned with an annual person-period export-survival panel.

### Original firm-level features

#### Time-varying

- employment / firm size;
- productivity;
- total firm exports.

#### Measured at launch / approximately time-invariant for the new flow

- prior export experience;
- number of products already exported;
- number of destinations already served;
- initial value of the new flow;
- proximity of the new product to the firm’s core product;
- ownership.

#### Destination controls

- distance;
- GDP;
- GDP per capita;
- rule of law;
- EU indicator;
- year/destination controls.

### What can be transferred to a country-product project?

The **firm-specific values cannot be copied literally**, because the SRT dataset has no firm dimension.

However, their economic concepts can be adapted.

| Lawless & Studnicka concept | Country-product analogue for Vietnam |
|---|---|
| Years the firm has exported before launch | Years Vietnam has exported to destination \(j\) before launch |
| Firm product experience | Prior Vietnam experience exporting product \(p\) to other markets |
| Number of firm products | Number of active Vietnam products in destination \(j\) |
| Number of firm destinations | Number of active destinations for Vietnam product \(p\) |
| Initial product-destination value | Initial value of the Vietnam–destination–product spell |
| Proximity to firm core | Product-space proximity to Vietnam's core export basket |
| Total firm exports | Total Vietnam exports to destination / total exports of product \(p\) |

These are **adapted features**, not variables directly estimated by the original paper. They should be labeled as such in the final manuscript.

### Main implication for benchmark design

Do not benchmark only raw “experience.” Benchmark an **experience + diversification + interaction** block.

For example:

\[
Experience^{dest}_{j,t_0}
\times
NProducts_{j,t_0}
\]

and

\[
Experience^{prod}_{p,t_0}
\times
Proximity_{p,t_0}.
\]

This provides a theory-motivated test of nonlinear effects that ML methods may learn automatically.

---

## 2.3 Islam et al. — Case-Base Neural Network (CBNN)

**Reference**

Jesse Islam, Maxime Turgeon, Robert Sladek, Sahir Bhatnagar. “Case-Base Neural Network: Survival analysis with time-varying, higher-order interactions.” *Machine Learning with Applications* 16 (2024), 100535.

- DOI: https://doi.org/10.1016/j.mlwa.2024.100535

### Research objective

This paper is fundamentally **method-centric**.

It asks whether a neural survival model can flexibly estimate:

- complex baseline hazards;
- time-varying covariate effects;
- higher-order interactions;

without requiring the analyst to manually specify the interaction with time.

### Core idea

The paper combines **case-base sampling** with a feed-forward neural network. Follow-up time is included directly as an input feature.

After case-base sampling, the model estimates:

\[
P(Y=1\mid X,T)
=
\sigma
\left(
f_\theta(X,T)
+
\log\frac{B}{b}
\right),
\]

where the offset corrects the bias introduced by the sampling mechanism.

The model output can be transformed into a full hazard function:

\[
\log h(t\mid X)\approx f_\theta(X,t).
\]

Because \(t\) is part of the network input, the network can learn covariate-time interactions of the form

\[
x_j\times g(t)
\]

without pre-specifying them.

### Benchmark in the paper

The authors compare CBNN against:

- Kaplan–Meier null model;
- Cox proportional hazards;
- case-base logistic regression (CBLR);
- DeepSurv;
- DeepHit.

They use simulation with a deliberately complex baseline hazard and time-varying interactions, followed by multiple real clinical case studies.

### Why it matters for this project

Trade-survival relationships are plausible candidates for **non-PH behavior**:

- the effect of initial scale may be strongest in early years;
- tariff shocks may matter differently for young vs mature relationships;
- volatility may be dangerous early but less informative after long persistence;
- policy effects may vary over time.

CBNN provides a direct model class for these patterns.

### What not to borrow

The clinical covariates in the paper are not relevant trade features.

Thus:

> **Use Islam et al. to justify CBNN, time-as-input, non-PH/time-varying interactions, and survival evaluation—not to choose economic input variables.**

---

## 2.4 Birolo et al. — *Beyond Cox models*

**Reference**

Giovanni Birolo, Ivan Rossi, Flavio Sartori, Cesare Rollo, Piero Fariselli, Tiziana Sanavia. “Beyond Cox models: Assessing the performance of machine-learning methods in non-proportional hazards and non-linear survival analysis.” *Computers in Biology and Medicine* 198 (2025), 111176.

- DOI: https://doi.org/10.1016/j.compbiomed.2025.111176

### Research objective

This is a **benchmark/method-selection paper**.

The authors explicitly construct synthetic datasets where:

1. linearity and PH hold;
2. PH holds but the feature-risk function is nonlinear;
3. PH is violated.

The goal is to identify the conditions under which ML/deep survival methods provide real value beyond Cox regression.

### Compared models

The benchmark includes:

- CoxPH;
- CoxNet;
- Gradient Boosting Survival Analysis;
- Random Survival Forest;
- FastCPH;
- DeepHit;
- Deep Survival Machines;
- SurvTRACE.

This creates a useful conceptual 2D grid:

| Model behavior | Linear/nonlinear | PH/non-PH |
|---|---:|---:|
| CoxPH / CoxNet | linear | PH |
| Cox-loss boosting | nonlinear | PH |
| RSF | nonlinear | non-PH |
| DeepHit | nonlinear | non-PH |
| DSM | nonlinear | non-PH |
| SurvTRACE | nonlinear | non-PH |

### Critical metric lesson

The paper emphasizes that **Harrell's C-index is not an appropriate sole metric for non-PH models**, because a non-PH model can change the risk ordering of two observations over time.

If

\[
Risk_i(t_1)>Risk_j(t_1)
\]

but

\[
Risk_i(t_2)<Risk_j(t_2),
\]

a single static ranking is insufficient.

The authors therefore emphasize:

- Antolini's time-dependent concordance;
- Brier score for probability calibration;
- time-dependent AUROC.

### Main conclusion

There is no universal “ML beats Cox” result.

When Cox assumptions are close to correct, Cox can be competitive or best. Flexible ML models become more useful when:

- sufficient data are available;
- nonlinearity is material;
- PH is meaningfully violated.

This is exactly the hypothesis that the SRT benchmark should test.

---

# 3. Cross-paper synthesis

## 3.1 Feature-centric versus model-centric papers

| Paper | Primary contribution | Use for features | Use for model | Use for evaluation |
|---|---|---:|---:|---:|
| Nitsch | Economic determinants of trade duration | **High** | Medium | Low |
| Lawless & Studnicka | Experience/diversification determinants | **High** | **High** (cloglog) | Low |
| Islam et al. | Flexible neural hazard model | Low | **Very high** | High |
| Birolo et al. | Neutral comparison under PH/non-PH/nonlinearity | Low | **Very high** | **Very high** |

The input feature design should therefore be anchored primarily in the two **trade papers**, plus project-specific policy variables.

---

# 4. Additional ML survival literature

The survival-ML literature is much broader than international trade. Most method papers are demonstrated on biomedical datasets, but the algorithms are domain-agnostic: their statistical object is still a censored time-to-event distribution.

A recent systematic review by Wiegrebe et al. (2024) identified dozens of deep survival methods and emphasized that they differ in survival representation, censoring mechanism, architecture, and supported outcome type.

**Review:**  
Simon Wiegrebe, Philipp Kopper, Raphael Sonabend, Bernd Bischl, Andreas Bender. “Deep learning for survival analysis: a review.” *Artificial Intelligence Review* 57, 65 (2024).  
https://doi.org/10.1007/s10462-023-10681-3

The following models are the most relevant to this project.

---

## 4.1 CoxNet — Elastic-Net penalized Cox

CoxNet retains the Cox proportional-hazards structure but applies L1/L2 regularization.

\[
h(t\mid x)
=
h_0(t)
\exp(x^\top\beta),
\]

with an Elastic-Net penalty on \(\beta\).

### Why include it

The current project has many candidate covariates. Comparing ordinary Cox with CoxNet answers whether any ML gain is merely due to **regularization/feature selection** rather than nonlinear representation learning.

### Position in benchmark

- nonlinear: no;
- PH: yes;
- highly interpretable: yes;
- core benchmark: **yes**.

---

## 4.2 Random Survival Forests (RSF)

**Reference**

Hemant Ishwaran, Udaya Kogalur, Eugene Blackstone, Michael Lauer. “Random survival forests.” *Annals of Applied Statistics* 2(3), 841–860 (2008).  
DOI: https://doi.org/10.1214/08-AOAS169

RSF extends random forests to censored time-to-event data using survival-specific splitting and ensemble cumulative-hazard/survival estimates.

### Strengths

- naturally nonlinear;
- captures interactions;
- no PH assumption;
- strong tabular-data baseline;
- relatively easy to train;
- supports permutation-based importance.

### Weaknesses

- survival probabilities can require calibration;
- interpretation is weaker than regression;
- high-cardinality categorical structures require careful encoding.

### Relevance

**Very high.** The SRT panel is large, tabular and interaction-rich.

---

## 4.3 Oblique Random Survival Forests (ORSF)

**Reference**

Byron Jaeger et al. “Oblique Random Survival Forests.” *Annals of Applied Statistics* 13(3), 1847–1883 (2019).  
DOI: https://doi.org/10.1214/19-AOAS1261

ORSF uses linear combinations of features inside survival-tree splits rather than axis-aligned one-feature splits.

### Why it is interesting

A large neutral survival benchmark published in *Bioinformatics* in 2026 found oblique survival forests among the competitive ML methods, while also concluding that no model universally dominates Cox on low-dimensional right-censored data.

### Position

- advanced tree comparator;
- good extension after standard RSF;
- recommended as **Phase-3 extension**, not required for the first runnable benchmark.

---

## 4.4 Survival gradient boosting / CoxBoost

Likelihood-based or gradient boosting adapts boosting to censored survival outcomes.

**Representative reference**

Harald Binder & Martin Schumacher. “Allowing for mandatory covariates in boosting estimation of sparse high-dimensional survival models.” *BMC Bioinformatics* 9, 14 (2008).

For a Cox-loss boosting model:

\[
risk(x)=f(x),
\qquad
h(t\mid x)=h_0(t)e^{f(x)}.
\]

This allows a nonlinear risk function while retaining a proportional-hazards structure.

### Why it is important for the benchmark

It separates two effects:

- **nonlinearity**;
- **non-PH behavior**.

If gradient boosting beats Cox but a non-PH model does not add much beyond boosting, then the key issue is nonlinear covariate structure—not time-varying risk ordering.

### Position

- nonlinear: yes;
- PH under Cox loss: yes;
- core benchmark: **yes**.

---

## 4.5 DeepSurv

**Reference**

Jared Katzman et al. “DeepSurv: personalized treatment recommender system using a Cox proportional hazards deep neural network.” *BMC Medical Research Methodology* 18, 24 (2018).  
DOI: https://doi.org/10.1186/s12874-018-0482-1

DeepSurv replaces the linear Cox predictor \(x^\top\beta\) with a neural network:

\[
h(t\mid x)
=
h_0(t)\exp(f_\theta(x)).
\]

### What it isolates

DeepSurv is **nonlinear but still PH**.

This is scientifically useful: it tests whether a neural representation alone is sufficient without relaxing proportional hazards.

### Position

- nonlinear: yes;
- PH: yes;
- core deep comparator: **yes**.

---

## 4.6 Cox-Time

**Reference**

Håvard Kvamme, Ørnulf Borgan, Ida Scheel. “Time-to-Event Prediction with Neural Networks and Cox Regression.” *Journal of Machine Learning Research* 20(129), 1–30 (2019).  
https://www.jmlr.org/papers/v20/18-424.html

Kvamme et al. extend Cox-style neural survival modeling and develop scalable losses that support both proportional and non-proportional effects.

Cox-Time can model risk as

\[
f_\theta(x,t),
\]

rather than only

\[
f_\theta(x).
\]

### Relevance

Very high because it creates a clean comparison:

\[
\text{DeepSurv: nonlinear + PH}
\]

versus

\[
\text{Cox-Time: nonlinear + non-PH}.
\]

If Cox-Time materially outperforms DeepSurv, this is evidence that the value comes from relaxing PH, not simply using a neural network.

---

## 4.7 Nnet-survival / LogisticHazard

**Reference**

Martin Gensheimer & Balasubramanian Narasimhan. “A scalable discrete-time survival model for neural networks.” *PeerJ* (2019).  
https://pmc.ncbi.nlm.nih.gov/articles/PMC6348952/

This class discretizes follow-up time and predicts conditional survival/hazard probabilities across intervals.

For annual trade data, this is conceptually natural:

\[
P(T=t \mid T\ge t, x).
\]

### Why relevant

The SRT outcome is already represented on annual person-period intervals. A discrete neural hazard model avoids pretending the observed resolution is continuous.

### Position

Useful extension, but DeepHit/CBNN/Cox-Time provide broader contrasts, so it can be omitted from V1 if computational scope must be limited.

---

## 4.8 DeepHit

**Reference**

Changhee Lee, William Zame, Jinsung Yoon, Mihaela van der Schaar. “DeepHit: A Deep Learning Approach to Survival Analysis With Competing Risks.” *AAAI* 2018.  
DOI: https://doi.org/10.1609/aaai.v32i1.11842

DeepHit directly learns a discrete distribution of event times and does not require a PH assumption.

### Strengths

- flexible nonlinear mapping;
- non-PH;
- direct time-distribution prediction;
- naturally extends to competing risks.

### Weaknesses

- discretization/horizon choice matters;
- more hyperparameters and training instability;
- calibration must be explicitly checked.

### Relevance

**High**, especially if the future project distinguishes types of relationship termination or reallocation.

---

## 4.9 Deep Survival Machines (DSM)

**Reference**

Chirag Nagpal, Xinyu Li, Artur Dubrawski. “Deep Survival Machines: Fully Parametric Survival Regression and Representation Learning for Censored Data With Competing Risks.” *IEEE Journal of Biomedical and Health Informatics* 25(8), 3163–3175 (2021).  
DOI: https://doi.org/10.1109/JBHI.2021.3052441

DSM learns a mixture of parametric primitive distributions such as Weibull or log-normal, with neural networks controlling mixture weights/parameters.

### Strengths

- full survival distribution;
- nonlinear representation;
- no Cox PH requirement;
- supports competing risks.

### Weakness

The mixture-family choice still imposes a parametric structure. The CBNN seed paper also reported convergence difficulties for DSM in its complex simulation setting.

### Position

Good secondary comparator, but not necessary in the first benchmark.

---

## 4.10 DeepPAMM

**Reference**

Philipp Kopper, Simon Wiegrebe, Bernd Bischl, Andreas Bender, David Rügamer. “DeepPAMM: Deep Piecewise Exponential Additive Mixed Models for Complex Hazard Structures in Survival Analysis.” PAKDD 2022.  
DOI: https://doi.org/10.1007/978-3-031-05936-0_20

DeepPAMM combines piecewise-exponential additive mixed models with neural representation learning.

### Why it is particularly relevant to SRT

DeepPAMM can accommodate:

- time-varying effects;
- time-varying features;
- mixed/random effects;
- structured interpretable components;
- an unstructured neural component.

This resembles the structure the SRT econometric model already wants:

\[
\text{duration baseline}
+
\text{structured economic terms}
+
\text{unobserved heterogeneity}
+
\text{nonlinear interactions}.
\]

### Position

**Best advanced-method extension** after the core benchmark because it creates a direct bridge between econometric hazard modeling and deep learning.

---

## 4.11 SurvTRACE

**Reference**

Zifeng Wang & Jimeng Sun. “SurvTRACE: Transformers for Survival Analysis with Competing Events.” ACM BCB 2022.  
DOI: https://doi.org/10.1145/3535508.3545521

SurvTRACE uses transformer-style representations for survival and competing-event prediction.

### Relevance

It is methodologically strong, and Birolo et al. found it competitive in non-PH settings. However, the current SRT task is:

- single-event;
- structured tabular;
- not extremely high dimensional.

Therefore a Transformer is **not a first-priority comparator**. Add it only after simpler models are stable.

---

## 4.12 Case-Base Neural Network (CBNN)

CBNN is already one of the four seed papers and should be included in the advanced core because:

- it estimates a full hazard;
- explicitly includes time;
- can learn time-varying higher-order interactions;
- it provides the most direct test of whether tariff/market effects vary with relationship age.

---

# 5. Evidence from recent neutral benchmarks

A particularly important recent result is:

**Lukas Burk et al. “A large-scale neutral comparison study of survival models on low-dimensional data.” *Bioinformatics* 42(5), btag186 (2026).**  
DOI: https://doi.org/10.1093/bioinformatics/btag186

The study benchmarks 21 models on 34 datasets and evaluates both ranking and full-distribution performance.

Its main warning is highly relevant:

> Flexible ML models may be strong on particular datasets, but there is no empirical basis for assuming beforehand that they will universally beat Cox.

This directly implies that the SRT paper should **not** frame the experiment as “prove AI is better.”

The correct hypothesis is conditional:

\[
H:
\text{ML gains should increase when the real trade-survival process is nonlinear and/or non-PH.}
\]

The benchmark should therefore diagnose:

- PH violation;
- nonlinearity;
- calibration;
- performance by spell age;
- performance during policy/macro shocks.

---

# 6. Current repository implications

The current branch documents:

- exporter fixed to Vietnam;
- 147 importers;
- product-family/HS6-level relationships;
- hundreds of thousands of episode-year observations;
- explicit `t_start`, `t_stop`, `event` style survival structure;
- trade-performance variables such as RCA, market share, growth, HHI;
- gravity and macro covariates;
- tariff / FTA variables;
- NTM variables;
- trade-remedy variables;
- global-shock variables;
- product complexity variables;
- US 2025 reciprocal-tariff variables;
- CBAM scope variables.

The data handoff records `panel_final.csv` as **747,719 episodes × 158 columns**, 147 importers, and 228,175 spells.

Two details directly affect benchmark validity:

1. **`event=1` in year \(Y\) means the relationship is last alive in \(Y\) and dies in \(Y+1\).** Feature and target timing must respect this convention.
2. Some late-period policy variables are not measured contemporaneously. TRAINS tariff schedules for 2024–2025 are unavailable and are carried from 2023; NTM coverage is based on irregular collection years.

Therefore the benchmark needs a formal **feature-timing registry** before any model is fitted.

---

# 7. Proposed feature architecture

## 7.1 Principle: benchmark models under the same information set

The primary leaderboard must enforce

\[
M_1(X_k), M_2(X_k),\ldots,M_m(X_k)
\]

for the **same \(X_k\)**.

Do not compare:

- Cox with 10 selected variables;
- ML with all 158 columns.

That confounds feature engineering with modeling capacity.

---

## 7.2 Feature registry

Create a registry with at least:

```yaml
feature:
  economic_concept:
  source_literature:
  source_column:
  construction:
  observation_level:
  timing:
  transform:
  missingness_rule:
  source_year_rule:
  expected_economic_direction:
  allowed_in_primary_benchmark:
  leakage_risk:
```

Example:

```yaml
initial_trade_value:
  economic_concept: relationship_scale
  source_literature:
    - Nitsch_2007
    - Lawless_Studnicka_2024
  construction: value in first active year of spell
  observation_level: spell
  timing: fixed_at_spell_start
  transform: log1p
  expected_economic_direction: lower_hazard
  allowed_in_primary_benchmark: true
  leakage_risk: low
```

---

# 8. Proposed feature sets

The recommended benchmark is an **incremental feature ablation**.

## F0 — Duration-only null structure

Use only:

- spell age / duration dummies;
- calendar-time controls where appropriate.

Purpose:

\[
\text{How much predictive power comes from duration dependence alone?}
\]

---

## F1 — Core relationship features

Anchored mainly in Nitsch and Lawless & Studnicka.

Recommended:

- `log(initial_trade_value)`;
- lagged `log(import_value_usd)`;
- Vietnam market share in importer × product;
- importer total market size for the product;
- RCA;
- lagged export growth;
- world/product demand growth;
- 3-year trade-value volatility;
- unit value, where reliable.

Expected important relationships:

\[
InitialValue\uparrow \Rightarrow Hazard\downarrow
\]

\[
MarketShare\uparrow \Rightarrow Hazard\downarrow
\]

\[
Volatility\uparrow \Rightarrow Hazard\uparrow.
\]

---

## F2 — Gravity and macro environment

Recommended:

- log importer GDP;
- log GDP per capita;
- log population;
- log distance;
- common border;
- common official language;
- exchange-rate change;
- inflation if economically justified;
- importer logistics performance as a robustness feature rather than mandatory core.

These variables capture destination size, trade cost, purchasing power, and macro instability.

---

## F3 — Experience, diversification and portfolio structure

This is the **Lawless-inspired adapted block**.

Engineer:

### Destination experience

\[
ExpDest_{j,t}
=
\#\{\tau<t: \text{Vietnam exported any product to }j\}.
\]

### Product experience

\[
ExpProd_{p,t}
=
\#\{\tau<t: \text{Vietnam exported }p\text{ to any market}\}.
\]

### Destination diversification

\[
NProducts_{j,t}
=
\#\{p: value_{jpt} > threshold\}.
\]

### Product market breadth

\[
NMarkets_{p,t}
=
\#\{j: value_{jpt} > threshold\}.
\]

### Portfolio concentration

- `hhi_market`;
- `hhi_product`;
- `partner_share_pct`;
- `product_share_pct`.

### Product proximity to Vietnam's core basket

Construct from product-space co-export proximity if feasible.

### Two-way trade

Adapt Nitsch:

\[
TwoWay_{jpt}
=
\log(1 + \text{imports of }p\text{ from }j\text{ into Vietnam}),
\]

or a symmetric intra-product trade ratio.

### Theory-motivated interactions for the traditional model

\[
Experience\times NProducts,
\]

\[
Experience\times NMarkets,
\]

\[
Experience\times ProductProximity.
\]

For ML, do **not** force these interactions; allow the algorithm to learn them, then compare whether learned dependence is consistent with the theory.

---

## F4 — Trade policy and barriers

Recommended variables:

- applied tariff / `tariff_rate`;
- FTA/RTA in-force indicator;
- preference margin where the rate is genuinely observed;
- tariff shock / tariff change;
- NTM at HS6 × year;
- NTM ad-valorem-equivalent as a separate between-market feature;
- anti-dumping / countervailing / safeguard indicators;
- CBAM scope for EU relationships.

### Important measurement restrictions

#### Tariff 2024–2025

Do not treat carried-forward 2023 tariffs as observed 2024–2025 tariffs.

Use:

- `tariff_source_year`;
- explicit contemporaneous-measurement flag;
- sensitivity specification excluding non-contemporaneous tariff observations.

#### NTM

Do not mix the old sector-level cross-sectional NTM variables with the HS6 × collection-year family in the same specification.

Primary options:

1. restrict policy benchmark to years where `ntm6_observed=1`; or
2. use an in-force construction but run strict source-year sensitivity checks.

#### NTM ad-valorem equivalent

It is effectively a time-invariant importer characteristic in the current construction. It should not be interpreted as a within-importer policy shock.

---

## F5 — Complexity, resilience and common shocks

Project-specific extension:

- product complexity index (PCI);
- importer ECI if available;
- global economic-policy uncertainty;
- commodity-price shocks;
- logistics / environmental composite variables if their construction is frozen.

These variables are not directly motivated by the four seed papers, so they should enter **after F1–F4** rather than in the literature-core model.

---

# 9. Features that should not enter the primary predictor set

Exclude from model input:

- IDs: `spell_id`, raw row IDs;
- outcome-derived fields unavailable at prediction time;
- future values;
- `t_stop` if it reveals realized spell endpoint;
- current-year trade value when the target definition makes it simultaneously determined with failure;
- `*_source_year` as a raw numeric economic predictor unless the goal is explicitly to model measurement process.

Use source-year fields for:

- filtering;
- missingness/measurement indicators;
- robustness analysis.

---

# 10. Recommended benchmark models

## 10.1 Core benchmark — must run

| ID | Model | Nonlinear | Non-PH | Main role |
|---|---|---:|---:|---|
| B0 | Kaplan–Meier | No covariates | — | Null reference |
| B1 | CoxPH | No | No | Classical baseline |
| B2 | CoxNet | No | No | Regularized classical baseline |
| B3 | Discrete-time cloglog + duration effects | Linear unless expanded | Approximately PH under basic form | Trade-literature/econometric baseline |
| B4 | RSF | Yes | Yes | Tree non-PH |
| B5 | Gradient Boosted Cox / CoxBoost | Yes | No | Nonlinear-PH comparator |
| B6 | DeepSurv | Yes | No | Neural nonlinear-PH |
| B7 | Cox-Time | Yes | Yes | Neural non-PH |
| B8 | DeepHit (single event) | Yes | Yes | Discrete neural survival |
| B9 | CBNN | Yes | Yes | Time-varying full-hazard NN |

This model set allows controlled scientific contrasts.

### Contrast A — linearity

\[
CoxPH \quad vs \quad BoostedCox/DeepSurv
\]

asks whether **nonlinearity** matters while keeping PH.

### Contrast B — proportional hazards

\[
DeepSurv \quad vs \quad CoxTime
\]

asks whether relaxing PH matters within neural models.

### Contrast C — tree PH structure

\[
BoostedCox \quad vs \quad RSF
\]

separates nonlinear-PH from nonlinear-non-PH tree models.

### Contrast D — explicit time modeling

\[
DeepHit / CoxTime \quad vs \quad CBNN
\]

tests whether direct continuous/time-input hazard modeling adds value.

---

## 10.2 Advanced extension

After the core pipeline is stable:

- ORSF;
- DeepPAMM;
- DSM;
- SurvTRACE.

Priority:

\[
DeepPAMM > ORSF > DSM > SurvTRACE
\]

for this dataset.

Reason: DeepPAMM has the closest structural match to the project's need for time-varying effects + mixed effects + interpretability.

---

# 11. Benchmark design

## 11.1 Freeze the prediction task first

Define explicitly:

- prediction origin \(t\);
- information available at \(t\);
- event horizon;
- relation between row-year and death-year;
- treatment of multiple spells;
- gap rule.

A recommended first target is **one-year relationship failure risk**:

\[
P(\text{relationship fails before }t+1 \mid \mathcal F_t).
\]

Then derive multi-year survival from the estimated hazard sequence.

This matches annual trade data and minimizes ambiguous interpolation.

---

## 11.2 Main historical benchmark window

The repository includes data through 2025, but late-period policy measurement is incomplete.

Recommended design:

### Benchmark H — Historical predictive benchmark

Use years where the feature/target pair is fully observable and policy covariates satisfy the frozen source-year rules.

A conservative main window should end no later than **2023 for contemporaneously measured standard tariff features**.

### Benchmark P — Policy-quality subset

Run F4 models on a stricter subset where policy variables are genuinely observed rather than borrowed.

### Prospective 2024–2025 scoring

Use 2024–2025 for scenario scoring / prospective risk estimates when covariates are available, but do not merge this with the clean historical leaderboard if the information quality differs.

---

## 11.3 US 2025 tariff must not be treated as a completed-effect benchmark

The repository's event convention implies that a relationship alive during 2025 can only reveal its post-2025 survival outcome in later data.

Therefore:

> **The 2025 US reciprocal tariff is currently a stress/counterfactual input, not an observed causal-training label for its eventual survival effect.**

Use it to generate:

\[
\widehat S_{jp,2026}^{shock}
\]

under alternative tariff conventions/scenarios.

Do not claim the present panel empirically estimates the realized 2025-tariff survival effect without subsequent outcome data.

---

# 12. Temporal validation

## 12.1 Never random-split episode rows

Rows from the same relationship and adjacent years are serially dependent.

Random splitting can place:

\[
(j,p,t)
\]

in training and

\[
(j,p,t+1)
\]

in testing, producing an unrealistically easy problem.

---

## 12.2 Rolling-origin evaluation

Recommended structure:

- fit only on past data;
- tune on a later validation block;
- test on a still later block;
- repeat across several origins.

Illustrative folds:

| Fold | Train | Validation | Test |
|---|---|---|---|
| 1 | 2003–2013 | 2014–2015 | 2016–2017 |
| 2 | 2003–2015 | 2016–2017 | 2018–2019 |
| 3 | 2003–2017 | 2018–2019 | 2020–2021 |
| 4 | 2003–2019 | 2020–2021 | 2022–2023 |

The exact fold boundaries should be adjusted after the target-timing convention is frozen.

This design intentionally tests performance during very different regimes, including COVID-era disruptions.

---

# 13. Preprocessing fairness rules

For every model and fold:

1. Fit scaler/encoder/imputer **only on the training period**.
2. Use the same feature definition across all models.
3. Use the same censoring definition.
4. Use the same prediction horizons.
5. Use the same test rows.
6. Tune every tunable model using a predefined search budget.
7. Do not manually give ML additional future-derived features.
8. Save all hyperparameters and random seeds.

Suggested tuning budget:

- 30–50 random/Bayesian trials per model per fold for V1;
- early stopping for neural methods;
- repeated seeds for deep models.

Report both:

- metric mean;
- uncertainty across folds/seeds.

---

# 14. Evaluation metrics

## 14.1 Primary metric: integrated probability accuracy

Because Stage 2 will use actual survival probabilities, not only rankings, the primary metric should be:

\[
\boxed{\text{Integrated Brier Score}}
\]

over a predefined evaluation time interval.

Lower is better.

---

## 14.2 Discrimination

Report:

- Antolini time-dependent concordance for models whose risk ordering can vary over time;
- Uno/IPCW concordance as a censoring-robust secondary measure where implementation permits;
- horizon-specific time-dependent AUROC.

Avoid making Harrell C-index the sole headline metric when comparing PH and non-PH models.

---

## 14.3 Calibration

At minimum:

- 1-year;
- 3-year;
- 5-year survival calibration.

For each horizon, compare predicted and empirical survival probabilities by decile/bin.

The practical question is:

\[
P(T>t \mid \widehat S(t)=0.8)\approx0.8?
\]

This matters directly for the Stage-2 calculation

\[
Value\times\widehat S.
\]

---

## 14.4 Optional full-distribution score

Add integrated survival log-likelihood or another likelihood-based score where all compared models expose a compatible survival distribution.

This aligns with recent neutral benchmark practice and prevents relying on one scoring rule.

---

# 15. Feature × model benchmark matrix

The central experiment should be:

| Feature set | CoxPH | CoxNet | Cloglog | RSF | Boosted Cox | DeepSurv | Cox-Time | DeepHit | CBNN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F0 Duration | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| F0+F1 Relationship | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| +F2 Gravity/Macro | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| +F3 Experience/Portfolio | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| +F4 Policy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| +F5 Resilience | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

This directly decomposes:

\[
\Delta_{\text{feature}}
\]

from

\[
\Delta_{\text{algorithm}}.
\]

---

# 16. Additional ablation experiments

## 16.1 Time-varying interaction test

Explicitly compare traditional-model variants:

### Linear cloglog

\[
\eta=X^\top\beta+\gamma(d).
\]

### Theory-enhanced cloglog

\[
\eta
=
X^\top\beta
+
f_1(\log Value)
+
f_2(MarketShare)
+
Experience\times Diversification
+
\gamma(d).
\]

Then compare against flexible ML.

This avoids creating a weak straw-man classical baseline.

---

## 16.2 PH versus non-PH diagnostic experiment

Group models as:

### PH family

- CoxPH;
- CoxNet;
- boosted Cox;
- DeepSurv.

### non-PH family

- RSF;
- Cox-Time;
- DeepHit;
- CBNN.

If non-PH models show gains specifically in periods/segments with crossing survival patterns, the paper obtains a stronger mechanism-level interpretation.

---

## 16.3 Spell-age performance

Because the repository reports that roughly half of spells are one-year spells under the current threshold, report metrics separately for:

- age 1;
- age 2–3;
- age 4+.

A model that appears strong overall may simply learn the very high baseline hazard of first-year relationships.

---

## 16.4 Shock-period performance

Report separately:

- pre-GFC / normal years where applicable;
- GFC;
- COVID;
- post-COVID;
- policy-shock scenarios.

This evaluates robustness under distribution shift.

---

# 17. Statistical uncertainty

For each test fold:

- compute paired model metric differences on the same test data;
- bootstrap at a relationship/spell level rather than individual row level;
- where common importer/product shocks dominate, consider hierarchical/block bootstrap.

Report:

\[
\Delta IBS = IBS_A-IBS_B
\]

with confidence intervals, not only ranks.

Do not describe a 0.002 metric difference as a meaningful win without uncertainty analysis.

---

# 18. Explainability

Explainability should be secondary to predictive validity but can connect ML back to economic theory.

Recommended:

### Tree models

- permutation importance;
- survival-aware partial dependence;
- SHAP only if the chosen implementation has a clearly defined prediction target/horizon.

### Neural models

- permutation importance at fixed horizons;
- integrated gradients;
- local sensitivity of \(\widehat S(t)\) to covariates.

Always define the explained quantity, for example:

\[
\widehat P(T>3\mid X)
\]

rather than reporting generic “SHAP risk” without a time horizon.

---

# 19. Proposed implementation phases

## Phase 0 — Freeze data semantics

Deliverables:

- target specification;
- spell/gap definition;
- benchmark time window;
- `feature_registry.yaml`;
- source-year policy.

No model training before this is frozen.

---

## Phase 1 — Classical baseline

Implement:

- KM;
- CoxPH;
- CoxNet;
- cloglog.

Run F0–F3.

Goal: create a stable benchmark harness and validate data semantics.

---

## Phase 2 — Standard ML

Implement:

- RSF;
- gradient-boosted Cox / CoxBoost.

Run F0–F4.

Goal: test nonlinear tabular effects before deep learning.

---

## Phase 3 — Deep survival

Implement:

- DeepSurv;
- Cox-Time;
- DeepHit;
- CBNN.

Only after the classical/tree pipeline is fully reproducible.

---

## Phase 4 — Advanced method extension

Prioritize:

1. DeepPAMM;
2. ORSF;
3. DSM;
4. SurvTRACE.

---

## Phase 5 — Stress / policy scenarios

Generate forward risk estimates under:

- tariff shocks;
- alternative US-2025 tariff conventions;
- CBAM scope;
- macro uncertainty shocks.

Keep this separate from the historical observed-outcome leaderboard.

---

# 20. Recommended repository structure

```text
benchmark/
├── README.md
├── config/
│   ├── benchmark.yaml
│   ├── horizons.yaml
│   └── splits.yaml
│
├── features/
│   ├── feature_registry.yaml
│   ├── build_f0_duration.py
│   ├── build_f1_relationship.py
│   ├── build_f2_gravity.py
│   ├── build_f3_experience.py
│   ├── build_f4_policy.py
│   └── build_f5_resilience.py
│
├── models/
│   ├── km.py
│   ├── cox.py
│   ├── coxnet.py
│   ├── cloglog.py
│   ├── rsf.py
│   ├── boosted_cox.py
│   ├── deepsurv.py
│   ├── coxtime.py
│   ├── deephit.py
│   └── cbnn.py
│
├── evaluation/
│   ├── concordance.py
│   ├── brier.py
│   ├── dynamic_auc.py
│   ├── calibration.py
│   └── bootstrap.py
│
├── splits/
│   └── rolling_origin.py
│
├── runs/
│   └── <run_id>/
│       ├── config_snapshot.yaml
│       ├── metrics.parquet
│       ├── predictions.parquet
│       └── hyperparameters.json
│
└── reports/
    ├── leaderboard.csv
    ├── feature_ablation.csv
    └── figures/
```

---

# 21. Minimum publishable benchmark

If compute/time is limited, the minimum defensible experiment is:

### Features

\[
F_{core}
=
F0+F1+F2+F3
\]

plus a separate

\[
F_{core}+F4
\]

policy experiment.

### Models

\[
\boxed{
KM,\;
CoxPH,\;
CoxNet,\;
Cloglog,\;
RSF,\;
BoostedCox,\;
CoxTime,\;
DeepHit,\;
CBNN
}
\]

DeepSurv can be included if the PH-vs-non-PH neural contrast is desired explicitly.

### Metrics

\[
\boxed{
IBS,\;
Antolini\ C,\;
AUC(t),\;
Calibration
}
\]

### Validation

Rolling-origin temporal validation with identical test windows.

This is enough to support a strong empirical claim about:

- linear versus nonlinear risk;
- PH versus non-PH;
- traditional versus ML;
- economic-feature value versus algorithmic value.

---

# 22. Main hypotheses to pre-register

## H1 — relationship strength

Higher initial trade value and market share reduce failure hazard.

## H2 — destination gravity

Larger, closer, more economically developed destinations exhibit higher relationship persistence, conditional on relationship/product factors.

## H3 — experience and diversification

Experience has a heterogeneous effect moderated by diversification and product proximity.

## H4 — policy barriers

Higher effective trade barriers increase relationship failure risk, subject to measurement-quality restrictions.

## H5 — nonlinear learning

Nonlinear models outperform linear Cox-style models if interactions and threshold effects are economically important.

## H6 — non-PH learning

Non-PH models outperform PH models when covariate effects vary materially with relationship age/calendar time.

## H7 — no universal ML dominance

If Cox/cloglog remain competitive, this is a valid scientific result rather than a failed ML experiment.

The 2025 Birolo paper and 2026 Burk benchmark both make this hypothesis scientifically credible.

---

# 23. Major failure modes to guard against

## 23.1 Temporal leakage

Using contemporaneous or future trade value to predict an event already reflected in that value.

**Control:** lag all endogenous flow variables.

## 23.2 Row-level random split

Same spell leaks across train/test.

**Control:** temporal rolling-origin validation.

## 23.3 Unequal feature information

ML receives 158 columns while Cox receives a hand-picked subset.

**Control:** feature × model matrix.

## 23.4 Wrong concordance metric

Static C-index is used to judge dynamic risk-ordering models.

**Control:** time-dependent concordance + Brier/calibration.

## 23.5 Measurement-calendar learning

ML learns `ntm6_source_year` or tariff data availability instead of economic policy.

**Control:** measurement-quality filters and source-year sensitivity analyses.

## 23.6 Overstating the 2025 tariff result

No post-2025 outcome is yet available.

**Control:** label it prospective scenario/stress inference.

## 23.7 Straw-man classical baseline

Only a purely linear Cox model is compared against powerful nonlinear networks.

**Control:** include theory-enhanced cloglog, CoxNet, and nonlinear-PH boosting/DeepSurv.

## 23.8 Hyperparameter-budget bias

Deep methods are given much larger tuning resources.

**Control:** predefine comparable trial/time budgets.

---

# 24. Recommended final paper framing

A strong Stage-1 paper can be framed around three nested contributions:

### Contribution 1 — domain dataset

A large spell-level dataset for Vietnam export relationships combining:

- trade flows;
- gravity/macro variables;
- product structure;
- tariffs/FTA;
- NTM/trade remedies;
- policy-shock variables.

### Contribution 2 — economic hazard analysis

Estimate which economic mechanisms drive persistence using discrete-time survival/econometric models.

### Contribution 3 — neutral predictive benchmark

Test whether relaxing:

1. linearity;
2. proportional hazards;

improves out-of-sample prediction under the **same feature set**.

This creates a research narrative stronger than “apply several ML models to trade data.”

---

# 25. References

## Four seed papers

1. Nitsch, V. (2007). *Die Another Day: Duration in German Import Trade*. CESifo Working Paper No. 2085.  
   https://www.ifo.de/DocDL/cesifo1_wp2085.pdf

2. Lawless, M., & Studnicka, Z. (2024). *Old Firms and New Export Flows: Does Experience Increase Survival?* Open Economies Review, 35, 215–243.  
   https://doi.org/10.1007/s11079-023-09727-4

3. Islam, J., Turgeon, M., Sladek, R., & Bhatnagar, S. (2024). *Case-Base Neural Network: Survival analysis with time-varying, higher-order interactions*. Machine Learning with Applications, 16, 100535.  
   https://doi.org/10.1016/j.mlwa.2024.100535

4. Birolo, G., Rossi, I., Sartori, F., Rollo, C., Fariselli, P., & Sanavia, T. (2025). *Beyond Cox models: Assessing the performance of machine-learning methods in non-proportional hazards and non-linear survival analysis*. Computers in Biology and Medicine, 198, 111176.  
   https://doi.org/10.1016/j.compbiomed.2025.111176

## Core ML survival references

5. Ishwaran, H., Kogalur, U. B., Blackstone, E. H., & Lauer, M. S. (2008). *Random survival forests*. Annals of Applied Statistics, 2(3), 841–860.  
   https://doi.org/10.1214/08-AOAS169

6. Katzman, J. L., et al. (2018). *DeepSurv: personalized treatment recommender system using a Cox proportional hazards deep neural network*. BMC Medical Research Methodology, 18, 24.  
   https://doi.org/10.1186/s12874-018-0482-1

7. Lee, C., Zame, W., Yoon, J., & van der Schaar, M. (2018). *DeepHit: A Deep Learning Approach to Survival Analysis With Competing Risks*. AAAI.  
   https://doi.org/10.1609/aaai.v32i1.11842

8. Kvamme, H., Borgan, Ø., & Scheel, I. (2019). *Time-to-Event Prediction with Neural Networks and Cox Regression*. Journal of Machine Learning Research, 20(129), 1–30.  
   https://www.jmlr.org/papers/v20/18-424.html

9. Gensheimer, M. F., & Narasimhan, B. (2019). *A scalable discrete-time survival model for neural networks*. PeerJ.  
   https://pmc.ncbi.nlm.nih.gov/articles/PMC6348952/

10. Nagpal, C., Li, X., & Dubrawski, A. (2021). *Deep Survival Machines: Fully Parametric Survival Regression and Representation Learning for Censored Data With Competing Risks*. IEEE Journal of Biomedical and Health Informatics, 25(8), 3163–3175.  
    https://doi.org/10.1109/JBHI.2021.3052441

11. Kopper, P., Wiegrebe, S., Bischl, B., Bender, A., & Rügamer, D. (2022). *DeepPAMM: Deep Piecewise Exponential Additive Mixed Models for Complex Hazard Structures in Survival Analysis*. PAKDD 2022.  
    https://doi.org/10.1007/978-3-031-05936-0_20

12. Wang, Z., & Sun, J. (2022). *SurvTRACE: Transformers for Survival Analysis with Competing Events*. ACM BCB 2022.  
    https://doi.org/10.1145/3535508.3545521

13. Wiegrebe, S., Kopper, P., Sonabend, R., Bischl, B., & Bender, A. (2024). *Deep learning for survival analysis: a review*. Artificial Intelligence Review, 57, 65.  
    https://doi.org/10.1007/s10462-023-10681-3

14. Burk, L., Zobolas, J., Bischl, B., Bender, A., Wright, M. N., & Sonabend, R. (2026). *A large-scale neutral comparison study of survival models on low-dimensional data*. Bioinformatics, 42(5), btag186.  
    https://doi.org/10.1093/bioinformatics/btag186

15. Jaeger, B. C., et al. (2019). *Oblique Random Survival Forests*. Annals of Applied Statistics, 13(3), 1847–1883.  
    https://doi.org/10.1214/19-AOAS1261

## Project source

16. NEU Bio Research Team. `SRT-survival-analysis`, branch `docs/idea-synthesis-and-data-progress`.  
    https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/tree/docs/idea-synthesis-and-data-progress

---

# 26. Final recommended decision

For the first serious benchmark run, freeze:

### Feature sets

\[
F0,\quad
F0+F1,\quad
F0+F1+F2,\quad
F0+F1+F2+F3,\quad
F0+\cdots+F4.
\]

Keep F5 as an extension.

### Core methods

\[
KM,\;
CoxPH,\;
CoxNet,\;
Cloglog,\;
RSF,\;
BoostedCox,\;
DeepSurv,\;
CoxTime,\;
DeepHit,\;
CBNN.
\]

### Primary score

\[
IBS
\]

with Antolini C-index, time-dependent AUC, and calibration as mandatory supporting metrics.

### Scientific interpretation

If ML wins, identify **why**:

- nonlinearity?
- non-PH?
- interactions?
- policy-shock regime?

If Cox/cloglog remain competitive, report that result directly. Recent neutral benchmarks show that this is entirely plausible and scientifically informative.

The benchmark should therefore be designed to answer:

> **Which modeling assumption must be relaxed to improve Vietnam export-survival prediction, and which economic information contributes the improvement?**

That is a publishable methodological question; “which model has the highest C-index?” is not sufficient on its own.
