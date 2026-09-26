# `notebook/` — chạy và đọc pipeline Stage 1

Folder này là **toàn bộ** những gì cần để dựng lại
`data/final/stage1_panel.parquet` từ dữ liệu thô, và để hiểu vì sao mỗi bước tồn
tại. Nó chạy được **một mình**: không cần clone repo, không cần file nào nằm
ngoài folder này.

`stage1_pipeline.ipynb` **không chép lại** code của pipeline. Nó gọi thẳng các
script thật trong [`scripts/`](scripts/) qua tiến trình con và stream log ra ngay
dưới cell — nên cái bạn đọc trong notebook đúng là cái chạy ra panel.

---

## 1. Folder này phải có gì

```
notebook/                   ← gốc dự án
├── README.md               ← file này
├── requirements.txt        môi trường
├── stage1_pipeline.ipynb   32 bước, 6 phần
├── nbtools/                công cụ dùng chung, để cell notebook ngắn và đọc được
│   ├── config.py           đường dẫn, thiết lập chạy, kiểm tra môi trường
│   ├── runner.py           Step + run(): gọi script, kiểm input/output, stream log
│   ├── artifacts.py        đọc nhanh csv/parquet (không nạp cả file vào RAM)
│   └── render.py           in markdown/bảng
├── scripts/                toàn bộ code của pipeline (30 script)
├── selection/              input làm bằng tay — không script nào sinh ra được
├── docs/                   tài liệu tham chiếu — TUỲ CHỌN, hay bị bỏ ra khi nén
├── data/
│   ├── raw/                tải từ API/nguồn gốc   765 MB
│   ├── interim/            bảng trung gian        1,2 GB  (pipeline dựng ra)
│   └── final/              stage1_panel.parquet   178 MB  (pipeline dựng ra)
└── logs/                   log đầy đủ của từng bước
```

**Bước 1 của notebook kiểm tra ba thành phần bắt buộc** (`scripts/`,
`selection/`, `data/`) và dừng ngay nếu thiếu, thay vì để bạn phát hiện ở bước
14. `docs/` chỉ là tuỳ chọn: thiếu nó pipeline vẫn chạy đủ, chỉ là các link tới
từ điển dữ liệu không mở được — bước 1 nói rõ điều đó.

### Vì sao gốc dự án lại là chính folder này

Mọi script trong `scripts/` mở đầu bằng cùng một dòng:

```python
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

— tức là chúng coi *thư mục cha của `scripts/`* là gốc, rồi đọc/ghi `<gốc>/data/`,
`<gốc>/selection/`, `<gốc>/docs/`, `<gốc>/.env`. Vì `scripts/` nằm ngay trong
folder này, gốc đó **chính là folder này**. Notebook và script vì thế nhìn cùng
một tập file, không có trường hợp "notebook đọc một đằng, script ghi một nẻo",
và không cần thiết lập biến môi trường nào.

---

## 2. Tạo môi trường

Khuyến nghị **Python 3.13** (bản đã dựng ra panel v2). Từ 3.10 trở lên đều chạy.

### Cách A — `venv`

```bash
cd /đường/dẫn/tới/notebook
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Ubuntu/Debian báo thiếu `venv`: `sudo apt install python3-venv python3-pip`.

### Cách B — conda

```bash
conda create -n wits python=3.13 -y
conda activate wits
pip install -r requirements.txt
```

### Đăng ký kernel cho Jupyter

Để notebook chạy đúng bằng môi trường vừa tạo, không phải python hệ thống:

```bash
python -m ipykernel install --user --name wits --display-name "wits (venv)"
```

### Mở notebook

```bash
cd /đường/dẫn/tới/notebook
jupyter lab stage1_pipeline.ipynb
```

Chọn kernel **wits (venv)** ở góc trên bên phải. **Bước 1 của notebook tự kiểm
tra** — bảng "Gói cần cho pipeline" phải hiện `polars 1.38.1`; lệch phiên bản thì
phép kiểm A18 (hai lần dựng phải cho file giống hệt nhau) có thể fail.

> VS Code cũng được: mở folder `notebook/`, mở file `.ipynb`, bấm
> **Select Kernel** → **Python Environments** → `.venv`.

