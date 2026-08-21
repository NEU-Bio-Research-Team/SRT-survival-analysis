# Bộ dữ liệu survival analysis cho xuất khẩu Việt Nam (WITS + Comtrade)

Dự án thu thập và dựng bộ dữ liệu **spell-level** để chạy mô hình survival
(Kaplan-Meier / Cox) trên tuổi thọ của **quan hệ xuất khẩu của Việt Nam** ở mức
tariff-line.

*Trạng thái trong tài liệu này được đo trực tiếp trên đĩa lúc **21/08/2026**.
Mọi con số đều là số thật, không phải ước lượng từ tài liệu cũ.*

> **Định hướng nghiên cứu:** [docs/TONG_HOP_Y_TUONG.md](docs/TONG_HOP_Y_TUONG.md)
> hợp nhất hai tài liệu ý tưởng. **Tiến độ ý tưởng ↔ dữ liệu:**
> [docs/MAPPING_IDEA_DATA.md](docs/MAPPING_IDEA_DATA.md) — đọc cái này để biết
> đang ở đâu.

---

## ĐỌC TRƯỚC TIÊN — 3 điều quan trọng nhất

1. **Thiết kế đã đổi: exporter chỉ còn Việt Nam.** Importer không còn bị chốt ở
   53 nước chọn tay nữa — **mọi nước có đủ dữ liệu đều được đưa vào, tổng 147
   nước**, phần bị loại được ghi rõ lý do từng nước. Chi tiết vì sao và đổi
   những gì: [docs/THIET_KE_VIET_NAM.md](docs/THIET_KE_VIET_NAM.md).
2. **Đổi thiết kế làm khối lượng tải giảm khoảng 100 lần.** Đường găng cũ là
   ~150 giờ tải trade; nay chỉ cần **partner = Việt Nam** nên toàn bộ trade tải
   xong trong ~2 giờ. Ngân sách tiết kiệm được dùng để tải thêm **nhập khẩu từ
   toàn thế giới** — nhờ đó RCA/world growth mới có mẫu số thật.
3. **Panel đã dựng xong và dùng được — cửa sổ nay là 2003–2023.**
   Toàn bộ trade (147/147 nước), mẫu số thế giới và ba pha 2022–2024 đã tải
   xong; `build_spells.py` → `merge_panel.py` chạy lại lúc 21/08 và cho
   **647.014 episode × 91 cột**, `rca` / `vn_market_share_pct` /
   `world_growth_pct` **100% độ phủ và có phương sai thật**. Điểm nghẽn còn lại
   không phải dữ liệu mà là **biểu thuế dừng ở 2021** (mục 3.1) và **chưa chạy
   mô hình survival nào**.

---

## 1. Thiết kế nghiên cứu (đã chốt)

| Chiều | Giá trị đã chốt | Chốt bằng cách nào |
|---|---|---|
| Cửa sổ thời gian | **2002–2023** (22 năm; spell chạy 2003–2023) | Đã kéo thêm 2022–2024 ngày 21/08. Dừng ở 2023: năm 2024 có 17 nước chưa nộp và VN chưa nộp gì cả. ⚠️ TRAINS vẫn chỉ có biểu thuế tới 2021 — mục 3.1 |
| **Exporter** | **Việt Nam** (Comtrade 704) | yêu cầu của nhóm nghiên cứu |
| **Importer** | **147 nước** — mọi nước đủ điều kiện, không chốt số | quy tắc 3 điều kiện ở mục 1.1 |
| Đơn vị sản phẩm | **HS 6-digit**, gom thành *product family* ổn định qua các phiên bản HS | 25.981 liên kết concordance H1→H0 … H5→H0 |
| Đơn vị quan sát | spell của cặp `(importer j, product family k)` cho hàng Việt Nam | |
| Ngưỡng tồn tại | nhập khẩu ≥ **10.000 USD**/năm | đúng ngưỡng WITS dùng trong Trade Outcomes |
| Kiểm duyệt | spell bắt đầu 2002 → **left-censored, loại**; còn sống 2023 → **right-censored, giữ, `event=0`**. Nước ngừng khai sớm (RUS, BLR, BGD, KNA, LCA, SLB) → kiểm duyệt hành chính tại năm cuối cùng khai, **không tính là chết** | |
| Hướng biến thuế | thuế **nước nhập khẩu áp lên hàng Việt Nam** (TRAINS: reporter = importer, partner = 704) | |

### 1.1. Quy tắc chọn importer — không còn chọn tay

Một nước vào panel khi **đủ cả ba** trong 2002–2021:

> ⚠️ Bảng sàng lọc chỉ chạy tới **2021**. Với 2022–2024 không có phép kiểm tra
> độc lập nào để phân biệt "nước đó không nhập gì" với "chưa tải xong" —
> `build_spells.py` xử lý bằng cách kiểm duyệt hành chính 6 nước ngừng khai sớm,
> nhưng đây vẫn là chỗ yếu nhất của hai năm cuối.

| # | Điều kiện | Nguồn kiểm chứng | Vì sao bắt buộc |
|---|---|---|---|
| 1 | có nộp dữ liệu HS hằng năm cho UN Comtrade | `getDA` | nhập khẩu từ VN ở mức HS6 phải do chính nước đó khai |
| 2 | có biểu thuế trong TRAINS (của mình, hoặc dùng chung `EUN` của EU) | `dataavailability` | không có thì biến Tariff thiếu **có hệ thống**, không phải thiếu ngẫu nhiên |
| 3 | thực sự có khai nhập khẩu từ Việt Nam | sàng lọc `cmdCode=TOTAL` | nước khai đủ nhưng không buôn bán với VN sẽ chỉ là dòng toàn số 0 |

