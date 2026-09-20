# Feature nào được *tính*, tính bằng công thức gì, và có ý nghĩa gì

*Viết 04/09/2026. Tài liệu này trả lời đúng một câu hỏi: trong 205 cột của
`data/final/stage1_panel.parquet`, cột nào là **số liệu chép thẳng từ nguồn**
và cột nào là **feature do code trong `scripts/` tính ra** — với, cho từng
feature tính ra: công thức đúng như code chạy, grain nó sống, ý nghĩa kinh tế,
và cái bẫy đi kèm.*

Khác với hai tài liệu bên cạnh:

- [TU_DIEN_DU_LIEU_FINAL_DF.md](TU_DIEN_DU_LIEU_FINAL_DF.md) — *cột này là gì, %null bao nhiêu*;
- [TRINH_BAY_NHOM_FEATURE_STAGE1_PANEL.md](TRINH_BAY_NHOM_FEATURE_STAGE1_PANEL.md) — *cột này dùng ở model nào*;
- **tài liệu này** — *cột này ra đời như thế nào từ dữ liệu thô*.

Mọi công thức dưới đây đọc trực tiếp từ code, không phải từ mô tả thiết kế.
File nguồn được ghi kèm mỗi khối.

---

## 0. Tóm tắt: 134 tính ra / 71 chép thẳng

| Loại | Số cột | Nghĩa |
|---|---:|---|
| **Feature tính ra (derived)** | ~134 | Có một phép biến đổi thực sự: tỷ số, tổng hợp, đếm, log, lag, quy tắc chọn, hoặc thành phần chính |
| Chép thẳng (pass-through) | ~71 | Chỉ join + đổi tên: WDI macro, 6 chỉ số con LPI, 20 biến gravity CEPII, 16 chỉ số giá Pink Sheet, PCI/ECI/COI/diversity, `ntm_coverage_ratio`/`ntm_frequency_ratio` |

Ranh giới ở vài chỗ là quy ước: `import_value_usd` được **cộng dồn** từ nhiều
dòng HS6 lên `product_family` nên tài liệu này xếp vào "tính ra", dù về bản
chất nó vẫn là kim ngạch gốc.

### Thứ tự pipeline (ai tính cái gì)

```
fetch_*.py            tải raw  ->  data/raw/
   |
build_spells.py       Bước 1: HS -> product_family; ngưỡng + gap rule -> spell/episode
                      Bước 2: derived() -> RCA, share, HHI, growth, market share
   |                  => data/interim/episodes.csv, spells.csv
   |
build_covariates.py   FTA (DESTA), TTBD, gravity, shocks, macro, complexity, US 2025
build_glpi.py         4 biến thể Green LPI
build_ntm.py          NTM cấp ngành (WITS public)
build_ntm6.py         NTM cấp HS6 x năm (TRAINS researcher)
build_ntm_ave.py      NTM ad-valorem equivalent (UNCTAD-GTAP 11)
build_evfta_staging.py + build_eu_mfn_cn.py + build_eu_tariff_panel.py
                      => eu_tariff_panel.csv (thuế EU hợp nhất 2002-2035)
build_us_tariff_panel.py + extract_us_exemptions.py
   |                  => data/interim/*.csv
   |
merge_panel.py        gắn tất cả vào episode; tính thuế generic, EVFTA cut, CBAM
   |                  => data/interim/panel_final.csv (171 cột)
   |
build_stage1_df.py    volatility, cấu trúc danh mục, log, và TOÀN BỘ lag t-1
                      => data/final/stage1_panel.parquet (205 cột)
```

---

## 1. Xương sống: product family, spell, và nhãn sinh tồn

**File:** `scripts/build_spells.py`
**Raw:** `data/raw/trade/` (Comtrade, importer khai), `data/raw/concordance/H1_to_H0 … H6_to_H0`
**Hằng số:** `YEAR_MIN, YEAR_MAX = 2002, 2025`, `THRESHOLD_USD = 10_000`, `GAP_TOLERANCE = 1`, `EXPORTER = "VNM"`

### 1.1. `product_family` — khoá sản phẩm bền qua 20 năm

Mỗi nước báo cáo theo revision HS của riêng nó (H1…H6 đều xuất hiện trong cửa
sổ, đôi khi cùng một năm). Một mã bị đánh số lại giữa hai revision trông y hệt
"một quan hệ chết + một quan hệ mới sinh" — đúng thứ mô hình survival sẽ hiểu
sai.

```
Dựng đồ thị: mỗi (revision, mã HS6) là một node.
Mỗi dòng trong bảng concordance WITS Hx_to_H0 nối hai node.
product_family = thành phần liên thông (connected component), đặt tên theo
                 đại diện thuộc H0:  "H0_610910"
Cấu trúc: union-find (disjoint set) — build_families() / family_of()
```

**Ý nghĩa:** đơn vị "sản phẩm" duy nhất mà duration có nghĩa. ~4.900 family.
**Bẫy:** một family có thể gộp nhiều HS6 → không gọi nó là "HS2012 thuần".

### 1.2. `import_value_usd`, `net_weight_kg`, `unit_value_usd_per_kg`

```
import_value_usd(c,p,t)  = Σ  value  trên mọi dòng HS6 thuộc family p
                           (chỉ dòng exporter == VNM, importer == c, năm t)
net_weight_kg(c,p,t)     = Σ  net_weight  cùng cách (chỉ cộng khi kg > 0)
unit_value_usd_per_kg    = import_value_usd / net_weight_kg      (rỗng nếu kg = 0)
```

**Ý nghĩa:** đơn giá tách "quan hệ chết vì mất khách" khỏi "chết vì giá sụp".
**Bẫy:** đơn vị đo không đồng nhất tuyệt đối giữa các dòng HS6 gộp lại → đơn
giá chỉ nên dùng ở nhánh robustness.

### 1.3. Spell: ngưỡng tồn tại + gap rule

```
alive_years = { t : value(c,p,t) >= 10.000 USD }
Cắt alive_years thành các run liên tiếp:
    t thuộc cùng run với t_prev  <=>  t - t_prev <= 1 + GAP_TOLERANCE  (= 2)
Mỗi run = một spell:
    spell_start_year = min(run),  spell_end_year = max(run)
    spell_id         = "{importer}_{exporter}_{family}_{start}"
    span             = mọi năm lịch từ start đến end (kể cả năm tụt ngưỡng)
```

