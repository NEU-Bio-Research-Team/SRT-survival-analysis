# Sinking Relationships — Khung nghiên cứu tổng quan & Pipeline Stage 1

**Tên đề tài:** Survival-Constrained Dynamic Reconfiguration of Vietnam's Export Portfolio under Tariff Policy Uncertainty

**Phiên bản:** Bản phác thảo thiết kế — tháng 8/2026 **Trạng thái:** Stage 1 đã chốt scope và pipeline. Stage 2 tạm pending.

---

# PHẦN I — TỔNG QUAN HAI TẦNG

## 1.1. Câu hỏi cốt lõi

Cách tiếp cận truyền thống đánh giá xuất khẩu bằng **tổng kim ngạch**. Nghiên cứu này lập luận rằng con số đó che giấu rủi ro: một danh mục tỷ đô xây trên những quan hệ thương mại ngắn hạn, dễ đứt gãy thì mong manh hơn một danh mục nhỏ hơn nhưng bền vững.

Đơn vị phân tích không phải quốc gia hay ngành, mà là **quan hệ thương mại \= 1 thị trường × 1 sản phẩm** (ví dụ: Đức × HS 610910 áo thun cotton). Mỗi quan hệ có tuổi thọ, có xác suất chết, và xác suất đó phản ứng khác nhau trước cùng một cú sốc chính sách.

**Câu hỏi tổng:** Việt Nam nên tái cấu trúc danh mục xuất khẩu như thế nào để tối đa hóa giá trị kỳ vọng, đồng thời giữ vững ngưỡng sinh tồn trước rủi ro chính sách?

## 1.2. Kiến trúc hai tầng

┌─────────────────────────────────────────────────────────────┐

│  STAGE 1 — SURVIVAL ANALYSIS                                │

│  "Quan hệ nào sống? Tại sao chết? Chính sách tác động sao?" │

│                                                             │

│  Input:  BACI \+ Gravity \+ WITS \+ EVFTA staging schedule     │

│  Method: Discrete-time hazard (cloglog \+ frailty)           │

│          \+ nhánh ML (RSF / GBM / DeepHit) \+ SHAP            │

│  Output: Ŝ(c,p,t) — xác suất sống sót từng quan hệ          │

│          \+ β̂ — cơ chế kinh tế đằng sau rủi ro đứt gãy       │

└─────────────────────────────────────────────────────────────┘

                              │

                              │  BẢNG BÀN GIAO

                              │  (c, p, t, Ŝ, E\[value\], SE)

                              ▼

┌─────────────────────────────────────────────────────────────┐

│  STAGE 2 — SURVIVAL-INFORMED PORTFOLIO  \[PENDING\]           │

│  "Giữ gì? Bỏ gì? Danh mục có sống nổi cú sốc không?"        │

│                                                             │

│  Input:  Bảng bàn giao từ Stage 1                           │

│  Method: Risk-adjusted ranking \+ CVaR constraint            │

│          \+ counterfactual tariff simulation                 │

│  Output: Xếp hạng quan hệ, khuyến nghị Duy trì/Mở rộng/     │

│          Thu hẹp/Gia nhập/Rút lui, bản đồ cảnh báo sớm      │

└─────────────────────────────────────────────────────────────┘

## 1.3. Chiến lược công bố

Hai tầng nên tách thành **hai bài báo riêng**, không gộp một manuscript:

|  | Paper A (Stage 1\) | Paper B (Stage 2\) |
| :---- | :---- | :---- |
| Nội dung | Survival của quan hệ XK VN–EU dưới EVFTA | Survival-informed portfolio reallocation |
| Đóng góp | Thực nghiệm \+ identification sạch | Phương pháp: nối micro-risk với macro-decision |
| Rủi ro | Thấp — có tiền lệ dày trong literature | Cao — thiếu dữ liệu chi phí, cần calibrate |
| Journal | *The World Economy*, *Review of World Economics*, *Journal of Asian Economics* | *Economic Modelling*, *Expert Systems with Applications*, *Annals of OR* |
| Vai trò | Deliverable chắc chắn của proposal | Phần tham vọng của proposal |

**Lý do tách:** ghép cả hai vào một bài sẽ ra sản phẩm nửa vời — reviewer kinh tế chê phần tối ưu thiếu nền tảng vi mô, reviewer OR chê phần thực nghiệm không phải đóng góp phương pháp.

## 1.4. Mạch nối Stage 1 → Stage 2

Đây là điểm quan trọng nhất cần hình dung rõ.

**Output cuối cùng của Stage 1 là một bảng phẳng duy nhất**, mỗi dòng là một quan hệ tại một thời điểm:

| c | p | t | S\_hat | S\_hat\_lo | S\_hat\_hi | value\_expected | hazard\_rank |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| DEU | 610910 | 2024 | 0.912 | 0.887 | 0.934 | 12,400,000 | 0.18 |
| ESP | 030617 | 2024 | 0.634 | 0.571 | 0.692 | 8,900,000 | 0.71 |
| POL | 640399 | 2024 | 0.845 | 0.802 | 0.881 | 3,200,000 | 0.34 |