---

## 3. Dữ liệu

### Bản gửi kèm có gì

**Bản `raw` đi kèm sẵn `data/raw/` — 765 MB, 10.132 file.** Đó là toàn bộ dữ liệu
thô đã tải từ UN Comtrade, WITS TRAINS, UNCTAD, CEPII, World Bank, USITC và công
báo EU. **Bạn không phải gọi lại API nào**, và phần mất thời gian nhất của
pipeline (ba lượt tải Comtrade, tính bằng ngày vì quota) đã xong.

`interim/` và `final/` để trống **có chủ ý**: chúng là thứ pipeline dựng ra, và
dựng lại chúng chính là cách bạn kiểm chứng mình chạy đúng.

| Bạn nhận được | Notebook làm gì | Đợi |
|---|---|---|
| `raw/` (bản mặc định) | dựng lại từ bước 12, không cần mạng | **~16 phút** (đo 22/09/2026) |
| `raw/` + `final/` | đọc panel ngay; dựng lại được nếu muốn | vài phút |
| `raw/` + `interim/` + `final/` | bỏ qua mọi bước dựng, đọc thẳng file thật | vài phút |
| không có gì | chạy thật từ đầu, kể cả tải API | **nhiều ngày** (quota Comtrade) |

Ai chỉ muốn phân tích ngay thì xin gói `panel` (178 MB) và bỏ
`stage1_panel.parquet` vào `data/final/`.

### Hai công tắc

Chúng nằm ở **cell thiết lập ngay sau bước 1**, và chỉ ở đó:

```python
nbtools.config.SKIP_EXISTING = True
nbtools.config.OFFLINE = data["has_raw"]
```

* **`SKIP_EXISTING = True`** — bước nào đã có đủ file output thì bỏ qua và in ra
  bảng output đang có. Trên máy trắng không file nào có sẵn, nên **toàn bộ
  pipeline vẫn chạy thật từ raw**; từ lần thứ hai notebook chạy lại trong vài
  phút. Muốn dựng lại đúng một bước: `run(step, force=True)`.
* **`OFFLINE`** — chặn mọi bước cần mạng, **mặc định bật khi đã có đủ `raw/`**.
  Khi đó Phần 1 không còn việc gì để làm, và bật lên là chắc chắn không bước nào
  lén gọi API. Bước 12 được đánh dấu *không bắt buộc* (không module nào đọc
  output của nó) nên nếu bị chặn thì notebook cảnh báo rồi đi tiếp; mọi bước
  còn lại đều chạy được ngoại tuyến từ `raw/`.

### API key — chỉ cần nếu tải lại từ đầu

**Với bản gửi kèm `raw/`, bạn không cần API key.** Phần 1 được bỏ qua sạch vì mọi
file đã có.

Ba bước tải Comtrade (4, 5a, 5b) cần `COMTRADE_PRIMARY_KEY` trong file `.env`
đặt ngay trong folder này:

```
COMTRADE_PRIMARY_KEY=<key của bạn>
COMTRADE_SECONDARY_KEY=<key dự phòng>
```

Xin key ở <https://comtradeplus.un.org>. Các nguồn còn lại (TRAINS, UNCTAD,
CEPII, World Bank, USITC, EU) đều công khai, không cần tài khoản.

> Tạo `.env` rồi thì **nhớ xoá nó trước khi gửi folder này đi**. Mặc định nó
> không tồn tại, chỉ có `.env.example`, nên trạng thái an toàn là trạng thái
> mặc định.

### Một file không script nào tải được

`data/raw/ntm/ave_gtap/UNCTADGTAP11_AVEborder.csv` (UNCTAD–GTAP 11) phải lấy
bằng tay. Nó **đã nằm trong bản gửi kèm `raw/`**. Nếu thiếu, bước 22c dừng và nói
rõ tên file — xin lại rồi chạy tiếp, các bước khác không ảnh hưởng.

---

## 4. Notebook có gì

32 bước, chia 6 phần (0–5). Mỗi bước là một cell giải thích + một cell chạy.

