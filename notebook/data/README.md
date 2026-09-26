# `data/` — dữ liệu của pipeline

```
data/
├── raw/       765 MB, 10.132 file   ← đi kèm sẵn, không phải tải lại từ API
├── interim/   1,2 GB                ← pipeline dựng ra (bước 12–24)
└── final/     178 MB                ← pipeline dựng ra (bước 28)
```

Ba thư mục này là **nơi duy nhất** mà notebook và mọi script trong `scripts/`
đọc ghi. Không có thư mục data thứ hai ở đâu khác: gốc dự án là chính folder
`notebook/`, nên `data/` ở đây cũng là `data/` mà script nhìn thấy.

---

## `raw/` — đã có sẵn

Toàn bộ dữ liệu thô đã tải về từ UN Comtrade, WITS TRAINS, UNCTAD, CEPII, World
Bank, USITC và công báo của EU. **Phần mất thời gian nhất của cả pipeline nằm ở
đây** — riêng ba lượt tải Comtrade tính bằng ngày vì quota. Bạn không phải làm
lại, và không cần API key.

Có `raw/` là dựng lại được toàn bộ phần còn lại, **không cần mạng**. Cell thiết
lập của notebook tự bật chế độ ngoại tuyến khi thấy đủ `raw/`:

```python
nbtools.config.OFFLINE = data["has_raw"]   # -> True
```

Mất khoảng **16 phút** để ra `final/stage1_panel.parquet` (đo 22/09/2026 trên
máy 8 GB WSL2), và kết quả trùng bản v2 tham chiếu ở mọi cột.

### Một file không script nào tải được

`raw/ntm/ave_gtap/UNCTADGTAP11_AVEborder.csv` (UNCTAD–GTAP 11) phải lấy bằng
tay; nó **đã nằm trong bản gửi kèm**. Thiếu nó thì chỉ bước 22c dừng, với tên
file in ra rõ ràng — các bước khác không ảnh hưởng.

---

## `interim/` và `final/` — để trống có chủ ý

Chúng là thứ pipeline **dựng ra**, và dựng lại chúng chính là cách bạn kiểm
chứng rằng mình chạy đúng: bước 30 chạy 18 phép kiểm định độc lập trên kết quả,
và cả 18 phải pass.

Ai chỉ muốn phân tích ngay mà không dựng thì xin gói `panel` và bỏ
`stage1_panel.parquet` vào `final/`.

### Vài file trong `interim/` không phải sản phẩm cuối

| Đường dẫn | Là gì |
|---|---|
| `interim/_merge_shards/` | mảnh tạm của `merge_panel.py`, xoá sau khi xong |
| `interim/_ntm6/` | shard NTM theo nước áp, `build_ntm6.py` dựng |
| `final/_features_tmp.parquet` | file tạm giữa bước 27 và 28; bước 28 xoá nó |

Bỏ hết những thứ này ra khi gửi đi — chúng chỉ có nghĩa trên máy đang chạy.

---

## Người gửi: gói lại thế nào

Lệnh `zip` đầy đủ nằm ở [`../README.md`](../README.md) §7. Tóm lại: gửi `raw/`,
bỏ `interim/` và `final/stage1_panel*` — chúng dựng lại được trong ~16 phút, và
dựng lại chính là cách bên nhận kiểm chứng mình chạy đúng.

`raw/` phần lớn đã là `.gz`, nên nén thêm gần như không giảm: 765 MB trên đĩa ra
zip ≈ 698 MB. Đừng trông chờ nhỏ đi nhiều.

| Người nhận có | Notebook làm gì | Đợi |
|---|---|---|
| `raw/` | dựng lại từ bước 12, không cần mạng | ~16 phút |
| `raw/` + `final/` | đọc panel ngay; dựng lại được nếu muốn | vài phút |
| `raw/` + `interim/` + `final/` | bỏ qua mọi bước dựng, đọc thẳng file thật | vài phút |
| không có gì | chạy thật từ đầu, kể cả tải API | nhiều ngày (quota Comtrade) |
