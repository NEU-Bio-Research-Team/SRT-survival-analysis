# Gói bàn giao `wits_data_20260825.tar.gz` — có gì bên trong

Tài liệu này để **đọc mà không cần giải nén**. Nó liệt kê đúng 228 file nằm
trong gói, file nào để chạy mô hình, file nào chỉ là dấu vết kiểm toán, và ba
điều phải biết trước khi đọc số.

| | |
|---|---|
| **File** | `wits_data_20260825.tar.gz` |
| **Dựng ngày** | 25/08/2026 |
| **Kích thước** | 159 MB nén → **851 MB** sau khi giải nén |
| **Số file** | 217 |
| **Giải nén ra** | đúng **một thư mục** `wits_data_20260825/` — không rải file ra thư mục hiện hành |
| **SHA-256** | xem `docs/wits_data_20260825.tar.gz.sha256` |
| **File để chạy mô hình** | `analysis/panel_final.csv` — 747.719 dòng × 158 cột |
| **Đọc đầu tiên sau khi giải nén** | `docs/DATA_HANDOFF.md`, rồi `README.md` |

```bash
# Kiem tra file khong hong sau khi truyen
sha256sum -c docs/wits_data_20260825.tar.gz.sha256

# Xem mục lục mà không giải nén
tar -tzf wits_data_20260825.tar.gz

# Giải nén — ra đúng một thư mục wits_data_20260825/
tar -xzf wits_data_20260825.tar.gz

# Chỉ lấy đúng file panel (655 MB)
tar -xzf wits_data_20260825.tar.gz wits_data_20260825/analysis/panel_final.csv
```

Sau khi giải nén, cấu trúc là:

```
wits_data_20260825/
├── NOI_DUNG.md              ← chính tài liệu này
├── README.md                ← bản đồ tổng thể
├── Sinking Relationships.md ← brief nghiên cứu gốc
├── analysis/                ← DỮ LIỆU ĐÍCH (843 MB, 157 file)
├── selection/               ← định nghĩa mẫu (15 file)
├── docs/                    ← 15 tài liệu, đọc DATA_HANDOFF.md trước
├── scripts/                 ← 25 file mã nguồn
└── data_raw/ntm/ave_gtap/   ← mảnh thô duy nhất đi kèm
```

Đường dẫn `data_raw/ntm/ave_gtap/` giữ nguyên có chủ ý: `scripts/build_ntm_ave.py`
đọc đúng đường dẫn tương đối đó, nên chạy lại script ngay trong thư mục này là được.

Gói được dựng bằng lệnh (README §8):

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

---

## 1. Tám mục bên trong thư mục

| Mục | Số file | Dung lượng | Là gì |
|---|---:|---:|---|
| `analysis/` | 157 | 843 MB | **Dữ liệu đích.** Panel đã dựng xong, chạy mô hình được ngay |
| `data_raw/ntm/ave_gtap/` | 2 | 6,6 MB | Mảnh dữ liệu thô duy nhất đi kèm — AVE của NTM |
| `scripts/` | 25 | 592 KB | Toàn bộ mã tải và dựng, mỗi file có docstring ghi nguồn và giới hạn |
| `docs/` | 15 | 268 KB | Vì sao mọi quyết định được ra như vậy |
| `selection/` | 15 | 400 KB | Danh sách nước, ánh xạ EU, độ phủ NTM — cần để hiểu mẫu |
| `README.md` | 1 | 47 KB | Bản đồ tổng thể, tiếng Việt |
| `Sinking Relationships.md` | 1 | 8,9 KB | Brief nghiên cứu gốc |
| `NOI_DUNG.md` | 1 | — | Chính tài liệu này, để sẵn bên trong gói |

Thiết kế: **exporter = Việt Nam**, quan hệ = (importer × HS6), cửa sổ **2002–2025**.
Đơn vị quan sát của panel là spell-năm.

---

## 2. `analysis/` — dữ liệu đích

### 2.1. Ba file lõi

| File | Dung lượng | Khóa | Nội dung |
|---|---:|---|---|
| **`panel_final.csv`** | 655 MB | `spell_id`, `year` | **File để chạy mô hình.** 747.719 dòng × 158 cột. Mọi thứ bên dưới đã được ghép vào đây |
| `spells.csv` | 16,5 MB | `spell_id` | 228.175 spell quan hệ thương mại (57.689 right-censored) |
| `episodes.csv` | 107 MB | `spell_id`, `year` | 747.719 episode-năm, chỉ các cột lõi. Là trung gian — `build_spells.py` dựng lại được |

