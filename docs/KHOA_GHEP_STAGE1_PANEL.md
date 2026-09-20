# `stage1_panel` được ghép từ nhiều nguồn như thế nào: khóa, cách tạo khóa, và độ tin cậy

> **Cập nhật 20/09/2026 — panel v2.** Các lỗi ở §7 đã được sửa theo
> [STAGE1_PANEL_FIX_PLAN.md](STAGE1_PANEL_FIX_PLAN.md) (kết quả:
> [audit/stage1_v2.md](audit/stage1_v2.md)). Hai điều ở dưới đã không còn đúng
> với v2: (1) §3.2 "mỗi family đúng 1 mã H0" — v2 gộp mã mồ côi vào family
> nhận hàng trong cùng HS4, family lớn nhất 10 mã (`scripts/families.py`);
> (2) §3.2 "cùng một hàm `family_of` cho mọi nguồn" — thực tế ở v1 CBAM, miễn
> trừ thuế Mỹ và NTM6 tự đọc concordance; v2 đưa cả ba về `families.py`.
> Con số 58% năm 2016 ở §7.2 là xấp xỉ bằng tập mồ côi H6; đo bằng đúng tập
> mồ côi H5 thì là 145/145 (100%).

*Viết 18/09/2026. Tài liệu này gom lại nội dung đang nằm rải rác ở 7 tài liệu cũ
(danh sách ở §9), đối chiếu lại với code hiện hành, và bổ sung các phép đo mới
trên mẫu chính B0 (Việt Nam × EU-27 không gồm UK, origin 2012–2024, 148.260 dòng
quan hệ-năm còn sống). Khi tài liệu cũ và code lệch nhau, tài liệu này theo code.*

---

## 0. Tóm tắt

1. **Không nguồn nào có sẵn một khóa chung.** Panel ghép hơn 10 nguồn. Mỗi nguồn
   định danh nước và sản phẩm theo cách riêng: mã số Comtrade, mã số TRAINS,
   ISO3, tên nước tiếng Anh, khối `EUN`; mã HS thuộc 7 revision H0–H6, hoặc CN8
   của EU.
2. **Dự án tự tạo ba khóa chuẩn:** `importer` (ISO3), `product_family` (mã
   HS1992 = H0) và `year`. Mọi nguồn được quy về ba khóa này rồi left join vào
   một khung xương `episodes` có grain `(importer, product_family, year)`.
3. **Khóa nước** là khóa đáng tin nhất: đều quy về ISO3 bằng bảng tra, các lỗi
   đã gặp đều được sửa và ghi lại.
4. **Khóa sản phẩm** dựng từ bảng concordance chính thức của WITS. Đo lại cho
   thấy bảng này **nhiều-một** (mỗi mã mới trỏ về đúng một mã H0), nên
   `product_family` thực chất **chính là mã H0**, không gộp chuỗi nhiều sản phẩm.
   Điểm yếu nằm ở chiều ngược lại: **419 mã H0 không có mã kế nhiệm trong
   HS2022**, và quan hệ thuộc các mã này "chết" hàng loạt đúng năm trước khi EU
   đổi revision (§7.2). Đây là **cái chết giả**, hiện đang nằm trong dữ liệu
   benchmark.
5. **Khóa năm** phần lớn ghép đúng năm. Các nguồn thiếu năm được kéo từ năm
   *trước* và đóng dấu `*_source_year`; không nguồn nào lấy giá trị của năm
   *sau* trên mẫu chính.

---

## 1. Bài toán: vì sao phải tự tạo khóa