**Stage 2 chỉ cần đúng bảng này.** Nó không cần chạy lại survival model, không cần dữ liệu thô. Nó lấy `value_expected × S_hat` làm giá trị điều chỉnh rủi ro, dùng `S_hat_lo/hi` để dựng phân phối cho mô phỏng, và giải bài toán phân bổ dưới ràng buộc CVaR.

Vì vậy **toàn bộ thiết kế Stage 1 phải hướng về việc sản xuất bảng này**. Nếu một bước nào đó trong pipeline không góp phần tạo ra hoặc kiểm chứng bảng này, nó thuộc về phụ lục, không phải mạch chính.

Một hệ quả thực tế: khi ước lượng ở Stage 1, phải lưu được **prediction ở cấp từng quan hệ**, không chỉ hệ số trung bình mẫu. Nhiều bài survival trong thương mại chỉ báo cáo hệ số — với đề tài này thì như vậy là chưa đủ.

---

# PHẦN II — STAGE 1: PIPELINE CHI TIẾT

## Sơ đồ tổng thể

\[B0\] Chốt scope

  ↓

\[B1\] Thu thập & nạp dữ liệu (4 nguồn)

  ↓

\[B2\] Dựng spell ★ KHỐI QUYẾT ĐỊNH

  ↓

\[B3\] Feature engineering (lag t−1)

  ↓

\[B4\] Phân tích mô tả (Kaplan–Meier)

  ↓

\[B5\] Mô hình kinh tế lượng (cloglog \+ frailty)

  ↓

\[B6\] Identification EVFTA (staging intensity)

  ↓

\[B7\] Nhánh ML \+ XAI

  ↓

\[B8\] Robustness

  ↓

\[B9\] Xuất bảng bàn giao → Stage 2

---

## B0 — Chốt scope

Chốt dứt khoát dựa trên tính khả thi dữ liệu, không để mở.

| Tham số | Giá trị chốt | Lý do |
| :---- | :---- | :---- |
| **Exporter** | Việt Nam (BACI code 704\) | — |
| **Importer** | EU-27 | Không gian thể chế chung, dễ cô lập biến chính sách |
| **Đơn vị sản phẩm** | HS6, bản **HS2012** | Ổn định qua toàn kỳ, tránh phải nối concordance |
| **Khung thời gian** | **2012–2024** | HS2012 có hiệu lực từ 2012; BACI 202601 phủ đến \~2024 |
| **Đơn vị quan sát** | quan hệ (c, p) × năm | — |
| **Cấp phân tích** | **Quốc gia**, KHÔNG phải doanh nghiệp | Firm-level cần customs data không public — rủi ro quá lớn cho critical path |
| **Ngưỡng tồn tại** | **≥ 10.000 USD/năm** | Lọc nhiễu quanh ngưỡng báo cáo Comtrade |
| **Quy tắc gap** | Gián đoạn **1 năm** không tính là chết | Chuẩn trong literature (Besedeš–Prusa) |
| **Left truncation** | Kéo BACI HS2007 về 2007 chỉ để đếm tuổi khởi điểm | Tránh bias tuổi thọ |
| **Mẫu mở rộng** | UK tách riêng (Brexit), 147 thị trường để robustness | Không gộp vào mẫu chính |

**Quyết định quan trọng nhất là dòng "cấp phân tích".** Slide gốc viết "1 Importer × 1 Product" — nếu hiểu "importer" là doanh nghiệp nhập khẩu thì phải xin dữ liệu hải quan cấp doanh nghiệp, không public, và đó là một đề tài khác hẳn. Chốt ở cấp quốc gia là lựa chọn khả thi; firm-level để làm extension nếu xin được dữ liệu.

**Ước lượng quy mô:** 27 nước × \~5.300 dòng HS6 × 13 năm ≈ **1,86 triệu ô** trong full grid. Chạy được trên laptop nếu dùng đúng công cụ.

---

## 

## B1 — Thu thập & nạp dữ liệu

### B1.1. BACI (CEPII) — nguồn chính

- **Bản:** 202601 (cập nhật 1/2026), revision **HS2012**  
- **Link:** `cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37`  
- **License:** Etalab 2.0 — dùng tự do, chỉ cần trích nguồn  
- **Định dạng:** zip chứa CSV theo từng năm \+ metadata mã nước/mã sản phẩm

**Cột:**

| Cột | Ý nghĩa | Ghi chú |
| :---- | :---- | :---- |
| `t` | năm |  |
| `i` | nước xuất khẩu | mã BACI, không phải ISO chuẩn |
| `j` | nước nhập khẩu |  |
| `k` | mã HS6 | **đọc dạng string**, numeric sẽ mất số 0 đầu |
| `v` | giá trị, nghìn USD |  |
| `q` | khối lượng, tấn | nhiều missing |