**Ý nghĩa:** một năm tụt dưới 10k rồi quay lại **không** phải một cái chết cộng
một lần tái sinh (Besedeš–Prusa). Đo được trên EU27: gap 0 → 21,3% chết/năm,
gap 1 → 15,1%, gap 2 → 12,1%.

### 1.4. Nhãn sinh tồn — 6 cột, mỗi cột một quy tắc

| Cột | Công thức | Ý nghĩa |
|---|---|---|
| `gap_filled` | `int(year not in run)` | 1 = năm đệm dưới ngưỡng, giữ lại chỉ để nối spell. **Lọc `== 0` trước khi đếm episode đang sống** |
| `t_start`, `t_stop` | `k = year - start + 1`; `t_start = k-1`, `t_stop = k` | Cặp counting-process cho Cox. Đọc theo **lịch**, không theo số dòng — nên năm đệm không làm lệch đồng hồ |
| `right_censored` | `int(end >= last_year[importer])` | `last_year` = năm cuối nước đó *thực sự có filing* (`observation_windows()`), không phải 2025 cứng. Nước ngừng báo cáo → censor hành chính, không phải chết |
| `left_trunc` | `int(start == 2002)` | Spell đã chạy từ năm đầu dữ liệu → tuổi thật không quan sát được |
| `event` | `int(year == end and not right_censored)` | **Outcome chính.** Chỉ 1 ở đúng năm cuối của một spell chết được quan sát |
| `duration` (trong `spells.csv`) | `end - start + 1` | Tuổi spell |

**Bẫy lớn nhất:** `right_censored = 1` được lặp trên **mọi** dòng của spell bị
censor, không chỉ dòng cuối. Với Kaplan–Meier phải co về một dòng/`spell_id`.

---

## 2. Chỉ số thương mại tính từ hai luồng Comtrade

**File:** `scripts/build_spells.py::derived()`
**Raw:** `data/raw/trade/` (VN → nước c) và `data/raw/trade_world/` (thế giới → nước c)

Ba tổng trung gian được tích luỹ trước:

```
vn_prod[p,t]  = Σ_c  value(c,p,t)        VN xuất sản phẩm p, toàn cầu, năm t
vn_tot[t]     = Σ_c,p value(c,p,t)       tổng xuất khẩu VN trong mẫu, năm t
vn_part[c,t]  = Σ_p  value(c,p,t)        VN xuất sang nước c, năm t
wld_prod[p,t] = nhập khẩu thế giới của p     (từ trade_world)
wld_tot[t]    = tổng nhập khẩu thế giới, năm t
wld_cell[c,p,t] = nước c nhập p từ TOÀN THẾ GIỚI  (chỉ giữ ô mà VN cũng bán)
```

> **Quy tắc all-or-nothing:** nếu `data/raw/trade_world/` thiếu bất kỳ
> importer-year nào so với phía VN, `load_world()` trả `None` và **không dùng
> gì cả** — RCA rơi về mẫu số nội mẫu, `vn_market_share_pct` để trống. Lý do:
> một mẫu số cộng từ "những nước tải xong trước" khiến chỉ số mang nghĩa khác
> nhau ở mỗi nước.

| Cột | Grain | Công thức | Ý nghĩa | Bẫy |
|---|---|---|---|---|
| `rca` | `(p, t)` | `(vn_prod[p,t] / vn_tot[t]) / (wld_prod[p,t] / wld_tot[t])` | **Balassa RCA.** >1 = VN chuyên môn hoá vào sản phẩm này hơn mức thế giới. Đây là vị thế toàn cầu của VN, **không phụ thuộc nước nào mua** | Trông như cấp quan hệ vì nằm trên mọi dòng, nhưng grain thật là `(p,t)` → lag phải theo `(product_family, year)` |
| `product_share_pct` | `(p, t)` | `100 × vn_prod[p,t] / vn_tot[t]` | Tỷ trọng sản phẩm p trong rổ xuất khẩu VN | Bị year FE hấp thụ một phần |
| `partner_share_pct` | `(c, t)` | `100 × vn_part[c,t] / vn_tot[t]` | Tỷ trọng thị trường c trong rổ xuất khẩu VN | Cấp nước, không cấp quan hệ |
| `vn_market_share_pct` | `(c, p, t)` | `100 × min(value(c,p,t) / wld_cell[c,p,t], 1)` | **Thị phần VN trong đúng thị trường–sản phẩm đó.** Thước đo trực tiếp nhất về mức độ "bám" của quan hệ | `min(...,1)` là chốt chặn khi hai luồng Comtrade lệch nhau; chỉ tồn tại khi có world folder đầy đủ |
| `total_import_cp_usd` | `(c, p, t)` | `wld_cell[c,p,t]` | Tổng cầu của nước c cho sản phẩm p — proxy tách "thị trường co lại" khỏi "VN thua kém" | Bản lag của nó **hiện đang sai grain**, xem §9 |
| `hhi_market` | `t` | `Σ_c (vn_part[c,t] / vn_tot[t])²` | Herfindahl: xuất khẩu VN tập trung vào ít thị trường đến mức nào | Chỉ đổi theo năm → **year FE hấp thụ hoàn toàn** |
| `hhi_product` | `t` | `Σ_p (vn_prod[p,t] / vn_tot[t])²` | Herfindahl theo sản phẩm | như trên |
| `country_growth_pct` | `(p, t)` | `100 × (vn_prod[p,t] − vn_prod[p,t−1]) / vn_prod[p,t−1]`, **bỏ nếu base < 10.000 USD** | Xuất khẩu VN của sản phẩm p tăng/giảm bao nhanh | Sàn base là bắt buộc: trước khi có nó, 1,6% giá trị vượt 1.000% và max = 1,4×10⁸ — đó là mẫu số gần 0, không phải sản phẩm bùng nổ |
| `world_growth_pct` | `(p, t)` | Y hệt, trên `wld_prod` | Cầu thế giới cho sản phẩm p tăng/giảm bao nhanh | như trên |

**Chi tiết ghi số:** hàm `_rnd()` ghi ô trống `""` thay vì text `"nan"` khi
không tính được. Sáu cột trên từng bị lỗi này (đọc lên thành kiểu chuỗi);
`build_stage1_df.py` bọc lại bằng `null_values=["", "nan"]` ở cả hai lượt đọc,
và file parquet bàn giao đã được xác minh là `Float64` sạch.

---

## 3. Thuế quan — hai khối, hai quy tắc khác nhau

### 3.1. Thuế generic cho 147 nước

**File:** `scripts/merge_panel.py::attach_tariff()` · **Raw:** TRAINS MFN + PREF
**Hằng số:** `MAX_CARRY_FORWARD = 3`