Thay vì cắt cứng, các nước được **xếp hạng**:

| Hạng | Năm Comtrade | Năm thuế | Năm có trade với VN | Số nước | Vào panel |
|---|---|---|---|---|---|
| **A** | 20 | ≥ 15 | ≥ 15 | **102** | ✅ |
| **B** | ≥ 15 | ≥ 10 | ≥ 10 | **45** | ✅ |
| **C** | không đạt A lẫn B | | | 46 | ❌ có ghi lý do từng nước |

Cột `tier` nằm trong file, **không lọc sẵn** — muốn kiểm định robustness chỉ trên
hạng A thì lọc lúc chạy mô hình.

**Phân bố 147 importer trong panel:**

| Nhóm thu nhập | Số nước | | Khu vực | Số nước |
|---|---|---|---|---|
| High income | 60 | | Europe & Central Asia | 42 |
| Upper middle income | 45 | | Sub-Saharan Africa | 35 |
| Lower middle income | 30 | | Latin America & Caribbean | 29 |
| Low income | 12 | | East Asia & Pacific | 19 |
| | | | Middle East & North Africa | 15 |
| | | | South Asia | 4 |
| | | | North America | 3 |

**Danh sách hạng A (102 nước):**
ALB ARE ARG ARM AUS AUT BDI BEL BEN BFA BGR BHR BLR BLZ BOL BRA BWA CAF CAN CHL
CHN CIV COL CRI CYP CZE DEU DNK DOM ECU EGY ESP EST FIN FJI FRA GBR GEO GRC GTM
GUY HKG HRV HUN IDN IND IRL ISL ISR ITA JOR JPN KGZ KOR LTU LUX LVA MAC MAR MDA
MDG MDV MEX MKD MLT MOZ MUS MYS NAM NER NIC NLD NOR NZL OMN PAN PER PHL POL PRT
PRY QAT ROU RUS RWA SAU SEN SGP SLV SVK SVN SWE SWZ TUR TZA UGA UKR URY USA VCT
ZAF ZMB

**Danh sách hạng B (45 nước):**
AGO ATG AZE BGD BIH BMU BRB BRN CMR COG COM CPV DMA DZA ETH GAB GHA GMB GRD HND
JAM KAZ KEN KHM KNA KWT LBN LCA LKA LSO MLI MNG MRT MWI NGA PAK PYF SLB SUR SYC
TGO THA TON TTO TUN

Đầy đủ kèm số liệu từng nước: [selection/importers_vn.csv](selection/importers_vn.csv).
Cả 46 nước bị loại kèm lý do: [selection/importer_vn_all.csv](selection/importer_vn_all.csv).

**15 thị trường lớn nhất** (nhập khẩu từ VN do chính nước đó khai báo):

| # | Nước | TB các năm (tỉ USD) | Năm 2021 (tỉ USD) | Hạng |
|---|---|---|---|---|
| 1 | USA | 31,3 | 108,2 | A |
| 2 | CHN | 25,5 | 92,3 | A |
| 3 | JPN | 12,2 | 23,0 | A |
| 4 | KOR | 8,1 | 24,0 | A |
| 5 | DEU | 6,3 | 12,5 | A |
| 6 | HKG | 4,8 | 15,1 | A |
| 7 | AUS | 3,5 | 5,4 | A |
| 8 | GBR | 3,5 | 6,3 | A |
| 9 | FRA | 3,4 | 6,6 | A |
| 10 | MYS | 3,3 | 5,7 | A |
| 11 | NLD | 2,9 | 7,3 | A |
| 12 | THA | 2,9 | 7,0 | **B** |
| 13 | ARE | 2,6 | 7,6 | A |
| 14 | SGP | 2,6 | 4,4 | A |
| 15 | IND | 2,4 | 7,1 | A |

27 nước có kim ngạch trên 1 tỉ USD/năm. Tổng 147 nước phủ **99,5%** giá trị xuất
khẩu của Việt Nam (đo ở năm gần nhất mỗi nước) — phần bị loại là nhiễu, không
phải thị trường thật.

---

## 2. Đã lấy được những gì

### 2.1. Bảng tiến độ tải — đo trên đĩa 21/08/2026

Kiểm kê đầy đủ, từng con số đếm bằng cách đọc thẳng file:
**[docs/DATA_INVENTORY_VN.md](docs/DATA_INVENTORY_VN.md)**.

| Nguồn | Đã có | Trạng thái |
|---|---|---|
| **Trade VN→importer** (Comtrade, HS6) | **3.216** file importer-năm · **1.473.471** ô VNM · **147/147 nước** · **6.225** mã HS6 (27.801 cặp phiên bản×mã, 27.800 ánh xạ được) | ✅ **đủ 2002–2024, 0 lỗ hổng** |
| **Trade importer→thế giới** (mẫu số RCA) | **3.260** file · 107.022 family-năm khớp được vào panel VN | ✅ **xong** |
| **Trade mirror** (VN tự khai) | **40** file · 933.834 dòng | ✅ 100% (VN chưa nộp 2024) |
| **Tariff MFN** (WITS TRAINS) | **2.250** reporter-năm · 134 reporter | ⚠️ **chỉ tới 2021** — mục 3.1 |
| **Tariff PREF cho VN** | **72** reporter-năm · **13 nước** · 237.414 dòng | ⚠️ chỉ tới 2021; đã hỏi hết 2.435 reporter-năm |
| **Vĩ mô** (`macro_panel_v2.csv`) | **3.404** nước-năm · 147 nước + VN · 9 biến | ✅ (Romania đã đủ) |
| **NTM công khai** (3 file WITS) | 1.200 + 3.944 + 150 dòng · 75 nước | ✅ 100% (nhưng time-invariant, mục 3.2) |
| **Concordance HS** | **6/6** bảng (thêm H6→H0 cho HS2022) | ✅ 100% |
| **FTA / TTB / Gravity / Shocks** | 4 panel, xem [docs/COVARIATES_ADDED.md](docs/COVARIATES_ADDED.md) | ✅ đã merge vào panel |
| **Sàng lọc đối tác VN** | 3.569 nước-năm, cả hai chiều mirror | ✅ 100% |
| **Kiểm chứng API** | 22 phép thử `probe_out/` | ✅ 100% |

