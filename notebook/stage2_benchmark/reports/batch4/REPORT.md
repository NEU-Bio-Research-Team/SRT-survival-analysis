# Đợt 4 — Nhánh suy luận I (B0 EU27, person-period)

Mẫu: dòng active EU27, origin 2012–2023, kết cục 1 năm đã xác nhận với dữ liệu tới 2025. Mẫu chính = spell known-start. Covariate **chỉ lag** (explanatory mode), chuẩn hoá trên mẫu; missing → median + cờ. Hệ số cloglog = log hazard ratio **trên 1 SD**. SE chính: cluster hai chiều importer × HS2 (CGM). Wild score bootstrap (Webb, 999) một chiều theo importer (27) và theo HS2 (~96) chỉ là kiểm tra bổ sung. **Mọi hệ số là association**, trừ khi có lập luận nhận diện riêng.

## I1–I5: thang M0–M3 (pooled cloglog, dummy tuổi 1..10+)

| | I1 D | I2 S1 | I3 S2 | I4 S3 | I5 S4 | I15 S4 (mọi spell) |
|---|---:|---:|---:|---:|---:|---:|
| n / events | 98,097 / 15,405 | 98,097 / 15,405 | 98,097 / 15,405 | 98,097 / 15,405 | 98,097 / 15,405 | 131,016 / 15,958 |
| log-lik | -35760.1 | -34665.4 | -34582.6 | -32907.5 | -32810.8 | -35038.9 |
| #params | 10 | 16 | 22 | 34 | 38 | 38 |
| HR `log_value_lag` |  | 0.556*** | 0.633*** | 0.695*** | 0.695*** | 0.646*** |
| HR `log_initial_value` |  | 0.869*** | 0.873*** | 0.859*** | 0.859*** | 0.833*** |
| HR `vn_market_share_lag1` |  | 1.167*** | 0.989 | 0.942** | 0.945** | 0.918*** |
| HR `volatility_3y_lag1` |  | 1.106*** | 1.135*** | 1.120*** | 1.121*** | 1.120*** |
| HR `log_gdp_d_lag1` |  |  | 1.050 | 1.073 | 1.092 | 1.099 |
| HR `log_gdpcap_d_lag1` |  |  | 0.978 | 1.011 | 1.016 | 1.010 |
| HR `log_total_import_cp_lag1` |  |  | 0.816*** | 0.854*** | 0.853*** | 0.829*** |
| HR `log_n_products_to_c_lag1` |  |  |  | 0.724*** | 0.716*** | 0.714*** |
| HR `log_n_markets_eu27_for_p_lag1` |  |  |  | 0.751*** | 0.747*** | 0.751*** |
| HR `log_rca_lag` |  |  |  | 0.938*** | 0.926*** | 0.916*** |
| HR `tariff_applied_lag` |  |  |  |  | 1.032* | 1.028 |
| HR `pref_margin_lag` |  |  |  |  | 0.919*** | 0.927*** |

HR trên 1 SD; `*` p < 0,1, `**` < 0,05, `***` < 0,01 (cluster hai chiều).

## I6–I9, I16, I7p: dị biệt ẩn theo relation (C04)

| spec | mẫu | nhóm | tham số RE | log-lik (pooled) | LR vs pooled | ghi chú |
|---|---|---:|---|---|---:|---|
| I6 cloglog + shared gamma frailty (relation) @S1 | known-start | 20,975 | θ = 4.46e-13 | -34665.4 (-34665.4) | 0.000 (p = 0.50) | max 4 spell chết/relation |
| I7 cloglog + shared gamma frailty (relation) @S4 | known-start | 20,975 | θ = 3.16e-11 | -32810.8 (-32810.8) | 0.000 (p = 0.50) | max 4 spell chết/relation |
| I7p cloglog + shared gamma frailty, parametric baseline (log age, log age^2) @S4 | known-start | 20,975 | θ = 1.98e-03 | -32802.0 (-32802.0) | 0.011 (p = 0.46) | max — spell chết/relation |
| I16 cloglog + shared gamma frailty (relation) @S4 | all spells | 23,799 | θ = 9.44e-03 | -35038.8 (-35038.9) | 0.258 (p = 0.31) | max 4 spell chết/relation |
| I8 random-intercept logit (relation) @S4 | known-start | 20,975 | σ_u = 9.72e-07, ρ = 2.9e-13 | -32724.5 (-32724.5) | 0.000 | |
| I9 random-intercept probit (relation) @S4 | known-start | 20,975 | σ_u = 4.63e-07, ρ = 2.1e-13 | -32676.3 (-32676.3) | 0.000 | |

**Đọc:** phương sai frailty/intercept ngẫu nhiên theo relation hội tụ về biên 0 trong mọi đặc tả, kể cả khi baseline là tham số (I7p) thay vì dummy tự do. Nên hệ số pooled và hệ số frailty trùng nhau. Sau khi kiểm soát sức mạnh quan hệ (giá trị lag, giá trị khởi đầu, biến động) thì **không còn dị biệt ẩn đáng kể ở cấp importer × family**. Kết luận này không có nghĩa quan hệ đồng nhất: phần dị biệt đã được covariate quan sát hấp thụ. Phương pháp của I6/I7 là likelihood frailty đúng (tích phân dạng đóng); đã kiểm chứng trên dữ liệu mô phỏng (θ = 0,8 → ước lượng 0,83).

## I10: effect có đổi theo tuổi spell không? (C03 phía suy luận)

