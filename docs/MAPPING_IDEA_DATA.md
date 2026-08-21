# Ánh xạ ý tưởng ↔ dữ liệu đã có — bạn đang ở đâu

*Mọi con số dưới đây đếm trực tiếp trên đĩa ngày **21/08/2026**, không lấy lại
từ tài liệu cũ. Ý tưởng lấy từ [TONG_HOP_Y_TUONG.md](TONG_HOP_Y_TUONG.md).*

Ký hiệu: ✅ đủ dùng ngay · ⚠️ có nhưng kèm hạn chế phải khai báo · ⏳ dựng được
nhưng chưa dựng · ❌ chưa có dữ liệu.

---

## 1. Trạng thái dữ liệu, gói trong một màn hình

| | |
|---|---|
| Panel chính | `analysis/panel_final.csv` — **647.014 episode × 91 cột**, 331 MB |
| Bảng spell | `analysis/spells.csv` — **205.607 spell**, 15 MB |
| Đơn vị | `VNM × importer × product family × năm` |
| Cửa sổ | **2003–2023** (spell bắt đầu 2002 bị loại vì left-censored) |
| Độ phủ | **147/147 importer**, **4.599 product family** |
| Sự kiện | **151.858 chết** · **53.749 right-censored (26,1%)** |
| Phân bố tuổi thọ | trung vị **1 năm**; **53,2%** spell chỉ sống 1 năm; 8,4% sống ≥10 năm |
| Dựng lúc | `build_spells` 21/08 14:26 · `merge_panel` 21/08 14:53 — **cả hai đã chạy trên dữ liệu đầy đủ** |

Bốn kiểm tra bắt buộc của README đều đạt:

| Kiểm tra | Đích | Thực tế |
|---|---|---|
| `exporter` duy nhất | `[VNM]` | ✅ VNM |
| `right_censored` > 0 | > 0 | ✅ 53.749 |
| Số importer | ~147 | ✅ 147 |
| Episode có thuế | > 90% | ✅ 95,7% |
| Episode có PREF | > 0% | ✅ 7,7% (50.136) |
| `rca` có phương sai | có | ✅ p25 = 0,23 · trung vị 0,83 · p75 = 2,94 |

---

## 2. Doc B — thang L0→L5: từng bậc cần gì, đã có gì

Đây là nhánh mà workspace này thực sự phục vụ.

### L0 — Traditional Export Portfolio Optimization

| Thành phần cần | Trạng thái | Nguồn trong workspace |
|---|---|---|
| Tập lựa chọn `importer × product` | ✅ | 647.014 episode, 147 × 4.599 |
| Export performance | ✅ | `import_value_usd`, `country_growth_pct` |
| Ràng buộc tập trung (HHI) | ✅ | `hhi_market`, `hhi_product`, `partner_share_pct`, `product_share_pct` |
| Ràng buộc thuế | ⚠️ | `tariff_rate` 95,7% — xem §5.1 |
| Formulation toán học | ❌ | **chưa viết** |

> **Kết luận L0:** dữ liệu xong. Việc còn lại thuần modeling.

### L1 — Survival-Adjusted Export Portfolio

| Thành phần cần | Trạng thái | Ghi chú |
|---|---|---|
| Spell + duration + event + censoring | ✅ | `spells.csv`, đã có cờ `right_censored` |
| Định dạng counting-process cho Cox | ✅ | `panel_final.csv` có `t_start`, `t_stop`, `event` — dùng thẳng được với `lifelines` / `survival` |
| Covariate biến thiên theo thời gian | ✅ | thuế, GDP, FTA, TTB, giá hàng hoá, share, HHI |
| Ước lượng `P(survival | horizon)` | ⏳ | **chưa chạy mô hình nào** |
| So sánh với L0 | ⏳ | phụ thuộc L0 |

> **Kết luận L1:** dữ liệu xong, kể cả phần khó nhất (counting process). Chưa
> chạy Kaplan–Meier hay Cox lần nào — đây là việc kế tiếp và là **cửa quyết
> định** cho toàn bộ cái thang.