> Số file nhỏ hơn 147 × 23 = 3.381 không phải thiếu: chênh lệch là những
> importer-năm mà nước đó **thật sự không nhập gì từ Việt Nam** hoặc năm đó
> không nộp báo cáo. Đối chiếu với bảng sàng lọc cho **0 lỗ hổng trên cả 147
> nước**, ở cả 2021, 2023 lẫn 2024.

**Sản phẩm đã dựng ra** (`build_spells` 21/08 14:26 · `merge_panel` 21/08 14:53):

| File | Kích thước | Nội dung |
|---|---|---|
| `analysis/spells.csv` | 15 MB | **205.607 spell** — 151.858 chết, 53.749 right-censored (26,1%) |
| `analysis/episodes.csv` | 77 MB | 647.014 episode-năm, 17 cột lõi |
| `analysis/panel_final.csv` | 331 MB | **647.014 × 91 cột** — file để chạy mô hình |

Kiểm tra lại bất cứ lúc nào:

```bash
ls data_raw/trade       | wc -l    # 3.216
ls data_raw/trade_world | wc -l    # 3.260
ls data_raw/tariffs/mfn | wc -l    # 2.250 — dừng ở 2021, cần kéo tiếp
ls data_raw/tariffs/pref/*_704.csv.gz | wc -l   # 72, ưu đãi dành cho VN
```

⚠️ **Comtrade có quota theo ngày, trả `403` khi hết** — khác hẳn `429` (throttle
vài giây). Script **dừng ngay khi gặp 403** và in ra thời điểm quota nạp lại,
thay vì đốt hết các job còn lại rồi đánh dấu "failed". Pha `world` vì thế phải
chạy nhiều ngày, mỗi ngày một đợt.

### 2.2. 11 biến yêu cầu — nguồn và mức chi tiết

| # | Biến | Nguồn thật sự dùng | Mức chi tiết |
|---|---|---|---|
| 1–2 | Trade value XK/NK | **UN Comtrade API** (có key) | HS6 × importer × năm |
| 3 | Tariff | WITS `TRN`, MFN + PREF cho partner 704, lấy mức thấp hơn | HS6 |
| 4 | RCA (Balassa) | tự tính, mẫu số = **nhập khẩu thế giới** | HS6 family |
| 5 | Product share | tự tính | HS6 family |
| 6 | Partner share | tự tính | importer × năm |
| 7 | Country growth | tự tính — **tăng trưởng XK của VN theo từng sản phẩm** | HS6 family |
| 8 | World growth | tự tính — **tăng trưởng nhập khẩu thế giới theo sản phẩm** | HS6 family |
| 9 | HHI thị trường + sản phẩm | tự tính (Herfindahl) | năm |
| 10 | **NTM** | 3 file công khai WITS | cấp ngành, 1 lát cắt/nước ⚠ mục 3.2 |
| 11 | GDP growth | WITS `tradestats-development` (WDI) | nước × năm |
| **+** | `vn_market_share_pct` **(mới)** | tự tính từ hai luồng trade | importer × HS6 family × năm |

> **Vì sao biến 4–9 phải tự tính:** WITS API chỉ cho các chỉ số này ở **31 nhóm
> ngành**, không có HS6 (`Invalid_Product` khi truyền mã HS6) — chi tiết ở
> [docs/KIEM_CHUNG_DU_LIEU_WITS.md](docs/KIEM_CHUNG_DU_LIEU_WITS.md) §3.1.
>
> **Ba biến phải định nghĩa lại vì chỉ còn một exporter:** country growth và
> world growth trước đây tính trên tổng xuất khẩu của cả nước → với một exporter
> sẽ thành **một con số mỗi năm**, trùng hoàn toàn với hiệu ứng năm và vô dụng
> trong Cox. Nay cả hai tính **theo từng sản phẩm**, đúng cách WITS định nghĩa
> trong Trade Outcomes. RCA cũng đổi mẫu số từ "tổng trong mẫu" sang **nhập khẩu
> thế giới thật**.

---

## 3. Còn thiếu những gì

### 3.0. Đã bổ sung 19–20/08/2026 — xem [docs/COVARIATES_ADDED.md](docs/COVARIATES_ADDED.md)

Bốn nguồn công khai, **không cần tài khoản**, đã tải và dựng xong:

| File | Vá lỗ hổng nào |
|---|---|
| `analysis/fta_vn.csv` | Ưu đãi khai theo mã nhóm (mục 3.3). Tỉ lệ episode biết chắc có ưu đãi: **8,0% → 38,8%**; 44 nước đổi trạng thái trong 2002–2021 |
| `analysis/ttbd_vn.csv` (+ `_cases`, `_products`) | **Rào cản duy nhất biến thiên theo thời gian**: 69 vụ AD/CVD nhắm vào VN + safeguard toàn cầu, kèm 3.231 mã HS. Dừng ở 2015Q4 |
| `analysis/gravity_vn.csv` | Biến kiểm soát chuẩn của literature trade-duration (khoảng cách, chung biên giới, ngôn ngữ, thuộc địa) — trước đây không có |
| `analysis/shocks_annual.csv` | Sốc chung cho Level 5: 17 chỉ số giá hàng hoá + chỉ số bất định chính sách toàn cầu |
| `analysis/macro_panel_v2.csv` | **Romania đã đủ 20 năm GDP**; thêm tỷ giá, lạm phát, dân số, LPI |

Cả bốn panel khoá `(importer, year)`, **đã merge thật vào `panel_final.csv`
ngày 21/08 với 0 dòng lệch** (gravity khớp 84,2% vì CEPII dừng ở 2021 — xem
mục 3.1).

```bash
python3 scripts/fetch_covariates.py   # tải, resume được
python3 scripts/build_covariates.py   # dựng panel
```

### 3.1. Thiếu do tải chưa xong (chỉ cần thời gian máy + quota)

| Hạng mục | Trạng thái 21/08 |
|---|---|
| Trade VN→importer | ✅ xong, kể cả 2022–2024 |
| Trade importer→thế giới | ✅ xong, 404/404, 0 failed |
| Trade mirror | ✅ xong (VN chưa nộp 2024 → mirror dừng 2023) |
| Dựng lại `spells.csv` → `panel_final.csv` | ✅ **đã chạy, đã kiểm tra đạt** |
| **Tariff 2022–2023** | ❌ **CHƯA TẢI — điểm nghẽn số 1** |

Trade phía Việt Nam đã phủ **toàn bộ 147 nước**; pha `world` cũng vậy. Đối chiếu
bảng sàng lọc cho **0 lỗ hổng** ở cả 2021, 2023 lẫn 2024.

> ✅ **Cảnh báo cũ đã được gỡ.** `panel_final.csv` bản 19/08 có `rca` = 1,0 ở mọi
> dòng và `vn_market_share_pct` trống 100% vì được dựng trước khi pha `world`
> xong; `load_world()` cũng từng OOM trên máy 5,6 GB RAM. Cả hai đã sửa. Bản
> 21/08 cho `rca` p25 = 0,23 · trung vị 0,83 · p75 = 2,94, và cả ba biến mẫu số
> đạt **100% độ phủ**.

> ⚠️ **Điểm nghẽn còn lại: `scripts/fetch_tariffs.py:46` vẫn là
> `YEARS = list(range(2002, 2022))`.** Trên đĩa không có file thuế nào cho
> 2022–2023, nên hai năm cuối của panel chỉ có thuế **mang sang từ 2021**
> (carry-forward ≤ 3 năm: 90.721 episode = 14,0% panel):
>
> | Năm | Episode | Có thuế |
> |---|---|---|
> | 2003–2021 | 605.780 | 98,6–100% |
> | **2022** | 49.989 | **75,3%** — toàn bộ là carry-forward |
> | **2023** | 52.245 | **74,3%** — toàn bộ là carry-forward |
>
> Nghĩa là **hai năm cuối không có biến thiên thuế thật**. Sửa một dòng thành
> `range(2002, 2024)` rồi chạy lại `fetch_tariffs.py --pass all` →
> `merge_panel.py`.

**Hai lỗ hổng nhỏ trong `merge_panel.py`, sửa nhanh:**

| Vấn đề | Chi tiết | Cách sửa |
|---|---|---|
| Gravity trống 2022–2023 | `dist` thiếu đúng 102.234 episode của hai năm này (độ phủ 84,2%); CEPII dừng ở 2021 — nhưng `dist`, `contig`, `comlang` **bất biến theo thời gian** | Carry-forward giá trị 2021 |
| 5 biến vĩ mô tải rồi nhưng chưa merge | `macro_panel_v2.csv` có `inflation_pct`, `exchange_rate_lcu_per_usd`, `lpi_overall`, `population`, `exports_pct_gdp`; `panel_final.csv` chỉ lấy 4 cột GDP | Mở rộng danh sách cột |

### 3.2. Thiếu do bản chất nguồn dữ liệu (NTM — điểm nghẽn lớn nhất)

Cả 3 file NTM công khai của WITS đều **không có chiều năm ở mức sản phẩm**:

| File | Dòng | Vấn đề |
|---|---|---|
| `NTM-Trade-Frequency-Coverage-Ratio` | 152 | chỉ 76 nước, chỉ 2012–2017, **không có chiều sản phẩm** |
| `NTM-Prevalence-Sector` | 3.943 | **không có cột year** |
| `NTM-Indicators-Measure-Sector` | 24.264 | **không có cột year**, sản phẩm chỉ ở mức Sector |

Ba hạn chế cố hữu còn lại:

1. **NTM là time-invariant** — một lát cắt/nước (2012–2017), ghi rõ ở cột
   `ntm_survey_year`. Đây là *thiết kế có chủ ý*, không phải sơ suất.
2. **NTM ở cấp ngành (16 nhóm), không phải HS6** — mọi sản phẩm trong cùng ngành
   nhận cùng giá trị, nên không giải thích được biến thiên **trong** ngành.
3. **Nhiều importer không có bản ghi NTM nào** — trong đó có Trung Quốc và Hàn
   Quốc. Đo trên panel 21/08: **79,6% episode** có giá trị NTM, tức **20,4%
   trống có hệ thống** (không phải trống ngẫu nhiên) — mọi mô hình dùng biến NTM
   phải khai báo điều này.