> Nếu kênh gửi quá nặng, bỏ được `episodes.csv` (107 MB) và `_ntm6/` (56 MB).
> `panel_final.csv` và `spells.csv` là hai file thật sự cần.

### 2.2. Biện pháp phi thuế (NTM)

| File | Dung lượng | Khóa | Nội dung |
|---|---:|---|---|
| `_ntm6/{REPORTER}.csv.gz` | 126 file, 56 MB | — | NTM ở mức HS6 chia mảnh theo nước áp dụng. Chỉ `merge_panel.py` đọc |
| `ntm6_observed.csv` | 2,7 KB | `reporter` | **Đọc file này trước.** Mỗi nước thật sự nộp báo cáo NTM vào những năm nào |
| `ntm_ave_vn.csv` | 84 KB | `importer`, `year` | NTM quy ra điểm thuế (AVE), từ UNCTAD-GTAP 11 |
| `ntm_by_type.csv` | 230 KB | | NTM cấp ngành theo loại — nguồn WITS công khai, dùng dự phòng |
| `ntm_sector.csv` | 97 KB | | NTM cấp ngành, 16 nhóm, không có chiều thời gian |
| `ntm_country.csv` | 7,4 KB | | NTM tổng hợp theo nước |

### 2.3. Thuế Mỹ 2025

| File | Dung lượng | Khóa | Nội dung |
|---|---:|---|---|
| `us_tariff_vn.csv` | 723 B | `importer`, `year` | Thuế đối ứng 2025, bốn quy ước tính |
| `us_tariff_2025_monthly.csv` | 848 B | `iso3`, `year`, `month` | Đường đi của mức thuế trong năm, kèm căn cứ pháp lý |
| `us_exempt_products.csv` | 13 KB | `product_family` | Tỷ lệ miễn trừ theo họ sản phẩm |
| `us_tariff_exemptions_2025_hs8.csv` | 29 KB | `hts8` | 1.087 mã HTS8 miễn trừ — dấu vết kiểm toán |
| `us_tariff_exemptions_2025.csv` | 18 KB | | Bảng miễn trừ đã gom nhóm |
| `us_tariffs_2025.csv` | 90 KB | | Biểu thuế chương 99 đã đọc ra bảng |

### 2.4. CBAM (cơ chế biên giới carbon của EU)

| File | Dung lượng | Khóa | Nội dung |
|---|---:|---|---|
| `cbam_products.csv` | 7,1 KB | `product_family` | Phạm vi Annex I và ngành tương ứng |
| `cbam_products_cn.csv` | 6,0 KB | `cn_code` | Từng dòng mã CN kể cả ngoại lệ — dấu vết kiểm toán |

### 2.5. Covariate

| File | Dung lượng | Nội dung |
|---|---:|---|
| `macro_panel_v2.csv` | 573 KB | GDP và các chuỗi vĩ mô, 147 nước + VN (bản đang dùng) |
| `macro_panel.csv` | 218 KB | Bản vĩ mô cũ, giữ để đối chiếu |
| `gravity_vn.csv` | 196 KB | Khoảng cách, biên giới, ngôn ngữ — CEPII Gravity |
| `fta_vn.csv` | 105 KB | Hiệp định thương mại có hiệu lực — DESTA |
| `ttbd_vn.csv` · `ttbd_vn_cases.csv` · `ttbd_vn_products.csv` | 90 + 51 + 98 KB | Phòng vệ thương mại — World Bank TTBD |
| `epi_indicators_annual.csv` | 5,1 MB | Chỉ báo EPI theo năm, 1996–2025 |
| `glpi.csv` | 74 KB | Green LPI, 4 biến thể đã công bố |
| `complexity_product.csv` · `complexity_country.csv` | 787 + 88 KB | PCI / ECI |
| `shocks_annual.csv` | 3,8 KB | Sốc chung theo năm |

### 2.6. Kết quả kiểm tra (không phải đầu vào)

| File | Dung lượng | Nội dung |
|---|---:|---|
| `km_survival.csv` | 2,5 KB | Đường sống sót Kaplan–Meier |
| `hazard_baseline.csv` | 865 B | Hazard nền cloglog |
| `threshold_sensitivity.csv` | 467 B | Độ nhạy của ngưỡng cắt spell |

