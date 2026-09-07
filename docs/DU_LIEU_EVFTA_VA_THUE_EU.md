# EVFTA staging schedule & thuế EU — đợt thu thập 29/08/2026

*Tiếp nối [DOI_CHIEU_B0_VOI_DU_LIEU.md](DOI_CHIEU_B0_VOI_DU_LIEU.md), §4. Doc
đó nêu đúng hai lỗ hổng dữ liệu chặn B6; doc này ghi lại việc đã lấp chúng như
thế nào, lấy ở đâu, kiểm chứng bằng gì, và còn sai lệch chỗ nào. Mọi con số
đếm trực tiếp trên file vừa dựng.*

---

## 1. Một màn hình

```
LỖ HỔNG §4.1 — EVFTA Annex 2-A staging schedule
  Trước:  ❌ không PDF, không bảng, không script
  Sau:    ✅ 9.394 dòng CN8 · 5.205 HS6 · 4.583 product family
          ✅ lộ trình thuế theo năm 2020–2035
          ✅ kiểm chứng độc lập với TRAINS: lệch trung bình 0,17 pp ở 2021

LỖ HỔNG §4.2 — Thuế EU áp cho VN 2022–2025
  Trước:  ⚠️ MFN dừng 2023 · ưu đãi chỉ có 2020–2021 · 2024–25 carry-forward
  Sau:    ✅ MFN 2024/2025/2026 lấy thẳng từ biểu thuế EU (không qua WITS)
          ✅ applied 2020–2035 dựng từ chính lộ trình EVFTA
          ✅ 100% episode EU27 mọi năm 2003–2025 có thuế và có pref_margin

PHÁT HIỆN THÊM (không nằm trong kế hoạch)
  🔎 Trước EVFTA, VN vào EU theo **GSP**, không phải MFN. TRAINS có biểu GSP
     của EU nhưng nộp dưới mã nhóm, nên đợt kéo cũ (chỉ hỏi partner 704)
     không thấy. Panel cũ vì vậy **khai thuế cao hơn thực tế ~2,3 pp** ở toàn
     bộ 2003–2019. Đã lấy được 2000–2014.
```

**Trả lời một dòng:** cả hai lỗ hổng đã đóng, và cái quan trọng nhất — biến
treatment `staging_cat` / `pref_margin` cho B6 — nay là **dữ liệu thật, kiểm
chứng được**, không còn là giả định.

---

## 2. Lấy từ đâu

| Nguồn | Nội dung | Kích thước | Truy cập |
|---|---|---|---|
| **EVFTA Annex 2-A** (VCCI, `wtocenter.vn`) | Annex 2-A + 5 appendix. **Appendix 2-A-1 = biểu thuế của EU**, 1.213 trang | 21 MB | công khai, không tài khoản |
| **CN regulation của EU** (EUR-Lex) | Common Customs Tariff 2024 / 2025 / 2026, mỗi bản ~1.100 trang | 30 MB | công khai |
| **TRAINS GSP nhóm** (WITS) | Biểu GSP của EU 2000–2015 dưới mã nhóm `G26/G27/P24/A34` | 16 file | công khai |

Ba script mới, đúng quy ước `fetch_*` / `build_*` của repo:

```
scripts/fetch_evfta_annex.py     tải Annex 2-A + 5 appendix
scripts/fetch_eu_cn.py           tải 3 CN regulation 2024–2026
scripts/fetch_eu_gsp.py          kéo biểu GSP của EU theo mã nhóm
scripts/build_evfta_staging.py   parse 2-A-1 → staging + lộ trình thuế
scripts/build_eu_mfn_cn.py       parse CN regulation → MFN 2024–2026
scripts/build_eu_tariff_panel.py gộp 4 nguồn → một bảng thuế duy nhất
scripts/check_evfta_vs_trains.py kiểm chứng chéo bản parse với TRAINS
```