```
reporter = "EUN" nếu importer là thành viên EU năm đó, ngược lại = importer
Với back = 0,1,2,3:
    y = year - back
    p = pref[reporter, y, VNM, family]      m = mfn[reporter, y, family]
    nếu có ít nhất một cái:
        tariff_rate = p nếu (p tồn tại và (m rỗng hoặc p <= m)) ngược lại m
        tariff_type = "PREF" / "MFN"
        tariff_source_year = y
        dừng
```

| Cột | Ý nghĩa |
|---|---|
| `tariff_rate` | Mức thuế **thấp nhất VN được hưởng** — nguyên tắc của nhà xuất khẩu: lấy biểu rẻ nhất mình đủ điều kiện |
| `tariff_type` | Biểu nào cho ra con số đó |
| `tariff_source_year` | Năm biểu thuế **thật sự** đo được. `tariff_source_year != year` ⇒ giá trị được carry-forward — đây chính là cách tạo cột `tariff_imputed` mà framework yêu cầu |
| `tariff_reporter` | Nước/khối có biểu được đọc |

**Bẫy:** với EU27 khối này mang sai số hệ thống ~2,3pp trước 2020 (không thấy
biểu GSP) và không có dữ liệu 2024–2025 (TRAINS trả 404). Dùng khối 3.2 thay thế.

### 3.2. Thuế EU hợp nhất + lộ trình EVFTA — biến treatment của B6

**File:** `scripts/build_evfta_staging.py` → `scripts/build_eu_tariff_panel.py` → `merge_panel.py::load_evfta()`
**Raw:** EVFTA Annex 2-A (PDF), TRAINS MFN EUN 2002–2023, EU CN regulation (EUR-Lex) 2024–2026, TRAINS GSP group 2002–2014
**Hằng số:** `EIF_YEAR = 2020`, `GSP_LAST_FILED = 2014`, `STAGES = {A:1, A+EP:1, B3:4, B5:6, B7:8, B10:11}`

**Bước 1 — từ CN8 lên product family** (`build_evfta_staging.py`):

```
base rate: tách phần ad-valorem khỏi phần specific
    "11,5"                    -> 11.5
    "10,2 + 93,1 EUR/100 kg"  -> 10.2   (+ cờ any_specific_duty)
    "20,9 EUR/hl"             -> 0.0    (thuần specific -> không nằm trên lộ trình %)
Gộp CN8 -> HS6 (H4) -> product_family (H0), rồi trong mỗi family:
    staging_cat         = category XUẤT HIỆN NHIỀU NHẤT (modal)
    staging_cat_share   = tỷ lệ HS6 mang category modal đó
    staging_cat_slowest = category có STAGES lớn nhất trong family
    staging_mixed       = int(family chứa >1 category)
    base_ad_valorem_pct = trung bình cộng base rate của các HS6 trong family
```

**Bước 2 — lộ trình cắt thuế tuyến tính** (`staged_rate()`):

```
n = STAGES[category]                    # số chặng
k = year - 2019                         # k = 1 tại năm hiệu lực 2020
nếu k >= n:  evfta_pct = 0
ngược lại:   evfta_pct = base × (n − k) / n
```

Ví dụ B5 (n=6), base 12%: 2020 → 10,0 · 2021 → 8,0 · 2022 → 6,0 · 2023 → 4,0 ·
2024 → 2,0 · 2025 → 0. Category A (n=1) về 0 ngay năm 2020.

**Bước 3 — mức thuế thực sự phải trả** (`build_eu_tariff_panel.py`):

```
MFN:  TRAINS 2002-2023  ->  CN regulation 2024+  ->  carry-forward năm gần nhất
      (mfn_source ghi rõ "trains" / "eu_cn_regulation" / "carried")
      Giá trị family = TRUNG BÌNH CỘNG rate_simple_avg của các HS6 trong family
GSP:  chỉ year <= 2019; 2015-2019 carry biểu 2014 (Reg. 978/2012 không đổi)

year >= 2020 và có lộ trình EVFTA:  applied = min(evfta_pct, mfn)
year <= 2019 và có GSP:             applied = min(gsp,  mfn)
còn lại:                            applied = mfn
applied_source ghi "evfta" / "gsp" / "mfn" — và đổi thành "mfn" nếu MFN rẻ hơn

pref_margin_pp = mfn − applied
years_since_evfta = year − 2020
applied_partial_year = int(year == 2020 và nguồn là evfta)   # EVFTA hiệu lực 01/8/2020
```

**Bước 4 — cường độ cắt tích luỹ** (`merge_panel.py::load_evfta()`):

```
nếu base > 0 và có evfta_pct:
    evfta_cut_cum_pp    = base − evfta_pct              # điểm phần trăm đã xoá
    evfta_cut_cum_share = (base − evfta_pct) / base     # tỷ lệ 0..1 đã xoá
ngược lại: cả hai = 0
```

| Cột | Ý nghĩa kinh tế | Bẫy |
|---|---|---|
| `tariff_mfn_pct` | Trần thuế — mức không có ưu đãi nào | Trung bình đơn giản trong family, không trọng số kim ngạch |
| `tariff_applied_pct` | Mức VN **thực sự** trả: GSP trước 2020, min(EVFTA, MFN) sau | |
| `pref_margin_pp` | **`PrefMargin` của B6** — lợi thế thuế VN có so với đối thủ trả MFN | Biến này, không phải dummy post-2020, là nguồn variation |
| `staging_cat` | Lộ trình cắt: A cắt ngay, B3/B5/B7 cắt dần | `TRQ`, `A+EP` không phải lộ trình ad-valorem — tách riêng hoặc loại |
| `staging_mixed` / `staging_cat_slowest` | Cờ + phương án robustness khi family gộp nhiều category | ~197/5.205 HS6 rơi vào trường hợp này |
| `evfta_cut_cum_pp` / `_share` | Cường độ cắt tích luỹ, dùng cho counterfactual | Chọn **một** thước đo mỗi specification |
| `years_since_evfta_policy` | `year − 2020` | Không có hệ số riêng khi đã dùng đủ year FE — chỉ để dựng event-time dummies |

**Broadcast:** bảng ra ở grain `(product_family, year)` rồi gán cho cả 27 nước
EU, vì biểu thuế chung và cam kết EVFTA là EU-wide. Đây là lựa chọn *đúng*,
không phải vá dữ liệu thiếu. Ngoài EU27, năm cột này để trống — **không phải 0**.

---

