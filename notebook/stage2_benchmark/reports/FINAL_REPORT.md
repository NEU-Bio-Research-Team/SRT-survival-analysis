# Báo cáo tổng hợp — Đợt 0–4 (kế hoạch `KE_HOACH_THUC_NGHIEM_DOT_1.md`)

Ngày 28/09/2026. Panel Stage 1 v2 (sha256 `e480392d…`), scope EU27 (B0), target
`exit_gap1_threshold10000_v1`. Branch `stage2/batch1`. Mọi con số dưới đây trích từ
các báo cáo con, có link ở từng mục; CI là bootstrap paired theo relation
(importer × family), B = 1.000.

| Đợt | Nội dung | Ô / spec | Lỗi | Báo cáo |
|---|---|---:|---:|---|
| 0 | 6 cổng kiểm tra | — | 0 | [stage0/README.md](stage0/README.md) |
| 1 | Sàng lọc F2 (validation) | 82 (69 done, 13 ineligible) | 0 | [batch1/REPORT.md](batch1/REPORT.md) |
| — | Shortlist (commit riêng `fea0975`) | — | — | [shortlist/SHORTLIST.md](shortlist/SHORTLIST.md) |
| 2 | Xác nhận 3 fold, test 2019/2020/2021 | 151 | 0 | [batch2/REPORT.md](batch2/REPORT.md) |
| 2 | LOBO | 27 | 0 | [batch2_lobo/REPORT.md](batch2_lobo/REPORT.md) |
| 3 | C05/C06/C07/C09/C10 | 66 | 0 | [batch3/REPORT.md](batch3/REPORT.md), [batch2/C07_strata.md](batch2/C07_strata.md) |
| 4 | Nhánh suy luận I1–I16 (+ I7p) | 17 | 0 | [batch4/REPORT.md](batch4/REPORT.md) |

## 1. Leaderboard (test, trung bình 3 fold, gói tốt nhất của mỗi model)

**Task D — xác suất exit 1 năm (Brier 1y, thấp hơn tốt hơn).** Tham chiếu age-only 0,0827.

| # | model | gói | Brier 1y | skill | Δ vs D01 @S4 |
|---|---|---|---:|---:|---|
| 1 | D06 MLP hazard | S6 | 0,07397 | 0,106 | (S4: −0,00043 [−0,00074, −0,00014]*) |
| 2 | D04 flexible cloglog | S6 | 0,07418 | 0,103 | (S4: −0,00028 [−0,00047, −0,00009]*) |
| 3 | D05 boosted hazard | S6 | 0,07432 | 0,102 | (S4: −0,00020 [−0,00059, +0,00018]) |
| 4 | D01 cloglog | S6 | 0,07445 | 0,100 | — |

**Task L — đường sống sót tại landmark (IPCW IBS 1–3).** Tham chiếu KM 0,1308.

| # | model | gói | IBS 1–3 | skill | Δ vs L02 @S4 | IBS 1–5 (F1) |
|---|---|---|---:|---:|---|---:|
| 1 | L09 DeepHitSingle | S6 | 0,09181 | 0,298 | −0,00308 [−0,00362, −0,00253]* | 0,1043 |
| 2 | L05 RSF | S6 | 0,09256 | 0,292 | −0,00269 [−0,00323, −0,00209]* | 0,1049 |
| 3 | L07 DeepSurv | S6 | 0,09332 | 0,286 | −0,00172 [−0,00213, −0,00127]* | 0,1051 |
| 4 | L08 CoxTime | S6 | 0,09389 | 0,282 | −0,00076 [−0,00110, −0,00044]* | 0,1063 |
| 5 | L02 CoxNet | S6 | 0,09415 | 0,280 | — | 0,1074 |

Thứ hạng giữ nguyên ở cả 3 fold; SD giữa 3 seed ≤ 0,0007, nhỏ hơn khoảng cách giữa các model.
C_td và td-AUC gần như bằng nhau giữa các model (C_td 0,850–0,853): phần hơn kém nằm ở
**calibration theo thời gian**, không ở khả năng xếp hạng.