**Bẫy chí mạng:** BACI (giống Comtrade) **không ghi các dòng giá trị bằng 0**. Mà số 0 chính là sự kiện đứt gãy cần đo. Đây là lý do B2 tồn tại.

### B1.2. CEPII Gravity — biến kiểm soát

- **Bản:** 202211, phủ 1948–2020, có sẵn CSV / R / Stata  
- **Cột dùng:** `distw_harmonic`, `contig`, `comlang_off`, `comcol`, `gdp_o`, `gdp_d`, `gdpcap_d`, `pop_d`, `rta`, `wto_d`  
- **Hạn chế:** dừng ở 2020 — đúng lúc EVFTA bắt đầu. Phải nối GDP/dân số 2021–2024 từ World Bank WDI

\# nối phần thiếu

import wbdata

gdp \= wbdata.get\_dataframe({'NY.GDP.MKTP.KD': 'gdp'}, country=eu27\_iso3)

R: `WDI::WDI(country=..., indicator="NY.GDP.MKTP.KD", start=2021, end=2024)`

### B1.3. WITS / UNCTAD TRAINS — thuế quan

- **API:** `wits.worldbank.org/witsapiintro.aspx`  
- **Chiều truy vấn:** Reporter × Partner × Product Code (HS6)  
- **Thư viện:**  
  - R: `devtools::install_github("diegoacastro/witstrainsr")` → `get_tariffs()`  
  - Python: `pip install world_trade_data` → `get_tariff_reported()`, `get_tariff_estimated()`

**Ba vấn đề đã biết, phải xử lý:**

1. Dữ liệu thiếu nhiều năm → nội suy hoặc carry-forward, ghi rõ trong bài  
2. Mã HS đổi theo thời gian → dựng concordance riêng  
3. Một tuyến–sản phẩm có nhiều mức thuế cùng lúc (MFN, PTA, GSP, EVFTA) → **quy ước lấy min**, và tính `preference_margin = MFN − applied`

**Lưu ý:** MAcMap-HS6 của CEPII **không dùng được** cho câu hỏi EVFTA — bản public chỉ có 2001, 2004, 2007, 2010, 2013, 2016 và 2019, dừng trước 2020\. Chỉ dùng làm thuế nền giai đoạn đầu.

### B1.4. EVFTA staging schedule — biến identification

Đây là tài sản dữ liệu riêng của đề tài.

- **Nguồn:** Annex 2-A của EVFTA, PDF tải tại Trung tâm WTO (VCCI): `trungtamwto.vn`  
- **Nội dung:** 10 mã staging category cho từng dòng thuế, từ xóa bỏ ngay đến giảm dần qua 11 giai đoạn. Lần cắt đầu 1/8/2020, các lần sau vào 1/1 hằng năm  
- **Đối chiếu:** Access2Markets → My Trade Assistant (tra theo từng sản phẩm)

**Việc phải làm:** parse PDF Annex 2-A thành bảng `HS8 → staging_category → lộ trình thuế theo năm`, rồi tổng hợp lên HS6.

import camelot          \# bảng có đường kẻ

import pdfplumber       \# bảng không đường kẻ

Ước lượng công sức: **1–2 tuần**, cần verify thủ công một mẫu ngẫu nhiên. Nên tính vào WP1 của proposal — chưa ai public bảng này ở dạng machine-readable, nên bản thân nó là một sản phẩm nghiên cứu.

### Output B1

4 file parquet: `baci_raw.parquet`, `gravity.parquet`, `tariff.parquet`, `evfta_staging.parquet`

---

## B2 — Dựng spell ★ KHỐI QUYẾT ĐỊNH

Đây là nơi quyết định chất lượng cả nghiên cứu, và cũng là nơi sai lầm khó phát hiện nhất.

### Quy trình 7 bước

1\. Lọc BACI: i \= 704 (VN), j ∈ EU27, k ∈ HS6

2\. Expand full grid: 27 × 5300 × 13 \= 1.86M ô

3\. Left join giá trị → ô trống điền 0

