# Bộ dữ liệu survival analysis cho xuất khẩu Việt Nam (WITS + Comtrade)

Dự án thu thập và dựng bộ dữ liệu **spell-level** để chạy mô hình survival
(Kaplan-Meier / Cox) trên tuổi thọ của **quan hệ xuất khẩu của Việt Nam** ở mức
tariff-line.

*Trạng thái trong tài liệu này được đo trực tiếp trên đĩa lúc **25/08/2026**.
Mọi con số đều là số thật, đếm bằng cách đọc file, không phải ước lượng từ tài
liệu cũ.*

> **Cộng sự mới đọc gì trước:** [docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md) —
> đối chiếu từng mục của `Sinking Relationships.md` với dữ liệu thật, cách đọc
> từng cột mới, và cách dựng lại toàn bộ từ số không.
> **Bản đồ nguồn ↔ brief:** §2.3 ngay dưới đây.
> **Tiến độ ý tưởng ↔ dữ liệu:** [docs/MAPPING_IDEA_DATA.md](docs/MAPPING_IDEA_DATA.md).
> **Đối chiếu với B0 bản chốt của thầy:** [docs/DOI_CHIEU_B0_VOI_DU_LIEU.md](docs/DOI_CHIEU_B0_VOI_DU_LIEU.md)
> — `Stage1_Research_Framework.md` yêu cầu gì, trên đĩa có gì, còn phải lấy thêm gì.
> **EVFTA staging schedule & thuế EU (29/08/2026):** [docs/DU_LIEU_EVFTA_VA_THUE_EU.md](docs/DU_LIEU_EVFTA_VA_THUE_EU.md)
> — hai lỗ hổng cuối của Stage 1 đã đóng; nguồn, cách parse, và ba phép kiểm chứng.

---

## ĐỌC TRƯỚC TIÊN — 3 điều quan trọng nhất

1. **Thiết kế đã đổi: exporter chỉ còn Việt Nam.** Importer không còn bị chốt ở
   53 nước chọn tay — **mọi nước có đủ dữ liệu đều được đưa vào, tổng 147
   nước**, phần bị loại ghi rõ lý do từng nước. Chi tiết:
   [docs/THIET_KE_VIET_NAM.md](docs/THIET_KE_VIET_NAM.md).
2. **Panel đã dựng xong và dùng được — cửa sổ 2003–2025.**
   `analysis/panel_final.csv`: **747.719 episode × 158 cột**, 147 nước nhập
   khẩu, 4.621 nhóm sản phẩm, **228.175 spell** (57.689 right-censored).
3. **Thu thập dữ liệu đã xong — không còn gì phải tải.** Đợt 25/08 đóng nốt bốn
   mục brief yêu cầu mà dự án chưa có: **NTM ở HS6 × năm** (file researcher của
   TRAINS, hoá ra không cần tài khoản), **thuế đối ứng Mỹ 2025 theo tháng và
   theo sản phẩm** (trước đó chưa từng nằm trong panel), **CBAM của EU** (brief
   nêu đích danh, dự án chưa từng thu thập), và **EPI theo năm**. Ba thứ còn
   thiếu là thiếu vĩnh viễn ở nguồn — mục 3.2.
   **Điểm nghẽn còn lại không phải dữ liệu:** (a) **chưa chạy mô hình nào ngoài
   baseline**, (b) sáu quyết định nghiên cứu chưa chốt, đứng đầu là **định nghĩa
   "network survivability"** — ràng buộc nằm trong chính tên đề tài.

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

### 2.1. Kiểm kê — đếm trên đĩa 25/08/2026

Kiểm kê chi tiết theo từng nguồn:
**[docs/DATA_INVENTORY_VN.md](docs/DATA_INVENTORY_VN.md)**. Đối chiếu từng mục
của brief kèm cách đọc từng cột: **[docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md)**.

| Nguồn | Đã có | Trạng thái |
|---|---|---|
| **Trade VN→importer** (Comtrade, HS6) | **3.306** file importer-năm · **147/147** nước · 2002–2025 | ✅ 0 lỗ hổng |
| **Trade importer→thế giới** (mẫu số RCA) | **3.350** file | ✅ xong, phủ tới 2025 |
| **Trade mirror** (VN tự khai) | **40** file | ✅ VN chưa nộp 2025 |
| **Tariff MFN** (WITS TRAINS) | **2.482** reporter-năm | ⚠️ tới **2023**; 2024–2025 TRAINS trả 404 |
| **Tariff PREF cho VN** | **72** reporter-năm · **13** nước | ⚠️ tới 2021, và khai theo mã nhóm — mục 3.3 |
| **NTM researcher** (TRAINS bulk) 🆕 | **18.686.715** dòng giữ lại · **126** nước áp dụng · HS6 × mã NTM × năm | ✅ 25/08 |
| **NTM ad-valorem equivalent** (UNCTAD-GTAP 11) 🆕 | **162.174** quan sát · VN xuất sang **89** thị trường | ✅ 25/08, lát cắt 2017 |
| **NTM công khai** (3 file WITS) | 75 nước, cấp ngành | ✅ giữ làm dự phòng |
| **Thuế đối ứng Mỹ 2025** 🆕 | 167 dòng heading · **1.087** mã HTS8 miễn trừ · 8 văn bản EO gốc | ✅ 25/08 |
| **CBAM (EU)** 🆕 | 42 dòng CN + 14 ngoại lệ → **269** nhóm H0 | ✅ 25/08 |
| **EPI theo năm** 🆕 | **184.827** giá trị · 220 nền kinh tế · 52 chỉ báo · 1996–2025 | ✅ 25/08 |
| **Vĩ mô** (`macro_panel_v2.csv`) | 3.404 nước-năm · 147 nước + VN | ✅ |
| **FTA / TTB / Gravity / Shocks / Complexity / LPI** | 6 panel phụ | ✅ đã merge |
| **Concordance HS** | 6/6 bảng (H1→H6 về H0) | ✅ |

