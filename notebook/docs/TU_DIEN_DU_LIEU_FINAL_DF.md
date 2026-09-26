# Từ điển dữ liệu — `data/final/stage1_panel.parquet`

> **Bản v2 (20/09/2026).** Panel đã được dựng lại theo
> [STAGE1_PANEL_FIX_PLAN.md](STAGE1_PANEL_FIX_PLAN.md): khóa sản phẩm gộp mã
> mồ côi, sự kiện chỉ tính khi được xác nhận bởi năm có dữ liệu HS6 thật, thuế
> EU lấy từ biểu EU, sửa lag `log_total_import_cp_lag1`. Kết quả kiểm định:
> [audit/stage1_v2.md](audit/stage1_v2.md) (so với v1:
> [audit/stage1_v1.md](audit/stage1_v1.md)). Các mục dưới đã cập nhật theo v2;
> tỷ lệ null của những cột không đổi định nghĩa vẫn là số đo trên v1.

*Viết 03/09/2026. Đây là dataframe cuối cùng cho Stage 1 (B4→B9 trong
[Stage1_Research_Framework.md](../Stage1_Research_Framework.md)) — mỗi dòng là
một **episode**: một quan hệ (nước nhập khẩu × nhóm sản phẩm) tại một năm cụ
thể. Mọi con số % null trong tài liệu này đếm trực tiếp trên file, không phải
ước lượng.*

---

## 1. Tổng quan

