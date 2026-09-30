# SRT Stage 1: Thiết kế thực nghiệm và kết quả Đợt 0–4

## Vietnam → EU27 export-relationship survival | Branch stage2/batch1

**Phạm vi báo cáo: panel Stage 1 v2, target exit\_gap1\_threshold10000\_v1. Toàn bộ Đợt 0–4 đã hoàn tất; kết quả hiện tại là temporal confirmation trên test origins 2019–2021, chưa phải final external validation.**

# 1\. Problem statement, sample, input features và target label

Bài toán nghiên cứu là dự báo và giải thích độ bền của quan hệ xuất khẩu Việt Nam ở cấp importer × product family. Đây không phải dữ liệu doanh nghiệp; một quan hệ có thể tiếp tục dù doanh nghiệp cụ thể tham gia quan hệ đã thay đổi.

## 1.1. Định nghĩa sample

| Thuộc tính | Định nghĩa |
| :---- | :---- |
| **Exporter** | Việt Nam (cố định) |
| **Quan hệ** | importer × product\_family |
| **Quan sát** | Một năm đang hoạt động trong một spell của quan hệ |
| **Nguồn trade** | Comtrade, importer-reported CIF |
| **Khoảng dữ liệu** | 2002–2025; training origins từ 2005 |
| **Full panel** | 932.204 dòng; 209 cột; 147 importers; 4.365 families |
| **B0 EU27** | 146.042 active rows; 15.958 confirmed events; origins 2012–2024 |
| **Đơn vị survival** | 189.830 spells; 112.885 confirmed events trên toàn panel |
| **Active rule** | Trade ≥ 10.000 USD/năm |
| **Gap rule** | Cho phép gián đoạn 1 năm; death chỉ xác nhận sau 2 năm không hoạt động quan sát được |

## 

## 

## 1.2. Target label và đầu ra cần dự báo

| Nhánh | Sample đầu vào | Target / output | Mục đích |
| :---- | :---- | :---- | :---- |
| **D — annual risk** | Origin đang active; X biết ở cuối năm t | y=1 nếu event xảy ra trong interval kế tiếp và đã được xác nhận; trường hợp chưa xác nhận bị mask | Dự báo q(exit năm t+1 | active tại t) |
| **L — landmark** | Quan hệ sống tại origin; X khóa tại origin | Remaining duration \+ censor indicator; xuất S(u|X) tại u=1–3 năm | Dự báo toàn bộ đường sống sót |
| **I — inference** | Person-period B0 EU27; interval có outcome đã xác nhận | Hệ số, marginal effects, time interactions và frailty | Giải thích association/cơ chế; tách khỏi leaderboard |

## 1.3. Input features, ý nghĩa và kiểu dữ liệu

Mọi feature phải có available\_at không muộn hơn prediction cutoff. Missing do chưa báo cáo hoặc thiếu lịch sử được coi là “unknown”, không được thay bằng 0; imputer và missing indicator chỉ được fit trong training fold.

| Block | Feature tiêu biểu được dùng | Ý nghĩa | Kiểu dữ liệu và grain |
| :---- | :---- | :---- | :---- |
| **D — Duration** | age\_obs, log\_age, known\_start | Tuổi spell quan sát được và độ tin cậy của điểm bắt đầu | Số nguyên/continuous derived \+ binary; spell-year/spell |
| **R — Relationship** | log\_value, lag value, initial value, market share, volatility | Sức mạnh và độ ổn định riêng của quan hệ | Continuous/log/lagged; importer–family–year hoặc spell |
| **M — Market/gravity** | GDP, GDP per capita, growth, inflation, total imports, distance | Quy mô thị trường và chi phí gravity | Continuous; importer-year, relation-year và static importer |
| **E — Experience/portfolio** | số products/markets, HS2 share, RCA, VN/world growth | Kinh nghiệm đa dạng hóa và vị thế danh mục | Count/log-count, share, continuous growth; importer/product/HS2-year |
| **P — Policy/tariff** | applied tariff, preference margin, cumulative EVFTA cut | Rào cản thuế và ưu đãi | Continuous percentage-point variables; product-family-year |
| **N — NTM** | SPS/TBT/other survey counts, source age, observed/mappable flags | Rào cản phi thuế và chất lượng coverage | Log-count, integer age, binary; relation/importer/product-year |
| **C — Complexity** | PCI, importer ECI, importer diversity | Độ phức tạp sản phẩm và năng lực danh mục thị trường | Continuous index \+ log-count; HS4-year/importer-year |
| **L — Logistics** | LPI overall, age since survey | Năng lực logistics và độ cũ của nguồn | Continuous index \+ integer; importer-wave/year |
| **H — Deep history** | prior spells, years since exit, active years, growth/trend, conditional HHI | Lịch sử tái gia nhập, momentum và concentration | Count, duration, continuous trend/HHI; relation/product/importer-year |