**Cái giá của việc gỡ được cả ba** đã đo bằng cách gọi thật backend TRAINS Online
(đo trên mẫu 53 importer cũ, tỉ lệ vẫn đúng hướng):

| Chỉ tiêu | WITS công khai (đang dùng) | TRAINS Online (cần tài khoản) |
|---|---|---|
| Importer có dữ liệu | 34/53 | **50/53** |
| Có ≥2 đợt khảo sát → **biến đổi theo năm** | **0** | **28** |
| Độ chi tiết sản phẩm | ngành (16 nhóm) | **HS6** |
| EU | 1 lát cắt (2016) | 15 năm (2010–2025) |

Chi tiết từng nước: [selection/ntm_availability.csv](selection/ntm_availability.csv).

### 3.3. Thuế ưu đãi khai theo nhóm — hạn chế nghiêm trọng nhất của biến thuế

**Chỉ 13 nước** khai biểu ưu đãi trực tiếp cho Việt Nam (mã 704): JPN, AUS, CHN,
CHL, KOR, ARM, KAZ, KGZ, RUS, BLR, EUN, GBR, IDN — tổng 72 reporter-năm. Đã hỏi
**đủ cả 2.435 reporter-năm**, kể cả 380 cái không có partner list để tra, nên đây
là giới hạn của TRAINS chứ không phải của việc thu thập.

Phần ưu đãi còn lại của VN được khai dưới **mã nhóm** (ASEAN, AANZFTA, danh sách
thụ hưởng GSP) mà WITS **không công bố bảng thành viên** qua API. Những episode
đó rơi về MFN → **mức thuế bị tính cao hơn thực tế**. Cột `tariff_type` đánh dấu
rõ MFN hay PREF nên vẫn nhận diện được, không bị giấu.

EU là trường hợp thiệt nhất: chỉ có 3 năm khai riêng cho VN, trong khi EU cho VN
hưởng GSP gần như suốt cửa sổ và ưu đãi EVFTA từ 2020.

### 3.4. Hai việc chỉ bạn mới làm được

| # | Việc | Vì sao tôi không tự làm được | Làm xong thì được gì |
|---|---|---|---|
| 1 | Đăng ký **trainsonline.unctad.org** → *Bulk Data Download* → tải "researcher file" → đặt vào `data_raw/ntm/trainsonline/` | Endpoint trả mảng rỗng rồi `403` nếu chưa đăng nhập; trang dùng Azure AD (MSAL) | NTM lên **HS6 × năm**, nhiều nước có biến đổi theo thời gian |
| 2 | Đăng ký API key miễn phí ở **apiportal.wto.org** (WTO I-TIP) | `data.wto.org` trả 403, `api.wto.org` trả 401 vì thiếu subscription key | Phương án dự phòng: dummy theo năm bắt đầu/kết thúc từng biện pháp |

---

## 4. Bản đồ thư mục

```
wits/
├── README.md                     ← bạn đang đọc; trạng thái tổng thể
├── .env                          ← API key Comtrade (ĐÃ gitignore, KHÔNG gửi ai)
│
├── TÓM TẮT DỰ ÁN NGHIÊN CỨU.md   ý tưởng gốc — 5 tab ứng viên + bản thẩm định
├── detail idea.md                ý tưởng gốc — thang nghiên cứu L0–L5
│
├── docs/
│   ├── TONG_HOP_Y_TUONG.md       ★★ hợp nhất hai tài liệu ý tưởng ở trên
│   ├── MAPPING_IDEA_DATA.md      ★★ ánh xạ ý tưởng ↔ dữ liệu, tiến độ đến đâu
│   ├── THIET_KE_VIET_NAM.md      ★ đổi thiết kế sang exporter = VN, đọc trước
│   ├── DATA_INVENTORY_VN.md      ★ kiểm kê chính xác dữ liệu VN đang có trên đĩa
│   ├── COVARIATES_ADDED.md       4 nguồn covariate bổ sung + mở rộng 2022–2024
│   ├── essences.txt              yêu cầu gốc về NTM
│   ├── guide.md                  khảo sát ban đầu về WITS (có chỗ sai)
│   ├── KIEM_CHUNG_DU_LIEU_WITS.md  kiểm chứng thật 22 phép thử API
│   ├── TIEN_TRINH_THU_THAP.md    nhật ký thi công
│   └── DOI_CHIEU_ESSENCES_NTM.md  đối chiếu essences.txt ↔ workspace
│
├── scripts/
│   ├── wits_probe.py             kiểm chứng API WITS → probe_out/
│   ├── select_countries.py       tải dữ liệu availability thô → selection/
│   ├── select_importers_vn.py    ★ chốt exporter = VN + xếp hạng 147 importer
│   ├── fetch_trade.py            ★ 3 pha: vn / world / mirror → data_raw/trade*/
│   ├── fetch_tariffs.py          thuế HS6, MFN + PREF cho partner 704
│   ├── fetch_macro.py            GDP + tải 3 file NTM thô
│   ├── fetch_ntm_availability.py bản đồ độ phủ NTM của TRAINS Online
│   ├── build_ntm.py              biến NTM tách theo chương MAST
│   ├── fetch_covariates.py       tải FTA/DESTA, TTBD, CEPII gravity, sốc chung
│   ├── build_covariates.py       dựng 4 panel covariate → analysis/
│   ├── pull_2022_2024.sh         mở rộng cửa sổ, 3 pha, resume được
│   ├── build_spells.py           dựng spell + RCA/HHI ở HS6
│   └── merge_panel.py            ghép tất cả → analysis/panel_final.csv
│
├── selection/    danh sách nước, availability, ánh xạ thuế EU — TRACKED trong git
├── data_raw/     dữ liệu thô — GITIGNORED
│   ├── trade/          nhập khẩu từ VN, HS6, một file/importer-năm
│   ├── trade_world/    nhập khẩu từ toàn thế giới (mẫu số RCA)
│   ├── trade_mirror/   VN tự khai xuất khẩu (đối chiếu)
│   ├── tariffs/mfn/ · tariffs/pref/ · _partnerlists.csv
│   ├── ntm/            3 file NTM công khai của WITS
│   └── concordance/    5 bảng chuyển đổi HS
├── analysis/     kết quả dựng ra — GITIGNORED, gửi qua Drive
│   ├── spells.csv       205.607 spell
│   ├── episodes.csv     647.014 episode-năm, 17 cột lõi
│   ├── panel_final.csv  647.014 × 91 cột ← file để chạy mô hình
│   └── fta_vn · ttbd_vn · gravity_vn · shocks_annual · macro_panel_v2
├── logs/         log các luồng tải — GITIGNORED
└── probe_out/    output 22 phép thử — GITIGNORED trừ _probe_log.csv
```