| | |
|---|---|
| Đường dẫn | `data/final/stage1_panel.parquet` (mặc định) hoặc `data/final/stage1_panel.csv` (khi công cụ không đọc được parquet) |
| Định dạng | Parquet nén zstd, **183 MB** (v2) |
| Số dòng | **932.204** episode-năm (v1: 949.537) |
| Số cột | **209** (v1: 205; thêm `censor_reason`, `start_reason`, `tariff_n_lines`, `ntm6_mappable`) |
| Đơn vị quan sát | `(importer, product_family, year)` — một dòng = một quan hệ tại một năm |
| Khung thời gian | 2002–2025 (mọi năm có dữ liệu thật; B0 chốt cửa sổ chính 2012–2024) |
| Số nước nhập khẩu | 147 (EU-27 là mẫu chính theo B0; 147 nước dùng cho robustness B8 #6) |
| Số nhóm sản phẩm | **4.365** `product_family` có trong panel (4.522 family trong khóa; xem `scripts/families.py`) |
| Dựng bằng | `scripts/build_stage1_df.py`, đọc `data/interim/panel_final.csv` |
| Tái tạo | `python3 scripts/build_stage1_df.py features && python3 scripts/build_stage1_df.py join` (xem §7 — máy yếu RAM thì **bắt buộc** chạy 2 lệnh tách rời, không chạy `all`) |

### Cách nạp

```python
import polars as pl
df = pl.read_parquet("data/final/stage1_panel.parquet")        # ~1-2 GB trong RAM
# hoặc, nếu máy yếu RAM — chỉ lấy cột cần, không load hết:
df = pl.scan_parquet("data/final/stage1_panel.parquet").select([...]).collect()
```

```python
import pandas as pd
df = pd.read_parquet("data/final/stage1_panel.parquet")        # cần pyarrow
```

```r
library(arrow)
df <- read_parquet("data/final/stage1_panel.parquet")
# hoặc duckdb (không cần load hết vào RAM):
library(duckdb)
con <- dbConnect(duckdb())
dbGetQuery(con, "SELECT * FROM 'data/final/stage1_panel.parquet' WHERE importer = 'DEU' LIMIT 10")
```

Nếu công cụ không đọc được parquet (Excel, một số bản R/Stata cũ), dùng
`data/final/stage1_panel.csv` — cùng nội dung, cùng 205 cột, chỉ nặng hơn
(1,2 GB thay vì 178 MB). Đọc bằng Python/polars **phải** khai `null_values`
đúng — file này chỉ dùng `""` làm null (không còn `"nan"` text, đã xác nhận ở
§11.2), nhưng khai thừa `null_values=["", "nan"]` vẫn an toàn:

```python
df = pl.read_csv("data/final/stage1_panel.csv", infer_schema_length=None,
                  null_values=["", "nan"])
```

### Cấu trúc thư mục `data/`

```
data/raw/      dữ liệu thô tải từ nguồn gốc (BACI/Comtrade, gravity, tariff, EVFTA PDF, WDI, ...)
               — KHÔNG track git, tái tạo bằng scripts/fetch_*.py
data/interim/  bảng trung gian (episodes.csv, spells.csv, panel_final.csv, eu_tariff_panel.csv, ...)
               — KHÔNG track git, tái tạo bằng scripts/build_*.py + merge_panel.py
data/final/    stage1_panel.parquet (178 MB) + stage1_panel.csv (1,2 GB, cùng
               nội dung) — dataframe DUY NHẤT cần cho B4→B9
               — KHÔNG track git (quá lớn); track duy nhất README.md này
```

Không cần đụng vào `data/raw/` hay `data/interim/` để chạy B4–B9 — mọi thứ nằm
trong `stage1_panel.parquet`. Hai thư mục kia chỉ cần khi tái tạo lại từ đầu
hoặc kiểm chứng một con số ngược lên tận nguồn.

---

## 2. Nguyên tắc đọc bảng dưới

- **%null** đếm trên toàn bộ 949.537 dòng (147 nước, mọi năm 2002–2025), không
  riêng EU27/2012–2024 — vì vậy một cột chỉ gắn cho EU27 (như `staging_cat`)
  sẽ luôn hiện %null ≈ 73–74% dù độ phủ *trong EU27* gần như tuyệt đối. Bảng
  ghi rõ trường hợp này ở cột Ghi chú.
- **`_lag1` hoặc `_lag`** = giá trị của cùng biến đó tại năm **t−1**, đúng
  theo B3: *"Mọi covariate lấy tại t−1"*. Đây **không phải** dịch dòng
  (`.shift()`) — là join theo đúng năm lịch, xem §6 để hiểu vì sao điều này
  quan trọng.
- Một dòng là **năm đầu tiên của một spell mới** (quan hệ chưa từng tồn tại
  trước đó trong cửa sổ dữ liệu) sẽ có mọi cột cấp-quan-hệ (`log_value_lag`,
  `vn_market_share_pct_lag1`, ...) = null một cách **có chủ đích** — đó là
  "chưa có lịch sử quan hệ", không phải lỗi thiếu dữ liệu. Các cột cấp
  quốc-gia/sản-phẩm (`log_gdp_d_lag1`, `rca_lag`, `n_products_to_c_lag1`, ...)
  vẫn có giá trị bình thường ở đúng dòng đó — xem §6.

---

## 3. Khoá & định danh

| Cột | Kiểu | %null | Ý nghĩa |
|---|---|---:|---|
| `importer` | str | 0.0 | Mã ISO3 nước nhập khẩu (147 nước; lọc `importer` ∈ EU27 cho mẫu chính B0) |
| `exporter` | str | 0.0 | Luôn `VNM` — thiết kế chỉ có một nước xuất khẩu |
| `product_family` | str | 0.0 | Nhóm sản phẩm, khoá theo revision HS gốc **H0** (không phải HS2012 thuần — xem `docs/DOI_CHIEU_B0_VOI_DU_LIEU.md` §5.1 về khác biệt với B0). Dạng `H0_610910`. Từ v2 một family có thể gồm **nhiều mã H0 cùng HS4** (mã mồ côi được gộp vào family đã hấp thụ hàng của nó khi đổi revision, ví dụ `H0_620213` = 620213 + 620293); tên family là mã H0 nhỏ nhất. Danh sách thành viên: `data/interim/family_members.csv` |
| `hs2` | str | 0.0 | 2 số đầu của mã HS6 trong `product_family` — dùng để cluster SE theo B5 ("cluster two-way theo c và HS2") và để tính `hs2_share` |
| `year` | int | 0.0 | Năm quan sát |
| `spell_id` | str | 0.0 | Định danh spell — `{importer}_{exporter}_{product_family}_{spell_start_year}` |
| `spell_start_year`, `spell_end_year` | int | 0.0 | Năm bắt đầu/kết thúc của spell chứa dòng này |
| `t_start`, `t_stop` | int | 0.0 | Cặp counting-process cho Cox/`lifelines` — `t_stop - t_start = 1` luôn đúng vì panel theo năm |

---

## 4. Nhãn sinh tồn (censoring, spell, gap)

| Cột | Kiểu | %null | Ý nghĩa |
|---|---|---:|---|
| `event` | int (0/1) | 0.0 | **Biến outcome chính.** 1 nếu quan hệ chết đúng ở năm này (năm sau tụt dưới ngưỡng, không hồi phục trong `GAP_TOLERANCE`), 0 nếu còn sống hoặc bị censor |
| `right_censored` | int (0/1) | 0.0 | 1 nếu điểm kết thúc của spell **không phải một cái chết đã được xác nhận** — lý do nằm ở `censor_reason`. Với gap rule 1 năm, chết ở năm E cần E+1 và E+2 đều có dữ liệu HS6 thật, và family phải biểu diễn được trong revision HS của các năm đó — **không được coi `event=0` do censor giống `event=0` do sống bình thường** |
| `censor_reason` | str | — | Rỗng = chết đã xác nhận (`event=1`). `window_end`: spell chạy tới năm cuối có dữ liệu của nước đó. `window_edge`: kết thúc trong `GAP_TOLERANCE` năm trước năm cuối, nên không thể xác nhận (vì vậy năm 2024 của EU không có event nào). `unobserved_year`: năm cần để xác nhận không có dữ liệu HS6 (không có file, chỉ có dòng tổng, batch rỗng, hoặc HS6 phủ < 50% TOTAL — `selection/hs6_unobserved_years.csv`). `hs_revision`: nước nhập khẩu đổi sang revision HS mà family không biểu diễn được |
| `left_trunc` | int (0/1) | 0.0 | 1 nếu **năm bắt đầu thật của spell không biết được** — lý do ở `start_reason`. v1 chỉ đánh dấu spell đang chạy năm 2002; v2 đánh dấu thêm các trường hợp dưới đây. Với cửa sổ B0 (2012–2024), phần lớn spell có tuổi quan sát được — xem `docs/DOI_CHIEU_B0_VOI_DU_LIEU.md` §5.3 |
| `start_reason` | str | — | Rỗng = năm bắt đầu đã xác nhận. `window_start`: năm trước đó (trong `GAP_TOLERANCE`) nằm trước 2002. `unobserved_year`: năm trước đó không có dữ liệu HS6. `hs_revision`: family không biểu diễn được trong revision của năm trước. `hs_revision_receiver`: spell mở ra đúng năm đổi revision ở family nhận hàng của một mã mồ côi chưa gộp được |
| `gap_filled` | int (0/1) | 0.0 | 1 nếu dòng này là **năm đệm dưới ngưỡng 10k USD** được giữ lại để nối hai năm sống liền kề theo gap rule (B0 chốt gap = 1 năm). **Lọc `gap_filled == 0` trước khi đếm "episode-năm đang sống"** — coi năm đệm là "đang sống" sẽ làm sai mẫu số của mọi tỷ lệ hazard |

**Kiểm tra đã xác nhận trên đúng scope B0** (EU27, 2012–2024, `gap_filled==0`):
v2 có 146.042 episode-năm, 15.958 event → **tỷ lệ chết 10,9%/năm** (v1:
148.475 / 18.516 / 12,5%). Chênh lệch chủ yếu đến từ năm 2024 (không còn event
nào, xem `window_edge`) và từ các cái chết giả năm 2016 và 2021 do mã mồ côi.

---

## 5. Nhóm 1 — Đặc tính quan hệ (B3 §Nhóm 1)

Cấp **(importer, product_family, year)** thật sự — biến đổi theo cả ba
chiều, khác các nhóm broadcast ở §6/§7.

| Cột | Kiểu | %null | Ý nghĩa | Nguồn |
|---|---|---:|---|---|
| `import_value_usd` | float | 0.0 | Kim ngạch VN xuất sang `importer`, nhóm `product_family`, năm `year` (USD) | Comtrade khai từ phía nhập khẩu |
| `net_weight_kg` | float | 5.5 | Khối lượng tịnh (kg) | Comtrade |
| `unit_value_usd_per_kg` | float | 5.5 | `import_value_usd / net_weight_kg` | tính toán |
| `vn_market_share_pct` | float | 2.0 | % thị phần VN trong tổng nhập khẩu của `importer` cho `product_family` từ toàn thế giới | `data/raw/trade_world/` làm mẫu số |
| `log_value` | float | 0.0 | `ln(import_value_usd + 1)` | tính toán (`build_stage1_df.py`) |
| **— bản lag (t−1), dùng cho mô hình hazard —** | | | | |
| `log_value_lag` | float | 20.5 | `ln(value)` **năm t−1**. Null ở dòng đầu spell = "chưa có lịch sử" | lag join theo (importer, product_family) |
| `log_total_import_cp_lag1` | float | — | `ln(1 + tổng nhập khẩu của importer cho family từ thế giới)` năm t−1. **v2 lag theo (importer, product_family)**; v1 lag nhầm theo family và lấy giá trị của một nước khác ở 94,6% dòng | lag join theo (importer, product_family) |
| `vn_market_share_pct_lag1` | float | 22.5 | thị phần năm t−1 | như trên |
| `unit_value_usd_per_kg_lag1` | float | 25.2 | đơn giá năm t−1 | như trên |
| `volatility_3y_lag1` | float | 31.9 | SD(ln value) trong 3 năm gần nhất **kết thúc ở t−1** (dùng t−3, t−2, t−1; cần ≥2/3 năm có dữ liệu, còn lại null) | tính toán, xem `build_stage1_df.py` |

**RCA và tăng trưởng — cấp sản phẩm, không phải cấp quan hệ, xem §7.** Hai
biến này *trông* giống cấp quan hệ vì nằm trên mọi dòng episode, nhưng
`build_spells.py::derived()` tính chúng theo `(product_family, year)` —
vị thế toàn cầu của VN trong sản phẩm đó, không phụ thuộc nước nào mua. Xếp ở
§7 để tránh lag sai grain (xem §6).

---

## 6. Vì sao lag phải đúng "grain" — đọc trước khi thêm biến mới

Đây là điểm dễ sai nhất khi mở rộng file này, nên ghi lại rõ.

`log_value_lag` đúng khi lag theo `(importer, product_family, year−1)`: nếu
đây là **năm đầu tiên** VN bán sản phẩm này cho nước đó, thì "giá trị năm
ngoái của quan hệ này" đúng là **không tồn tại** → null là chính xác, và các
dummy duration ở B5 sẽ hấp thụ nó.

Nhưng `rca` và `country_growth_pct` — vị thế cạnh tranh toàn cầu của Việt Nam
trong sản phẩm đó, GDP của nước nhập khẩu, tổng cầu thế giới cho sản phẩm đó —
**không phụ thuộc việc quan hệ (c,p) cụ thể này có tồn tại năm ngoái hay
không**. Một nước lần đầu mua giày Việt Nam năm 2015 vẫn "biết" RCA giày của
Việt Nam năm 2014 là bao nhiêu — đó là sự thật khách quan về Việt Nam, không
phải về quan hệ VN–nước đó. Nếu lag các biến này theo grain quan hệ
(`importer × product_family`), **dòng đầu spell — đúng nơi hazard cao nhất và
quan trọng nhất — sẽ bị null oan**, làm mất chính xác những quan sát cần nhất.

Vì vậy `build_stage1_df.py` lag mỗi biến theo đúng grain nó *thực sự* sống:

| Grain | Biến | Vì sao |
|---|---|---|
| `(importer, product_family, year)` | value, market share, unit value, `tariff_rate` (thuế TRAINS chung), volatility | thật sự phụ thuộc cả ba chiều |
| `(importer, year)` | GDP, dân số, lạm phát, tỷ giá, `n_products_to_c` | thuộc về nước nhập khẩu, không phụ thuộc sản phẩm |
| `(product_family, year)` | `rca`, `country_growth_pct`, `world_growth_pct`, `n_markets_for_p`, thuế/EVFTA của EU | thuộc về sản phẩm (hoặc, với thuế EU, thuộc về cả khối EU vì đây là thuế quan chung — xem §8) |
| `(importer, hs2, year)` | `hs2_share` | thuộc về danh mục VN bán sang nước đó, ở cấp nhóm HS2 |

Một lỗi thật đã xảy ra và được sửa khi dựng file này: bước lag cấp
`(product_family, year)` ban đầu dùng `.unique()` để khử trùng lặp mà không
ưu tiên giữ dòng có giá trị — với các cột chỉ có giá trị ở EU27 (thuế/EVFTA,
27/147 nước), việc này khiến ~92% giá trị đúng bị mất oan (chọn trúng dòng của
147−27=120 nước không-EU, vốn luôn null). Đã sửa bằng cách `drop_nulls()`
trước khi khử trùng lặp cho đúng nhóm cột này. Bài học: **trước khi thêm một
cột `_lag` mới, luôn hỏi "biến này biến thiên theo đúng những chiều nào?"
rồi mới chọn khoá join** — đừng mặc định khoá của bảng chính.

---

## 7. Nhóm 3+4 — Chính sách & cấu trúc danh mục (B3 §Nhóm 3, §Nhóm 4)

### 7a. Thuế quan chung (147 nước) — nguồn TRAINS

| Cột | Kiểu | %null | Ý nghĩa | Ghi chú |
|---|---|---:|---|---|
| `tariff_rate` | float | 0.5 | Thuế VN thực chịu khi xuất `product_family` sang `importer` năm đó. **Dòng EU** (tư cách thành viên theo năm): lấy từ biểu EU `eu_tariff_panel.csv` — GSP tới 2019, EVFTA từ 2020, MFN khi không có ưu đãi; bằng `tariff_applied_pct`. **Các nước khác**: TRAINS — với mỗi dòng HS6 lấy min(ưu đãi, MFN), rồi lấy trung bình cộng thật trên các dòng của family (v1 dùng trung bình trượt sai). ⚠️ Ưu đãi TRAINS khai theo **mã nhóm** (ASEAN, AANZFTA…) chưa được lấy, nên ở ASEAN, IND, NZL, CAN, MEX, PER, HKG giá trị này vẫn là MFN — cận trên | EU: biểu EU; khác: TRAINS theo `tariff_reporter` |
| `tariff_type` | str | 0.5 | TRAINS: `"PREF"` / `"MFN"`. Dòng EU: `"GSP"` / `"EVFTA"` / `"MFN"` |
| `tariff_n_lines` | int | — | Số dòng HS6 TRAINS được lấy trung bình (trống ở dòng EU) |
| `tariff_source_year` | int | 2.9 | Năm biểu thuế thật sự đo được (có thể carry-forward tối đa vài năm nếu thiếu) |
| `tariff_reporter` | str | 0.0 | Nước/khối có biểu thuế được đọc — với EU27 luôn là `"EUN"` (biểu chung) |
| `tariff_rate_lag1` | float | 21.8 | `tariff_rate` năm t−1, lag theo `(importer, product_family)` |

**v2:** trên dòng EU, `tariff_rate` giờ chính là `tariff_applied_pct` (biểu EU),
nên không còn sai số ~2,3pp trước 2020, cú sốc thuế giả +4,1pp năm 2022, hay
ô trống 2024–2025 của v1. Lag từ biểu EU (`tariff_applied_lag`) vẫn nên được
ưu tiên hơn `tariff_rate_lag1`, vì nó không trống ở năm đầu spell.

### 7b. Khối chính sách EU27 — biến treatment của B6

**Chỉ có giá trị cho `importer` ∈ EU27** (73–74% null trên toàn mẫu 147 nước
là *đúng thiết kế*, không phải thiếu dữ liệu — trong EU27 độ phủ ~97–98%).

| Cột | Kiểu | %null (toàn mẫu) | Ý nghĩa | Nguồn |
|---|---|---:|---|---|
| `tariff_mfn_pct` | float | 73.4 | Thuế MFN của EU cho `product_family`, năm đó | TRAINS 2002–2023, biểu CN của EU (EUR-Lex) cho 2024–2026 |
| `tariff_applied_pct` | float | 73.4 | Thuế **thực sự VN được hưởng**: GSP trước 2020, `min(lộ trình EVFTA, MFN)` từ 2020 | xem `docs/DU_LIEU_EVFTA_VA_THUE_EU.md` §4.1 |
| `tariff_applied_source` | str | 73.4 | `"gsp"` / `"evfta"` / `"mfn"` — biểu nào cho ra `tariff_applied_pct` | như trên |
| `pref_margin_pp` | float | 73.4 | `mfn − applied`, điểm phần trăm — biến `PrefMargin` của B6 | như trên |
| `staging_cat` | str | 73.7 | Mã lộ trình cắt thuế EVFTA (Annex 2-A): `A` (cắt ngay), `B3/B5/B7` (cắt dần 4/6/8 chặng), `TRQ`, `A+EP` | parse Annex 2-A |
| `staging_cat_slowest` | str | 73.7 | Như trên, nhưng lấy category **chậm nhất** khi một `product_family` gộp nhiều mã CN8 khác category (~197/5.205 HS6 — cờ `staging_mixed`) — dùng cho robustness | như trên |
| `staging_mixed` | int (0/1) | 73.7 | 1 nếu `product_family` gộp CN8 thuộc nhiều category khác nhau | như trên |
| `evfta_cut_cum_pp` | float | 73.4 | Mức cắt thuế **tích luỹ** tính đến năm đó so với base rate Annex 2-A (điểm %) — biến `evfta_cut_cum` của B3 | tính từ lộ trình staging |
| `evfta_cut_cum_share` | float | 73.4 | Như trên, theo **tỷ lệ** (0–1) của base rate đã được xoá | như trên |
| `years_since_evfta_policy` | int | 73.4 | `year − 2020` (âm nếu trước hiệp định) | tính toán |
| **— bản lag (t−1) —** | | | | |
| `tariff_mfn_pct_lag1` | float | 93.5 | | lag theo `product_family` (khối EU-wide, xem §6) |
| `tariff_applied_lag` | float | 93.5 | | như trên |
| `pref_margin_lag` | float | 93.5 | | như trên |
| `evfta_cut_cum_pp_lag` | float | 93.5 | | như trên |
| `evfta_cut_cum_share_lag` | float | 93.5 | | như trên |

*(%null của khối lag cao hơn khối gốc — đúng, vì cộng thêm phần null "chưa
có năm t−1 trong cửa sổ" ở ngoài EU27 vẫn giữ null 73%, cộng phần null tự
nhiên của EU27 dòng-đầu-spell/thiếu-2002.)*

**Phân bố treatment (đọc trước khi thiết kế B6):** category A (cắt thuế ngay)
chiếm 93% episode và kim ngạch EU27; B3/B5/B7 (cắt dần — nguồn biến thiên
chính cho B6) chỉ ~6% kim ngạch. Identification "sạch" nhưng dựa trên phần
đuôi danh mục — B6 phải nói rõ điều này. Chi tiết, số liệu kiểm chứng chéo với
TRAINS: `docs/DU_LIEU_EVFTA_VA_THUE_EU.md` §3.

### 7c. Cấu trúc danh mục (B3 §Nhóm 4 — "economies of scope")

| Cột | Kiểu | %null | Ý nghĩa | Grain lag |
|---|---|---:|---|---|
| `n_products_to_c` | uint | 0.2 | Số `product_family` VN đang bán *đủ ngưỡng* (`gap_filled==0`) sang `importer`, năm đó | `(importer, year)` |
| `n_markets_for_p` | uint | 0.1 | Số `importer` đang mua *đủ ngưỡng* `product_family` đó từ VN, năm đó | `(product_family, year)` |
| `hs2_share` | float | 0.4 | Tỷ trọng nhóm HS2 chứa `product_family` trong tổng kim ngạch VN→`importer` năm đó | `(importer, hs2, year)` |
| `hhi_market` | float | 0.0 | Chỉ số Herfindahl tập trung thị trường, theo năm | year |
| `hhi_product` | float | 0.0 | Chỉ số Herfindahl tập trung sản phẩm, theo năm | year |
| `n_products_to_c_lag1` | uint | 1.9 | | lag theo `(importer)` |
| `n_markets_for_p_lag1` | uint | 2.6 | | lag theo `(product_family)` |
| `hs2_share_lag1` | float | 4.0 | | lag theo `(importer, hs2)` |

---

## 8. Nhóm 2 — Thị trường & gravity (B3 §Nhóm 2)

### 8a. Vĩ mô nước nhập khẩu/xuất khẩu — World Bank WDI (`macro_panel_v2.csv`)

| Cột | Kiểu | %null | Ý nghĩa |
|---|---|---:|---|
| `importer_gdp_usd`, `importer_gdp_growth_pct`, `importer_gdp_per_capita_usd` | float | 0.0 | GDP, tăng trưởng GDP, GDP đầu người của nước nhập khẩu |
| `importer_population` | int | 0.0 | Dân số |
| `importer_inflation_pct`, `importer_exchange_rate_lcu_per_usd` | float | ≤1.0 | Lạm phát, tỷ giá |
| `importer_exports_pct_gdp`, `importer_imports_pct_gdp` | float | 2.1 | Độ mở thương mại |
| `importer_co2_per_capita_t`, `importer_renewable_energy_pct` | float | 5.5 / 24.2 | Hai biến môi trường, dùng cho GLPI biến thể 3/4 |
| `exporter_gdp_usd`, `exporter_gdp_growth_pct`, ... | float | 0.0 | Y hệt nhưng cho Việt Nam (`exporter` luôn VNM — hằng số theo năm, không theo importer) |
| `log_gdp_d`, `log_gdpcap_d`, `log_pop_d` | float | 0.0 | `ln()` của ba biến GDP/GDP-đầu-người/dân-số nước nhập khẩu — đúng tên B3 dùng |
| `log_gdp_d_lag1`, `log_gdpcap_d_lag1`, `log_pop_d_lag1` | float | 1.6 | bản t−1, lag theo `(importer)` |
| `importer_gdp_growth_pct_lag1`, `importer_inflation_pct_lag1`, `importer_exchange_rate_lcu_per_usd_lag1`, `importer_imports_pct_gdp_lag1`, `importer_exports_pct_gdp_lag1` | float | 1.6–2.9 | bản t−1 của các biến tương ứng |

### 8b. Logistics Performance Index (LPI) — World Bank, theo đợt khảo sát

Chỉ có ở các năm khảo sát thật (2007, 2010, 2012, 2014, 2016, 2018, 2022);
các năm khác mang giá trị đợt khảo sát **gần nhất trước đó** — `importer_lpi_source_year`
ghi rõ năm nào. Từ v2, các năm **trước đợt đầu tiên** để trống (v1 lấy đợt
đầu, tức là giá trị của tương lai), nên %null dưới đây của v1 thấp hơn thực tế v2.

| Cột | %null | Ý nghĩa |
|---|---:|---|
| `importer_lpi_overall` | 0.7 | Điểm LPI tổng hợp |
| `importer_lpi_customs`, `_infrastructure`, `_intl_shipments`, `_logistics_competence`, `_tracking_tracing`, `_timeliness` | 0.7 | 6 chỉ số con LPI |
| `importer_lpi_source_year` | 0.7 | Năm khảo sát thật được mang sang dòng này |

### 8c. Gravity — CEPII Gravity V202211

| Cột | Kiểu | %null | Ý nghĩa |
|---|---|---:|---|
| `dist`, `distw_harmonic`, `distcap` | int | 0.0 | Khoảng cách địa lý (km), ba cách tính khác nhau |
| `log_dist` | — | *(chưa có cột riêng trong file — tính bằng `ln(dist)` khi cần, vì `dist` không thay đổi theo năm nên không cần lag)* | |
| `contig` | int (0/1) | 0.0 | Có chung biên giới |
| `comlang_off`, `comlang_ethno` | int (0/1) | 0.0 | Chung ngôn ngữ chính thức / ngôn ngữ dân tộc |
| `comcol`, `col45` | int (0/1) | 0.0 | Từng là thuộc địa của nhau / thuộc địa sau 1945 |
| `comrelig` | float | 0.2 | Chỉ số tương đồng tôn giáo |
| `comleg_posttrans` | int (0/1) | 0.0 | Hệ pháp luật hậu-chuyển-đổi giống nhau |
| `diplo_disagreement` | float | 32.2 | Chỉ số bất đồng ngoại giao (UN voting) |
| `gatt_d`, `wto_d`, `eu_d` | int (0/1) | 0.0 | Thành viên GATT/WTO/EU |
| `fta_wto` | int (0/1) | 0.0 | Có FTA được thông báo lên WTO |
| `rta_coverage`, `rta_type` | int | 58.8 | Phạm vi/loại hiệp định khu vực (chỉ có khi có RTA) |
| `entry_cost_d`, `entry_proc_d`, `entry_time_d` | float | 37.6 | Chi phí/thủ tục/thời gian gia nhập thị trường (Doing Business) |
| `gravity_source_year` | int | 0.0 | CEPII Gravity dừng ở 2020 — năm 2021–2025 mang giá trị 2020 (carry-forward), cột này ghi năm thật |

*Các biến gravity thời-bất-biến (dist, contig, comlang…) không có bản `_lag` —
không có gì để lag, giá trị năm nào cũng như nhau.*

### 8d. Hiệp định thương mại (DESTA) & phòng vệ thương mại (TTBD, Bown 2016)

| Cột | Kiểu | %null | Ý nghĩa |
|---|---|---:|---|
| `fta_in_force`, `any_agreement_in_force`, `gstp_in_force` | int (0/1) | 0.0 | Có FTA/ưu đãi đang hiệu lực |
| `n_agreements` | int | 0.0 | Số hiệp định đang hiệu lực |
| `first_fta_year`, `years_since_fta` | int | 55.4 | Năm FTA đầu tiên có hiệu lực / số năm kể từ đó (null nếu chưa từng có FTA) |
| `fta_names` | str | 55.4 | Danh sách tên hiệp định |
| `ad_initiated`, `ad_in_force` | int (0/1) | 0.0 | Có vụ điều tra/áp thuế chống bán phá giá |
| `cvd_initiated`, `cvd_in_force` | int (0/1) | 0.0 | Thuế chống trợ cấp |
| `sg_initiated`, `sg_in_force` | int (0/1) | 0.0 | Biện pháp tự vệ |
| `ttb_any_in_force` | int (0/1) | 0.0 | Bất kỳ biện pháp phòng vệ nào đang hiệu lực |
| `ttbd_observed` | int (0/1) | 0.0 | 1 nếu năm nằm trong phạm vi TTBD (≤ 2015). **Từ v2, mọi cột `ad_*`, `cvd_*`, `sg_*`, `ttb_any_in_force` để trống khi `ttbd_observed = 0`** — v1 mang các biện pháp cũ sang và ghi 0 cho mọi vụ mới |

**Giới hạn quan trọng:** TTBD (Bown 2016) chỉ ghi nhận **initiation đến
2015** — dùng các cột này cho giai đoạn sau 2015 nghĩa là giả định "không có
vụ mới", không phải "chắc chắn không có". Nêu rõ trong Limitations nếu dùng ở
B8.

---

## 9. Nhóm bổ sung — không bắt buộc theo B0, nhưng sẵn sàng cho robustness (B8) và XAI (B7)

### 9a. Rào cản phi thuế quan (NTM) — hai nguồn khác nhau, đừng nhầm

| Nguồn | Cột | Đơn vị thời gian | Ghi chú |
|---|---|---|---|
| **WITS 3 file công khai** (`ntm_*`) | `ntm_coverage_ratio`, `ntm_frequency_ratio`, `ntm_sps_coverage`, `ntm_tbt_coverage`, `ntm_quantity_coverage`, `ntm_technical_coverage`, `ntm_nontechnical_coverage`, `ntm_n_types`, `ntm_sector_freq_any`, `ntm_sector_share_3plus` | **1 snapshot/nước**, không theo năm (%null 19.2 — 20% episode không có, TQ/Hàn Quốc nằm trong số này) | `ntm_survey_year` ghi năm khảo sát; `ntm_reporter`/`ntm_sector` là khoá join |
| **TRAINS researcher file, ở HS6×năm** (`ntm6_*`) | `ntm6_all_survey`, `ntm6_sps_survey`, `ntm6_tbt_survey`, `ntm6_bilateral_survey`, `ntm6_all_inforce`, `ntm6_sps_inforce`, `ntm6_tbt_inforce`, ... | Đúng theo năm khảo sát gần nhất (`ntm6_source_year`) | **Ưu tiên dùng khối này cho B5/B7** — đúng đơn vị HS6×năm mà thiết kế B0 cần, thay vì snapshot cấp-nước của khối `ntm_*`. Từ v2: để trống (không phải 0) trước đợt khảo sát đầu tiên của reporter và ở family không có mã HS2012 nào (`ntm6_mappable = 0`); reporter EU theo năm (HRV đọc biểu riêng tới 2012) |
| | `ntm_ave_border_pct`, `ntm_ave_border_simple_pct` | theo năm (`ntm_ave_source_year`) | Ad-valorem equivalent của NTM, ước lượng GTAP — %null 6.2 |

### 9b. Độ phức tạp sản phẩm/kinh tế — Harvard Growth Lab Atlas v18

| Cột | %null | Ý nghĩa |
|---|---:|---|
| `pci` | 0.0 | Product Complexity Index của `product_family` (theo HS92 4-digit, `product_hs4`) |
| `pci_source_year` | 0.0 | Năm PCI thật được mang sang (Atlas dừng ở một năm nhất định, carry-forward sau đó) |
| `importer_eci`, `importer_coi`, `importer_diversity` | 0.0 | Economic Complexity Index, Complexity Outlook Index, số sản phẩm xuất khẩu có RCA>1 — của **nước nhập khẩu** |
| `exporter_eci` | 0.0 | ECI của Việt Nam (hằng số theo năm) |

### 9c. Green Logistics Performance Index — 4 biến thể, chọn một khi dùng

`build_glpi.py` dựng **4 công thức khác nhau** vì literature chưa thống nhất
— đừng dùng cả 4 cùng lúc trong một mô hình (đa cộng tuyến gần như tuyệt đối).

| Cột | %null | Công thức | Khuyến nghị |
|---|---:|---|---|
| `importer_glpi_pca_lpi_epi` | 2.8 | PCA trên (LPI, EPI) đã min-max hoá | **Dùng cái này làm mặc định** — El-Nakib & Elzarka (2026), bản mới nhất, khắc phục nhược điểm của bản ratio |
| `importer_glpi_ratio_lpi_epi` | 4.8 | Dạng tỷ lệ LPI/EPI | bản dự phòng B8 yêu cầu; **chưa đọc được công thức 2024 gốc** (trả phí) — đây là bản tái tạo theo mô tả gián tiếp, kiểm tra lại nếu trích dẫn |
| `importer_glpi_pca_components` | 23.5 | PCA trên 6 chỉ số con LPI + 2 biến môi trường | biến thiên theo năm ở phần môi trường — %null cao hơn vì phụ thuộc cả LPI (theo đợt khảo sát) lẫn môi trường |
| `importer_glpi_equal_weights` | 23.5 | Trung bình cộng thay vì PCA của biến thể trên | dùng để kiểm tra ranking có bền với PCA hay không |

### 9d. Cú sốc chung theo năm (không biến thiên theo nước/sản phẩm)

| Cột | %null | Ý nghĩa |
|---|---:|---|
| `cmo_all_commodities`, `price_agriculture`, `price_energy`, `price_food`, `price_metals__minerals`, ... (15 chỉ số) | 0.0 | Chỉ số giá hàng hoá thế giới, World Bank "Pink Sheet", danh nghĩa, theo năm |
| `gepu_current`, `gepu_months` | 0.0 | Global Economic Policy Uncertainty Index (Baker–Bloom–Davis), trung bình năm |

Dùng cho **B8 #5/ mô hình frailty tương quan** — đây là kênh sốc *chung* duy
nhất trong panel (mọi nước/sản phẩm cùng chịu), cần cho khi kiểm định "các
lần chết có độc lập không".

### 9e. Ngoài phạm vi B0 (EU-27) — giữ lại cho bài khác, không dùng cho Paper A

| Cột | %null | Ý nghĩa | Vì sao ngoài scope |
|---|---:|---|---|
| `cbam_in_scope`, `cbam_sector`, `cbam_partial`, `cbam_reporting_share`, `cbam_definitive` | 73.4 | Phạm vi CBAM (Regulation EU 2023/956) — chỉ gắn cho EU27 | CBAM là **Stage 2 / bài khác**, không phải biến của Stage 1. Lưu ý: giai đoạn chuyển tiếp 10/2023–12/2025 chỉ là nghĩa vụ báo cáo, chưa phải chi phí thật — `cbam_definitive` luôn 0 trong cửa sổ panel |
| `us_recip_rate_yearend`, `us_recip_rate_peak`, `us_recip_floor`, `us_transship_rate`, `us_recip_effective_from`, `us_recip_exempt_share`, `us_recip_exempt_full` | 96.1–99.8 | Thuế đối ứng Mỹ 2025 (chương 99 HTS Mỹ) | B0 chốt importer = EU-27, không phải Mỹ — các cột này chỉ có giá trị khi `importer == "USA"`, một nhánh nhỏ ngoài mẫu chính |

---

## 10. Bảng tra nhanh: biến nào dùng cho khối nào của Stage 1

| Khối | Biến chính |
|---|---|
| **B4 — Kaplan–Meier, cắt lát theo staging** | `duration` (= `t_stop`), `event`, `right_censored` (tự tính từ `spell_id`/`t_start`/`t_stop` hoặc join `data/interim/spells.csv`), cắt theo `staging_cat`, `hs2`, quy mô thị trường (`importer_gdp_usd`) |
| **B5 — cloglog M0→M3** | M1: `log_value_lag`, `vn_market_share_pct_lag1`, `unit_value_usd_per_kg_lag1`, `volatility_3y_lag1`, `growth_lag_pct` · M2: + `log_gdp_d_lag1`, `log_gdpcap_d_lag1`, `log_pop_d_lag1`, `contig`, `comlang_off`, `log_total_import_cp_lag1` · M3: + `tariff_applied_lag`/`tariff_rate_lag1`. Cluster SE theo `(importer, hs2)` |
| **B6 — Identification EVFTA** | `pref_margin_lag` (hoặc `pref_margin_pp` nếu chọn không lag treatment — xem tranh luận trong docstring `build_stage1_df.py`), `staging_cat`, `years_since_evfta_policy`, FE theo `importer`/`hs2`/`year` |
| **B7 — ML/XAI** | Toàn bộ cột `_lag1`/`_lag` (đặc trưng), split theo `year` (2012–2020 / 2021–2022 / 2023–2024), KHÔNG random split |
| **B8 — Robustness** | ngưỡng: dựng lại từ `data/interim/episodes.csv` ở ngưỡng khác · gap rule: đổi `GAP_TOLERANCE` trong `build_spells.py` · loại 2020–2021: filter `year` · Cox: `t_start`/`t_stop`/`event` · 147 thị trường: bỏ filter EU27 |
| **B9 — Bảng bàn giao Stage 2** | `importer`, `product_family`, `year`, dự báo `S_hat`/`S_hat_lo`/`S_hat_hi` (đầu ra mô hình, chưa có trong file này), `import_value_usd` (làm `value_expected`), `staging_cat` |

---

## 11. Việc còn lại trước khi chạy B4–B9 (không phải vấn đề dữ liệu)

1. **`data/interim/panel_final.csv` cần rebuild lại một lần** để B4–B9 dùng
   đúng `stage1_panel.parquet` này — đã làm xong, file hiện tại phản ánh:
   `GAP_TOLERANCE=1`, spell left-truncated được giữ (không loại bỏ), 5 biến
   B3 còn thiếu đã tính, mọi covariate đã có bản lag t−1.
2. Một lỗi nguồn trong `build_spells.py::attach()` (trước khi có `_rnd()`):
   `rca`, `product_share_pct`, `partner_share_pct`, `vn_market_share_pct`,
   `country_growth_pct`, `world_growth_pct` từng ghi ra text `"nan"` thay vì
   ô trống khi không tính được, khiến các cột này đọc lên thành **kiểu chuỗi**
   thay vì số ở bất kỳ công cụ nào tự suy kiểu từ CSV. `build_spells.py` đã
   sửa tận gốc (hàm `_rnd()`), nhưng `data/interim/panel_final.csv`/
   `episodes.csv` trên đĩa **vẫn là bản dựng trước khi sửa** (rebuild lại hai
   file này là job nặng — grid 1,86 triệu ô × 147 nước — chưa chạy lại).
   `scripts/build_stage1_df.py` tự bọc quanh vấn đề này ở cả hai lượt đọc CSV
   (`CSV_NULLS = ["", "nan"]`), nên **`stage1_panel.parquet`/`.csv` — file bàn
   giao thật sự — đã được xác minh trực tiếp: cả 9 cột trên (6 cột gốc + 3 bản
   `_lag`) đều là `Float64`, 0 ô mang text `"nan"`**. Chỉ cần thận trọng khi
   đọc thẳng `panel_final.csv`/`episodes.csv` (không qua `build_stage1_df.py`)
   — lúc đó nhớ truyền `null_values=["", "nan"]` cho CSV reader.
3. B5 (cloglog M0–M3, frailty, cluster SE), B6 (event-study, placebo,
   heterogeneity), B7 (RSF/GBM/DeepHit, SHAP) — **chưa chạy**. Thư viện cần:
   `lifelines`, `statsmodels`, `scikit-survival` **chưa cài** trên máy này.
4. Ba quyết định cần chốt với người hướng dẫn (không phải thiếu dữ liệu):
   BACI hay Comtrade làm nguồn chính, HS2012 thuần hay product family H0, và
   cách xử lý spell một-năm (~44% spell EU27 chỉ sống 1 năm ngay cả sau khi
   áp gap rule) — chi tiết: `docs/DOI_CHIEU_B0_VOI_DU_LIEU.md` §5.