Thứ tự chạy lại từ số không: `fetch_evfta_annex` → `fetch_eu_cn` →
`fetch_eu_gsp` → `build_evfta_staging` → `build_eu_mfn_cn` →
`build_eu_tariff_panel` → `check_evfta_vs_trains`. Hai bước parse PDF mất
khoảng 5 và 20 phút.

---

## 3. EVFTA staging schedule — cái mà B6 cần

### 3.1. Parse ra được gì

Appendix 2-A-1 là bảng 5 cột: `CN 2012 | Description | Base rate | Category |
Comment`. Base rate là thuế MFN của EU **tại 26/6/2012**, category là mã lộ
trình.

| Category | Số dòng CN8 | Nghĩa (Annex 2-A Section A) |
|---|---:|---|
| **A** | 7.862 | miễn thuế ngay từ ngày hiệu lực |
| **B3** | 630 | xoá trong 4 chặng bằng nhau → 0 từ 2023 |
| **B5** | 394 | 6 chặng → 0 từ 2025 |
| **B7** | 403 | 8 chặng → 0 từ 2027 |
| **TRQ** | 76 | hạn ngạch thuế quan, không phải lộ trình |
| **A+EP** | 28 | bỏ phần ad valorem ngay, **giữ** thuế theo giá nhập tối thiểu |
| **R75** | 1 | thang EUR/tấn cố định theo năm lịch |
| | **9.394** | |

Category A chiếm **83,7% số dòng thuế** — khớp với con số EU vẫn công bố
(“xoá ngay khoảng 84% dòng thuế”). Đó là kiểm tra thứ nhất.

### 3.2. Ba kiểm tra cho thấy bản parse đọc đúng

1. **Đếm chéo với text thô của PDF.** Regex trên text thô tìm được 9.396 dòng
   CN8; parser lấy 9.394 và **không sót mã nào** (tập mã trong text trừ tập mã
   parse được = rỗng).
2. **Số HS6 riêng biệt = 5.205.** HS2012 có **đúng 5.205 phân nhóm 6 số**. Con
   số trùng khít là dấu hiệu bảng được đọc trọn vẹn, không mất chương nào.
3. **Đối chiếu tay 12 dòng ngẫu nhiên** với text gốc của đúng trang: 12/12
   khớp cả base rate lẫn category.

### 3.3. Quy ước tính lộ trình — nói rõ để còn cãi được

Annex 2-A viết “xoá trong N chặng bằng nhau, bắt đầu từ ngày hiệu lực”. Quy
ước dùng ở đây: **N lần cắt bằng nhau, mỗi lần `base/N`, lần đầu vào
1/8/2020, các lần sau vào 1/1 hằng năm.** Do đó thuế năm `y` là

```
rate(y) = base × (N − k) / N      với k = y − 2019
```

và dòng hàng về 0 từ năm `2019 + N`: **B3 → 2023 · B5 → 2025 · B7 → 2027**.

> ⚠️ **Năm 2020 là năm duy nhất quy ước này không thể đúng tuyệt đối.** Lần cắt
> đầu rơi vào 1/8, nên 5 tháng đầu năm vẫn tính giá cũ. Cột
> `stage_1_partial_year` đánh dấu đúng những dòng đó; ai muốn trung bình theo
> năm thì lấy `7/12 × base + 5/12 × stage-1`.

### 3.4. Kiểm chứng độc lập: bản parse vs TRAINS

TRAINS tình cờ có biểu ưu đãi EU dành cho VN ở **đúng hai năm 2020 và 2021** —
và không năm nào khác. Đó là phép kiểm chứng độc lập duy nhất tồn tại, nên đáng
để tiêu. Hai bên đưa về cùng `product_family` rồi so:

| | 2020 | 2021 |
|---|---:|---:|
| Số family so được | 3.311 | 3.310 |
| **Trùng khít (<0,01 pp)** | **83,8%** | **87,6%** |
| Lệch ≤ 0,5 pp | 87,0% | 90,4% |
| Lệch ≤ 2,0 pp | 91,9% | **97,6%** |
| Lệch trung bình có dấu | +0,258 pp | **+0,093 pp** |
| Lệch tuyệt đối trung bình | 0,335 pp | **0,171 pp** |

2021 khớp tốt hơn 2020 đúng như dự đoán — 2020 là năm chỉ có 5 tháng hiệu lực.
Phần lệch còn lại tập trung ở các family gộp nhiều dòng CN8 khác category
(thuỷ sản HS0302–0307, phân bón HS3102) và ở các dòng TRQ.

Lệnh chạy lại: `python3 scripts/check_evfta_vs_trains.py`.

### 3.5. File ra

| File | Dòng | Nội dung |
|---|---:|---|
| `analysis/evfta_eu_schedule_cn8.csv` | 9.394 | bản parse thô, một dòng một mã CN8 |
| `analysis/evfta_staging_hs6.csv` | 5.205 | staging gộp lên HS6, có cờ `staging_mixed` khi các CN8 dưới cùng HS6 không cùng category |
| `analysis/evfta_tariff_path_hs6.csv` | 82.416 | (HS6 × năm) 2020–2035: `evfta_rate_pct`, `evfta_cut_cum_pp`, `evfta_cut_cum_share` |
| `analysis/evfta_staging_family.csv` | 4.583 | **cùng nội dung nhưng khoá theo `product_family` của panel** — join thẳng, không phải làm lại concordance |

Biểu thuế viết bằng CN, phần 6 số là **HS2012 (revision H4)**; panel khoá theo
family H0. Bước nối dùng **đúng union-find của `build_spells.py`**, không dựng
bảng chuyển đổi thứ hai — nếu không sẽ có hai cách map cùng một mã.

### 3.6. Nối vào panel: khớp 99,4%

| Chỉ số | Giá trị |
|---|---|
| Episode EU27 khớp được với biểu EVFTA | **175.173 / 176.277 = 99,4%** |
| Theo kim ngạch | **99,56%** của 392 tỷ USD |
| Tỷ lệ khớp từng năm 2019–2025 | 99,4 – 99,5%, không năm nào tụt |

**Phân bố treatment — đây là thứ B6 sống nhờ vào:**

| Category | Episode EU27 | % kim ngạch |
|---|---:|---:|
| A (cắt ngay) | 140.764 | 92,9% |
| B5 | 15.540 | 2,9% |
| B3 | 10.797 | 2,6% |
| B7 | 6.608 | 0,8% |
| TRQ | 1.382 | 0,2% |
| A+EP | 82 | 0,0% |

> **Đọc kỹ bảng này trước khi thiết kế B6.** Có ~33.000 episode-năm nằm trên
> lộ trình cắt dần (B3/B5/B7) — đủ để có biến thiên **giữa các sản phẩm trong
> cùng một nước, cùng một năm**, đúng thứ COVID không có. Nhưng chúng chỉ
> chiếm **6,3% kim ngạch**: hàng xuất chủ lực của VN sang EU phần lớn rơi vào
> category A. Nghĩa là identification sẽ **sạch nhưng dựa trên phần đuôi của
> danh mục**, và điều đó phải nói thẳng trong bài, không giấu.

---

## 4. Bảng thuế EU hợp nhất — `analysis/eu_tariff_panel.csv`

### 4.1. Bốn nguồn, một bảng

| Nguồn | Phủ | Vai trò |
|---|---|---|
| TRAINS MFN | 2002–2023 | MFN, 102.285 family-year |
| **CN regulation của EU** | **2024, 2025, 2026** | MFN cho những năm TRAINS trả 404 |
| **TRAINS GSP nhóm** | 2000–2014 (mang tới 2019) | thuế VN **thực sự** trả trước EVFTA |
| **Biểu staging EVFTA** | 2020–2035 | thuế ưu đãi sau hiệp định |