| Nguồn | Định danh nước | Định danh sản phẩm | Năm |
|---|---|---|---|
| UN Comtrade (hàng VN do nước nhập khẩu khai) | mã số reporter, có mã lịch sử | HS6 theo revision của nước khai (H0–H6) | năm |
| UN Comtrade (nhập khẩu từ thế giới, làm mẫu số) | như trên | như trên | năm |
| WITS TRAINS (thuế MFN/ưu đãi) | ISO3 hoặc `EUN`; partner là mã số (`704`) | HS6 theo `nomen` của biểu | năm, có lỗ |
| EVFTA Annex 2-A, EU CN (EUR-Lex), GSP | cả EU | CN8 | lộ trình / năm |
| World Bank WDI, LPI | ISO3 | — | năm; LPI theo đợt khảo sát |
| CEPII Gravity V202211 | ISO3 (`iso3_o`, `iso3_d`) | — | năm, dừng ở 2021 |
| DESTA (FTA), TTBD (phòng vệ thương mại) | **tên nước tiếng Anh**, khối ("European Union") | TTBD: HS | năm |
| Harvard Atlas (PCI/ECI) | ISO3 | HS92 4 chữ số | năm, dừng ở 2024 |
| TRAINS NTM researcher file | ISO3 hoặc `EUN` | HS6 | khoảng hiệu lực |
| CBAM, miễn trừ thuế Mỹ 2025 | EU / Mỹ | CN8 / HS | tĩnh |

Nếu join thẳng các nguồn này, sẽ gặp đủ loại lỗi: không khớp, khớp sai, hoặc
khớp mà không báo lỗi. §3 mô tả từng khóa được tạo ra như thế nào.

---

## 2. Thứ tự dựng và nơi mỗi khóa được tạo

```
selection/            chọn 147 nước nhập khẩu, bảng ISO3 ↔ mã số, bảng EU → EUN
      │
scripts/fetch_*.py    tải nguồn; quy mã nước về ISO3 ngay khi ghi file
      │
scripts/build_spells.py
      │  tạo product_family (union-find trên concordance WITS)
      │  cộng giá trị HS6 → (importer, family, year); ngưỡng 10.000 USD; gap 1 năm
      ▼
data/interim/episodes.csv          ← KHUNG XƯƠNG: (importer, product_family, year)
      │
scripts/build_covariates.py, build_eu_tariff_panel.py, build_evfta_staging.py,
build_ntm6.py, build_glpi.py, …    → mỗi nguồn thành một bảng đã mang khóa chuẩn
      │
scripts/merge_panel.py             ← LEFT JOIN từng bảng vào khung xương
      ▼                              (chạy theo từng importer vì máy chỉ có 8 GB)
data/interim/panel_final.csv
      │
scripts/build_stage1_df.py         ← biến group-by + biến trễ t−1 (join theo năm lịch)
      ▼
data/final/stage1_panel.parquet    949.537 dòng × 205 cột, 147 nước, 2002–2025
```

Mọi join vào khung xương đều là **left join**: một dòng quan hệ-năm không bao giờ
bị xóa vì nguồn phụ thiếu dữ liệu. Chỗ thiếu để trống, hoặc được lấp theo quy tắc
có đóng dấu (§3.3).

---

## 3. Ba khóa chuẩn được tạo ra sao

### 3.1. Khóa nước: `importer` (ISO3)

| Nguồn gốc | Cách quy về ISO3 | Code |
|---|---|---|
| Comtrade: mã số reporter | Bảng tra từ `partnerAreas.json`: **bỏ** bản ghi có `entryExpiredDate`, **bỏ** nhóm (`isGroup`), lấy bản ghi hiệu lực mới nhất | `fetch_trade.py`, `select_importers_vn.py` |
| TRAINS: partner dạng mã số | `TRAINS_PARTNER_ISO = {"704": "VNM"}`, vì thiết kế chỉ có một exporter | `merge_panel.py` |
| TRAINS: biểu thuế EU khai dưới `EUN` | [`selection/eu_tariff_mapping.csv`](../selection/eu_tariff_mapping.csv): (ISO3, năm) → `EUN` từ năm gia nhập; UK dùng `EUN` tới 2020; bảng có tới 2023, 2024–2025 giữ thành viên của 2023 | `merge_panel.py::eu_mapping`, `build_ntm6.py::reporter_of` |
| DESTA, TTBD: tên nước tiếng Anh | Tên → ISO3 qua `selection/country_meta.csv` cộng bảng `ALIASES`; DESTA còn thử thêm mã số; tên không khớp được gom vào tập `unmapped` và bỏ qua; khối EU được bung ra từng thành viên | `build_covariates.py::name_to_iso3` |
| WDI, LPI, CEPII, Atlas | Đã là ISO3, join thẳng | — |

