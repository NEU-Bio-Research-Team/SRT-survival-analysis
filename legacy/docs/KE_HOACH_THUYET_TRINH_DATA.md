# Kế hoạch thuyết trình bộ dữ liệu cho giảng viên

Mục tiêu: sau 25 phút, thầy phải trả lời được ba câu — **dữ liệu này đo cái gì**,
**từng file nằm ở đâu trong hệ thống**, và **nó đang phục vụ câu hỏi nghiên cứu nào**.
Thầy chưa từng mở bộ dữ liệu này, nên bài nói phải dựng khung trước, đổ chi tiết sau.

---

## 0. Nguyên tắc điều hướng

Trở ngại lớn nhất không phải 228 file hay 158 cột. Trở ngại là **đơn vị quan sát**.
Khi thầy nắm được `spell_id × year`, mọi file còn lại tự có chỗ đứng, vì mỗi file
chỉ rơi vào một trong ba loại:

1. thứ **định nghĩa** đơn vị (mẫu, ngưỡng, mã sản phẩm);
2. thứ **gắn vào** đơn vị ở một khóa ghép nào đó (12 module covariate);
3. thứ **sinh ra từ** đơn vị (panel master và các output chẩn đoán).

Câu điều hướng nói ngay đầu buổi và nhắc lại ở giữa buổi:

> "Bộ dữ liệu chỉ có **một đơn vị quan sát** và **sáu khóa ghép**.
> Mọi file trong gói đều thuộc về một trong hai thứ đó."

Ba lỗi phải tránh:

- đọc danh sách file theo thứ tự alphabet;
- trình bày 158 cột;
- nói "nghiên cứu đã chứng minh" trong khi mới có chẩn đoán mô tả.

---

## 1. Kịch bản 25 phút — năm chặng

### Chặng 1 (0–3′) — Dữ liệu này sinh ra để trả lời câu hỏi gì

Mục tiêu: thầy hiểu **vì sao phải dựng dữ liệu mới** thay vì dùng số kim ngạch có sẵn.

Mở bằng một quan hệ có thật, không mở bằng định nghĩa:

> "Việt Nam bán một dòng hàng may mặc sang Đức từ năm 2005. Năm đầu 19 nghìn USD,
> đến 2011 đạt 1,92 triệu USD. Năm 2020 rơi xuống 15,8 nghìn. Sau 2021 thì quan hệ
> đó chấm dứt. Nếu chỉ nhìn tổng kim ngạch xuất khẩu sang Đức, không có gì cho thấy
> quan hệ này đang chết. Bộ dữ liệu của em được dựng để nhìn thấy đúng chỗ đó."

Rồi mới nêu tương phản:

| Số liệu thương mại thông thường | Bộ dữ liệu này |
|---|---|
| Đơn vị: nước × năm, hoặc ngành × năm | Đơn vị: **thị trường × nhóm sản phẩm × spell × năm** |
| Trả lời: bán được bao nhiêu | Trả lời: quan hệ nào sống được bao lâu, rủi ro đứt gãy ở đâu |
| Kết quả: quy mô danh mục | Kết quả: **độ bền** của danh mục |

Câu định vị một dòng:

> "Kim ngạch cho biết danh mục **lớn** đến đâu, không cho biết danh mục **bền** đến đâu."

Chưa nói: nguồn dữ liệu, số file, tên biến.

---

### Chặng 2 (3–11′) — Đơn vị quan sát, dạy bằng một quan hệ có thật

Đây là chặng quan trọng nhất. Nếu chặng này trôi, cả buổi trôi.

**Bước 1 — định nghĩa quan hệ.** Một quan hệ = một thị trường nhập khẩu × một
`product_family`. Quan hệ được coi là **sống** trong năm nếu nước nhập khẩu khai
nhập ít nhất **10.000 USD** hàng Việt Nam của đúng nhóm sản phẩm đó.

**Bước 2 — chiếu timeline có thật.** Dùng cặp Đức × `H0_620429`, giai đoạn 2003–2025:

| spell_id | Năm sống | Duration | event | right_censored |
|---|---|---:|---:|---:|
| `DEU_VNM_H0_620429_2006` | 2006 | 1 | 1 | 0 |
| `DEU_VNM_H0_620429_2010` | 2010 | 1 | 1 | 0 |
| `DEU_VNM_H0_620429_2013` | 2013–2014 | 2 | 1 | 0 |
| `DEU_VNM_H0_620429_2022` | 2022 | 1 | 1 | 0 |
| `DEU_VNM_H0_620429_2024` | 2024–2025 | 2 | 0 | **1** |

