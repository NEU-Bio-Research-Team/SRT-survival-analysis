# Tổng hợp bộ dữ liệu WITS và câu chuyện nghiên cứu “Sinking Relationships”

## Mục đích của tài liệu

Tài liệu này giúp người đọc:

1. biết chính xác gói `wits_data_20260825.tar.gz` chứa những gì;
2. hiểu đơn vị quan sát, cách dựng dữ liệu và ý nghĩa của các nhóm biến;
3. hiểu bộ dữ liệu phục vụ câu hỏi nghiên cứu nào;
4. phân biệt phần đã có dữ liệu với phần mới chỉ là định hướng nghiên cứu;
5. nắm các hạn chế phải nói trước khi trình bày kết quả;
6. có thể trình bày lại với giảng viên mà không biến bài nói thành một danh sách 158 biến.

Tài liệu được tổng hợp từ:

- `wits_data_20260825_NOI_DUNG.md`;
- toàn bộ 13 slide của `Vietnam_Export_Portfolio_Resilience.pdf`;
- bản mới nhất `SINKING RELATIONSHIPS (1).md`;
- danh sách tệp thật trong archive;
- header và số dòng của các bảng dữ liệu thật;
- `README.md`, `docs/DATA_HANDOFF.md` và một số tài liệu kiểm kê liên quan.

Các con số về kích thước panel, số importer, sản phẩm, spell, event và mẫu EU bên dưới đã được kiểm tra trực tiếp trên file, không chỉ sao chép từ tài liệu mô tả.

---

## 1. Tóm tắt điều quan trọng nhất

### 1.1. Bộ dữ liệu này là gì?

Đây là một bộ dữ liệu panel để nghiên cứu **tuổi thọ của các quan hệ xuất khẩu của Việt Nam**. Một quan hệ được định nghĩa là:

> **một thị trường nhập khẩu × một nhóm sản phẩm Việt Nam**.

Ví dụ: “Đức × một nhóm hàng may mặc của Việt Nam” là một quan hệ. Quan hệ này có thể tồn tại liên tục nhiều năm, có thể đứt sau một năm, hoặc còn sống khi dữ liệu kết thúc.

Bộ dữ liệu không chỉ cho biết Việt Nam xuất khẩu bao nhiêu. Nó cho phép hỏi:

- quan hệ nào tồn tại lâu hơn;
- quan hệ nào có nguy cơ chấm dứt cao hơn;
- quy mô, thị phần, thuế, FTA, điều kiện thị trường và đặc điểm sản phẩm liên quan thế nào tới nguy cơ đứt gãy;
- sau khi ước lượng rủi ro, Việt Nam nên duy trì, mở rộng, thu hẹp, rút khỏi hoặc mở mới quan hệ nào.

### 1.2. Quy mô chính xác của dữ liệu đích

| Chỉ tiêu | Giá trị kiểm tra trực tiếp |
|---|---:|
| Exporter | Việt Nam (`VNM`) |
| Importer | 147 thị trường |
| Cửa sổ của panel đã dựng | 2003–2025 |
| Số năm trong panel | 23 |
| Nhóm sản phẩm ổn định | 4.621 `product_family` |
| Số spell | 228.175 |
| Số spell đã chấm dứt | 170.486 |
| Số spell right-censored | 57.689, tương đương 25,3% |
| Số spell chỉ dài một năm | 120.297, tương đương 52,7% |
| Số episode-năm | 747.719 |
| Số cột trong master panel | 158 |

File trung tâm là `analysis/panel_final.csv`, có **747.719 dòng × 158 cột**. Đây là master panel đã ghép dữ liệu thương mại, spell, thuế, FTA, vĩ mô, gravity, logistics, độ phức tạp, NTM, CBAM, thuế Mỹ và các lớp rủi ro khác.

### 1.3. Cách kể câu chuyện nghiên cứu trong một câu

> Tổng kim ngạch cho biết danh mục xuất khẩu lớn đến đâu, nhưng không cho biết danh mục bền đến đâu; nghiên cứu này ước lượng khả năng sống sót của từng quan hệ thị trường–sản phẩm, rồi dùng thông tin rủi ro đó để hỗ trợ tái cấu trúc danh mục xuất khẩu của Việt Nam.

Chuỗi logic là:

`Quan hệ thương mại → thời gian tồn tại → hazard đứt gãy → xác suất sống sót → cơ hội có điều chỉnh rủi ro → quyết định danh mục`

### 1.4. Phạm vi nghiên cứu nên trình bày

| Tầng phân tích | Phạm vi | Vai trò |
|---|---|---|
| Mẫu chính | EU-27, 2003–2023 | Survival/hazard và chính sách trong một bối cảnh thể chế tương đối thống nhất |
| Mở rộng thể chế | UK | Tách riêng trước/sau Brexit và UKVFTA; không gọi là EU-28 |
| Kiểm tra tính khái quát | 147 thị trường | Xem kết luận EU có còn đúng trên toàn cầu không |
| Mở rộng cú sốc gần đây | 2024–2025 | Thuế Mỹ 2025 và chính sách mới; không trộn với panel thuế lịch sử như thể thuế TRAINS được đo đúng năm |

Mẫu EU-27 có đủ cả 27 nước trong dữ liệu. Kiểm tra trực tiếp cho kết quả:

| Mẫu | Episode-năm | Spell | Event | Product family |
|---|---:|---:|---:|---:|
| EU-27, 2003–2023 | 148.442 | 45.815 | 35.503 | 3.423 |
| EU-27, 2003–2025 | 176.277 | 52.024 | 37.511 | 3.524 |
| EU-27 + UK, 2003–2023 | 161.289 | 49.812 | 38.567 | 3.510 |
| EU-27 + UK, 2003–2025 | 191.469 | 56.445 | 40.730 | 3.606 |

Lưu ý kiểm toán: một dòng trong `README.md` ghi “16 nước EU trong panel”. Con số này mâu thuẫn với danh sách importer thật. Dữ liệu và `selection/eu_tariff_mapping.csv` xác nhận đủ 27 nước EU, cộng UK thành 28 mã quốc gia. Khi trình bày nên dùng số kiểm tra trực tiếp ở bảng trên.

### 1.5. Trạng thái thực tế của dự án

- **Khâu thu thập và dựng master data:** về cơ bản đã hoàn thành.
- **Phân tích mô tả ban đầu:** đã có Kaplan–Meier, baseline hazard và sensitivity theo ngưỡng.
- **Mô hình nghiên cứu chính:** chưa được khóa specification và chưa có kết quả cuối cùng.
- **Tối ưu hóa danh mục:** chưa thể chạy chính thức vì chưa định nghĩa toán học “network survivability”, hàm mục tiêu và quy tắc hành động.

Vì vậy, không nên nói “nghiên cứu đã chứng minh…”. Cách nói đúng là “dữ liệu đã sẵn sàng để kiểm định…” và “kết quả hiện có mới là chẩn đoán sơ bộ”.

