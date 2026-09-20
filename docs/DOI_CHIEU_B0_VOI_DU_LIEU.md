# Đối chiếu B0 (bản chốt của thầy) với dữ liệu đang có trên đĩa

*Viết 29/08/2026. Nguồn yêu cầu: `Stage1_Research_Framework.md` — PHẦN II, B0
đến B9. Mọi con số bên dưới đếm trực tiếp trên file trong workspace, không lấy
từ tài liệu cũ.*

> ✅ **Cập nhật 29/08/2026 — cả hai lỗ hổng ở §4 đã được lấp.** EVFTA staging
> schedule đã parse (9.394 dòng CN8, kiểm chứng với TRAINS lệch 0,17 pp) và
> thuế EU 2022–2025 đã đủ (100% episode EU27 mọi năm). Chi tiết cách lấy, cách
> kiểm chứng và phần còn sai lệch:
> [DU_LIEU_EVFTA_VA_THUE_EU.md](DU_LIEU_EVFTA_VA_THUE_EU.md). Phần dưới giữ
> nguyên như lúc viết, để đối chiếu được trước–sau; §4 có ghi chú cập nhật.

---

## 1. Trả lời một màn hình

**Có cần lấy thêm dữ liệu không? — Có, nhưng chỉ đúng hai thứ.**

```
CẦN LẤY THÊM (chặn B6 — khối identification, tức khối quyết định journal)
  1. EVFTA Annex 2-A staging schedule            ❌ chưa có gì cả
  2. Thuế EU áp cho VN 2022–2025 (MFN + ưu đãi)  ❌ TRAINS không phát hành

KHÔNG CẦN LẤY THÊM — đã có đủ, chỉ cần dựng lại theo tham số B0
  Thương mại VN×EU27×HS6×năm 2002–2025          ✅ đủ 27/27 nước, đủ mọi năm
  Mẫu số nhập khẩu thế giới theo (nước, sản phẩm) ✅ có → log_total_import_cp
  Gravity, GDP, dân số, RTA                      ✅ 100% độ phủ
  Thuế 2003–2023                                 ✅ 100% EU27, đo đúng năm
  Spell / duration / event / censoring           ✅ đã dựng, cần chỉnh 2 tham số
  Kaplan–Meier + baseline hazard                 ✅ đã chạy thử, dấu đúng kỳ vọng

QUYẾT ĐỊNH CẦN THẦY/NHÓM CHỐT (không phải vấn đề dữ liệu)
  BACI hay Comtrade?   ·   HS2012 hay product family H0?   ·   ngưỡng one-shot
```

Nói gọn: **phần thu thập nặng nhọc đã xong từ tháng 8**, và nó phủ rộng hơn B0
yêu cầu (147 nước thay vì 27, 2002–2025 thay vì 2012–2024). Cái thiếu không phải
dữ liệu nền, mà đúng **biến treatment của bài** — lộ trình cắt thuế EVFTA và mức
thuế EU thật sự áp cho hàng Việt Nam ở bốn năm cuối.

---

## 2. B0 chốt gì, trên đĩa có gì