Từ đúng một bảng này rút ra được toàn bộ từ vựng:

- **Quan hệ** là khái niệm kinh tế: Đức × nhóm hàng đó. Chỉ có một.
- **Spell** là một chuỗi năm sống liên tục. Ở đây có **năm** spell.
- Khoảng trống giữa các spell là các năm dưới ngưỡng: quan hệ đứt rồi quay lại.
- Spell cuối chưa chết mà **hết thời gian quan sát** → `right_censored = 1`,
  `event = 0`. Đây không phải dữ liệu thiếu, đây là thông tin hợp lệ.
- **Episode-năm** là một dòng cho mỗi năm trong mỗi spell. Năm spell trên cho 7 episode-năm.

**Bước 3 — ba file lõi hiện ra tự nhiên.**

| File | Một dòng là gì | Khóa | Quy mô |
|---|---|---|---|
| `analysis/spells.csv` | một spell | `spell_id` | 228.175 × 11 |
| `analysis/episodes.csv` | một spell trong một năm | `spell_id + year` | 747.719 × 22 |
| `analysis/panel_final.csv` | episodes sau khi ghép hết covariate | `spell_id + year` | 747.719 × **158** |

**Bước 4 — hai quy ước dễ đọc sai, phải nói chủ động.**

- `event = 1` ở năm Y nghĩa là **Y là năm cuối còn sống**; quan hệ chấm dứt ở Y+1.
  Hệ quả: một chính sách năm 2025 phải căn với khoảng rủi ro dẫn tới cái chết 2025,
  không gắn thẳng vào dòng 2025.
- `product_family` không phải mã HS6 thô. Mã HS đổi qua các phiên bản H1–H6, nên
  pipeline quy tất cả về nền H0 rồi gom các mã liên thông thành một họ ổn định.
  Mục đích: tránh biến **"HS đổi mã"** thành **"quan hệ chết rồi sinh lại"**.
  Toàn bộ có 4.621 `product_family`.

**Bước 5 — ba loại kiểm duyệt.**

- *Left-censored*: spell đã sống từ năm nền 2002, không biết bắt đầu khi nào → loại khỏi mẫu survival.
- *Right-censored*: còn sống ở cuối cửa sổ → giữ với `event = 0` (57.689 spell, 25,3%).
- *Administrative censoring*: nước ngừng nộp dữ liệu → kiểm duyệt hành chính, không ghi
  là chết. Sáu reporter được xử lý: RUS, BLR, BGD, KNA, LCA, SLB.

Câu chốt chặng:

> "Mọi con số còn lại trong bộ dữ liệu đều chỉ là **thuộc tính gắn thêm** vào một trong các thanh này."

---

### Chặng 3 (11–19′) — Bản đồ file: năm tầng và sáu khóa ghép

**Trình bày theo tầng, tuyệt đối không theo alphabet.**

```
Tầng 0  selection/        ai được vào mẫu           → 15 file, không vào panel
Tầng 1  lõi thương mại    spells.csv, episodes.csv  → dựng từ Comtrade + ngưỡng 10k
Tầng 2  module covariate  13 nhóm, ~25 file         → mỗi nhóm gắn ở một khóa
Tầng 3  master            panel_final.csv           → 158 cột = 16 khối
Tầng 4  output chẩn đoán  km / hazard / threshold   → kết quả, không phải input
Tầng 5  scripts/ + docs/  25 script, 15 tài liệu    → tái lập và truy vết
```

**Sáu khóa ghép — công cụ mạnh nhất để thầy định vị bất kỳ biến nào.**
Nói thêm một câu về ý nghĩa kinh tế lượng, vì đây là chỗ thầy sẽ đánh giá:
**khóa ghép quyết định biến đó sống sót được với fixed effects nào.**