# 2\. Literature Review được chọn cho lượt experiment: Feature sets

Trade-survival literature được dùng để xác định các nhóm biến kinh tế; machine-learning survival literature không quyết định feature kinh tế mà quyết định cách mô hình hóa nonlinear, non-PH và uncertainty. Thiết kế dùng tám gói feature để đo incremental value thay vì đưa tất cả biến vào một lần.

| Set | Thành phần | Câu hỏi được kiểm tra | Vai trò trong lượt chạy |
| :---- | :---- | :---- | :---- |
| **S1** | D \+ R | Relationship strength đã đủ chưa? | Gói hẹp; luôn vào confirmation |
| **S2** | S1 \+ M | Macro/gravity thêm thông tin không? | Cumulative feature step |
| **S3** | S2 \+ E | Experience/portfolio thêm tín hiệu không? | Increment lớn nhất trong screening |
| **S4** | S3 \+ P | Tariff/policy thêm gì ngoài fundamentals? | Anchor: cả 16 model chạy trên S4 |
| **S5** | S4 \+ N | NTM có incremental value khi kiểm soát as-of? | Ineligible cho Task L ở các fold thiếu coverage |
| **S6** | S4 \+ C | Complexity có giá trị riêng không? | S★ được khóa cho cả D và L; chạy confirmation |
| **S7** | S4 \+ L | Logistics có giá trị riêng không? | Đối chiếu với S4/S6 |
| **S8** | S4 \+ N \+ C \+ L \+ H | Joint wide set có thắng sau selection không? | Dùng screening/LOBO; Task L dùng S8−N khi N ineligible |

Trong xác nhận ba fold, shortlist chỉ mở test với S1, S4 và S★. S★ được khóa trước khi đọc test và bằng S6 cho cả hai task. S5/S8 không đủ điều kiện cho Task L vì NTM as-of coverage ở fold phát triển chỉ đạt 40,4%, thấp hơn ngưỡng 50%.

# 

# 3\. Literature Review được chọn cho lượt experiment: Methods và optimization

Benchmark tách mô hình theo hai task. Task D tối ưu dự báo rủi ro một năm trên active origins; Task L tối ưu đường sống sót 1–3 năm từ landmark origin. Mỗi mô hình được fit bằng loss/likelihood phù hợp với cấu trúc của nó; hyperparameter được chọn bằng metric chính trên validation, không dùng test outcome.