⚠️ **Một cảnh báo về hình dạng dữ liệu:** 53,2% spell chỉ sống đúng 1 năm. Với
ngưỡng 10.000 USD/năm, phần lớn "quan hệ" là giao dịch một lần rồi thôi. Trước
khi mô hình hoá phải quyết: giữ nguyên, nâng ngưỡng, hay tách riêng nhóm
one-shot. Quyết định này đổi hoàn toàn ý nghĩa của hazard ước lượng được.

### L2 — Survival-Constrained Export Diversification

| Thành phần cần | Trạng thái | Ghi chú |
|---|---|---|
| Export performance + survival prob. | ⏳ | phụ thuộc L1 |
| Partner share / product share / HHI | ✅ | 100% độ phủ |
| Ràng buộc network survivability ≥ α | ❌ | **định nghĩa chưa tồn tại** — xem §5.4 |
| Ràng buộc HHI ≤ Hmax | ✅ | tính được |
| Ràng buộc tariff exposure ≤ Tmax | ⚠️ | tính được nhưng thuế bị chệch lên, §5.1 |

> **Kết luận L2:** dữ liệu xong; chặn ở định nghĩa, không ở dữ liệu.

### L3 — Dynamic Survival-Aware Export Network Reconfiguration (CORE TARGET)

| Thành phần cần | Trạng thái | Ghi chú |
|---|---|---|
| Relationship state theo thời gian | ✅ | episode-year có `event`, `t_start`, `t_stop` |
| Hazard/survival có covariate động | ✅ | 21 năm × 91 cột |
| Trade barrier theo thời gian | ⚠️ | thuế dừng 2021 (§5.1); TTB dừng 2015 (§5.2); NTM time-invariant (§5.3) |
| Action maintain/expand/reduce/enter/exit | ❌ | **chưa định nghĩa đo bằng gì** |
| Time loop + backtest | ⏳ | dữ liệu 21 năm đủ để backtest rolling |
| Benchmark tĩnh | ⏳ | chính là L0 và L1 |

> **Kết luận L3:** dữ liệu đủ về chiều thời gian. Điểm yếu thật sự là **chiều
> rào cản thương mại**: cả ba biến barrier đều mất tính biến thiên đúng ở đoạn
> cuối cửa sổ. Nếu L3 muốn nói "policy shock đẩy hazard lên", ba lỗ hổng ở §5
> phải được xử lý hoặc khai báo thẳng.

### L4 — Export Network Reliability Optimization

| Thành phần cần | Trạng thái |
|---|---|
| Node/edge và mức gộp | ❌ chưa chốt |
| Edge survival probability | ⏳ ra từ L1 |
| Failure scenario | ⏳ dựng được từ lịch sử event |
| Network performance threshold | ❌ chưa định nghĩa |
| Reliability metric có ý nghĩa kinh tế **và** toán học | ❌ chưa định nghĩa |

> **Kết luận L4:** dữ liệu không phải rào cản. Rào cản là định nghĩa.

### L5 — Correlated Failure / Common-Shock Resilience

| Thành phần cần | Trạng thái | Nguồn |
|---|---|---|
| Individual hazard | ⏳ | ra từ L1 |
| Biến sốc chung | ✅ | `shocks_annual.csv` → 17 chỉ số giá WB CMO + `gepu_current` (Global EPU), đã merge 100% |
| Cấu trúc phụ thuộc giữa các failure | ❌ | chưa ước lượng |
| Stress testing | ⏳ | có 2008–2009 và 2020 trong cửa sổ để làm sốc thật |
| Robust/stochastic optimization | ❌ | chưa tới |

> **Kết luận L5:** ✅ đáng chú ý — biến sốc chung **đã có sẵn**. Cửa sổ 2003–2023
> chứa đủ hai cú sốc lớn (GFC, COVID) để nhận dạng correlated failure. Đây là
> bậc thang mà dữ liệu hiện có hỗ trợ tốt hơn mong đợi.

---

## 3. Doc A — năm tab: cần gì, workspace đáp ứng được bao nhiêu