---

## 5. Chạy tiếp từ đúng chỗ đang dở

**Mọi script đều bỏ qua file đã tải xong**, nên cứ chạy lại là nó tiếp tục.

```bash
cd /home/minhquang/wits/scripts

# 0) (chỉ khi muốn chốt lại danh sách nước) — ~1 giờ
python3 select_importers_vn.py --refresh

# 1) Trade: VN → importer. Đây là panel chính, ~2 giờ
nohup python3 -u fetch_trade.py --pass vn > ../logs/trade_vn.log 2>&1 &

# 2) Trade: importer → thế giới. Mẫu số cho RCA / world growth / market share
nohup python3 -u fetch_trade.py --pass world > ../logs/trade_world.log 2>&1 &

# 3) Trade mirror: VN tự khai. Chỉ để đối chiếu, chạy sau cùng
nohup python3 -u fetch_trade.py --pass mirror > ../logs/trade_mirror.log 2>&1 &

# 4) Thuế: MFN rồi PREF (chỉ partner 704)
#    ⚠️ TRƯỚC KHI CHẠY: sửa fetch_tariffs.py:46 thành range(2002, 2024),
#    nếu không 2022-2023 sẽ tiếp tục trống — xem mục 3.1
nohup python3 -u fetch_tariffs.py --pass all > ../logs/tariff_vn.log 2>&1 &

# 5) Vĩ mô cho 147 nước + VN
python3 fetch_macro.py

# 5b) Covariate bổ sung: FTA, trade remedy, gravity, sốc chung
python3 fetch_covariates.py
python3 build_covariates.py

# 5c) Mở rộng cửa sổ sang 2022-2024 (đã chạy xong 21/08; resume được)
./pull_2022_2024.sh

# 6) Sau khi tải xong — dựng lại toàn bộ (BẮT BUỘC)
python3 build_ntm.py
python3 build_spells.py     # ~1,7 phút · 1,8 GB RAM
python3 merge_panel.py      # ~26 phút · 5,2 GB RAM ⚠️ đừng chạy song song thứ khác
```

⚠️ **Dùng `setsid` cho mọi lượt tải dài.** `nohup ... &` vẫn bị kill khi phiên
terminal (hoặc phiên Claude Code) kết thúc, vì tiến trình còn nằm chung process
group. Đúng cách:

```bash
setsid nohup python3 -u fetch_trade.py --pass world >> ../logs/trade_world.log 2>&1 < /dev/null &
```

⚠️ **Đừng chạy quá 2 luồng Comtrade cùng lúc.** Ba luồng trở lên là `429` xuất
hiện dày mà tổng thông lượng không tăng. TRAINS (`fetch_tariffs.py`) là host
khác nên chạy song song với Comtrade được.

**Kiểm tra bắt buộc sau khi dựng lại** — chưa đạt thì đừng tin kết quả mô hình.
Cột cuối là giá trị **thật sự đo được ở bản dựng 21/08**:

```bash
python3 -c "
import pandas as pd
s = pd.read_csv('analysis/spells.csv')
p = pd.read_csv('analysis/panel_final.csv', low_memory=False)
print('exporter duy nhất:', s.exporter.unique(), '(phải là [VNM])')
print('right-censored:', int(s.right_censored.sum()), '(PHẢI > 0)')
print('số importer:', s.importer.nunique(), '(đích 147)')
print('episode có thuế: %.1f%%' % (100*p.tariff_rate.notna().mean()), '(đích > 90%)')
print('episode có PREF: %.1f%%' % (100*p.tariff_type.eq(\"PREF\").mean()), '(0% = lại hỏng khớp mã)')
print('rca p25/med/p75:', p.rca.quantile([.25,.5,.75]).round(2).tolist(), '(toàn 1.0 = pha world chưa vào)')
print('vn_market_share trống: %.1f%%' % (100*p.vn_market_share_pct.isna().mean()), '(100% = hỏng)')
"
```

| Kiểm tra | Đích | Bản 21/08 |
|---|---|---|
| exporter duy nhất | `['VNM']` | ✅ VNM |
| right-censored | > 0 | ✅ 53.749 |
| số importer | 147 | ✅ 147 |
| episode có thuế | > 90% | ✅ 95,7% |
| episode có PREF | > 0% | ✅ 7,7% |
| `rca` có phương sai | không toàn 1,0 | ✅ 0,23 / 0,83 / 2,94 |
| `vn_market_share_pct` trống | ≈ 0% | ✅ 0% |