---

## 2. Hiểu đúng đơn vị dữ liệu

### 2.1. `product_family` là gì?

Dữ liệu thương mại gốc ở cấp HS6. Mã HS thay đổi qua các phiên bản HS, nên cùng một sản phẩm có thể mang mã khác nhau theo thời gian. Pipeline dùng các bảng concordance H1–H6 về H0, rồi gom các mã liên thông thành một `product_family` ổn định.

Ví dụ `H0_090122` là một định danh họ sản phẩm đã được quy về nền HS0. Việc dùng family ổn định tránh nhầm “mã HS đổi” thành “quan hệ thương mại chết rồi sinh lại”.

### 2.2. Khi nào một quan hệ được coi là sống?

Một cặp importer–product family được coi là sống trong năm nếu kim ngạch nhập khẩu do nước nhập khẩu khai báo đạt ít nhất **10.000 USD**.

- Từ 10.000 USD trở lên: quan hệ tồn tại trong năm đó.
- Dưới 10.000 USD: quan hệ không được coi là sống.
- Không cho phép một năm trống nằm giữa spell: một năm dưới ngưỡng làm spell đứt.
- Nếu quan hệ xuất hiện lại sau đó, nó tạo một spell mới.

Ngưỡng 10.000 USD giữ lại 99,97% tổng giá trị thương mại, nhưng vẫn có 52,7% spell chỉ dài một năm. Đây là đặc điểm thật của trade-duration data, không nên tự động xóa.

### 2.3. Spell, episode và panel khác nhau thế nào?

| Khái niệm | Ý nghĩa | File chính |
|---|---|---|
| Quan hệ | Một importer × một product family | Khái niệm kinh tế |
| Spell | Một chuỗi năm sống liên tục của quan hệ | `spells.csv` |
| Episode-năm | Một năm nằm trong một spell | `episodes.csv` |
| Master panel | Episode-năm sau khi ghép toàn bộ covariate | `panel_final.csv` |

Ví dụ một quan hệ sống 2008–2010, mất năm 2011, rồi xuất hiện lại 2013–2015 sẽ có hai spell và sáu episode-năm.

### 2.4. Left-censoring, right-censoring và administrative censoring

- **Left-censored:** spell đã sống ngay từ năm nền 2002, nên không biết nó thực sự bắt đầu từ khi nào. Các spell này bị loại khỏi survival sample.
- **Right-censored:** spell vẫn sống ở cuối thời gian quan sát. Ta biết nó đã sống đến đó nhưng chưa biết khi nào chết; giữ lại với `event = 0`.
- **Administrative censoring:** một nước ngừng nộp dữ liệu, nên không thể kết luận các quan hệ của nước đó chết. Pipeline kiểm duyệt hành chính thay vì ghi nhận một cú chết giả.

Sáu reporter được xử lý kiểm duyệt hành chính là RUS, BLR, BGD, KNA, LCA và SLB.

### 2.5. Quy ước năm sự kiện rất dễ đọc sai

Trong panel:

> `event = 1` ở năm Y nghĩa là Y là năm cuối quan hệ còn sống; quan hệ chấm dứt ở Y+1.

Do đó một chính sách bắt đầu năm 2025 phải được căn chỉnh với risk interval dẫn tới cái chết năm 2025. Nếu gắn thẳng chính sách 2025 vào `event = 1` trên dòng 2025, phân tích có thể lệch một năm.

---

## 3. Gói nén có gì bên trong?

### 3.1. Thông tin kiểm toán của archive

| Thuộc tính | Giá trị |
|---|---|
| Tên file | `wits_data_20260825.tar.gz` |
| Ngày dựng | 25/08/2026 |
| Kích thước chính xác | 166.923.025 byte, xấp xỉ 159 MiB |
| Kích thước sau giải nén | xấp xỉ 850 MiB |
| Số file thật | 228 |
| SHA-256 | `5edcc6e7ef77d5fc1aec0f2c7755064ae0f917ceec922662a14b2cf536f2c8` |

Đây là gói **bàn giao dữ liệu đã dựng**, không phải bản sao đầy đủ của toàn bộ dữ liệu thô.

### 3.2. Bảy thành phần cấp cao nhất

| Thành phần | Số file | Dung lượng sau giải nén | Vai trò |
|---|---:|---:|---|
| `analysis/` | 157 | khoảng 843 MiB | Dữ liệu đích, panel và các module đã xử lý |
| `data_raw/ntm/ave_gtap/` | 2 | khoảng 6,6 MB | Hai file thô AVE của NTM |
| `scripts/` | 37 | khoảng 569 KB | Code tải, dựng, ghép và kiểm tra |
| `docs/` | 15 | khoảng 251 KB | Thiết kế, kiểm kê, handoff, hạn chế và nhật ký |
| `selection/` | 15 | khoảng 370 KB | Danh sách nước, quy tắc chọn mẫu và mapping |
| `README.md` | 1 | khoảng 48 KB | Bản đồ tổng thể của project |
| `Sinking Relationships.md` | 1 | khoảng 9 KB | Brief nghiên cứu cũ nằm trong archive |

Điểm cần phân biệt: archive chỉ có `Sinking Relationships.md` bản cũ. Bản `SINKING RELATIONSHIPS (1).md` mà nhóm đang dùng là bản mới nhất và nằm ngoài archive; bản mới đã chốt hướng EU-27 main, UK extension và global robustness.

---

## 4. Ba file lõi trong `analysis/`

### 4.1. `analysis/panel_final.csv` — master panel

- Kích thước: 686.881.987 byte, khoảng 655 MiB.
- Quy mô: 747.719 dòng × 158 cột.
- Khóa thực tế: `spell_id + year`.
- Mỗi dòng: một spell trong một năm còn sống.
- Vai trò: nguồn duy nhất để tạo các model-specific dataset.

Không nên đưa cả 158 biến vào một regression. Master panel được thiết kế để giữ đủ thông tin và truy vết nguồn; mỗi mô hình chỉ lấy một nhóm biến phù hợp.

### 4.2. `analysis/spells.csv` — một dòng cho mỗi spell

- Kích thước: khoảng 16,5 MiB.
- Quy mô: 228.175 dòng dữ liệu, 11 cột.
- Khóa: `spell_id`.
- Dùng cho Kaplan–Meier, phân phối duration, censoring và sensitivity.

Các cột gồm định danh, năm bắt đầu/kết thúc, duration, event, right-censoring, giá trị năm đầu và giá trị trung bình.

### 4.3. `analysis/episodes.csv` — episode-năm lõi

- Kích thước: khoảng 107 MiB.
- Quy mô: 747.719 dòng dữ liệu, 22 cột.
- Khóa: `spell_id + year`.
- Chứa trade, survival và các chỉ báo cấu trúc cơ bản trước khi ghép các module ngoài.
- Có thể dựng lại bằng `build_spells.py`.

Luồng dữ liệu chính:

`Comtrade HS6 → hài hòa mã HS → áp ngưỡng 10.000 USD → dựng spells/episodes → ghép policy + market + product + risk → panel_final → survival/hazard → portfolio`

---

## 5. Các nhóm dữ liệu trong `analysis/`

### 5.1. Thương mại, survival và cấu trúc danh mục

Nằm trực tiếp trong `episodes.csv`, `spells.csv` và `panel_final.csv`.

| Nhóm | Biến tiêu biểu | Ý nghĩa |
|---|---|---|
| Quy mô | `import_value_usd` | Giá trị hàng Việt Nam do importer khai báo |
| Lượng và đơn giá | `net_weight_kg`, `unit_value_usd_per_kg` | Phân biệt thay đổi lượng với thay đổi giá; khối lượng không phủ 100% |
| Lợi thế so sánh | `rca` | Balassa RCA ở cấp product family |
| Tỷ trọng | `product_share_pct`, `partner_share_pct`, `vn_market_share_pct` | Vai trò của sản phẩm, đối tác và Việt Nam trong thị trường |
| Tập trung | `hhi_market`, `hhi_product` | Mức độ tập trung theo thị trường và sản phẩm |
| Tăng trưởng | `country_growth_pct`, `world_growth_pct` | Điều kiện tăng trưởng theo sản phẩm của Việt Nam và thế giới |
| Survival | `t_start`, `t_stop`, `event`, `right_censored` | Dữ liệu counting-process cho hazard model |

Các biến 4–9 không lấy trực tiếp từ WITS ở HS6 mà được tính từ dữ liệu Comtrade, vì WITS chỉ cung cấp nhiều chỉ số ở cấp ngành rộng hơn.

Cách đọc chính xác các chỉ báo tự tính:

- `product_share_pct`: tỷ trọng xuất khẩu của product family trong tổng xuất khẩu Việt Nam năm đó;
- `partner_share_pct`: tỷ trọng của importer trong tổng xuất khẩu Việt Nam năm đó;
- `vn_market_share_pct`: hàng Việt Nam chia cho tổng nhập khẩu của importer từ thế giới đối với đúng product family;
- `hhi_market`: tổng bình phương tỷ trọng của các thị trường trong danh mục xuất khẩu Việt Nam;
- `hhi_product`: tổng bình phương tỷ trọng của các product family;
- `country_growth_pct`: tăng trưởng xuất khẩu của Việt Nam theo từng product family, không phải tăng trưởng tổng xuất khẩu quốc gia;
- `world_growth_pct`: tăng trưởng nhập khẩu thế giới theo từng product family;
- `rca`: tỷ trọng product family trong xuất khẩu Việt Nam chia cho tỷ trọng cùng product family trong nhập khẩu thế giới.

### 5.2. Thuế lịch sử và FTA

| File/biến | Nội dung | Vai trò | Cảnh báo |
|---|---|---|---|
| `tariff_rate` | Thuế importer áp lên hàng Việt Nam | Policy covariate chính | Xem `tariff_source_year` |
| `tariff_type` | MFN hoặc PREF | Phân biệt loại biểu thuế | PREF không phủ đầy đủ |
| `tariff_source_year` | Năm thật của biểu thuế | Cờ chất lượng | 2024–2025 dùng giá trị 2023 |
| `tariff_reporter` | Reporter thuế, gồm mapping `EUN` | Truy vết nguồn | EU dùng biểu thuế chung theo năm thành viên |
| `analysis/fta_vn.csv` | 3.528 importer-năm, 9 cột | Chế độ FTA | Cho biết có ưu đãi, không luôn cho biết đúng mức ưu đãi |

`fta_vn.csv` gồm `fta_in_force`, số hiệp định, năm FTA đầu tiên, số năm từ khi có FTA, GSTP, cờ có bất kỳ hiệp định nào và tên hiệp định.

### 5.3. Thuế đối ứng Mỹ 2025

| File | Số dòng dữ liệu | Chức năng |
|---|---:|---|
| `us_tariff_vn.csv` | 23 | Bốn quy ước thuế Mỹ 2025 theo năm |
| `us_tariff_2025_monthly.csv` | 12 | Đường đi theo tháng và căn cứ pháp lý |
| `us_tariffs_2025.csv` | 166 | Bảng chương 99 đã trích xuất |
| `us_exempt_products.csv` | 547 | Tỷ lệ miễn trừ theo product family |
| `us_tariff_exemptions_2025.csv` | 667 | Miễn trừ đã gom HS6/family |
| `us_tariff_exemptions_2025_hs8.csv` | 1.087 | Danh sách HTS8 gốc để kiểm toán |

Các mức trong master panel:

- `us_recip_rate_yearend`: mức cuối năm, 20%;
- `us_recip_rate_peak`: mức đỉnh, 46%;
- `us_recip_rate_days_wt`: bình quân theo số ngày, 11,55%;
- `us_recip_rate_terminated`: cờ mức đã chấm dứt;
- `us_recip_floor`: mức sàn;
- `us_transship_rate`: mức phạt tiềm năng đối với chuyển tải;
- `us_recip_exempt_share`, `us_recip_exempt_full`: mức miễn trừ theo sản phẩm.

Nhóm nghiên cứu phải chọn một quy ước năm và giải thích. Không được trộn 20%, 46% và 11,55% như thể chúng là cùng một treatment.

### 5.4. NTM — ba họ dữ liệu khác nhau

#### A. NTM ở HS6 × năm

- `analysis/_ntm6/{REPORTER}.csv.gz`: 126 mảnh theo reporter, chỉ phục vụ quá trình merge.
- `analysis/ntm6_observed.csv`: 126 reporter và các năm họ thực sự nộp báo cáo.
- Trong panel: các cột `ntm6_*_survey`, `ntm6_*_inforce`, `ntm6_source_year`, `ntm6_observed`.

Ý nghĩa:

- `_survey`: số biện pháp theo kỳ khảo sát gần nhất;
- `_inforce`: số biện pháp có khoảng hiệu lực bao phủ năm quan sát;
- `bilateral`: biện pháp nhắm đích danh Việt Nam;
- `sps`, `tbt`, `quantity`, `price`: nhóm loại NTM; `nonh` là số biện pháp không mang tính horizontal (không áp đồng loạt theo cách phân loại của nguồn);
- `ntm6_observed`: điều kiện bắt buộc để biết năm đó có dữ liệu khảo sát thật hay không.

Độ phủ gắn vào panel là 95,2%, nhưng chỉ 36,6% dòng có NTM được nộp đúng năm. Khoảng 29,0% panel mang `ntm6_source_year` ở tương lai so với `year`, tức số liệu được mượn ngược từ kỳ khảo sát đầu tiên và phải coi là **chưa đo được**, không phải NTM thấp.

#### B. NTM quy ra tương đương thuế

