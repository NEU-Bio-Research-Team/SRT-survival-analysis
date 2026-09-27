# Shortlist (quy tắc §5, áp dụng máy móc)

Nguồn: batch1, F2 validation. Code `9b8406cf863c9cf84a04dd6ad10aec9879bcf7b8-dirty`.

## Model

- D: cố định D01, D04, D05; tốt nhất trong {D02, D03, D06} theo Brier @S4: D06 0.07811, D02 0.07845, D03 0.07852 → **D06**
- L: cố định L02, L07, L08; hai tốt nhất trong {L01, L03, L04, L05, L06, L09, L10} theo IBS @S4: L09 0.09891, L05 0.09931, L10 0.10124, L01 0.10263, L06 0.10333, L03 0.10829, L04 0.10841 → **L09, L05**

- Cờ 'chưa hội tụ' còn lại sau +15 trial: không có

## Gói feature — task D

Gói eligible ở cả F1–F3: ['S2', 'S3', 'S6', 'S7']. Hạng trung bình trên ['D01', 'D05']: S6 1.00, S3 2.50, S7 2.50, S2 4.00 → **S★ = S6**

## Gói feature — task L

Gói eligible ở cả F1–F3: ['S2', 'S3', 'S6', 'S7']. Hạng trung bình trên ['L02', 'L05', 'L07']: S6 1.67, S7 1.67, S3 2.67, S2 4.00 → **S★ = S6**

## L★ (đại diện phi tuyến cho Đợt 3)

Ứng viên phi tuyến: L07 0.10109, L08 0.10237, L09 0.09891, L05 0.09931
→ **L★ = L05** (L09 tốt nhất nhưng CI paired so với L05 chứa 0 (-0.00040 [-0.00117, +0.00033]) → L05)

## Kết quả

- D: ['D01', 'D04', 'D05', 'D06'] × ['S1', 'S4', 'S6']
- L: ['L02', 'L07', 'L08', 'L09', 'L05'] × ['S1', 'S4', 'S6']
- R4 cho Đợt 3: ['D01', 'D05', 'L02', 'L05']

Đã ghi `configs/shortlist.yaml`. Commit riêng trước khi mở test origin.

## Ghi chú biên bản

- Bổ sung budget (plan §5) trước khi xếp hạng: ba ô còn cờ "chưa hội tụ" sau quy tắc +15 (D05×S7, D06×S1, L07×S3) được chạy tiếp tới 45 trial (`runners/extend_budget.py`). D06×S1 và L07×S3 không đổi. D05×S7 còn cờ (best ở trial 41/45) nhưng chỉ cải thiện 0,00004 (0,07830 → 0,07826) và vẫn kém S6 (0,07795) nên thứ hạng S★ không phụ thuộc vào ô này.
- Task L: S6 và S7 hoà hạng trung bình (1,67). Hoà được phá theo thứ tự trong `CANDIDATE_SETS` (S2, S3, S5, S6, S7, S8), quy tắc đã có trong code trước khi đọc kết quả → S6.
- S5 và S8 không được xét cho S★ vì ineligible ở ít nhất một fold (block N, bảng 0.3).
