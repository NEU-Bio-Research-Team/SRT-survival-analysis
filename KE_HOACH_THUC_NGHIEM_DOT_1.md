# Kế hoạch thực nghiệm đợt đầu — benchmark survival trên panel Stage 1 v2

Ngày: 27/09/2026. Dựa trên `SRT_Stage1_Literature_Experiment_Design_VI.md`
(bản rà soát 26/09/2026, dưới đây gọi là **doc thiết kế**), panel v2 tại commit
`672e0a9` và benchmark legacy tại `dbae191`.

**Trạng thái: kế hoạch, chưa chạy.** Phiên soạn thảo không có
`stage1_panel.parquet`. Mọi con số hiệu năng dẫn ở đây là số legacy đã lưu. Mọi
số lượng fit là ước lượng trước eligibility gate, có thể giảm sau Đợt 0.

---

## 0. Một màn hình

Doc thiết kế giữ nguyên: 16 mô hình (D01–D06, L01–L10), 8 gói feature (S1–S8),
12 nhóm câu hỏi (C01–C12). Kế hoạch này **không bỏ model nào và không bỏ gói
feature nào**. Nó chỉ bỏ những *hoán vị* không trả lời câu hỏi nào.

Cách làm: thay lưới đầy đủ 16 × 8 bằng **thiết kế neo + chéo** (anchor + cross).

- **Trục method:** cả 16 model chạy trên một gói neo duy nhất là **S4** (D+R+M+E+P).
- **Trục feature:** cả 8 gói chạy trên **5 model đại diện**: D01 cloglog, D05
  boosted, L02 CoxNet, L05 RSF và L07 DeepSurv. Năm model này phủ ba hành vi:
  tuyến tính, cây và neural.
- Hai trục cắt nhau ở ô S4, nên mọi kết quả nối được với nhau qua ô neo.
- Sàng lọc chỉ chạy trên **một fold phát triển** và chỉ đọc **validation**. Test
  chỉ mở cho shortlist đã đóng băng.

| | Doc thiết kế (core đầy đủ) | Kế hoạch này (Đợt 1–3) |
|---|---:|---:|
| Cấu hình model × feature ở sàng lọc | 128 (Screening32 là tập con) | **51** (+22 tùy chọn) |
| Model được phủ / gói được phủ | 16 / 8 | **16 / 8** |
| Ô model ngẫu nhiên cần tune (config × fold) | 192 | ≈ 95 (+10) |
| Lượt tune ước tính | ≈ 2.900–3.800 (15–20 trial/ô) | ≈ 1.150 (+150) |
| Fit (config × fold × seed), chưa gồm tune | 768, **chưa gồm** robustness | ≈ 310, **đã gồm** C05/C06/C09/C10 và LOBO |

Năm đợt:

| Đợt | Việc | Số cấu hình | Phụ thuộc |
|---|---|---:|---|
| 0 | Cổng kiểm tra: profile, view D/L/I, registry, test rò rỉ, tái lập adapter, pilot runtime | — | — |
| 1 | Sàng lọc phủ: 16 model @S4 + 5 model × 7 gói còn lại | 51 (+22) | Đợt 0 |
| 2 | Xác nhận shortlist trên 3 fold (test + seed); LOBO | 27 × 3 fold; 16 | Đợt 1 |
| 3 | Câu hỏi trọng tâm C05/C06/C07/C09/C10 trên 4 model đại diện | 54 | Đợt 2 |
| 4 | Nhánh suy luận I: M0–M3, frailty, RE, EVFTA (C03/C04/C07/C08) | 16 đặc tả | **chỉ cần Đợt 0**, chạy song song |
| 5 (để sau) | C11, phần còn lại của C12, model extension, fold final 2023 | — | Đợt 2–3 |

---

## 1. Vì sao giảm được mà không mất thông tin

### 1.1. Bằng chứng từ benchmark legacy eu27_v4

Đây là số lưu trữ, không phải benchmark sạch (doc thiết kế §7): GLPI/NTM còn lỗi
timing, mỗi họ chỉ tune 2–3 trial, chạy 1 seed, cap sample không đều. Vì vậy chỉ
dùng để định hướng thiết kế, không dùng để kết luận.