4\. Áp ngưỡng 10k USD → biến nhị phân \`active\`

5\. Áp gap rule (1 năm) → làm mượt chuỗi

6\. Gán spell\_id cho mỗi chuỗi active liên tục

7\. Tính duration, failure, censored, left\_trunc

### Công cụ

Với 1,86 triệu dòng, pandas sẽ chậm nhưng vẫn chạy được. Khuyến nghị:

import duckdb          \# SQL trực tiếp trên parquet, không load hết vào RAM

import polars as pl    \# nhanh hơn pandas 5–10× cho groupby/window

R: `data.table` hoặc `duckdb`. Tránh `dplyr` thuần cho bước expand grid.

### Ví dụ code khung

import duckdb

con \= duckdb.connect()

\# Bước 2-3: expand grid \+ join

con.execute("""

CREATE TABLE grid AS

SELECT c.iso3 AS c, p.hs6 AS p, y.t AS t

FROM eu27 c CROSS JOIN hs6\_list p CROSS JOIN years y

""")

con.execute("""

CREATE TABLE panel AS

SELECT g.c, g.p, g.t,

       COALESCE(b.v \* 1000, 0\) AS value\_usd,

       CASE WHEN COALESCE(b.v \* 1000, 0\) \>= 10000 THEN 1 ELSE 0 END AS active\_raw

FROM grid g

LEFT JOIN baci b ON g.c \= b.j AND g.p \= b.k AND g.t \= b.t

""")

Bước 5–7 (gap rule \+ spell id) dùng window function:

import polars as pl

df \= (df.sort(\["c", "p", "t"\])

      \# gap rule: nếu năm trước và năm sau đều active thì lấp năm giữa

      .with\_columns(\[

          pl.col("active\_raw").shift(1).over(\["c","p"\]).alias("prev"),

          pl.col("active\_raw").shift(-1).over(\["c","p"\]).alias("next"),

      \])

      .with\_columns(

          pl.when((pl.col("active\_raw")==0) & (pl.col("prev")==1) & (pl.col("next")==1))

            .then(1).otherwise(pl.col("active\_raw")).alias("active")

      )

      \# spell\_id \= cumsum của các lần bật từ 0 lên 1

      .with\_columns(

          ((pl.col("active")==1) & (pl.col("active").shift(1).over(\["c","p"\]).fill\_null(0)==0))

          .cum\_sum().over(\["c","p"\]).alias("spell\_seq")

      ))

### Bảng kết quả — định dạng person-period

| c | p | t | spell\_id | duration | active | failure | censored | left\_trunc |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| DEU | 610910 | 2016 | 1042 | 1 | 1 | 0 | 0 | 0 |
| DEU | 610910 | 2017 | 1042 | 2 | 1 | 0 | 0 | 0 |
| DEU | 610910 | 2018 | 1042 | 3 | 1 | 1 | 0 | 0 |
| DEU | 610910 | 2019 | — | — | 0 | — | — | — |

Định nghĩa:

- `duration`: số năm tính từ đầu spell (1, 2, 3, …)  
- `failure = 1` tại năm cuối cùng còn sống nếu năm sau chết  
- `censored = 1` nếu spell còn sống tại 2024 (chưa quan sát được cái chết)  
- `left_trunc = 1` nếu spell đã bắt đầu trước 2012

### Ba bẫy phải xử lý

**1\. Left truncation.** Quan hệ đang chạy tại 2012 đã sống bao lâu rồi ta không biết. Bỏ qua sẽ làm lệch ước lượng duration dependence. Hai cách:

- (a) Kéo BACI HS2007 về 2007 chỉ để đếm tuổi khởi điểm — tốt hơn, phải nối concordance HS2007→HS2012  
- (b) Chỉ giữ spell bắt đầu ≥ 2013 — đơn giản hơn, mất mẫu

Khuyến nghị (a), nhưng làm (b) trước để có kết quả sớm.

**2\. Right censoring.** Spell còn sống ở 2024 phải đánh `censored = 1`, tuyệt đối không coi là `failure = 0` bình thường — đó là lỗi cơ bản mà reviewer sẽ bắt ngay.

**3\. Multiple spell.** Một cặp (c,p) có thể chết rồi hồi sinh. Không được coi các spell của cùng một cặp là quan sát độc lập → phải dùng **shared frailty theo cụm (c,p)** ở B5.

### Kiểm tra bắt buộc trước khi sang B3

✓ SUM(value\_usd) sau khi dựng grid \== tổng kim ngạch VN→EU trong BACI gốc

✓ Số spell \> 0, số failure \> 0, tỷ lệ failure trong khoảng 5–15%

✓ Không có spell nào có duration nhảy cóc (1, 2, 4\)

✓ Số ô trong grid \== 27 × n\_hs6 × 13

Nếu check 1 không khớp, dừng lại. Mọi thứ phía sau sẽ vô nghĩa.

---

## B3 — Feature engineering

### Nguyên tắc bắt buộc

**Mọi covariate lấy tại `t−1`.** Dùng giá trị cùng năm sẽ tạo simultaneity — quan hệ sắp chết thì kim ngạch năm đó đã giảm sẵn rồi, hệ số sẽ vô nghĩa về mặt nhân quả.

### Bốn nhóm biến

**Nhóm 1 — Đặc tính quan hệ**

| Biến | Công thức | Nguồn |
| :---- | :---- | :---- |
| `log_value_lag` | ln(value)ₜ₋₁ | BACI |
| `rca` | (Xᵥₙ,ₚ / Xᵥₙ) / (X\_world,ₚ / X\_world) | BACI |
| `market_share` | value(VN→c,p) / tổng nhập khẩu của c cho p | BACI |
| `unit_value` | v / q | BACI |
| `volatility_3y` | SD(ln value) 3 năm gần nhất | tính toán |
| `growth_lag` | Δln(value)ₜ₋₁ | tính toán |

**Nhóm 2 — Thị trường & gravity**

`log_gdp_d`, `log_gdpcap_d`, `log_pop_d`, `log_dist`, `contig`, `comlang_off`, và quan trọng: `log_total_import_cp` (tổng nhập khẩu của nước c cho sản phẩm p từ toàn thế giới — proxy cho cầu thị trường, tách khỏi hiệu ứng riêng của VN).

**Nhóm 3 — Chính sách**

| Biến | Ý nghĩa |
| :---- | :---- |
| `tariff_applied` | thuế thực áp dụng, % |
| `pref_margin` | MFN − applied |
| `staging_cat` | mã lộ trình EVFTA (A, B3, B5, B7, B10…) |
| `evfta_cut_cum` | mức cắt thuế tích lũy theo cam kết tại năm t |
| `years_since_evfta` | t − 2020, âm nếu trước |

**Nhóm 4 — Cấu trúc danh mục (economies of scope)**

- `n_products_to_c`: số sản phẩm VN đang xuất sang nước c  
- `n_markets_for_p`: số thị trường EU đang mua sản phẩm p từ VN  
- `hs2_share`: tỷ trọng của nhóm HS2 chứa p trong tổng XK sang c

Hai biến này bắt được logic "chi phí thâm nhập chìm được chia sẻ" — quan hệ nằm trong một cụm dày thì sống lâu hơn.

### Xử lý missing

- Thuế: carry-forward tối đa 2 năm, sau đó đánh dấu `tariff_imputed = 1` và đưa dummy này vào mô hình  
- Unit value: nhiều missing do `q` thiếu → chỉ dùng ở robustness, không đưa vào specification chính

---

## B4 — Phân tích mô tả

Trước khi ước lượng, phải nhìn dữ liệu. Bước này bắt lỗi B2 hiệu quả hơn bất kỳ unit test nào.

### Kaplan–Meier

from lifelines import KaplanMeierFitter

kmf \= KaplanMeierFitter()

kmf.fit(durations=spell\_df\['duration'\], event\_observed=spell\_df\['failure'\])

kmf.plot\_survival\_function()

R: `survival::survfit(Surv(duration, failure) ~ 1, data = spell_df)`

### Kỳ vọng phải thấy

**Negative duration dependence** — hazard cao nhất ở năm 1–2 rồi giảm dần. Đây là kết quả kinh điển trong literature (Besedeš & Prusa 2006; Nitsch 2009): quan hệ mới rất dễ chết, sống qua được 3 năm thì ổn định hẳn.

**Nếu không thấy pattern này, quay lại kiểm tra B2.** Gần như chắc chắn có lỗi ở gap rule hoặc left truncation.

### Cắt lát cần vẽ

- Theo nhóm ngành: dệt may (HS61-62), thủy sản (HS03), điện tử (HS85), da giày (HS64), nông sản (HS08-09)  
- Theo quy mô thị trường: Đức/Hà Lan/Pháp vs các nước nhỏ  
- Theo giai đoạn: spell bắt đầu trước 2020 vs sau 2020  
- Theo staging category: A (cắt ngay) vs B7/B10 (cắt dần)

Cái cuối cùng là **hình quan trọng nhất của Paper A** — nếu nhìn thấy khoảng cách giữa các đường KM theo staging category, identification ở B6 sẽ có sức thuyết phục.

### Bảng thống kê mô tả

Bảng 1 của bài báo: số quan hệ, số spell, median duration, tỷ lệ chết trong năm đầu, tỷ lệ censored — chia theo ngành và theo giai đoạn.

---

## B5 — Mô hình kinh tế lượng

### Đặc tả chính: discrete-time complementary log-log với shared frailty

h(t | X) \= 1 − exp( −exp( β'X\_{t−1} \+ γ(t) \+ u\_cp ) )

- `γ(t)`: duration dummies — baseline hazard phi tham số, không áp đặt dạng hàm  
- `u_cp`: shared frailty theo cụm (c,p) — xử lý multiple spell và unobserved heterogeneity

**Vì sao cloglog chứ không Cox?**

1. Dữ liệu theo năm là discrete-time thực sự, không phải continuous bị làm tròn  
2. Rất nhiều ties (hàng nghìn quan hệ chết cùng năm) — Cox xử lý ties kém  
3. Time-varying covariates (thuế đổi theo năm) vào tự nhiên trong khung person-period  
4. cloglog là discrete-time analogue của Cox PH → vẫn diễn giải được hệ số như hazard ratio

### Thang bậc đặc tả — chạy đủ 4, báo cáo cả 4

| Model | Biến |
| :---- | :---- |
| M0 | chỉ duration dummies |
| M1 | \+ đặc tính quan hệ |
| M2 | \+ gravity & thị trường |
| M3 | \+ chính sách thuế |

Cách trình bày này cho thấy hệ số nào ổn định, hệ số nào bị hút khi thêm control — reviewer rất thích.

### Thư viện

| Việc | R | Python |
| :---- | :---- | :---- |
| cloglog person-period | `glm(family=binomial(link="cloglog"))` | `statsmodels.GLM(family=Binomial(link=cloglog()))` |
| Shared frailty | `coxme`, `frailtyEM` | `lifelines` (cluster\_col) |
| Cox PH (so sánh) | `survival::coxph` | `lifelines.CoxPHFitter` |
| Competing risks | `cmprsk`, `mstate` | `lifelines` |
| SE cluster | `sandwich` \+ `lmtest` | `statsmodels` cov\_type='cluster' |

### Standard errors

Cluster **two-way theo nước nhập khẩu (c) và nhóm sản phẩm HS2**. Cluster một chiều theo c sẽ underestimate vì các sản phẩm cùng ngành có shock chung.

### Kết quả kỳ vọng (để tự kiểm tra)

- `log_value_lag`: hệ số âm mạnh — quan hệ lớn sống lâu hơn  
- `duration`: negative dependence  
- `n_products_to_c`: âm — economies of scope  
- `tariff_applied`: dương — thuế cao thì dễ chết  
- `volatility_3y`: dương

Nếu dấu ngược với kỳ vọng ở những biến này, gần như chắc chắn có lỗi ở B3 (quên lag) hoặc B2.

---

## B6 — Identification EVFTA

**Đây là khối quyết định bài lên được journal nào.** Phần còn lại của Stage 1 là công việc chuẩn; phần này là đóng góp.

### Vấn đề

Dùng dummy trước/sau 2020 sẽ bị reject ngay: EVFTA có hiệu lực 1/8/2020, đúng giữa COVID. Không cách nào tách được hai cú sốc nếu chỉ có biến thiên theo thời gian.

### Giải pháp: continuous treatment intensity từ staging schedule

EVFTA cắt thuế theo lộ trình **khác nhau cho từng dòng hàng** (category A cắt về 0 ngay; B3, B5, B7, B10 cắt dần). Điều này tạo ra biến thiên **giữa các sản phẩm trong cùng một năm, cùng một thị trường** — chính là thứ COVID không có.

h(t) \= 1 − exp(−exp( δ · (PrefMargin\_p × Post\_t)

                     \+ β'X\_{t−1} \+ γ(t)

                     \+ FE\_c \+ FE\_hs2 \+ FE\_t \+ u\_cp ))

`FE_t` hút toàn bộ cú sốc chung theo thời gian (COVID, suy thoái EU, đứt gãy logistics). Cái còn lại trong `δ` là hiệu ứng riêng của cường độ cắt thuế.

### Ba kiểm định bắt buộc

**1\. Event-study plot**

h(t) \= Σ\_{k=-5}^{+4} δ\_k · (PrefMargin\_p × 1\[t − 2020 \= k\]) \+ ...

Vẽ `δ_k` theo k. Các hệ số trước 2020 phải không khác 0 có ý nghĩa → **parallel pre-trend**. Đây là hình quan trọng nhất của bài.

**2\. Placebo** Giả định EVFTA có hiệu lực 2017, chạy lại. Hệ số phải bằng 0\.

**3\. Heterogeneity** Tương tác `PrefMargin × Post` với: tuổi quan hệ (quan hệ non nhạy hơn?), quy mô, ngành. Đây là chỗ trả lời câu hỏi "tác động bất đối xứng của chính sách" mà slide gốc đặt ra.

### Lưu ý kỹ thuật

Preference margin có thể nội sinh: EU cắt thuế mạnh cho những dòng hàng ít nhạy cảm với họ, mà những dòng đó có thể vốn dĩ đã ổn định. Cách xử lý: kiểm soát bằng `FE_hs2` và thảo luận thẳng trong phần limitation. Nếu muốn mạnh hơn, có thể dùng thuế MFN trước 2020 làm instrument cho mức cắt.

---

## B7 — Nhánh ML \+ XAI

### Nói rõ mục tiêu, nếu không reviewer sẽ nghĩ là trang trí

B5 hỏi **"tại sao chết"** — cần hệ số diễn giải được, unbiased. B7 hỏi **"dự báo được không"** — cần sức dự báo out-of-sample, không cần hệ số.

Hai mục tiêu khác nhau, báo cáo song song, không thay thế nhau. Đây là framing chuẩn cho journal AI-in-economics.

### Split theo thời gian, KHÔNG random

Train:    2012–2020

Validate: 2021–2022

Test:     2023–2024

Random split sẽ leak nghiêm trọng: các dòng cùng một spell dính chặt nhau, mô hình sẽ "nhìn thấy tương lai".

### Mô hình so sánh

| Model | Thư viện | Ghi chú |
| :---- | :---- | :---- |
| cloglog (baseline) | statsmodels | benchmark bắt buộc |
| Random Survival Forest | `scikit-survival` (`RandomSurvivalForest`) | mạnh, dễ tune |
| Gradient-boosted Cox | `scikit-survival` (`GradientBoostingSurvivalAnalysis`) | thường tốt nhất |
| DeepSurv | `pycox` | cần nhiều data |
| DeepHit | `pycox` | xử lý competing risks tốt |

pip install scikit-survival pycox torchtuples shap

### Metrics

- **Harrell's C-index** — khả năng xếp hạng đúng  
- **Time-dependent AUC** — theo từng horizon  
- **Integrated Brier Score** — calibration, quan trọng vì Stage 2 dùng `Ŝ` như xác suất thật

IBS quan trọng hơn C-index cho đề tài này: Stage 2 nhân `value × Ŝ`, nên `Ŝ` phải được calibrate đúng, không chỉ xếp hạng đúng.

### Class imbalance

Failure rate thường 5–15%. Cân nhắc: class weight, hoặc để nguyên và đánh giá bằng AUC/IBS thay vì accuracy.

### XAI — SHAP trên survival model

import shap

explainer \= shap.TreeExplainer(rsf\_model)

shap\_values \= explainer.shap\_values(X\_test)

Trả lời câu hỏi 2 của slide ("yếu tố nào quyết định rủi ro đứt gãy") ở **cấp từng quan hệ**, không chỉ trung bình mẫu. Ví dụ: quan hệ Tây Ban Nha × thủy sản có hazard cao chủ yếu do volatility, còn Ba Lan × da giày cao do market share thấp — hai khuyến nghị chính sách khác nhau.

### Hướng mở rộng: GNN

Coi mỗi quan hệ (VN, c, p) là cạnh trong đồ thị hai tầng (nước–nước, sản phẩm–sản phẩm). Embedding lan truyền qua nước láng giềng và sản phẩm liên quan. Đây là đóng góp phương pháp thật, và nó biện minh cho phần "network survivability" mà Stage 2 cần. Thư viện: `torch-geometric` hoặc `dgl`.

Để làm sau khi Paper A đã ổn — không đưa vào critical path.

---

## B8 — Robustness

Sáu kiểm định, mỗi cái một bảng phụ lục:

| \# | Kiểm định | Mục đích |
| :---- | :---- | :---- |
| 1 | Ngưỡng 5k / 10k / 50k USD | Kết quả có phụ thuộc định nghĩa "tồn tại"? |
| 2 | Gap rule 0 / 1 / 2 năm | Định nghĩa "chết" |
| 3 | Loại 2020–2021 | Tách COVID |
| 4 | Cox PH thay cloglog | Dạng hàm |
| 5 | Competing risks | Phân biệt "chết hẳn" vs "chuyển sang thị trường EU khác" |
| 6 | Mẫu 147 thị trường | Kết quả có riêng cho EU? |

Kiểm định 5 đáng chú ý: nếu VN ngừng xuất áo thun sang Ba Lan nhưng tăng sang Đức, đó không phải "mất quan hệ" theo nghĩa kinh tế mà là tái phân bổ. Phân biệt hai loại này làm bài sâu hơn hẳn — và nó chính là cầu nối tự nhiên sang Stage 2\.

---

## B9 — Xuất bảng bàn giao

### Sản phẩm cuối của Stage 1

handoff \= predict\_survival(best\_model, X\_2024)

handoff.to\_parquet("stage1\_output.parquet")

| Cột | Ý nghĩa | Dùng cho |
| :---- | :---- | :---- |
| `c`, `p`, `t` | khóa | join |
| `S_hat` | xác suất sống sót năm t+1 | trọng số rủi ro |
| `S_hat_lo`, `S_hat_hi` | khoảng tin cậy 95% | mô phỏng Monte Carlo ở Stage 2 |
| `value_expected` | giá trị kỳ vọng | tử số của hàm mục tiêu |
| `hazard_rank` | percentile rủi ro trong danh mục | xếp hạng |
| `shap_top3` | 3 yếu tố đóng góp lớn nhất | diễn giải khuyến nghị |
| `staging_cat` | lộ trình EVFTA | mô phỏng counterfactual |

`S_hat_lo/hi` là cột dễ quên nhất nhưng Stage 2 rất cần — không có nó thì không dựng được phân phối để tính CVaR.

### Sản phẩm phụ

- Bảng hệ số M0–M3 (Table 2 của Paper A)  
- Event-study plot (Figure 3\)  
- Bảng so sánh ML vs econometric (Table 4\)  
- Bộ dữ liệu spell VN–EU — **nên công bố trên Zenodo/Harvard Dataverse**, tự nó là một đóng góp và tăng citation

---

# PHẦN III — LỘ TRÌNH THỰC HIỆN

## Thứ tự ưu tiên

Tuần 1–2   B0 \+ B1        Chốt scope, tải dữ liệu, test API WITS

Tuần 3–6   B2  ★          Dựng spell — dồn lực ở đây

Tuần 7–8   B3 \+ B4        Features \+ mô tả, verify B2

Tuần 9–12  B5             Mô hình kinh tế lượng

Tuần 13–16 B6             Identification EVFTA

Tuần 17–20 B7             ML \+ XAI

Tuần 21–22 B8             Robustness

Tuần 23–24 B9 \+ viết      Bàn giao \+ draft Paper A

**Song song từ tuần 1:** parse Annex 2-A (1–2 tuần công, không chặn các bước khác nhưng B6 phụ thuộc vào nó).

## Ba việc nên làm ngay trong 2 tuần tới

1. **Tải BACI HS2012 bản 202601**, lọc VN→EU27, dựng grid và đếm thử số spell \+ số failure sau khi áp ngưỡng 10k. Nếu số event quá ít, phải hạ ngưỡng — biết sớm tốt hơn nhiều so với biết ở tháng thứ 4\.  
2. **Test `witstrainsr` với một nước, một năm** để đo mức độ thiếu dữ liệu thực tế trước khi cam kết trong thuyết minh.  
3. **Parse thử 100 dòng đầu Annex 2-A** để ước lượng công sức thật.

Kết quả ba việc này chính là phần "tính khả thi" thuyết phục nhất trong hồ sơ NAFOSTED.

## Cấu trúc work package cho proposal

| WP | Nội dung | Thời gian | Deliverable |
| :---- | :---- | :---- | :---- |
| WP1 | Xây dựng bộ dữ liệu panel \+ parse EVFTA staging | T1–T6 | Dataset công bố trên Zenodo |
| WP2 | Stage 1 — survival \+ identification | T7–T14 | Paper A (Q1/Q2) |
| WP3 | Stage 2 — portfolio ranking \+ simulation | T15–T22 | Paper B |
| WP4 | Dashboard cảnh báo sớm | T20–T24 | Sản phẩm chuyển giao |

**Điểm mạnh cần nhấn:** dữ liệu công khai, không phụ thuộc thu thập thực địa → rủi ro triển khai thấp; có sản phẩm chuyển giao cho Bộ Công Thương / VCCI.

**Điểm yếu cần chủ động xử lý:** hội đồng kinh tế sẽ hỏi "đóng góp lý thuyết kinh tế ở đâu, hay chỉ là áp dụng ML". Cần một mục riêng về cơ chế kinh tế — tại sao sunk cost và learning-by-exporting sinh ra negative duration dependence, và tại sao ưu đãi thuế tác động bất đối xứng lên các quan hệ khác nhau.

---

# PHẦN IV — STAGE 2 (PENDING)

Chưa triển khai. Ghi lại đây để giữ mạch, sẽ chi tiết hóa sau khi B9 hoàn thành.

**Contract đã chốt:** Stage 2 chỉ đọc `stage1_output.parquet`, không đụng vào dữ liệu thô.

**Hướng đề xuất (khiêm tốn, khả thi):** thay vì bài toán tối ưu phân bổ nguồn lực đầy đủ — vốn cần dữ liệu chi phí gia nhập/duy trì thị trường mà không nguồn public nào có — chuyển sang:

1. **Risk-adjusted ranking**: xếp hạng theo `E[value] × Ŝ`, so danh mục thực tế của VN với danh mục "hiệu quả"  
2. **Ràng buộc sinh tồn \= CVaR**: yêu cầu 5% kịch bản xấu nhất vẫn giữ ≥ X% kim ngạch. Mượn thẳng từ tài chính, có nền lý thuyết sẵn, reviewer quen thuộc  
3. **Counterfactual simulation**: nếu thuế tăng X%, bao nhiêu % kim ngạch rơi vào vùng hazard cao

Hướng tham vọng hơn (ước lượng sunk cost kiểu Das–Roberts–Tybout) để dành cho extension.

**Câu hỏi còn mở, cần thảo luận với hội đồng:**

- Định nghĩa toán học chính xác của "ngưỡng an toàn mạng lưới"  
- Hàm mục tiêu tối ưu số đo cụ thể nào  
- Lượng hóa các hành động Duy trì/Gia nhập/Rút lui qua các năm ra sao

---

## Phụ lục — Checklist môi trường

\# Python

pip install duckdb polars pyarrow pandas numpy

pip install lifelines scikit-survival pycox torchtuples

pip install statsmodels linearmodels shap

pip install world\_trade\_data wbdata

pip install camelot-py pdfplumber

\# R

install.packages(c("data.table", "duckdb", "survival", "coxme",

                   "frailtyEM", "randomForestSRC", "cmprsk",

                   "sandwich", "lmtest", "fixest", "WDI"))

devtools::install\_github("diegoacastro/witstrainsr")

Gợi ý: `fixest` (R) xử lý high-dimensional fixed effects rất nhanh — hữu ích cho B6 khi có `FE_c × FE_hs2 × FE_t`.  
