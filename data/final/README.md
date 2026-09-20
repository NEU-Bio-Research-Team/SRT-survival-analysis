# data/final/

Thư mục này chỉ track một file: `README.md` (file này). Hai file dữ liệu
không track git (quá lớn — xem `.gitignore`):

| File | Kích thước | Khi nào dùng |
|---|---|---|
| `stage1_panel.parquet` | 178 MB (nén zstd) | **Mặc định — dùng cái này.** Nạp nhanh, ít RAM, giữ đúng kiểu số |
| `stage1_panel.csv` | 1,2 GB | Chỉ khi công cụ không đọc được parquet (Excel, một số bản R/Stata cũ) |

Bản v2 (20/09/2026): **932.204 dòng × 209 cột**. `stage1_panel.csv` trên đĩa
vẫn là bản v1 cho tới khi xuất lại từ parquet (lệnh bên dưới). Bản v1
đầy đủ nằm ở `data/v1_backup/`. Kết quả kiểm định: `docs/audit/stage1_v2.md`.
Parquet dựng từ
`data/interim/panel_final.csv` bằng:

```
python3 scripts/build_stage1_df.py features
python3 scripts/build_stage1_df.py join
```

(chạy tách hai lệnh, không dùng `all`, nếu máy có dưới ~6GB RAM khả dụng —
xem docstring đầu file `scripts/build_stage1_df.py` để biết vì sao)

Xuất bản CSV từ parquet đã dựng (không phải chạy lại pipeline):

```python
import polars as pl
pl.scan_parquet("data/final/stage1_panel.parquet").sink_csv("data/final/stage1_panel.csv")
```

**Từ điển dữ liệu đầy đủ — ý nghĩa, nguồn, cách tính từng cột trong 209
cột:**
[`docs/TU_DIEN_DU_LIEU_FINAL_DF.md`](../../docs/TU_DIEN_DU_LIEU_FINAL_DF.md)