| # | Khóa ghép | Module gắn ở đây | Bị fixed effect nào hấp thụ |
|---|---|---|---|
| 1 | `spell_id × year` | đơn vị của panel | — |
| 2 | `importer × product_family × year` | trade core, thuế lịch sử | biến động nhiều nhất, an toàn nhất |
| 3 | `importer × year` | vĩ mô, FTA, gravity, LPI/GLPI, phòng vệ thương mại, NTM AVE, ECI/COI | chết nếu dùng importer × year FE |
| 4 | `product_family` hoặc `HS4 × year` | PCI, phạm vi CBAM, miễn trừ thuế Mỹ | chết nếu dùng product FE |
| 5 | `importer × HS6 × year` | NTM6 | gần khóa 2, nhưng độ phủ theo năm yếu |
| 6 | `year` | GEPU, 16 chỉ số giá hàng hóa, thuế Mỹ 2025 | **chết hoàn toàn với year FE** |

Bổ sung một câu quan trọng: vì exporter được khóa là Việt Nam, **toàn bộ biến phía
exporter** (GDP Việt Nam, ECI Việt Nam, tỷ giá, lạm phát) chỉ thay đổi theo năm,
tức là rơi vào khóa 6 và đồng tuyến với year fixed effects. Đây là hạn chế đã biết
chứ không phải sơ suất.

**Mười ba module, mỗi module đúng một câu.** Không mô tả biến, chỉ nói: đo gì —
khóa nào — dùng làm core hay robustness.

| Module | File chính | Khóa | Vai trò | Cảnh báo phải nói |
|---|---|---|---|---|
| Thuế lịch sử | cột trong panel, nguồn TRAINS | 2 | core policy | chỉ 13 reporter khai đích danh VN; 2024–2025 mang giá trị 2023 |
| FTA | `fta_vn.csv` (3.528) | 3 | core policy | biết **có** ưu đãi, không luôn biết đúng **mức** ưu đãi |
| Thuế Mỹ 2025 | 6 file `us_*` | 6 + 4 | extension cú sốc | bốn quy ước 20% / 46% / 11,55% — phải chọn một |
| NTM HS6 | `_ntm6/` 126 mảnh + `ntm6_observed.csv` | 5 | robustness | chỉ 36,6% dòng có khảo sát đúng năm |
| NTM quy ra thuế | `ntm_ave_vn.csv` (2.668) | 3 | robustness | thực chất là lát cắt 2017 kéo qua thời gian |
| NTM cấp ngành | `ntm_country/sector/by_type` | 3 | dự phòng | khác khái niệm, không trộn với NTM HS6 |
| Vĩ mô | `macro_panel_v2.csv` (3.552) | 3 | core (GDP, GDP/người) | phần mở rộng để robustness |
| Logistics xanh | `glpi.csv` (3.552) | 3 | robustness | bốn cách xây, xếp hạng khác nhau đáng kể |
| EPI | `epi_indicators_annual.csv` (184.827) | 3 | nguyên liệu GLPI | 52 chỉ báo, không đưa thẳng vào mô hình |
| Gravity | `gravity_vn.csv` (2.940 × 22) | 3 | core (dist, contig, comlang) | CEPII dừng ở 2021 |
| Phòng vệ thương mại | `ttbd_vn*.csv` | 3 (+ sản phẩm) | robustness | quan sát yếu sau 2015 |
| Độ phức tạp & sốc | `complexity_product/country`, `shocks_annual` | 4 / 3 / 6 | core (PCI) + kiểm soát chung | sốc chung chết với year FE |
| CBAM | `cbam_products.csv` (269) + `_cn` (56) | 4, chỉ importer EU | extension | **chưa phải giá carbon**, mới là phạm vi và nghĩa vụ báo cáo |

**Tầng 0 nói gọn nhưng phải nói**, vì đây là chỗ thầy sẽ hỏi về tính đại diện:
147 importer được chọn phải thỏa **cả ba** điều kiện trong 2002–2021 — nộp dữ liệu HS
hằng năm cho Comtrade, có biểu thuế TRAINS riêng hoặc dùng biểu chung EU, và thực sự
có khai nhập khẩu từ Việt Nam. `importer_vn_all.csv` giữ đủ 193 ứng viên và **lý do
loại 46 nước** — đưa file này ra nếu thầy nghi ngờ chọn mẫu.

Lưu ý: `importers_selected.csv`, `exporters_selected.csv`, `importer_candidates.csv`
là di sản của thiết kế cũ (nhiều exporter, 53 importer). Nếu thầy mở trúng, nói ngay
là **không dùng**, đừng để thầy tự phát hiện.

**Tầng 3 — cách trình bày 158 cột mà không đọc 158 cột.** Chiếu một dải chia khối:

| Khối | Cột | Nội dung |
|---|---|---|
| Định danh + survival | 1–11 | `spell_id`, `importer`, `product_family`, `year`, `t_start`, `t_stop`, `event`, `right_censored` |
| Trade + cấu trúc danh mục | 12–22 | giá trị, đơn giá, RCA, các tỷ trọng, HHI, tăng trưởng |
| Thuế lịch sử | 23–26 | mức, loại, năm nguồn, reporter |
| Vĩ mô exporter | 27–32 | phía Việt Nam |
| Vĩ mô importer | 33–42 | GDP, dân số, CO2, năng lượng tái tạo |
| LPI | 43–50 | 7 cấu phần + năm nguồn |
| GLPI | 51–54 | bốn cách xây |
| FTA | 55–61 | hiệu lực, số hiệp định, số năm kể từ FTA |
| Phòng vệ thương mại | 62–69 | AD, CVD, safeguard, cờ quan sát |
| Gravity + thể chế | 70–90 | khoảng cách, biên giới, ngôn ngữ, WTO/EU/RTA, chi phí gia nhập |
| Thuế Mỹ 2025 | 91–97, 127–128 | bốn quy ước mức + miễn trừ theo sản phẩm |
| NTM AVE | 98–101 | quy NTM về đơn vị phần trăm |
| Sốc chung | 102–119 | GEPU + 16 chỉ số giá |
| Độ phức tạp | 120–126 | PCI, ECI, COI, diversity |
| CBAM | 129–133 | phạm vi, ngành, tỷ lệ báo cáo |
| NTM cấp ngành | 134–146 | coverage, frequency theo nhóm |
| NTM HS6 × năm | 147–158 | count survey / in-force + cờ quan sát |

Câu phải nói kèm:

> "Master panel được thiết kế để **lưu trữ đầy đủ và truy vết được nguồn**, không phải
> để đưa cả 158 biến vào một hồi quy. Mỗi mô hình chỉ rút một tập con."

**Tầng 4 — ba file output.** Nói rõ đây là **kết quả**, không phải biến giải thích:
`km_survival.csv` (69 dòng, đường Kaplan–Meier), `hazard_baseline.csv` (18 dòng,
cloglog baseline), `threshold_sensitivity.csv` (5 dòng, thử 5 ngưỡng).

---

### Chặng 4 (19–23′) — Dữ liệu phục vụ bốn khối phân tích

Chuỗi logic một dòng:

`quan hệ → thời gian tồn tại → hazard đứt gãy → xác suất sống sót → cơ hội đã điều chỉnh rủi ro → quyết định danh mục`

| Khối | Câu hỏi | Dữ liệu dùng | Trạng thái |
|---|---|---|---|
| 1. Survival | Quan hệ nào sống lâu hơn? | `spells.csv`, KM | **đã có mô tả sơ bộ** |
| 2. Hazard | Điều gì liên quan tới rủi ro đứt gãy? | panel, 5 lớp biến từ trade → market → product → institutions → robustness | **pipeline chạy được, chưa khóa specification** |
| 3. Cú sốc chính sách | Cùng một thay đổi chính sách tác động khác nhau ở đâu? | thuế, FTA/EVFTA, Brexit/UKVFTA, NTM, CBAM, thuế Mỹ 2025 | **dữ liệu sẵn, chưa chạy** |
| 4. Danh mục | Biết rủi ro rồi thì nên làm gì? | giá trị hiện tại × xác suất sống sót dự báo | **chưa định nghĩa được toán học** |

Phạm vi thực nghiệm, nói bằng bốn dòng:

- **Mẫu chính**: EU-27, 2003–2023 — 148.442 episode-năm, 45.815 spell, 35.503 event, 3.423 nhóm sản phẩm.
- **Mở rộng thể chế**: UK tách riêng trước/sau Brexit và UKVFTA. Không gọi là "EU-28".
- **Kiểm tra khái quát**: toàn bộ 147 thị trường.
- **Mở rộng cú sốc**: 2024–2025 tách riêng, vì thuế TRAINS hai năm này là carry-forward.

Kết quả mô tả được phép nói, kèm cảnh báo:

- Kaplan–Meier toàn mẫu: sống sót sau 1 năm ≈ 53,1%; 2 năm ≈ 38,9%; 5 năm ≈ 25,3%; 10 năm ≈ 18,9%.
- Nhóm có FTA có đường sống sót cao hơn — **mô tả, chưa phải nhân quả**.
- 52,7% spell chỉ dài một năm. Thử ngưỡng từ 1.000 lên 500.000 USD, tỷ lệ này chỉ giảm
  từ 55,3% xuống 41,9%: **đây là đặc tính thật của dữ liệu trade duration**, không phải nhiễu cần xóa.

---

### Chặng 5 (23–25′) — Hạn chế và sáu quyết định xin thầy chốt

Nói hạn chế **trước khi thầy hỏi**. Đây là chỗ ghi điểm, không phải chỗ mất điểm.

Năm hạn chế lớn nhất, xếp theo mức độ ảnh hưởng tới kết luận:

1. **Thuế ưu đãi chưa đo đầy đủ.** Chỉ 13 reporter khai biểu thuế đích danh Việt Nam;
   phần còn lại nằm dưới mã nhóm (ASEAN, AANZFTA, GSP). Hệ quả: `tariff_rate` có thể
   cao hơn thực tế ở khoảng 39% episode có FTA. Với mẫu EU chính, cần dựng lại
   applied/preferential tariff theo schedule chính thức và EVFTA.
2. **Thuế 2024–2025 là carry-forward từ 2023.** Chỉ lớp thuế Mỹ 2025 có biến động chính sách thật.
3. **NTM không phải chuỗi hằng năm.** File researcher bắt đầu 2010, các nước nộp theo
   lịch khảo sát rời rạc; 29% panel mang `ntm6_source_year` ở **tương lai** so với `year`
   — phải đọc là "chưa đo được", không phải "NTM thấp".
4. **CBAM chưa phải giá carbon.** Chế độ chính thức bắt đầu 01/01/2026, sau cửa sổ panel,
   nên `cbam_definitive = 0` trên toàn bộ dữ liệu.
5. **Survival không tự động là quan hệ nhân quả.** Muốn nói chính sách *gây ra* đứt gãy
   thì cần chiến lược nhận dạng, thời điểm treatment và counterfactual.

Kèm một quy tắc đọc dữ liệu: **ô trống không phải số 0**. Cột thuế Mỹ chỉ có nghĩa với
importer là Hoa Kỳ; cột CBAM chỉ có nghĩa với thành viên EU theo từng năm. Trống nghĩa là
"biện pháp không áp cho dòng này"; 0 nghĩa là "có áp và giá trị bằng 0".

**Sáu quyết định xin thầy chốt** — kết bài bằng câu hỏi, không kết bằng lời cảm ơn:

1. **Network survivability** định nghĩa bằng gì: tỷ lệ giá trị còn sống, xác suất tối thiểu
   của danh mục, hay expected loss dưới cú sốc?
2. **Hàm mục tiêu** tối ưu hóa là gì: tối đa xuất khẩu kỳ vọng, có phạt tập trung, hay đa mục tiêu?
3. **Ngưỡng hành động** maintain / expand / reduce / enter / exit đặt ở đâu, và
   candidate universe cho "enter" dựng thế nào?
4. **Specification chính**: cloglog hay Cox, fixed effects nào, clustering nào, policy ở t hay t−1?
5. **Chọn cách xây GLPI nào** làm bản chính?
6. **Xử lý spell một năm**: giữ trong mô hình chính, tách tầng, hay chỉ để robustness?

Cộng thêm hai câu kỹ thuật nếu còn thời gian: chọn quy ước nào cho thuế Mỹ 2025,
và dựng applied tariff EU/EVFTA theo cách nào.

---

## 2. Vật liệu cần chuẩn bị

**Bảy slide, không hơn.**

| # | Slide | Nội dung hình |
|---|---|---|
| 1 | Câu hỏi nghiên cứu | quan hệ Đức 19k → 1,92M → chết; bảng tương phản hai cột |
| 2 | Một quan hệ có thật | timeline 2003–2025 của Đức × `H0_620429`, 5 spell + censoring |
| 3 | Ba file lõi | spells / episodes / panel_final + quy ước `event = 1` |
| 4 | Bản đồ năm tầng | sơ đồ tầng 0 → tầng 5 |
| 5 | Sáu khóa ghép | bảng khóa + dải 158 cột chia 16 khối |
| 6 | Bốn khối phân tích | chuỗi logic + cột "đã làm / chưa làm" |
| 7 | Hạn chế + 6 quyết định | năm hạn chế, sáu câu hỏi cho thầy |