- Ở F0F1, 6 model đứng đầu chỉ cách nhau ≈ 0,005 IBS 1–3 (RSF 0,0977 … CBNN
  0,1024).
- Đổi feature set làm IBS của **cùng một model** dao động mạnh hơn: RSF F0 → F0F1
  giảm 0,0072; DeepSurv F0F1 → full tăng 0,0108; CoxTime F0F1 → full tăng 0,0256.
- Thứ hạng thay đổi theo feature set: RSF đứng đầu ở F0F1, CBNN đứng đầu ở full.
- DeepHit có IBS 0,13–0,21 ở mọi set. Đó là dấu hiệu của tuning hoặc
  discretization, chưa phải kết luận về kiến trúc.

Từ đó rút ra ba hệ quả cho thiết kế:

1. Trục feature cần phủ đủ 8 gói, nhưng chỉ trên ít model (Track B).
2. Có tương tác model × feature, nên mỗi hành vi (tuyến tính / cây / neural) cần
   một đại diện đi hết trục feature. Các model còn lại cần ít nhất 2–3 điểm
   (thin sweep).
3. Khoảng cách giữa các model nhỏ, nên **không loại model theo thứ hạng thô**.
   Shortlist chọn theo family, theo cặp đối chiếu và theo CI paired.

### 1.2. Bảy quy tắc giảm

1. **Phủ, không nhân chéo.** Mỗi model có ít nhất 1 ô, mỗi gói có ít nhất 5 ô,
   và hai trục gặp nhau ở ô neo.
2. **Một fold phát triển cho sàng lọc.** Ba fold chỉ dành cho shortlist.
3. **Seed chỉ nhân ở refit/test của model ngẫu nhiên trong shortlist.** Không
   nhân seed khi tune, không nhân seed cho model tất định.
4. **Horizon 1/2/3(/5) đọc từ cùng một đường survival.** Không fit riêng từng
   horizon.
5. **Robustness theo kiểu một-yếu-tố-một-lúc (OFAT)** quanh cấu hình gốc. Ví dụ
   threshold/gap dùng 5 target thay vì 9.
6. **Robustness chỉ chạy trên 4 model đại diện**, chọn bằng quy tắc viết trước
   khi xem kết quả.
7. **Câu hỏi trả lời được bằng prediction đã lưu thì không fit lại** (phân tầng
   first/recurrent, known-start, từng horizon).

---

## 2. Quyết định cố định trước khi chạy

| Mục | Giá trị | Ghi chú |
|---|---|---|
| Scope | EU27 (B0) | broad147 để dành cho C11 |
| Target | `exit_gap1_threshold10000_v1` (panel v2) | chỉ C09 mới đổi |
| Task | D (rủi ro 1 năm), L (landmark H1–3), I (suy luận) | mỗi task một leaderboard |
| Fold phát triển | **F2 — test origin 2020** | D: validation origin 2017, label cutoff 2016, outcome tới 2019. L: validation origin 2015, cutoff 2014, outcome tới 2019 (bảng §8.2 doc thiết kế) |
| Training origins | từ 2005 (lịch sử 2002–2004 dùng để dựng covariate) | báo riêng với biến thể training ≥ 2012 |
| Metric chính | D: Brier 1y. L: IPCW IBS 1–3 | tuning dùng đúng metric này |
| Metric phụ | như §8.4 doc thiết kế | |
| Reference | D: age-only empirical hazard. L: KM. Cả hai fit lại ở mỗi fold | báo Brier skill = 1 − IBS/IBS_ref |
| So sánh | paired bootstrap theo relation importer × family, B = 1.000 | không t-test giữa các fold |
| Sample budget | `full_eligible` cho mọi model | nếu pilot buộc phải cap thì ghi cap vào manifest; C12 đo lại |
| Ties / time grid | Cox dùng Efron; grid năm 1..5; event ở biên thuộc interval trước | chốt trong `tasks.yaml` |
| Missing | imputer + missing indicator fit trong train fold | **không bao giờ điền 0** cho unreported / no-history |