---

## 3. `data_raw/ntm/ave_gtap/` — mảnh thô duy nhất

Toàn bộ phần còn lại của `data_raw/` (735 MB: trade, thuế, gravity, EPI…)
**không** nằm trong gói. Chỉ hai file này đi kèm, vì `build_ntm_ave.py` cần
chúng và tải lại thì mất công:

| File | Dung lượng | Nội dung |
|---|---:|---|
| `UNCTADGTAP11_AVEborder.csv` | 5,6 MB | AVE của NTM, lát cắt ngang 2017, khóa `exporter`, `importer`, `gtapcode` |
| `AVE_GTAP_README_rev1.pdf` | 1,0 MB | Tài liệu phương pháp đi kèm |

---

## 4. `docs/` — 15 tài liệu

| File | Đọc khi nào |
|---|---|
| **`DATA_HANDOFF.md`** | ★★★ **Đọc đầu tiên.** Đối chiếu brief ↔ dữ liệu, cách đọc từng cột, cách dựng lại từ số không |
| `TONG_HOP_Y_TUONG.md` | ★★ Hợp nhất hai tài liệu ý tưởng gốc |
| `MAPPING_IDEA_DATA.md` | ★★ Ánh xạ ý tưởng ↔ dữ liệu, tiến độ đến đâu |
| `THIET_KE_VIET_NAM.md` | ★ Vì sao thiết kế chuyển sang exporter = Việt Nam |
| `DATA_INVENTORY_VN.md` | ★ Kiểm kê chính xác dữ liệu trên đĩa |
| `TIEN_DO_SO_VOI_SINKING.md` | ★ Tiến độ so với brief, tiếng Việt |
| `BRIEF_SINKING_COVERAGE.md` | Bản đối chiếu brief chi tiết, tiếng Anh |
| `COVARIATES_ADDED.md` | 4 nguồn covariate bổ sung + mở rộng cửa sổ 2022–2024 |
| `KIEM_CHUNG_DU_LIEU_WITS.md` | 22 phép thử API thật trên WITS |
| `TIEN_TRINH_THU_THAP.md` | Nhật ký thi công |
| `DOI_CHIEU_ESSENCES_NTM.md` | Đối chiếu yêu cầu NTM gốc ↔ những gì đã làm |
| `essences.txt` | Yêu cầu gốc về NTM |
| `guide.md` | Khảo sát WITS ban đầu — **có chỗ sai**, giữ làm lịch sử |
| `PROMPT_TRAINS_BROWSER_AGENT.md` · `PROMPT_TRAINS_EXPORT_AGENT.md` | Prompt cho hướng lấy NTM đã bị bỏ |

---

## 5. `scripts/` — 25 file mã nguồn

Chạy theo thứ tự trong README §5. Chỉ **ba** script cần API key Comtrade
(`fetch_trade.py`, `select_importers_vn.py`, `select_countries.py`); phần còn
lại hoàn toàn công khai, không cần đăng ký gì.

| Nhóm | File |
|---|---|
| **Chọn mẫu** | `select_countries.py`, `select_importers_vn.py` |
| **Tải thô** | `fetch_trade.py`, `fetch_tariffs.py`, `fetch_macro.py`, `fetch_covariates.py`, `fetch_ntm_availability.py`, `fetch_ntm_researcher.py`, `fetch_ntm_trains.py`, `fetch_us_tariffs_2025.py`, `fetch_cbam_scope.py`, `fetch_epi_annual.py`, `pull_2022_2024.sh` |
| **Dựng** | `build_spells.py`, `build_covariates.py`, `build_ntm.py`, `build_ntm6.py`, `build_ntm_ave.py`, `build_us_tariff_panel.py`, `build_glpi.py`, `extract_us_exemptions.py`, `merge_panel.py` |
| **Kiểm tra** | `survival_baseline.py`, `spell_threshold_sensitivity.py`, `wits_probe.py` |

---

## 6. `selection/` — 15 bảng định nghĩa mẫu