| Họ phương pháp | Models | Cấu trúc / đầu ra | Objective khi fit |
| :---- | :---- | :---- | :---- |
| **Reference** | Age-only; Kaplan–Meier | Empirical hazard hoặc survival không covariate | Ước lượng empirical hazard / KM product-limit; không tune |
| **Traditional discrete hazard** | Cloglog, Logit, Probit, Flexible cloglog | Annual failure probability; linear/spline; grouped PH hoặc time interaction | Tối đa hóa Bernoulli log-likelihood theo link; ridge penalty khi cần |
| **Traditional survival** | CoxPH, CoxNet, Weibull AFT, Log-normal AFT | Linear PH hoặc parametric AFT | Cox negative partial log-likelihood (+ elastic-net); AFT full censored likelihood (+ penalizer) |
| **Tree-based ML** | BoostedHazard, RSF, GB-Cox | Nonlinear interactions; RSF non-PH; GB-Cox PH | Binary logloss; RSF log-rank splitting/ensemble; Cox negative log-likelihood |
| **Deep learning** | MLPHazard, DeepSurv, CoxTime, DeepHitSingle, CBNN | Annual probability, PH/non-PH hazard hoặc discrete survival PMF | BCE; Cox partial likelihood; DeepHit NLL \+ ranking loss; CBNN case-base BCE \+ sampling offset |
| **Inference branch** | Pooled cloglog, gamma frailty, RE logit/probit, event study | Association, heterogeneity, time-varying effect, EVFTA | Likelihood theo specification; SE cluster hai chiều; wild cluster bootstrap bổ sung |

**Nguyên tắc optimization: training loss dùng để ước lượng tham số trong từng trial; Brier 1y (Task D) hoặc IPCW IBS 1–3 (Task L) dùng để chọn hyperparameter giữa các trial. Vì vậy “loss khi train” và “metric dùng để xếp hạng benchmark” là hai lớp khác nhau.**

# 4\. Experiment setup

| Thành phần | Thiết lập | Mục đích |
| :---- | :---- | :---- |
| **Scope** | B0 EU27; target 10.000 USD, gap tolerance 1 | Giữ cùng estimand/cohort cho mọi model |
| **Views** | D annual risk; L landmark H1–3; I person-period inference | Không trộn classifier, survival curve và inference |
| **Preprocessing** | Median imputation \+ missing indicator fit trong train fold; bỏ constant theo fold | Ngăn leakage và không đồng nhất missing với zero |
| **Eligibility** | Block phụ N/C/L/H cần ≥50% train rows có giá trị as-of và không hằng | Không coi một block không tồn tại là đã được kiểm nghiệm |
| **Screening** | F2 validation; 16 model @S4 \+ 5 đại diện quét S1–S8 | Anchor \+ cross giảm compute nhưng vẫn phủ đủ method/feature |
| **Shortlist** | D: D01/D04/D05/D06; L: L02/L07/L08/L09/L05; sets S1/S4/S6 | Khóa bằng commit riêng trước khi mở test |
| **Confirmation** | 27 model×set configs trên F1/F2/F3; stochastic models refit/test 3 seeds | Đánh giá temporal stability |
| **Robustness** | LOBO 27 ô; Batch 3 có 66 ô cho selection, timing, target definition, vintage | Kiểm tra feature value và độ bền kết luận |
| **Uncertainty** | Paired bootstrap theo relation, B=1.000; không t-test ba fold | Giữ dependency của spells/landmarks cùng relation |
| **Trạng thái** | Đợt 0–4 hoàn tất; 151 confirmation cells; 0 failure | C11/C12 và final fold 2023 để Đợt 5 |

## 4.1. Temporal split và chống leakage

Không dùng random row split vì cùng relation có thể có nhiều spell và nhiều prediction origin. Mỗi fold chỉ dùng label đã được xác nhận trước cutoff; sau tuning, mô hình được refit đến cutoff ngay trước test origin.

| Task / Fold | Inner cutoff → validation origin | Refit cutoff | Test origin |
| :---- | :---- | :---- | :---- |
| **D / F1** | 2015 → 2016 | 2018 | 2019 |
| **D / F2** | 2016 → 2017 | 2019 | 2020 |
| **D / F3** | 2017 → 2018 | 2020 | 2021 |
| **L / F1** | 2013 → 2014 | 2018 | 2019 |
| **L / F2** | 2014 → 2015 | 2019 | 2020 |
| **L / F3** | 2015 → 2016 | 2020 | 2021 |

## 4.2. Metrics