**Vì sao chọn F2.** Validation của cả D và L đều kết thúc ở 2019, tức trước
COVID, và đủ follow-up cho H1–3. Test origin 2020 không bị chạm tới trong lúc
sàng lọc. F1 và F3 chỉ dùng để xác nhận.

**Ngân sách tuning:**

| Họ | Model | Đợt 1 | Đợt 2 (mỗi fold mới) |
|---|---|---|---|
| GLM link | D01, D02, D03 | không tune (hoặc ridge λ ∈ {0; 1e-3; 1e-2}) | như Đợt 1 |
| Flexible cloglog | D04 | spline df ∈ {3; 5} × {không tương tác; X×age cho 5 biến R/P} = 4 | như Đợt 1 |
| Linear PH | L01, L02 | L01 không tune. L02: l1_ratio ∈ {0,1; 0,5; 0,9} × đường λ tự động | như Đợt 1 |
| AFT | L03, L04 | penalizer ∈ {0; 0,01; 0,1} | như Đợt 1 |
| Cây / boosting | D05, L05, L06 | 15 trial | 15 trial |
| Neural | D06, L07–L10 | 15 trial + early stopping | 15 trial |

**Quy tắc hội tụ.** Nếu trial tốt nhất nằm trong 25% trial cuối, cộng thêm 15
trial trước khi chốt shortlist. Quy tắc này nhắm trước hết vào L09 DeepHit. Mọi ô
đều lưu đường best-vs-budget.

---

## 3. Đợt 0 — cổng kiểm tra

Không fit model zoo nào trước khi cả 6 mục dưới đây pass.

| # | Việc | Pass khi |
|---|---|---|
| 0.1 | Profile v2 | Tái lập được số audit: 932.204 dòng, 189.830 spell, 112.885 event; B0 có 146.042 dòng / 15.958 event. Có bảng count/missingness/variation theo origin × block |
| 0.2 | Dựng view D / L / I | Nhãn được cắt theo cutoff. Origin được chọn bằng trade quan sát được ≥ ngưỡng (không dùng `gap_filled`). Hàng có kết cục năm sau **chưa xác nhận thì bị mask**, không coi là event = 0 — nhất là 14.958 dòng EU27 năm 2024. Cả cohort phải thỏa L + h + g ≤ D, không chỉ những hàng đã biết sống. Có cờ incident / recurrent / known-start |
| 0.3 | Feature registry + as-of | Mỗi feature có grain, công thức, `available_at` và `missing_semantics` (theo mẫu YAML §10.2 doc thiết kế). Có bảng eligibility S1–S8 × fold gồm rows, events và % block có giá trị as-of |
| 0.4 | Test rò rỉ và nhãn | Pass 10 kiểm tra ở §10.3 doc thiết kế, đặc biệt: thêm năm tương lai vào nguồn không làm đổi feature/nhãn ở cutoff cũ, và không cột outcome-derived nào lọt vào X |
| 0.5 | Tái lập adapter | KM, CoxNet, RSF và cloglog với feature đơn giản trên 3 fold legacy; mọi sai khác so với eu27_v4 đều được giải thích |
| 0.6 | Pilot runtime | 16 model × S4 × 1 trial trên F2: đo thời gian, RAM, khả năng hội tụ, rồi chốt budget và quyết định có cần cap không |

**Eligibility của block phụ (N, C, L, H).** Một block đủ điều kiện ở một fold
nếu ≥ 50% số hàng train có giá trị as-of và block đó không hằng trong train.
Ngưỡng 50% là tham số config, được kiểm lại ở C10. Block không đạt thì gói tương
ứng được ghi "ineligible" kèm lý do. Không impute cả một block không tồn tại.

### 3.1. Bản nháp ánh xạ block → cột (chốt lại trong registry ở 0.3)