| File | Số dòng dữ liệu | Nội dung |
|---|---:|---|
| `ntm_ave_vn.csv` | 2.668 | AVE bình quân theo importer–năm |
| `UNCTADGTAP11_AVEborder.csv` | dữ liệu thô 2017 | AVE ở biên giới theo GTAP sector |
| `AVE_GTAP_README_rev1.pdf` | tài liệu phương pháp | Giải thích nguồn AVE |

Các biến `ntm_ave_border_pct` và `ntm_ave_border_simple_pct` đưa NTM về cùng đơn vị phần trăm như thuế. Tuy nhiên đây là lát cắt năm 2017, được kéo qua thời gian; fixed effect theo importer có thể hấp thụ toàn bộ variation.

#### C. NTM công khai cấp ngành

| File | Số dòng dữ liệu | Độ chi tiết |
|---|---:|---|
| `ntm_country.csv` | 150 | Tổng hợp cấp quốc gia |
| `ntm_sector.csv` | 1.200 | 16 nhóm ngành, lát cắt |
| `ntm_by_type.csv` | 3.944 | Theo ngành và chương NTM |

Đây là lớp dự phòng, không nên trộn với NTM HS6 × năm trong cùng specification vì chúng đo khác khái niệm và khác độ phân giải.

### 5.5. CBAM của EU

| File | Số dòng dữ liệu | Nội dung |
|---|---:|---|
| `cbam_products.csv` | 269 | Product family nằm trong phạm vi CBAM |
| `cbam_products_cn.csv` | 56 | Mã CN, ngành và ngoại lệ để kiểm toán |

Biến trong panel gồm `cbam_in_scope`, `cbam_sector`, `cbam_partial`, `cbam_reporting_share`, `cbam_definitive`.

Trong giai đoạn panel, CBAM phản ánh **phạm vi và nghĩa vụ báo cáo**, chưa phải một mức thuế carbon. Chế độ chính thức bắt đầu 01/01/2026, sau năm cuối panel; vì vậy `cbam_definitive = 0` ở toàn bộ dữ liệu hiện tại.

### 5.6. Vĩ mô, thị trường và logistics

| File | Số dòng dữ liệu | Nội dung |
|---|---:|---|
| `macro_panel_v2.csv` | 3.552 | 147 importer + Việt Nam; GDP, GDP/người, tỷ giá, lạm phát, dân số, thương mại, CO2, năng lượng tái tạo và các cấu phần LPI |
| `macro_panel.csv` | 2.940 | Bản cũ, ít biến hơn; giữ để đối chiếu |
| `glpi.csv` | 3.552 | Bốn cách xây Green LPI |
| `epi_indicators_annual.csv` | 184.827 | 52 chỉ báo EPI, 220 nền kinh tế, 1996–2025 |

Các biến importer thường dùng trong core model là GDP và GDP/người. LPI, GLPI, CO2, renewable energy và macro mở rộng phù hợp hơn với robustness.

Bốn GLPI gồm PCA LPI–EPI, tỷ số LPI/EPI, PCA các cấu phần và trọng số bằng nhau. Các cách xây có thể xếp hạng quốc gia rất khác; hệ số tương quan hạng giữa một số biến thể gần như ngược chiều. Không nên đưa cả bốn vào một mô hình hoặc tự chọn mà không khóa phương pháp.

### 5.7. Gravity và chi phí thương mại cấu trúc

`gravity_vn.csv` có 2.940 importer-năm và 22 biến, gồm:

- khoảng cách (`dist`, `distw_harmonic`, `distcap`);
- chung biên giới và ngôn ngữ;
- lịch sử thuộc địa;
- tôn giáo và hệ pháp lý;
- bất đồng ngoại giao;
- GATT/WTO/EU/FTA/RTA;
- chi phí, thủ tục và thời gian gia nhập thị trường.

Nguồn CEPII dừng ở 2021; `gravity_source_year` trong master panel cho biết các năm được mang sang. Core thường chỉ cần `dist`, `contig`, `comlang_off`; các biến thể chế thay đổi theo thời gian sau 2021 không nên đọc như quan sát mới.

### 5.8. Phòng vệ thương mại

| File | Số dòng dữ liệu | Nội dung |
|---|---:|---|
| `ttbd_vn.csv` | 3.528 | Panel antidumping, countervailing và safeguard |
| `ttbd_vn_cases.csv` | 711 | Vụ kiện và thời điểm |
| `ttbd_vn_products.csv` | 3.231 | Mã sản phẩm liên quan vụ kiện |

Các cột `ad_*`, `cvd_*`, `sg_*`, `ttb_any_in_force` cho biết khởi xướng và hiệu lực. Phải kiểm `ttbd_observed`; dữ liệu sau 2015 không còn là quan sát trực tiếp đầy đủ và chỉ nên dùng như robustness có cảnh báo.

### 5.9. Độ phức tạp và sốc chung

| File | Số dòng dữ liệu | Nội dung |
|---|---:|---|
| `complexity_product.csv` | 28.563 | PCI theo HS4–năm và giá trị xuất khẩu thế giới |
| `complexity_country.csv` | 3.404 | ECI, COI và diversity theo nước–năm |
| `shocks_annual.csv` | 24 | GEPU và các chỉ số giá hàng hóa theo năm |

PCI cho đặc điểm sản phẩm; ECI/COI/diversity cho năng lực nền kinh tế; GEPU và giá hàng hóa là common shocks. Vì Việt Nam là exporter duy nhất, nhiều biến exporter chỉ thay đổi theo năm và sẽ đồng tuyến với year fixed effects.

### 5.10. Kết quả chẩn đoán hiện có

| File | Số dòng dữ liệu | Nội dung | Trạng thái |
|---|---:|---|---|
| `km_survival.csv` | 69 | Đường Kaplan–Meier cho toàn mẫu, FTA và không FTA | Sơ bộ |
| `hazard_baseline.csv` | 18 | Hệ số và hazard ratio baseline cloglog | Sơ bộ, chưa phải kết quả cuối |
| `threshold_sensitivity.csv` | 5 | Kết quả ở 5 ngưỡng 1.000–500.000 USD | Chẩn đoán phương pháp |

Đây là output, không phải explanatory input.

---

## 6. `selection/` — dữ liệu định nghĩa mẫu

| File | Vai trò |
|---|---|
| `importers_vn.csv` | 147 importer được chọn, tier A/B và chỉ tiêu sàng lọc |
| `importer_vn_all.csv` | 193 ứng viên, gồm 46 nước bị loại và lý do |
| `vn_partner_screen.csv` | 3.569 nước-năm sàng lọc giao thương với Việt Nam |
| `exporter_selected.csv` | Exporter đã khóa là Việt Nam |
| `eu_tariff_mapping.csv` | Mapping nước EU/UK theo năm sang reporter thuế, thường là `EUN` |
| `country_meta.csv` | Tên, khu vực và nhóm thu nhập |
| `comtrade_da.csv` | Độ sẵn có dữ liệu Comtrade |
| `ntm_availability.csv` | Độ phủ NTM trong cửa sổ nghiên cứu |
| `ntm_types.csv` | Từ điển 16 mã/nhóm NTM |
| `trains_avail.csv` | Độ sẵn có TRAINS theo nước–năm |
| `trains_countries.csv` | Mapping mã TRAINS–ISO3 và cờ nằm trong panel |
| `trains_export_targets.csv` | Danh sách target để xuất dữ liệu TRAINS |
| `importer_candidates.csv` | Ứng viên importer theo thiết kế cũ |
| `importers_selected.csv` | 53 importer của thiết kế cũ |
| `exporters_selected.csv` | Danh sách exporter của thiết kế cũ |