## 2. Feature increment (C01)

| bước | D (Brier, test gộp 3 fold) | L (IBS, test gộp 3 fold) |
|---|---|---|
| S1 → S4 | −0,0048 đến −0,0051, mọi model * | −0,0033 (CoxNet) đến −0,0066 (DeepHit), mọi model * |
| S4 → S6 (+ complexity) | −0,0001 đến −0,0002 (chỉ D01 *) | −0,0012 CoxNet *, ≈ 0 RSF/DeepSurv |

Phân rã trong Đợt 1 (validation F2) và LOBO:
- **Block E (kinh nghiệm/danh mục) là bước tăng lớn nhất** (S2 → S3: −0,004 đến −0,006), và bỏ E khỏi gói rộng làm mọi model kém đi (+0,0017 đến +0,0030 *).
- **Block R (sức mạnh quan hệ) là block không thể thiếu** (LOBO: +0,0037 đến +0,0050 *).
- **M (gravity/vĩ mô) và P (thuế quan) gần như không có thông tin riêng.** P đúng như kế hoạch §12 dự báo: `evfta_cut_cum_pp_lag` bằng 0 ở mọi dòng train nên P chỉ còn mức thuế và biên GSP.
- **N (NTM) không eligible** cho L ở mọi fold và cho D ở F1 (NTM có từ 2010). Trên subset có NTM (C10a) N không thêm gì.
- **C (complexity), L (logistics)** chỉ giúp model tuyến tính (CoxNet: C +0,0009 *, L +0,0011 * trong LOBO); model cây/neural đã tự học phần này.
- **H (lịch sử sâu)**: giúp nhẹ D05 (−0,0004 *), làm L02/L05 kém nhẹ (+0,0002 đến +0,0004 *) (C06c).

## 3. Giả định mô hình (C02, C03)

| câu hỏi | bằng chứng | kết luận |
|---|---|---|
| C02 phi tuyến, task D | D05/D06 vs D01: −0,0002 đến −0,0004 | có nhưng rất nhỏ; cloglog tuyến tính gần tối ưu cho rủi ro 1 năm |
| C02 phi tuyến, task L | DeepSurv vs CoxNet −0,0017 *; RSF −0,0027 * | có, rõ ràng |
| C03 PH, neural | CoxTime vs DeepSurv: +0,0013 * (Đợt 1), CoxTime kém hơn ở test | bỏ PH qua time-input không giúp |
| C03 PH, cây | RSF vs GB-Cox −0,0040 * (Đợt 1) | bỏ PH giúp trong họ cây |
| C03 PH, suy luận | I10: X × log(tuổi) Wald p ≈ 1e-59 | PH theo tuổi bị bác bỏ cho giá trị lag (+ mạnh dần) và giá trị khởi đầu (− yếu dần) |
| AFT | Weibull/log-normal AFT +0,0054 * vs CoxNet | dạng tham số quá cứng cho dữ liệu này |
| link D | logit/probit − cloglog ≤ 0,0001 | không phân biệt được — kiểm tra pipeline pass |

## 4. Các câu hỏi robustness