| Block | Cột panel v2 / cần dựng | Loại trừ |
|---|---|---|
| D | tuổi spell quan sát được tại origin, log tuổi, bin tuổi; `known_start` = (`start_reason` rỗng) | `spell_end_year`, `t_stop`, và mọi thống kê trên cả spell |
| R | `log_value` của năm origin (hợp lệ vì exit bắt đầu từ năm sau), `log_value_lag`, initial observed value (**dựng**), `vn_market_share_pct_lag1`, `volatility_3y_lag1`; `unit_value_usd_per_kg_lag1` là tùy chọn | |
| M | `log_gdp_d_lag1`, `log_gdpcap_d_lag1`, `importer_gdp_growth_pct_lag1`, `importer_inflation_pct_lag1`, `log_total_import_cp_lag1`, `log_dist` | không đưa `log_pop_d_lag1` cùng hai biến GDP vào model tuyến tính không phạt; biến gravity hằng trong EU27 bị loại theo fold |
| E | `n_products_to_c_lag1`, `n_markets_for_p_lag1` + bản đếm riêng EU27 (**dựng**), `hs2_share_lag1`, `rca_lag`, `growth_lag_pct` (tăng trưởng product của VN, không phải bilateral), `world_growth_pct_lag1` | `hhi_market`, `hhi_product` (tính trên cả rổ VN, không phải HHI có điều kiện) |
| P | `tariff_applied_lag`, `pref_margin_lag`, `evfta_cut_cum_pp_lag` | `tariff_mfn_pct_lag1` (đồng nhất thức MFN = applied + margin), `tariff_rate_lag1` (trùng), `years_since_evfta_policy` (chỉ là lịch) |
| N | log1p của `ntm6_sps_inforce`, `ntm6_tbt_inforce`, other = all − sps − tbt; tuổi nguồn; `ntm6_observed`, `ntm6_mappable`. Chỉ dùng khi `ntm6_source_year` ≤ origin | `ntm_*` (snapshot cấp nước), `ntm_ave_*` có source year > origin |
| C | `pci`, `importer_eci`, `importer_diversity`, khi source year ≤ origin | |
| L | `importer_lpi_overall` (hoặc các components) và tuổi khảo sát, khi `importer_lpi_source_year` ≤ origin | mọi `importer_glpi_*` (EPI 2026 cross-section + PCA fit trên toàn dữ liệu) |
| H | **dựng mới**: số spell trước đã kết thúc và xác nhận, thời gian từ lần exit trước, số năm hoạt động trong prefix, bilateral growth, trend 3 năm, HHI có điều kiện (product-destination, importer-product) | |

---

## 4. Đợt 1 — sàng lọc phủ toàn bộ method và feature set

Chạy trên fold F2, chỉ đọc validation, seed 1.

### 4.1. Track A — quét method trên gói neo S4 (16 cấu hình)

Mỗi model D01–D06 và L01–L10 có một ô ở S4. Vì cùng một nền, Track A trả lời
ngay được:

- **C02 (phi tuyến):** L02 so với L05/L06/L07; D01 so với D04/D05/D06.
- **C03 (PH):** L07 DeepSurv so với L08 CoxTime (cùng thiết kế neural); D01 so với
  D04 (có tương tác X×age); L02 so với L03/L04 (AFT).
- **Kiểm tra link:** D01/D02/D03 được kỳ vọng cho kết quả gần trùng. Lệch nhiều
  thì nghi lỗi pipeline trước.

**Vì sao chọn S4 làm neo.** S4 là gói lớn nhất không dính vấn đề availability
(N/C/L/H thì đều có). Nó cũng là nền mà S5–S8 cộng thêm vào, nên ô neo đồng thời
là baseline cho mọi so sánh block phụ.

### 4.2. Track B — quét feature trên 5 model đại diện (35 cấu hình)

{D01, D05, L02, L05, L07} × {S1, S2, S3, S5, S6, S7, S8}. Ô S4 của năm model này
đã có trong Track A.

| Đại diện | Task | Hành vi | Vì sao |
|---|---|---|---|
| D01 cloglog | D | tuyến tính, grouped-PH | baseline của D, và là cầu nối sang nhánh I |
| D05 boosted | D | phi tuyến, cây | ML chính cho rủi ro một năm |
| L02 CoxNet | L | tuyến tính có phạt | baseline của L, tự lọc biến |
| L05 RSF | L | cây, không giả định PH | legacy: ổn định nhất khi thêm feature |
| L07 DeepSurv | L | neural | legacy: xuống cấp mạnh khi thêm feature — đúng tương tác cần đo |