| Tham số B0 | Giá trị thầy chốt | Trên đĩa | Trạng thái |
|---|---|---|---|
| Exporter | Việt Nam | `exporter = VNM` duy nhất | ✅ khớp |
| Importer | EU-27 | **27/27 nước**, mọi năm 2002–2025 đều có file | ✅ khớp (còn dư 120 nước khác) |
| Đơn vị sản phẩm | HS6 bản **HS2012** | HS6 gốc theo revision nước khai (H0…H6) + **product family khoá theo H0** | ⚠️ **lệch quy ước** — xem §5.1 |
| Khung thời gian | 2012–2024 | **2002–2025** | ✅ bao trùm, dư 10 năm trước và 1 năm sau |
| Đơn vị quan sát | (c, p) × năm | `importer × product_family × year` | ✅ khớp |
| Cấp phân tích | Quốc gia | quốc gia | ✅ khớp |
| Ngưỡng tồn tại | ≥ 10.000 USD/năm | `THRESHOLD_USD = 10_000` | ✅ khớp, **và đã có bảng độ nhạy 1k/10k/50k/100k/500k** |
| Quy tắc gap | gián đoạn **1 năm** không tính là chết | `GAP_TOLERANCE = 0` | ❌ **lệch** — xem §5.2 |
| Left truncation | kéo về 2007 để đếm tuổi khởi điểm | có dữ liệu thật từ **2002**, nhưng script đang **loại bỏ** spell left-censored | ⚠️ **dựng lại là xong, và tốt hơn cách thầy đề xuất** — §5.3 |
| Mẫu mở rộng | UK tách riêng, 147 thị trường robustness | GBR có đủ 2002–2025 (15.192 episode); 147 nước có sẵn | ✅ **đã có sẵn cả hai** |

**Quy mô mẫu chính theo đúng scope B0** (EU-27, 2012–2024, ngưỡng 10k, đếm trên
`analysis/episodes.csv`):

| Chỉ số | Giá trị |
|---|---|
| Episode-năm | **123.465** |
| Số sự kiện chết quan sát được | **24.710** (20,0% episode-năm) |
| Cặp (nước × sản phẩm) riêng biệt | **23.850** |
| Nhóm sản phẩm | **3.168** |
| Tổng kim ngạch trong cửa sổ | **327 tỷ USD** |

Cả mẫu EU-27 xuyên suốt 2003–2025: **176.277 episode-năm · 52.024 spell ·
37.511 chết · 14.513 right-censored**.

> ⚠️ **Một con số cần chú ý ngay:** tỷ lệ chết 20,0%/năm **cao hơn khoảng
> 5–15% mà B5 nói là dấu hiệu lành mạnh**. Nguyên nhân gần như chắc chắn là
> `GAP_TOLERANCE = 0`: một năm tụt dưới ngưỡng rồi quay lại đang bị đếm thành
> một cái chết cộng một lần tái sinh. Áp đúng quy tắc gap 1 năm của B0 sẽ kéo
> con số này xuống. Đây là lý do đủ mạnh để dựng lại spell trước khi chạy B5.

---

## 3. Đi từng bước B1 → B9

### B1 — Thu thập & nạp dữ liệu

| B1 yêu cầu | Trên đĩa | Trạng thái |
|---|---|---|
| **B1.1 BACI (CEPII) 202601 HS2012** | ❌ chưa tải. Thay vào đó là **Comtrade khai từ phía nước nhập** — 3.306 file, 1.687.841 bản ghi HS6, 1.473.471 ô (nước × HS6 × năm) | ⚠️ **khác nguồn, không phải thiếu dữ liệu** — §5.1 |
| **B1.2 CEPII Gravity 202211** | ✅ `data_raw/gravity/Gravity_csv_V202211.zip` → `analysis/gravity_vn.csv`, 20 cột (`dist`, `distw_harmonic`, `contig`, `comlang_off`, `comcol`, `wto_d`…), 100% độ phủ | ✅ |
| B1.2b nối GDP/dân số 2021–2024 từ WDI | ✅ `macro_panel_v2.csv` — 3.404 country-year, 17 biến, **tới 2025** | ✅ **đã làm, còn vượt yêu cầu** |
| **B1.3 WITS/TRAINS thuế** | ✅ 2.482 biểu MFN / 134 reporter, **2002–2023**; EU27 đo đúng năm 100% cho 2007–2023 | ⚠️ **thủng 2024–2025** — §4.2 |
| thuế ưu đãi + `preference_margin` | ⚠️ EU chỉ có bản ưu đãi ở **2020 (7.826 episode) và 2021 (8.791)**; 2022–2025 TRAINS trả 404 | ❌ **thiếu đúng đoạn cần nhất** |
| **B1.4 EVFTA Annex 2-A staging** | ❌ **không có gì**: không PDF, không script parse, không bảng `HS8 → staging_category` | ❌ **lỗ hổng lớn nhất** |
| Output: 4 file parquet | có CSV tương đương (`panel_final.csv`, `gravity_vn.csv`, tariff trong `data_raw/tariffs/`) | ⚠️ định dạng CSV, không phải parquet |