- **C04 dị biệt ẩn (Đợt 4)**: θ gamma frailty và σ RE logit/probit theo relation → 0 trong mọi đặc tả, kể cả baseline tham số. Sau khi kiểm soát covariate không còn dị biệt ẩn đáng kể ở cấp relation.
- **C05 lựa chọn biến**: enet-stability và consensus ≥ 3/4 giữ ~22/42 cột. Không cải thiện có ý nghĩa ở model nào; với D05 còn làm kém nhẹ (+0,0005 *). Model có phạt/cây đã tự chọn.
- **C06 timing**: bỏ giá trị trade năm hiện tại (lag-only) làm mọi model kém rõ (+0,0017 đến +0,0031 *). Cửa sổ lịch sử 5 năm thay 3 năm: ≈ 0.
- **C07 first vs recurrent, known- vs unknown-start**: model có ích ở mọi tầng. Ví dụ DeepHit so với KM: skill 0,36 ở spell đầu, 0,20 ở spell tái gia nhập. I11: spell tái gia nhập có hazard thấp hơn (−0,13 log-HR *), không khác về độ dốc của covariate.
- **C09 định nghĩa survival**: ngưỡng 5k/50k và gap 0/2 làm tỷ lệ exit B0 đổi từ 7,9% đến 16,7%, nhưng **dấu của increment S1 → S4 giữ nguyên ở mọi target** và RSF vẫn tốt hơn CoxNet. Ngoại lệ duy nhất: với gap 0, increment của CoxNet không còn có ý nghĩa (−0,0007, CI chứa 0).
- **C10 coverage/vintage**: probe lenient (NTM có source year tương lai) cải thiện CoxNet −0,0007 *. Đây là mức mà một benchmark không kiểm soát as-of có thể bị thổi phồng. Probe chỉ để chẩn đoán, không vào leaderboard.
- **C08 EVFTA (Đợt 4)**: không có pre-trend (p = 0,92), placebo 2017 bằng 0. Family có cắt thuế nhiều hơn có hazard exit thấp hơn ở năm kết cục 2022–2024 (−0,12 đến −0,17 log-HR / SD). Nhưng Wald chung hậu EVFTA với SE hai chiều không có ý nghĩa (p = 0,27). **Có dấu hiệu gợi ý, chưa đủ để khẳng định nhân quả.**

## 5. Quyết định lệch khỏi bản nháp và lý do

1. **Censor hành chính tại H = C − g** cho mọi dòng. Quy tắc legacy censor death chưa xác nhận sớm hơn người sống, tức censoring phụ thuộc kết cục ([0.5](stage0/0.5_adapter_reproduction.md)).
2. **Block N dùng `ntm6_*_survey`**, không dùng `ntm6_*_inforce`: `inforce` gộp cả đợt thu thập sau origin.
3. **Early stopping trên holdout nội bộ của train** (theo relation), không trên cohort validation đang chấm.
4. **RSF**: giữ full rows, thu hẹp không gian (pilot 308 s/trial → ~60 s). **GB-Cox** dùng XGBoost `survival:cox`, bỏ được cap 8.000 dòng của legacy.
5. **Gói thay thế khi S8 ineligible = S8 bỏ block không đạt (S8-N)**; LOBO cho L dùng gốc S8-N.
6. **S★ chọn trong các gói eligible ở cả F1–F3** (Đợt 2 chạy 3 fold).
7. Event study đặt event time theo **năm kết cục** (t + 1), vì origin 2019 có kết cục trong năm EVFTA 2020.
8. Chạy song song khi RAM cho phép: GPU worker cho model neural, khóa theo ô để không chạy trùng.

## 6. Giới hạn

- Test origin 2019–2021 **đã được dùng trong report legacy**, nên chỉ là development/reproduction, không phải holdout mới. Fold final 2023 (Đợt 5) chưa chạy.
- Calendar-time backtest: chưa có vintage công bố đầy đủ cho mọi nguồn (design doc §4.4).
- EVFTA không có biến thiên trong train của F1–F3; block P trong C01 không đo EVFTA.
- Đơn vị là quan hệ importer × family tổng hợp, không phải doanh nghiệp.
- C09: ở ngưỡng 5k, dòng 5–10k thiếu các cột thị phần/tổng nhập khẩu cấp quan hệ (lấy từ panel 10k) → missing + cờ. Covariate của bản dựng lại (10k, gap 1) khớp panel ở 20/25 cột, lệch 1–6% dòng ở 5 cột.
- Ba ô Đợt 1 còn cờ "chưa hội tụ" sau 45 trial (ghi trong SHORTLIST). DeepHit (L09) thường chạm 100 epoch.
- Wild bootstrap một chiều cho p nhỏ hơn SE hai chiều. Suy luận chính dùng SE hai chiều.
- Để sau (Đợt 5): C11 (broad147, leave-country-out, HS4 holdout), C12 (equal-row, calibration, budget), model extension, fold final 2023.