| Task | Primary metric | Secondary metrics | Cách đọc |
| :---- | :---- | :---- | :---- |
| **D** | Brier score 1 năm | Log-loss, PR-AUC, ROC-AUC, calibration slope/intercept | Brier thấp hơn tốt hơn; reference \= age-only hazard |
| **L** | IPCW IBS 1–3 năm | Brier từng horizon, Antolini Ctd, td-AUC@1/@3, calibration, runtime | IBS thấp hơn tốt hơn; reference \= Kaplan–Meier |
| **I** | Coefficient / marginal effect \+ uncertainty | PH diagnostics, time interactions, sensitivity | Diễn giải association; không dùng SHAP/importance làm bằng chứng nhân quả |

 

## 4.3. Tuning, epoch và cấu hình huấn luyện

| Model family | Search space chính | Budget / stopping | Ghi chú công bằng |
| :---- | :---- | :---- | :---- |
| **GLM links** | ridge λ ∈ {0; 10⁻³; 10⁻²} | 3 grid points | Cloglog/logit/probit dùng cùng preprocessing |
| **Flexible cloglog** | spline df ∈ {3;5} × age interaction {no;yes} | 4 grid points | So sánh linear/grouped-PH với flexible/non-PH |
| **CoxNet / AFT** | l1\_ratio {0,1;0,5;0,9} × 30-alpha path; AFT penalizer {0;0,01;0,1} | Grid; CoxNet tối đa 100.000 iterations | CoxNet Breslow; CoxPH Efron |
| **Tree / boosting** | XGB depth 2–8, eta 0,01–0,3, subsampling/regularization; RSF 100 trees, leaf 20–300 | 15 Optuna trials; XGB tối đa 2.000 rounds, early stop 50 | Full eligible rows; không cap 8.000 như legacy |
| **Neural** | 1–3 layers; width 32/64/128/256; dropout 0–0,5; lr 10⁻⁴–10⁻²; batch 256/512/1024 | 15 Optuna trials; Adam; tối đa 100 epochs; patience 8 | Early stopping trên inner holdout của training relations |
| **Budget rule / seeds** | Nếu best trial nằm trong 25% trial cuối, cộng 15 trials | Batch 3 bổ sung 6 trials; tuning seed 1; refit/test seeds 1,2,3 | Không dùng validation/test cohort để early-stop network |

# 5\. Results

Đợt 2 có 151 ô xác nhận trên ba fold test và không có lỗi. Model ngẫu nhiên được báo cáo bằng trung bình ba seed. Khoảng tin cậy 95% được ước lượng bằng paired bootstrap theo relation importer × family với B \= 1.000.

## 5.1. Task D — xác suất exit trong một năm

| Hạng | Model | Set | Brier 1y | Skill vs age-only |
| :---- | :---- | :---- | :---- | :---- |
| **1** | MLP Hazard | S6 | 0,07397 | 0,106 |
| **2** | Flexible cloglog | S6 | 0,07418 | 0,103 |
| **3** | Boosted Hazard | S6 | 0,07432 | 0,102 |
| **4** | Linear cloglog | S6 | 0,07445 | 0,100 |
| **Ref.** | Age-only hazard | — | 0,08272 | 0 |

MLP đứng đầu, nhưng chỉ hơn linear cloglog 0,00048 Brier. Trong khi đó, tăng feature từ S1 lên S4 cải thiện khoảng 0,0048–0,0051. Vì vậy, ở Task D, feature representation quan trọng hơn tăng complexity của architecture.

## 5.2. Task L — đường sống sót 1–3 năm

| Hạng | Model | Set | IPCW IBS 1–3 | Skill vs KM |
| :---- | :---- | :---- | :---- | :---- |
| **1** | DeepHitSingle | S6 | 0,09181 | 0,298 |
| **2** | Random Survival Forest | S6 | 0,09256 | 0,292 |
| **3** | DeepSurv | S6 | 0,09332 | 0,286 |
| **4** | CoxTime | S6 | 0,09389 | 0,282 |
| **5** | CoxNet | S6 | 0,09415 | 0,280 |
| **Ref.** | Kaplan–Meier | — | 0,13079 | 0 |