Ngoài yêu cầu B1, workspace còn có sẵn: nhập khẩu thế giới theo (nước × HS6 ×
năm) — **3.350 file, đúng thứ B3 gọi là `log_total_import_cp`**; mirror khai
báo của chính Việt Nam; 6 bảng concordance H1→H0 … H6→H0.

### B2 — Dựng spell ★

Bảy bước của B2 đã được `scripts/build_spells.py` thực hiện đủ, chỉ lệch tham số:

| Bước B2 | Trạng thái |
|---|---|
| 1. Lọc VN → EU27 | ✅ (script đang chạy trên cả 147 nước; lọc EU27 là một dòng) |
| 2–3. Expand full grid + điền 0 | ✅ — đúng cách xử lý "BACI/Comtrade không ghi dòng giá trị 0" |
| 4. Ngưỡng 10k → `active` | ✅ |
| 5. Gap rule | ❌ **đang là 0 năm, B0 yêu cầu 1 năm** |
| 6. `spell_id` | ✅ |
| 7. duration / failure / censored / left_trunc | ⚠️ có `duration`, `event`, `right_censored`, `t_start`, `t_stop`; **không có cờ `left_trunc`** vì spell left-censored đang bị **loại bỏ** |

Ba cái bẫy B2 nêu, đối chiếu:

1. **Left truncation** — B0 đề xuất kéo BACI HS2007 về 2007 để đếm tuổi. **Ta có
   dữ liệu thật từ 2002**, tức là với cửa sổ 2012–2024 thì tuổi khởi điểm của
   mọi spell đang chạy tại 2012 đều **quan sát được, không phải ước lượng**. Đây
   là chỗ workspace **mạnh hơn** thiết kế B0. Việc phải làm chỉ là đổi từ "loại
   bỏ" sang "giữ lại và gắn cờ `left_trunc`".
2. **Right censoring** — ✅ đã xử lý đúng, còn có thêm **kiểm duyệt hành chính**
   cho nước ngừng nộp báo cáo (Nga, Belarus…), thứ B0 chưa nghĩ tới nhưng cần.
3. **Multiple spell** — ✅ dữ liệu có sẵn nhiều spell trên cùng cặp (c,p);
   frailty theo cụm (c,p) chạy được ngay, **chưa chạy**.

Bốn kiểm tra bắt buộc trước khi sang B3: đã có cơ chế tương đương trong
`build_spells.py` (đối chiếu tổng kim ngạch, guard giữ lại importer có lỗ tải,
báo cáo interior gap). Riêng **"tỷ lệ failure 5–15%"** thì **chưa đạt** (20,0%)
— xem cảnh báo ở §2.

### B3 — Feature engineering

**Nguyên tắc "mọi covariate lấy tại t−1": panel hiện lưu giá trị cùng năm, chưa
có cột nào hậu tố `_lag`.** Việc lag là một bước trong script mô hình, rẻ, nhưng
**bắt buộc phải làm** — nếu quên thì mọi hệ số B5 vô nghĩa.