**Lỗi đã gặp và đã sửa** (ghi trong README bản 25/08/2026 §6 — file đã gỡ khỏi
cây thư mục ngày 20/09/2026, đọc bằng
`git show dbae191:legacy/docs/README_v1_2026-08-25.md`):
- Tra mã theo kiểu "ghi đè" trả về mã lịch sử (USA 841, Đức 280), khiến API trả
  0 dòng mà không báo lỗi.
- Thuế ưu đãi được lưu theo mã số `704` nhưng tra bằng `VNM`, nên không bao giờ
  khớp và mọi dòng âm thầm rơi về MFN.
- Thành viên EU có 0 năm thuế trong TRAINS; nếu không map sang `EUN` sẽ mất
  trắng thị trường EU.

### 3.2. Khóa sản phẩm: `product_family`

**Vấn đề.** Mỗi nước khai theo revision HS riêng, và đổi revision theo thời gian
(với EU, dữ liệu cho thấy H5 từ 2017 và H6 từ 2022). Một mã được đánh số lại trông giống hệt
"một quan hệ chết và một quan hệ mới sinh", đúng loại lỗi làm hỏng phân tích
duration.

**Cách tạo** (`build_spells.py::build_families`, `family_of`):
1. Dùng 6 bảng concordance chính thức của WITS, `H1_to_H0` … `H6_to_H0`, lưu ở
   `data/raw/concordance/`: tổng cộng **31.593 liên kết**.
2. Mỗi `(revision, mã HS6)` là một nút; mỗi liên kết nối mã mới với mã H0 mà nó
   tương ứng. Các nút được gom bằng union-find.
3. Khóa được đặt tên theo mã H0 đại diện, ví dụ `H0_610910`. Mã không có trong
   bảng thì đứng riêng.
4. **Cùng một hàm** `family_of` được dùng cho mọi nguồn có sản phẩm: hàng VN,
   mẫu số nhập khẩu thế giới, biểu thuế TRAINS, NTM, EVFTA. Nhờ vậy tử số và mẫu
   số nói về cùng một sản phẩm, và không có hai cách map cho cùng một mã.

**Cấu trúc thật của khóa, đo ngày 18/09/2026:**

| Chỉ số | Giá trị |
|---|---:|
| Số family | 4.954 |
| Số mã H0 trong mỗi family | **đúng 1** ở mọi family |
| Family trải trên nhiều hơn 1 nhóm HS4 | 110 |
| Family trải trên nhiều hơn 1 chương HS2 | 36 |
| Mẫu chính B0: số family xuất hiện | 3.168 |
| Mẫu chính: tỷ trọng dòng / kim ngạch thuộc family trải trên nhiều HS4 | 4,5% / 35,3% |
| Mẫu chính: tỷ trọng dòng / kim ngạch thuộc family trải trên nhiều HS2 | 2,4% / 6,5% |
| Mẫu chính: dòng có khóa không nằm trong đồ thị concordance | 0% |

**Vì sao mỗi family chỉ có đúng 1 mã H0.** Kiểm tra từng bảng WITS cho thấy
chúng **nhiều-một**: mỗi mã của revision mới trỏ về **đúng một** mã H0 (0 trường
hợp trỏ về hai mã H0 trở lên, ở cả 6 bảng). Ngược lại, một mã H0 có thể được chia
thành nhiều mã mới: 116 mã H0 bị chia trong H1, tăng dần lên 454 mã trong H6. Hệ
quả:
- **Tách mã (một H0 → nhiều mã mới)** được xử lý đúng: các mã mới được gom về
  chung mã H0.
- **Gộp mã (nhiều H0 → một mã mới)** thì bảng WITS chỉ giữ **một** mã H0 đích.
  Các mã H0 còn lại không có mã kế nhiệm. §7.2 đo hậu quả của việc này.
- Cơ chế "thành phần liên thông" mô tả trong các tài liệu cũ không gộp chuỗi
  nhiều sản phẩm thành family khổng lồ. Rủi ro đó **không tồn tại**; family chính
  là mã HS1992.

**Lệch so với B0:** B0 chốt HS6 bản HS2012 lấy từ BACI. Panel dùng mã HS1992
(H0) làm khóa, với dữ liệu thô là Comtrade do nước nhập khẩu khai
([DOI_CHIEU_B0_VOI_DU_LIEU.md](DOI_CHIEU_B0_VOI_DU_LIEU.md) §5.1). Việc chọn
nguồn và revision đang chờ thầy quyết.