| Phần | Bước | Việc | Ra |
|---|---|---|---|
| 0 | 1–3 | Môi trường, input làm tay, bảng tra cứu mã HS | `selection/`, `data/raw/concordance/` |
| 1 | 4–13 | **Thu thập raw** từ 10 nguồn | `data/raw/` (765 MB) |
| 2 | 14–23 | **Tiền xử lý**: khoá sản phẩm, spell, từng module đặc trưng | `data/interim/` |
| 3 | 24–26 | **Merge thành data tổng** | `data/interim/panel_final.csv` |
| 4 | 27–29 | **Dựng panel Stage 1** | `data/final/stage1_panel.parquet` |
| 5 | 30–32 | **Kiểm định** 18 phép thử + bàn giao | `docs/audit/stage1_v2.md` |

### Thời gian và RAM

Cột **đo được** dưới đây là một lượt **dựng lại đầy đủ từ `data/raw/`, hoàn toàn
ngoại tuyến**, trên máy 8 GB RAM / WSL2, ngày 22/09/2026. Kết quả của lượt đó:
cả 39 bảng trong `data/interim/` **giống hệt từng byte** bản v2 tham chiếu, và
panel trùng bản v2 ở **mọi cột** (A18 pass).

| Bước | Đo được | Ghi chú |
|---|---|---|
| **Tổng, từ `raw/` đến panel đã kiểm định** | **16 phút** | 18/18 phép kiểm pass |
| 20a — `build_eu_mfn_cn.py` bản đầy đủ | 7'54 | bước dài nhất; bóc PDF công báo CN ba năm |
| 24 — `merge_panel.py` | 2'06 | bản v2 đo 4'15, đỉnh RAM 378 MB |
| 16 — `build_spells.py` | 1'54 | bản v2 đo 3'09, **đỉnh RAM 2,8 GB** ← nặng RAM nhất |
| 19 — `build_evfta_staging.py` | 1'30 | bóc PDF Annex 2-A |
| 22a — `build_ntm6.py` | 54 giây | |
| 28 — `build_stage1_df.py join` | 30 giây | |
| 23a — `build_covariates.py` | 31 giây | |
| 30 — `audit_stage1.py` (17 phép) | 23 giây | A18 cần bước 30b |
| 27 — `build_stage1_df.py features` | 20 giây | |
| 13, 14, 20b, 21, 22b, 22c, 23b, 23c | dưới 5 giây mỗi bước | |
| 30b — A18, dựng lại lần hai | ~1,5 phút | tuỳ chọn, tắt sẵn |
| 7 — tải file NTM researcher | **58,4 phút** | chỉ khi tải lại raw; một request, 10,5 GB stream |
| 4, 5a, 5b — tải Comtrade | tính bằng ngày | chỉ khi tải lại raw; quota. Resume được. |

> Các tài liệu bàn giao cũ ghi con số lớn hơn cho một vài bước (ví dụ 22a: 12
> phút, 23a: 15 phút). Chúng là ước lượng chưa đo lại; số trong bảng trên là số
> bấm đồng hồ, và output đã được đối chiếu từng byte.

⚠️ **Bước 27 và 28 phải chạy tách rời.** Đừng gộp thành `build_stage1_df.py all`
trên máy dưới ~6 GB RAM trống — lý do nằm trong docstring đầu
[`scripts/build_stage1_df.py`](scripts/build_stage1_df.py).

⚠️ **Hai bước tự chọn chế độ theo tình trạng đĩa**, không theo giả định:

* **20a** — nếu `data/interim/eu_mfn_hs6.csv` chưa có (đúng trường hợp máy chỉ mới
  có `raw/`), nó chạy bản đầy đủ để bóc PDF công báo CN. Nếu file đó đã có, nó chỉ
  gấp lại về mức family trong vài giây.
* **13** — ngoại tuyến thì chạy `--ntm-only`, dựng lại `ntm_country.csv` từ
  `data/raw/ntm/` đã có; có mạng thì chạy cả nửa vĩ mô WITS Development.
  `ntm_country.csv` **bắt buộc** phải có: `build_ntm.py` và `merge_panel.py` đều
  thoát ngay nếu thiếu.

---