| Nhóm | Biến B0 yêu cầu | Trạng thái |
|---|---|---|
| 1. Đặc tính quan hệ | `log_value_lag` | ✅ `import_value_usd` (lag khi mô hình hoá) |
| | `rca` | ✅ có, đúng mẫu số thế giới, p25 0,23 / med 0,83 / p75 2,94 |
| | `market_share` | ✅ `vn_market_share_pct`, 100% |
| | `unit_value` | ✅ `unit_value_usd_per_kg`, 96,5% |
| | `volatility_3y` | ❌ **chưa tính** (tính được từ panel, không cần tải gì) |
| | `growth_lag` | ⚠️ có `country_growth_pct`, `world_growth_pct` — chưa lag |
| 2. Thị trường & gravity | `log_gdp_d`, `log_gdpcap_d`, `log_pop_d`, `log_dist`, `contig`, `comlang_off` | ✅ đủ cả sáu, 100% |
| | `log_total_import_cp` | ⚠️ **chưa có cột**, nhưng mẫu số đã trên đĩa (`data_raw/trade_world/`) — chỉ là một phép join |
| 3. Chính sách | `tariff_applied` | ⚠️ ✅ tới 2023, ❌ 2024–2025 |
| | `pref_margin` | ❌ **chưa có** — cần cả MFN lẫn applied ở cùng năm |
| | `staging_cat` | ❌ **chưa có nguồn** |
| | `evfta_cut_cum` | ❌ **chưa có nguồn** |
| | `years_since_evfta` | ✅ `years_since_fta` (EVFTA 2020 gắn cho cả 27 nước) |
| 4. Cấu trúc danh mục | `n_products_to_c`, `n_markets_for_p`, `hs2_share` | ❌ **chưa tính**; có `hhi_market`, `hhi_product`, `partner_share_pct`, `product_share_pct` là họ hàng gần. Tính được hoàn toàn từ panel |

**Kết luận B3: mọi thứ thiếu ở nhóm 1, 2, 4 đều tính được từ dữ liệu đang có,
không cần tải thêm. Chỉ nhóm 3 (chính sách) là bị chặn bởi nguồn.**

### B4 — Phân tích mô tả — ✅ đã chạy, kết quả đúng kỳ vọng

- `analysis/km_survival.csv` — Kaplan–Meier toàn mẫu: S(1) ≈ **53,1%**,
  S(2) ≈ 38,9%, S(5) ≈ 25,3%, S(10) ≈ 18,9%.
- `analysis/hazard_baseline.csv` — hazard ratio theo duration: 0,447 → 0,266 →
  0,185 → … → 0,048 ở 10+ năm. **Negative duration dependence rõ ràng, đúng thứ
  B4 nói phải thấy** (Besedeš–Prusa). Tức là B2 không sai về cơ bản.
- `analysis/threshold_sensitivity.csv` — 5 mức ngưỡng, đã có sẵn cho B8 #1.
- ❌ **Chưa vẽ**: cắt lát theo ngành, theo quy mô thị trường, theo giai đoạn, và
  **theo staging category** — cái cuối là "hình quan trọng nhất của Paper A"
  theo lời B4, và nó bị chặn bởi cùng một lỗ hổng EVFTA.

### B5 — Mô hình kinh tế lượng — ⏳ mới có bản chạy thử

`hazard_baseline.csv` là một lần chạy nháp trên toàn mẫu 147 nước, **không lag,
không FE, không frailty, không cluster**. Không được dùng làm kết quả.

Một dấu hiệu đáng ngờ đã lộ ra ngay trong bản nháp đó: `log_tariff_1p` có
**hệ số âm** (HR 0,987), trong khi B5 nói dấu kỳ vọng phải **dương**. Ba cách
giải thích, phải loại trừ theo thứ tự: (a) chưa lag t−1; (b) chưa có FE nước và
FE ngành nên thuế đang bắt lấy hiệu ứng cơ cấu; (c) thuế đo sai vì phần lớn ưu
đãi FTA nằm dưới mã nhóm mà TRAINS không công bố. Không nên coi đây là kết quả
kinh tế trước khi ba việc trên xong.

Thang M0→M3, cloglog + shared frailty, cluster two-way (c, HS2): **chưa chạy**.

### B6 — Identification EVFTA — ❌ **bị chặn hoàn toàn**

Đây là khối B0 gọi là "quyết định bài lên được journal nào", và nó là khối
**duy nhất trong toàn Stage 1 mà workspace không có dữ liệu để bắt đầu**:

- `staging_cat` và `evfta_cut_cum`: không có nguồn nào trên đĩa.
- `PrefMargin_p × Post_t`: preference margin cần applied tariff **và** MFN ở
  cùng năm. EU chỉ có biểu ưu đãi 2020 và 2021 → treatment intensity chỉ dựng
  được cho **2 năm sau hiệp định**, quá ngắn cho event-study ±4 năm mà B6 đòi.
- Event-study, placebo 2017, heterogeneity: đều phụ thuộc hai thứ trên.

Nói thẳng: **không parse được Annex 2-A thì không có Paper A theo thiết kế của
thầy** — chỉ còn một bài survival mô tả, tức là đúng thứ B0 cảnh báo là "công
việc chuẩn, không phải đóng góp".

### B7 — ML + XAI — ⏳ chưa chạy, nhưng không thiếu gì

Split theo thời gian (train 2012–2020 / valid 2021–2022 / test 2023–2024) khớp
đúng với dữ liệu đang có. RSF / GBM / DeepHit / SHAP đều chạy được trên
`panel_final.csv` ngay hôm nay. Không có hạng mục dữ liệu nào chặn B7.

### B8 — Robustness — 1/6 đã có sẵn

| # | Kiểm định | Trạng thái |
|---|---|---|
| 1 | Ngưỡng 5k/10k/50k | ✅ **đã có** `threshold_sensitivity.csv` (5 mức) |
| 2 | Gap rule 0/1/2 năm | ⏳ chạy lại `build_spells.py` ba lần, rẻ |
| 3 | Loại 2020–2021 (tách COVID) | ⏳ thuần mô hình |
| 4 | Cox PH thay cloglog | ⏳ panel đã ở dạng counting-process, chạy thẳng được |
| 5 | Competing risks | ⏳ dữ liệu đủ (biết quan hệ chết ở nước này có mọc ở nước khác không) |
| 6 | **Mẫu 147 thị trường** | ✅ **đã có sẵn toàn bộ** — đây là mẫu gốc của workspace |

### B9 — Bảng bàn giao — ⏳ chưa dựng

Bảy cột đích: `c, p, t` ✅ · `S_hat`, `S_hat_lo/hi`, `hazard_rank`, `shap_top3`
đều là output của B5/B7 chưa chạy · `value_expected` ✅ có từ panel ·
`staging_cat` ❌ chặn bởi EVFTA.

---

## 4. Hai thứ thật sự cần lấy thêm

> ✅ **Cả hai đã lấy xong ngày 29/08/2026.** Giữ nguyên phần mô tả dưới đây vì
> nó là lý do tại sao phải đi lấy; kết quả nằm ở
> [DU_LIEU_EVFTA_VA_THUE_EU.md](DU_LIEU_EVFTA_VA_THUE_EU.md).

### 4.1. EVFTA Annex 2-A staging schedule — ưu tiên tuyệt đối

| | |
|---|---|
| Vì sao cần | Là **biến treatment** của B6, là biến `staging_cat` của B3 và B9, là biến chia nhóm cho hình KM quan trọng nhất của B4 |
| Trên đĩa | Không có gì |
| Nguồn | Annex 2-A của EVFTA (PDF) — Trung tâm WTO VCCI `trungtamwto.vn`; đối chiếu từng dòng qua EU Access2Markets → My Trade Assistant |
| Việc phải làm | parse PDF → bảng `HS8 → staging_category → lộ trình thuế theo năm`, rồi gộp lên HS6 |
| Công cụ | `camelot` (bảng có đường kẻ) + `pdfplumber` (bảng không đường kẻ) |
| Công sức | thầy ước 1–2 tuần, cần verify tay một mẫu ngẫu nhiên |
| Ai làm | **máy làm được**, không cần tài khoản, không cần trả tiền |