**Khóa CN8 của EU** (EVFTA, CN, GSP; xem `build_evfta_staging.py`): gộp CN8 →
HS6 (H4) → family qua cùng union-find. Khi một family gộp nhiều dòng CN8 thuộc
các loại lộ trình khác nhau, lấy loại phổ biến nhất (`staging_cat`), đồng thời
giữ loại chậm nhất (`staging_cat_slowest`) và cờ `staging_mixed`. Trên mẫu chính,
6,9% số dòng có `staging_mixed = 1`.

**Khóa HS4 cho PCI:** lấy 4 chữ số đầu của mã H0. Cách này hợp lệ vì Atlas công
bố PCI theo HS92, cũng chính là H0.

### 3.3. Khóa năm: `year`

| Quy tắc | Áp cho | Đóng dấu |
|---|---|---|
| Đúng năm | Trade, WDI, FTA, TTBD, sốc chung, biểu thuế EU hợp nhất | — |
| Lấy năm gần nhất **trước đó**, tối đa 3 năm | Thuế TRAINS generic | `tariff_source_year` |
| Lấy 2021 cho các năm sau, tối đa 4 năm | Gravity CEPII | `gravity_source_year` |
| Lấy năm công bố cuối, tối đa 4 năm | PCI/ECI (Atlas dừng ở 2024) | `pci_source_year` |
| Lấy đợt khảo sát **trước đó** gần nhất; năm trước đợt đầu tiên lấy đợt đầu | LPI, Green LPI | `importer_lpi_source_year` |
| Lấy đợt khảo sát trước đó; năm trước đợt đầu lấy đợt đầu | NTM HS6 | `ntm6_source_year`, `ntm6_observed` |
| **Biến trễ t−1: join theo năm lịch `year − 1`**, không dùng `.shift(1)`, ở đúng grain của từng biến | Mọi biến `_lag1`/`_lag` | — |

Biến trễ phải join theo năm lịch, vì một cặp (nước, sản phẩm) có thể có nhiều
spell cách nhau nhiều năm. Grain được dùng khi join:

| Grain | Ví dụ biến |
|---|---|
| `(importer, product_family, year−1)` | giá trị, thị phần, đơn giá, thuế của nước nhập khẩu, volatility |
| `(importer, year−1)` | GDP, dân số, `n_products_to_c` |
| `(product_family, year−1)` | RCA, tăng trưởng sản phẩm, chính sách EU/EVFTA, `n_markets_for_p` |
| `(importer, hs2, year−1)` | `hs2_share` |

Nhờ đó, dòng đầu của một spell mới chỉ trống ở các biến cấp quan hệ, còn GDP của
nước đích vẫn có giá trị. Chi tiết: [TU_DIEN_DU_LIEU_FINAL_DF.md](TU_DIEN_DU_LIEU_FINAL_DF.md) §6.

---

## 4. Bảng ghép từng nguồn

Độ phủ đo trên mẫu chính B0: EU-27 không gồm UK, origin 2012–2024, 148.260 dòng
còn sống.