## 4. Rào cản phi thuế — ba khối, ba đơn vị đo khác nhau

### 4.1. NTM cấp ngành (`build_ntm.py`) — WITS 3 file công khai

**Raw:** `NTM-Indicators-Measure-Sector.csv`, `NTM-Prevalence-Sector.csv`, `ntm_country.csv`

Chỉ đọc dòng có `NTMCode` **một chữ cái** (chương MAST tổng hợp); dòng 4 chữ là
biện pháp con. Chương P (xuất khẩu của chính nước đó) bị loại khỏi mọi tổng hợp
nhập khẩu.

| Cột | Công thức | Ý nghĩa |
|---|---|---|
| `ntm_sps_coverage` | coverage của chương **A**, **0.0 nếu chương vắng mặt** ở một nước-ngành *có* trong khảo sát | Tỷ lệ kim ngạch bị biện pháp SPS phủ |
| `ntm_tbt_coverage` | như trên, chương **B** | Rào cản kỹ thuật |
| `ntm_quantity_coverage` | như trên, chương **E** | Kiểm soát số lượng |
| `ntm_technical_coverage` | `max(coverage)` trên các chương A, B, C | **Cận dưới** của hợp các chương kỹ thuật |
| `ntm_nontechnical_coverage` | `max(coverage)` trên D–O | Cận dưới của nhóm bị coi là bảo hộ |
| `ntm_n_types` | `#{chương không phải P có coverage > 0}` | Số loại rào cản cùng tồn tại — thước đo cường độ |
| `ntm_sector_freq_any` | `100 − share("No NTMs")` | % dòng sản phẩm chịu **ít nhất một** biện pháp |
| `ntm_sector_share_3plus` | `share("3+ types")` | % dòng chịu từ 3 loại trở lên |

**Hai quyết định phương pháp phải nói rõ:**
1. Coverage của các chương **chồng lấn** (một dòng có thể vừa SPS vừa TBT) nên
   **không được cộng** — vì thế dùng `max` làm cận dưới, và lấy tỷ lệ "ít nhất
   một" từ file prevalence (bốn nhóm cộng lại đúng 100%).
2. Chương *vắng mặt* ở một nước có trong khảo sát = **0**, khác hẳn nước không
   có trong khảo sát = **trống**. Đây là chỗ duy nhất giải quyết mập mờ
   "missing hay none?" của Carrère (2011).

**Bẫy:** một snapshot/nước, không có chiều năm (`ntm_survey_year` ghi năm khảo
sát 2012–2017); 20% episode không có gì — Trung Quốc và Hàn Quốc nằm trong số đó.

### 4.2. NTM cấp HS6 × năm (`build_ntm6.py`) — TRAINS researcher file **← ưu tiên dùng**

**Raw:** `ntm_researcher_filtered.csv.gz` (~22 triệu dòng), `H4_to_H0`
Lọc: chương A–O (bỏ P), partner ∈ {`WLD`, `VNM`}, reporter = importer (EU đọc `EUN`).

Hai họ biến, **không được lẫn**:

```
# Họ 1 — "survey": đếm những gì thu thập được trong đợt khảo sát gần nhất <= t
src = max{ y thuộc năm khảo sát của reporter : y <= year }
ntm6_all_survey       = Σ cột `ntm_all`   (mọi chương A-O)
ntm6_nonh_survey      = Σ cột `ntm_nonH`  — biện pháp KHÔNG hài hoà hoá theo
                        chuẩn quốc tế, phần thường bị coi là mang tính bảo hộ hơn
ntm6_bilateral_survey = Σ `ntm_all` chỉ trên dòng partner == VNM
ntm6_sps_survey / _tbt_ / _quantity_ / _price_ = Σ `ntm_all` theo chương A / B / E / F
ntm6_source_year      = src

# Họ 2 — "in force": đếm biện pháp mà cửa sổ [MinStartYear, MaxEndYear] phủ năm t
live = { (family, code, start, end) : start <= year <= end }   # đã khử trùng lặp chéo năm
ntm6_all_inforce = |live|
ntm6_sps_inforce = |{t thuộc live : chương A}|
ntm6_tbt_inforce = |{t thuộc live : chương B}|

ntm6_observed = int(year thuộc danh sách năm reporter có filing)
```

**Ý nghĩa:** `_survey` là cách đọc thận trọng (giống `importer_lpi_source_year`);
`_inforce` là cách duy nhất biến động **giữa** các đợt khảo sát.
**Bẫy quyết định:** file researcher bắt đầu từ 2010, và một biện pháp chỉ được
thấy nếu có đợt khảo sát nào bắt được nó → số đếm trước đợt khảo sát đầu tiên
của một reporter là **0 do cấu trúc**, không phải "ít rào cản". Luôn kèm
`ntm6_observed` trong mọi bảng dùng khối này. Độ phủ 95,2%.

### 4.3. NTM quy ra điểm thuế (`build_ntm_ave.py`) — UNCTAD–GTAP 11

**Raw:** `UNCTADGTAP11_AVEborder.csv` · Lọc `regexporter == VNM`.

```
ntm_ave_border_pct        = Σ(AVEgtap × gtaptrade) / Σ(gtaptrade)   # trọng số thương mại 2017
ntm_ave_border_simple_pct = mean(AVEgtap)                            # trung bình đơn giản
ntm_ave_n_sectors         = số ngành GTAP có giá trị
ntm_ave_source_year       = 2017 (hằng số)
EUN được nhân bản cho từng thành viên EU.
```

**Ý nghĩa:** biến NTM **duy nhất** trong dự án đo bằng điểm phần trăm thuế —
tức là biến duy nhất có thể so trực tiếp một cú sốc thuế với một cú sốc phi thuế.
Bản trọng số trả lời "một đô-la xuất khẩu trung bình gặp gì ở biên giới"; bản
đơn giản trả lời "một ngành trung bình tốn kém đến đâu".
**Bẫy:** một lát cắt 2017 lặp cho mọi năm → importer FE hấp thụ hoàn toàn.

---

## 5. Green LPI — 4 công thức, chọn 1

**File:** `scripts/build_glpi.py` · **Raw:** `macro_panel_v2.csv` (LPI + CO₂ + năng lượng tái tạo), `epi2026results.xlsx` (Yale EPI)

Hai hàm nền:

```
minmax(x) = (x − min) / (max − min)          # bỏ qua ô trống; nếu max == min -> 0.5
first_pc(X): chuẩn hoá z-score -> eigen của ma trận hiệp phương sai ->
             điểm trên PC1, ĐẢO DẤU nếu loading đầu tiên âm
             (dấu eigenvector là tuỳ ý; một chỉ số lộn ngược giữa hai lần chạy
              còn tệ hơn không có chỉ số)
```

| Cột | Công thức | Khi nào dùng |
|---|---|---|
| `importer_glpi_pca_lpi_epi` | PC1 của `[minmax(LPI tổng), minmax(EPI)]` | **Mặc định** — El-Nakib & Elzarka (2026), bản mới nhất, viết ra để thay bản ratio |
| `importer_glpi_ratio_lpi_epi` | `LPI / EPI × 100` (thang gốc, không chuẩn hoá) | Dự phòng. **Chưa đọc được công thức 2024 gốc (trả phí)** — đây là tái tạo theo mô tả gián tiếp; kiểm lại trước khi trích dẫn |
| `importer_glpi_pca_components` | PC1 của 6 chỉ số con LPI + CO₂/người + % năng lượng tái tạo, tất cả đã min-max, **CO₂ đảo dấu (`1 − x`)** vì phát thải cao = xanh kém | Biến thể duy nhất có phần môi trường đổi theo **từng năm** |
| `importer_glpi_equal_weights` | Trung bình cộng đúng 8 biến đó | Chỉ để kiểm tra ranking có bền khi bỏ PCA hay không |

**Gắn vào panel:** GLPI được đọc theo **đợt khảo sát LPI**, không theo năm lịch —
nếu theo năm lịch thì 4 năm trong 5 sẽ trống.
**Bẫy:** đừng đưa cả 4 vào một mô hình (gần như đa cộng tuyến tuyệt đối).

---

## 6. Hiệp định & phòng vệ thương mại

### 6.1. FTA (`build_covariates.py::build_fta`) — DESTA dyads

```
Giữ dòng có Việt Nam; giải partner theo TÊN trước, ISO numeric sau
Bỏ dòng không có entryforceyear (ký nhưng chưa phê chuẩn)
Khử trùng lặp theo base_treaty, giữ năm hiệu lực SỚM NHẤT
    (DESTA để bản hợp nhất "(consolidated)" thành dòng riêng -> ASEAN-China đếm 2 lần)
Với mỗi (importer, year):
    live  = hiệp định ưu đãi có entry_year <= year
    fta_in_force           = int(live khác rỗng)
    n_agreements           = |live|
    first_fta_year         = năm hiệu lực sớm nhất (rỗng nếu chưa tới)
    years_since_fta        = year − first_fta_year
    gstp_in_force          = int(có hiệp định tên bắt đầu "Global System")
    any_agreement_in_force = tính cả hiệp định KHÔNG ưu đãi
    fta_names              = danh sách tên, nối bằng " | "
```

**Ý nghĩa:** `n_agreements` đo độ dày thể chế của quan hệ; việc **chuyển trạng
thái** của `fta_in_force` trong 2002–2021 mới là variation nhận dạng được.
**Bẫy:** không thay thế mức thuế thực — một FTA có hiệu lực không nói lên mức
cắt bao nhiêu.

### 6.2. Phòng vệ thương mại (`build_covariates.py::build_ttbd`) — TTBD Bown 2016

Ba họ: `GAD` (chống bán phá giá), `GCVD` (chống trợ cấp) — giữ vụ **nêu tên Việt
Nam**; `GSGD` (tự vệ toàn cầu) — theo cấu trúc không nêu tên ai, nên **mọi vụ đều
tính** vì tự vệ áp cho mọi nguồn. `CSGD` (tự vệ riêng Trung Quốc) và `DSUD`
(tranh chấp WTO) bị loại. Một vụ của EU được **nhân bản ra từng thành viên EU**.

```
start = năm biện pháp cuối cùng, hoặc năm khởi xướng nếu chỉ có thuế tạm thời
end   = năm thu hồi, hoặc 2025 nếu REVOKE_DATE == "IF" (còn hiệu lực tại 2015Q4),
        ngược lại = start
{ad,cvd,sg}_initiated = số vụ khởi xướng trong đúng năm đó
{ad,cvd,sg}_in_force  = số vụ có start <= year <= end
ttb_any_in_force      = int(bất kỳ *_in_force nào > 0)
ttbd_observed         = int(year <= 2015)
```

**Bẫy:** TTBD cập nhật lần cuối 6/2016. Sau 2015 các con số **không phải phép
đo** — chúng là "những gì còn hiệu lực tại thời điểm cắt, carry forward, không
bao giờ có vụ mới". Không có cờ `ttbd_observed` đi kèm, nó đọc thành một cú sụp
đổ phòng vệ thương mại đúng chỗ panel đông dữ liệu nhất.

---

## 7. Cú sốc chung theo năm

**File:** `scripts/build_covariates.py::build_shocks` · **Raw:** World Bank Pink Sheet, Baker–Bloom–Davis GEPU

```
price_* , cmo_all_commodities : đọc thẳng sheet "Annual Indices (Nominal)"  [pass-through]
gepu_current = TRUNG BÌNH CỘNG chuỗi GEPU hàng tháng trong năm      [tính ra]
gepu_months  = số tháng thực sự có số liệu trong năm đó             [tính ra]
```

**Ý nghĩa:** đây là kênh sốc *chung* duy nhất trong panel (mọi quan hệ cùng
chịu) — thứ B8 #5 / mô hình frailty tương quan cần để kiểm định "các lần chết có
độc lập không". `gepu_months` cho biết trung bình năm đó dựa trên bao nhiêu tháng.
**Bẫy:** chỉ đổi theo năm → year FE hấp thụ hoàn toàn.

---

## 8. Thuế Mỹ 2025 và CBAM (ngoài scope B0, nhưng đã tính sẵn)

### 8.1. Thuế đối ứng Mỹ (`build_us_tariff_panel.py`)

Mức thuế Việt Nam chịu **đổi 4 lần trong năm 2025**, đọc từ chính văn bản EO:

| Từ ngày | Mức | Căn cứ |
|---|---:|---|
| 05/4/2025 | 10% | EO 14257 §3(a) đoạn 1 — sàn phổ quát |
| 09/4/2025 | 46% | EO 14257 §3(a) đoạn 2 — Annex I |
| 10/4/2025 | 10% | EO 14266 §2 đình chỉ Annex I |
| 07/8/2025 | 20% | EO 31/7/2025 |