## 5. `nbtools/` — công cụ dùng chung

Mọi thứ lặp lại được tách ra đây để cell notebook chỉ còn phần nội dung.

```python
from nbtools import Step, run, plan, describe

run(Step("16_spells", "Dựng spell + episode từ panel HS6",
         ["scripts/build_spells.py"],
         outputs=["data/interim/spells.csv", "data/interim/episodes.csv"],
         requires=["data/interim/family_map.csv", "data/raw/trade"],
         minutes=3.2))
```

`Step` là một bản kê khai: lệnh chạy, file nó **phải đọc** (`requires`), file nó
**phải sinh ra** (`outputs`), thời gian ước tính, có cần mạng / API key không.
`run()` lo phần còn lại:

1. **input thiếu thì dừng ngay**, nói rõ file nào — thay vì để script chết giữa
   chừng với một traceback không ai đọc được;
2. bỏ qua nếu output đã có;
3. stream log ra cell, ghi log đầy đủ vào `logs/<id>.log`, ném lỗi kèm 20 dòng
   cuối nếu script hỏng;
4. **kiểm lại output sau khi chạy** và báo đỏ nếu thiếu.

Chốt (1) và (4) có lý do cụ thể: `merge_panel.py` **bỏ qua trong im lặng** mọi
bảng phụ không tìm thấy (`if not table: continue`). Một bước bị quên sẽ không làm
gì đổ vỡ — nó chỉ lặng lẽ cho ra một panel thiếu cột.

Hàm hay dùng:

| Hàm | Làm gì |
|---|---|
| `run(step, force=True)` | dựng lại một bước dù output đã có |
| `plan()` | bảng kê mọi bước notebook đã định nghĩa: bước nào xong, còn bao lâu |
| `describe(path)` | dung lượng, số dòng × cột, vài dòng đầu |
| `unique_key(path, [...])` | kiểm grain — bộ khoá có duy nhất không |
| `value_counts(path, col)` | phân bố một cột (`censor_reason`, `staging_cat`…) |
| `null_share(path, [...])` | tỷ lệ null từng cột — độ phủ của từng module |
| `column_groups(path, {...})` | đếm cột theo nhóm chủ đề (cách đọc 209 cột) |
| `dir_summary(path)` | thư mục raw: bao nhiêu file, nặng bao nhiêu |
| `nbtools.exists(path)` | có file đó chưa (thư mục rỗng tính là chưa) |

Không hàm nào nạp cả file vào RAM: parquet đọc metadata, CSV đếm byte.

---

## 6. Gặp sự cố

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| `SystemExit: Không thấy nbtools/…` | Mở file `.ipynb` mà không mở cả folder. Mở folder `notebook/` rồi mở notebook từ trong đó. |
| Bước 1 báo thiếu `scripts/` hoặc `selection/` | Giải nén chưa hết, hoặc copy mỗi file `.ipynb` ra chỗ khác. Cần cả folder. |
| `ModuleNotFoundError: nbtools` | Kernel không phải môi trường vừa tạo. Chọn lại kernel rồi Restart. |
| Bước nào đó báo **"Thiếu input: …"** | Đúng thiết kế — bước sinh ra file đó chưa chạy. Chạy lại các cell phía trên theo thứ tự (hoặc Run All). |
| Bước 4/5 thoát mã 1 | Hết quota Comtrade trong ngày. File đã tải được giữ nguyên — chạy lại cell hôm sau. |
| Bước 6 trả 404 cho 2024–2025 | Đúng như vậy: TRAINS không có hai năm đó. Bước 8 + 20 vá bằng công báo CN của EU. |
| Bước 22b/24 báo `ntm_country.csv missing - run fetch_macro.py first` | Bước 13 chưa chạy. Ngoại tuyến nó vẫn chạy được (`--ntm-only`, dựng lại từ `data/raw/ntm/` đã có) — chạy lại cell bước 13. |
| `build_spells.py` dừng vì "mass death" | Chốt chặn T7 đang làm việc. Kiểm chứng ca đó trước, rồi mới thêm vào `selection/mass_death_allowlist.csv`. |
| Máy hết RAM ở bước 20a | Bản đầy đủ bóc PDF khá nặng. Đóng bớt ứng dụng và chạy riêng cell đó. |
| Máy hết RAM ở bước 27/28 | Đang chạy `all` thay vì `features` rồi `join` tách rời. |
| Bước 22c báo thiếu file | `data/raw/ntm/ave_gtap/UNCTADGTAP11_AVEborder.csv` phải lấy tay — xem §3. |