Quy tắc `applied` — theo đúng cách một nhà xuất khẩu hành xử, lấy mức thấp nhất
mình được hưởng:

```
năm ≤ 2019   GSP nếu có biểu, còn không thì MFN
năm ≥ 2020   min(thuế EVFTA theo lộ trình, MFN)
pref_margin_pp = mfn − applied
```

Mỗi dòng đều ghi `mfn_source`, `mfn_source_year`, `gsp_source`,
`applied_source`, `applied_partial_year` — nên **không có con số nào phải tin
suông**: nhìn cột nguồn là biết nó đo thật hay mang từ năm khác sang.

Kết quả: **166.363 dòng (product_family × năm), 4.902 family, 2002–2035**.

### 4.2. Độ phủ trên panel EU27 — 100% mọi năm

| Năm | Episode | Có thuế | MFN bình quân | Applied bình quân | % có ưu đãi | Margin bq theo kim ngạch |
|---|---:|---:|---:|---:|---:|---:|
| 2012 | 6.480 | **100%** | 5,52 | 3,10 | 81,6% | 0,65 |
| 2019 | 9.734 | **100%** | 4,99 | 2,74 | 78,0% | 0,70 |
| 2020 | 10.029 | **100%** | 4,86 | **1,45** | 75,9% | 0,93 |
| 2021 | 11.311 | **100%** | 4,82 | **1,10** | 76,3% | 1,10 |
| 2022 | 12.124 | **100%** | 4,81 | **0,76** | 76,2% | 1,44 |
| 2023 | 12.651 | **100%** | 4,85 | **0,47** | 75,8% | 1,55 |
| **2024** | 13.322 | **100%** | 4,96 | **0,36** | 76,6% | 1,60 |
| **2025** | 14.513 | **100%** | 4,94 | **0,17** | 77,0% | 1,73 |

So với trạng thái trước đợt này: 2024 và 2025 có **31% episode mang thuế và 0%
đo đúng năm**. Nay là 100%, và mức applied giảm đều theo đúng lộ trình cam kết
— tức là chuỗi có **biến thiên chính sách thật**, không phải một con số bị kéo
ngang.

**Độ phân tán của `pref_margin` cũng đổi hẳn**, và đây mới là thứ nuôi B6:

| Giai đoạn | SD của margin trên episode | p90 |
|---|---:|---:|
| 2003–2019 (GSP) | 1,8 – 1,9 pp | ~4,4 pp |
| 2020–2025 (EVFTA) | **3,8 – 4,5 pp** | **8,9 – 12,0 pp** |

### 4.3. Kiểm chứng MFN parse từ CN regulation

Biểu CN 2024 so với TRAINS MFN 2023 (thuế chung của EU gần như không đổi giữa
hai năm liền kề, nên đây là phép thử hợp lệ):

| | |
|---|---|
| Family so được | 4.076 |
| **Trùng khít (<0,01 pp)** | **94,1%** |
| Lệch ≤ 0,5 pp | 95,2% |
| Lệch tuyệt đối trung bình | **0,243 pp** |

---

## 5. Phát hiện ngoài kế hoạch: trước EVFTA, VN vào EU theo GSP

Đây là đính chính một điều panel hiện tại đang làm sai, và nó ảnh hưởng toàn bộ
17 năm đầu của cửa sổ.

**Việt Nam là nước hưởng GSP tiêu chuẩn của EU cho tới khi EVFTA có hiệu lực.**
TRAINS **có** biểu GSP của EU — nhưng nộp dưới **mã nhóm** (`G26`, `G27`,
`P24`, `A34`), không nộp dưới mã 704 của Việt Nam. `fetch_tariffs.py` chỉ hỏi
partner 704, nên chưa bao giờ thấy chúng, và mọi episode EU trước 2020 trong
panel đang mang **thuế MFN**.

