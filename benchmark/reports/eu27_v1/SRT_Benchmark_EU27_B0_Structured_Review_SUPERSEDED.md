# Structured Review — Benchmark sống sót của quan hệ xuất khẩu Việt Nam × EU-27 (khung B0)

> **Phạm vi.** Tài liệu này báo cáo run `eu27_v1` (16/09/2026), tái cấu trúc theo đúng năm phần của [`SRT_Benchmark_Structured_Review.md`](SRT_Benchmark_Structured_Review.md): **Outline → Data → Model → Metrics → Results**. Khác với run `v1` gốc — vốn vô tình mở rộng ra **147 nước nhập khẩu × 2002–2025** và đánh mất khung EVFTA — run này chạy đúng scope **thầy đã chốt** ở `Stage1_Research_Framework.md` (khối "B0"): **Việt Nam × EU-27 × HS6 × 2012–2024**, với **lộ trình cắt thuế EVFTA làm biến chính sách trung tâm**. Toàn bộ phương pháp luận feature/model đã chọn qua literature review (F0–F5, 11 model, rolling-origin, IPCW Brier/IBS/Antolini/AUC/ECE, paired spell bootstrap) được **giữ nguyên** — chỉ có tầng dữ liệu và cửa sổ dự báo được sửa lại cho đúng.

> **Trạng thái benchmark.** 11 mô hình × 6 tập feature × 4 rolling-origin folds = **264 cells**, không cell nào lỗi. Panel nguồn không đổi so với `v1` (vẫn `data/final/stage1_panel.parquet`, 147 nước, 2002–2025) — điểm khác là một lớp lọc **VN×EU27×2012–2024** được áp **sau** khi các feature toàn cầu (`exp_dest`, `exp_prod`, kinh nghiệm/portfolio) đã được tính trên toàn bộ 147 nước, để không đánh giá thấp kinh nghiệm xuất khẩu thật của Việt Nam. Bốn mô hình Phase 4 (DeepPAMM, ORSF, DSM, SurvTRACE) vẫn chưa chạy.

---

## 1. Outline