| Tab | Dữ liệu cốt lõi mà tab cần | Có trong workspace? | Còn phải làm gì |
|---|---|---|---|
| **1** — DSS logistics | Giá cước theo lane, booking, lead time, tồn kho, chi phí stock-out | ❌ **không có gì** | Toàn bộ. Dữ liệu vi mô không công khai |
| **2** — Event study trade diversion | US Census HS10 **theo tháng**, 2018–2025 | ❌ không có | Panel hiện tại là **năm**, mức HS6, dừng 2023. Phải tải nguồn mới |
| **4** — Stochastic sourcing dưới bất định thuế | Lịch sử thuế Mỹ–VN 2025, cấu trúc chi phí DN | ❌ không có | Thuế trên đĩa dừng **2021** |
| **5** — I-O / Markowitz 9 DN niêm yết | BCTC quý HOSE/HNX 2025, bảng I-O | ❌ không có | Toàn bộ |
| **6** — Vòng xoáy trả đũa + spillover VN | WTO–IMF Tariff Tracker (ngày hiệu lực, song phương, HS6) | ❌ không có — **chờ API key I-TIP** | Tầng 1–3 phải tải mới |
| **6, Tầng 4** — VN spillover exposure index | Tỷ trọng xuất khẩu theo ngành/đối tác, thị phần | ✅ **có đủ** | Tính được ngay từ `partner_share_pct`, `product_share_pct`, `vn_market_share_pct`, `hhi_*` — nhưng chỉ tới **2023** |

**Đọc bảng này:** bốn tab đầu của Doc A gần như không dùng được gì từ workspace.
Tab 6 dùng được đúng một tầng — và đó cũng là tầng dễ nhất. Nếu nhóm chọn hướng
Doc A, phải chấp nhận là **phần thu thập dữ liệu bắt đầu lại gần như từ đầu**.

---

## 4. Bảng biến chi tiết — 91 cột, độ phủ đo thật

### 4.1. Khoá và kết cục

| Cột | Độ phủ | Ghi chú |
|---|---|---|
| `spell_id`, `importer`, `exporter`, `product_family`, `year` | 100% | `exporter` luôn = VNM |
| `t_start`, `t_stop`, `event` | 100% | định dạng counting-process, dùng thẳng cho Cox |
| `import_value_usd` | 100% | do nước nhập khẩu khai (CIF) |

### 4.2. Hiệu năng và cấu trúc — 8 biến, tự tính, **100% độ phủ**

| Cột | Ý nghĩa | Dùng cho level nào |
|---|---|---|
| `rca` | Balassa RCA, mẫu số là nhập khẩu thế giới thật | L0–L3 |
| `product_share_pct` | tỷ trọng sản phẩm trong rổ XK của VN | L0–L2 |
| `partner_share_pct` | tỷ trọng đối tác | L0–L2 |
| `vn_market_share_pct` | thị phần VN trong `importer × product` | L2–L4 |
| `hhi_market`, `hhi_product` | hai chỉ số Herfindahl | L2 (ràng buộc) |
| `country_growth_pct` | tăng trưởng XK của VN theo từng sản phẩm | L0–L1 |
| `world_growth_pct` | tăng trưởng nhập khẩu thế giới theo sản phẩm | L1–L3 |

> ✅ Đây là nhóm biến từng hỏng hoàn toàn ở bản dựng 19/08 (`rca` = 1,0 mọi
> dòng, `vn_market_share_pct` trống 100%). Bản dựng 21/08 đã sửa: cả 8 biến
> **100% độ phủ và có phương sai thật**.

### 4.3. Rào cản thương mại

| Cột | Độ phủ | Hạn chế |
|---|---|---|
| `tariff_rate`, `tariff_type`, `tariff_source_year`, `tariff_reporter` | 95,7% | MFN 568.917 · PREF 50.136 · không có 27.961. **2022–2023 chỉ là carry-forward từ 2021** — §5.1 |
| `ad_*`, `cvd_*`, `sg_*`, `ttb_any_in_force`, `ttbd_observed` (8 cột) | 100% | Khởi xướng vụ kiện **dừng ở 2015**; sau đó `in_force` là ngoại suy — §5.2 |
| `ntm_*` (11 cột) | 79,6% | **Time-invariant**, cấp ngành 16 nhóm — §5.3 |
| `fta_in_force`, `n_agreements`, `years_since_fta`, … (10 cột) | 100% | ✅ biến thiên theo thời gian tốt: 995 episode có FTA năm 2003 → 33.335 năm 2023 |
| `rta_coverage`, `rta_type`, `fta_wto` | 29,6% | Từ CEPII Gravity V202211; thưa và **không trùng khớp** với `fta_in_force` dựng từ DESTA — chọn một, đừng dùng cả hai |