**Sản phẩm đã dựng ra** (`merge_panel.py`, 25/08):

| File | Kích thước | Nội dung |
|---|---|---|
| `analysis/spells.csv` | 16 MB | **228.175 spell** — 170.486 chết, **57.689 right-censored** (25,3%) |
| `analysis/episodes.csv` | 107 MB | 747.719 episode-năm, các cột lõi |
| `analysis/panel_final.csv` | 655 MB | **747.719 × 158 cột** — file để chạy mô hình |
| `analysis/_ntm6/` | 58 MB | 126 mảnh NTM HS6, chỉ `merge_panel.py` đọc |

⚠️ **Comtrade có quota theo ngày, trả `403` khi hết** — khác hẳn `429` (throttle
vài giây). Script **dừng ngay khi gặp 403** và in thời điểm quota nạp lại, thay
vì đốt hết các job còn lại rồi đánh dấu "failed". Pha `world` vì thế phải chạy
nhiều ngày.

### 2.2. 11 biến yêu cầu ban đầu — nguồn và mức chi tiết

| # | Biến | Nguồn thật sự dùng | Mức chi tiết |
|---|---|---|---|
| 1–2 | Trade value XK/NK | **UN Comtrade API** (cần key) | HS6 × importer × năm |
| 3 | Tariff | WITS `TRN`, MFN + PREF cho partner 704, lấy mức thấp hơn | HS6 |
| 4 | RCA (Balassa) | tự tính, mẫu số = **nhập khẩu thế giới** | HS6 family |
| 5 | Product share | tự tính | HS6 family |
| 6 | Partner share | tự tính | importer × năm |
| 7 | Country growth | tự tính — tăng trưởng XK của VN **theo từng sản phẩm** | HS6 family |
| 8 | World growth | tự tính — tăng trưởng nhập khẩu thế giới theo sản phẩm | HS6 family |
| 9 | HHI thị trường + sản phẩm | tự tính (Herfindahl) | năm |
| 10 | **NTM** | **file researcher TRAINS** (25/08) — thay cho 3 file cấp ngành | **HS6 × mã NTM × năm thu thập** |
| 11 | GDP growth | WITS `tradestats-development` (WDI) | nước × năm |
| **+** | `vn_market_share_pct` | tự tính từ hai luồng trade | importer × HS6 family × năm |

> **Vì sao biến 4–9 phải tự tính:** WITS API chỉ cho các chỉ số này ở **31 nhóm
> ngành**, không có HS6 (`Invalid_Product` khi truyền mã HS6) — chi tiết ở
> [docs/KIEM_CHUNG_DU_LIEU_WITS.md](docs/KIEM_CHUNG_DU_LIEU_WITS.md) §3.1.
>
> **Ba biến phải định nghĩa lại vì chỉ còn một exporter:** country growth và
> world growth trước đây tính trên tổng xuất khẩu cả nước → với một exporter sẽ
> thành **một con số mỗi năm**, trùng hoàn toàn với hiệu ứng năm. Nay cả hai
> tính **theo từng sản phẩm**. RCA cũng đổi mẫu số sang **nhập khẩu thế giới
> thật**.

---

### 2.3. Mỗi nguồn dữ liệu phục vụ mục nào của `Sinking Relationships.md`

Đây là bảng để cộng sự đọc trước khi mở panel: cột nào trả lời câu hỏi nào của
brief, và cái bẫy đi kèm.

#### §1 — Dữ liệu xuất khẩu và dựng spell (nền tảng)

| Cột trong panel | Nguồn | Brief dùng để làm gì | Bẫy |
|---|---|---|---|
| `import_value_usd` | Comtrade, importer khai | Biến kết cục nền: quan hệ còn sống hay không | Dùng số **importer khai**, không phải VN khai; mirror chỉ để đối chiếu |
| `net_weight_kg`, `unit_value_usd_per_kg` | Comtrade | Phân biệt "chết vì mất khách" với "chết vì rớt giá" | 96,2% — thiếu ở vài dòng không khai khối lượng |
| `spell_start_year`, `spell_end_year`, `right_censored` | tự dựng | Chính là đối tượng của mô hình survival | **Ngưỡng chết = 10.000 USD**; đã đo 5 ngưỡng, xem §2c của `TIEN_DO_SO_VOI_SINKING.md` |
| `t_start`, `t_stop`, `event` | tự dựng | Dạng counting-process, chạy thẳng Cox / cloglog | **`event`=1 ở năm Y nghĩa là chết ở năm Y+1** |

> **Cơ chế bảo vệ quan trọng nhất:** nước ngừng nộp báo cáo (Nga, Belarus từ
> 2022; 58 nước chưa nộp 2025) được **kiểm duyệt hành chính**, không tính là
> chết. Nếu không, mô hình sẽ đọc thành "FTA giết chết quan hệ".

#### §2 — Thuế quan (covariate chính)