| Nguồn | Bảng trung gian | Khóa ghép vào khung xương | Khi thiếu | Độ phủ mẫu chính |
|---|---|---|---|---|
| Comtrade (VN) | `episodes.csv` | chính là khung xương | — | 100% |
| Comtrade (thế giới) | trong `build_spells.py` | `(importer, family, year)` | trống | xem [TU_DIEN](TU_DIEN_DU_LIEU_FINAL_DF.md) §5 |
| TRAINS MFN/ưu đãi | `data/raw/tariffs/` | `(reporter, year, family)`, reporter = `EUN` nếu thuộc EU | lấy năm trước, tối đa 3 năm | 92,8% có giá trị: 89,8% đúng năm, 3,0% năm trước, 7,2% trống |
| Thuế EU hợp nhất + EVFTA | `eu_tariff_panel.csv` | `(family, year)`, broadcast cho mọi thành viên EU | trống | `tariff_applied_pct`, `evfta_cut_cum_pp`: 100% |
| WDI | `macro_panel_v2.csv` | `(importer, year)` | trống | GDP: 100% |
| LPI | cột trong WDI | `(importer, đợt khảo sát trước)` | đợt đầu | 100%; chỉ 35,8% đúng năm, 64,2% từ đợt trước |
| CEPII Gravity | `gravity_vn.csv` | `(importer, year)` | lấy 2021, tối đa 4 năm | 100%; 70,7% đúng năm, 29,3% (2022–2024) lấy 2021 |
| DESTA | `fta_vn.csv` | `(importer, year)` | trống | `fta_in_force`: 100% |
| TTBD | `ttbd_vn.csv` | `(importer, year)` | trống | 100% dòng, nhưng không quan sát sau 2015 ([COVARIATES_ADDED.md](COVARIATES_ADDED.md)) |
| Atlas PCI/ECI | `complexity_*.csv` | PCI: `(HS4 của H0, year)`; ECI: `(importer, year)` | năm công bố cuối, tối đa 4 năm | PCI: 100% đúng năm |
| NTM HS6 | `_ntm6/` | reporter (`EUN` với EU) → `(family, đợt khảo sát trước)` | đếm = 0 | 92,8% dòng có khảo sát đúng năm (`ntm6_observed`) |
| CBAM, miễn trừ thuế Mỹ | `cbam_products*.csv`, … | `family` (CBAM chỉ ghi cho EU) | trống | ngoài mẫu B0 |
| Sốc chung | `shocks_annual.csv` | `year` | — | 100% |

Không nguồn nào trên mẫu chính dùng giá trị của **năm sau** năm quan sát: tỷ lệ
`*_source_year > year` bằng 0 ở cả 5 cột đóng dấu.

---

## 5. Từ panel sang benchmark

Benchmark không ghép thêm gì. `benchmark/features/build_matrix.py` đọc panel,
chọn cột theo feature registry, tính target và vài biến dẫn xuất, rồi mới lọc
EU-27 sau khi đã tính feature trên đủ 147 nước. Kết quả là một ma trận đóng băng;
mỗi cell benchmark chỉ lọc dòng theo fold và chọn cột theo tập feature. Chi tiết
ở `SRT_Benchmark_EU27_B0_Structured_Review.md` §3 (đã gỡ khỏi cây thư mục —
`git show dbae191:legacy/docs/SRT_Benchmark_EU27_B0_Structured_Review.md`).

Hệ quả: **mọi lỗi của khóa ở tầng panel đều đi thẳng vào benchmark**, gồm cả
cái chết giả ở §7.2.

---

## 6. Những gì đã được kiểm chứng

| Kiểm chứng | Kết quả | Nguồn |
|---|---|---|
| Mã sản phẩm báo cáo có vào được một family | 14.042/14.042 mã (lần đo cũ); mẫu chính hiện tại 0% dòng nằm ngoài đồ thị | [TIEN_TRINH_THU_THAP.md](TIEN_TRINH_THU_THAP.md); đo 18/09 |
| Biểu EVFTA tự parse so với TRAINS (hai năm duy nhất TRAINS có) | Trùng khít 83,8% (2020) và 87,6% (2021); lệch tuyệt đối trung bình 0,34 và 0,17 điểm %; phần lệch tập trung ở family gộp nhiều CN8 và dòng hạn ngạch thuế quan | [DU_LIEU_EVFTA_VA_THUE_EU.md](DU_LIEU_EVFTA_VA_THUE_EU.md) §3.4 |
| Episode EU27 khớp được biểu EVFTA | 99,4% số dòng, 99,56% kim ngạch, ổn định qua các năm | như trên, §3.6 |
| PCI khớp theo HS4 | 1.216/1.216 nhóm | [BRIEF_SINKING_COVERAGE.md](BRIEF_SINKING_COVERAGE.md) §2.1 |
| FTA / TTBD / sốc chung / gravity khớp theo `(importer, year)` | 100% / 100% / 100% / 84,2% trước khi kéo gravity sang 2022–2023 | [COVARIATES_ADDED.md](COVARIATES_ADDED.md) |
| Merge theo từng importer cho kết quả giống merge toàn bộ | Giống từng byte; RAM đỉnh giảm từ 5,2 GB xuống 371 MB | [COVARIATES_ADDED.md](COVARIATES_ADDED.md) §12 |
| Target của benchmark khớp cờ `event` của panel | assert trong `build_matrix.py` | code |
| Khóa `(importer, year)` của gravity không trùng | chỉ in cảnh báo nếu có dòng trùng, không dừng build | `build_covariates.py` |