Track B trả lời **C01 đầy đủ** cho cả ba hành vi: thang S1 → S4, S4 so với
S5/S6/S7 theo từng block, và S8 gộp tất cả.

### 4.3. Đợt 1b — thin sweep (22 cấu hình, khuyến nghị)

11 model còn lại × {S1, S8}. Nhờ vậy mỗi model có 3 điểm (hẹp – neo – rộng) và
đọc được tương tác model × độ rộng feature.

- 12 ô tất định (D02, D03, D04, L01, L03, L04) gần như miễn phí — **nên chạy
  luôn**.
- 10 ô ngẫu nhiên (D06, L06, L08, L09, L10) chạy nếu pilot 0.6 cho phép.
- Nếu S8 ineligible thì thay bằng gói rộng nhất còn eligible.

### 4.4. Ma trận phủ

`A` = Track A, `B` = Track B, `b` = thin sweep tất định, `b*` = thin sweep ngẫu
nhiên (tùy chọn), `·` = không chạy trong đợt đầu.

| Model | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| D01 Cloglog | B | B | B | **A** | B | B | B | B |
| D02 Logit | b | · | · | **A** | · | · | · | b |
| D03 Probit | b | · | · | **A** | · | · | · | b |
| D04 Flexible cloglog | b | · | · | **A** | · | · | · | b |
| D05 Boosted hazard | B | B | B | **A** | B | B | B | B |
| D06 MLP hazard | b* | · | · | **A** | · | · | · | b* |
| L01 CoxPH | b | · | · | **A** | · | · | · | b |
| L02 CoxNet | B | B | B | **A** | B | B | B | B |
| L03 Weibull AFT | b | · | · | **A** | · | · | · | b |
| L04 Log-normal AFT | b | · | · | **A** | · | · | · | b |
| L05 RSF | B | B | B | **A** | B | B | B | B |
| L06 GB-Cox | b* | · | · | **A** | · | · | · | b* |
| L07 DeepSurv | B | B | B | **A** | B | B | B | B |
| L08 CoxTime | b* | · | · | **A** | · | · | · | b* |
| L09 DeepHitSingle | b* | · | · | **A** | · | · | · | b* |
| L10 CBNN | b* | · | · | **A** | · | · | · | b* |

**So với Screening32 của doc thiết kế** (S1–S4 × 8 model): Đợt 1 phủ 16 model
thay vì 8 và 8 gói thay vì 4. Chỉ 6 ô của Screening32 không có ở đây (D02, D06,
L10 × S2, S3). Ba model đó vẫn có S1 trong Đợt 1b.

### 4.5. Registry thí nghiệm (nháp cho `stage2_benchmark/configs/experiments.yaml`)

```yaml
batch1:
  fold: F2
  evaluate_on: validation        # test origin 2020 chưa mở
  seeds: [1]
  cells:
    - id: A_method_sweep
      feature_sets: [S4]
      models: [D01, D02, D03, D04, D05, D06,
               L01, L02, L03, L04, L05, L06, L07, L08, L09, L10]
      questions: [C02, C03]
    - id: B_feature_sweep
      feature_sets: [S1, S2, S3, S5, S6, S7, S8]
      models: [D01, D05, L02, L05, L07]
      questions: [C01]
    - id: b_thin_deterministic
      feature_sets: [S1, S8]
      models: [D02, D03, D04, L01, L03, L04]
    - id: b_thin_stochastic
      optional: true
      feature_sets: [S1, S8]
      models: [D06, L06, L08, L09, L10]
```

### 4.6. Đầu ra của Đợt 1

- Hai bảng validation (D và L) cho Track A, có Δ so với reference và CI paired.
- Heatmap 5 model × 8 gói (Track B); ô ineligible ghi rõ lý do.
- Bảng runtime/RAM, đường best-vs-budget, và cờ "chưa hội tụ".

---

## 5. Quy tắc chốt shortlist — viết trước khi xem kết quả

Shortlist được chốt ở một commit riêng, trước khi mở bất kỳ test origin nào.

**Model.** Luôn giữ các cặp đối chiếu, bất kể thứ hạng, vì chúng trả lời những
câu hỏi đã đăng ký trước:

- **D:** D01 (baseline), D04 (cho C03), D05 (cho C02), cộng model có Brier
  validation @S4 tốt nhất trong {D02, D03, D06} → **4 model**.
- **L:** L02 (baseline), cặp L07 và L08 (PH/non-PH, cho C03), cộng 2 model có IBS
  validation @S4 tốt nhất trong {L01, L03, L04, L05, L06, L09, L10} → **5
  model**.
- Model mang cờ "chưa hội tụ" phải được bổ sung budget trước khi xếp hạng. Không
  loại một model chỉ vì một lần tune ít trial.

**Gói feature.** Dùng {S1, S4, S★}. S★ là gói có thứ hạng validation trung bình
tốt nhất trên các đại diện cùng task, chọn trong các gói eligible thuộc {S2, S3,
S5, S6, S7, S8} → 3 gói.

**L★** là model phi tuyến đại diện cho Đợt 3: model phi tuyến có IBS validation
@S4 tốt nhất trong shortlist L. Nếu hòa (CI paired chứa 0) thì chọn L05 RSF vì rẻ
và ổn định.

---

## 6. Đợt 2 — xác nhận

### 6.1. Shortlist trên 3 fold

(4 + 5) model × 3 gói = **27 cấu hình**, chạy trên F1/F2/F3 theo protocol §8.2
của doc thiết kế: tune trên validation origin của từng fold, refit ở cutoff, rồi
dự báo test origin.

- F2 dùng lại kết quả tune của Đợt 1. F1 và F3 tune độc lập, 15 trial mỗi ô.
  Không mượn hyperparameter từ fold muộn hơn: F2 đọc outcome tới 2019, muộn hơn
  cutoff của F1.
- Model ngẫu nhiên chạy 3 seed ở bước refit + test.
- Horizon 5 chỉ báo trên F1 (test origin 2019), để ở bảng riêng.

Đầu ra (khớp bước 7 ở §10.4 doc thiết kế):

- một leaderboard cho mỗi task;
- bảng feature increment S1 → S4 → S★ kèm CI paired;
- bảng giả định mô hình (tuyến tính/phi tuyến × PH/non-PH).

### 6.2. Leave-one-block-out (16 cấu hình)

Chạy trên validation F2, chỉ khi S8 eligible: từ S8 bỏ lần lượt R, M, E, P, N, C,
L, H, trên {L02, L★}. Thêm D05 × 8 nếu còn compute. Mục đích là đo phần thông tin
riêng của từng block khi các block khác đã có mặt.

---

## 7. Đợt 3 — câu hỏi trọng tâm trên 4 model đại diện

R4 = {D01, D05, L02, L★}. Chạy trên validation F2. Hyperparameter khởi đầu từ ô
gốc; model ngẫu nhiên được tune bổ sung 6 trial.

| Câu hỏi | Biến thể | Model | Gói | Số ô |
|---|---|---|---|---:|
| C05 selection | elastic-net stability; consensus ≥ 3/4 từ 4 selector fit trong inner train (CoxNet ≠ 0, permutation RSF, gain boosting, Wald cloglog) | R4 | S8 (hoặc gói rộng nhất còn eligible) | 8 |
| C06 timing / lịch sử | (a) lag-only thay cho current + lag; (b) cửa sổ lịch sử 5 năm thay cho 3; (c) S4 + H | R4 | S4 | 12 |
| C07 first / recurrent | **không fit mới**: đánh giá phân tầng prediction đã lưu theo first vs recurrent và known-start vs unknown-start. Phần tương tác nằm ở Đợt 4 (I11) | — | — | 0 |
| C09 định nghĩa survival | OFAT quanh (10k, gap 1): 5k·gap1, 50k·gap1, 10k·gap0, 10k·gap2 | D01 và L02 ở S1 + S4; D05 và L★ ở S4 | | 24 |
| C10 coverage / vintage | (a) S4 và S5 trên subset có NTM; S4 và S7 trên subset có LPI. (b) probe rò rỉ: S5 lenient (giữ snapshot NTM có source year tương lai) | L02, L★ | | 10 |
| | | | **Tổng** | **54** |