Quy tắc chọn 147 importer yêu cầu cả ba điều kiện trong 2002–2021:

1. nước đó nộp dữ liệu HS hằng năm cho Comtrade;
2. có biểu thuế TRAINS của mình hoặc dùng biểu chung EU;
3. thực sự có khai nhập khẩu từ Việt Nam.

Tier A gồm 102 nước có độ phủ mạnh hơn; tier B gồm 45 nước chấp nhận được. Có thể dùng riêng tier A như một robustness check.

---

## 7. `scripts/`, `docs/` và dữ liệu thô đi kèm

### 7.1. `scripts/`

Archive có 25 file mã nguồn và 12 file `.pyc` vô hại.

| Nhóm | Chức năng chính |
|---|---|
| Chọn mẫu | `select_countries.py`, `select_importers_vn.py` |
| Tải trade | `fetch_trade.py`, `pull_2022_2024.sh` |
| Tải thuế/NTM | `fetch_tariffs.py`, `fetch_ntm_availability.py`, `fetch_ntm_researcher.py`, `fetch_ntm_trains.py` |
| Tải policy mới | `fetch_us_tariffs_2025.py`, `fetch_cbam_scope.py` |
| Tải covariate | `fetch_macro.py`, `fetch_covariates.py`, `fetch_epi_annual.py` |
| Dựng trade/survival | `build_spells.py` |
| Dựng policy/NTM | `build_ntm.py`, `build_ntm6.py`, `build_ntm_ave.py`, `extract_us_exemptions.py`, `build_us_tariff_panel.py` |
| Dựng covariate | `build_covariates.py`, `build_glpi.py` |
| Ghép master | `merge_panel.py` |
| Kiểm tra | `survival_baseline.py`, `spell_threshold_sensitivity.py`, `wits_probe.py` |

Chỉ ba script cần API key Comtrade: `fetch_trade.py`, `select_importers_vn.py`, `select_countries.py`. Key không nằm trong archive.

### 7.2. `docs/`

| Tài liệu | Nên dùng khi nào |
|---|---|
| `DATA_HANDOFF.md` | Đọc đầu tiên để hiểu brief ↔ dữ liệu và các bẫy |
| `TONG_HOP_Y_TUONG.md` | Tổng hợp ý tưởng ban đầu |
| `MAPPING_IDEA_DATA.md` | Ánh xạ câu hỏi nghiên cứu với nguồn dữ liệu |
| `THIET_KE_VIET_NAM.md` | Vì sao chuyển sang exporter duy nhất là Việt Nam |
| `DATA_INVENTORY_VN.md` | Kiểm kê dữ liệu trên đĩa; một số số liệu là snapshot cũ |
| `TIEN_DO_SO_VOI_SINKING.md` | Tiến độ so với brief |
| `BRIEF_SINKING_COVERAGE.md` | Đối chiếu brief bằng tiếng Anh |
| `COVARIATES_ADDED.md` | Nguồn covariate được bổ sung |
| `KIEM_CHUNG_DU_LIEU_WITS.md` | Các kiểm tra API WITS thật |
| `TIEN_TRINH_THU_THAP.md` | Nhật ký thi công |
| `DOI_CHIEU_ESSENCES_NTM.md` | Đối chiếu yêu cầu và dữ liệu NTM |
| `essences.txt` | Yêu cầu NTM gốc |
| `guide.md` | Khảo sát ban đầu, có chỗ sai; chỉ dùng làm lịch sử |
| Hai file prompt TRAINS | Dấu vết của hướng tải NTM đã bỏ |

Một số tài liệu được viết ở các thời điểm khác nhau nên số spell/product có thể cũ. Khi mâu thuẫn, ưu tiên theo thứ tự: **file dữ liệu thật → README/Data Handoff ngày 25/08 → tài liệu snapshot cũ**.

### 7.3. Dữ liệu thô đi kèm

Chỉ có hai file trong `data_raw/ntm/ave_gtap/`:

- `UNCTADGTAP11_AVEborder.csv`;
- `AVE_GTAP_README_rev1.pdf`.

Phần raw còn lại không có trong gói, gồm trade, world trade, mirror, tariff, gravity, EPI, CBAM, RTA, shocks, WDI, TTBD, NTM researcher và concordance. Muốn dựng lại từ số không phải tải lại hoặc nhận thêm raw data.

### 7.4. Những thứ cố ý không nằm trong archive

- `.env` và API key;
- gần như toàn bộ `data_raw/`;
- `logs/` và `probe_out/`;
- các tài liệu ý tưởng gốc đã được hợp nhất;
- bản latest `SINKING RELATIONSHIPS (1).md`.

### 7.5. Bản đồ nguồn gốc dữ liệu

| Khối dữ liệu | Nguồn chính |
|---|---|
| Trade Việt Nam→importer, importer→thế giới, mirror | UN Comtrade API |
| Thuế MFN/PREF lịch sử | WITS–UNCTAD TRAINS |
| NTM HS6 và NTM cấp ngành | UNCTAD TRAINS researcher file và WITS public files |
| NTM ad-valorem equivalent | UNCTAD–GTAP 11 |
| GDP và chỉ báo vĩ mô | World Bank WDI/WITS development indicators |
| Gravity | CEPII Gravity V202211 |
| FTA | DESTA |
| Trade remedies | World Bank Temporary Trade Barriers Database |
| PCI/ECI/COI | Atlas of Economic Complexity |
| LPI | World Bank Logistics Performance Index |
| EPI | Yale Environmental Performance Index archive |
| Giá hàng hóa và GEPU | Các chuỗi World Bank/GEPU đã dựng trong `shocks_annual.csv` |
| CBAM | Regulation (EU) 2023/956 Annex I |
| Thuế Mỹ 2025 | HTS Chapter 99 và tám văn bản hành pháp/pháp lý đi kèm |

---

## 8. Bản đồ 158 cột trong `panel_final.csv`

Không cần học thuộc 158 cột. Nên hiểu chúng theo module.

### 8.1. Định danh và survival

`spell_id`, `importer`, `exporter`, `product_family`, `year`, `spell_start_year`, `spell_end_year`, `right_censored`, `t_start`, `t_stop`, `event`.

### 8.2. Trade và cấu trúc danh mục