```
us_recip_rate_yearend    = mức đang hiệu lực 31/12/2025          (VNM: 20)
us_recip_rate_peak       = mức cao nhất từng được ấn định         (VNM: 46)
us_recip_rate_days_wt    = Σ(rate ngày) / số ngày trong năm       # trung bình theo NGÀY
us_recip_rate_terminated = int(heading đỉnh bị đánh dấu terminated)
us_recip_floor           = heading 9903.01.25, sàn phổ quát       (10)
us_transship_rate        = heading 9903.02.01, hàng bị coi là trung chuyển (40)
Mọi năm < 2025 ghi 0 (nghĩa là "không có sắc thuế này"), không để trống.
```

**Ý nghĩa:** `days_wt` là bản tóm tắt trung thực nhất của một mức thuế chỉ có
hiệu lực một phần năm — và nó **nhỏ hơn nhiều** cả hai con số headline. Đọc 46,
hay kể cả 20, lên toàn bộ năm 2025 là phóng đại độ phơi nhiễm ít nhất gấp đôi.

### 8.2. Miễn trừ theo sản phẩm (`extract_us_exemptions.py`)

Danh sách miễn trừ nằm trong U.S. note 2(v)(iii), chỉ công bố dạng PDF.

```
Gom HTS8 miễn trừ -> HS6 (HS 2022 = H6) -> product_family (H0) qua H6_to_H0
us_recip_exempt_share = |HS6 miễn trừ trong family| / |HS6 thuộc family|
us_recip_exempt_full  = int(share == 1.0)
```

**Ý nghĩa:** `= 1.0` nghĩa là mọi dòng HS 2022 trong family đều được miễn; nhỏ
hơn 1 nghĩa là family **nằm vắt qua ranh giới** và thành phần thực tế của
episode mới quyết định. Đọc là "family này *có chứa* dòng được miễn", không phải
"sản phẩm này được miễn". HS 1992 không phân biệt nổi thêm.

### 8.3. CBAM (`merge_panel.py::attach_cbam`)

```
cbam_in_scope        = int(product_family nằm trong danh mục Reg. EU 2023/956)
cbam_reporting_share = 0.0        nếu year < 2023
                     = 92/365     nếu year == 2023   (hiệu lực 01/10/2023)
                     = 1.0        nếu year > 2023
cbam_definitive      = 0 (luôn) — giai đoạn tính phí thật bắt đầu ngoài cửa sổ panel
Chỉ ghi trên importer EU (membership đọc theo năm, giữ ở 2023 cho 2024-2025).
```

**Ý nghĩa:** `reporting_share` mã hoá đúng việc 2023 chỉ chịu nghĩa vụ báo cáo
92/365 ngày. `cbam_definitive = 0` là lời nhắc: **trong cửa sổ này CBAM chưa hề
là một chi phí carbon thật**, chỉ là nghĩa vụ báo cáo.

---

## 9. Feature cuối cùng: cấu trúc danh mục, biến động, log và lag

**File:** `scripts/build_stage1_df.py` — phase 1 (`build_features()`)
**Định nghĩa "đang sống":** `ACTIVE = (gap_filled == 0)` — một năm đệm dưới ngưỡng
**không** được tính là một sản phẩm/thị trường đang hoạt động.

### 9.1. Cấu trúc danh mục (B3 nhóm 4 — "economies of scope")

```
n_products_to_c[c,t] = số product_family PHÂN BIỆT mà VN bán đủ ngưỡng sang c năm t
n_markets_for_p[p,t] = số importer PHÂN BIỆT mua đủ ngưỡng p từ VN năm t
hs2_share[c,h,t]     = Σ value(c, family thuộc HS2 h, t)  /  Σ value(c, mọi family, t)
                       (cả tử và mẫu chỉ cộng dòng gap_filled == 0)
hs2                  = 2 ký tự đầu của mã HS6 trong product_family  ("H0_610910" -> "61")
```

**Ý nghĩa:** giả thuyết một quan hệ nằm trong **cụm xuất khẩu dày** thì bền hơn
— chia sẻ chi phí chìm, thông tin thị trường, mạng phân phối.
**Bẫy đã xử lý:** dòng `gap_filled == 1` không xuất hiện bên trái các phép gộp
này với tư cách family của chính nó, nhưng vẫn **nhận** được `n_products_to_c`
của thị trường năm đó từ các family khác đang hoạt động — đúng như mong muốn.

### 9.2. `volatility_3y_lag1` — bất ổn gần đây

```
Với k = 1, 2, 3:  lnv_mk = ln(import_value_usd(c, p, year − k) + 1)     # join theo LỊCH
volatility_3y_lag1 = SD của tập {lnv_m1, lnv_m2, lnv_m3} sau khi bỏ ô trống,
                     CHỈ tính khi còn >= 2 giá trị, ngược lại null
```

**Ý nghĩa:** quan hệ có kim ngạch nhảy loạn trong 3 năm gần nhất rủi ro đứt hơn.
**Chú ý:** cửa sổ **kết thúc ở t−1** (dùng t−3, t−2, t−1) — nên tên cột đã mang
sẵn hậu tố `_lag1` và **không được lag lần nữa**. Đây là cột thiếu nhiều nhất
trong mẫu core (25,01%).

### 9.3. Biến đổi log

```
log1p:   log_value            = ln(import_value_usd + 1)
         log_total_import_cp  = ln(total_import_cp_usd + 1)
log_pos: log_gdp_d            = ln(importer_gdp_usd)              nếu > 0, ngược lại null
         log_gdpcap_d         = ln(importer_gdp_per_capita_usd)   nếu > 0
         log_pop_d            = ln(importer_population)           nếu > 0
```

`+1` cho kim ngạch vì giá trị 0 tồn tại thật (năm đệm); GDP/dân số không bao giờ
bằng 0 một cách hợp lệ nên dùng dạng có điều kiện, sạch hơn.
**Chưa có:** `log_dist` — tự tính `ln(dist)` khi lập model (dist bất biến theo
năm nên không cần cột riêng, cũng không cần lag).

### 9.4. Toàn bộ 24 cột lag — **lag là JOIN theo lịch, không phải `.shift()`**

Đây là điểm dễ sai nhất của cả pipeline.

```
lag_lookup(df, cols, on):
    lấy df[on..., year, cols]  ->  unique theo (on..., year)
    ->  year := year + 1  ->  đổi tên cols thành cols_lag1
    ->  join vào bảng đích theo (on..., year)
```

`.shift(1)` sau khi sort sẽ **kéo nhầm giá trị qua khoảng trống**: một cặp
(importer, family) có thể có nhiều spell cách nhau nhiều năm lịch, và ngay trong
một spell, `GAP_TOLERANCE=1` đã chèn thêm dòng năm đệm.