---

## 7. Độ tin cậy khoa học: điểm mạnh, điểm yếu, và phát hiện mới

### 7.1. Điểm mạnh

- **Khóa sản phẩm dựa trên bảng concordance chính thức**, không tự đoán. Việc
  dùng một hàm map duy nhất cho mọi nguồn loại bỏ được lỗi tử số và mẫu số lệch
  sản phẩm.
- **Khóa nước quy về ISO3 bằng bảng tra tường minh**; các lỗi khớp không báo lỗi
  đều đã được phát hiện, sửa và ghi lại.
- **Không lấp dữ liệu một cách âm thầm:** mọi giá trị kéo từ năm khác đều có cột
  `*_source_year`, nên có thể lọc ra để chạy robustness.
- **Hướng thời gian đúng:** mọi phép lấp đều nhìn về quá khứ, và biến trễ join
  theo năm lịch ở đúng grain.
- **Thuế EU/EVFTA có kiểm chứng độc lập** với TRAINS; đây là biến chính sách
  trung tâm.

### 7.2. Phát hiện mới: cái chết giả khi EU đổi revision HS

**Cơ chế.** Bảng WITS là nhiều-một (§3.2). Khi một revision mới gộp nhiều mã H0
thành một mã, chỉ một mã H0 nhận được mã kế nhiệm. Mọi quan hệ thuộc các mã H0
còn lại sẽ biến mất khỏi dữ liệu ngay khi nước nhập khẩu chuyển sang revision
mới, và panel ghi nhận đó là **một cái chết** dù hàng hóa vẫn được buôn bán.

**Quy mô:** trong 4.954 mã H0 có trong bảng WITS, **419 mã không có mã kế nhiệm
trong H6** và 371 mã không có trong H4.

**Bằng chứng trên mẫu EU-27.** Quy ước `event = 1` ở năm Y nghĩa là chết ở năm
Y+1. Theo dữ liệu, EU đổi sang H5 năm 2017 và H6 năm 2022.

| Năm | Số dòng | Tỷ lệ chết: toàn mẫu | Tỷ lệ chết: nhóm mã H0 không có mã kế nhiệm H6 (số dòng) | Tỷ lệ chết: nhóm còn lại |
|---:|---:|---:|---:|---:|
| 2014 | 9.342 | 0,136 | 0,151 (232) | 0,136 |
| 2015 | 9.561 | 0,124 | 0,136 (220) | 0,124 |
| **2016** | 10.058 | 0,134 | **0,581** (236) | 0,123 |
| 2017 | 10.695 | 0,120 | 0,031 (128) | 0,121 |
| 2020 | 11.900 | 0,100 | 0,103 (126) | 0,100 |
| **2021** | 13.161 | 0,122 | **1,000** (145) | 0,112 |
| 2022 | 13.927 | 0,120 | — (0) | 0,120 |

- Năm 2021: **cả 145/145** quan hệ thuộc nhóm này "chết", so với 11% ở nhóm còn
  lại. Từ 2022 nhóm này biến mất hoàn toàn khỏi dữ liệu.
- Năm 2016: 58% so với 12%. Nhóm được đo là nhóm không có mã kế nhiệm H6, không
  trùng hoàn toàn với nhóm bị ảnh hưởng khi đổi sang H5, nên con số 2016 chỉ là
  xấp xỉ.
- Ước tính thô, số cái chết dư ra khoảng **130 năm 2021 và 110 năm 2016**, tức
  khoảng **8%** số sự kiện của mỗi năm đó. Các mã này chiếm 1,9% kim ngạch
  2012–2021.

**Hậu quả cho các phân tích dùng panel:**
- Tỷ lệ chết năm 2016 và 2021 bị thổi phồng. Năm 2021 trùng giai đoạn EVFTA/COVID,
  nên B6 có thể đọc nhầm cái chết giả thành tác động chính sách.