`import_value_usd`, `net_weight_kg`, `unit_value_usd_per_kg`, `rca`, `product_share_pct`, `partner_share_pct`, `vn_market_share_pct`, `hhi_market`, `hhi_product`, `country_growth_pct`, `world_growth_pct`.

### 8.3. Thuế lịch sử

`tariff_rate`, `tariff_type`, `tariff_source_year`, `tariff_reporter`.

### 8.4. Vĩ mô exporter và importer

Các biến GDP growth, GDP, GDP/người, tỷ giá, lạm phát, dân số; phía importer có thêm tỷ lệ xuất/nhập khẩu trên GDP, CO2/người và tỷ lệ năng lượng tái tạo.

Với exporter duy nhất là Việt Nam, exporter macro không có variation giữa các quan hệ trong cùng năm và thường không nên vào mô hình có year fixed effects.

### 8.5. LPI và GLPI

Các cấu phần LPI: overall, customs, infrastructure, international shipments, logistics competence, tracking/tracing, timeliness và `importer_lpi_source_year`.

Bốn GLPI: `importer_glpi_pca_lpi_epi`, `importer_glpi_ratio_lpi_epi`, `importer_glpi_pca_components`, `importer_glpi_equal_weights`.

### 8.6. FTA

`fta_in_force`, `n_agreements`, `first_fta_year`, `years_since_fta`, `gstp_in_force`, `any_agreement_in_force`, `fta_names`.

### 8.7. Trade remedies

`ad_initiated`, `ad_in_force`, `cvd_initiated`, `cvd_in_force`, `sg_initiated`, `sg_in_force`, `ttb_any_in_force`, `ttbd_observed`.

### 8.8. Gravity và thể chế

Khoảng cách, chung biên giới/ngôn ngữ/thuộc địa/tôn giáo/pháp lý; GATT/WTO/EU/FTA/RTA; bất đồng ngoại giao; chi phí, số thủ tục và thời gian entry; cùng `gravity_source_year`.

### 8.9. Thuế Mỹ 2025 và miễn trừ

Các mức year-end, peak, day-weighted, terminated, floor, transshipment, ngày hiệu lực; cùng tỷ lệ và cờ miễn trừ theo product family.

### 8.10. NTM AVE

`ntm_ave_border_pct`, `ntm_ave_border_simple_pct`, số sector và năm nguồn.

### 8.11. Sốc chung

CMO all commodities, GEPU và 16 chỉ số giá nhóm hàng hóa.

### 8.12. Độ phức tạp

`pci`, `pci_source_year`, `product_hs4`, `importer_eci`, `importer_coi`, `importer_diversity`, `exporter_eci`.

### 8.13. CBAM

`cbam_in_scope`, `cbam_sector`, `cbam_partial`, `cbam_reporting_share`, `cbam_definitive`.

### 8.14. NTM cấp ngành

Reporter, survey year, sector, coverage/frequency, tỷ lệ sản phẩm có từ ba NTM, SPS/TBT/quantity/technical/nontechnical coverage và số loại NTM.

### 8.15. NTM HS6 × năm

Các count survey và in-force theo all/non-horizontal/bilateral/SPS/TBT/quantity/price, cùng `ntm6_source_year` và `ntm6_observed`.

---

## 9. Bộ dữ liệu trả lời câu chuyện trong PDF và bản latest như thế nào?

### 9.1. Khối 1 — Survival: quan hệ nào sống lâu hơn?

Dữ liệu dùng:

- `spells.csv` để mô tả duration và Kaplan–Meier;
- `episodes.csv` hoặc subset của `panel_final.csv` để ước lượng hazard theo năm;
- event, censoring và ngưỡng 10.000 USD để xác định outcome.

Đầu ra mong muốn:

- đường survival theo nhóm;
- xác suất sống qua 1, 3, 5 hoặc 10 năm;
- phân bố spell một năm và spell dài;
- risk score cho mỗi quan hệ.

### 9.2. Khối 2 — Hazard: điều gì liên quan đến rủi ro đứt gãy?

Dữ liệu dùng theo lớp:

1. trade performance: value, RCA, share, HHI, growth;
2. market: GDP, GDP/người và gravity;
3. product: PCI và HS4;
4. institutions: tariff và FTA;
5. robustness: NTM, GLPI và trade remedies.

Mô hình nên bắt đầu đơn giản bằng Kaplan–Meier và discrete-time hazard/cloglog, sau đó mới thêm fixed effects, clustering và các block robustness.

### 9.3. Khối 3 — Policy shock: chính sách làm rủi ro thay đổi thế nào?

Các cơ chế có trong data:

- tariff lịch sử và thay đổi tariff;
- FTA/EVFTA và số năm từ khi FTA có hiệu lực;
- Brexit/UKVFTA ở extension;
- NTM và trade remedies;
- CBAM scope/reporting;
- thuế đối ứng Mỹ 2025.

Câu hỏi trung tâm không phải chỉ là “thuế có tăng hazard không”, mà là “cùng một thay đổi chính sách có tác động khác nhau theo thị trường, sản phẩm và chất lượng quan hệ không”.

### 9.4. Khối 4 — Portfolio choice: khi biết rủi ro, nên làm gì?

Hai trục của quyết định là:

- giá trị xuất khẩu hiện tại;
- xác suất sống sót hoặc hazard dự báo.

Logic hành động dự kiến:

| Giá trị | Sống sót | Gợi ý hành động khái niệm |
|---|---|---|
| Cao | Cao | Duy trì |
| Thấp | Cao | Mở rộng hoặc mở mới |
| Cao | Thấp | Thu hẹp, giảm phụ thuộc hoặc phòng vệ |
| Thấp | Thấp | Rút khỏi hoặc không ưu tiên |

Đây mới là logic khái niệm. Chưa có ngưỡng toán học chính thức cho maintain/expand/reduce/enter/exit.

### 9.5. Đóng góp kỳ vọng

Đóng góp không chỉ là chạy survival analysis. Điểm mới dự kiến là nối hai nhánh:

- literature về tuổi thọ quan hệ thương mại;
- tối ưu hóa/phân bổ danh mục dưới rủi ro.

Tức là dùng survival information để thay đổi quyết định danh mục, thay vì chỉ tối đa hóa kim ngạch hiện tại.

---

## 10. Kết quả mô tả sơ bộ có thể nói gì?

### 10.1. Sensitivity theo ngưỡng

| Ngưỡng USD | Spell | Spell một năm | Median duration | Giá trị thương mại giữ lại |
|---:|---:|---:|---:|---:|
| 1.000 | 345.740 | 55,3% | 1 năm | 100,00% |
| 10.000, đang dùng | 228.175 | 52,7% | 1 năm | 99,97% |
| 50.000 | 140.912 | 48,9% | 2 năm | 99,81% |
| 100.000 | 108.051 | 46,6% | 2 năm | 99,64% |
| 500.000 | 53.340 | 41,9% | 2 năm | 98,55% |