**Mỗi biến được lag theo đúng grain nó *thực sự* sống:**

| Grain join | Cột lag | Vì sao grain đó |
|---|---|---|
| `(importer, product_family)` | `log_value_lag`, `vn_market_share_pct_lag1`, `unit_value_usd_per_kg_lag1`, `tariff_rate_lag1` | Thật sự phụ thuộc cả ba chiều. Null ở dòng đầu spell = "chưa có lịch sử quan hệ", **đúng**, và duration dummies ở B5 hấp thụ nó |
| `(importer)` | `log_gdp_d_lag1`, `log_gdpcap_d_lag1`, `log_pop_d_lag1`, `importer_gdp_growth_pct_lag1`, `importer_inflation_pct_lag1`, `importer_exchange_rate_lcu_per_usd_lag1`, `importer_imports_pct_gdp_lag1`, `importer_exports_pct_gdp_lag1`, `n_products_to_c_lag1` | Thuộc về nước nhập khẩu. Một quan hệ mới toanh vẫn "biết" GDP năm ngoái của thị trường đó |
| `(product_family)` | `rca_lag`, `growth_lag_pct`, `world_growth_pct_lag1`, `n_markets_for_p_lag1`, `log_total_import_cp_lag1`, `tariff_applied_lag`, `tariff_mfn_pct_lag1`, `pref_margin_lag`, `evfta_cut_cum_pp_lag`, `evfta_cut_cum_share_lag` | Vị thế toàn cầu của VN trong sản phẩm, hoặc biểu thuế EU-wide. Nước lần đầu mua giày VN năm 2015 vẫn "biết" RCA giày của VN năm 2014 |
| `(importer, hs2)` | `hs2_share_lag1` | Cụm ngành trong danh mục riêng của từng thị trường |

**Vì sao grain quan trọng đến thế:** nếu lag `rca` theo grain quan hệ, **dòng
đầu mỗi spell — đúng nơi hazard cao nhất — sẽ bị null oan**, làm mất chính những
quan sát cần nhất.

**Một lỗi thật đã xảy ra và đã sửa:** bước lag cấp `(product_family, year)` ban
đầu dùng `.unique()` để khử trùng lặp mà không ưu tiên dòng có giá trị. Năm cột
chính sách EU chỉ được ghi trên 27/147 nước, nên `.unique()` chọn trúng dòng
non-EU (luôn null) khoảng 120/147 lần → ~92% giá trị đúng bị mất oan. Sửa bằng
`drop_nulls(subset=["tariff_applied_pct"])` **trước** khi khử trùng lặp.

> **Bài học để lại:** trước khi thêm bất kỳ cột `_lag` nào, hỏi *"biến này biến
> thiên theo đúng những chiều nào?"* rồi mới chọn khoá join — đừng mặc định lấy
> khoá của bảng chính.

### 9.5. Cột lag đang SAI grain — chưa dùng được

`log_total_import_cp_lag1` bị xếp vào nhóm broadcast `(product_family, year)`,
trong khi `total_import_cp_usd` có grain thật là `(importer, product_family,
year)` (tổng nhập khẩu của **nước c**). Hệ quả: cầu của một importer bị gán cho
mọi importer cùng product-year.

Kiểm tra trực tiếp trên EU27 2012–2024: 126.481 dòng đối chiếu được, **chỉ 2.527
dòng trùng**, 123.954 dòng lệch; và trong cả 24.138 nhóm product–year, giá trị
lag lưu trong file là hằng số giữa các importer.

**⇒ Không đưa `log_total_import_cp_lag1` vào M2/B7 cho tới khi chuyển sang
lookup cấp quan hệ và rebuild.**

---

## 10. Các cột `*_source_year` — metadata, nhưng là metadata *tính ra*

Không phải feature kinh tế, nhưng cũng không phải dữ liệu thô: chúng ghi lại
đúng năm mà giá trị bên cạnh **thật sự được đo**, để không ai phải tin suông.

| Cột | Quy tắc | Dùng để |
|---|---|---|
| `tariff_source_year` | Lùi tối đa 3 năm (`MAX_CARRY_FORWARD`) | `tariff_imputed = int(tariff_source_year != year)` |
| `importer_lpi_source_year` | Đợt khảo sát LPI **gần nhất trong quá khứ** (2007, 2010, 2012, 2014, 2016, 2018, 2022) | Biết điểm LPI đến từ năm nào; GLPI cũng đọc theo đợt này |
| `gravity_source_year` | CEPII dừng ở 2020, carry tối đa 4 năm (`MAX_GRAVITY_CARRY`) | 2021–2025 đều mang 2020 |
| `pci_source_year` | Atlas dừng ở 2024, carry tối đa 4 năm | PCI là thuộc tính chậm đổi của sản phẩm, carry tốt hơn để trống — nhưng phải đóng dấu |
| `ntm_survey_year` | Năm khảo sát NTM của nước đó (2012–2017) | Nói rõ regression đang điều kiện hoá trên cái gì |
| `ntm6_source_year` | Đợt thu thập TRAINS gần nhất ≤ năm | Đi kèm bắt buộc với họ `ntm6_*_survey` |
| `ntm_ave_source_year` | Hằng số 2017 | Nhắc rằng AVE không có chiều thời gian |
| `ttbd_observed` | `int(year <= 2015)` | Cờ *phải* đi kèm mọi bảng dùng `ad_*`/`cvd_*`/`sg_*` |
| `ntm6_observed` | `int(year thuộc năm reporter có filing)` | Phân biệt "0 biện pháp" với "không quan sát" |
| `applied_partial_year` | `int(year == 2020 và nguồn evfta)` | EVFTA chỉ hiệu lực từ 01/8/2020 |

---

## 11. Cột **không** tính — chép thẳng, chỉ join

Nêu ra để khỏi phải kiểm lại: những cột này không có công thức nào ở phía dự án.