- Trong benchmark: sự kiện năm 2021 nằm trong test của fold 2 (origin 2020–2021)
  và train của fold phụ EVFTA; sự kiện năm 2016 nằm trong train của fold 2 và 3.
- Đây là quan hệ có hệ thống với sản phẩm (các mã bị gộp), không phải nhiễu ngẫu
  nhiên, nên có thể làm lệch ước lượng theo sản phẩm.

**Hướng sửa, cần chốt:**
- (a) Gộp các mã H0 cùng trỏ về một mã mới thành một family chung. Muốn làm vậy
  phải dùng thêm bảng nối theo chiều H0 → mã mới, hoặc bảng nối giữa các revision
  liền kề.
- (b) Coi quan hệ kết thúc đúng năm đổi revision ở các mã H0 không có mã kế nhiệm
  là **right-censored**, không phải sự kiện.
- (c) Tối thiểu: loại các mã này và chạy robustness.

### 7.3. Điểm yếu khác phát hiện khi đối chiếu code

| # | Vấn đề | Chỗ trong code | Ảnh hưởng | Mức |
|---|---|---|---|---|
| 1 | **Trung bình MFN trong một family bị tính sai.** Khi nhiều dòng HS6 cùng rơi vào một family, code tính `(giá trị cũ + giá trị mới) / 2` theo thứ tự đọc. Đó là trung bình trượt, dòng đọc sau có trọng số lớn hơn, không phải trung bình cộng như comment ghi. | `merge_panel.py::load_tariffs` | `tariff_rate` generic ở các family có mã bị tách; `tariff_rate`/`tariff_rate_lag` là feature F4 trong benchmark. Chưa đo độ lớn. Thuế EU hợp nhất (`tariff_applied_pct`) **không** bị ảnh hưởng. | Trung bình |
| 2 | **NTM HS6 ghi 0 khi không có khảo sát** cho một (family, đợt), nên "không đo" trông giống "không có biện pháp". | `build_ntm6.py::attach` | 7,2% dòng mẫu chính không có khảo sát đúng năm; phải dùng kèm `ntm6_observed` | Thấp |
| 3 | **Năm trước đợt khảo sát đầu tiên lấy đợt đầu** (LPI, NTM HS6), tức dùng giá trị đo ở tương lai | `merge_panel.py::lpi_source_year`, `build_ntm6.py::attach` | Trên mẫu chính 2012–2024 tỷ lệ này là 0% (đã đo); chỉ ảnh hưởng các năm trước 2007 trong panel 147 nước | Thấp với B0 |
| 4 | **Tên nước DESTA/TTBD không khớp bị bỏ qua**, nên một hiệp định bị bỏ sót sẽ trông như "không có FTA", không hiện thành ô trống | `build_covariates.py` | Chưa có tài liệu nào báo cáo tập `unmapped`. Với EU-27, EVFTA đã được kiểm tra khớp (`fta_in_force = 1` từ 2020) | Thấp với B0, chưa đo với 147 nước |
| 5 | **Carry-forward lớn ở LPI và gravity:** 64,2% dòng LPI lấy từ đợt trước; 29,3% dòng gravity lấy năm 2021 | `merge_panel.py` | Gravity trên EU-27 phần lớn là biến tĩnh nên ít rủi ro; LPI biến thiên chậm | Thấp |
| 6 | **Map EU → `EUN` của NTM không theo năm:** lấy dòng cuối trong bảng cho mỗi nước | `build_ntm6.py::reporter_of` | Chỉ sai với nước đổi chế độ (UK), không thuộc mẫu B0 | Không ảnh hưởng B0 |

### 7.4. Những gì chưa được đánh giá

- **Chưa đối chiếu với phương pháp nối mã HS đã công bố** trong literature về
  thương mại. Cần tìm và dẫn nguồn trước khi viết phần phương pháp. Tài liệu này
  cố ý không nêu tên nguồn nào chưa kiểm chứng.
- **Chưa có robustness theo cách định nghĩa sản phẩm**, ví dụ so với BACI HS2012
  như B0 yêu cầu, hoặc với cách sửa (a)/(b) ở §7.2.