| File | Nội dung |
|---|---|
| `importers_vn.csv` | **147 importer được chọn**, kèm số liệu từng nước |
| `importer_vn_all.csv` | Cả danh sách, gồm 46 nước bị loại **kèm lý do** |
| `vn_partner_screen.csv` | 3.569 nước-năm sàng lọc; 190 nước có giao thương với VN ít nhất một năm |
| `exporter_selected.csv` | Exporter đã chốt — Việt Nam |
| `eu_tariff_mapping.csv` | Ánh xạ nước EU → reporter thuế (đã kéo dài qua 2021) |
| `ntm_availability.csv` · `trains_avail.csv` · `trains_countries.csv` · `trains_export_targets.csv` | Độ phủ NTM của TRAINS |
| `ntm_types.csv` | Từ điển mã NTM |
| `country_meta.csv` | Vùng, nhóm thu nhập |
| `comtrade_da.csv` | Độ sẵn có dữ liệu Comtrade thô |
| `importer_candidates.csv` · `importers_selected.csv` · `exporters_selected.csv` | Bản chọn mẫu của thiết kế cũ, giữ để truy vết |

---

## 7. Ba điều phải biết trước khi đọc số

1. **Thuế 2024–2025 là giá trị mang sang từ 2023.** TRAINS không công bố biểu
   thuế cho hai năm này. Cột `tariff_source_year` ghi rõ từng dòng. Biến thuế
   duy nhất thật sự biến thiên trong 2025 là thuế Mỹ.

2. **`ntm6_*` chỉ có nghĩa trong những năm nước đó thật sự nộp báo cáo.** Kiểm
   `ntm6_observed.csv` trước. File nguồn bắt đầu từ 2010, nên 2003–2009 bằng 0
   là do lịch thu thập chứ không phải do chính sách. Khi `ntm6_source_year` lớn
   hơn `year` (29,0% panel) thì con số là mượn, phải coi là **chưa đo được**,
   không phải "NTM thấp".

3. **Ô trống ≠ số 0.** `us_recip_*` chỉ điền trên dòng `importer == "USA"`,
   `cbam_*` chỉ điền trên importer EU (đọc tư cách thành viên theo từng năm, nên
   Anh dừng sau 2020). Trống nghĩa là "biện pháp này không áp cho thị trường
   đó"; số 0 nghĩa là "có áp và không được miễn".

Thêm hai điểm khi viết Limitations:

- **Thuế ưu đãi bị khai theo nhóm.** Chỉ 13 reporter nộp biểu thuế nêu đích danh
  Việt Nam. Phần còn lại nằm dưới mã nhóm (ASEAN, AANZFTA, GSP) mà WITS không
  công bố thành viên. `fta_vn.csv` phục hồi được *có hay không* có ưu đãi, nhưng
  **mức thuế thực tế bị khai cao hơn thật** ở khoảng 39% episode.
- **Quy ước ngày sự kiện.** `event = 1` ở năm Y nghĩa là Y là năm cuối quan hệ
  còn sống — nó chết ở Y+1. Thuế Mỹ 2025 vì thế phải đọc như một lead so với
  `event` gắn năm 2024, nếu không sẽ lệch một năm.

---

## 8. Những gì **không** có trong gói

| Không có | Vì sao |
|---|---|
| `.env` | Chứa hai API key Comtrade. **Không bao giờ gửi.** Đăng ký key riêng miễn phí tại `comtradeplus.un.org`, mất vài phút. Đã kiểm: gói này không chứa `.env` hay bất kỳ thông tin xác thực nào |
| `data_raw/` (trừ `ntm/ave_gtap/`) | 735 MB tải thô: `trade/`, `trade_world/`, `trade_mirror/`, `tariffs/`, `gravity/`, `epi/`, `cbam/`, `rta/`, `shocks/`, `wdi/`, `ttbd/`, `us_tariffs_2025/`, `concordance/`, phần còn lại của `ntm/`. Chỉ cần nếu muốn **dựng lại từ số không** — xem `docs/DATA_HANDOFF.md` §7.3 |
| `logs/`, `probe_out/` | Dấu vết chạy máy, chỉ có nghĩa trên máy gốc |
| `TÓM TẮT DỰ ÁN NGHIÊN CỨU.md`, `detail idea.md` | Tài liệu ý tưởng gốc — nội dung đã được hợp nhất vào `docs/TONG_HOP_Y_TUONG.md` |

Đây là đường **"gửi bản đã dựng"**: cộng sự chạy mô hình được ngay, nhưng không
dựng lại được từ đầu. Nếu cần dựng lại, gửi kèm `data_raw/` hoặc để họ chạy lại
theo README §5.