- **C09 phải dựng lại spell từ raw.** Trong `build_spells.py`, `THRESHOLD_USD` và
  `GAP_TOLERANCE` là hằng số, nên cần tham số hóa; phần threshold có thể tận dụng
  `spell_threshold_sensitivity.py`. Gap 0 và gap 2 làm đổi lịch xác nhận
  L + h + g ≤ D, nên `splits.yaml` phải dựng lại cho từng gap. Metric tuyệt đối
  giữa các target không so được với nhau. Chỉ so: tỷ lệ event và KM, thứ hạng
  model, dấu và độ lớn tương đối của increment S1 → S4.
- **Probe rò rỉ ở C10(b) chỉ là chẩn đoán, không bao giờ vào leaderboard.** Nó đo
  xem các số legacy có thể đã bị thổi phồng bao nhiêu.

---

## 8. Đợt 4 — nhánh suy luận I (song song, chỉ cần Đợt 0)

Dùng view person-period trên B0 (EU27), chỉ gồm những interval có kết cục đã xác
nhận (origin ≤ 2023). Tuổi spell tính từ lịch sử 2002. Mẫu chính là các spell
known-start. Không tái dùng model thắng leaderboard: đặc tả và likelihood viết lại
từ đầu.

| # | Đặc tả | Câu hỏi |
|---|---|---|
| I1–I5 | Pooled cloglog, duration dummies + D / S1 / S2 / S3 / S4 | thang M0–M3 (B5 của framework) |
| I6–I7 | Cloglog với shared gamma frailty theo relation importer × family, ở S1 và S4 | C04 |
| I8–I9 | RE logit và RE probit @S4 | C04; đối chiếu Besedeš/Lejour |
| I10 | S4 + X × log(age) | C03 phía suy luận |
| I11 | S4 + tương tác recurrent spell và known-start | C07 |
| I12 | Event study: preference margin / cường độ cắt thuế × 1[t − 2020 = k], FE importer, HS2 và năm | C08, B6 của framework |
| I13 | Cường độ cắt thuế × (incumbent trước EVFTA vs entrant); năm 2020 tách thành năm chuyển tiếp | C08 |
| I14 | Placebo: giả định EVFTA hiệu lực 2017 | C08 |
| I15–I16 | Chạy lại I5 và I7 trên toàn bộ spell (kể cả unknown-start) | độ nhạy theo left truncation |

- **Standard error:** two-way cluster theo importer và HS2. Vì chỉ có 27 cluster
  importer, thêm wild cluster bootstrap.
- **Diễn giải:** hệ số là association, trừ khi đặc tả nhận diện được chứng minh.
  SHAP và feature importance không dùng làm bằng chứng nhân quả.

---

## 9. Để sau (Đợt 5)

- **C11:** broad147, leave-country-out, holdout HS4, cohort COVID/EVFTA — chạy
  trên L02 và L★.
- **C12:** full-data vs equal-row (cap 8.000 như legacy) cho L05/L06; calibrated
  vs raw trên heldout; độ phân tán theo seed.
- **Model extension** (LogisticHazard, PCHazard, DSM, SurvTRACE): mỗi model vào
  qua Track A (1 ô @S4), và chỉ vào xác nhận nếu vượt model tốt nhất cùng family.
  Với thiết kế neo, chi phí thêm một model chỉ tăng tuyến tính.
- **Fold final H1, test origin 2023** (validation 2020, refit cutoff 2022): chạy
  một lần với shortlist đã đóng băng. Chỉ gọi là untouched nếu nhóm chưa từng
  dùng cohort này để ra quyết định.

---

## 10. Bảng đếm

Giả định shortlist có 2 model ngẫu nhiên ở D và 4 model ngẫu nhiên ở L.

| Đợt | Cấu hình | Fold | Fit (config × fold × seed) | Ô ngẫu nhiên cần tune | Trial ước tính |
|---|---:|---|---:|---:|---:|
| 1 core | 51 | F2 | 51 | 29 | ≈ 435 |
| 1b | 22 | F2 | 22 | 10 | ≈ 150 (tùy chọn) |
| 2 xác nhận | 27 | F1, F2, F3 | ≈ 190 | 36 (chỉ ở F1, F3) | ≈ 540 |
| 2 LOBO | 16 | F2 | 16 | 8 | ≈ 50 |
| 3 | 54 | F2 | 54 | ≈ 23 | ≈ 140 |
| **Tổng (không kể 1b)** | | | **≈ 310** | **≈ 95** | **≈ 1.150** |
| 4 suy luận | 16 đặc tả | toàn bộ B0 | 16 | — | — |