---

## 6. Những cái bẫy đã gặp — đừng đạp lại

1. **Comtrade trả trùng dòng theo thủ tục hải quan.** Nhiều nước (rõ nhất là
   Đức) trả **cùng một dòng HS6 tách theo `customsCode`, `motCode`,
   `partner2Code`** — khoảng 20 dòng cho 1 dòng thật. Cộng lại là **thổi phồng
   giá trị thương mại**, và làm request chạm trần 100.000 bản ghi. Lần sàng lọc
   đầu tiên vì lỗi này mà Đức trông như mua hàng Việt Nam nhiều hơn Mỹ — sai.
   Mọi request nay đều ghim `customsCode=C00&motCode=0&partner2Code=0`, và
   parser vẫn loại thêm một lần nữa cho chắc.
2. **Khớp thuế ưu đãi bằng mã sai kiểu.** `merge_panel.py` lưu PREF theo **mã số
   TRAINS** lấy từ tên file (`704`) nhưng tra cứu bằng **iso3** (`VNM`) → không
   bao giờ khớp, mọi episode âm thầm rơi về MFN. Đã sửa bằng bảng dịch mã.
3. **Mã nước lịch sử của Comtrade.** `partnerAreas.json` có nhiều bản ghi cùng
   một mã ISO3: USA nằm ở cả 840, 842 và **841 = "USA and Puerto Rico (…1980)"**;
   Đức có 276 và **280 = "Fed. Rep. of Germany (…1990)"**. Tra bảng kiểu ghi đè
   → nhận mã đã ngừng dùng → **API trả 0 dòng mà không báo lỗi**. Cách đúng: bỏ
   bản ghi có `entryExpiredDate`, bỏ nhóm (`isGroup`), lấy `entryEffectiveDate`
   mới nhất. Đúng: USA 842, DEU 276, FRA 251, VNM 704, SRB 688.
4. **Thuế EU khai một lần dưới `EUN`.** Đức, Pháp, Ý, Hà Lan, Bỉ, Tây Ban Nha
   đều hiển thị **0 năm thuế** trong TRAINS. Không xử lý → **mất trắng toàn bộ
   thị trường EU**. Đã ánh xạ từng thành viên sang `EUN` từ năm gia nhập
   ([selection/eu_tariff_mapping.csv](selection/eu_tariff_mapping.csv)); Anh dùng
   EUN đến hết 2020, biểu riêng từ 2021. Bảng này dùng lại cho cả NTM.
5. **Đổi phiên bản HS giữa chừng.** Cùng năm 2019 Rwanda dùng H4 còn Mỹ dùng H5.
   Một mã bị đánh số lại trông y hệt **một quan hệ chết đi và một quan hệ mới
   sinh ra** → hỏng toàn bộ phân tích duration. Cách xử lý: gom mã qua **thành
   phần liên thông** của đồ thị concordance → *product family* ổn định.
6. **Comtrade cắt âm thầm ở 100.000 bản ghi/call.** Pipeline tự chia nhỏ khoảng
   năm khi chạm trần, và **không bao giờ cache một importer-year rỗng**.
7. **Endpoint `bulk/v1` của Comtrade trả 401** — không nằm trong gói Free API.
   `429` là throttle tức thời, không phải quota ngày; chờ ~20s là qua.
8. **WITS API: `product=ALL` + `year=ALL` → HTTP 413.** Tối đa 2 chiều `ALL`.
9. **Sai `partner`/`product` → 404 dù chỉ số vẫn tồn tại.** Mỗi indicator có quy
   định riêng (`999` cho partner, `999999` cho product khi "không áp dụng").
10. **Hai chỗ `guide.md` nói sai:** header `Accept: application/vnd.sdmx.data+json`
    **không có tác dụng** (phải dùng `?format=JSON`); mã `GDP-CURRENT-USD`
    **không tồn tại** (dùng `NY-GDP-MKTP-KD-ZG`).
11. **Đơn vị lệch nhau:** WITS tính bằng **nghìn USD**, Comtrade tính bằng **USD**.
12. **Mã D của hai bảng NTM khác thế hệ:** file WITS cũ ghi *D = Price control*,
    TRAINS Online hiện hành ghi *D = Contingent trade protective measures*.
    **Không được trộn mã D của hai nguồn.**

---

## 7. Hạn chế cần nêu chủ động trong phần Discussion

1. **Không so sánh được giữa các nước xuất khẩu.** Chỉ có Việt Nam, nên mọi nhận
   dạng đến từ biến thiên **giữa các thị trường nhập khẩu, giữa sản phẩm và theo
   thời gian**. Câu hỏi kiểu "quan hệ của VN có chết nhanh hơn của Trung Quốc
   không" nằm ngoài tầm của bộ dữ liệu này.
2. **NTM là time-invariant** và **ở cấp ngành** — xem mục 3.2.
3. **"Thiếu dữ liệu" hay "không có biện pháp"?** — đúng vấn đề Carrère (2011)
   nêu. Xử lý ở **đúng một chỗ**, ghi rõ trong docstring `build_ntm.py`: chương
   vắng mặt trong một nước-ngành *đã được khảo sát* tính là **0**; nước **không**
   được khảo sát để **trống**, không suy diễn.