| Khối | Cột | Nguồn |
|---|---|---|
| Macro | `importer_gdp_usd`, `importer_gdp_growth_pct`, `importer_gdp_per_capita_usd`, `importer_population`, `importer_inflation_pct`, `importer_exchange_rate_lcu_per_usd`, `importer_exports_pct_gdp`, `importer_imports_pct_gdp`, `importer_co2_per_capita_t`, `importer_renewable_energy_pct` + 6 cột `exporter_*` | World Bank WDI |
| LPI | `importer_lpi_overall` + 6 chỉ số con | World Bank LPI |
| Gravity | `dist`, `distw_harmonic`, `distcap`, `contig`, `comlang_off`, `comlang_ethno`, `comcol`, `col45`, `comrelig`, `comleg_posttrans`, `diplo_disagreement`, `gatt_d`, `wto_d`, `eu_d`, `fta_wto`, `rta_coverage`, `rta_type`, `entry_cost_d`, `entry_proc_d`, `entry_time_d` | CEPII Gravity V202211 |
| Giá hàng hoá | `cmo_all_commodities` + 15 cột `price_*` | World Bank Pink Sheet |
| Complexity | `pci`, `importer_eci`, `importer_coi`, `importer_diversity`, `exporter_eci` | Harvard Growth Lab Atlas v18 (`product_hs4` = 4 ký tự đầu của mã family — đây mới là phần tính) |
| NTM ngành | `ntm_coverage_ratio`, `ntm_frequency_ratio` | WITS `ntm_country.csv` (cấp nước, phía nhập khẩu) |
| CBAM | `cbam_sector`, `cbam_partial` | Reg. EU 2023/956 qua `fetch_cbam_scope.py` |

Trong mẫu EU27 hiện tại, `contig`, `comlang_off`, `comlang_ethno`, `comcol`
**chỉ có một giá trị 0** → không ước lượng được. `col45` còn variation.

---

## 12. Bảng tra ngược: từ cột → file tính nó

| Prefix / cột | File tính | Mục ở trên |
|---|---|---|
| `product_family`, `spell_*`, `t_start/t_stop`, `event`, `*_censored`, `left_trunc`, `gap_filled`, `import_value_usd`, `net_weight_kg`, `unit_value_usd_per_kg` | `build_spells.py` | §1 |
| `rca`, `*_share_pct`, `hhi_*`, `*_growth_pct`, `total_import_cp_usd` | `build_spells.py::derived()` | §2 |
| `tariff_rate`, `tariff_type`, `tariff_source_year`, `tariff_reporter` | `merge_panel.py::attach_tariff()` | §3.1 |
| `tariff_mfn_pct`, `tariff_applied_*`, `pref_margin_pp`, `staging_*`, `years_since_evfta_policy` | `build_evfta_staging.py` → `build_eu_tariff_panel.py` | §3.2 |
| `evfta_cut_cum_pp`, `evfta_cut_cum_share` | `merge_panel.py::load_evfta()` | §3.2 |
| `ntm_*` (trừ `ntm_ave_*`, `ntm6_*`) | `build_ntm.py` | §4.1 |
| `ntm6_*` | `build_ntm6.py` | §4.2 |
| `ntm_ave_*` | `build_ntm_ave.py` | §4.3 |
| `importer_glpi_*` | `build_glpi.py` | §5 |
| `fta_*`, `n_agreements`, `*_fta*`, `gstp_in_force`, `any_agreement_in_force` | `build_covariates.py::build_fta` | §6.1 |
| `ad_*`, `cvd_*`, `sg_*`, `ttb_any_in_force`, `ttbd_observed` | `build_covariates.py::build_ttbd` | §6.2 |
| `gepu_current`, `gepu_months` | `build_covariates.py::build_shocks` | §7 |
| `us_recip_rate_*`, `us_recip_floor`, `us_transship_rate`, `us_recip_effective_from` | `build_us_tariff_panel.py` | §8.1 |
| `us_recip_exempt_share`, `us_recip_exempt_full` | `extract_us_exemptions.py` | §8.2 |
| `cbam_in_scope`, `cbam_reporting_share`, `cbam_definitive` | `merge_panel.py::attach_cbam()` | §8.3 |
| `n_products_to_c`, `n_markets_for_p`, `hs2_share`, `hs2` | `build_stage1_df.py` | §9.1 |
| `volatility_3y_lag1` | `build_stage1_df.py` | §9.2 |
| `log_value`, `log_total_import_cp`, `log_gdp_d`, `log_gdpcap_d`, `log_pop_d` | `build_stage1_df.py` | §9.3 |
| mọi cột `_lag` / `_lag1` | `build_stage1_df.py::lag_lookup()` | §9.4 |

---

## 13. Ngưỡng và hằng số — đổi cái nào thì phải dựng lại cái gì

| Hằng số | Giá trị | Ở đâu | Đổi thì phải chạy lại |
|---|---:|---|---|
| `THRESHOLD_USD` | 10.000 | `build_spells.py` | Toàn bộ pipeline (spell thay đổi) — đây là robustness B8 #1 |
| `GAP_TOLERANCE` | 1 | `build_spells.py` | Toàn bộ pipeline — robustness B8 #2 |
| `YEAR_MIN/MAX` | 2002 / 2025 | `build_spells.py` | Toàn bộ pipeline |
| `MAX_CARRY_FORWARD` | 3 năm | `merge_panel.py` | `merge_panel.py` + `build_stage1_df.py` |
| `MAX_GRAVITY_CARRY` | 4 năm | `merge_panel.py` | như trên |
| `EIF_YEAR` | 2020 | `build_eu_tariff_panel.py` | Khối thuế EU + merge + stage1 |
| `STAGES` | A:1, B3:4, B5:6, B7:8, B10:11 | `build_eu_tariff_panel.py`, `build_evfta_staging.py` | như trên |
| `CBAM_START` | (2023, 92/365) | `merge_panel.py` | merge + stage1 |
| `TTBD_LAST_YEAR` | 2015 | `build_covariates.py` | `build_covariates.py` + merge + stage1 |
| `SOURCE_YEAR` (AVE) | 2017 | `build_ntm_ave.py` | AVE + merge + stage1 |

---

## 14. Ba cảnh báo cuối, gộp lại một chỗ

1. **`log_total_import_cp_lag1` sai grain** (§9.5) — chưa dùng được cho M2/B7.
2. **`tariff_applied_lag` đúng giá trị nhưng mất coverage không cần thiết**:
   feature lag đang dựng từ các product–year *từng có episode EU*, thay vì nối
   thẳng từ `eu_tariff_panel.csv`, nên 2,60% dòng mẫu chính bị null. Chính sách
   tồn tại **trước** quan hệ thương mại — nên lag từ bảng policy đầy đủ.
3. **Không cột nào ở đây là output mô hình.** `S_hat`, `S_hat_lo`, `S_hat_hi`,
   `hazard_rank`, `shap_top3`, `value_expected` chỉ ra đời sau khi chạy B5–B7 —
   chúng chưa nằm trong file này.