Đối chiếu với doc thiết kế: riêng phần core đã là 768 fit và khoảng 2.900–3.800
trial (192 ô ngẫu nhiên × 15–20 trial), **chưa tính** robustness C04–C12.

---

## 11. Cố ý không chạy trong đợt đầu

| Không chạy | Lý do |
|---|---|
| 55 ô còn lại của lưới 128 (11 model ngoài đại diện × S2, S3, S5, S6, S7) | tương tác model × feature đã đọc được qua 5 đại diện + thin sweep |
| 3 fold cho mọi cấu hình | 3 fold chỉ dành cho 27 cấu hình trong shortlist |
| Seed cho model tất định; seed trong lúc tune | không tạo thêm thông tin |
| Lưới đầy đủ 3 × 3 threshold × gap | OFAT dùng 5 target thay vì 9 |
| Fit riêng cho từng horizon H1/H3/H5 | đọc từ cùng một đường survival |
| GLPI, snapshot NTM, CBAM, thuế Mỹ 2025, TTBD sau 2015 làm predictor | timing/coverage không hợp lệ (§4.3 doc thiết kế) |
| Competing risks "upgrade vs failure" | Stage 1 không có nguyên nhân exit đã kiểm chứng |
| GRU / LSTM / Dynamic-DeepHit | cần chuỗi historical covariate và masking chưa có |

---

## 12. Hai điều phải biết trước khi đọc kết quả

1. **EVFTA không có biến thiên trong train của mọi fold dự báo.** Với F1–F3,
   train của D dừng ở origin ≤ 2018 và của L ở origin ≤ 2019. Ngay cả fold final
   2023 thì train của D cũng chỉ tới origin 2020. Vì lịch cắt thuế bắt đầu
   1/8/2020, `evfta_cut_cum_pp_lag` bằng 0 ở mọi hàng train và bị loại trong fold
   như một biến hằng. Do đó increment của block P trong C01 thực chất đo **mức
   thuế áp dụng và biên ưu đãi GSP/MFN, không đo EVFTA**. Tác động của EVFTA chỉ
   trả lời được ở Đợt 4 (I12–I14), nơi mẫu B0 có đủ các năm 2020–2023.
2. **Số legacy chỉ để định hướng.** Chúng có vấn đề timing ở GLPI/NTM, tune 2–3
   trial, 1 seed và cap sample không đều. S1 mới cũng không phải bản sao của
   F0F1 cũ. Không có kết quả nào của kế hoạch này được coi là đã biết trước khi
   Đợt 2 xong.

---

## 13. Thứ tự thực thi

| Bước | Việc | Chuyển tiếp khi |
|---|---|---|
| 1 | Đợt 0 | cả 6 mục pass |
| 2a | Đợt 1 core + phần tất định của 1b | có đủ bảng validation và runtime; không còn lỗi pipeline |
| 2b | Đợt 4, song song với 2a | có bảng M0–M3, frailty và event study |
| 3 | Chốt shortlist bằng commit riêng | quy tắc §5 được áp dụng máy móc, không chỉnh tay |
| 4 | Đợt 2 | có leaderboard 3 fold cho mỗi task |
| 5 | Đợt 3 | có bảng robustness cho từng câu hỏi |
| 6 | Báo cáo | mỗi task một leaderboard, bảng feature increment, bảng giả định, phần limitations |

Có thể chia hai người chạy song song: một người lo nhánh benchmark (Đợt 1 → 2 →
3), một người lo nhánh kinh tế lượng (Đợt 4). Hai nhánh chỉ dùng chung Đợt 0.

Code đặt ở `notebook/stage2_benchmark/` theo cấu trúc §10.2 của doc thiết kế.
Stage 1 giữ nguyên, không sửa.
