# Stage 2 benchmark — Đợt 0–4 (kế hoạch `KE_HOACH_THUC_NGHIEM_DOT_1.md`)

Code và config của chương trình thực nghiệm trên panel Stage 1 v2. Stage 1
(`notebook/scripts`, `notebook/data`) **không bị sửa**: mọi thứ ở đây chỉ đọc
`data/final/stage1_panel.parquet` và `data/raw/` (C09).

## Môi trường

```
conda create -n srt-stage2 python=3.10     # bản dùng: clone của drug-tox-env
pip install -r stage2_benchmark/requirements-stage2.txt
```

Bản đã chạy: torch 2.11 (CUDA), pycox 0.3.0, scikit-survival 0.25.0,
lifelines 0.30.0, xgboost 3.2.0, optuna 4.8.0, statsmodels 0.15.0 — danh sách
đầy đủ ở `requirements-stage2.txt` (pip freeze).

## Chạy / chạy tiếp sau khi máy sập

Mọi lệnh đều **resume được**. Chạy lại đúng lệnh cũ là đủ: ô đã xong
(`status.json` = done/ineligible) được bỏ qua; ô đang tune dở chạy tiếp từ
trial cuối (grid: `trials.jsonl`; optuna: `optuna.db`); prediction tốt nhất đã
được ghi nguyên tử sau mỗi trial cải thiện.

```
cd notebook
PY=/home/minhquang/miniconda3/envs/srt-stage2/bin/python
$PY -m stage2_benchmark.data.base_table              # bảng gốc EU27 (~10 s)
$PY -m stage2_benchmark.data.profile                 # Đợt 0.1
$PY -m stage2_benchmark.runners.stage0_report        # Đợt 0.2 / 0.3
$PY -m pytest -q stage2_benchmark/tests              # Đợt 0.4
$PY -m stage2_benchmark.runners.reproduce_legacy     # Đợt 0.5
$PY -m stage2_benchmark.runners.batch --plan pilot0  # Đợt 0.6
$PY -m stage2_benchmark.inference.run_inference      # Đợt 4 (song song được)
$PY -m stage2_benchmark.inference.report
$PY -m stage2_benchmark.runners.batch --plan batch1  # Đợt 1 (~5–6 h)
$PY -m stage2_benchmark.runners.aggregate --plan batch1
$PY -m stage2_benchmark.runners.shortlist            # chốt shortlist -> commit riêng
$PY -m stage2_benchmark.data.target_variants         # C09: dựng lại spell từ raw
$PY -m stage2_benchmark.runners.batch --plan batch2       # Đợt 2 (mở test)
$PY -m stage2_benchmark.runners.batch --plan batch2_lobo
$PY -m stage2_benchmark.runners.batch --plan batch3       # Đợt 3
$PY -m stage2_benchmark.runners.aggregate --plan batch2   # (batch2_lobo, batch3)
```

`run_all.sh` chạy tuần tự các bước dài, và `STEPS="batch1 ..."` chọn bước.
`--retry-failed` chạy lại những ô lỗi. Tiến độ xem ở
`artifacts/logs/<plan>.log` và `reports/<plan>/progress.csv`.

Chỉ chạy **một process nặng mỗi lúc**: máy 8 GB RAM, và một process benchmark
đã dùng khoảng 2,3 GB sau khi nạp torch/CUDA.

## Cấu trúc

| Đường dẫn | Nội dung |
|---|---|
| `configs/` | tasks, splits, feature registry, feature sets, models, experiments, shortlist (đóng băng) |
| `data/` | `base_table` (bảng gốc EU27), `views` (re-censor theo cutoff), `profile`, `target_variants` (C09) |
| `features/` | resolve set/eligibility/preprocessor (fit trên train), selector C05 |
| `models/` | 16 adapter + 2 reference (D00 age-only, L00 KM) |
| `evaluation/` | IPCW Brier/IBS, C_td, td-AUC, Brier 1y, calibration; bootstrap theo relation |
| `runners/` | `cell` (một ô, checkpoint), `batch` (kế hoạch), `aggregate`, `shortlist`, báo cáo Đợt 0 |
| `inference/` | GLM IRLS + cluster SE, gamma frailty, RE logit/probit, I1–I16 |
| `reports/` | kết quả nhỏ (commit git). `artifacts/` = view, prediction, optuna DB (không commit) |

## Quy ước chốt trước khi chạy

Xem `configs/tasks.yaml`. Điểm lệch khỏi legacy quan trọng nhất là censor hành
chính tại H = C − g cho mọi người, để censoring không phụ thuộc kết cục
(`reports/stage0/0.5_adapter_reproduction.md`).