4. **Thuế ưu đãi khai theo nhóm không lấy được** — xem mục 3.3.
5. **Panel dựa trên khai báo phía nhập khẩu.** Số liệu VN tự khai được giữ riêng
   trong `data_raw/trade_mirror/` để đối chiếu; hai phía lệch nhau vì CIF/FOB,
   trung chuyển và tái xuất.
6. **Thuế của 2022–2023 là giá trị mang sang từ 2021**, không phải số thật —
   TRAINS chưa có biểu thuế cho hai năm đó và `fetch_tariffs.py` cũng chưa hỏi.
   Hai năm cuối panel vì thế **không có biến thiên thuế**. Mục 3.1.
7. **Biến trade remedy chỉ có khởi xướng vụ kiện tới 2015.** TTBD của World Bank
   dừng cập nhật tháng 6/2016. Sau đó `ttb_any_in_force` vẫn khác 0 vì một biện
   pháp không có ngày thu hồi được coi là còn hiệu lực — tức 8 năm cuối là
   **ngoại suy**, không được diễn giải hệ số cho giai đoạn đó.
8. **Nga và Belarus là mất mát vĩnh viễn, không phải độ trễ.** Nga ngừng công bố
   số liệu hải quan chi tiết từ tháng 4/2022. Vì Nga là đối tác FTA theo VN–EAEU
   (hiệu lực 2016), nếu không xử lý thì mọi spell vào Nga "chết" năm 2022 *trong
   khi hiệp định đang có hiệu lực* — mô hình hazard sẽ đọc thành "FTA giết chết
   quan hệ" và **dấu của hệ số bị lật**. `build_spells.py` đã kiểm duyệt hành
   chính 6 nước ngừng khai sớm (1.504 spell), nhưng phần Limitations vẫn phải
   nói rõ điều này.

---

## 8. Gửi gì cho cộng sự

| Gửi | Vì sao |
|---|---|
| **`analysis/`** | Bộ dữ liệu đích. `panel_final.csv` là file để chạy mô hình |
| **`selection/`** | Danh sách nước, ánh xạ EU, độ phủ NTM — cần để hiểu mẫu |
| **`docs/`** | Vì sao mọi thứ được quyết định như vậy |
| **`README.md`** | Bản đồ tổng thể |

**KHÔNG gửi:** `.env` (chứa API key Comtrade — tuyệt đối không), `data_raw/`
(chỉ gửi nếu cộng sự cần tự dựng lại panel, khi đó gửi kèm `scripts/`),
`logs/`, `probe_out/`, `__pycache__/`.

```bash
cd /home/minhquang/wits
tar czf wits_data_$(date +%Y%m%d).tar.gz analysis selection docs README.md
```

> ✅ **Cảnh báo cũ đã gỡ.** `analysis/` nay là bản dựng đúng của thiết kế
> exporter = Việt Nam, chạy 21/08 trên dữ liệu đầy đủ. **Gửi được.**
>
> ⚠️ Kèm đúng một lưu ý cho cộng sự: **thuế của 2022–2023 là giá trị mang sang
> từ 2021**, không phải số thật (mục 3.1). Đừng diễn giải hệ số thuế cho hai
> năm đó cho tới khi kéo xong biểu thuế mới.

---

## 9. Việc tiếp theo, theo thứ tự ưu tiên

Xếp hạng đầy đủ kèm lý do, đối chiếu với từng level nghiên cứu:
**[docs/MAPPING_IDEA_DATA.md](docs/MAPPING_IDEA_DATA.md) §7**.

| # | Việc | Ai làm | Chặn cái gì |
|---|---|---|---|
| — | ~~Tải nốt `--pass vn` + `--pass world` + thuế~~ | máy | ✅ xong 19/08 |
| — | ~~Sửa `load_world()` OOM, chạy lại `build_spells` → `merge_panel`~~ | máy | ✅ xong 21/08 |
| — | ~~Merge 4 panel covariate mới~~ | máy | ✅ xong 21/08 |
| — | ~~Kiểm tra right-censored > 0, importer = 147, `rca` có phương sai, PREF > 0%~~ | máy | ✅ cả 5 kiểm tra đều đạt |
| — | ~~Kéo Comtrade 2022–2024~~ | máy | ✅ xong 21/08, 0 failed |
| **1** | **Sửa `fetch_tariffs.py:46` → `range(2002, 2024)`, tải lại, `merge_panel`** | máy | Biến thiên thuế cho hai năm cuối — mục 3.1 |
| **2** | **Chạy Kaplan–Meier + Cox baseline** | máy | **Cửa quyết định của toàn bộ thang L0–L5** |
| 3 | Chốt 12 định nghĩa nghiên cứu (decision-maker, export performance, survival horizon, network definition…) | **nhóm** | Mọi thứ phía mô hình |
| 4 | Quyết cách xử lý 53,2% spell chỉ sống 1 năm | **nhóm** | Ý nghĩa của hazard ước lượng được |
| 5 | Carry-forward gravity 2022–2023 + merge 5 biến vĩ mô còn lại | máy | Bộ kiểm soát đầy đủ |
| 6 | Đăng ký TRAINS Online, tải researcher file | **bạn** | NTM lên HS6 × năm |
| 7 | Viết phần đọc file TRAINS Online, thay 11 cột NTM time-invariant | máy | phụ thuộc #6 |
| 8 | API key WTO I-TIP tại apiportal.wto.org | **bạn** | tariff actions 2025 — bắt buộc nếu chọn hướng "vòng xoáy trả đũa" |
| 9 | Kiểm duyệt biến trade-remedy ở 2015, hoặc scrape báo cáo bán niên WTO | máy | 8 năm cuối của biến này đang là ngoại suy |