**Một tờ A4 phát tay.** Mặt trước: sơ đồ năm tầng + bảng sáu khóa ghép.
Mặt sau: bảng định vị file ở mục 3 bên dưới. Thầy sẽ cầm tờ này khi hỏi.

**Laptop mở sẵn ba lệnh**, để chứng minh dữ liệu là thật khi thầy hỏi:

```bash
head -3 analysis/spells.csv
grep "^DEU_VNM_H0_620429" analysis/spells.csv
head -1 analysis/panel_final.csv | tr ',' '\n' | wc -l
```

**Không** mở `panel_final.csv` bằng Excel — file 656 MB, sẽ treo giữa buổi.

---

## 3. Bảng định vị nhanh — mỗi file một dòng

Dùng làm mặt sau tờ phát tay.

### Tầng 0 — `selection/`, định nghĩa mẫu, không vào panel

| File | Vai trò |
|---|---|
| `importers_vn.csv` | 147 importer được chọn, tier A (102) / tier B (45) |
| `importer_vn_all.csv` | 193 ứng viên, gồm 46 nước bị loại **và lý do** |
| `vn_partner_screen.csv` | 3.569 nước-năm sàng lọc giao thương với Việt Nam |
| `exporter_selected.csv` | exporter đã khóa: Việt Nam |
| `eu_tariff_mapping.csv` | nước EU/UK theo năm → reporter thuế (thường là `EUN`) |
| `country_meta.csv` | tên, khu vực, nhóm thu nhập |
| `comtrade_da.csv` | độ sẵn có dữ liệu Comtrade |
| `ntm_availability.csv`, `ntm_types.csv` | độ phủ NTM và từ điển 16 nhóm |
| `trains_avail.csv`, `trains_countries.csv`, `trains_export_targets.csv` | độ sẵn có và mapping TRAINS |
| `importer_candidates.csv`, `importers_selected.csv`, `exporters_selected.csv` | **di sản thiết kế cũ — không dùng** |

### Tầng 1–3 — lõi, module, master

| File | Dòng | Khóa | Vai trò |
|---|---:|---|---|
| `spells.csv` | 228.175 | `spell_id` | KM, phân phối duration, censoring |
| `episodes.csv` | 747.719 | `spell_id + year` | trade + survival, trước khi ghép module |
| `panel_final.csv` | 747.719 | `spell_id + year` | **master 158 cột**, nguồn duy nhất để cắt dataset mô hình |
| `fta_vn.csv` | 3.528 | importer × năm | chế độ FTA |
| `macro_panel_v2.csv` | 3.552 | nước × năm | GDP, dân số, LPI, CO2, năng lượng tái tạo |
| `macro_panel.csv` | 2.940 | nước × năm | bản cũ, giữ để đối chiếu |
| `glpi.csv` | 3.552 | nước × năm | bốn cách xây Green LPI |
| `epi_indicators_annual.csv` | 184.827 | nước × năm × chỉ báo | 52 chỉ báo EPI, nguyên liệu cho GLPI |
| `gravity_vn.csv` | 2.940 | importer × năm | 22 biến CEPII, dừng ở 2021 |
| `complexity_product.csv` | 28.563 | HS4 × năm | PCI |
| `complexity_country.csv` | 3.404 | nước × năm | ECI, COI, diversity |
| `shocks_annual.csv` | 24 | năm | GEPU + giá hàng hóa |
| `ttbd_vn.csv` | 3.528 | importer × năm | AD / CVD / safeguard |
| `ttbd_vn_cases.csv` | 711 | vụ kiện | thời điểm khởi xướng |
| `ttbd_vn_products.csv` | 3.231 | vụ kiện × sản phẩm | mã hàng liên quan |
| `ntm_ave_vn.csv` | 2.668 | importer × năm | NTM quy ra phần trăm, gốc 2017 |
| `ntm_country.csv` / `ntm_sector.csv` / `ntm_by_type.csv` | 150 / 1.200 / 3.944 | importer × ngành | lớp NTM dự phòng |
| `_ntm6/*.csv.gz` | 126 mảnh | importer × HS6 × năm | NTM chi tiết, chỉ phục vụ merge |
| `ntm6_observed.csv` | — | importer × năm | **cờ bắt buộc kiểm** trước khi dùng NTM6 |
| `cbam_products.csv` / `cbam_products_cn.csv` | 269 / 56 | product_family | phạm vi CBAM, không phải giá carbon |
| `us_tariff_vn.csv` | 23 | năm | bốn quy ước thuế Mỹ 2025 |
| `us_tariff_2025_monthly.csv` | 12 | tháng | đường đi theo tháng + căn cứ pháp lý |
| `us_tariffs_2025.csv` | 166 | dòng thuế | bảng chương 99 |
| `us_exempt_products.csv` | 547 | product_family | tỷ lệ miễn trừ |
| `us_tariff_exemptions_2025.csv` / `_hs8.csv` | 667 / 1.087 | HS6 / HTS8 | miễn trừ đã gom và bản gốc để kiểm toán |