Thông điệp: one-year spells không biến mất dù tăng ngưỡng rất mạnh. Vì vậy nên xử lý bằng sensitivity hoặc mô hình riêng, không định nghĩa chúng biến mất.

### 10.2. Kaplan–Meier toàn mẫu

Đường sơ bộ cho thấy xác suất sống còn ước tính:

- sau 1 năm: khoảng 53,1%;
- sau 2 năm: khoảng 38,9%;
- sau 5 năm: khoảng 25,3%;
- sau 10 năm: khoảng 18,9%.

Nhóm có FTA có đường sống sót cao hơn nhóm không FTA trong thống kê mô tả. Tuy nhiên đây không phải bằng chứng nhân quả: hai nhóm khác nhau về quy mô thị trường, cơ cấu sản phẩm, lịch sử quan hệ và nhiều yếu tố khác.

### 10.3. Baseline hazard

File `hazard_baseline.csv` cho thấy dữ liệu và pipeline mô hình có thể chạy được. Không nên dùng dấu hoặc độ lớn các hệ số hiện tại làm kết luận nghiên cứu, vì specification, timing, fixed effects, sample EU và biến policy chính chưa được khóa.

---

## 11. Những bẫy và hạn chế phải nói chủ động

### 11.1. Thuế ưu đãi chưa được đo đầy đủ

Chỉ 13 reporter nộp biểu thuế gọi đích danh Việt Nam. Nhiều ưu đãi nằm dưới mã nhóm như ASEAN, AANZFTA hoặc GSP mà WITS không công bố đầy đủ thành viên. `fta_vn.csv` có thể phục hồi việc **có ưu đãi**, nhưng không luôn phục hồi đúng **mức thuế ưu đãi**.

Hậu quả: `tariff_rate` có thể cao hơn mức thực tế ở khoảng 39% episode có FTA. Với EU main, nên dựng lại applied/preferential tariff theo schedule chính thức và EVFTA trước khi gọi đây là treatment chính.

### 11.2. Thuế 2024–2025 bị carry-forward

TRAINS không công bố biểu thuế cho hai năm này. `tariff_source_year` cho thấy panel đang mang giá trị 2023 sang. Chỉ lớp thuế Mỹ 2025 có variation policy mới thật sự trong 2025.

### 11.3. NTM không phải chuỗi hằng năm hoàn hảo

- File researcher bắt đầu từ 2010.
- Các nước nộp theo lịch khảo sát rời rạc.
- NTM bằng 0 trước kỳ khảo sát đầu tiên không đồng nghĩa “không có NTM”.
- Phải dùng `ntm6_observed` và `ntm6_source_year`.
- Không trộn NTM cấp ngành, NTM HS6 và NTM AVE trong cùng một specification mà không giải thích.

### 11.4. Ô trống không phải số 0

- Cột thuế Mỹ chỉ có nghĩa cho importer USA.
- Cột CBAM chỉ có nghĩa cho importer EU theo tư cách thành viên từng năm.
- Blank thường nghĩa là “biện pháp không áp cho dòng này”; zero nghĩa là “có trường áp dụng và giá trị bằng 0”.

### 11.5. CBAM chưa phải một mức thuế carbon trong panel

Data hiện chỉ cho biết sản phẩm nằm trong phạm vi và tỷ lệ phải báo cáo. Không được diễn giải `cbam_in_scope` như một carbon price trong 2003–2025.

### 11.6. GLPI chưa có construction chính

Bốn biến thể có thể cho thứ hạng quốc gia khác nhau đáng kể. Chọn construction là quyết định phương pháp có khả năng đổi kết luận, không phải thao tác dữ liệu trung tính.

### 11.7. Trade remedies yếu sau 2015

Các vụ khởi xướng mới sau 2015 không được quan sát đầy đủ. Dùng `ttbd_observed` hoặc giới hạn thời gian khi chạy robustness.

### 11.8. Reporting gap có thể tạo “cái chết giả”

Nếu importer ngừng nộp Comtrade mà vẫn ghi event, mô hình sẽ nhầm thiếu dữ liệu thành quan hệ chấm dứt. Pipeline đã xử lý sáu reporter rõ nhất, nhưng năm 2024–2025 vẫn có độ bất định reporting cao hơn cửa sổ chính.

### 11.9. Survival không tự động là causal effect

Mô hình hazard mô tả hoặc dự báo mối liên hệ. Muốn nói một chính sách **gây ra** quan hệ đứt gãy cần identification strategy, treatment timing, counterfactual và robustness phù hợp.

---

## 12. Những gì dữ liệu làm được và chưa làm được

### 12.1. Đã làm được ngay

- mô tả duration và survival theo thị trường, sản phẩm, FTA và nhóm rủi ro;
- chạy KM và discrete-time hazard;
- kiểm soát quy mô, gravity và đặc điểm sản phẩm;
- thử từng module NTM, GLPI, trade remedies;
- tách EU-27, UK và global robustness;
- tạo risk score sau khi khóa mô hình;
- kiểm tra độ nhạy theo ngưỡng và one-year spells.

### 12.2. Chưa thể kết luận ngay từ master panel

- hiệu ứng nhân quả của tariff/FTA;
- network survivability là bao nhiêu;
- quan hệ nào chắc chắn phải enter/exit;
- danh mục tối ưu chính thức;
- applied tariff EU chính xác cho mọi product–year;
- tác động giá CBAM trước năm 2026.

### 12.3. Những biến/output còn phải tạo

- log và lag của value, RCA, share, HHI;
- cờ source-year hợp lệ;
- EU membership theo năm, EVFTA và UK/Brexit regime;
- EU applied/preferential tariff sạch;
- predicted hazard và survival probability theo horizon;
- candidate universe gồm cả quan hệ chưa hoạt động để nghiên cứu entry;
- expected export có điều chỉnh rủi ro;
- action label với ngưỡng kinh tế rõ ràng;
- portfolio weights, portfolio HHI và network survivability.

---

## 13. Sáu quyết định nghiên cứu cần chốt tiếp

1. **Network survivability được định nghĩa bằng gì?** Có thể là tỷ lệ giá trị còn sống, xác suất tối thiểu của danh mục, expected loss dưới shock, hay một thước đo mạng lưới khác.
2. **Hàm mục tiêu tối ưu hóa là gì?** Tối đa hóa export kỳ vọng, có phạt tập trung/rủi ro, hay tối đa hóa utility đa mục tiêu?
3. **Quy tắc maintain/expand/reduce/enter/exit là gì?** Cần ngưỡng định lượng và candidate universe.
4. **Specification hazard chính là gì?** Cloglog hay Cox, fixed effects nào, clustering nào, dùng policy ở t hay t−1?
5. **Construction GLPI nào được chọn?** Một bản chính và các bản sensitivity.
6. **Xử lý one-year spells thế nào?** Giữ trong main, tách tầng, hoặc chạy robustness; không nên xóa mặc định.

Ngoài ra phải chốt quy ước thuế Mỹ 2025 và cách xây applied tariff EU/EVFTA.