Wald chung cho 5 tương tác X × log(tuổi): χ² = 285.1, df = 5, p = 1.6e-59.

| tương tác | hệ số | SE 2 chiều | p |
|---|---:|---:|---:|
| log_value_lag_x_logage | -0.214 | 0.024 | 0.000 |
| vn_market_share_lag1_x_logage | -0.025 | 0.031 | 0.414 |
| tariff_applied_lag_x_logage | +0.003 | 0.019 | 0.856 |
| pref_margin_lag_x_logage | -0.011 | 0.016 | 0.491 |
| log_initial_value_x_logage | +0.197 | 0.018 | 0.000 |

Giả định PH theo tuổi **bị bác bỏ** cho hai biến R: tác động bảo vệ của giá trị lag mạnh lên theo tuổi, còn của giá trị khởi đầu yếu đi theo tuổi (hệ số dương). Biến thuế quan không có tương tác đáng kể.

## I11: spell tái gia nhập và spell không rõ điểm bắt đầu (C07)

| hạng tử | hệ số | SE 2 chiều | p |
|---|---:|---:|---:|
| recurrent | -0.127 | 0.036 | 0.000 |
| unknown_start | -0.356 | 0.112 | 0.002 |
| recurrent_x_log_value_lag | -0.032 | 0.023 | 0.171 |
| unknown_start_x_log_value_lag | -0.321 | 0.050 | 0.000 |
| recurrent_x_log_initial_value | +0.017 | 0.019 | 0.388 |
| unknown_start_x_log_initial_value | +0.007 | 0.072 | 0.922 |
| recurrent_x_vn_market_share_lag1 | +0.006 | 0.045 | 0.890 |
| unknown_start_x_vn_market_share_lag1 | -0.052 | 0.090 | 0.561 |

Wald tương tác recurrent: p = 0.51; unknown-start: p = 2.2e-12.

## I12–I14: EVFTA (C08)

Cường độ = mức cắt thuế EVFTA tích luỹ tới 2023 theo lộ trình Annex 2-A của family (chuẩn hoá, 1 SD = 4.19 điểm %). Event time theo **năm kết cục** (t + 1 − 2020), tham chiếu = năm kết cục 2019. FE importer, HS2, năm kết cục; dummy tuổi + lag R.

| k | hệ số | SE 2 chiều | p 2 chiều | p wild (importer) | p wild (HS2) |
|---|---:|---:|---:|---:|---:|
| -7 | +0.011 | 0.075 | 0.879 | 0.814 | 0.844 |
| -6 | +0.026 | 0.072 | 0.722 | 0.649 | 0.607 |
| -5 | -0.029 | 0.071 | 0.680 | 0.540 | 0.530 |
| -4 | -0.001 | 0.075 | 0.994 | 0.992 | 0.991 |
| -3 | -0.023 | 0.081 | 0.774 | 0.610 | 0.739 |
| -2 | -0.057 | 0.081 | 0.481 | 0.365 | 0.143 |
| +0 | -0.025 | 0.066 | 0.706 | 0.588 | 0.624 |
| +1 | -0.045 | 0.109 | 0.682 | 0.628 | 0.410 |
| +2 | -0.119 | 0.084 | 0.155 | 0.039 | 0.059 |
| +3 | -0.173 | 0.087 | 0.048 | 0.002 | 0.008 |
| +4 | -0.129 | 0.069 | 0.062 | 0.007 | 0.002 |

Pre-trend (k ≤ −2) Wald: p = 0.92. Post (k = 1..4) Wald: p = 0.27.

**I13** — cloglog: intensity × {transition 2020, post 2021+} × (entrant: spell start ≥ 2020); FE importer, HS2, outcome year (known-start):

| hạng tử | hệ số | p 2 chiều | p wild HS2 |
|---|---:|---:|---:|
| intensity_x_transition | -0.014 | 0.730 | 0.628 |
| intensity_x_post | -0.104 | 0.065 | 0.016 |
| entrant_x_post | -0.059 | 0.452 | 0.270 |
| intensity_x_post_x_entrant | -0.011 | 0.841 | 0.777 |

**I14** — placebo: EVFTA dated 2017; intensity × 1[outcome year ≥ 2017] (known-start, outcome years ≤ 2019):

| hạng tử | hệ số | p 2 chiều | p wild HS2 |
|---|---:|---:|---:|
| intensity_x_fakepost2017 | -0.026 | 0.440 | 0.198 |

**Đọc (thận trọng):** không có pre-trend và placebo 2017 bằng 0, nên thiết kế qua được hai kiểm tra cơ bản. Family có mức cắt thuế lớn hơn có hazard exit thấp hơn từ năm kết cục 2022 (k = +2..+4, khoảng −0,12 đến −0,17 log-HR trên 1 SD). Tuy nhiên kiểm định chung sau EVFTA với SE hai chiều không có ý nghĩa (p ≈ 0,27), và từng hệ số chỉ ở mức biên (p ≈ 0,05–0,15). Wild bootstrap một chiều cho p nhỏ hơn nhưng bỏ qua chiều cluster còn lại. Lộ trình cắt thuế cố định từ trước, nhưng các ngành cắt nhiều cũng có thể trùng với cú sốc hậu COVID riêng của ngành. Kết luận: **có dấu hiệu gợi ý, chưa đủ để khẳng định nhân quả**. Category A chiếm 93% kim ngạch, nên biến thiên nhận diện dựa trên phần đuôi (TU_DIEN §7b).