### Tầng 4 — output

| File | Dòng | Nội dung |
|---|---:|---|
| `km_survival.csv` | 69 | Kaplan–Meier toàn mẫu, nhóm FTA và không FTA |
| `hazard_baseline.csv` | 18 | hệ số cloglog baseline — **sơ bộ** |
| `threshold_sensitivity.csv` | 5 | kết quả ở 5 ngưỡng 1.000–500.000 USD |

### Tầng 5 — `scripts/` (25 file) và `docs/` (15 file)

| Nhóm script | File |
|---|---|
| Chọn mẫu | `select_countries.py`, `select_importers_vn.py` |
| Tải trade | `fetch_trade.py`, `pull_2022_2024.sh` |
| Tải thuế / NTM | `fetch_tariffs.py`, `fetch_ntm_availability.py`, `fetch_ntm_researcher.py`, `fetch_ntm_trains.py` |
| Tải chính sách mới | `fetch_us_tariffs_2025.py`, `fetch_cbam_scope.py` |
| Tải covariate | `fetch_macro.py`, `fetch_covariates.py`, `fetch_epi_annual.py` |
| Dựng lõi | `build_spells.py` |
| Dựng policy / NTM | `build_ntm.py`, `build_ntm6.py`, `build_ntm_ave.py`, `extract_us_exemptions.py`, `build_us_tariff_panel.py` |
| Dựng covariate | `build_covariates.py`, `build_glpi.py` |
| Ghép master | `merge_panel.py` |
| Kiểm tra | `survival_baseline.py`, `spell_threshold_sensitivity.py`, `wits_probe.py` |

Tài liệu nên chỉ cho thầy nếu thầy muốn đọc tiếp: `docs/DATA_HANDOFF.md` (nguồn, độ phủ, bẫy),
`docs/MAPPING_IDEA_DATA.md` (câu hỏi ↔ dữ liệu), `docs/THIET_KE_VIET_NAM.md` (vì sao chỉ một exporter).

---

## 4. Mười câu thầy nhiều khả năng hỏi

**1. Sao dùng số nước nhập khẩu khai, không dùng số Việt Nam khai?**
Vì outcome là hàng Việt Nam **thực sự được thị trường đích ghi nhận**. Số Việt Nam khai
(mirror) chỉ dùng đối chiếu.

**2. Ngưỡng 10.000 USD ở đâu ra?**
Là ngưỡng WITS Trade Outcomes dùng. Kiểm tra độ nhạy cho thấy nó giữ lại 99,97% giá trị thương mại.

**3. Hơn một nửa spell chỉ dài một năm — có phải nhiễu không?**
Không. Nâng ngưỡng lên 500.000 USD, tỷ lệ chỉ giảm từ 55,3% xuống 41,9%. Đây là đặc tính
đã được ghi nhận của dữ liệu trade duration. Sẽ xử lý bằng phân tầng hoặc robustness,
không xóa mặc định.

**4. Vì sao EU-27 là mẫu chính khi có 147 thị trường?**
Bối cảnh thể chế thống nhất hơn, có EVFTA làm cú sốc chính sách rõ ràng, đủ biến thiên
giữa nước và sản phẩm, và vẫn còn 148.442 episode-năm. Panel toàn cầu giữ lại để kiểm
tra tính khái quát.

**5. `product_family` khác HS6 chỗ nào, có mất thông tin không?**
Có gom nhóm, nên độ chi tiết giảm nhẹ. Đổi lại tránh được sai số nghiêm trọng hơn:
mã HS đổi phiên bản bị đọc nhầm thành quan hệ chết. 4.621 family so với khoảng 5.000+ mã HS6.