Log đầy đủ của mọi bước: `logs/<id>.log`.

---

## 7. Gửi folder này đi tiếp

Trong đây toàn file thật, không symlink, không đường dẫn tuyệt đối — **nén kiểu
gì cũng chạy được**. Lệnh đang dùng, chạy từ thư mục **cha** của `notebook/`:

```bash
zip -r wits_notebook_$(date +%Y%m%d).zip notebook \
  -x 'notebook/docs/*'      'notebook/docs' \
     'notebook/probe_out/*' 'notebook/probe_out' \
     'notebook/data/interim/*' \
     'notebook/data/final/stage1_panel*' \
     'notebook/logs/*'      'notebook/logs' \
     'notebook/.env' \
     '*__pycache__*' '*.ipynb_checkpoints*' '*.venv*'
```

→ **≈698 MB, 10.238 mục.** Bên nhận giải nén rồi làm ba bước ở §2 là chạy được;
Run All mất ~16 phút, không cần mạng, không cần API key.

### Cái gì bị loại, và vì sao

| Loại ra | Vì sao |
|---|---|
| `docs/` | tài liệu tham chiếu, không cần để chạy. Bước 1 báo là thiếu và nói rõ hệ quả: các link tới từ điển 209 cột ở bước 29 và 32 sẽ không mở được. |
| `data/interim/` · `data/final/stage1_panel*` | pipeline dựng lại chúng trong ~16 phút, và dựng lại chính là cách bên nhận kiểm chứng mình chạy đúng. Gửi kèm thì nặng thêm 1,6 GB và mọi bước dựng bị bỏ qua. |
| `probe_out/` · `logs/` | chỉ có nghĩa trên máy đã chạy. |
| `.env` | **key Comtrade.** Mặc định folder này không có nó, chỉ có `.env.example` — nên trạng thái an toàn là trạng thái mặc định. Tạo rồi thì dòng `-x 'notebook/.env'` là chốt thứ hai. |
| `__pycache__/` · `.venv/` | rác của máy bạn, và `.venv` còn hard-code đường dẫn tuyệt đối. |

**Giữ lại** `data/final/README.md` (giải thích parquet vs CSV) và
`Stage1_Research_Framework.md`.

### Muốn gửi kèm cả panel

Bỏ dòng `'notebook/data/final/stage1_panel*'` ra → thêm ~180 MB, bên nhận phân
tích được ngay mà vẫn dựng lại được nếu muốn.

Kiểm nhanh zip trước khi gửi:

```bash
unzip -Z1 wits_notebook_*.zip | grep -c 'notebook/.env$'    # phải là 0
unzip -Z1 wits_notebook_*.zip | grep -c 'data/raw/.*[^/]$'  # phải là 10132
```

## 8. Đọc tiếp

| Câu hỏi | Tài liệu |
|---|---|
| Mỗi cột trong 209 cột nghĩa là gì | [`docs/TU_DIEN_DU_LIEU_FINAL_DF.md`](docs/TU_DIEN_DU_LIEU_FINAL_DF.md) |
| Các module ghép với nhau bằng khoá nào | [`docs/KHOA_GHEP_STAGE1_PANEL.md`](docs/KHOA_GHEP_STAGE1_PANEL.md) |
| Lỗi nào của v1, sửa thế nào, còn tồn gì | [`docs/STAGE1_PANEL_FIX_PLAN.md`](docs/STAGE1_PANEL_FIX_PLAN.md) |
| Thu thập gì, từ đâu, phủ tới đâu | [`docs/DATA_HANDOFF.md`](docs/DATA_HANDOFF.md) |
| Khung nghiên cứu B0–B9 | [`Stage1_Research_Framework.md`](Stage1_Research_Framework.md) |