1. [Data](#2-data)
   - Bài toán dự báo và đơn vị quan sát
   - Input, target huấn luyện và output dự báo
   - Kích thước dữ liệu, cửa sổ thời gian và chia fold
   - Sáu tập feature F0–F5 (F4 mở rộng 3 biến EVFTA thật)
   - Tổng quan từng feature
   - Feature nào biến mất vì scope EU27
2. [Model](#3-model)
   - Tổng số mô hình
   - Phân loại theo traditional survival, tree-based ML và deep survival
   - Phân loại theo proportional hazards (PH) và non-PH
3. [Metrics](#4-metrics)
   - Brier Score và Integrated Brier Score
   - Antolini time-dependent concordance
   - Dynamic AUC
   - Expected Calibration Error
   - Bootstrap ΔIBS
4. [Results](#5-results)
   - Xếp hạng theo từng tập feature
   - Leaderboard trên tập feature đầy đủ
   - Độ ổn định qua bốn fold thời gian
   - Kết quả theo tuổi quan hệ và theo giai đoạn trước/sau EVFTA
   - Kết luận về feature, giả định mô hình và hiệu chuẩn
   - Giới hạn và khác biệt so với `v1`

### Câu hỏi nghiên cứu trung tâm

Khi tất cả mô hình nhận **cùng một tập covariates được kiểm soát leakage**, trên đúng mẫu **VN × EU-27 × 2012–2024** mà đề tài đã chốt, liệu mô hình nonlinear và/hoặc non-proportional-hazards có cải thiện khả năng phân biệt và hiệu chuẩn xác suất sống sót so với các hazard model truyền thống hay không?

### Kết luận ngắn

- **RSF vẫn đứng đầu theo IBS 1–3 năm** (0,0872), biên độ nhỏ và không thắng ở mọi fold — kết luận định tính giống `v1`.
- **F1 (relationship strength) vẫn làm phần lớn công việc**; nhưng trên scope EU27, full feature set (F0–F5) gần như không kém F0F1 đối với RSF (0,0872 so với 0,0866) — khác `v1`, nơi full set kém hẳn F0–F4.
- **Contrast mạnh nhất vẫn là bỏ PH trong họ cây**: BoostedCox → RSF cải thiện 20/24 cells, ΔIBS trung bình −0,0041.
- **Phát hiện mới, riêng của bản EU27 này:** biến `evfta_cut_cum_pp_lag` (mức cắt thuế EVFTA lũy kế) **hằng số bằng 0 trong mọi train block của cả 4 fold** — vì EVFTA có hiệu lực 1/8/2020 và mọi train window đều kết thúc ≤ 2020, nên biến này chưa từng đóng góp gì vào bất kỳ model nào ở đây. Hai biến EVFTA còn lại (`tariff_applied_lag`, `years_since_evfta_policy`) sống sót và được dùng.
- Fold 4 (test chỉ có năm 2024) khiến **Antolini C không tính được (NaN) cho toàn bộ fold này** — hệ quả cấu trúc của cửa sổ B0 ngắn hơn `v1`, không phải lỗi.

---

## 2. Data

### 2.1. Có bao nhiêu dataset?

Vẫn **một panel dataset chính**, không đổi so với `v1`: `data/final/stage1_panel.parquet` — **949.537 episode-year rows × 205 columns**, **194.461 spells**, giai đoạn 2002–2025, 147 nước nhập khẩu.

Khác với `v1`, run này áp thêm một **lớp lọc scope** trước khi vào leaderboard:

| Bước | Số dòng | Ghi chú |
|---|---:|---|
| Panel nguồn | 949.537 | 147 nước, 2002–2025 |
| Sau bỏ gap-filled padding rows | 902.645 | như `v1` |
| Sau lọc cửa sổ (giữ tới 2025 cho prospective margin) | 673.856 | trước khi lọc nước |
| **Sau lọc EU-27 theo năm** | **172.848** | `selection/eu_tariff_mapping.csv`, `tariff_reporter == "EUN"` |
| Trong cửa sổ chấm leaderboard 2012–2024 | **156.557** | |
| — trong đó cuối cùng quan sát thấy sự kiện chết | 43.027 | trên toàn bộ follow-up quan sát được |
| — trong đó chết trong vòng một năm | **19.368** | khớp với đếm độc lập trước khi build matrix |

**Vì sao lọc nước diễn ra sau, không phải trước.** `exp_dest`/`exp_prod` (kinh nghiệm xuất khẩu của Việt Nam sang một nước bất kỳ / với một sản phẩm sang bất kỳ thị trường nào) và các chỉ số RCA/HHI/thị phần đều được tính trên **toàn bộ 147 nước** trước khi lọc. Nếu lọc EU27 trước, "kinh nghiệm toàn cầu" của Việt Nam sẽ bị hiểu nhầm thành "kinh nghiệm trong EU" — làm sai lệch đúng những feature mà B3 gọi là economies-of-scope. Cửa sổ thời gian cũng vậy: panel vẫn giữ lịch sử từ 2002 để đếm tuổi/kinh nghiệm chính xác cho một origin từ 2012, dù prediction origin chỉ bắt đầu từ 2012.

**EU-27 được xác định theo năm**, không phải một danh sách tĩnh: `selection/eu_tariff_mapping.csv` gắn cờ `tariff_reporter == "EUN"` cho từng (nước, năm), phản ánh đúng Brexit (`GBR` là thành viên tới 2020, rút khỏi 2021) và các đợt gia nhập trước đó. 28 nước từng xuất hiện là thành viên trong cửa sổ 2012–2024 (27 nước hiện tại cộng UK giai đoạn 2012–2020).

F0–F5 vẫn là **sáu phiên bản input cộng dồn**, dùng cho feature ablation. F4 mở rộng thêm 3 feature EVFTA thật (xem §2.7):

| Cấu hình | Các block được dùng | Số feature đăng ký | Số cột model thực nhận* |
|---|---|---:|---:|
| F0 | F0 | 3 | 3 |
| F0F1 | F0 + F1 | 17 | 25 |
| F0F1F2 | F0 + F1 + F2 | 31 | 36 |
| F0F1F2F3 | F0 + F1 + F2 + F3 | 38 | 45 |
| F0F1F2F3F4 | F0 + F1 + F2 + F3 + F4 | 55 | 64 |
| F0F1F2F3F4F5 | F0 + F1 + F2 + F3 + F4 + F5 | 63 | 72 |

\* Đếm trên train block của fold 4 (lớn nhất, đại diện nhất); số cột thực tế xê dịch nhẹ theo từng fold vì bộ lọc zero-variance (`sd > 1e-12`) chạy riêng trên từng train block.

Số cột model **thấp hơn** `v1` ở cùng cấu hình (ví dụ F0F1F2: 36 so với 46 ở `v1`) vì một số dummy trở thành hằng số khi mẫu chỉ còn EU-27 — xem §2.7bis.

Ba tương tác F3x vẫn chỉ cấp cho `Cloglog-theory`, không đổi:

- `exp_dest × n_products_to_c_lag`
- `exp_prod × n_markets_for_p_lag`
- `exp_prod × proximity_hs2_lag`

### 2.2. Một sample được định nghĩa như thế nào?

Không đổi so với `v1`. Một sample là một **prediction origin**:

$$
i=(j,p,t),
$$

trong đó $j$ nay bị giới hạn: $j\in\text{EU-27 tại năm }t$; $p$ là họ sản phẩm; $t\in[2012,2024]$.

Một spell có thể sinh nhiều samples ở các năm liên tiếp; các rows trong cùng spell không độc lập. Pipeline lấy mẫu và bootstrap theo **spell**, không theo row.

### 2.3. Input của một sample

$$
\mathbf{x}_{jpt}\in\mathbb{R}^{d},\qquad d\in\{3,25,36,45,64,72\}.
$$

Quy ước timing (`at_t`, `lag1`, `spell_start`, `static`) không đổi. Các trường tiết lộ outcome/tương lai (`spell_end_year`, `event`, `right_censored`, `tariff_source_year`, biến kịch bản thuế Mỹ 2025) vẫn bị cấm khỏi predictors — bản EU27 này không đụng đến nhánh thuế Mỹ, đúng scope B0 (`importer = EU-27`).

### 2.4. Target huấn luyện

Không đổi:

$$
\text{duration}_u=\text{last year alive}-t+1.
$$

`duration_u = 1, event_u = 1` vẫn được assert phải trùng `event = 1` của row gốc — đã kiểm tra lại **trên đúng lát EU27+2012–2024**, không chỉ trên toàn panel.

### 2.5. Output của model

Không đổi: mọi model trả về $\hat{\mathbf S}_i=[\hat S_i(1\mid\mathbf{x}_i),\ldots,\hat S_i(8\mid\mathbf{x}_i)]$, primary evaluation ở 1–3 năm.

### 2.6. Cửa sổ thời gian, leakage control và fold

| Năm | Cách dùng |
|---|---|
| 2002–2011 | Giữ trong panel nguồn chỉ để đếm tuổi/kinh nghiệm (left-truncation, `exp_dest`, `exp_prod`) — **không** dùng làm prediction origin trong bản B0 này |
| **2012–2024** | Prediction origins dùng cho benchmark, đúng B0 chốt |
| 2025 | Chỉ giữ như prospective margin, không thuộc leaderboard |

Hai lớp chống leakage giữ nguyên: rolling-origin split theo thời gian, và administrative re-censoring tại information horizon của từng block.

Vì cửa sổ B0 (13 năm origin) ngắn hơn nhiều so với `v1` (21 năm), 4 fold được nén lại nhưng giữ đúng nhịp thiết kế gốc (train mở rộng, test trượt 2 năm mỗi fold), sao cho fold 2 vẫn cô lập đúng giai đoạn COVID:

| Fold | Train years | Validation years | Test years | Train n | Validation n | Test n |
|---:|---|---|---|---:|---:|---:|
| 1 | 2012–2015 | 2016–2017 | 2018–2019 | 28.955 | 10.982 | 24.923 |
| 2 | 2012–2017 | 2018–2019 | 2020–2021 (COVID) | 39.801 | 12.289 | 26.091 |
| 3 | 2012–2019 | 2020–2021 | 2022–2023 | 39.803 | 12.930 | 28.373 |
| 4 | 2012–2021 | 2022–2023 | **2024** (hậu-EVFTA, 1 năm) | 39.802 | 13.927 | 15.108 |

**Fold 4 lệch với ba fold kia:** cửa sổ B0 dừng ở 2024 nên test block chỉ còn đúng một năm, không phải hai. Đây là đánh đổi có chủ đích để dùng hết 13 năm dữ liệu thay vì bỏ năm 2024; hệ quả của nó (Antolini C = NaN ở fold này) nêu ở §4.4 và §5.11.

Validation vẫn chỉ có một năm follow-up hợp lệ nên hyperparameter selection dùng IPCW Brier Score 1 năm; kết quả cuối chấm ở 1–3 năm.

### 2.7. Tổng quan nhanh từng feature

Đối chiếu với [`benchmark/features/feature_registry_eu27.yaml`](benchmark/features/feature_registry_eu27.yaml). F0, F1, F2, F3, F5 **giữ nguyên** so với `v1`; chỉ F4 được mở rộng.

#### F0 — Duration dependence (3 features, không đổi)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `spell_age` | Tuổi hiện tại của quan hệ xuất khẩu | `at_t` | ↓ |
| `log_spell_age` | Tuổi quan hệ trên thang log | `at_t` | ↓ |
| `left_trunc` | Cờ tuổi thật bắt đầu trước cửa sổ dữ liệu | `spell_start` | ? |

#### F1 — Relationship strength (14 features, không đổi)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `log_initial_value` | Quy mô giá trị xuất khẩu ở năm đầu spell | `spell_start` | ↓ |
| `log_value` | Quy mô giá trị xuất khẩu tại năm gốc | `at_t` | ↓ |
| `log_value_lag` | Quy mô giá trị xuất khẩu năm trước | `lag1` | ↓ |
| `value_growth_lag` | Động lượng dòng thương mại | `lag1` | ↓ |
| `vn_market_share` | Thị phần VN trong thị trường importer–product | `at_t` | ↓ |
| `vn_market_share_lag` | Thị phần VN trễ một năm | `lag1` | ↓ |
| `log_market_size` | Tổng cầu nhập khẩu của nước đích | `at_t` | ↓ |
| `log_market_size_lag` | Quy mô thị trường đích trễ một năm | `lag1` | ↓ |
| `rca_lag` | RCA của Việt Nam với sản phẩm | `lag1` | ↓ |
| `world_growth_lag` | Tăng trưởng nhu cầu thế giới | `lag1` | ↓ |
| `volatility_3y_lag` | Bất ổn dòng thương mại 3 năm gần trước | `lag1` | ↑ |
| `log_unit_value_lag` | Unit value song phương | `lag1` | ↓ |
| `partner_share_pct` | Tỷ trọng nước đích trong XK sản phẩm của VN | `at_t` | ↓ |
| `product_share_pct` | Tỷ trọng sản phẩm trong XK của VN sang nước đích | `at_t` | ↓ |

#### F2 — Gravity and macroeconomics (14 features, không đổi — nhưng xem §2.7bis)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `log_gdp_d_lag` | Quy mô kinh tế nước đích | `lag1` | ↓ |
| `log_gdpcap_d_lag` | Thu nhập bình quân đầu người nước đích | `lag1` | ↓ |
| `log_pop_d_lag` | Dân số/quy mô thị trường nước đích | `lag1` | ↓ |
| `log_dist` | Khoảng cách địa lý | `static` | ↑ |
| `contig` | Chung biên giới | `static` | ↓ |
| `comlang_off` | Chung ngôn ngữ chính thức | `static` | ↓ |
| `comcol` | Chung lịch sử thuộc địa | `static` | ↓ |
| `comrelig` | Gần gũi tôn giáo | `static` | ↓ |
| `wto_d` | Thành viên WTO | `static` | ↓ |
| `eu_d` | Thành viên EU | `static` | ↓ |
| `gdp_growth_d_lag` | Chu kỳ kinh tế qua tăng trưởng GDP | `lag1` | ↓ |
| `inflation_d_lag` | Bất ổn vĩ mô qua lạm phát | `lag1` | ↑ |
| `fx_change_lag` | Biến động tỷ giá | `lag1` | ↑ |
| `imports_pct_gdp_lag` | Độ mở nhập khẩu | `lag1` | ↓ |

#### F3 — Experience, diversification and portfolio (7 features, không đổi)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `exp_dest` | Kinh nghiệm XK bất kỳ hàng hóa nào sang nước đích | `at_t` | ↓ |
| `exp_prod` | Kinh nghiệm XK sản phẩm này ra bất kỳ thị trường nào (toàn cầu) | `at_t` | ↓ |
| `n_products_to_c_lag` | Đa dạng giỏ sản phẩm sang nước đích | `lag1` | ↓ |
| `n_markets_for_p_lag` | Độ rộng thị trường quốc tế của sản phẩm (toàn cầu) | `lag1` | ↓ |
| `hhi_market` | Tập trung thị trường của VN với sản phẩm | `at_t` | ↑ |
| `hhi_product` | Tập trung giỏ sản phẩm của VN tại nước đích | `at_t` | ↑ |
| `proximity_hs2_lag` | Proxy độ gần sản phẩm với giỏ XK lõi | `lag1` | ↓ |

#### F4 — Trade policy and barriers (**17 features, +3 so với v1**)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `tariff_rate` | Thuế quan áp dụng cho VN tại năm gốc | `at_t` | ↑ |
| `tariff_rate_lag` | Thuế quan áp dụng trễ một năm | `lag1` | ↑ |
| `tariff_change` | Cú sốc thuế | `at_t` | ↑ |
| `fta_in_force` | Có FTA đang hiệu lực | `at_t` | ↓ |
| `years_since_fta` | Độ trưởng thành của FTA (bất kỳ) | `at_t` | ↓ |
| `pref_margin_lag` | Biên ưu đãi khi preferential rate được quan sát | `lag1` | ↓ |
| **`tariff_applied_lag`** ⭐ | Thuế thực áp dụng cho VN theo EVFTA (MFN/GSP/lộ trình cắt, tùy cái nào panel giải quyết được năm đó) — thay thế bản thô `tariff_rate_lag` cho các dòng EU27 | `lag1` | ↑ |
| **`evfta_cut_cum_pp_lag`** ⭐ | Mức cắt thuế EVFTA lũy kế (điểm phần trăm) — biến treatment liên tục theo lộ trình staging, đúng ý B6 | `lag1` | ↓ |
| **`years_since_evfta_policy`** ⭐ | Số năm kể từ khi **riêng EVFTA** (không phải FTA nào khác) có hiệu lực | `at_t` | ↓ |
| `ntm6_all_inforce` | Tổng NTM đang hiệu lực ở HS6 | `at_t` | ↑ |
| `ntm6_sps_inforce` | Biện pháp SPS | `at_t` | ↑ |
| `ntm6_tbt_inforce` | Hàng rào kỹ thuật TBT | `at_t` | ↑ |
| `ntm6_observed` | Cờ đo lường, không phải biến chính sách | `at_t` | ? |
| `ntm_ave_border_pct` | AVE của NTM | `static` | ↑ |
| `ttb_any_in_force` | Có trade remedy nào đang hiệu lực | `at_t` | ↑ |
| `ad_in_force` | Có biện pháp chống bán phá giá | `at_t` | ↑ |
| `cbam_in_scope` | Sản phẩm thuộc phạm vi CBAM | `at_t` | ↑ |

⭐ = ba biến EVFTA mới đăng ký cho bản EU27 này. Cả ba đã có sẵn trong `stage1_panel.parquet` (parse từ Annex 2-A, verify chéo với TRAINS lệch 0,17–0,34pp, join khớp 99,2–100% episode EU27) nhưng chưa từng được đăng ký trong `feature_registry.yaml` gốc vì file đó phải hợp lệ cho cả 147 nước, còn ba biến này chỉ có giá trị cho EU27.

**Nhưng xem §2.7bis: `evfta_cut_cum_pp_lag` không thực sự được model nào dùng trong run này.**

#### F5 — Complexity, resilience and common shocks (8 features, không đổi)

| Feature | Tổng quan | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `pci` | Product Complexity Index | `at_t` | ↓ |
| `importer_eci` | Economic Complexity Index nước đích | `at_t` | ↓ |
| `importer_diversity` | Đa dạng xuất khẩu nước đích | `at_t` | ↓ |
| `importer_lpi_overall` | Năng lực logistics tổng thể | `static` | ↓ |
| `importer_glpi` | Green logistics index (PCA) | `static` | ↓ |
| `gepu_current` | Global Economic Policy Uncertainty | `at_t` | ↑ |
| `cmo_all_commodities` | Giá hàng hóa thế giới tổng hợp | `at_t` | ? |
| `price_energy` | Cú sốc giá năng lượng | `at_t` | ↑ |

### 2.7bis. Feature nào biến mất vì scope EU27

Đây là phát hiện mới, không có ở `v1`, và đáng ghi lại vì nó ảnh hưởng trực tiếp tới cách đọc §5.4/§5.7.

Bộ lọc zero-variance của `Preprocessor` (`sd > 1e-12` trên train block) loại các cột sau khỏi **mọi** model khi fit trên fold 4 (train 2012–2021, đại diện):

| Feature | Vì sao trở thành hằng số trong mẫu EU27 |
|---|---|
| `contig` | Không nước EU27 nào chung biên giới với Việt Nam → luôn 0 |
| `comlang_off` | Không nước EU27 nào chung ngôn ngữ chính thức với Việt Nam → luôn 0 |
| `comcol` | Hằng số trong dữ liệu gravity hiện tại đối với cặp VN–EU27 |
| `wto_d` | Toàn bộ EU27 là thành viên WTO trong cửa sổ này → luôn 1 |
| `years_since_fta` | Hằng số trong mẫu này — bị thay thế đúng nghĩa bởi `years_since_evfta_policy`, biến EVFTA-specific mới thêm |
| **`evfta_cut_cum_pp_lag`** | **Bằng 0 ở mọi dòng của mọi train block**, vì EVFTA có hiệu lực 1/8/2020 và cả 4 fold đều có train window kết thúc ≤ 2020 (lag1 nghĩa là giá trị năm t−1, nên chỉ origin từ 2021 trở đi mới thấy cắt thuế > 0). Biến này **chỉ khác 0** ở valid/test block của fold 2 trở đi (ví dụ 10.563/26.091 dòng ở test fold 2, tới 22.822pp ở giá trị lớn nhất) — nhưng vì `keep_` được fit trên train rồi áp dụng nguyên cho valid/test, biến này bị loại khỏi toàn bộ pipeline của fold đó, kể cả ở test. **Kết luận: `evfta_cut_cum_pp_lag` chưa từng đóng góp vào bất kỳ model nào trong benchmark này** — đây là giới hạn cấu trúc của thiết kế fold hiện tại, không phải của bản thân biến. Muốn dùng được biến này cần một fold có train window vượt qua 8/2020 với đủ variation, hoặc một đặc tả model chấp nhận imputation khác cho cột hằng-số-trên-train. |
| `ntm_ave_border_pct` | Gần như hằng số giữa các cặp thị trường trong dữ liệu hiện tại (đã cảnh báo sẵn trong mô tả F4 gốc) |
| `ad_in_force` | Hiếm/hằng số trong lát cắt EU27+cửa sổ train này |

Hai biến EVFTA còn lại (`tariff_applied_lag`, `years_since_evfta_policy`) **sống sót** ở mọi fold và được model sử dụng thật.

Ngoài ra, một loạt cờ `_isna` (của các feature hầu như không missing trong EU27, ví dụ `log_gdp_d_lag_isna`, `hhi_market_isna`, `pci_isna`…) cũng bị loại vì hằng số 0 — đây chỉ là hệ quả bình thường của quy tắc `median+flag` khi cột nền không có missing trong lát dữ liệu nhỏ hơn, không phải phát hiện kinh tế.

### 2.8. Preprocessing chính

Không đổi so với `v1`: `log1p`/`log_clip1` giảm lệch phải; `clip_pct` chặn tỷ lệ tăng trưởng cực đoan; `median+flag` điền median học từ train; `zero`/`zero+flag` cho structural zero. Mọi tham số fit trên train fold rồi áp dụng cho validation/test.

---

## 3. Model

Không đổi so với `v1` — cùng 11 model, cùng registry model (`benchmark/models/`), chỉ preprocessor nhận `feature_registry_eu27.yaml` thay vì bản gốc.

### 3.1. Tổng số và cách phân loại

- **1 no-covariate baseline:** Kaplan–Meier.
- **4 statistical/traditional survival models:** CoxPH, CoxNet, Cloglog, Cloglog-theory.
- **2 tree-based survival ML models:** BoostedCox, RSF.
- **4 deep survival models:** DeepSurv, CoxTime, DeepHit, CBNN.

### 3.2. Ma trận giả định PH × tính phi tuyến

| | Proportional hazards (PH) | Non-proportional hazards (non-PH) |
|---|---|---|
| **Linear/traditional** | CoxPH, CoxNet, Cloglog | — |
| **Nonlinear/flexible** | BoostedCox, DeepSurv, Cloglog-theory | RSF, CoxTime, DeepHit, CBNN |

### 3.3. Các contrast được thiết kế trước

| Contrast | So sánh | Giả định được cô lập |
|---|---|---|
| A | CoxPH → BoostedCox / DeepSurv | Thêm nonlinearity nhưng giữ PH |
| B | DeepSurv → CoxTime | Bỏ PH nhưng giữ họ neural network |
| C | BoostedCox → RSF | Bỏ PH nhưng giữ họ tree |
| D | DeepHit/CoxTime → CBNN | Cho thời gian đi trực tiếp vào model |
| E | CoxPH → CoxNet | Chỉ thêm regularization |
| F | Cloglog → Cloglog-theory | Kiểm tra baseline truyền thống có bị làm straw man hay không |

---

## 4. Metrics

Công thức và quy tắc đọc **không đổi** so với `v1` (xem file gốc để tra công thức đầy đủ); chỉ số minh họa dưới đây cập nhật theo run EU27.

### 4.1–4.3. Brier / IBS

**Cách đọc mới:** Brier 1y = 0,0776 của RSF thấp hơn 0,1029 của Kaplan–Meier — chính xác hơn trên trung bình bình phương, không phải "chính xác 92,24%".

IBS 1–3 năm vẫn là metric chính. **Về IBS 1–5 năm: cửa sổ B0 ngắn hơn `v1` nên caveat còn chặt hơn.** Với `outcome_observed_through = 2025`, chỉ fold 1 (test 2018–2019) có đủ 5 năm follow-up cho origin muộn nhất của nó (2019+5=2024 ≤ 2025); fold 2–4 đều có ít nhất một phần test block vượt quá 2025 khi tích phân tới horizon 5. Engine vẫn trả về số (IPCW xử lý được censoring), nhưng **không nên so sánh IBS 1–5 giữa các fold ở bản EU27 này** — dùng IBS 1–3 làm chuẩn duy nhất, chặt hơn cả khuyến nghị gốc.

### 4.4. Antolini time-dependent concordance

**Ghi chú mới, riêng bản này:** ở fold 4 (test chỉ có năm 2024), mọi origin có `duration = 1` (một năm follow-up duy nhất tính tới `outcome_observed_through`), nên không tồn tại cặp $T_i<T_j$ nào để so sánh — Antolini C **= NaN cho toàn bộ 66 cell của fold 4** (11 model × 6 feature set). Đây là hệ quả toán học của test block một năm, không phải lỗi tính toán; ba fold còn lại tính Antolini bình thường (0% NaN).

**Cách đọc:** 0,8359 (RSF, full feature set) nghĩa là khoảng 83,59% comparable pairs được xếp đúng.

### 4.5. Cumulative/dynamic AUC

**Cách đọc mới:** AUC 3y = 0,8500 (RSF) nghĩa là một case và một control ngẫu nhiên có xác suất khoảng 85,00% được xếp đúng theo risk tại ba năm.

### 4.6. Expected Calibration Error

**Cách đọc mới:** ECE 3y = 0,0433 (RSF) nghĩa là khoảng cách tuyệt đối trung bình giữa xác suất dự báo và survival quan sát là 4,33 điểm phần trăm.

### 4.7. Paired spell bootstrap

Không đổi về công thức. Bootstrap 200 lần theo spell, báo cáo trên F0F1F2F3 và F0F1F2F3F4 (như `v1`).

---

## 5. Results

### 5.1. Quy tắc xếp hạng

Không đổi: mean IBS 1–3y qua bốn test folds, thấp hơn là tốt hơn.

### 5.2. Xếp hạng model theo từng tập feature

| Feature set | Xếp hạng theo IBS 1–3y, từ tốt đến kém |
|---|---|
| **F0** | RSF 0,0952 → CBNN 0,0972 ≈ DeepSurv 0,0972 → Cloglog 0,0973 ≈ Cloglog-theory 0,0973 → CoxPH 0,0974 → CoxNet 0,0985 → BoostedCox 0,0986 ≈ CoxTime 0,0986 → KM 0,1220 → DeepHit 0,1266 |
| **F0F1** | RSF 0,0866 → CBNN 0,0881 → DeepSurv 0,0887 → CoxPH 0,0900 → Cloglog 0,0903 → Cloglog-theory 0,0911 → BoostedCox 0,0915 → CoxNet 0,0917 → CoxTime 0,0918 → DeepHit 0,1171 → KM 0,1220 |
| **F0F1F2** | RSF 0,0871 → DeepSurv 0,0872 → CoxPH 0,0882 → Cloglog 0,0885 → CoxTime 0,0891 → Cloglog-theory 0,0892 → CBNN 0,0893 → BoostedCox 0,0902 → CoxNet 0,0935 → DeepHit 0,1048 → KM 0,1220 |
| **F0F1F2F3** | CBNN 0,0841 → Cloglog 0,0883 → RSF 0,0884 → Cloglog-theory 0,0891 → CoxPH 0,0892 → CoxNet 0,0906 → BoostedCox 0,0924 → KM 0,1220 → CoxTime 0,1803 → DeepHit 0,2277 → DeepSurv 0,2339 |
| **F0F1F2F3F4** | RSF 0,0885 → Cloglog 0,0888 → Cloglog-theory 0,0897 → CoxNet 0,0916 → CoxPH 0,0926 → BoostedCox 0,0931 → CBNN 0,0960 → CoxTime 0,1067 → KM 0,1220 → DeepSurv 0,1349 → DeepHit 0,2496 |
| **F0F1F2F3F4F5** | RSF 0,0872 → CoxNet 0,0912 → Cloglog 0,0918 → BoostedCox 0,0920 → Cloglog-theory 0,0926 → CoxPH 0,0938 → CBNN 0,0983 → CoxTime 0,1084 → DeepSurv 0,1095 → KM 0,1220 → DeepHit 0,1646 |

Đáng chú ý: ở **F0F1F2F3**, CoxTime và DeepSurv sụp đổ hẳn (0,18 và 0,23 IBS) — train block của fold 1 chỉ có 28.955 dòng, mẫu nhỏ nhất trong cả bốn fold, và các model neural với chỉ 1 seed/2 tuning trial dễ hội tụ kém khi thêm F3 (7 feature kinh nghiệm/portfolio) trên mẫu nhỏ này. Đây là artefact huấn luyện, không phải bằng chứng kinh tế rằng F3 "có hại" cho họ neural.

#### Model tốt nhất của từng feature set

| Feature set | #1 | #2 | Khoảng cách #1–#2 |
|---|---:|---:|---:|
| F0 | RSF 0,0952 | CBNN 0,0972 | 0,0020 |
| F0F1 | RSF 0,0866 | CBNN 0,0881 | 0,0015 |
| F0F1F2 | RSF 0,0871 | DeepSurv 0,0872 | 0,0001 |
| F0F1F2F3 | CBNN 0,0841 | Cloglog 0,0883 | 0,0043 |
| F0F1F2F3F4 | RSF 0,0885 | Cloglog 0,0888 | 0,0003 |
| Full F0–F5 | RSF 0,0872 | CoxNet 0,0912 | 0,0041 |

### 5.3. Full-feature leaderboard

| Model | IBS 1–3y ↓ | Brier 1y ↓ | Brier 3y ↓ | Antolini C ↑ | AUC 1y ↑ | AUC 3y ↑ | ECE 3y ↓ | Seconds/cell ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **RSF** | **0,0872** | **0,0776** | 0,0898 | 0,8359 | 0,8657 | 0,8500 | 0,0433 | 5 |
| CoxNet | 0,0912 | 0,0824 | 0,0935 | 0,8378 | 0,8666 | 0,8488 | **0,0354** | 1 |
| Cloglog | 0,0918 | 0,0845 | 0,0944 | 0,8397 | 0,8691 | 0,8495 | 0,0446 | 1 |
| BoostedCox | 0,0920 | 0,0823 | 0,0963 | 0,8369 | 0,8670 | 0,8497 | 0,0531 | 88 |
| Cloglog-theory | 0,0926 | 0,0844 | 0,0951 | 0,8402 | 0,8690 | 0,8497 | 0,0425 | 2 |
| CoxPH | 0,0938 | 0,0837 | **0,0898** † | 0,8415 | 0,8694 | **0,8551** | 0,0390 | 2 |
| CBNN | 0,0983 | 0,0866 | 0,0966 | 0,8144 | 0,8445 | 0,8214 | 0,1174 | 2 |
| CoxTime | 0,1084 | 0,0944 | 0,1094 | 0,7854 | 0,8174 | 0,7973 | 0,0661 | 1 |
| DeepSurv | 0,1095 | 0,1002 | 0,1021 | 0,8258 | 0,8496 | 0,8327 | 0,1732 | 5 |
| Kaplan–Meier | 0,1220 | 0,1029 | 0,1338 | 0,5000 | 0,5000 | 0,5000 | 0,0428 | 0 |
| DeepHit | 0,1646 | 0,1016 | 0,2676 | 0,7332 | 0,8165 | 0,4541 | 0,3183 | 16 |

† RSF thực chất có Brier 3y thấp nhất (0,0898, đồng mức với CoxPH ở 4 chữ số hiển thị) — hai model gần bằng nhau ở chỉ số này, không nên đọc thành "CoxPH thắng Brier 3y".

#### Cách đọc leaderboard

- **RSF vẫn là model tốt nhất theo IBS 1–3y và Brier 1y**, giống `v1`.
- **CoxNet có ECE 3y tốt nhất** (0,0354), không phải RSF — khác `v1`, nơi RSF dẫn đầu cả ECE 1y và 3y. Trên scope EU27 nhỏ hơn, RSF hiệu chuẩn tốt nhưng không còn là số 1 tuyệt đối ở mọi chỉ số calibration.
- **CoxPH có discrimination tốt nhất** (Antolini C 0,8415, AUC 3y 0,8551) — giống mô hình `v1` (nơi Cloglog-theory/CoxPH dẫn đầu C/AUC), củng cố lại thông điệp cũ: model IBS tốt nhất không nhất thiết là model discrimination tốt nhất.
- Khoảng cách Kaplan–Meier → RSF là 0,0348 IBS; RSF → CoxPH chỉ 0,0066. Phần lớn gain vẫn đến từ covariates, không phải model complexity — nhưng biên độ ở đây hẹp hơn `v1` (0,0388 và 0,0044 tương ứng), phù hợp với việc mẫu EU27 nhỏ và đồng nhất hơn nên ít "chỗ" cho model phức tạp thể hiện lợi thế.
- BoostedCox vẫn đắt nhất (88s/cell so với 1–5s của phần lớn model khác) mà không thắng RSF — cùng kết luận với `v1`: nếu ưu tiên chi phí, CoxNet là baseline rất cạnh tranh (chỉ kém RSF 0,004 IBS, rẻ hơn RSF ~5 lần và rẻ hơn BoostedCox ~88 lần).

### 5.4. Feature ablation: feature nào thực sự có ích?

| Model | F0 | +F1 | +F2 | +F3 | +F4 | +F5/full | Best set |
|---|---:|---:|---:|---:|---:|---:|---|
| RSF | 0,0952 | **0,0866** | 0,0871 | 0,0884 | 0,0885 | 0,0872 | F0F1 |
| CBNN | 0,0972 | 0,0881 | 0,0893 | **0,0841** | 0,0960 | 0,0983 | F0F1F2F3 |
| Cloglog | 0,0973 | 0,0903 | 0,0885 | **0,0883** | 0,0888 | 0,0918 | F0F1F2F3 |
| Cloglog-theory | 0,0973 | 0,0911 | 0,0892 | **0,0891** | 0,0897 | 0,0926 | F0F1F2F3 |
| CoxNet | 0,0985 | 0,0917 | 0,0935 | **0,0906** | 0,0916 | 0,0912 | F0F1F2F3 |
| CoxPH | 0,0974 | 0,0900 | **0,0882** | 0,0892 | 0,0926 | 0,0938 | F0F1F2 |
| BoostedCox | 0,0986 | 0,0915 | **0,0902** | 0,0924 | 0,0931 | 0,0920 | F0F1F2 |
| CoxTime | 0,0986 | 0,0918 | **0,0891** | 0,1803 | 0,1067 | 0,1084 | F0F1F2 |
| DeepSurv | 0,0972 | 0,0887 | **0,0872** | 0,2339 | 0,1349 | 0,1095 | F0F1F2 |
| DeepHit | 0,1266 | 0,1171 | **0,1048** | 0,2277 | 0,2496 | 0,1646 | F0F1F2 |

Kết luận ablation:

1. **F1 vẫn làm phần lớn công việc**, giống `v1`: mọi model giảm IBS đáng kể ngay khi thêm F1.
2. **F2 (gravity/macro) hữu ích hơn ở scope EU27 so với `v1`.** Sáu trong mười model đạt best score tại F0F1F2 (so với chỉ vài model ở `v1`) — hợp lý về mặt kinh tế: trong `v1`, F2 gần như vô ích một phần vì thị trường trải khắp thế giới, biến động GDP/lạm phát/tỷ giá đa dạng làm nhiễu tín hiệu; còn trong mẫu EU27 đồng nhất hơn (chung khối kinh tế, cùng đơn vị tiền tệ phần lớn), các biến gravity/macro có tín hiệu ổn định hơn.
3. **F3 vẫn có ích cho một nhóm nhỏ model** (CBNN, Cloglog, Cloglog-theory, CoxNet đạt best tại F0F1F2F3) nhưng **gây hại nghiêm trọng cho các model neural PH-based và DeepHit** (CoxTime, DeepSurv, DeepHit nhảy vọt IBS khi thêm F3) — như đã nói ở §5.2, nhiều khả năng là vấn đề hội tụ trên mẫu train nhỏ (fold 1 = 28.955 dòng) hơn là tín hiệu kinh tế thật.
4. **F4 và F5 (kể cả ba biến EVFTA mới) không cải thiện thêm cho bất kỳ model nào** — không model nào đạt best set ở F0F1F2F3F4 hoặc full. Điều này nhất quán với phát hiện ở §2.7bis: biến EVFTA mạnh nhất về mặt lý thuyết (`evfta_cut_cum_pp_lag`) chưa từng được dùng thật trong benchmark này.
5. **RSF là ngoại lệ đáng chú ý theo hướng ngược với `v1`:** ở `v1`, RSF đạt best tại F0–F4 (feature set rộng nhất trước F5); ở đây RSF đạt best chỉ tại **F0F1**, tập hẹp nhất sau F0. Trên mẫu nhỏ hơn ~6 lần, thêm nhiều feature chính sách/policy có vẻ làm RSF overfit thay vì khai thác được tín hiệu, ngược lại với vai trò "khai thác chọn lọc policy features tốt hơn model tuyến tính" mà `v1` từng ghi nhận.

### 5.5. Độ ổn định qua bốn temporal folds

IBS 1–3y trên full feature set:

| Model | Fold 1 (2018–19) | Fold 2 (2020–21, COVID) | Fold 3 (2022–23) | Fold 4 (2024) | Mean | Range max–min |
|---|---:|---:|---:|---:|---:|---:|
| CoxPH | 0,0985 | 0,1053 | 0,0931 | 0,0783 | 0,0938 | **0,0270** |
| CoxNet | 0,1020 | 0,1022 | 0,0913 | 0,0695 | 0,0912 | 0,0326 |
| BoostedCox | 0,1036 | 0,1007 | 0,0970 | 0,0665 | 0,0920 | 0,0372 |
| Cloglog-theory | 0,1019 | 0,1080 | 0,0913 | 0,0693 | 0,0926 | 0,0387 |
| Cloglog | 0,1018 | 0,1079 | 0,0919 | 0,0654 | 0,0918 | 0,0425 |
| KM | 0,1382 | 0,1314 | 0,1271 | 0,0911 | 0,1220 | 0,0471 |
| **RSF** | 0,0996 | 0,1012 | 0,0925 | 0,0553 | **0,0872** | 0,0459 |
| CoxTime | 0,1253 | 0,1299 | 0,1012 | 0,0773 | 0,1084 | 0,0526 |
| CBNN | 0,1383 | 0,1056 | 0,0901 | 0,0590 | 0,0983 | 0,0793 |
| DeepSurv | 0,1318 | 0,1596 | 0,0987 | 0,0480 | 0,1095 | 0,1117 |
| DeepHit | 0,3283 | 0,1341 | 0,1180 | 0,0779 | 0,1646 | 0,2504 |

#### Đánh giá stability

- Không model nào đứng đầu cả bốn fold. Fold winners: **CoxPH** ở fold 1, **BoostedCox** ở fold 2, **CBNN** ở fold 3, **DeepSurv** ở fold 4.
- **Khác biệt quan trọng so với `v1`: ở đây RSF không phải model có range nhỏ nhất.** CoxPH có range thấp nhất (0,0270), RSF chỉ đứng thứ bảy về độ ổn định (0,0459) dù có mean tốt nhất. `v1` từng nói "RSF ổn định nhất trong nhóm vừa cạnh tranh vừa không thất bại ở fold nào" — nhận định đó **không lặp lại được** trên scope EU27: RSF vẫn có mean tốt nhất nhưng đánh đổi bằng biến động fold-to-fold lớn hơn nhiều model PH tuyến tính.
- Toàn bộ leaderboard đều tốt hơn hẳn ở fold 4 (test 2024) so với ba fold trước — dễ gây hiểu lầm là "model học tốt hơn theo thời gian". Đọc thận trọng: fold 4 chỉ có 15.108 dòng test và test-block một năm (thay vì hai), nên phương sai của chính bản thân IBS trên fold này lớn hơn, và các đường cong survival cho origin 2024 có ít follow-up quan sát được nhất — con số thấp một phần phản ánh ít thông tin để phạt sai số hơn, không hẳn là model giỏi hơn thật.
- DeepHit ở fold 1 (0,3283) là một outlier rõ rệt so với chính nó ở ba fold còn lại (~0,12–0,13) — trùng với fold có train nhỏ nhất (28.955 dòng), cùng nguyên nhân hội tụ kém đã nêu ở §5.2/§5.4.

### 5.6. Paired bootstrap so với CoxPH

Trên feature set F0–F4, mean paired ΔIBS của RSF so với CoxPH là **−0,0041**.

| Fold | RSF − CoxPH | 95% CI | Diễn giải |
|---:|---:|---|---|
| 1 | −0,0002 | [−0,0013; 0,0009] | **Không có ý nghĩa thống kê** — CI chứa 0 |
| 2 | −0,0113 | [−0,0130; −0,0095] | RSF tốt hơn có ý nghĩa |
| 3 | +0,0019 | [0,0013; 0,0025] | RSF kém hơn có ý nghĩa |
| 4 | −0,0067 | [−0,0075; −0,0059] | RSF tốt hơn có ý nghĩa |

**Khác biệt so với `v1`:** ở `v1`, RSF thắng CoxPH có ý nghĩa ở cả 3 fold thắng (không fold nào "không ý nghĩa"). Ở bản EU27 này, fold 1 đảo thành **không có ý nghĩa thống kê** thay vì thắng — do mẫu fold 1 nhỏ hơn nhiều (train 28.955, test 24.923) nên khoảng tin cậy rộng hơn, không đủ sức phân biệt hai model. Tuyên bố đúng cho bản này: **RSF thắng CoxPH có ý nghĩa ở 2/4 fold, thua có ý nghĩa ở 1/4 fold (fold 3), và không phân biệt được ở 1/4 fold (fold 1)** — yếu hơn tuyên bố "thắng 3/4" của `v1`.

### 5.7. Kết quả của các contrast kiến trúc

| So sánh | ΔIBS | Cells cải thiện | Kết luận |
|---|---:|---:|---|
| CoxPH → BoostedCox | +0,0011 | 3/24 | Nonlinearity trong họ tree, giữ PH, không giúp — cùng chiều `v1` |
| CoxPH → DeepSurv | +0,0334 | 13/24 | Neural nonlinearity làm trung bình kém hơn nhiều, biên độ lớn hơn `v1` |
| DeepSurv → CoxTime | −0,0128 | 9/24 | Bỏ PH trong họ neural cho lợi ích yếu, không nhất quán — giống `v1` |
| **BoostedCox → RSF** | **−0,0041** | **20/24** | Vẫn là lợi ích nhất quán nhất: bỏ PH trong họ tree |
| DeepHit → CBNN | −0,0729 | 24/24 | CBNN mạnh hơn DeepHit ở **toàn bộ** 24 cells (còn dứt khoát hơn 23/24 của `v1`) |
| CoxPH → CoxNet | +0,0010 | 7/24 | Regularization riêng lẻ không tạo gain ổn định — giống `v1` |
| Cloglog → Cloglog-theory | +0,0007 | 7/24 | Spline/theory interactions không cải thiện trung bình — giống `v1` |

Ghi chú theo họ PH/non-PH trung bình (từ `ph_vs_nonph.csv`): ở **mọi** feature set, non-PH trung bình vẫn tệ hơn PH trung bình (chênh từ +0,0031 ở F0F1F2 tới +0,0368 ở F0F1F2F3F4) — vì trung bình này trộn cả RSF (rất tốt) với CoxTime/DeepHit/DeepSurv (kém, đặc biệt kém ở F3+). Contrast giữ kiến trúc gần nhau (bảng trên) vẫn là phép so sánh sạch hơn nhiều so với con số trung bình theo nhóm này.

### 5.8. Kết quả theo tuổi quan hệ

Trên F0–F4:

| Nhóm tuổi | Model tốt nhất | IBS | Model nhì | Nhận xét |
|---|---|---:|---|---|
| Tuổi 1 | **CBNN** | 0,1839 | RSF 0,1872 | Khác `v1` (RSF #1 ở tuổi 1) |
| Tuổi 2–3 | **Cloglog** | 0,1526 | Cloglog-theory 0,1529 | Khác `v1` (CBNN #1) |
| Tuổi 4+ | **Cloglog-theory** | 0,0491 | Cloglog 0,0492 | Khác `v1` (RSF #1) |

**RSF không dẫn đầu ở bất kỳ nhóm tuổi nào trên scope EU27**, dù vẫn luôn nằm trong top 3. Đây là khác biệt rõ so với `v1`, nơi RSF dẫn đầu cả tuổi 1 và tuổi 4+. Biên giữa model tốt nhất và kém nhất vẫn rất lớn ở tuổi 1 (khoảng 0,13, từ CBNN 0,1839 tới KM 0,3182) và co hẹp mạnh ở tuổi 4+ (khoảng 0,004) — cùng thông điệp với `v1`: **giá trị của model selection tập trung ở quan hệ mới**, nhưng model cụ thể nên chọn cho nhóm tuổi 1 khác với gợi ý của `v1`.

### 5.9. Kết quả theo giai đoạn trước/sau EVFTA

Trên F0–F4, chia theo `pre_evfta` (2012–2019), `covid` (2020–2021), `post_evfta` (2022–2024) — thay cho lát cắt "trước/sau COVID" chung chung của `v1`, phù hợp hơn với câu hỏi B0 vì tách rõ giai đoạn EVFTA đã trưởng thành (hậu 2022) khỏi giai đoạn COVID:

| Giai đoạn | Model tốt nhất | IBS | Model nhì | Kết luận |
|---|---|---:|---|---|
| Trước EVFTA (2012–2019) | **RSF** | 0,1002 | CoxPH 0,1005 | Gần như hòa — RSF nhỉnh hơn không đáng kể |
| COVID (2020–2021) | **CoxNet** | 0,0984 | RSF 0,1018 | RSF thua CoxNet ở giai đoạn sốc, giống thông điệp `v1` (RSF thua CoxPH ở COVID) |
| Hậu EVFTA (2022–2024) | **DeepSurv** | 0,0608 | CBNN 0,0658 | Hai model deep dẫn đầu rõ giai đoạn EVFTA đã trưởng thành — khác hẳn `v1` |

Không có bằng chứng rằng model càng flexible thì càng robust trước cú sốc (RSF/CoxNet vẫn tốt hơn các model neural ở giai đoạn COVID), nhất quán với `v1`. Nhưng phát hiện mới đáng chú ý: **ở giai đoạn hậu-EVFTA, hai model deep (DeepSurv, CBNN) dẫn đầu** — cần đọc thận trọng vì đây cũng chính là giai đoạn `evfta_cut_cum_pp_lag` mới bắt đầu có variation (§2.7bis) dù bản thân biến đó không được dùng, và vì post_evfta gộp cả fold 3 lẫn fold 4 (fold 4 vốn đã có IBS thấp bất thường do ít follow-up, xem §5.5) — **không nên vội kết luận "deep model học được cấu trúc EVFTA"** từ bảng này; cần permutation importance hoặc SHAP trên chính hai model này để xác nhận trước khi đưa vào Paper A.

### 5.10. Calibration

| Model | ECE 1y ↓ | ECE 3y ↓ |
|---|---:|---:|
| **CoxNet** | 0,0370 | **0,0354** |
| CoxPH | 0,0381 | 0,0390 |
| Cloglog-theory | 0,0399 | 0,0425 |
| Kaplan–Meier | 0,0189 | 0,0428 |
| RSF | **0,0215** | 0,0433 |
| Cloglog | 0,0401 | 0,0446 |
| BoostedCox | 0,0446 | 0,0531 |
| CoxTime | 0,0570 | 0,0661 |
| CBNN | 0,0518 | 0,1174 |
| DeepSurv | 0,1037 | 0,1732 |
| DeepHit | 0,0905 | 0,3183 |

- RSF tốt nhất ở ECE 1y nhưng **không** tốt nhất ở ECE 3y (CoxNet dẫn đầu) — khác `v1`, nơi RSF dẫn đầu cả hai.
- Kaplan–Meier vẫn hiệu chuẩn cạnh tranh dù discrimination bằng ngẫu nhiên: tốt hơn **7/10** covariate models ở ECE 3y (chỉ CoxNet, CoxPH, Cloglog-theory hiệu chuẩn tốt hơn KM; bảy model còn lại — RSF, Cloglog, BoostedCox, CoxTime, CBNN, DeepSurv, DeepHit — đứng dưới) — vẫn giữ thông điệp cốt lõi của `v1`: **calibration tốt không đồng nghĩa individualized prediction tốt**, nhưng tỷ lệ cụ thể (7/10, không phải 9/10) khác đi vì bảng leaderboard đổi thứ hạng.
- DeepHit vẫn lệch tệ nhất (ECE 3y = 0,3183, tệ hơn cả `v1`'s 0,0824) — đây là model duy nhất mà khoảng cách với `v1` nới rộng thay vì thu hẹp, có thể vì mẫu EU27 nhỏ hơn làm discrete-time PMF của DeepHit khó ước lượng ổn định hơn.

### 5.11. Kết luận cuối cùng về kết quả

1. **Model nên chọn cho run `eu27_v1`:** vẫn RSF nếu ưu tiên IBS 1–3 năm thuần túy, nhưng biên lợi thế với CoxPH thu hẹp hơn `v1` (0,0066 so với 0,0044 tuyệt đối, nhưng CI ở một fold không còn phân biệt được hai model — §5.6). Nếu ưu tiên **ổn định qua thời gian và calibration 3 năm**, CoxPH/CoxNet là lựa chọn hợp lý hơn RSF trên scope này.
2. **Baseline production/benchmark nên giữ:** CoxNet — rẻ (1s/cell), hiệu chuẩn tốt nhất (ECE 3y), IBS chỉ kém RSF 0,004.
3. **Feature set hợp lý nhất đổi theo model**, không có một câu trả lời chung: RSF tốt nhất ở F0F1 (hẹp nhất), CBNN/Cloglog/Cloglog-theory/CoxNet tốt nhất ở F0F1F2F3, CoxPH/BoostedCox/CoxTime/DeepSurv/DeepHit tốt nhất ở F0F1F2. **Không model nào trong run này đạt best set khi thêm F4 hoặc F5** — bao gồm cả ba biến EVFTA mới.
4. **Biến EVFTA treatment mạnh nhất về lý thuyết (`evfta_cut_cum_pp_lag`) chưa hề được kiểm chứng dự báo**, vì hằng số trên mọi train block hiện tại (§2.7bis). Đây là việc cần làm trước khi dùng benchmark này làm bằng chứng ủng hộ/bác bỏ vai trò dự báo của cường độ cắt thuế EVFTA.
5. **Không có bằng chứng deep learning thắng classical survival**, đúng như `v1`, và trên mẫu nhỏ hơn thì các model neural PH-based (CoxTime, DeepSurv) còn dễ tổn thương hơn khi thêm feature (F3+) trên fold có train nhỏ.
6. **Kết luận kiến trúc mạnh nhất không đổi:** non-PH có ích trong họ tree (BoostedCox→RSF, 20/24 cells), không phải nonlinearity nói chung.
7. **Tính ổn định đảo ngược một phần so với `v1`:** RSF có mean tốt nhất nhưng range fold-to-fold lớn hơn cả CoxPH/CoxNet/BoostedCox/Cloglog(-theory) — không còn là model "vừa tốt vừa ổn định" như `v1` từng kết luận.
8. **Giới hạn cần giữ khi diễn giải:** RSF và BoostedCox vẫn bị cap ở 8.000 train rows/cell (không đổi so với `v1`, và vẫn bind vì mọi train block ở đây đã ≥ 28.955 dòng); mỗi deep model vẫn chỉ 1 seed, 2–3 tuning trials; validation vẫn chỉ tối ưu Brier 1 năm; **và mới:** fold 4 có test block một năm nên Antolini C không tính được ở đó, IBS 1–5 chỉ đáng tin ở fold 1, và biến EVFTA-cut-cum chưa từng được model sử dụng. Đây là bằng chứng so sánh V1 của scope B0, không phải performance ceiling của model nào, và chưa phải bằng chứng identification (B6) — chỉ là bước dự báo/feature-model selection mà B0 gọi là B7.

### 5.12. Giới hạn và khác biệt so với `v1` — tóm tắt

| # | Khác biệt | Vì sao |
|---|---|---|
| 1 | Mẫu: EU-27×2012–2024 (156.557 origins) thay vì 147 nước×2003–2023 (778.971) | Đúng scope B0 đã chốt; `v1` vô tình dùng mẫu robustness (147 nước, B0 §"mẫu mở rộng") làm mẫu chính |
| 2 | F4 có thêm 3 biến EVFTA thật (`tariff_applied_lag`, `evfta_cut_cum_pp_lag`, `years_since_evfta_policy`) | Các cột này đã có sẵn trong panel nhưng chưa từng đăng ký vì registry gốc phải hợp lệ cho cả 147 nước |
| 3 | 4 fold rolling-origin nén trong 2012–2024, fold 4 test chỉ 1 năm (2024) | Cửa sổ B0 ngắn hơn `v1` (13 năm origin so với 21 năm) |
| 4 | Antolini C = NaN toàn bộ fold 4 | Test block một năm → mọi `duration=1` → không có cặp $T_i<T_j$ |
| 5 | `evfta_cut_cum_pp_lag` hằng số 0 trên mọi train block, chưa từng được model dùng | EVFTA có hiệu lực 8/2020, mọi train window kết thúc ≤ 2020 |
| 6 | Một số dummy gravity/WTO/FTA-chung (`contig`, `comlang_off`, `comcol`, `wto_d`, `years_since_fta`) trở thành hằng số, bị loại khỏi model | Mẫu chỉ còn EU27 nên các thuộc tính phân biệt "trong/ngoài nhóm" không còn biến thiên |
| 7 | RSF không còn là model ổn định nhất/dẫn đầu mọi nhóm tuổi/calibration 3y tốt nhất | Mẫu nhỏ hơn ~6 lần → phương sai model-to-model và fold-to-fold lớn hơn tương đối |
| 8 | Kết luận định tính cốt lõi (RSF#1 theo IBS, F1 quan trọng nhất, non-PH-trong-tree là contrast mạnh nhất, DeepHit tệ nhất) **không đổi** | Cấu trúc bài toán và phương pháp luận benchmark giữ nguyên qua rescope |

---

## Nguồn đối chiếu

- [`SRT_Benchmark_Structured_Review.md`](SRT_Benchmark_Structured_Review.md) — báo cáo `v1` (scope 147 nước, đã xác định là lệch B0)
- [`Stage1_Research_Framework.md`](Stage1_Research_Framework.md) — khung nghiên cứu, khối B0 chốt scope EU27/2012–2024/EVFTA
- [`benchmark/config/benchmark_eu27.yaml`](benchmark/config/benchmark_eu27.yaml) — config đóng băng cho run này
- [`benchmark/config/splits_eu27.yaml`](benchmark/config/splits_eu27.yaml) — biên fold
- [`benchmark/features/feature_registry_eu27.yaml`](benchmark/features/feature_registry_eu27.yaml) — feature registry (F4 mở rộng EVFTA)
- [`benchmark/features/eu27_scope.py`](benchmark/features/eu27_scope.py) — filter EU27 theo năm
- [`docs/DU_LIEU_EVFTA_VA_THUE_EU.md`](docs/DU_LIEU_EVFTA_VA_THUE_EU.md) — nguồn gốc và kiểm chứng dữ liệu EVFTA staging/thuế EU
- [`benchmark/runs/eu27_v1/`](benchmark/runs/eu27_v1/) — 264 cell JSON + `metrics.parquet`
- [`benchmark/reports/`](benchmark/reports/) — leaderboard/ablation/contrasts/subgroups/bootstrap CSV + figures cho run này; bản `v1` gốc lưu riêng ở [`benchmark/reports/v1_global/`](benchmark/reports/v1_global/)