**6. Đã kết luận được FTA làm quan hệ sống lâu hơn chưa?**
Chưa. Kaplan–Meier cho thấy nhóm FTA có đường sống sót cao hơn, nhưng chưa xử lý
selection và biến gây nhiễu: hai nhóm khác nhau cả về quy mô thị trường, cơ cấu sản phẩm
và lịch sử quan hệ.

**7. Sao không đưa hết 158 biến vào mô hình?**
Vì nhiều biến ở cùng khóa ghép sẽ đồng tuyến hoặc bị fixed effects hấp thụ. Master panel
là kho lưu trữ; mô hình chỉ rút một tập con theo lớp core / robustness.

**8. Thuế năm 2024–2025 lấy ở đâu?**
TRAINS chưa công bố. Panel đang mang giá trị 2023 sang, và `tariff_source_year` ghi rõ
điều đó. Vì vậy 2024–2025 được tách thành extension riêng thay vì trộn vào mẫu chính.

**9. Đã có danh mục tối ưu chưa?**
Chưa, và đó là phần em cần thầy góp ý. Trước đó phải khóa mô hình survival, dự báo xác
suất sống sót, dựng candidate universe và định nghĩa được network survivability.

**10. Nước ngừng nộp dữ liệu có tạo ra "cái chết giả" không?**
Có nguy cơ đó. Pipeline đã kiểm duyệt hành chính sáu reporter rõ nhất. Riêng 2024–2025
độ bất định về báo cáo còn cao hơn, nên hai năm này không nằm trong cửa sổ chính.

---

## 5. Những câu không được nói

| Không nói | Nói thay bằng |
|---|---|
| "Bộ dữ liệu có 158 biến" (như một điểm mạnh) | "158 cột được tổ chức thành 16 khối theo sáu khóa ghép" |
| "Kết quả cho thấy FTA làm tăng survival" | "Thống kê mô tả cho thấy nhóm FTA có đường sống sót cao hơn" |
| "EU-28" | "EU-27, và UK tách riêng như một extension" |
| "16 nước EU" (con số sai trong `README.md`) | "đủ 27 nước EU, cộng UK là 28 mã quốc gia" |
| "CBAM là thuế carbon trong panel" | "CBAM trong panel mới là phạm vi và nghĩa vụ báo cáo" |
| Trộn 20% / 46% / 11,55% của thuế Mỹ | "bốn quy ước, nhóm sẽ chọn một và giải thích lý do" |
| "Nghiên cứu đã chứng minh…" | "Dữ liệu đã sẵn sàng để kiểm định…" |

---

## 6. Bản rút gọn 8 phút, nếu bị cắt thời gian

Giữ đúng bốn ý, bỏ hết phần còn lại:

1. **(2′)** Quan hệ Đức có thật: 19k → 1,92 triệu → chết. Kim ngạch cao không đồng nghĩa bền.
2. **(3′)** Đơn vị quan sát: quan hệ → spell → episode-năm. Chiếu timeline. Ba file lõi.
   Ngưỡng 10.000 USD. Quy ước `event = 1` là năm cuối còn sống.
3. **(2′)** 158 cột = 16 khối gắn theo 6 khóa. Mẫu chính EU-27 2003–2023: 148.442 episode-năm.
4. **(1′)** Trạng thái thật: dữ liệu xong, mô hình chưa khóa, bài toán danh mục chưa định nghĩa.
   Nêu hai câu hỏi quan trọng nhất cho thầy: định nghĩa network survivability và specification hazard.

---

## 7. Checklist trước buổi

- [ ] In tờ A4 hai mặt (sơ đồ tầng + bảng khóa / bảng định vị file).
- [ ] Chuẩn bị 7 slide, kiểm tra slide timeline hiển thị đúng năm spell.
- [ ] Mở sẵn terminal ở thư mục `wits/`, thử trước ba lệnh demo.
- [ ] Thuộc sáu con số: 147 importer · 4.621 product family · 228.175 spell ·
      747.719 episode-năm · 158 cột · 148.442 episode-năm mẫu EU.
- [ ] Thuộc bốn con số Kaplan–Meier: 53,1% · 38,9% · 25,3% · 18,9%.
- [ ] Chuẩn bị trước câu trả lời cho ba câu khó nhất: câu 3 (spell một năm),
      câu 6 (FTA có nhân quả không), câu 9 (danh mục tối ưu).
- [ ] Viết sẵn sáu quyết định lên một slide riêng để kết bài bằng câu hỏi.