| Cột | Nguồn | Brief dùng để làm gì | Bẫy |
|---|---|---|---|
| `tariff_rate`, `tariff_type`, `tariff_source_year` | WITS TRAINS | Biến giải thích trung tâm | 83,8% đo đúng năm. **2024–2025 mang sang từ 2023** — đọc `tariff_source_year` trước khi diễn giải |
| `us_recip_rate_yearend` / `_peak` / `_days_wt` | Biểu thuế Mỹ ch.99 + 8 văn bản EO | Cú sốc 2025 mà brief đặt ở trung tâm | Ba quy ước năm khác nhau: **20% / 46% / 11,55%**. Chọn một, và nói rõ đã chọn cái nào |
| `us_recip_exempt_share`, `us_recip_exempt_full` | U.S. note 2(v)(iii) | Đưa cú sốc từ cấp nước xuống cấp sản phẩm | **39,0% giá trị xuất sang Mỹ nằm trên nhóm có dòng được miễn**. Dùng `share` chứ đừng nhị phân hoá |
| `us_transship_rate` | heading 9903.02.01 | Rủi ro bị quy là trung chuyển (40%) | Không quan sát được ai bị áp — là mức phạt tiềm năng |
| `fta_in_force`, `years_since_fta` | DESTA | Nhóm đối chứng có FTA bảo vệ | Đã kiểm chứng 19/19 mốc thời gian |

> ⚠️ **Lệch pha một năm.** Thuế Mỹ có hiệu lực tháng 4 và tháng 8/2025, nhưng
> cái chết do nó gây ra được ghi ở episode **năm 2024**. Phải dùng biến thuế
> dạng *lead*, hoặc định nghĩa lại năm sự kiện là `end + 1`.

#### §3 — Covariate gravity/survival chuẩn

| Cột | Nguồn | Brief dùng để làm gì | Bẫy |
|---|---|---|---|
| `dist`, `contig`, `comlang_off`, … | CEPII Gravity V202211 | Kiểm soát trọng lực chuẩn | Nguồn dừng 2021; `gravity_source_year` đánh dấu 4 năm mang sang. **Đừng đọc các cột biến thiên theo thời gian (`entry_*`, `wto_d`) cho 2022–2025** |
| `importer_gdp_usd`, `importer_gdp_per_capita_usd` | World Bank WDI | Quy mô và mức phát triển thị trường | 100% |
| `pci`, `product_hs4` | Atlas of Economic Complexity v18 | Độ phức tạp sản phẩm | Atlas công bố ở HS92 **4 số**; family khoá theo H0 nên nối bằng 4 ký tự đầu, **không mất dòng nào** |
| `importer_eci`, `exporter_eci`, `importer_coi` | Atlas | Năng lực của nền kinh tế đối tác | |

#### §4 — Robustness: logistics xanh, NTM, và cú sốc carbon

| Cột | Nguồn | Brief dùng để làm gì | Bẫy |
|---|---|---|---|
| `importer_glpi_*` (4 biến thể) | LPI + EPI, 3 công thức đã công bố | Câu hỏi phụ của brief | **Bốn biến thể bất đồng nhau**: bản tỷ số và bản PCA xếp hạng gần như ngược (Spearman −0,463). Chọn công thức **sẽ đổi kết luận** |
| `ntm6_*_survey`, `ntm6_*_inforce` | TRAINS researcher | NTM ở HS6 × năm | 95,2% có giá trị nhưng **chỉ 36,6% đo đúng năm**. Kiểm `ntm6_observed` và `ntm6_source_year` |
| `ntm6_bilateral_survey` | TRAINS researcher | Biện pháp **nhắm đích danh Việt Nam** | Hiếm hơn nhiều so với biện pháp erga omnes; đó chính là điều làm nó sắc |
| `ntm_ave_border_pct` 🆕 | UNCTAD-GTAP 11 (Kee & Nicita 2022) | **NTM tính bằng điểm thuế**, cùng thang với `tariff_rate` | Lát cắt 2017, **bất biến theo thời gian** — fixed effect theo importer sẽ hút hết. Có sẵn cả bản trọng số thương mại và bản trung bình đều |
| `cbam_in_scope`, `cbam_sector`, `cbam_reporting_share` | Regulation (EU) 2023/956 Annex I | Cú sốc carbon để so với cú sốc thuế | **Trong cửa sổ panel, CBAM chỉ là nghĩa vụ báo cáo** — chế độ chính thức từ 1/1/2026. `cbam_definitive` bằng 0 ở mọi dòng |
| `ad_in_force`, `ttb_any_in_force`, `ttbd_observed` | World Bank TTBD | Biện pháp phòng vệ thương mại | **Lọc `ttbd_observed`=1 trước khi đọc** — từ 2016 là ngoại suy |
| `analysis/epi_indicators_annual.csv` | Yale EPI archive | Nguyên liệu để GLPI biến thiên theo thời gian | Chưa gộp thành chỉ số; bảng trọng số ở `data_raw/epi/` |

#### §5 — Sản phẩm giao ra

Brief đòi "một bảng panel sạch × 6 cột" cộng `spell_start`/`spell_end`/
`censored`. Cả chín đều có, ở độ phủ 96,9–100%. Bảng đối chiếu tên brief ↔ tên
cột thật nằm ở [docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md) §1.

#### Bảng ưu tiên nước của brief — đã phủ hết