### 4.4. Kiểm soát

| Nhóm | Cột | Độ phủ | Hạn chế |
|---|---|---|---|
| Vĩ mô | `exporter_gdp_*`, `importer_gdp_*` (4 cột) | 100% | **Chỉ 4 trong 9 biến vĩ mô đã tải được merge** — §5.5 |
| Gravity | `dist`, `distw_harmonic`, `contig`, `comlang_*`, `col45`, … (20 cột) | 84,2% | Thiếu đúng 2022 và 2023 — CEPII dừng ở 2021, §5.5 |
| Sốc chung | `cmo_all_commodities`, `gepu_current` + 17 chỉ số giá | 100% | ✅ sẵn cho L5 |
| Thể chế | `entry_cost_d`, `entry_proc_d`, `entry_time_d` | 69,4% | Cũng từ CEPII Gravity V202211 (gốc Doing Business); thưa hơn `dist` |

---

## 5. Năm lỗ hổng có thể chặn kết luận

### 5.1. Thuế dừng ở 2021 — lỗ hổng đắt nhất

`scripts/fetch_tariffs.py:46` vẫn là `YEARS = list(range(2002, 2022))`. Trên đĩa
không có file thuế nào cho 2022–2023. Hệ quả đo được:

| Năm | Episode | Có thuế |
|---|---|---|
| 2003–2021 | 605.780 | 98,6–100% |
| **2022** | 49.989 | **75,3%** |
| **2023** | 52.245 | **74,3%** |

Toàn bộ phần "có thuế" của 2022–2023 là **giá trị 2021 mang sang** (`merge_panel`
carry-forward ≤ 3 năm: 90.721 episode, 14,0% panel). Nghĩa là **hai năm cuối
cùng của panel không có biến thiên thuế thật**.

**Vì sao quan trọng:** L3 sống bằng việc rủi ro thay đổi theo thời gian. Nếu hai
năm cuối là hằng số, mọi kết luận "policy shock đẩy hazard" ở đoạn cuối là giả.

**Cách sửa:** đổi một dòng thành `range(2002, 2024)` rồi chạy lại
`fetch_tariffs.py --pass all` → `merge_panel.py`. Máy làm được, không cần ai cấp
quyền. **Đây là việc ưu tiên số 1.**

### 5.2. Trade remedy dừng ở 2015

`ad_initiated` có giá trị dương ở các năm 2004–2015 rồi **im lặng hoàn toàn**.
Nhưng `ttb_any_in_force` vẫn khác 0 tới 2023 (9.644 episode) vì một biện pháp
khởi xướng trước 2016 không có ngày thu hồi sẽ được coi là còn hiệu lực mãi mãi.

**Rủi ro:** 8 năm cuối panel, biến trade-remedy trông có dữ liệu nhưng thực chất
là ngoại suy. Không được diễn giải hệ số của nó cho giai đoạn 2016–2023.

**Cách sửa:** hoặc kiểm duyệt biến này ở 2015 và nói rõ trong Limitations, hoặc
scrape báo cáo bán niên WTO. Chi phí trung bình.

### 5.3. NTM time-invariant, cấp ngành

Ba file NTM công khai của WITS không có chiều năm ở mức sản phẩm. Mọi sản phẩm
trong cùng một ngành (16 nhóm) nhận cùng một giá trị, cho một lát cắt duy nhất
2012–2017. Độ phủ 79,6%; nhiều importer lớn — trong đó có Trung Quốc và Hàn Quốc
— không có bản ghi nào.

**Cách sửa:** cần tài khoản TRAINS Online (Azure AD) → researcher file → NTM lên
HS6 × năm, 28/53 nước có ≥2 đợt khảo sát. **Chỉ bạn làm được**, máy không đăng
ký thay được.

### 5.4. Không có định nghĩa "network survivability"

Đây không phải lỗ hổng dữ liệu mà là lỗ hổng khái niệm, nhưng nó chặn L2, L4 và
L5. Doc B cảnh báo thẳng: không được đổi tên tổng xuất khẩu hoặc HHI thành
"reliability". Cần một định nghĩa vừa có nghĩa toán học vừa có nghĩa kinh tế,
chốt **trước** khi viết code tối ưu.