---

## 14. Bộ dữ liệu nên được thu gọn thế nào trước khi chạy mô hình?

Nên giữ kiến trúc module:

| Lớp | File dự kiến | Vai trò |
|---|---|---|
| Master | `panel_final.csv` | Giữ toàn bộ thông tin, không sửa đè |
| EU survival core | `EU27_survival_master.csv` | Trade + spell + tariff/FTA + GDP + gravity + PCI + structure |
| EU policy | `EU27_tariff_panel.csv` | Applied tariff, EVFTA và source metadata |
| Robustness | `EU27_robustness.csv` | NTM, GLPI, TTB và controls tùy chọn |
| UK extension | `UK_extension.csv` | Brexit/UKVFTA riêng |
| Global robustness | `global_robustness.csv` | Cùng core schema trên 147 importer |
| Prediction | `EU27_portfolio_inputs.csv` | Hazard/survival dự báo và value |
| Candidate universe | `EU27_candidate_universe.csv` | Quan hệ active và inactive để nghiên cứu entry |
| Documentation | dictionary + QC report | Định nghĩa, nguồn, missing rule và kiểm tra |

Nguyên tắc: **master data lớn để lưu trữ; model data nhỏ để phân tích**.

---

## 15. Kịch bản trình bày với giảng viên

### 15.1. Bản nói khoảng 7–10 phút

**Mở đầu — vấn đề nghiên cứu**

“Bộ dữ liệu của nhóm không chỉ đo tổng kim ngạch xuất khẩu. Nhóm coi mỗi cặp thị trường nhập khẩu–nhóm sản phẩm là một quan hệ thương mại và theo dõi quan hệ đó sống bao lâu. Lý do là một danh mục lớn vẫn có thể mong manh nếu nó tập trung vào các quan hệ dễ đứt gãy.”

**Thiết kế dữ liệu**

“Exporter được khóa là Việt Nam. Dữ liệu bao phủ 147 importer, 4.621 họ sản phẩm HS6 đã được hài hòa qua các phiên bản HS và giai đoạn 2003–2025. Một quan hệ được coi là sống khi giá trị nhập khẩu do đối tác khai đạt ít nhất 10.000 USD trong năm.”

**Quy mô**

“Master panel có 747.719 episode-năm, 228.175 spell và 158 biến. Trong đó 57.689 spell còn sống ở cuối quan sát nên được right-censor thay vì tính là chết.”

**Các lớp thông tin**

“Ngoài trade và spell, panel có tariff, FTA, GDP, gravity, PCI, concentration, NTM, logistics xanh, trade remedies, CBAM và thuế Mỹ 2025. Tuy nhiên các biến được tổ chức thành core và robustness, không đưa 158 biến vào một mô hình.”

**Hướng thực nghiệm**

“EU-27 giai đoạn 2003–2023 là mẫu chính; UK là extension; 147 thị trường dùng kiểm tra tính khái quát; 2024–2025 tách làm policy-shock extension. Quy trình là KM → hazard → predicted survival → risk-adjusted opportunity → portfolio reconfiguration.”

**Trạng thái và hạn chế**

“Dữ liệu đã dựng xong nhưng mô hình chính và bài toán tối ưu chưa chốt. Những hạn chế lớn nhất là thuế ưu đãi chưa được quan sát đầy đủ, tariff 2024–2025 carry-forward từ 2023, NTM có lịch survey rời rạc, CBAM chưa phải giá carbon và định nghĩa network survivability còn mở.”

**Kết luận**

“Giá trị của bộ dữ liệu là cho phép chuyển câu hỏi từ ‘Việt Nam xuất khẩu bao nhiêu?’ sang ‘quan hệ nào đáng duy trì khi tính nghiêm túc tới rủi ro sống sót?’.”

### 15.2. Năm câu hỏi thầy có thể hỏi

**1. Vì sao dùng importer-reported data thay vì số Việt Nam khai?**  
Vì outcome là hàng Việt Nam thực sự được thị trường đích ghi nhận nhập khẩu. Mirror data của Việt Nam chỉ dùng đối chiếu.

**2. Vì sao chọn ngưỡng 10.000 USD?**  
Đây là ngưỡng WITS Trade Outcomes dùng; sensitivity cho thấy nó giữ 99,97% giá trị. Tuy nhiên one-year spells vẫn nhiều nên sẽ được kiểm tra độ vững.

**3. Vì sao EU-27 là mẫu chính khi có 147 thị trường?**  
EU cho bối cảnh thể chế thống nhất hơn, có EVFTA, đủ variation giữa nước và sản phẩm, và vẫn có 148.442 episode-năm trong cửa sổ chính. Global panel được giữ để kiểm tra external validity.

**4. Có thể nói FTA làm quan hệ sống lâu hơn chưa?**  
Chưa. KM mô tả nhóm FTA có survival cao hơn, nhưng chưa xử lý selection và confounders. Cần hazard model và identification phù hợp trước khi nói causal.

**5. Danh mục tối ưu đã có chưa?**  
Chưa. Cần khóa mô hình survival, dự báo xác suất sống, xây candidate universe và định nghĩa network survivability cùng objective/constraints trước.

---

## 16. Thứ tự đọc file để nắm project nhanh nhất

1. Tài liệu này.
2. `SINKING RELATIONSHIPS (1).md` để hiểu hướng nghiên cứu latest.
3. `Vietnam_Export_Portfolio_Resilience.pdf` để nắm cách kể câu chuyện bằng slide.
4. `wits_data_20260825_NOI_DUNG.md` để xem inventory archive.
5. `docs/DATA_HANDOFF.md` để hiểu source, coverage và bẫy.
6. `README.md` để xem pipeline và reproducibility.
7. Chỉ sau đó mới mở `panel_final.csv` hoặc dựng curated EU datasets.

---

## 17. Kết luận cuối cùng

Bộ archive là một gói bàn giao dữ liệu đã dựng tương đối hoàn chỉnh cho nghiên cứu survival của xuất khẩu Việt Nam. Giá trị chính không nằm ở số lượng 158 cột, mà ở việc các lớp dữ liệu đã được nối vào đúng đơn vị kinh tế **thị trường × sản phẩm × spell × năm**.

Ba thông điệp cần giữ nhất khi trình bày là:

1. **Kim ngạch cao không đồng nghĩa sức bền cao.**
2. **Data cho phép ước lượng rủi ro chấm dứt ở cấp quan hệ, không chỉ cấp quốc gia hay ngành.**
3. **Bước đóng góp mới — tái cấu trúc danh mục dưới ràng buộc sống sót — vẫn cần nhóm định nghĩa mô hình toán và quy tắc quyết định.**

Nói ngắn gọn: phần data đã tạo được nền tảng thực nghiệm mạnh; phần nghiên cứu tiếp theo là biến nền tảng đó thành một mô hình survival đáng tin cậy và một bài toán portfolio có ý nghĩa kinh tế rõ ràng.