Lấy được 16 file, 2000–2015, mỗi file 3.500–4.600 dòng HS6.

**Sai lệch đo được, trên chính episode EU27 của panel:**

| | MFN bình quân | GSP bình quân | Chênh |
|---|---:|---:|---:|
| 2012 | 5,52 | 3,10 | **−2,42 pp** |
| 2019 | 4,99 | 2,74 | **−2,25 pp** |

Tức là **panel cũ khai thuế cao hơn thực tế khoảng 2,3 điểm phần trăm ở
78–83% số episode EU trước 2020** — và sai lệch đó **không ngẫu nhiên**: nó lớn
nhất đúng ở những dòng hàng GSP ưu đãi mạnh, tức là dệt may, da giày, thuỷ sản.
Với một mô hình hazard có biến thuế, đây không phải nhiễu, mà là sai số hệ
thống tương quan với ngành.

> ⚠️ **Ba giới hạn của lớp GSP này, phải nêu trong Limitations:**
>
> 1. **2015–2019 không có biểu nào** — EU không nộp mã nhóm GSP cho 5 năm này.
>    Bảng đang **mang biểu 2014 sang**, có cờ `gsp_source = "carried"`. Cơ sở:
>    Regulation 978/2012 giữ nguyên hiệu lực suốt giai đoạn đó.
> 2. **Biểu nhóm là *chế độ*, không phải *quyền được hưởng của Việt Nam*.** GSP
>    có cơ chế “graduation” loại từng nhóm hàng của từng nước; TRAINS không
>    công bố ai bị loại lúc nào. Với VN, giày dép (Section XII) từng bị
>    graduation — nên với riêng nhóm đó, GSP trong bảng có thể **thấp hơn** mức
>    thực tế.
> 3. **Không phải lô hàng nào cũng dùng ưu đãi.** Đây là thuế *được hưởng*, không
>    phải thuế *đã trả*; tỷ lệ tận dụng ưu đãi không có trong nguồn công khai
>    nào ở mức HS6.

---

## 6. Còn chưa hoàn hảo ở chỗ nào

| Hạng mục | Mức độ | Tại sao | Xử lý |
|---|---|---|---|
| MFN 2024–2026 phủ **83%** family, phần còn lại mang từ 2023 | nhỏ | parser bỏ 291 dòng có mã nhưng không có mức thuế trong ô, và 172 ô chỉ chứa số chú thích (thuế theo mùa nằm trong footnote) | có cờ `mfn_source`; chênh giữa CN 2024 và TRAINS 2023 chỉ 0,24 pp nên phần carry-forward gần như vô hại |
| Thuế **theo lượng** (EUR/100 kg, EUR/t) | trung bình | bảng chỉ giữ phần **ad valorem**; 860 dòng CN8 có cấu phần specific | cờ `any_specific_duty`; muốn quy đổi AVE thì cần đơn giá — panel đã có `unit_value_usd_per_kg` phủ 96,5% |
| **TRQ** (76 dòng CN8, 1.382 episode) | nhỏ | hạn ngạch không phải một mức thuế | loại khỏi lộ trình, giữ nguyên nhãn `TRQ` để lọc |
| `staging_mixed` — HS6 gộp nhiều CN8 khác category | 197/5.205 HS6 | HS6 thô hơn CN8 | có sẵn cả `staging_cat` (modal) lẫn `staging_cat_slowest` (bảo thủ); nên chạy robustness bằng cả hai |
| GSP 2015–2019 | trung bình | nguồn không có | mang từ 2014, có cờ |
| Tỷ lệ tận dụng ưu đãi | không có | không nguồn công khai nào ở HS6 | chỉ nêu trong Limitations |
| Biểu thuế của **Việt Nam** (Appendix 2-A-2) | chưa parse | Stage 1 chỉ cần thuế VN **phải chịu**, tức phía EU | PDF 675 trang đã nằm sẵn trên đĩa nếu sau này cần |

