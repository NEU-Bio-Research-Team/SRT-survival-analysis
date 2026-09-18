# Structured Review — Benchmark sống sót của quan hệ xuất khẩu Việt Nam

> **Phạm vi.** Tài liệu này tái cấu trúc kết quả của run `v1` theo năm phần: **Outline → Data → Model → Metrics → Results**. Nguồn chính là báo cáo benchmark ngày 10/09/2026; nhánh [`benchmark/literature-review`](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/tree/benchmark/literature-review) chỉ được dùng để kiểm tra và bổ sung định nghĩa feature, target và metric còn thiếu trong báo cáo.

> **Trạng thái benchmark.** 11 mô hình × 6 tập feature × 4 rolling-origin folds = **264 cells**, không cell nào lỗi. Bốn mô hình Phase 4 (DeepPAMM, ORSF, DSM, SurvTRACE) chưa được chạy và không thuộc kết quả này.

---

## 1. Outline

1. [Data](#2-data)
   - Bài toán dự báo và đơn vị quan sát
   - Input, target huấn luyện và output dự báo
   - Kích thước dữ liệu, cửa sổ thời gian và chia fold
   - Sáu tập feature F0–F5
   - Tổng quan từng feature
2. [Model](#3-model)
   - Tổng số mô hình
   - Phân loại theo traditional survival, tree-based ML và deep survival
   - Phân loại theo proportional hazards (PH) và non-PH
3. [Metrics](#4-metrics)
   - Brier Score và Integrated Brier Score
   - Antolini time-dependent concordance
   - Dynamic AUC
   - Expected Calibration Error
   - Bootstrap ΔIBS và thời gian chạy
4. [Results](#5-results)
   - Xếp hạng theo từng tập feature
   - Leaderboard trên tập feature đầy đủ
   - Độ ổn định qua bốn fold thời gian
   - Kết quả theo nhóm thời kỳ và tuổi quan hệ
   - Kết luận về feature, giả định mô hình và hiệu chuẩn

### Câu hỏi nghiên cứu trung tâm

Khi tất cả mô hình nhận **cùng một tập covariates được kiểm soát leakage**, liệu mô hình nonlinear và/hoặc non-proportional-hazards có cải thiện khả năng phân biệt và hiệu chuẩn xác suất sống sót của quan hệ xuất khẩu Việt Nam so với các hazard model truyền thống hay không?

### Kết luận ngắn

- **RSF đứng đầu theo primary metric IBS 1–3 năm**, nhưng lợi thế nhỏ và không thắng ở mọi fold.
- **Feature quan trọng hơn lựa chọn thuật toán**: thêm F1 làm IBS giảm khoảng 0,009–0,012, còn khoảng cách giữa phần lớn mô hình có covariates chỉ vài phần nghìn.
- **Nonlinearity không tạo lợi ích ổn định** khi vẫn giữ giả định PH.
- Lợi ích nhất quán nhất đến từ việc bỏ PH trong họ cây: **BoostedCox → RSF cải thiện 21/24 cells**.
- Các deep survival model không thắng tổng thể; **DeepSurv đặc biệt bất ổn và hiệu chuẩn kém** trên tập đầy đủ.

---

## 2. Data

### 2.1. Có bao nhiêu dataset?

Benchmark chỉ dùng **một panel dataset chính**: `data/final/stage1_panel.parquet`.

- Panel gốc: **949.537 episode-year rows × 205 columns**, gồm **194.461 spells**, giai đoạn 2002–2025.
- Ma trận prediction-origin sau bước xây dựng feature: **889.467 samples**.
- Cửa sổ hợp lệ để chấm leaderboard, 2003–2023: **778.971 samples**.
- Trong cửa sổ chấm điểm: **295.835 samples** cuối cùng quan sát thấy sự kiện chết; **123.618 samples** chết trong vòng một năm.

F0–F5 không phải sáu dataset độc lập. Chúng là **sáu phiên bản input cộng dồn của cùng panel**, dùng cho feature ablation:

| Cấu hình | Các block được dùng | Số feature đăng ký | Số cột model thực nhận |
|---|---|---:|---:|
| F0 | F0 | 3 | 3 |
| F0F1 | F0 + F1 | 17 | 25 |
| F0F1F2 | F0 + F1 + F2 | 31 | 46 |
| F0F1F2F3 | F0 + F1 + F2 + F3 | 38 | 56 |
| F0F1F2F3F4 | F0 + F1 + F2 + F3 + F4 | 52 | 78 |
| F0F1F2F3F4F5 | F0 + F1 + F2 + F3 + F4 + F5 | 60 | 88 |

Số cột lớn hơn số feature vì preprocessing tạo thêm các cờ `*_isna` cho những biến có missingness thực tế. Các cờ này có ý nghĩa: khoảng 20% panel là quan hệ tuổi 1, nơi lagged features khuyết theo cấu trúc, và nhóm này chứa khoảng một nửa số sự kiện.

Ba tương tác F3x chỉ được cấp cho `Cloglog-theory` và **không** nằm trong shared 60-feature/88-column matrix:

- `exp_dest × n_products_to_c_lag`
- `exp_prod × n_markets_for_p_lag`
- `exp_prod × proximity_hs2_lag`

### 2.2. Một sample được định nghĩa như thế nào?

Một sample là một **prediction origin**:

$$
i=(j,p,t),
$$

trong đó:

- $j$: nước nhập khẩu;
- $p$: họ sản phẩm;
- $t$: năm gốc dự báo.

Ví dụ logic: “Việt Nam đang có một quan hệ xuất khẩu sản phẩm $p$ sang nước $j$ trong năm 2018”. Hàng năm 2018 là một sample dùng thông tin biết được đến hết 2018 để dự báo quan hệ còn sống thêm 1, 2, …, 8 năm hay không.

Một spell có thể sinh nhiều samples ở các năm liên tiếp. Do đó, các rows trong cùng spell không độc lập. Pipeline lấy mẫu và bootstrap theo **spell**, không theo row, để giữ cấu trúc phụ thuộc này.

### 2.3. Input của một sample

Input của model là vector covariates:

$$
\mathbf{x}_{jpt}\in\mathbb{R}^{d},
$$

với $d\in\{3,25,46,56,78,88\}$ tùy cấu hình F0–F5 sau preprocessing.

Thông tin đầu vào chỉ được lấy từ tập thông tin $\mathcal{F}_t$: dữ liệu tại năm $t$, dữ liệu trễ $t-1$, thông tin cố định tại đầu spell, hoặc thuộc tính static. Các trường trực tiếp tiết lộ outcome hoặc thời điểm tương lai như `spell_end_year`, `event`, `right_censored`, `tariff_source_year` và các biến kịch bản thuế Mỹ 2025 bị cấm khỏi predictors.

Quy ước timing:

| Timing | Ý nghĩa |
|---|---|
| `at_t` | Giá trị đã biết ở prediction-origin year $t$ |
| `lag1` | Giá trị của năm $t-1$ |
| `spell_start` | Cố định tại năm spell bắt đầu |
| `static` | Thuộc tính bất biến theo thời gian trong thiết kế hiện tại |

### 2.4. Target huấn luyện

Panel quy ước `event = 1` tại năm $Y$ nghĩa là quan hệ **sống lần cuối trong năm Y và chết ở Y+1**. Từ prediction origin $t$:

$$
\text{duration}_u=\text{last year alive}-t+1.
$$

Mỗi sample có nhãn survival:

- `duration_u`: thời gian còn lại quan sát được tính từ năm gốc;
- `event_u`: 1 nếu quan sát thấy quan hệ chết, 0 nếu bị right-censored.

Đặc biệt, `duration_u = 1, event_u = 1` phải trùng với `event = 1` của row gốc. Pipeline assert điều này để tránh âm thầm chấm sai target.

### 2.5. Output của model

Mọi mô hình phải trả về cùng một loại output:

$$
\hat{\mathbf S}_i=
[\hat S_i(1\mid\mathbf{x}_i),\ldots,\hat S_i(8\mid\mathbf{x}_i)],
$$

trong đó $\hat S_i(u\mid\mathbf{x}_i)=P(T_i>u\mid\mathbf{x}_i)$ là xác suất quan hệ còn sống sau $u$ năm.

- Output kỹ thuật: ma trận `S(u | X)` có shape `(n_samples, 8)`.
- Primary evaluation chỉ dùng các chân trời 1–3 năm.
- IBS 1–5 chỉ được báo cáo ở các fold có đủ follow-up.
- Việc bắt mọi model xuất cùng survival curve giúp so sánh công bằng: model không bị chấm trên các đại lượng khác nhau như hazard, risk score và probability.

### 2.6. Cửa sổ thời gian và leakage control

| Năm | Cách dùng |
|---|---|
| 2002 | Loại: mọi lagged feature bị thiếu và các spell đang sống đều left-truncated |
| 2003–2023 | Prediction origins dùng cho benchmark |
| 2024–2025 | Chỉ dùng cho prospective scenario scoring, không thuộc leaderboard |

Hai lớp chống leakage:

1. **Rolling-origin split theo thời gian**, không random split.
2. **Administrative re-censoring tại information horizon của từng block.** Ví dụ, training kết thúc năm 2013 không được dùng thông tin rằng một spell sau đó chết năm 2018.

| Fold | Train years | Validation years | Test years | Train n | Validation n | Test n |
|---:|---|---|---|---:|---:|---:|
| 1 | 2003–2013 | 2014–2015 | 2016–2017 | 39.806 | 24.875 | 29.850 |
| 2 | 2003–2015 | 2016–2017 | 2018–2019 | 39.801 | 24.875 | 29.851 |
| 3 | 2003–2017 | 2018–2019 | 2020–2021 (COVID) | 39.802 | 24.875 | 29.850 |
| 4 | 2003–2019 | 2020–2021 | 2022–2023 | 39.807 | 24.875 | 29.851 |

Validation chỉ có một năm follow-up hợp lệ, nên hyperparameter selection dùng **IPCW Brier Score 1 năm**; kết quả cuối mới được chấm ở 1–3 năm.

### 2.7. Tổng quan nhanh từng feature

Các mô tả dưới đây được đối chiếu với [`feature_registry.yaml`](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/benchmark/literature-review/benchmark/features/feature_registry.yaml). Dấu “hazard kỳ vọng” là giả thuyết kinh tế đăng ký trước, không phải dấu hệ số ước lượng từ run.

#### F0 — Duration dependence (3 features)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `spell_age` | Tuổi hiện tại của quan hệ xuất khẩu | `at_t` | ↓ |
| `log_spell_age` | Tuổi quan hệ trên thang log, cho phép hiệu ứng tuổi giảm dần | `at_t` | ↓ |
| `left_trunc` | Cờ cho biết tuổi thật bắt đầu trước cửa sổ dữ liệu và không quan sát đầy đủ | `spell_start` | ? |

#### F1 — Relationship strength (14 features)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `log_initial_value` | Quy mô giá trị xuất khẩu ở năm đầu của spell | `spell_start` | ↓ |
| `log_value` | Quy mô giá trị xuất khẩu tại năm gốc | `at_t` | ↓ |
| `log_value_lag` | Quy mô giá trị xuất khẩu ở năm trước | `lag1` | ↓ |
| `value_growth_lag` | Động lượng/tốc độ tăng của dòng thương mại | `lag1` | ↓ |
| `vn_market_share` | Thị phần Việt Nam trong thị trường importer–product | `at_t` | ↓ |
| `vn_market_share_lag` | Thị phần Việt Nam trễ một năm | `lag1` | ↓ |
| `log_market_size` | Tổng cầu nhập khẩu của nước đích đối với sản phẩm | `at_t` | ↓ |
| `log_market_size_lag` | Quy mô thị trường đích trễ một năm | `lag1` | ↓ |
| `rca_lag` | Revealed Comparative Advantage của Việt Nam đối với sản phẩm | `lag1` | ↓ |
| `world_growth_lag` | Tăng trưởng nhu cầu thế giới đối với sản phẩm | `lag1` | ↓ |
| `volatility_3y_lag` | Mức bất ổn của dòng thương mại trong ba năm gần trước đó | `lag1` | ↑ |
| `log_unit_value_lag` | Unit value song phương; proxy cho giá/chất lượng | `lag1` | ↓ |
| `partner_share_pct` | Tỷ trọng nước đích trong tổng xuất khẩu sản phẩm đó của Việt Nam | `at_t` | ↓ |
| `product_share_pct` | Tỷ trọng sản phẩm trong tổng xuất khẩu của Việt Nam sang nước đích | `at_t` | ↓ |

#### F2 — Gravity and macroeconomics (14 features)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `log_gdp_d_lag` | Quy mô kinh tế của nước đích | `lag1` | ↓ |
| `log_gdpcap_d_lag` | Thu nhập bình quân đầu người của nước đích | `lag1` | ↓ |
| `log_pop_d_lag` | Dân số/thang quy mô thị trường nước đích | `lag1` | ↓ |
| `log_dist` | Khoảng cách địa lý, proxy cho trade cost | `static` | ↑ |
| `contig` | Hai nước có chung biên giới | `static` | ↓ |
| `comlang_off` | Có ngôn ngữ chính thức chung | `static` | ↓ |
| `comcol` | Có lịch sử chung nước thực dân | `static` | ↓ |
| `comrelig` | Mức độ gần gũi tôn giáo | `static` | ↓ |
| `wto_d` | Nước đích là thành viên WTO | `static` | ↓ |
| `eu_d` | Nước đích là thành viên EU | `static` | ↓ |
| `gdp_growth_d_lag` | Trạng thái chu kỳ kinh tế qua tăng trưởng GDP | `lag1` | ↓ |
| `inflation_d_lag` | Bất ổn vĩ mô qua lạm phát | `lag1` | ↑ |
| `fx_change_lag` | Biến động tỷ giá nội tệ nước đích so với USD | `lag1` | ↑ |
| `imports_pct_gdp_lag` | Độ mở nhập khẩu của nước đích | `lag1` | ↓ |

#### F3 — Experience, diversification and portfolio (7 features)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `exp_dest` | Số năm Việt Nam đã có kinh nghiệm xuất khẩu bất kỳ hàng hóa nào sang nước đích | `at_t` | ↓ |
| `exp_prod` | Số năm Việt Nam đã có kinh nghiệm xuất khẩu sản phẩm này ra bất kỳ thị trường nào | `at_t` | ↓ |
| `n_products_to_c_lag` | Độ đa dạng của giỏ sản phẩm xuất khẩu sang nước đích | `lag1` | ↓ |
| `n_markets_for_p_lag` | Độ rộng thị trường quốc tế của sản phẩm | `lag1` | ↓ |
| `hhi_market` | Mức tập trung thị trường của Việt Nam đối với sản phẩm | `at_t` | ↑ |
| `hhi_product` | Mức tập trung giỏ sản phẩm của Việt Nam tại nước đích | `at_t` | ↑ |
| `proximity_hs2_lag` | Proxy thô cho độ gần sản phẩm với giỏ xuất khẩu lõi: tỷ trọng chương HS2, không phải product-space co-export proximity chuẩn | `lag1` | ↓ |

#### F4 — Trade policy and barriers (14 features)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `tariff_rate` | Thuế quan áp dụng cho Việt Nam tại năm gốc | `at_t` | ↑ |
| `tariff_rate_lag` | Thuế quan áp dụng trễ một năm | `lag1` | ↑ |
| `tariff_change` | Cú sốc thuế: chênh lệch thuế hiện tại và năm trước | `at_t` | ↑ |
| `fta_in_force` | Có hiệp định thương mại đang có hiệu lực cho cặp nước | `at_t` | ↓ |
| `years_since_fta` | Độ trưởng thành của FTA, tính theo số năm có hiệu lực | `at_t` | ↓ |
| `pref_margin_lag` | Biên ưu đãi khi preferential rate thực sự được quan sát | `lag1` | ↓ |
| `ntm6_all_inforce` | Tổng số non-tariff measures đang hiệu lực ở HS6 | `at_t` | ↑ |
| `ntm6_sps_inforce` | Số biện pháp vệ sinh và kiểm dịch động thực vật (SPS) | `at_t` | ↑ |
| `ntm6_tbt_inforce` | Số hàng rào kỹ thuật đối với thương mại (TBT) | `at_t` | ↑ |
| `ntm6_observed` | Cờ đo lường: importer có thực sự nộp báo cáo NTM trong năm đó hay không; không phải biến chính sách | `at_t` | ? |
| `ntm_ave_border_pct` | Ad-valorem equivalent của NTM; trong dữ liệu hiện tại gần như là thuộc tính giữa các thị trường | `static` | ↑ |
| `ttb_any_in_force` | Có bất kỳ trade remedy nào đang hiệu lực | `at_t` | ↑ |
| `ad_in_force` | Có biện pháp chống bán phá giá đang hiệu lực | `at_t` | ↑ |
| `cbam_in_scope` | Sản phẩm thuộc phạm vi EU CBAM; non-EU được xử lý như structural zero | `at_t` | ↑ |

#### F5 — Complexity, resilience and common shocks (8 features)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `pci` | Product Complexity Index | `at_t` | ↓ |
| `importer_eci` | Economic Complexity Index của nước đích | `at_t` | ↓ |
| `importer_diversity` | Độ đa dạng xuất khẩu của nước đích | `at_t` | ↓ |
| `importer_lpi_overall` | Năng lực logistics tổng thể của nước đích | `static` | ↓ |
| `importer_glpi` | Chỉ số green logistics tổng hợp bằng PCA | `static` | ↓ |
| `gepu_current` | Global Economic Policy Uncertainty tại năm gốc | `at_t` | ↑ |
| `cmo_all_commodities` | Mức giá hàng hóa thế giới tổng hợp | `at_t` | ? |
| `price_energy` | Cú sốc giá năng lượng | `at_t` | ↑ |

### 2.8. Preprocessing chính

- `log1p`/`log_clip1`: giảm lệch phải và ổn định scale.
- `clip_pct`: chặn các tỷ lệ tăng trưởng cực đoan.
- `median+flag`: điền median học từ train và thêm cờ missing.
- `zero` hoặc `zero+flag`: dùng cho structural zero hoặc biến nhị phân.
- Mọi tham số preprocessing phải được fit trên train fold rồi áp dụng cho validation/test.

---

## 3. Model

### 3.1. Tổng số và cách phân loại

Có **11 mô hình đã chạy**:

- **1 no-covariate baseline:** Kaplan–Meier.
- **4 statistical/traditional survival models:** CoxPH, CoxNet, Cloglog, Cloglog-theory.
- **2 tree-based survival ML models:** BoostedCox, RSF.
- **4 deep survival models:** DeepSurv, CoxTime, DeepHit, CBNN.

`CoxNet` nằm ở vùng giao giữa traditional statistics và ML: về biểu diễn nó vẫn là linear Cox PH, nhưng dùng elastic-net regularization và model selection. Trong tài liệu này nó được đặt trong nhóm statistical/regularized survival, không coi là representation-learning model.

### 3.2. Ma trận giả định PH × tính phi tuyến

| | Proportional hazards (PH) | Non-proportional hazards (non-PH) |
|---|---|---|
| **Linear/traditional** | CoxPH, CoxNet, Cloglog | — |
| **Nonlinear/flexible** | BoostedCox, DeepSurv, Cloglog-theory | RSF, CoxTime, DeepHit, CBNN |

Kaplan–Meier là baseline không covariates nên không được đặt vào phép so sánh PH/non-PH theo $X$.

### 3.3. Tổng quan từng model

| Model | Nhóm | PH? | Cơ chế chính | Output survival curve |
|---|---|---:|---|---|
| **Kaplan–Meier** | Traditional nonparametric baseline | N/A | Ước lượng survival curve chung, không dùng feature | Một đường $\hat S(u)$ giống nhau cho mọi sample |
| **CoxPH** | Traditional semi-parametric hazard | Có | Log-risk tuyến tính $\eta=x^T\beta$, baseline hazard không tham số | Kết hợp relative risk với baseline cumulative hazard |
| **CoxNet** | Regularized survival regression | Có | CoxPH với elastic-net để shrink/select coefficients | Như CoxPH, nhưng hệ số được regularize |
| **Cloglog** | Traditional discrete-time hazard | Có | Complementary log-log hazard với baseline theo tuổi không ràng buộc và shared gamma frailty | Tích lũy discrete hazards; frailty correction $S=(1+\theta H)^{-1/\theta}$ |
| **Cloglog-theory** | Theory-enhanced traditional model | Có | Cloglog cộng spline cho hai biến được giả thuyết phi tuyến và ba tương tác F3x | Như Cloglog |
| **BoostedCox** | Tree-based survival ML | Có | Gradient-boosted trees tối ưu Cox partial likelihood | Tree risk score + Cox baseline hazard |
| **RSF** | Tree-based survival ML | Không | Random Survival Forest; mỗi tree học các survival/hazard patterns cục bộ | Trung bình survival/cumulative-hazard từ ensemble |
| **DeepSurv** | Deep survival | Có | MLP thay thế linear predictor trong Cox model | Neural risk score + Cox baseline hazard |
| **CoxTime** | Deep survival | Không | Neural relative risk phụ thuộc trực tiếp vào thời gian | Survival curve có risk ordering thay đổi theo thời gian |
| **DeepHit** | Deep discrete-time survival | Không | Mạng học phân phối xác suất thời gian sự kiện trên time grid | PMF/CDF được chuyển thành $S(u)$ |
| **CBNN** | Deep hazard model | Không | Case-base sampling; thời gian là input của neural hazard, có offset `log(B/b)` | Tích phân/tích lũy neural hazard theo thời gian |

### 3.4. Các contrast được thiết kế trước

Mục tiêu của benchmark không chỉ là tìm “model thắng”, mà tách ảnh hưởng của từng giả định:

| Contrast | So sánh | Giả định được cô lập |
|---|---|---|
| A | CoxPH → BoostedCox / DeepSurv | Thêm nonlinearity nhưng giữ PH |
| B | DeepSurv → CoxTime | Bỏ PH nhưng giữ họ neural network |
| C | BoostedCox → RSF | Bỏ PH nhưng giữ họ tree |
| D | DeepHit/CoxTime → CBNN | Cho thời gian đi trực tiếp vào model |
| E | CoxPH → CoxNet | Chỉ thêm regularization |
| F | Cloglog → Cloglog-theory | Kiểm tra baseline truyền thống có bị làm thành straw man hay không |

---

## 4. Metrics

### 4.1. Quy tắc đọc nhanh

| Metric | Đo cái gì? | Tốt hơn khi | Mốc diễn giải |
|---|---|---:|---|
| **Brier Score tại $u$** | Sai số bình phương của xác suất sống tại một horizon | Thấp hơn | 0 là hoàn hảo; phải so trên cùng horizon/dataset |
| **IBS 1–3y** | Brier Score trung bình/tích phân trong 1–3 năm | Thấp hơn | **Primary ranking metric** |
| **IBS 1–5y** | Sai số xác suất dài hơn | Thấp hơn | Chỉ hợp lệ ở folds 1–3 |
| **Antolini C** | Khả năng xếp hạng đúng tại thời điểm event xảy ra | Cao hơn | 0,5 ≈ ngẫu nhiên; 1 = hoàn hảo |
| **Dynamic AUC($u$)** | Phân biệt người chết trước $u$ với người sống quá $u$ | Cao hơn | 0,5 ≈ ngẫu nhiên; 1 = hoàn hảo |
| **ECE($u$)** | Độ lệch tuyệt đối giữa xác suất dự báo và sống sót quan sát | Thấp hơn | 0 là hiệu chuẩn hoàn hảo |
| **ΔIBS vs CoxPH** | Chênh lệch primary metric so với CoxPH | Âm hơn | Âm = tốt hơn CoxPH; CI phải xét theo spell bootstrap |
| **Seconds/cell** | Chi phí tính toán | Thấp hơn, nếu accuracy tương đương | Không phải metric chất lượng dự báo |

Không có một threshold tuyệt đối như “IBS < 0,1 là tốt” áp dụng cho mọi dữ liệu. IBS/Brier phụ thuộc event rate, censoring và horizon; nên đọc bằng so sánh out-of-sample trên **cùng test fold và cùng target**.

### 4.2. IPCW Brier Score

Tại horizon $u$, với $G$ là survival function của censoring distribution:

$$
\operatorname{BS}(u)=\frac{1}{n}\sum_{i=1}^{n}
\left[
\frac{\mathbb{1}(T_i\le u,\delta_i=1)\hat S_i(u)^2}{G(T_i-1)}
+
\frac{\mathbb{1}(T_i>u)(1-\hat S_i(u))^2}{G(u)}
\right].
$$

IPCW (inverse probability of censoring weighting) tránh coi sample bị censored trước $u$ như failure. Metric đồng thời phạt:

- xác suất sống cao cho một quan hệ đã chết trước $u$;
- xác suất sống thấp cho một quan hệ vẫn sống quá $u$.

**Cách đọc:** Brier 1y = 0,0937 của RSF thấp hơn 0,1212 của Kaplan–Meier, nên xác suất 1 năm của RSF chính xác hơn trên trung bình bình phương. Nó không có nghĩa là “RSF chính xác 90,63%”.

### 4.3. Integrated Brier Score

$$
\operatorname{IBS}_{[1,3]}=
\frac{1}{3-1}\int_1^3 \operatorname{BS}(u)\,du,
$$

được xấp xỉ bằng trapezoidal integration trên lưới 1, 2, 3 năm.

IBS 1–3 năm là metric chính vì downstream Stage 2 cần **xác suất sống được hiệu chuẩn** để tính `Trade value × predicted survival`. C-index đẹp nhưng probability lệch lớn vẫn làm expected value sai.

IBS 1–5 năm không dùng làm primary metric vì fold 4 không có đủ 5 năm follow-up; so sánh trung bình 4-fold bằng IBS 1–5 sẽ không hợp lệ.

### 4.4. Antolini time-dependent concordance

$$
C_{td}=P\left(\hat S_i(T_i)<\hat S_j(T_i)\mid T_i<T_j,\delta_i=1\right).
$$

Metric so sánh hai survival curves tại đúng thời điểm sample $i$ chết. Nó phù hợp hơn static Harrell C cho non-PH models vì risk ordering có thể thay đổi theo thời gian.

**Cách đọc:** 0,8197 nghĩa là khoảng 81,97% comparable pairs được xếp đúng, với ties tính nửa điểm trong implementation. Đây là discrimination, không chứng minh probability được hiệu chuẩn.

### 4.5. Cumulative/dynamic AUC

Tại horizon $u$:

- case: đã chết trước hoặc tại $u$;
- control: còn sống quá $u$;
- sample censored trước $u$: không được gán đoán thành case/control và được xử lý bằng IPCW.

Risk score được đọc trực tiếp từ curve: $1-\hat S(u)$.

**Cách đọc:** AUC 3y = 0,8466 nghĩa là một case và một control ngẫu nhiên có xác suất khoảng 84,66% được model xếp đúng theo risk tại ba năm. AUC cao không đảm bảo calibration tốt.

### 4.6. Expected Calibration Error

Predicted survival được chia thành mười nhóm có kích thước gần bằng nhau. Trong mỗi bin $b$:

- `predicted_b`: trung bình $\hat S(u)$;
- `observed_b`: survival quan sát bằng Kaplan–Meier để xử lý censoring.

$$
\operatorname{ECE}(u)=\sum_b\frac{n_b}{n}
\left|\operatorname{predicted}_b-\operatorname{observed}_{KM,b}\right|.
$$

**Cách đọc:** ECE 3y = 0,0388 nghĩa là khoảng cách tuyệt đối trung bình giữa xác suất dự báo và survival quan sát là **3,88 điểm phần trăm**. ECE không thể hiện model đang overpredict hay underpredict; cần xem calibration table/curve theo bin để biết hướng lệch.

### 4.7. Paired spell bootstrap

Benchmark resample **200 lần theo spell**, không theo row. Báo cáo $\Delta$IBS so với CoxPH:

$$
\Delta\operatorname{IBS}=\operatorname{IBS}_{model}-\operatorname{IBS}_{CoxPH}.
$$

- $\Delta<0$: model tốt hơn CoxPH.
- $\Delta>0$: model kém hơn CoxPH.
- “Significant” chỉ cho biết khoảng tin cậy không chứa 0; dấu của $\Delta$ mới cho biết khác biệt có lợi hay có hại.

---

## 5. Results

### 5.1. Quy tắc xếp hạng

Mọi xếp hạng chính dưới đây dùng **mean IBS 1–3y qua bốn test folds**; thấp hơn là tốt hơn. Kaplan–Meier không phụ thuộc feature nên chỉ đưa vào full leaderboard, không lặp lại trong mọi ablation column.

### 5.2. Xếp hạng model theo từng tập feature

| Feature set | Xếp hạng theo IBS 1–3y, từ tốt đến kém |
|---|---|
| **F0** | RSF 0,1207 ≈ CBNN 0,1207 → CoxTime 0,1218 → DeepSurv 0,1220 → CoxPH 0,1224 → BoostedCox 0,1234 → CoxNet 0,1235 → Cloglog-theory 0,1246 ≈ Cloglog 0,1246 → DeepHit 0,1348 |
| **F0F1** | RSF 0,1116 → DeepSurv 0,1117 → CBNN 0,1118 → CoxTime 0,1121 → CoxPH 0,1126 → BoostedCox 0,1128 → CoxNet 0,1130 → Cloglog-theory 0,1142 → Cloglog 0,1150 → DeepHit 0,1237 |
| **F0F1F2** | RSF 0,1117 ≈ DeepSurv 0,1117 → CBNN 0,1120 → CoxPH 0,1121 → BoostedCox 0,1126 → CoxTime 0,1129 → CoxNet 0,1136 → Cloglog-theory 0,1137 → Cloglog 0,1146 → DeepHit 0,1269 |
| **F0F1F2F3** | RSF 0,1122 → CoxPH 0,1130 → CBNN 0,1139 → BoostedCox 0,1140 → CoxNet 0,1150 → CoxTime 0,1160 → DeepSurv 0,1187 → Cloglog 0,1207 → Cloglog-theory 0,1217 → DeepHit 0,1286 |
| **F0F1F2F3F4** | RSF 0,1111 → CBNN 0,1128 → BoostedCox 0,1143 → CoxPH 0,1144 → DeepSurv 0,1145 → CoxNet 0,1154 → CoxTime 0,1176 → Cloglog 0,1213 → Cloglog-theory 0,1228 → DeepHit 0,1337 |
| **F0F1F2F3F4F5** | RSF 0,1122 → BoostedCox 0,1146 → CoxNet 0,1149 → Cloglog 0,1153 → Cloglog-theory 0,1161 → CoxPH 0,1166 → CBNN 0,1170 → CoxTime 0,1174 → DeepHit 0,1265 → DeepSurv 0,1299 |

#### Model tốt nhất của từng feature set

| Feature set | #1 | #2 | Khoảng cách #1–#2 | Nhận xét |
|---|---:|---:|---:|---|
| F0 | RSF/CBNN 0,1207 | Đồng hạng ở 4 chữ số | ≈0 | Chỉ duration features không đủ tách hai model |
| F0F1 | RSF 0,1116 | DeepSurv 0,1117 | 0,0001 | Lợi thế thực tế rất nhỏ |
| F0F1F2 | RSF/DeepSurv 0,1117 | Đồng hạng ở 4 chữ số | ≈0 | Gravity/macro không thay đổi thứ tự rõ ràng |
| F0F1F2F3 | RSF 0,1122 | CoxPH 0,1130 | 0,0008 | Traditional Cox trở lại vị trí thứ hai |
| F0F1F2F3F4 | RSF 0,1111 | CBNN 0,1128 | 0,0017 | Đây là feature set tốt nhất của RSF |
| Full F0–F5 | RSF 0,1122 | BoostedCox 0,1146 | 0,0024 | RSF vẫn thắng nhưng F5 làm điểm kém hơn F4 |

### 5.3. Full-feature leaderboard

| Model | IBS 1–3y ↓ | IBS 1–5y ↓ | Brier 1y ↓ | Brier 3y ↓ | Antolini C ↑ | AUC 1y ↑ | AUC 3y ↑ | ECE 3y ↓ | Seconds/cell ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **RSF** | **0,1122** | 0,1176 | **0,0937** | **0,1222** | 0,8115 | 0,8490 | 0,8423 | **0,0388** | 4 |
| BoostedCox | 0,1146 | 0,1203 | 0,0961 | 0,1257 | 0,8143 | 0,8523 | 0,8455 | 0,0620 | 103 |
| CoxNet | 0,1149 | 0,1203 | 0,0963 | 0,1258 | 0,8172 | 0,8536 | 0,8461 | 0,0512 | 1 |
| Cloglog | 0,1153 | 0,1203 | 0,1006 | 0,1237 | 0,8188 | 0,8574 | 0,8445 | 0,0492 | 2 |
| Cloglog-theory | 0,1161 | 0,1218 | 0,0994 | 0,1266 | **0,8197** | **0,8578** | 0,8459 | 0,0567 | 2 |
| CoxPH | 0,1166 | 0,1225 | 0,0972 | 0,1291 | 0,8190 | 0,8539 | **0,8466** | 0,0586 | 2 |
| CBNN | 0,1170 | 0,1190 | 0,0975 | 0,1261 | 0,8132 | 0,8465 | 0,8422 | 0,0642 | 4 |
| CoxTime | 0,1174 | 0,1248 | 0,0975 | 0,1306 | 0,8109 | 0,8466 | 0,8406 | 0,0678 | 4 |
| DeepHit | 0,1265 | 0,1347 | 0,1014 | 0,1440 | 0,8074 | 0,8479 | 0,8157 | 0,0824 | 26 |
| DeepSurv | 0,1299 | 0,1334 | 0,1062 | 0,1418 | 0,8092 | 0,8463 | 0,8412 | 0,1124 | 5 |
| Kaplan–Meier | 0,1510 | 0,1619 | 0,1212 | 0,1695 | 0,5000 | 0,5000 | 0,5000 | 0,0489 | 0 |

#### Cách đọc leaderboard

- **RSF là model tốt nhất theo metric chính**, đồng thời có Brier 1y, Brier 3y và ECE 3y tốt nhất.
- Model có discrimination tốt nhất không phải RSF: theo số trong bảng, `Cloglog-theory` có Antolini C = 0,8197 và AUC 1y = 0,8578; CoxPH có AUC 3y = 0,8466.
- Vì downstream cần probability, thứ hạng IBS/ECE quan trọng hơn việc chỉ chọn model có C/AUC cao nhất.
- CoxNet chỉ kém BoostedCox 0,0003 IBS nhưng nhanh hơn khoảng hai bậc độ lớn trong run này; nếu ưu tiên chi phí, CoxNet là baseline rất cạnh tranh.
- Khoảng cách từ Kaplan–Meier đến RSF là 0,0388 IBS; khoảng cách RSF đến CoxPH chỉ 0,0044. Phần lớn gain đến từ covariates, không phải model complexity.

### 5.4. Feature ablation: feature nào thực sự có ích?

| Model | F0 | +F1 | +F2 | +F3 | +F4 | +F5/full | Best set |
|---|---:|---:|---:|---:|---:|---:|---|
| RSF | 0,1207 | 0,1116 | 0,1117 | 0,1122 | **0,1111** | 0,1122 | F0–F4 |
| DeepSurv | 0,1220 | 0,1117 | **0,1117** | 0,1187 | 0,1145 | 0,1299 | F0F1/F0F1F2 |
| CBNN | 0,1207 | **0,1118** | 0,1120 | 0,1139 | 0,1128 | 0,1170 | F0F1 |
| CoxPH | 0,1224 | 0,1126 | **0,1121** | 0,1130 | 0,1144 | 0,1166 | F0F1F2 |
| CoxTime | 0,1218 | **0,1121** | 0,1129 | 0,1160 | 0,1176 | 0,1174 | F0F1 |
| BoostedCox | 0,1234 | 0,1128 | **0,1126** | 0,1140 | 0,1143 | 0,1146 | F0F1F2 |
| CoxNet | 0,1235 | **0,1130** | 0,1136 | 0,1150 | 0,1154 | 0,1149 | F0F1 |
| Cloglog-theory | 0,1246 | 0,1142 | **0,1137** | 0,1217 | 0,1228 | 0,1161 | F0F1F2 |
| Cloglog | 0,1246 | 0,1150 | **0,1146** | 0,1207 | 0,1213 | 0,1153 | F0F1F2 |
| DeepHit | 0,1348 | **0,1237** | 0,1269 | 0,1286 | 0,1337 | 0,1265 | F0F1 |

Kết luận ablation:

1. **F1 làm gần như toàn bộ công việc.** Relationship scale, momentum, market share và volatility đưa IBS của mọi model từ khoảng 0,121–0,135 xuống khoảng 0,112–0,124.
2. **F2 gần như trung tính.** Một số model cải thiện rất nhỏ, một số kém đi rất nhỏ.
3. **F3, F4 và F5 thường làm model kém hơn ngoài mẫu.** Chín trong mười covariate models đạt best score tại F0F1 hoặc F0F1F2.
4. **RSF là ngoại lệ:** nó đạt điểm tốt nhất tại F0–F4, cho thấy tree ensemble có thể bỏ qua/khai thác chọn lọc policy features tốt hơn các mô hình tuyến tính.
5. Full feature set không phải input tốt nhất. Việc thêm feature có động cơ kinh tế không đảm bảo tăng predictive signal.

### 5.5. Độ ổn định qua bốn temporal folds

Kết quả dưới đây là IBS 1–3y trên full feature set:

| Model | Fold 1 | Fold 2 | Fold 3 COVID | Fold 4 | Mean | Range max–min |
|---|---:|---:|---:|---:|---:|---:|
| RSF | 0,1191 | 0,1119 | 0,1078 | 0,1101 | **0,1122** | **0,0113** |
| BoostedCox | 0,1206 | 0,1141 | 0,1089 | 0,1149 | 0,1146 | 0,0117 |
| CoxNet | 0,1249 | 0,1158 | **0,1052** | 0,1136 | 0,1149 | 0,0197 |
| Cloglog | 0,1326 | 0,1122 | 0,1072 | 0,1091 | 0,1153 | 0,0254 |
| Cloglog-theory | 0,1337 | 0,1114 | 0,1074 | 0,1120 | 0,1161 | 0,0263 |
| CoxPH | 0,1378 | **0,1102** | 0,1066 | 0,1117 | 0,1166 | 0,0312 |
| CBNN | **0,1190** | 0,1147 | 0,1309 | **0,1035** | 0,1170 | 0,0274 |
| CoxTime | 0,1278 | 0,1169 | 0,1075 | 0,1174 | 0,1174 | 0,0203 |
| DeepHit | 0,1289 | 0,1251 | 0,1289 | 0,1231 | 0,1265 | 0,0058 |
| DeepSurv | 0,1401 | 0,1158 | 0,1593 | 0,1046 | 0,1300 | **0,0547** |
| Kaplan–Meier | 0,1590 | 0,1556 | 0,1454 | 0,1440 | 0,1510 | 0,0150 |

#### Đánh giá stability

- Không model nào đứng đầu cả bốn folds.
- Fold winners theo đúng giá trị số: **CBNN** ở fold 1, **CoxPH** ở fold 2, **CoxNet** ở fold 3, và **CBNN** ở fold 4.
- **RSF ổn định nhất trong nhóm model vừa có điểm trung bình cạnh tranh vừa không thất bại ở fold nào**, với range 0,0113 và hạng trung bình tốt nhất.
- DeepHit có numerical range nhỏ hơn, 0,0058, nhưng đây là “ổn định ở mức kém”: IBS luôn quanh 0,123–0,129. Vì vậy không nên dùng range đơn độc để chọn model.
- **DeepSurv bất ổn nhất**, range 0,0547; performance đặc biệt xấu ở COVID fold 3 nhưng lại rất tốt ở fold 4. Với chỉ một seed và hai tuning trials, kết luận về neural instability cần được kiểm tra lại bằng nhiều seeds.

### 5.6. Paired bootstrap so với CoxPH

Trên feature set F0–F4, mean paired $\Delta$IBS của RSF so với CoxPH là **−0,0033**.

| Fold | RSF − CoxPH | Diễn giải |
|---:|---:|---|
| 1 | −0,0080 | RSF tốt hơn có ý nghĩa |
| 2 | −0,0051 | RSF tốt hơn có ý nghĩa |
| 3 (COVID) | +0,0014 | RSF kém hơn có ý nghĩa |
| 4 | −0,0015 | RSF tốt hơn có ý nghĩa |

Vì vậy tuyên bố đúng là: **RSF thắng CoxPH ở ba trên bốn temporal regimes, nhưng không thống trị phổ quát**. Kết quả phù hợp giả thuyết H7 của benchmark.

### 5.7. Kết quả của các contrast kiến trúc

| So sánh | ΔIBS | Cells cải thiện | Kết luận |
|---|---:|---:|---|
| CoxPH → BoostedCox | +0,0001 | 7/24 | Nonlinearity trong họ tree nhưng giữ PH không giúp |
| CoxPH → DeepSurv | +0,0029 | 16/24 | Neural nonlinearity làm trung bình kém hơn |
| DeepSurv → CoxTime | −0,0018 | 9/24 | Bỏ PH trong họ neural cho lợi ích yếu, không nhất quán |
| **BoostedCox → RSF** | **−0,0021** | **21/24** | Lợi ích nhất quán nhất: bỏ PH trong họ tree |
| DeepHit → CBNN | −0,0144 | 23/24 | CBNN mạnh hơn DeepHit rõ, nhưng vẫn không thắng tổng thể |
| CoxPH → CoxNet | +0,0007 | 8/24 | Regularization riêng lẻ không tạo gain ổn định |
| Cloglog → Cloglog-theory | +0,0003 | 8/24 | Spline và theory interactions không cải thiện trung bình |

Lưu ý: dấu âm nghĩa là model phía sau tốt hơn. Kết quả trung bình theo “họ PH vs non-PH” có thể khác pairwise contrast vì nó trộn cả chất lượng implementation/model family; contrast giữ kiến trúc gần nhau là phép kiểm tra sạch hơn.

### 5.8. Kết quả theo tuổi quan hệ

Trên F0–F4:

| Nhóm tuổi | Model tốt nhất | IBS | Nhận xét |
|---|---|---:|---|
| Tuổi 1 | RSF | 0,2162 | Đây là nhóm khó và tạo phần lớn khác biệt giữa model |
| Tuổi 2–3 | CBNN | 0,1786 | CBNN nhỉnh hơn RSF 0,0012 |
| Tuổi 4+ | RSF | 0,0670 | Mọi model đều gần nhau; lựa chọn model ít quan trọng |

Biên giữa model tốt nhất và kém nhất khoảng 0,092 ở tuổi 1 nhưng chỉ khoảng 0,004 ở tuổi 4+. Do đó, **giá trị của model selection tập trung chủ yếu vào quan hệ mới**.

### 5.9. Kết quả theo temporal regime

Trên F0–F4:

| Giai đoạn | Model tốt nhất | IBS | Kết luận |
|---|---|---:|---|
| Trước COVID | RSF | 0,1143 | RSF có lợi thế rõ nhất trong giai đoạn bình thường trước cú sốc |
| COVID 2020–2021 | CoxPH | 0,1056 | Flexible models không bền hơn dưới cú sốc; đây là regime RSF thua CoxPH |
| Sau COVID 2022–2023 | CBNN | 0,1019 | Neural time-dependent hazard thích nghi tốt trong fold này |

Không có bằng chứng rằng model càng flexible thì càng robust trước structural shock.

### 5.10. Calibration

| Model | ECE 1y ↓ | ECE 3y ↓ |
|---|---:|---:|
| **RSF** | **0,0241** | **0,0388** |
| Kaplan–Meier | 0,0374 | 0,0489 |
| Cloglog | 0,0570 | 0,0492 |
| CoxNet | 0,0432 | 0,0512 |
| Cloglog-theory | 0,0546 | 0,0567 |
| CoxPH | 0,0423 | 0,0586 |
| BoostedCox | 0,0497 | 0,0620 |
| CBNN | 0,0423 | 0,0642 |
| CoxTime | 0,0440 | 0,0678 |
| DeepHit | 0,0552 | 0,0824 |
| DeepSurv | 0,0748 | 0,1124 |

- RSF tốt nhất ở cả ECE 1y và 3y.
- Theo các giá trị ECE 3y trong bảng, Kaplan–Meier hiệu chuẩn tốt hơn **9 trong 10** covariate models, dù discrimination của nó bằng ngẫu nhiên. Điều này cho thấy **calibration tốt không đồng nghĩa individualized prediction tốt**.
- DeepSurv lệch trung bình khoảng 11,24 điểm phần trăm ở ba năm. Đây là failure mode nghiêm trọng nếu dùng $\hat S$ để tính expected trade value.

### 5.11. Kết luận cuối cùng về kết quả

1. **Model nên chọn cho run v1:** RSF, nếu mục tiêu chính là xác suất sống 1–3 năm và calibration.
2. **Baseline production/benchmark nên giữ:** CoxNet hoặc CoxPH. CoxNet gần BoostedCox nhưng rẻ hơn rất nhiều; CoxPH mạnh trong COVID regime và dễ diễn giải.
3. **Feature set hợp lý nhất:** F0F1 hoặc F0F1F2 cho phần lớn model; riêng RSF tốt nhất ở F0–F4. Không nên mặc định full F0–F5 là input tốt nhất.
4. **Không có bằng chứng deep learning thắng classical survival** trong thiết kế và compute budget hiện tại.
5. **Kết luận kiến trúc mạnh nhất:** non-PH có ích trong họ tree, không phải nonlinearity nói chung.
6. **Tính ổn định:** RSF có trade-off mean–stability tốt nhất, nhưng không thắng ở từng fold; model ranking phụ thuộc temporal regime.
7. **Giới hạn cần giữ khi diễn giải:** train chỉ khoảng 40.000 origins/fold, riêng RSF và BoostedCox bị cap ở 8.000 train rows, mỗi deep model chỉ dùng một seed và 2–3 tuning trials, validation chỉ tối ưu Brier 1 năm. Vì vậy đây là bằng chứng so sánh V1, không phải performance ceiling của từng model.

### 5.12. Ghi chú kiểm tra tính nhất quán của báo cáo nguồn

Tài liệu này ưu tiên **giá trị số trong bảng** khi chúng mâu thuẫn với câu mô tả hoặc định dạng in đậm của báo cáo gốc:

- Ở fold 2, CoxPH có IBS 0,1102 và thực sự đứng đầu; ô Cloglog-theory 0,1114 được in đậm trong báo cáo nguồn nhưng không phải minimum.
- DeepHit có range qua fold nhỏ nhất, 0,0058, nhưng ổn định ở mức performance kém. Vì vậy nhận định “RSF ổn định nhất” chỉ đúng khi xét đồng thời **mean performance và variability**, không đúng nếu chỉ tối thiểu hóa range.
- Bảng ECE cho thấy Kaplan–Meier tốt hơn 9/10 covariate models ở horizon ba năm; câu mô tả “7/10” trong báo cáo nguồn không khớp với chính bảng số liệu.

---

## Nguồn đối chiếu

- [Benchmark branch](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/tree/benchmark/literature-review)
- [Frozen benchmark configuration](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/benchmark/literature-review/benchmark/config/benchmark.yaml)
- [Feature registry](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/benchmark/literature-review/benchmark/features/feature_registry.yaml)
- [Benchmark README and design rationale](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/benchmark/literature-review/benchmark/README.md)
- [Brier/IBS implementation](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/benchmark/literature-review/benchmark/evaluation/brier.py)
- [Antolini concordance implementation](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/benchmark/literature-review/benchmark/evaluation/concordance.py)
- [Dynamic AUC implementation](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/benchmark/literature-review/benchmark/evaluation/dynamic_auc.py)
- [Calibration/ECE implementation](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/benchmark/literature-review/benchmark/evaluation/calibration.py)