| Nhóm brief nêu | Trong panel | Ghi chú |
|---|---|---|
| Mỹ | ✅ 24.355 episode | Nguồn shock chính; NTM chỉ có 4 năm thu thập |
| EU (27 nước) | ✅ 16 nước trong panel, 184.081 episode | Nguồn CBAM; NTM khai chung dưới mã `EUN` |
| ASEAN + TQ, Ấn, Bangladesh | ✅ | Cả thuế Mỹ 2025 của họ cũng có, để kiểm soát trade diversion |
| Nhật, Hàn, Úc (CPTPP/FTA) | ✅ | Nhóm đối chứng có FTA ổn định |
| Thị trường nhỏ/mới nổi | ✅ | 147 importer tổng cộng, đủ variation trong outcome |

#### Ba quy ước phải nhớ khi đọc panel

1. **Ô trống ≠ số 0.** `us_recip_*` chỉ điền cho `importer == USA`; `cbam_*` chỉ
   cho nước EU (tư cách thành viên đọc theo năm, nên Anh dừng sau 2020). Trống
   nghĩa là "biện pháp không áp cho thị trường đó".
2. **Mọi cột `*_source_year` đều là lời cảnh báo.** `tariff_source_year`,
   `gravity_source_year`, `importer_lpi_source_year`, `ntm6_source_year`,
   `pci_source_year`, `ntm_ave_source_year` — khác `year` nghĩa là giá trị được
   mang từ năm khác sang.
3. **Đừng trộn hai họ biến NTM.** `ntm_*` (cấp ngành, một lát cắt, 79,9%) và
   `ntm6_*` (HS6 × năm, 95,2%) đo hai thứ khác nhau ở hai độ phân giải khác
   nhau. Chọn một họ cho mỗi specification.

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

### 3.1. Thiếu do tải chưa xong — **không còn mục nào**

Kiểm 25/08 bằng cách đếm trên chính panel: `rca`, `world_growth_pct`,
`vn_market_share_pct`, `country_growth_pct`, `hhi_market`, `dist`, `pci` và các
chuỗi GDP đều **100% ở mọi năm 2003–2025**. Ba pass trade thô phủ 2002–2025.
Không còn lượt tải nào đang dở, và không còn nguồn nào máy lấy được mà chưa lấy.

Nguồn tuỳ chọn duy nhất còn nằm ngoài đĩa là **CEPII BACI** (~2,3 GB, 1995–2023).
Brief có khuyến nghị nó, nhưng **BACI dừng ở 2023 nên lấy nó làm nguồn chính là
xoá mất năm 2025** — năm duy nhất quan sát được cú sốc thuế Mỹ. Chỉ nên dùng làm
kiểm tra độ vững cho định nghĩa spell, sau khi đã có kết quả.

### 3.2. Thiếu do bản chất nguồn — ba mục, và đều là Limitations

Mục "NTM là điểm nghẽn lớn nhất" của các bản README trước **đã được gỡ 25/08**:
file researcher của TRAINS tải được bằng **một request GET công khai**, không
cần tài khoản. Chi tiết ở [docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md) §2.1.
Ba file WITS cấp ngành vẫn giữ làm dự phòng cho những nước file researcher không
phủ.

Ba thứ còn thiếu là thiếu vĩnh viễn — viết vào Limitations, đừng đưa vào việc
phải làm:

| Thiếu gì | Vì sao không sửa được |
|---|---|
| **Mức thuế ưu đãi thật** | Chỉ 13 nước khai riêng cho VN, và không nước nào khai cho 2022–2023. Phần còn lại nằm dưới mã nhóm (ASEAN, AANZFTA, GSP) mà WITS không công bố thành viên |
| **Thuế 2024–2025** | TRAINS không phát hành biểu thuế cho hai năm này (đã probe lại 25/08). Hai năm đó mang giá trị 2023, có `tariff_source_year` đánh dấu |
| **NTM trước 2010** | File researcher bắt đầu từ 2010. `ntm6_observed` đánh dấu; 2003–2009 bằng 0 là do lịch thu thập |

### 3.3. Thuế ưu đãi khai theo nhóm — hạn chế nghiêm trọng nhất của biến thuế

Hệ quả đo được: hai năm cuối có **101.280 episode MFN so với 239 PREF**, tức
**mức thuế bị khai cao hơn thực tế** với khoảng 39% episode đang có FTA hiệu
lực. Cột `fta_in_force` đánh dấu đúng những dòng đó nên sai lệch *nhìn thấy
được*, nhưng không nguồn công khai nào sửa được. **Phải nêu trong Limitations.**

### 3.4. Việc chỉ bạn làm được — **không còn**

Cả hai mục của các bản README trước đều đã đóng, và cả hai đều đóng bằng cách
phát hiện tài liệu cũ nói sai:

| # | Việc cũ | Kết cục |
|---|---|---|
| 1 | ~~Đăng ký `trainsonline.unctad.org` để tải researcher file~~ | ❌ **KHÔNG CẦN.** Endpoint `get-researcher-file/2` mở công khai, không login, không rate-limit. Đã tải 25/08 |
| 2 | ~~Đăng ký API key WTO I-TIP cho thuế Mỹ 2025~~ | ❌ **KHÔNG CẦN.** Nằm ngay trong chương 99 biểu thuế Mỹ, USITC mở REST API |

**Cái thật sự đang chặn không phải dữ liệu.** Sáu quyết định nghiên cứu, mỗi cái
đã có sẵn nguyên liệu trong gói bàn giao — định nghĩa *network survivability*,
12 định nghĩa ở §2.3 của tài liệu L0–L5, công thức Green LPI, có dựng EPI hàng
năm không, quy ước năm cho thuế Mỹ 2025, và xử lý spell một năm. Liệt kê đầy đủ
kèm lý do ở [docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md) §5.