Một điểm nên nói với thầy: bảng này **chưa ai công bố ở dạng
machine-readable** — nên bản thân nó là một sản phẩm nghiên cứu, hợp để đưa vào
WP1 và công bố kèm dataset trên Zenodo.

### 4.2. Thuế EU áp cho Việt Nam, 2022–2025

| | |
|---|---|
| Vì sao cần | `pref_margin = MFN − applied` là biến chính của B6; thiếu bốn năm cuối thì cửa sổ hậu-EVFTA chỉ còn 2020–2021 |
| Trên đĩa | MFN đủ và đo đúng năm tới **2023**; ưu đãi cho EU **chỉ 2020 và 2021** |
| Vì sao thiếu | TRAINS trả 404: không phát hành biểu ưu đãi nào cho 2022–2023 (đã hỏi thẳng JPN/KOR/IND/EUN), và không phát hành gì cho 2024–2025 |
| Đường đi thay thế | (a) **dựng applied tariff từ chính lịch staging EVFTA + MFN nền** — tự nhất quán, và đúng thứ B6 cần; (b) EU TARIC / Access2Markets công bố thuế theo dòng và theo năm; (c) WTO Tariff Download Facility cho MFN 2024–2025 |
| Khuyến nghị | làm **(a) + (b)**: (a) cho biến treatment, (b) để kiểm chứng chéo một mẫu |

Lưu ý: hướng (a) chỉ khả thi **sau khi** có Annex 2-A — nên hai việc ở §4.1 và
§4.2 thực chất là một chuỗi, không song song được.

---

## 5. Ba chỗ lệch quy ước — cần thầy chốt, không phải cần tải thêm

### 5.1. Nguồn thương mại: BACI hay Comtrade?

B0 chốt **BACI 202601 HS2012**. Workspace dùng **Comtrade khai từ phía nước
nhập khẩu**, đã hoàn tất.

| | BACI (B0 chốt) | Comtrade (đang có) |
|---|---|---|
| Bản chất | đã hoà giải hai chiều khai báo, ước lượng lại giá FOB | khai báo thô của nước nhập (CIF) |
| Năm | tới ~2024 | **2002–2025** (27/27 nước EU đủ cả 2025) |
| Nomenclature | HS2012 thống nhất | HS gốc từng nước (H0…H6) + product family |
| Khối lượng | `q` thiếu nhiều | `net_weight_kg` phủ **96,5%** |
| Chi phí chuyển đổi | phải tải + dựng lại toàn bộ pipeline | 0 |

**Khuyến nghị:** giữ Comtrade làm mẫu chính (đã xong, có 2025, có khối lượng
tốt hơn), **tải BACI làm kiểm chứng chéo** cho một vài năm và báo cáo mức lệch
trong phụ lục. Nếu thầy nhất định muốn BACI làm nguồn chính thì phải chấp nhận
mất năm 2025 và dựng lại từ B2.

### 5.2. Gap rule: 0 hay 1 năm?

Đang là **0**, B0 chốt **1**. Đây là một hằng số trong
`scripts/build_spells.py` (`GAP_TOLERANCE`). Chạy lại là xong. **Nên đổi** — vừa
tuân B0, vừa nhiều khả năng kéo tỷ lệ chết 20% về khoảng 5–15% mà B5 mong đợi,
đồng thời cho luôn kiểm định B8 #2 (chạy cả ba giá trị 0/1/2).

### 5.3. Left truncation: bỏ hay giữ?

Script đang **loại bỏ** spell đã chạy từ năm đầu cửa sổ (13.178 spell ở ngưỡng
10k trên toàn mẫu). Với cửa sổ B0 là 2012–2024 mà dữ liệu có từ 2002, cách đúng
là **giữ lại, gắn cờ `left_trunc`, và lấy tuổi thật đếm từ 2002** — mạnh hơn cả
phương án (a) của B0 (kéo BACI HS2007 về 2007), vì tuổi là quan sát được chứ
không phải suy ra qua concordance.