DeepHit và RSF đứng đầu. Tuy nhiên C-index của các model chỉ nằm trong khoảng 0,850–0,853; chênh lệch IBS chủ yếu đến từ ước lượng magnitude/time profile của survival probability, không phải từ một ordering hoàn toàn khác.

## 5.3. Kết quả về feature value và robustness

| Kết quả | Effect size chính | Diễn giải |
| :---- | :---- | :---- |
| **Feature expansion, Task D** | S1→S4: −0,00475 đến −0,00506 Brier; tất cả CI loại 0 | Feature engineering lớn hơn architecture gain khoảng một bậc độ lớn |
| **Feature expansion, Task L** | S1→S4: −0,00325 đến −0,00655 IBS; tất cả CI loại 0 | Feature value lặp lại trên linear, tree và neural |
| **S4→S6** | D: chỉ −0,00007 đến −0,00020; L: CoxNet −0,00116, DeepHit −0,00042, RSF ≈0 | Complexity hữu ích rõ nhất như explicit representation cho linear model |
| **LOBO — bỏ R** | Metric xấu đi \+0,00365 đến \+0,00501 | Relationship strength là block không thể thiếu |
| **LOBO — bỏ E** | Metric xấu đi \+0,00168 đến \+0,00298 | Experience/portfolio là nguồn gain lớn nhất khi mở rộng từ S2 |
| **Feature selection** | Chọn khoảng 21–23/36–42 cột nhưng không cải thiện; D05 xấu \+0,00048 | Regularization/implicit selection của model đã làm phần lớn công việc |
| **Timing / history** | Lag-only xấu \+0,00169 đến \+0,00311; history 5 năm ≈ history 3 năm | Current-origin state quan trọng; chưa có bằng chứng long memory là bottleneck |
| **Vintage leakage** | NTM lenient làm CoxNet tốt giả −0,00068 IBS | Timing violation có thể thổi phồng benchmark |
| **Target robustness** | Exit rate đổi 7,9%–16,7% nhưng kết luận định tính giữ; ngoại lệ CoxNet gap0 | Kết quả bền với phần lớn threshold/gap definitions |

## 5.4. Kết luận cần báo cáo

Kết quả mạnh nhất là: R (relationship strength) và E (experience/portfolio) là hai nguồn thông tin cốt lõi; Task D gần đạt trần bằng mô hình hazard tương đối đơn giản, trong khi Task L thực sự hưởng lợi từ nonlinear survival models.

Không nên kết luận macro hoặc tariff “không quan trọng về kinh tế”. Kết quả chỉ cho thấy M và P có ít predictive information biên sau khi đã biết R/E. Riêng block P trong các fold dự báo không đo trực tiếp EVFTA vì biến cắt giảm EVFTA bằng 0 trong toàn bộ training origins.

EVFTA có pattern theo hướng giảm exit hazard ở nhóm chịu cắt thuế mạnh hơn, nhưng joint post-treatment Wald p \= 0,27; do đó đây mới là bằng chứng gợi ý, chưa phải kết luận nhân quả.

**C01–C10 đã có bằng chứng. C11 về generalization, C12 về equal-budget/calibration và fold final 2023 vẫn chưa chạy. Trạng thái phù hợp nhất là “result section nội bộ đã hoàn chỉnh về logic, nhưng chưa hoàn thành final external/generalization validation”.**

# Nguồn đối chiếu

[Design document](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/stage2/batch1/SRT_Stage1_Literature_Experiment_Design_VI.md)  
[Kế hoạch thực nghiệm](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/stage2/batch1/KE_HOACH_THUC_NGHIEM_DOT_1.md)  
[FINAL\_REPORT — Đợt 0–4](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/stage2/batch1/notebook/stage2_benchmark/reports/FINAL_REPORT.md)  
[Batch 2 — Leaderboards và metric phụ](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/stage2/batch1/notebook/stage2_benchmark/reports/batch2/REPORT.md)  