---

## 4. Bản đồ thư mục

```
wits/
├── README.md                     ← bạn đang đọc; trạng thái tổng thể
├── .env                          ← API key Comtrade (ĐÃ gitignore, KHÔNG gửi ai)
│
├── docs/
│   ├── idea/                     tài liệu ý tưởng gốc, không sinh ra từ code
│   │   ├── SINKING RELATIONSHIPS (1).md  ★ bản brief mới nhất nhóm đang dùng
│   │   ├── Sinking Relationships.md      brief gốc — mọi tài liệu khác đối chiếu về đây
│   │   ├── TÓM TẮT DỰ ÁN NGHIÊN CỨU.md   5 tab ứng viên + bản thẩm định
│   │   └── detail idea.md                thang nghiên cứu L0–L5
│   ├── TONG_HOP_Y_TUONG.md       ★★ hợp nhất hai tài liệu ý tưởng ở trên
│   ├── MAPPING_IDEA_DATA.md      ★★ ánh xạ ý tưởng ↔ dữ liệu, tiến độ đến đâu
│   ├── THIET_KE_VIET_NAM.md      ★ đổi thiết kế sang exporter = VN, đọc trước
│   ├── DATA_INVENTORY_VN.md      ★ kiểm kê chính xác dữ liệu VN đang có trên đĩa
│   ├── COVARIATES_ADDED.md       4 nguồn covariate bổ sung + mở rộng 2022–2024
│   ├── essences.txt              yêu cầu gốc về NTM
│   ├── guide.md                  khảo sát ban đầu về WITS (có chỗ sai)
│   ├── KIEM_CHUNG_DU_LIEU_WITS.md  kiểm chứng thật 22 phép thử API
│   ├── DATA_HANDOFF.md           ★★★ đối chiếu brief ↔ dữ liệu, cách đọc từng cột,
│   │                                  và cách dựng lại từ số không — đọc đầu tiên
│   ├── TIEN_DO_SO_VOI_SINKING.md ★ tiến độ so với brief, tiếng Việt
│   ├── BRIEF_SINKING_COVERAGE.md đối chiếu brief, bản chi tiết tiếng Anh
│   ├── TIEN_TRINH_THU_THAP.md    nhật ký thi công
│   ├── DOI_CHIEU_ESSENCES_NTM.md  đối chiếu essences.txt ↔ workspace
│   ├── TONG_HOP_BO_DU_LIEU_VA_CAU_CHUYEN_NGHIEN_CUU.md  gói dữ liệu ↔ câu chuyện
│   ├── KE_HOACH_THUYET_TRINH_DATA.md  kịch bản buổi trình bày dữ liệu
│   ├── wits_data_20260825_NOI_DUNG.md  bản kê 217 file trong gói bàn giao
│   ├── wits_data_20260825.tar.gz.sha256  hash gói đã gửi 25/08 (gói dựng lại ở §8)
│   ├── PROMPT_TRAINS_BROWSER_AGENT.md · PROMPT_TRAINS_EXPORT_AGENT.md
│   └── trains_url.txt            lệnh curl gốc của TRAINS Online, để dò lại API
│
├── deck/                         slide thuyết trình — code TRACKED, output GITIGNORED
│   ├── src/                      engine + nội dung: deck*.py, content*.py,
│   │                             build_deck.py, build2.py, make_figs.py, figs2.py,
│   │                             render.py, overlap.py + data_*.json
│   ├── assets/                   Slides_template.pptx (template gốc),
│   │                             example_slide.pdf, Vietnam_Export_Portfolio_Resilience.pdf
│   ├── fig/ · fig2/              hình dựng ra từ analysis/ — GITIGNORED
│   ├── preview/                  ảnh render để soát bố cục — GITIGNORED
│   └── out/                      4 file .pptx dựng ra — GITIGNORED
│
├── scripts/
│   ├── wits_probe.py             kiểm chứng API WITS → probe_out/
│   ├── select_countries.py       tải dữ liệu availability thô → selection/
│   ├── select_importers_vn.py    ★ chốt exporter = VN + xếp hạng 147 importer
│   ├── fetch_trade.py            ★ 3 pha: vn / world / mirror → data_raw/trade*/
│   ├── fetch_tariffs.py          thuế HS6, MFN + PREF cho partner 704
│   ├── fetch_macro.py            GDP + tải 3 file NTM thô
│   ├── fetch_ntm_availability.py bản đồ độ phủ NTM của TRAINS Online
│   ├── build_ntm.py              biến NTM cấp ngành (dự phòng)
│   ├── fetch_ntm_researcher.py   ★ file researcher TRAINS 10,5 GB, lọc trong luồng
│   ├── build_ntm6.py             ★ NTM ở HS6 → analysis/_ntm6/ theo nước áp dụng
│   ├── build_ntm_ave.py          NTM quy ra điểm thuế (UNCTAD-GTAP 11)
│   ├── fetch_us_tariffs_2025.py  biểu thuế Mỹ ch.99 + PDF ghi chú pháp lý
│   ├── extract_us_exemptions.py  ★ 1.087 mã HTS8 miễn trừ → cấp sản phẩm
│   ├── build_us_tariff_panel.py  ★ thuế Mỹ 2025 vào panel + đường đi theo tháng
│   ├── fetch_cbam_scope.py       ★ phạm vi CBAM từ Regulation (EU) 2023/956
│   ├── fetch_epi_annual.py       EPI theo năm 1996–2025
│   ├── fetch_covariates.py       tải FTA/DESTA, TTBD, CEPII gravity, sốc chung
│   ├── build_covariates.py       dựng 4 panel covariate → analysis/
│   ├── build_glpi.py             Green LPI, 4 biến thể đã công bố
│   ├── pull_2022_2024.sh         mở rộng cửa sổ, 3 pha, resume được
│   ├── spell_threshold_sensitivity.py  độ nhạy của ngưỡng cắt spell
│   ├── survival_baseline.py      Kaplan–Meier + cloglog, phép kiểm tra panel
│   ├── build_spells.py           dựng spell + RCA/HHI ở HS6
│   └── merge_panel.py            ghép tất cả → analysis/panel_final.csv
│
├── selection/    danh sách nước, availability, ánh xạ thuế EU — TRACKED trong git
├── data_raw/     dữ liệu thô — GITIGNORED
│   ├── trade/          nhập khẩu từ VN, HS6, một file/importer-năm
│   ├── trade_world/    nhập khẩu từ toàn thế giới (mẫu số RCA)
│   ├── trade_mirror/   VN tự khai xuất khẩu (đối chiếu)
│   ├── tariffs/mfn/ · tariffs/pref/ · _partnerlists.csv
│   ├── ntm/            3 file WITS + researcher/ (TRAINS HS6) + ave_gtap/ (AVE)
│   ├── us_tariffs_2025/  biểu thuế ch.99, PDF ghi chú, 8 văn bản EO gốc
│   ├── cbam/           Regulation (EU) 2023/956 (bản CELLAR)
│   ├── epi/            EPI 2026 + kho chỉ báo theo năm + bảng trọng số
│   └── concordance/    6 bảng chuyển đổi HS (H1–H6 → H0)
├── analysis/     kết quả dựng ra — GITIGNORED, gửi qua Drive
│   ├── spells.csv       228.175 spell (57.689 right-censored)
│   ├── episodes.csv     747.719 episode-năm, các cột lõi
│   ├── panel_final.csv  747.719 × 158 cột ← file để chạy mô hình
│   ├── _ntm6/           126 mảnh NTM HS6, chỉ merge_panel.py đọc
│   ├── us_tariff_vn · us_exempt_products · us_tariff_2025_monthly
│   ├── cbam_products · ntm_ave_vn · epi_indicators_annual · glpi
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

# 4) Thuế: MFN rồi PREF (chỉ partner 704). YEARS đã là range(2002, 2024).
#    Có 2 cache khiến chạy lại rất rẻ: _no_schedule.csv (901 nước-năm TRAINS
#    trả 404) và _partnerlists.csv (ghi dần theo từng nước).
setsid nohup python3 -u fetch_tariffs.py --pass all > ../logs/tariff_vn.log 2>&1 &

# 5) Vĩ mô cho 147 nước + VN
python3 fetch_macro.py

# 5b) Covariate bổ sung: FTA, trade remedy, gravity, sốc chung
python3 fetch_covariates.py
python3 build_covariates.py

# 5c) Mở rộng cửa sổ sang 2022-2024 (đã chạy xong 21/08; resume được)
./pull_2022_2024.sh

# 5d) Bốn nguồn bổ sung, chạy 25/08. Ba cái đầu vài phút; cái cuối ~1 giờ.
python3 extract_us_exemptions.py    # phạm vi sản phẩm của thuế Mỹ 2025 (PDF chương 99)
python3 build_us_tariff_panel.py    # thuế Mỹ 2025 vào panel + đường đi theo tháng
python3 fetch_cbam_scope.py         # phạm vi CBAM của EU — brief có yêu cầu, trước đó chưa có gì
python3 fetch_epi_annual.py         # EPI theo năm 1996-2025, để GLPI có thể biến thiên
#     File AVE của NTM đi kèm gói bàn giao sẵn (data_raw/ntm/ave_gtap/); nếu
#     dựng lại từ số không thì lấy ở get-researcher-file/4, 2,8 MB.
setsid nohup python3 -u fetch_ntm_researcher.py > ../logs/ntm_researcher.log 2>&1 &
                                    # NTM ở HS6: một request GET 10,5 GB, lọc ngay trong luồng

# 6) Sau khi tải xong — dựng lại toàn bộ (BẮT BUỘC)
python3 build_ntm.py
python3 build_ntm6.py       # chia mảnh NTM HS6 theo nước áp dụng
python3 build_ntm_ave.py    # NTM quy ra điểm thuế (UNCTAD-GTAP 11)
python3 build_spells.py     # ~1,7 phút · 1,8 GB RAM
python3 merge_panel.py      # ~2 phút · < 500 MB RAM
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
Cột cuối là giá trị **thật sự đo được ở bản dựng 25/08**:

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

| Kiểm tra | Đích | Bản 25/08 |
|---|---|---|
| kích thước panel | — | ✅ **747.719 × 158** |
| exporter duy nhất | `['VNM']` | ✅ VNM |
| right-censored | > 0 | ✅ **57.689** / 228.175 spell |
| số importer | 147 | ✅ 147 |
| episode có thuế | > 90% | ✅ 96,9% (83,8% đo đúng năm) |
| episode có PREF | > 0% | ✅ > 0% |
| `rca` có phương sai | không toàn 1,0 | ✅ có |
| `vn_market_share_pct` trống | ≈ 0% | ✅ 0% |
| NTM ở HS6 | > 90% | ✅ **95,2%** (36,6% nộp đúng năm) |
| NTM quy ra điểm thuế | > 90% | ✅ **94,4%** |
| thuế Mỹ 2025 | mọi dòng USA | ✅ 24.355 |
| CBAM | > 0 | ✅ 7.823 episode EU |

**Nếu `merge_panel.py` in ra 128 cột thay vì 158**, nghĩa là một trong năm bước
build ghi file phụ (`extract_us_exemptions`, `build_us_tariff_panel`,
`fetch_cbam_scope`, `build_ntm6`, `build_ntm_ave`) chưa chạy. Merge **không
crash** khi thiếu input — nó chỉ in một dòng ghi chú rồi đi tiếp. **Luôn kiểm số
cột.**

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
2. **NTM có ba dạng, và mỗi dạng có hạn chế riêng.** `ntm6_*` ở HS6 × năm,
   nhưng `Year` là **năm thu thập** chứ không phải năm lịch: chỉ 36,6% episode
   nằm trong năm nước đó thực sự nộp, và file gốc bắt đầu từ 2010 nên 2003–2009
   bằng 0 là do lịch thu thập. `ntm_ave_border_pct` quy ra điểm thuế nhưng là
   **một lát cắt 2017**, không sống được qua fixed effect theo importer. `ntm_*`
   cấp ngành là dự phòng, một lát cắt, 16 nhóm. Xem mục 3.2 và
   [docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md) §4.
3. **"Thiếu dữ liệu" hay "không có biện pháp"?** — đúng vấn đề Carrère (2011)
   nêu. Xử lý ở **đúng một chỗ**, ghi rõ trong docstring `build_ntm.py`: chương
   vắng mặt trong một nước-ngành *đã được khảo sát* tính là **0**; nước **không**
   được khảo sát để **trống**, không suy diễn.
4. **Thuế ưu đãi khai theo nhóm không lấy được** — xem mục 3.3.
5. **Panel dựa trên khai báo phía nhập khẩu.** Số liệu VN tự khai được giữ riêng
   trong `data_raw/trade_mirror/` để đối chiếu; hai phía lệch nhau vì CIF/FOB,
   trung chuyển và tái xuất.
6. **Thuế của 2024–2025 là giá trị mang sang từ 2023**, không phải số thật —
   TRAINS không phát hành biểu thuế cho hai năm đó (đã probe lại 25/08). Biến
   thuế duy nhất *thật sự* biến thiên trong 2025 là **thuế đối ứng Mỹ**, và nó
   chỉ nhận dạng được cho một thị trường. Cột `tariff_source_year` đánh dấu từng
   dòng. Mục 3.2.
7. **Biến trade remedy chỉ có khởi xướng vụ kiện tới 2015.** TTBD của World Bank
   dừng cập nhật tháng 6/2016. Sau đó `ttb_any_in_force` vẫn khác 0 vì một biện
   pháp không có ngày thu hồi được coi là còn hiệu lực — tức 8 năm cuối là
   **ngoại suy**, không được diễn giải hệ số cho giai đoạn đó.
8. **CBAM trong cửa sổ panel không phải là giá.** Điều 32 của Regulation (EU)
   2023/956 đặt giai đoạn chuyển tiếp 1/10/2023–31/12/2025 với **nghĩa vụ báo
   cáo, không có chứng chỉ và không phải trả tiền**; chế độ chính thức bắt đầu
   1/1/2026, tức sau năm cuối của panel. Mọi bảng đặt CBAM cạnh thuế Mỹ 2025
   phải nói rõ điều này, nếu không là đang so một sắc thuế với một nghĩa vụ khai
   báo. Cột `cbam_definitive` bằng 0 ở mọi dòng chính là để chỗ đó nhìn thấy
   được.
9. **Thuế Mỹ 2025 có ba quy ước năm và chúng lệch nhau rất xa** — 20% cuối năm,
   46% đỉnh, **11,55% trọng số ngày**. Panel mang cả ba. Chọn quy ước nào là
   quyết định phải công bố, không phải chi tiết kỹ thuật.
10. **Nga và Belarus là mất mát vĩnh viễn, không phải độ trễ.** Nga ngừng công bố
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
| **`docs/`** | Vì sao mọi thứ được quyết định như vậy. Bắt đầu từ [docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md) |
| **`README.md`** | Bản đồ tổng thể |

**KHÔNG gửi:** `.env` (chứa API key Comtrade — tuyệt đối không), `data_raw/`
(chỉ gửi nếu cộng sự cần tự dựng lại panel, khi đó gửi kèm `scripts/`),
`logs/`, `probe_out/`, `__pycache__/`.

```bash
cd /home/minhquang/wits
B=wits_data_$(date +%Y%m%d)
mkdir -p "$B/data_raw/ntm"
cp -a analysis selection docs scripts "$B/"
rm -rf "$B/scripts/__pycache__"
cp -a data_raw/ntm/ave_gtap "$B/data_raw/ntm/"
cp -a README.md "docs/idea/Sinking Relationships.md" "$B/"
cp -a docs/wits_data_*_NOI_DUNG.md "$B/NOI_DUNG.md"
tar czf "$B.tar.gz" "$B/"
sha256sum "$B.tar.gz" > "$B.tar.gz.sha256"
```

Gói **giải nén ra đúng một thư mục** `wits_data_YYYYMMDD/`, không rải file ra
thư mục hiện hành. Gửi kèm hai file nhỏ bên cạnh gói:
[docs/wits_data_20260825_NOI_DUNG.md](docs/wits_data_20260825_NOI_DUNG.md) — bản kê toàn bộ
217 file, đọc được mà không cần giải nén — và `.tar.gz.sha256` để kiểm file có
hỏng khi truyền không (`sha256sum -c`).

**~160 MB nén** (đã dựng thật 25/08, gom lại thành thư mục 27/08; đã kiểm không chứa `.env` và không còn `__pycache__`). Đây là đường "gửi bản đã dựng" — cộng sự chạy mô hình
được ngay nhưng không dựng lại được, vì `data_raw/` (735 MB) không đi kèm. Nếu
họ cần dựng lại từ đầu thì xem
[docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md) §7.3: **chỉ ba script cần API key
Comtrade**, phần còn lại công khai hoàn toàn.

> ✅ **Không còn gì phải tải.** Kiểm 25/08 bằng cách đếm trên chính panel:
> `rca`, `world_growth_pct`, `vn_market_share_pct`, `dist`, `pci` và các chuỗi
> GDP đều **100% ở mọi năm 2003–2025**; ba pass trade thô phủ 2002–2025. Hai chỗ
> chưa đầy là do nguồn, không phải do tải: thuế 2024–2025 và NTM trước 2010.

> ✅ **Cảnh báo cũ đã gỡ.** `analysis/` nay là bản dựng đúng của thiết kế
> exporter = Việt Nam, chạy 21/08 trên dữ liệu đầy đủ. **Gửi được.**
>
> ⚠️ Kèm đúng ba lưu ý cho cộng sự (đầy đủ trong
> [docs/DATA_HANDOFF.md](docs/DATA_HANDOFF.md)):
>
> 1. **Thuế của 2024–2025 là giá trị mang sang từ 2023** — TRAINS trả 404 cho
>    hai năm này. Cột `tariff_source_year` ghi rõ từng dòng.
> 2. **`ntm6_*` chỉ có nghĩa trong những năm nước đó thực sự nộp báo cáo NTM.**
>    Kiểm `ntm6_observed` trước khi đọc, và nhớ file gốc bắt đầu từ 2010 nên
>    2003–2009 bằng 0 là do lịch thu thập, không phải do chính sách.
> 3. **`us_recip_*` và `cbam_*` chỉ điền cho đúng thị trường của nó** — Mỹ và
>    EU. Ô trống nghĩa là "biện pháp này không áp cho thị trường đó", khác hẳn
>    với số 0.

---

## 9. Việc tiếp theo, theo thứ tự ưu tiên

Xếp hạng đầy đủ kèm lý do, đối chiếu với từng level nghiên cứu:
**[docs/MAPPING_IDEA_DATA.md](docs/MAPPING_IDEA_DATA.md) §7**.

**Toàn bộ hàng "máy làm" đã xong.** Không còn việc thu thập hay dựng dữ liệu nào
đang treo — xem mục 3.1 và 3.4.

| # | Việc | Ai làm | Chặn cái gì |
|---|---|---|---|
| — | ~~Tải trade, thuế, vĩ mô, covariate; dựng spell + panel~~ | máy | ✅ xong 19–23/08 |
| — | ~~Mở cửa sổ panel sang 2024–2025~~ | máy | ✅ xong 23/08 |
| — | ~~Chạy Kaplan–Meier + baseline hazard~~ | máy | ✅ xong 24/08 — `survival_baseline.py`, §2d của `TIEN_DO_SO_VOI_SINKING.md` |
| — | ~~NTM ở HS6 × năm~~ | máy | ✅ **xong 25/08** — không cần tài khoản, xem `DATA_HANDOFF.md` §2.1 |
| — | ~~Thuế Mỹ 2025 theo tháng và theo sản phẩm~~ | máy | ✅ **xong 25/08** |
| — | ~~CBAM, EPI theo năm, NTM quy ra điểm thuế~~ | máy | ✅ **xong 25/08** |
| — | ~~Kiểm duyệt biến trade-remedy ở 2015~~ | máy | ✅ đã có sẵn — `ttbd_observed` |
| **1** | **Chốt định nghĩa "network survivability"** | **nhóm** | L2, L4, L5 — ràng buộc nằm trong chính tên đề tài, chưa có nó thì không viết được bài toán tối ưu |
| **2** | **Chốt 12 định nghĩa ở §2.3 của tài liệu L0–L5** | **nhóm** | L0 trở đi |
| 3 | Chọn công thức Green LPI (4 biến thể đã dựng, xếp hạng gần như ngược nhau) | **nhóm** | Ý nghĩa của câu hỏi phụ |
| 4 | Chọn quy ước năm cho thuế Mỹ 2025 (20% / 46% / 11,55%) | **nhóm** | Độ lớn của cú sốc trung tâm |
| 5 | Quyết cách xử lý 52,7% spell chỉ sống 1 năm | **nhóm** | Ý nghĩa của hazard ước lượng được |
| 6 | Chạy lại baseline **có fixed effects** (importer × năm, product) + clustering theo quan hệ | máy | Hệ số thuế đang ra **dấu ngược** — §2d |
| 7 | Có dựng EPI hàng năm từ kho chỉ báo không, và trọng số nào | **nhóm** | GLPI biến thiên theo thời gian |
| 8 | (tuỳ chọn) Tải CEPII BACI làm kiểm tra độ vững cho định nghĩa spell | máy | Không chặn gì — làm sau khi có kết quả |
