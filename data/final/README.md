# data/final/

Thư mục này chỉ track một file: `README.md` (file này). Hai file dữ liệu
không track git (quá lớn — xem `.gitignore`):

| File | Kích thước | Khi nào dùng |
|---|---|---|
| `stage1_panel.parquet` | 178 MB (nén zstd) | **Mặc định — dùng cái này.** Nạp nhanh, ít RAM, giữ đúng kiểu số |
| `stage1_panel.csv` | 1,2 GB | Chỉ khi công cụ không đọc được parquet (Excel, một số bản R/Stata cũ) |

Cả hai cùng nội dung: **949.537 dòng × 205 cột**, dựng từ
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

**Từ điển dữ liệu đầy đủ — ý nghĩa, nguồn, cách tính từng cột trong 205
cột:**
[`docs/TU_DIEN_DU_LIEU_FINAL_DF.md`](../../docs/TU_DIEN_DU_LIEU_FINAL_DF.md)