- **Chưa đo sai số của mirror data** (Comtrade phía nhập khẩu, giá CIF) so với
  BACI (đã hòa giải hai chiều khai báo, giá FOB).

---

## 8. Việc nên làm, theo thứ tự

1. **Sửa cái chết giả do đổi revision** (§7.2): chốt hướng (a), (b) hoặc (c),
   dựng lại spell, chạy lại benchmark. Đây là lỗi duy nhất đã được đo là làm sai
   biến kết cục.
2. **Sửa trung bình MFN** (§7.3 #1) thành trung bình cộng thật, rồi đo độ lệch
   trước và sau.
3. Báo cáo tập tên nước không khớp của DESTA/TTBD (§7.3 #4).
4. Chạy kiểm chứng chéo với BACI cho vài năm, như khuyến nghị ở
   [DOI_CHIEU_B0_VOI_DU_LIEU.md](DOI_CHIEU_B0_VOI_DU_LIEU.md) §5.1.
5. Cập nhật các tài liệu cũ có số đã lỗi thời: "5 bảng concordance, 25.981 liên
   kết" (nay là 6 bảng, 31.593 liên kết); "spell bắt đầu năm 2002 bị loại" (nay
   giữ lại với cờ `left_trunc`); mô tả family như thành phần liên thông gộp nhiều
   mã H0 (thực tế mỗi family là một mã H0).

---

## 9. Nguồn

**Tài liệu cũ được gộp vào đây:**

| Tài liệu | Phần liên quan |
|---|---|
| [TRINH_BAY_NHOM_FEATURE_STAGE1_PANEL.md](TRINH_BAY_NHOM_FEATURE_STAGE1_PANEL.md) | §3–4: sơ đồ nguồn → khung xương, grain và broadcast; §5.3: ghép thuế EU |
| [TU_DIEN_DU_LIEU_FINAL_DF.md](TU_DIEN_DU_LIEU_FINAL_DF.md) | §3: cột khóa; §6: lag theo đúng grain |
| [FEATURE_TINH_TU_DU_LIEU_RAW.md](FEATURE_TINH_TU_DU_LIEU_RAW.md) | §1.1: `product_family`; §3: thuế generic và thuế EU/EVFTA |
| [COVARIATES_ADDED.md](COVARIATES_ADDED.md) | "How these join", §11–12: tỷ lệ khớp, carry-forward, merge theo importer |
| [DU_LIEU_EVFTA_VA_THUE_EU.md](DU_LIEU_EVFTA_VA_THUE_EU.md) | §3.4–3.6: kiểm chứng EVFTA với TRAINS và tỷ lệ khớp |
| [../README.md](../README.md) | Bố cục repo, cách dựng lại panel, những gì đổi ở v2 |
| [DOI_CHIEU_B0_VOI_DU_LIEU.md](DOI_CHIEU_B0_VOI_DU_LIEU.md) | §5.1: Comtrade so với BACI |

**Code:** `scripts/build_spells.py` (family, spell), `scripts/merge_panel.py`
(join), `scripts/build_stage1_df.py` (lag, group-by), `scripts/build_covariates.py`
(DESTA, TTBD, gravity), `scripts/build_ntm6.py`, `scripts/build_evfta_staging.py`,
`scripts/build_eu_tariff_panel.py`, `selection/eu_tariff_mapping.csv`.

**Cách tái lập các số đo mới (§3.2, §4, §7.2):**
- Kích thước family: gọi `build_spells.build_families()`, gom nút theo gốc
  union-find, đếm số mã H0 và số nhóm HS4/HS2 trong mỗi gốc.
- Tính nhiều-một của bảng concordance: với mỗi file `Hx_to_H0`, đếm số mã mới trỏ
  về nhiều hơn một mã H0, và số mã H0 được nhiều hơn một mã mới trỏ về.
- Độ phủ và cái chết giả: đọc các cột khóa, `*_source_year`, `event`,
  `import_value_usd` từ `stage1_panel.parquet`; lọc bằng
  `benchmark/features/eu27_scope.filter_eu27`, `gap_filled = 0`, năm 2012–2024;
  đánh dấu mã H0 không nằm trong tập đích của `H6_to_H0`; tính tỷ lệ `event`
  theo năm và theo nhóm.