### 5.4. Bonus — quyết định B0 chưa đụng tới nhưng sẽ đổi ý nghĩa hazard

**52,7% spell chỉ sống đúng 1 năm** và con số này **không biến mất khi nâng
ngưỡng lên 500.000 USD** (vẫn 41,9%). Ở ngưỡng 10k, phần lớn "quan hệ" là lô
hàng một lần. Phải chốt: giữ nguyên, nâng ngưỡng, hay tách nhóm one-shot ra mô
hình riêng. Đây không phải vấn đề dữ liệu, nhưng nó **đổi hoàn toàn ý nghĩa
kinh tế của hazard ước lượng được**, nên nên hỏi thầy sớm.

---

## 6. Đang có sẵn nhưng B0 không yêu cầu

Những thứ này đã tốn công thu thập; không nên vứt, nhưng cũng **không nên để
chúng kéo Stage 1 chệch khỏi mạch B0**. Xếp theo mức hữu ích cho Paper A:

| Tài sản | Dùng được vào đâu trong Stage 1 |
|---|---|
| **Mẫu 147 thị trường**, 2002–2025 | B8 #6 — kiểm tra kết quả có riêng cho EU không. **Đúng thứ B0 gọi là mẫu mở rộng** |
| **GBR 2002–2025** | mẫu Brexit tách riêng mà B0 yêu cầu |
| NTM ở HS6 × năm (`ntm6_*`, 95,2% episode) | control chất lượng cao cho B5/B8 — hàng rào phi thuế là biến gây nhiễu kinh điển của tác động thuế |
| Product complexity PCI (100%) | biến giải thích cho B5, và feature tốt cho B7 |
| Gravity đầy đủ 20 cột | ✅ đã dùng, đúng nhóm 2 của B3 |
| Trade remedies (AD/CVD) | control, nhưng **initiation dừng 2015** — phải kiểm duyệt biến ở 2015 |
| CBAM scope EU | không thuộc Stage 1; để dành Stage 2 / counterfactual |
| Thuế đối ứng Mỹ 2025 | **ngoài scope B0** (B0 chốt importer = EU-27). Giữ cho một bài khác |
| GLPI (4 biến thể) | robustness; độ phủ chỉ 22–25% country-year |

---

## 7. Việc nên làm, theo thứ tự

1. ~~**Bắt đầu parse Annex 2-A ngay hôm nay.**~~ ✅ **Xong 29/08/2026** —
   `analysis/evfta_staging_family.csv` khớp 99,4% episode EU27. Đường găng đã
   thông; B4 (hình KM theo staging) và B6 chạy được ngay.
2. **Dựng lại spell theo đúng tham số B0** — `GAP_TOLERANCE = 1`, giữ spell
   left-truncated và gắn cờ, lọc EU-27, cửa sổ 2012–2024 nhưng dùng lịch sử
   2002–2011 để đếm tuổi. Chạy luôn cả ba giá trị gap để có sẵn B8 #2.
3. **Kiểm tra lại tỷ lệ failure** sau bước 2. Nếu vẫn ngoài 5–15%, dừng lại soi
   B2 trước khi đi tiếp — đúng như B2 dặn.
4. **Bổ sung 5 biến còn thiếu của B3** (`volatility_3y`, `log_total_import_cp`,
   `n_products_to_c`, `n_markets_for_p`, `hs2_share`) và **lag toàn bộ về t−1**.
5. **Vẽ đủ bộ KM của B4** theo ngành / quy mô / giai đoạn (hình theo staging
   phải chờ bước 1).
6. **Chạy M0→M3 của B5** với cloglog + frailty (c,p) + cluster two-way, và giải
   thích cho được dấu của `tariff_applied`.
7. Chốt với thầy ba câu hỏi ở §5 — BACI/Comtrade, HS2012/product family,
   one-shot spell.

Bước 1 và bước 2 chạy song song được: bước 2 không cần dữ liệu EVFTA.