### 5.5. Hai lỗ hổng nhỏ, sửa nhanh

| Vấn đề | Chi tiết | Cách sửa |
|---|---|---|
| Gravity trống 2022–2023 | `dist` thiếu đúng 102.234 episode của hai năm này; CEPII dừng ở 2021. Nhưng `dist`, `contig`, `comlang` là **bất biến theo thời gian** | Carry-forward giá trị 2021 cho 2022–2023 trong `merge_panel.py`. Vài dòng code |
| 5 biến vĩ mô đã tải nhưng chưa merge | `macro_panel_v2.csv` có `inflation_pct`, `exchange_rate_lcu_per_usd`, `lpi_overall`, `population`, `exports_pct_gdp` — `panel_final.csv` **không có cột nào trong 5 cột này** | Mở rộng danh sách cột trong `merge_panel.py`. Tỷ giá và LPI là kiểm soát chuẩn của literature trade-duration |

---

## 6. Thanh tiến độ

```
DOC B — nhánh journal (workspace phục vụ nhánh này)
  Thu thập dữ liệu     ████████████████████░  95%   thiếu thuế 2022–23, NTM HS6
  Dựng panel           ████████████████████░  95%   thiếu gravity carry-fwd, 5 biến macro
  Chốt định nghĩa      ███░░░░░░░░░░░░░░░░░   15%   2/12 chốt hẳn + 1 còn hạn chế (§2.3 Doc B)
  Survival baseline    ░░░░░░░░░░░░░░░░░░░░    0%   CHƯA CHẠY MÔ HÌNH NÀO
  L0 benchmark         ░░░░░░░░░░░░░░░░░░░░    0%
  L1 optimization      ░░░░░░░░░░░░░░░░░░░░    0%
  L2 / L3              ░░░░░░░░░░░░░░░░░░░░    0%

DOC A — nhánh thi
  Tab 6 tầng 1–3       ░░░░░░░░░░░░░░░░░░░░    0%   chặn ở API key WTO I-TIP
  Tab 6 tầng 4         ████████████████░░░░   80%   biến đã có, chưa gộp thành index
  Tab 1 / 2 / 4 / 5    ░░░░░░░░░░░░░░░░░░░░    0%   không có dữ liệu nào
```

**Đọc thanh này:** phần thu thập gần xong; phần **modeling chưa bắt đầu**. Điểm
nghẽn đã dịch từ "thiếu dữ liệu" sang "thiếu định nghĩa và thiếu mô hình".

---

## 7. Việc tiếp theo, xếp theo thứ tự

| # | Việc | Ai | Chi phí | Mở khoá cái gì |
|---|---|---|---|---|
| 1 | Sửa `fetch_tariffs.py:46` → `range(2002, 2024)`, tải lại, `merge_panel` | máy | ~2–3 giờ | Biến thiên thuế cho 2022–2023 — §5.1 |
| 2 | **Chạy Kaplan–Meier + Cox baseline** | máy | ~1 giờ | **Cửa quyết định của cả cái thang** |
| 3 | Chốt 12 định nghĩa ở §2.3 của Doc B | **nhóm** | 1 buổi họp | L0 trở đi |
| 4 | Quyết cách xử lý 53,2% spell một năm | **nhóm** | 1 buổi họp | Ý nghĩa của hazard |
| 5 | Carry-forward gravity + merge 5 biến vĩ mô | máy | ~30 phút | Bộ kiểm soát đầy đủ |
| 6 | Dựng L0 benchmark | máy | — | Điểm so sánh cho L1 |
| 7 | Đăng ký TRAINS Online → researcher file | **bạn** | — | NTM lên HS6 × năm — §5.3 |
| 8 | API key WTO I-TIP tại apiportal.wto.org | **bạn** | — | Toàn bộ Doc A / Tab 6 |
| 9 | Kiểm duyệt biến trade-remedy ở 2015 hoặc scrape WTO | máy | — | §5.2 |
| 10 | Nếu chọn nhánh thi: gộp exposure index cho VN | máy | ~2 giờ | Tab 6 tầng 4 |

**Hai việc chỉ bạn làm được là #7 và #8.** Cả hai đều là đăng ký tài khoản, và
cả hai đang chặn những thứ mà máy không thể tự gỡ.