---

## 7. Đối chiếu lại với B0 sau đợt này

Cập nhật trực tiếp bảng §3 của [DOI_CHIEU_B0_VOI_DU_LIEU.md](DOI_CHIEU_B0_VOI_DU_LIEU.md):

| Yêu cầu B0 | Trước 29/08 | Sau 29/08 |
|---|---|---|
| B1.4 EVFTA staging schedule | ❌ không có gì | ✅ **9.394 dòng, đã kiểm chứng** |
| B3 `staging_cat` | ❌ | ✅ `evfta_staging_family.csv` |
| B3 `evfta_cut_cum` | ❌ | ✅ `evfta_cut_cum_pp` + `evfta_cut_cum_share` |
| B3 `pref_margin` | ❌ | ✅ `pref_margin_pp`, 100% episode EU27 |
| B3 `tariff_applied` 2024–2025 | ❌ 0% đo đúng năm | ✅ 100% |
| B4 hình KM theo staging category | ❌ bị chặn | ✅ **chạy được ngay** |
| B6 `PrefMargin × Post` | ❌ bị chặn | ✅ **chạy được ngay**, ±5 năm quanh 2020 đều có dữ liệu |
| B9 cột `staging_cat` của bảng bàn giao | ❌ | ✅ |

**Không còn hạng mục dữ liệu nào chặn Stage 1.** Những gì còn lại ở
[DOI_CHIEU_B0_VOI_DU_LIEU.md](DOI_CHIEU_B0_VOI_DU_LIEU.md) §5 và §7 đều là
**quyết định** hoặc **việc mô hình hoá**, không phải việc tải dữ liệu:

- dựng lại spell với `GAP_TOLERANCE = 1` và giữ spell left-truncated;
- bổ sung 5 biến còn thiếu của B3 và lag toàn bộ về `t−1`;
- chốt BACI/Comtrade, HS2012/product family, và cách xử lý spell một năm;
- **và một việc mới sinh ra từ đợt này:** cho `merge_panel.py` đọc
  `eu_tariff_panel.csv` cho nhóm importer EU27, thay vì lấy `tariff_rate` cũ.
  Chưa làm — vì làm nó là bước B, mà đợt này chỉ nhận nhiệm vụ lấy dữ liệu.

---

## 8. Ghi chú vận hành

- **Toàn bộ đợt này không cần một tài khoản nào**, không key, không đăng nhập.
  Ghi chú cũ của dự án từng cho rằng lấy được thuế 2024–2025 phải qua nguồn trả
  tiền; giống hệt bài học NTM hồi 25/08, **hoá ra chỉ cần hỏi đúng nơi**: EU tự
  công bố biểu thuế của mình mỗi tháng 10 trên EUR-Lex.
- **WITS vẫn 404 cho 2024 và 2025** — kiểm lại 29/08/2026 với EU (918), Mỹ
  (840) và Trung Quốc (156), cả sáu lượt hỏi đều 404. Đây là thuộc tính của
  TRAINS, không phải lỗi mạng.
- Parse PDF dùng `pdfplumber` theo **toạ độ x của chữ**, không dùng regex trên
  text. Lý do: hai lần đầu làm bằng regex đều mất dòng — bảng EVFTA mất **một
  dòng thuế mỗi trang** (1.086 mã) vì dòng dữ liệu đầu nằm sát header, và bảng
  CN mất **1 dòng trên 8** vì mô tả dài đẩy mức thuế xuống dòng kế. Cả hai lỗi
  chỉ lộ ra khi đếm chéo với text thô — nên bước đếm chéo đó là bắt buộc, không
  phải tuỳ chọn.
- File thô nằm ở `data_raw/evfta/` (21 MB) và `data_raw/eu_cn/` (30 MB); cả hai
  thư mục đã nằm trong `.gitignore` như mọi dữ liệu thô khác, tái tạo được bằng
  hai script `fetch_*`.
