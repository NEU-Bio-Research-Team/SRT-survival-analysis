# Structured Review — Từ literature review đến benchmark sống sót quan hệ xuất khẩu Việt Nam × EU-27 (khung B0)

> **Phạm vi.** Tài liệu nối liền hai tầng: **(i) literature review của bốn seed papers → (ii) các quyết định thực tế trong benchmark `eu27_v3`**, rồi báo cáo theo mạch **Research framing → Literature review → Data → Models → Metrics → Results**. Mẫu chính theo khối B0 của [`Stage1_Research_Framework.md`](../../Stage1_Research_Framework.md): **Việt Nam × EU-27 (không gồm UK) × HS6/product family × prediction origin 2012–2024**, với lộ trình cắt thuế EVFTA là biến chính sách trung tâm.
>
> **Trạng thái.** Hai run:
> - `eu27_v3`: 11 mô hình × 6 tập feature × 3 fold = **198 cells**, dùng cho leaderboard.
> - `eu27_v3_evfta1y`: 11 × 6 × 1 fold = **66 cells**. Đây là fold phụ, chỉ chấm ở chân trời 1 năm, để kiểm tra biến EVFTA.
>
> Cả hai run đã chạy xong ngày 16/09/2026; bảng tổng hợp nằm ở [`benchmark/reports/eu27_v3/`](../benchmark/reports/eu27_v3/) (fold phụ: `evfta1y/`). Bốn mô hình Phase 4 (DeepPAMM, ORSF, DSM, SurvTRACE) chưa chạy. Những điểm còn lệch so với B0 và cần thầy quyết định được tóm tắt ở §3.1bis.

---

## 1. Outline

1. [Literature review và truy vết vào benchmark](#2-literature-review-và-truy-vết-vào-benchmark)
   - Vai trò khác nhau của bốn seed papers
   - Paper nào đóng góp feature, model, metric và contrast nào
   - Nội dung nào được chuyển thể, loại bỏ hoặc chưa triển khai
2. [Data](#3-data)
   - Dataset, lớp lọc scope và đối chiếu với B0
   - Đơn vị quan sát, input, target và output
   - Cửa sổ thời gian, chống leakage và chia fold
   - Sáu tập feature F0–F5, các biến EVFTA, feature bị loại
3. [Models](#4-models)
   - 11 mô hình theo họ và theo giả định PH / non-PH
   - Các contrast thiết kế trước, ngân sách huấn luyện
4. [Metrics](#5-metrics)
   - Quy ước censoring dùng thống nhất cho mọi metric
   - Brier/IBS, Antolini C, dynamic AUC, ECE, bootstrap
5. [Results](#6-results)
   - Xếp hạng theo tập feature, leaderboard, ablation
   - Độ ổn định qua fold (trước EVFTA / COVID / sau EVFTA)
   - Contrast kiến trúc, nhóm tuổi quan hệ, calibration
   - Fold phụ EVFTA (1 năm)
   - Kết luận, giới hạn, lịch sử phiên bản

### Câu hỏi nghiên cứu trung tâm

Khi mọi mô hình nhận **cùng một tập covariates đã kiểm soát leakage** trên mẫu **VN × EU-27 × 2012–2024**, mô hình phi tuyến và/hoặc non-proportional-hazards có cải thiện độ phân biệt và độ hiệu chuẩn của xác suất sống sót so với hazard model truyền thống hay không? Câu hỏi phụ: biến cường độ cắt thuế EVFTA có thêm thông tin dự báo hay không?

### Kết quả chính (tổng hợp ngày 17/09/2026, chi tiết ở §6)

- **Không mô hình nào thắng CoxPH một cách nhất quán.** Trên tập đầy đủ, RSF đứng đầu với IBS 1–3y = 0,1012, CoxPH đứng thứ hai với 0,1015; khoảng cách 0,0003 nhỏ hơn biến thiên giữa các fold. Trên F0–F3 và F0–F4 (hai tập có bootstrap), CoxPH đứng #1. RSF chỉ tốt hơn CoxPH có ý nghĩa ở fold 1 của F0–F3, và kém hơn có ý nghĩa ở 3/6 cặp (tập, fold) (§6.6).
- **Thông tin dự báo đến gần như toàn bộ từ F1** (quy mô/sức mạnh quan hệ): thêm F1 vào F0 giảm IBS khoảng 0,005–0,009 ở các mô hình ổn định. F2 và F3 chỉ thêm ≤ 0,0013 cho CoxPH; F4 và F5 không thêm gì (§6.4).
- **Contrast rõ nhất:** RSF tốt hơn BoostedCox ở 16/18 cells (bỏ PH trong họ cây). Thêm phi tuyến nhưng giữ PH (BoostedCox) thì kém CoxPH ở cả 18/18 cells; spline và tương tác lý thuyết (Cloglog-theory) kém Cloglog ở 18/18 (§6.7).
- **Calibration:** RSF có ECE 1y thấp nhất (0,0167). KM không dùng covariate nhưng có ECE 3y thấp nhất (0,0287), tốt hơn cả 10 mô hình có covariate ở 3 năm (§6.10).
- **Fold phụ EVFTA:** thêm block F4 **không cải thiện có ý nghĩa** Brier 1y ở mô hình nào; 6/10 mô hình có covariate còn **kém đi có ý nghĩa** (§6.9).

---

## 2. Literature review và truy vết vào benchmark

### 2.1. Nguyên tắc tổng hợp

Bốn seed papers không đóng cùng một vai trò. Hai paper thương mại định hình **biến giải thích và baseline kinh tế lượng**; hai paper phương pháp định hình **không gian mô hình và cách đánh giá**:

\[
\underbrace{\text{Nitsch; Lawless \& Studnicka}}_{\text{trade-survival}}
\longrightarrow
\text{feature universe + econometric baselines},
\]

\[
\underbrace{\text{Islam et al.; Birolo et al.}}_{\text{survival methods/benchmark}}
\longrightarrow
\text{model universe + evaluation protocol}.
\]

Vì vậy, benchmark không lấy biến lâm sàng/synthetic từ hai paper phương pháp; ngược lại, nó không xem hai paper thương mại là bằng chứng rằng một kiến trúc deep learning cụ thể sẽ tốt hơn. Mọi mô hình được so sánh trên **cùng tập thông tin**, để chênh lệch kết quả phản ánh thuật toán thay vì ưu thế feature.

### 2.2. Bốn seed papers

#### 2.2.1. Nitsch (2007/2009) — *Die Another Day: Duration in German Import Trade*

Nitsch nghiên cứu duration của quan hệ nhập khẩu ở cấp nước xuất khẩu × sản phẩm CN8 × Đức. Paper dùng Kaplan–Meier và Cox proportional hazards phân tầng; đóng góp quan trọng nhất cho dự án này là logic về quy mô ban đầu, quy mô hiện tại, thị phần nhà cung cấp, quy mô thị trường, unit value và các biến gravity. Kết quả nền tảng là quan hệ có giá trị ban đầu/thị phần lớn hơn và chi phí thương mại thấp hơn thường có hazard thấp hơn.

**Đưa vào benchmark:** KM và CoxPH; phần lớn F1; lõi gravity của F2. Việc chuyển từ “nhiều exporter bán vào Đức” sang “Việt Nam bán vào nhiều nước EU” là một **chuyển thể theo cơ chế kinh tế**, không phải sao chép nguyên xi thiết kế mẫu của paper.

#### 2.2.2. Lawless & Studnicka (2024) — *Old Firms and New Export Flows: Does Experience Increase Survival?*

Paper nghiên cứu flow mới ở cấp firm × product × destination bằng discrete-time complementary-log-log với random effects. Đóng góp trung tâm là phải đọc experience cùng diversification, proximity với năng lực lõi và các tương tác; hệ số experience đứng riêng có thể gây hiểu sai vì doanh nghiệp giàu kinh nghiệm cũng thử nghiệm các flow cận biên hơn.

**Đưa vào benchmark:** Cloglog có gamma frailty; block F3 về kinh nghiệm/đa dạng hóa; biến launch value trong F1; và các tương tác theory-informed trong Cloglog-theory. Do dữ liệu SRT không có firm, các khái niệm firm-level được **chuyển thể** sang cấp Việt Nam × sản phẩm × thị trường, xem §3.7 và §2.3.

#### 2.2.3. Islam et al. (2024) — *Case-Base Neural Network*

Islam et al. đưa thời gian trực tiếp vào neural hazard, cho phép học baseline hazard phức tạp, covariate–time interactions và higher-order interactions mà không phải chỉ định thủ công. Paper so sánh CBNN với KM, CoxPH, case-base logistic regression, DeepSurv và DeepHit.

**Đưa vào benchmark:** CBNN; nhánh non-PH có time-as-input; contrast “explicit time modeling”; yêu cầu xuất full survival curve để đánh giá probability. **Không đưa vào:** các covariate lâm sàng của paper.

#### 2.2.4. Birolo et al. (2025) — *Beyond Cox Models*

Birolo et al. thiết kế benchmark theo ba data-generating regimes: tuyến tính + PH, phi tuyến + PH, và vi phạm PH. Paper so sánh CoxPH, CoxNet, gradient boosting survival, RSF, FastCPH, DeepHit, DSM và SurvTRACE; đồng thời nhấn mạnh rằng Harrell's C đơn lẻ không đủ công bằng cho mô hình non-PH có thứ hạng rủi ro thay đổi theo thời gian.

**Đưa vào benchmark:** lưới tuyến tính/phi tuyến × PH/non-PH; CoxPH, CoxNet, BoostedCox, RSF và DeepHit; Antolini C, Brier/IBS và dynamic AUC; các contrast tách giá trị của phi tuyến khỏi giá trị của việc bỏ PH. **Chưa triển khai:** DSM và SurvTRACE; chúng vẫn thuộc Phase 4, không được tính là kết quả đã chạy.

### 2.3. Ma trận paper → benchmark đã thực hiện

| Nguồn | Ý tưởng/đối tượng gốc | Hiện thực trong `eu27_v3` | Mức độ chuyển giao | Trạng thái |
|---|---|---|---|---|
| Nitsch (2007/2009) | KM; CoxPH | Kaplan–Meier; CoxPH | Trực tiếp về phương pháp | ✅ đã chạy |
| Nitsch (2007/2009) | Initial/current trade value, market share, market size, unit value | `log_initial_value`, `log_value`, `log_value_lag`, `vn_market_share`, `vn_market_share_lag`, `log_market_size`, `log_market_size_lag`, `log_unit_value_lag` trong F1 | Chuyển hướng dyad sang VN → EU | ✅ đã dùng |
| Nitsch (2007/2009) | GDP, GDP/người, distance, border, language và institutional/gravity controls | `log_gdp_d_lag`, `log_gdpcap_d_lag`, `log_dist`, `contig`, `comlang_off`, `comcol`, `wto_d`, `eu_d` trong F2 | Trực tiếp về khái niệm; một số cột bị loại tự động vì hằng số trên EU-27 | ✅/lọc theo fold |
| Lawless & Studnicka (2024) | Random-effects discrete-time cloglog | Cloglog với gamma frailty | Trực tiếp về họ mô hình | ✅ đã chạy |
| Lawless & Studnicka (2024) | Experience, số product/destination, proximity, launch value | `exp_prod`, `n_products_to_c_lag`, `n_markets_for_p_lag`, `proximity_hs2_lag` (F3) và `log_initial_value` (F1) | **Chuyển thể** firm-level → country-product | ✅ đã dùng |
| Lawless & Studnicka (2024) | Experience × diversification/proximity | `exp_prod × n_markets_for_p_lag`, `exp_prod × proximity_hs2_lag` trong Cloglog-theory | Theory-informed adaptation | ✅ đã dùng |
| Lawless & Studnicka (2024) | Destination experience | `exp_dest` | Chuyển thể nhưng biến thành xu hướng năm trên EU-27 | ❌ loại theo thiết kế |
| Islam et al. (2024) | Case-base sampling; neural hazard nhận time làm input | CBNN | Trực tiếp về kiến trúc | ✅ đã chạy |
| Islam et al. (2024) | Time-varying/higher-order interactions | CBNN và contrast với DeepHit/CoxTime; phân tích theo tuổi quan hệ | Trực tiếp về giả thuyết mô hình | ✅ đã thiết kế |
| Birolo et al. (2025) | So sánh dưới tuyến tính/phi tuyến và PH/non-PH | Ma trận §4.2 và contrasts A–F | Trực tiếp về logic benchmark | ✅ đã dùng |
| Birolo et al. (2025) | CoxPH, CoxNet, boosting, RSF, DeepHit | Cùng năm họ mô hình trong 11-model benchmark | Trực tiếp | ✅ đã chạy |
| Birolo et al. (2025) | DSM, SurvTRACE | Phase 4 | Trực tiếp | ⏳ chưa chạy |
| Birolo et al. (2025) | Antolini C, Brier, time-dependent AUC | §5.2–§5.4 | Trực tiếp về tiêu chí đánh giá | ✅ đã dùng |

### 2.4. Provenance ở cấp feature

Bảng dưới bám theo trường `lit` trong [`feature_registry_eu27_v3.yaml`](../benchmark/features/feature_registry_eu27_v3.yaml). Nhãn “Nitsch-motivated” hoặc “Lawless–Studnicka-motivated” có nghĩa là paper cung cấp **cơ chế/khái niệm kinh tế** cho biến; chỉ các biến được nêu là “trực tiếp” mới nên được mô tả như phép chuyển giao gần nguyên bản.

| Provenance trong registry | Feature thực tế | Cách đọc học thuật |
|---|---|---|
| Lawless & Studnicka | `spell_age`, `log_spell_age` | Duration/interval dependence; trực tiếp về cấu trúc hazard |
| Cả Nitsch và Lawless & Studnicka | `log_initial_value`, `log_gdp_d_lag`, `log_gdpcap_d_lag`, `log_dist` | Các khái niệm xuất hiện ở cả hai trade papers; đã đổi cấp phân tích cho mẫu VN × EU |
| Nitsch-motivated: relationship strength | `log_value`, `log_value_lag`, `value_growth_lag`, `vn_market_share`, `vn_market_share_lag`, `log_market_size`, `log_market_size_lag`, `rca_lag`, `world_growth_lag`, `volatility_3y_lag`, `log_unit_value_lag`, `partner_share_pct`, `product_share_pct` | Value, share, market size và unit value là chuyển giao gần; growth, RCA, volatility và portfolio shares là operational extensions theo cùng cơ chế persistence |
| Nitsch-motivated: gravity/macro | `log_pop_d_lag`, `contig`, `comlang_off`, `comcol`, `comrelig`, `wto_d`, `gdp_growth_d_lag`, `inflation_d_lag`, `fx_change_lag`, `imports_pct_gdp_lag` | Gravity/institution là lõi; các chỉ báo macro mở rộng môi trường đích. Các biến hằng số bị lọc như mô tả ở §3.7bis |
| Lawless & Studnicka, chuyển thể | `exp_prod`, `n_products_to_c_lag`, `n_markets_for_p_lag`, `proximity_hs2_lag` | Chuyển từ firm experience/diversification/core proximity sang kinh nghiệm và breadth của Việt Nam theo product/destination |
| Lawless & Studnicka, chuyển thể nhưng loại | `exp_dest`; các tương tác liên quan | `exp_dest` trở thành calendar trend trong mẫu EU-27 nên bị loại; hai tương tác còn nhận diện được được giữ cho Cloglog-theory |
| Nitsch-motivated ở mức trade cost/institution | `tariff_rate`, `tariff_rate_lag`, `tariff_change`, `fta_in_force`, `pref_margin_lag` | Hỗ trợ khái niệm cho block policy; không hàm ý paper cung cấp EVFTA coding |
| Thiết kế EVFTA riêng của dự án | `tariff_applied_lag`, `evfta_cut_cum_pp_lag` | Dựng từ schedule pháp lý EVFTA và dữ liệu thuế EU; Nitsch chỉ là nền kinh tế học tổng quát |
| Không lấy từ bốn seed papers | `left_trunc`; toàn bộ NTM/trade-remedy/CBAM; toàn bộ F5 | Data handling hoặc phần mở rộng policy, complexity và logistics của dự án |

Hai paper phương pháp—Islam et al. và Birolo et al.—không xuất hiện trong cột `lit` của feature registry vì benchmark **không nhập feature lâm sàng hay synthetic** từ họ.

### 2.5. Từ literature review đến sáu tập feature

| Tập | Cơ sở chính | Vai trò trong benchmark | Lưu ý truy xuất nguồn |
|---|---|---|---|
| F0 — Duration | Nitsch; Lawless & Studnicka; survival literature | Đo duration dependence trước khi thêm thông tin kinh tế | `left_trunc` là xử lý dữ liệu của dự án |
| F1 — Relationship strength | Chủ yếu Nitsch; launch value có ở cả hai trade papers | Quy mô, sức mạnh và động học của quan hệ | Registry gắn cả block với Nitsch theo **logic kinh tế rộng**; RCA, growth, volatility và partner/product shares là biến vận hành hóa/mở rộng, không phải danh sách biến được chép nguyên từ paper |
| F2 — Gravity/macro | Chủ yếu Nitsch; một phần destination controls của Lawless & Studnicka | Quy mô thị trường, trade cost và bất ổn vĩ mô | Population, inflation, import openness là mở rộng của dự án |
| F3 — Experience/diversification | Lawless & Studnicka, được chuyển thể | Kiểm tra experience cùng breadth/proximity và tương tác | Không diễn giải là firm experience nguyên bản |
| F4 — Policy/barriers | Logic trade-cost/institution của Nitsch + thiết kế B0 + dữ liệu pháp lý/thuế EVFTA của dự án | Kiểm tra giá trị dự báo tăng thêm của thuế, EVFTA, NTM, remedies, CBAM | Tariff/FTA được Nitsch hỗ trợ ở mức khái niệm; EVFTA staging, NTM, remedies và CBAM là vận hành hóa/mở rộng của dự án |
| F5 — Complexity/logistics | Mở rộng riêng của dự án | Robustness/incremental information | **Không xuất phát trực tiếp từ bốn seed papers** |

### 2.6. Những thành phần không nên gán nhầm cho bốn papers

- CoxTime và DeepSurv là comparator bổ sung từ literature deep survival; RSF/boosting cũng có paper phương pháp gốc riêng. Việc chúng có mặt giúp tạo contrast sạch, nhưng không có nghĩa cả 11 mô hình đều do bốn seed papers đề xuất.
- Rolling-origin, re-censor theo block, cùng information set, preprocessing học trên train và paired spell bootstrap là cách dự án **vận hành hóa một benchmark chống leakage và có uncertainty**, không phải một package được bê nguyên từ một paper.
- EVFTA staging, `tariff_applied_lag`, `evfta_cut_cum_pp_lag`, NTM, CBAM và logistics/complexity là đóng góp dữ liệu/thiết kế của dự án. Nitsch hỗ trợ logic tổng quát về trade cost/institution, nhưng không cung cấp cách dựng các biến EVFTA-specific này.
- Kết quả benchmark là bằng chứng **dự báo**. Không paper nào trong bốn paper biến leaderboard thành identification nhân quả cho EVFTA.

### 2.7. Câu hỏi benchmark suy ra từ literature

Tổng hợp bốn paper dẫn đến hai trục kiểm định, thay vì câu hỏi chung chung “AI có tốt hơn không”:

1. **Feature contribution:** khi đi từ F0 đến F5, thông tin kinh tế nào cải thiện dự báo ngoài duration dependence?
2. **Architecture contribution:** trên cùng một tập feature, hiệu năng tăng đến từ phi tuyến, regularization hay việc nới giả định PH?

Các contrast ở §4.3 và các metric probability-aware ở §5 trả lời trực tiếp hai trục này.

---

## 3. Data

### 3.1. Dataset và lớp lọc scope

Panel nguồn là `data/final/stage1_panel.parquet`: **949.537 episode-year × 205 cột**, 194.461 spells, 147 nước nhập khẩu, 2002–2025. Mẫu benchmark lấy ra từ panel này qua các bước sau:

| Bước | Số dòng | Ghi chú |
|---|---:|---|
| Panel nguồn | 949.537 | 147 nước, 2002–2025 |
| Bỏ các năm đệm dưới ngưỡng (`gap_filled`) | 902.645 | không phải năm quan hệ còn sống |
| Giữ các năm origin trong cửa sổ, kèm 2025 làm biên | 673.856 | |
| **Lọc EU-27 theo năm, không gồm UK** | **164.551** | [`eu27_scope.py`](../benchmark/features/eu27_scope.py) |
| Origin trong cửa sổ chấm điểm 2012–2024 | **148.260** | |
| — trong đó quan sát thấy spell chết | 40.635 | trên toàn bộ follow-up |
| — trong đó chết trong vòng 1 năm | 18.401 | khớp với cờ `event` của dòng gốc (có assert) |

**Định nghĩa EU-27.** Một cặp (nước, năm) thuộc mẫu khi thỏa cả hai điều kiện:
1. Nước đó thuộc 27 thành viên sau Brexit.
2. Nước đó thuộc chế độ thuế quan chung EU trong năm đó (`tariff_reporter == "EUN"`).

Như vậy UK bị loại ở mọi năm, đúng B0 ("UK tách riêng, không gộp vào mẫu chính"). So với bản trước, UK bị loại 8.297 origin (2012–2020). Croatia chỉ vào mẫu từ 2013.

**Lọc nước sau khi tính feature.** Các biến kinh nghiệm và độ phủ thị trường (`exp_prod`, `n_markets_for_p_lag`, RCA) được tính trên **toàn bộ 147 nước trước khi lọc**. Nếu lọc trước, "kinh nghiệm xuất khẩu toàn cầu" của Việt Nam sẽ bị thu hẹp thành "kinh nghiệm trong EU". Lịch sử từ 2002 được giữ lại để đếm đúng tuổi quan hệ cho origin từ 2012.

### 3.1bis. Đối chiếu với B0

| Tham số B0 | Thực hiện | Trạng thái |
|---|---|---|
| Exporter: Việt Nam | Việt Nam | ✅ |
| Importer: EU-27, UK tách riêng | EU-27 theo năm, UK loại hẳn | ✅ |
| Cấp quốc gia; quan hệ (c, p) × năm | (nước, họ sản phẩm) × năm | ✅ |
| Ngưỡng ≥ 10.000 USD/năm | 10.000 USD | ✅ |
| Gián đoạn 1 năm không tính là chết | `GAP_TOLERANCE = 1` | ✅ |
| Khung thời gian 2012–2024 | Origin 2012–2024. Kết cục đọc tới 2025, cần để biết origin 2024 có sống qua 1 năm hay không | ✅ (ghi chú) |
| Left truncation: kéo về 2007 để đếm tuổi | Lịch sử từ 2002, dài hơn yêu cầu | ✅ |
| **Nguồn: BACI 202601** | **Số liệu nhập khẩu do nước EU báo cáo (mirror data)**, không phải BACI | ⚠️ **cần thầy quyết** |
| **HS6 bản HS2012, không nối concordance** | **Họ sản phẩm (product family)**: nối các revision H0–H6 qua bảng concordance WITS, vì nước báo cáo dùng nhiều revision khác nhau trong cùng giai đoạn | ⚠️ **cần thầy quyết** |
| EVFTA staging là biến chính sách | Có trong F4 (`evfta_cut_cum_pp_lag`, `tariff_applied_lag`), nhưng chỉ fold phụ học được biến cắt thuế (§3.7bis) | ⚠️ giới hạn thiết kế |
| Mẫu mở rộng (UK riêng, 147 thị trường) | Chưa chạy lại trên phiên bản metric hiện tại | ⏳ |

Hai dòng ⚠️ đầu tiên thuộc tầng dựng panel, không thuộc benchmark. Có hai hướng:
- (a) chấp nhận và ghi rõ là lệch khỏi B0;
- (b) dựng lại panel từ BACI HS2012, kéo theo tính lại toàn bộ spell và feature.

### 3.2. Đơn vị quan sát

Một sample là một **prediction origin** $i=(j,p,t)$: $j$ là nước EU-27 tại năm $t$, $p$ là họ sản phẩm, $t\in[2012,2024]$. Một spell sinh ra nhiều origin ở các năm liên tiếp; các origin này không độc lập, nên việc lấy mẫu và bootstrap đều thực hiện theo **spell**.

### 3.3. Input

$$
\mathbf{x}_{jpt}\in\mathbb{R}^{d},\qquad d\in\{3,\,25,\,35,\,41,\,54\text{–}57,\,59\text{–}62\}\ \text{(tùy tập feature và fold, xem §3.7)}.
$$

Mỗi feature có một mốc thời gian: `at_t`, `lag1`, `spell_start` hoặc `static`. Mọi trường chứa kết cục hoặc thông tin tương lai (`spell_end_year`, `event`, `right_censored`, `tariff_source_year`, kịch bản thuế Mỹ 2025) bị cấm làm predictor.

### 3.4. Target và quy ước censoring

$$
\text{duration}_u=\text{năm cuối còn sống}-t+1,
$$

trong đó `event = 1` ở năm $Y$ nghĩa là quan hệ còn sống ở $Y$ và chết ở $Y+1$.

Sau khi re-censor theo từng block (§3.6), mỗi dòng mang một trong hai loại thông tin:

- `event = 1, duration = D`: quan hệ chết ở năm thứ $D$ sau origin.
- `event = 0, duration = c`: **đã biết quan hệ sống qua $c$ năm**, tức $T>c$.

Mọi mô hình (KM, Breslow, cloglog) và mọi metric (§5.1) đều đọc dữ liệu theo đúng quy ước này.

### 3.5. Output

Mọi mô hình trả về $\hat{\mathbf S}_i=[\hat S_i(1\mid\mathbf{x}_i),\ldots,\hat S_i(8\mid\mathbf{x}_i)]$. Đánh giá chính ở 1–3 năm.

### 3.6. Cửa sổ thời gian, chống leakage và chia fold

**Chống leakage có hai lớp:**
1. Chia theo thời gian (rolling-origin).
2. **Re-censor tại mốc thông tin của từng block:** train và validation chỉ được biết kết cục tới năm cuối của chính block đó; riêng test đọc kết cục tới 2025.

Hệ quả là origin ở năm cuối của một block train/validation có follow-up bằng 0 và bị loại. Vì vậy năm hiệu dụng ngắn hơn khung ghi trong config một năm.

**Leaderboard gồm 3 fold.** Với kết cục quan sát tới 2025, block test phải bắt đầu không muộn hơn 2022 thì horizon 3 năm mới quan sát được. Vì thế fold test 2024 của bản trước không được dùng cho IBS 1–3 năm.

| Fold | Train (hiệu dụng) | Validation (hiệu dụng) | Test | Train n / sự kiện | Valid n / sự kiện | Test n / sự kiện |
|---:|---|---|---|---:|---:|---:|
| 1 | 2012–2014 | 2016 | 2018–2019 · trước EVFTA | 26.475 / 4.871 | 10.058 / 1.345 | 22.929 / 6.763 |
| 2 | 2012–2016 | 2018 | 2020–2021 · COVID, EVFTA hiệu lực 8/2020 | 46.094 / 10.061 | 11.302 / 1.476 | 25.061 / 6.141 |
| 3 | 2012–2018 | 2020 | 2022–2023 · sau EVFTA | 68.091 / 16.033 | 11.900 / 1.188 | 28.373 / 5.466 |

**Fold phụ EVFTA, chỉ chấm ở 1 năm.** `evfta_cut_cum_pp_lag` chỉ khác 0 từ origin 2021. Không fold leaderboard nào có train chứa origin 2021, nên biến này là hằng số trên train và bị loại. Fold phụ chấp nhận đánh đổi: có train tới 2021, nhưng test chỉ còn 1 năm follow-up.

| Fold | Train (hiệu dụng) | Validation | Test | Train n / sự kiện | Valid n / sự kiện | Test n / sự kiện |
|---:|---|---|---|---:|---:|---:|
| 4 | 2012–2021 | 2023 | 2024 | 104.779 / 26.595 | 14.446 / 1.595 | 15.108 / 2.016 |

Không có giới hạn số dòng train nào bị chạm tới: train mở rộng thật từ 26k lên 105k origin. Riêng RSF và BoostedCox có giới hạn 8.000 dòng train/cell (§4.4).

### 3.7. Tập feature

Registry: [`feature_registry_eu27_v3.yaml`](../benchmark/features/feature_registry_eu27_v3.yaml). Các tập feature là cộng dồn và dùng cho ablation:

| Cấu hình | Số feature đăng ký | Số cột mô hình nhận: fold 1 / 2 / 3 / phụ* |
|---|---:|---|
| F0 | 3 | 3 / 3 / 3 / 3 |
| F0F1 | 17 | 25 / 25 / 25 / 25 |
| F0F1F2 | 31 | 35 / 35 / 35 / 35 |
| F0F1F2F3 | 35 | 41 / 41 / 41 / 41 |
| F0F1F2F3F4 | 50 | 54 / 54 / 55 / 57 |
| F0F1F2F3F4F5 | 55 | 59 / 59 / 60 / 62 |

\* Số cột gồm cả cờ `_isna` do quy tắc `median+flag` sinh ra, trừ các cột hằng số trên train của fold đó (§3.7bis).

Cloglog-theory nhận thêm hai tương tác `exp_prod × n_markets_for_p_lag` và `exp_prod × proximity_hs2_lag`. Tương tác thứ ba (`exp_dest × n_products_to_c_lag`) bị bỏ vì `exp_dest` bị loại (§3.7bis).

#### F0 — Duration dependence (3)

| Feature | Nội dung | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `spell_age` | Tuổi hiện tại của quan hệ | `at_t` | ↓ |
| `log_spell_age` | Tuổi trên thang log | `at_t` | ↓ |
| `left_trunc` | Spell bắt đầu trước cửa sổ dữ liệu | `spell_start` | ? |

#### F1 — Relationship strength (14)

| Feature | Nội dung | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `log_initial_value` | Giá trị xuất khẩu năm đầu spell | `spell_start` | ↓ |
| `log_value` | Giá trị xuất khẩu tại năm origin | `at_t` | ↓ |
| `log_value_lag` | Giá trị xuất khẩu năm trước | `lag1` | ↓ |
| `value_growth_lag` | Tăng trưởng giá trị | `lag1` | ↓ |
| `vn_market_share` | Thị phần VN trong nhập khẩu nước–sản phẩm | `at_t` | ↓ |
| `vn_market_share_lag` | Như trên, trễ 1 năm | `lag1` | ↓ |
| `log_market_size` | Tổng nhập khẩu sản phẩm của nước đích | `at_t` | ↓ |
| `log_market_size_lag` | Như trên, trễ 1 năm | `lag1` | ↓ |
| `rca_lag` | RCA của VN với sản phẩm | `lag1` | ↓ |
| `world_growth_lag` | Tăng trưởng cầu thế giới | `lag1` | ↓ |
| `volatility_3y_lag` | Biến động dòng thương mại 3 năm | `lag1` | ↑ |
| `log_unit_value_lag` | Đơn giá song phương | `lag1` | ↓ |
| `partner_share_pct` | Tỷ trọng nước đích trong **tổng** xuất khẩu của VN | `at_t` | ↓ |
| `product_share_pct` | Tỷ trọng sản phẩm trong **tổng** xuất khẩu của VN | `at_t` | ↓ |

#### F2 — Gravity và vĩ mô (14)

| Feature | Nội dung | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `log_gdp_d_lag` | GDP nước đích | `lag1` | ↓ |
| `log_gdpcap_d_lag` | GDP bình quân đầu người | `lag1` | ↓ |
| `log_pop_d_lag` | Dân số | `lag1` | ↓ |
| `log_dist` | Khoảng cách | `static` | ↑ |
| `contig`, `comlang_off`, `comcol` | Chung biên giới / ngôn ngữ / thuộc địa | `static` | ↓ |
| `comrelig` | Gần gũi tôn giáo | `static` | ↓ |
| `wto_d`, `eu_d` | Thành viên WTO / EU | `static` | ↓ |
| `gdp_growth_d_lag` | Tăng trưởng GDP | `lag1` | ↓ |
| `inflation_d_lag` | Lạm phát | `lag1` | ↑ |
| `fx_change_lag` | Biến động tỷ giá | `lag1` | ↑ |
| `imports_pct_gdp_lag` | Độ mở nhập khẩu | `lag1` | ↓ |

#### F3 — Kinh nghiệm, đa dạng hóa, danh mục (4)

| Feature | Nội dung | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `exp_prod` | Số năm VN đã xuất khẩu sản phẩm này ra bất kỳ thị trường nào | `at_t` | ↓ |
| `n_products_to_c_lag` | Số sản phẩm VN xuất sang nước đích | `lag1` | ↓ |
| `n_markets_for_p_lag` | Số thị trường (toàn cầu) mua sản phẩm này từ VN | `lag1` | ↓ |
| `proximity_hs2_lag` | Proxy độ gần sản phẩm với giỏ xuất khẩu lõi | `lag1` | ↓ |

`exp_dest`, `hhi_market`, `hhi_product` bị loại, xem §3.7bis.

#### F4 — Chính sách thương mại và rào cản (15)

| Feature | Nội dung | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `tariff_rate`, `tariff_rate_lag` | Thuế quan áp dụng cho VN, năm gốc / trễ 1 năm | `at_t` / `lag1` | ↑ |
| `tariff_change` | Thay đổi thuế | `at_t` | ↑ |
| `fta_in_force` | FTA đang hiệu lực (trên EU-27: = 1 từ 2020, tức chỉ báo sau EVFTA) | `at_t` | ↓ |
| `pref_margin_lag` | Biên ưu đãi khi quan sát được thuế ưu đãi | `lag1` | ↓ |
| **`tariff_applied_lag`** ⭐ | Thuế thực áp cho VN: MFN / GSP / thuế theo lộ trình EVFTA | `lag1` | ↑ |
| **`evfta_cut_cum_pp_lag`** ⭐ | Mức cắt thuế EVFTA lũy kế (điểm %), cường độ treatment theo lộ trình staging | `lag1` | ↓ |
| `ntm6_all_inforce`, `ntm6_sps_inforce`, `ntm6_tbt_inforce` | Số NTM / SPS / TBT đang hiệu lực ở HS6 | `at_t` | ↑ |
| `ntm6_observed` | Cờ đo lường NTM | `at_t` | ? |
| `ntm_ave_border_pct` | AVE của NTM | `static` | ↑ |
| `ttb_any_in_force`, `ad_in_force` | Có trade remedy / chống bán phá giá | `at_t` | ↑ |
| `cbam_in_scope` | Thuộc phạm vi CBAM | `at_t` | ↑ |

⭐ Biến EVFTA riêng cho EU-27, parse từ Annex 2-A và kiểm chứng chéo với TRAINS (sai lệch trung bình 0,17–0,34 điểm %). Chi tiết: [`docs/DU_LIEU_EVFTA_VA_THUE_EU.md`](../../docs/DU_LIEU_EVFTA_VA_THUE_EU.md).

#### F5 — Độ phức tạp và logistics (5)

| Feature | Nội dung | Timing | Hazard kỳ vọng |
|---|---|---|---:|
| `pci` | Product Complexity Index | `at_t` | ↓ |
| `importer_eci` | ECI nước đích | `at_t` | ↓ |
| `importer_diversity` | Đa dạng xuất khẩu nước đích | `at_t` | ↓ |
| `importer_lpi_overall` | Logistics Performance Index | `static` | ↓ |
| `importer_glpi` | Green logistics index | `static` | ↓ |

Ba biến cú sốc chung `gepu_current`, `cmo_all_commodities`, `price_energy` bị loại, xem §3.7bis.

### 3.7bis. Feature bị loại

**(a) Loại theo thiết kế: biến đếm thời gian lịch.** Trên mẫu EU-27, ba biến sau có giá trị giống hệt nhau cho mọi dòng trong cùng một năm và tăng đều mỗi năm, nên chúng thực chất là một biến xu hướng thời gian:

| Feature | Giá trị trên EU-27 | Vì sao loại |
|---|---|---|
| `exp_dest` | = năm − 2002 (VN xuất khẩu sang mọi nước EU-27 mỗi năm từ 2002) | Không có biến thiên giữa các dòng; ở test luôn nằm ngoài miền giá trị đã thấy khi train |
| `years_since_evfta_policy` | = năm − 2020 | Như trên; hơn nữa dễ bị hiểu nhầm là biến treatment EVFTA trong khi chỉ là biến đếm năm |
| `years_since_fta` | = năm − 2020 từ 2020, missing trước đó | Trùng với biến trên |

**(b) Loại theo thiết kế: biến liên tục chỉ biến thiên theo năm.** Năm biến sau chỉ nhận một giá trị cho mỗi năm lịch, cho mọi nước và mọi sản phẩm:

| Feature | Block | Ghi chú |
|---|---|---|
| `hhi_market`, `hhi_product` | F3 | Được dựng ở mức tập trung của **toàn bộ** xuất khẩu Việt Nam theo năm, không theo sản phẩm/nước như khái niệm dự định |
| `gepu_current`, `cmo_all_commodities`, `price_energy` | F5 | Cú sốc chung toàn cầu |

Train chỉ có 3–7 năm origin, nên mỗi biến này chỉ có 3–7 giá trị khác nhau. Thực chất chúng là biến giả theo năm, và mỗi năm validation/test lại là một giá trị mới mà mô hình phải ngoại suy. Ở lần chạy thử với các biến này, mô hình tuyến tính không regularization và mô hình deep bị kéo tệ đi rõ rệt, trong khi RSF và CoxNet gần như không đổi. Khi chạy lại đúng các cell đó mà bỏ 5 biến:

| Cell | Mô hình | IBS 1–3y có 5 biến | IBS 1–3y bỏ 5 biến |
|---|---|---:|---:|
| Fold 1, F0F1F2F3 | CoxPH | 0,1471 | 0,1027 |
| Fold 1, F0F1F2F3 | Cloglog | 0,1229 | 0,1029 |
| Fold 2, đầy đủ | CoxPH | 0,1297 | 0,1002 |
| Fold 3, đầy đủ | Cloglog | 0,1365 | 0,1037 |

Để hạng mô hình phản ánh kiến trúc chứ không phản ánh độ nhạy với 5 biến này, cả 5 biến bị loại khỏi benchmark. Ba chỉ báo nhị phân theo năm được giữ, vì giá trị ở test luôn nằm trong miền đã thấy khi train: `fta_in_force` (chỉ báo sau EVFTA), `ntm6_observed` và `ttb_any_in_force`.

**(c) Loại tự động vì hằng số trên train** (bộ lọc `sd > 1e-12`, học trên train rồi áp nguyên cho validation/test):

| Feature | Fold 1–2 | Fold 3 | Fold phụ | Lý do |
|---|:-:|:-:|:-:|---|
| `contig`, `comlang_off`, `comcol` | loại | loại | loại | Không nước EU-27 nào chung biên giới/ngôn ngữ/thuộc địa với VN |
| `wto_d`, `eu_d` | loại | loại | loại | Luôn = 1 trên EU-27 |
| `ntm_ave_border_pct`, `ad_in_force` | loại | loại | loại | Hằng số trong mẫu |
| `ntm6_observed` | loại | giữ | giữ | Chỉ biến thiên khi train gồm năm 2017 |
| `fta_in_force` | loại | loại | **giữ** | = 0 cho mọi origin ≤ 2019 |
| **`evfta_cut_cum_pp_lag`** | loại | loại | **giữ** | = 0 cho mọi origin ≤ 2020 |

**Hệ quả:** trong 3 fold leaderboard, biến chính sách EVFTA duy nhất mô hình dùng được là `tariff_applied_lag`. Vai trò dự báo của cường độ cắt thuế EVFTA chỉ đánh giá được ở fold phụ (§6.9).

### 3.8. Preprocessing

`log1p`/`log_clip1` giảm lệch phải; `clip_pct` chặn tăng trưởng cực đoan ở ±500%; `median+flag` điền median học từ train và thêm cờ `_isna`; `zero`/`zero+flag` cho các giá trị 0 mang tính cấu trúc. Mọi tham số chỉ học trên train của từng fold.

---

## 4. Models

### 4.1. Mười một mô hình

- **Baseline không covariate:** Kaplan–Meier.
- **Survival truyền thống:** CoxPH, CoxNet, Cloglog (có gamma frailty), Cloglog-theory (thêm spline và tương tác theo lý thuyết).
- **Tree-based:** BoostedCox, RSF.
- **Deep survival:** DeepSurv, CoxTime, DeepHit, CBNN.

### 4.2. Ma trận PH × phi tuyến

| | Proportional hazards (PH) | Non-PH |
|---|---|---|
| **Tuyến tính** | CoxPH, CoxNet, Cloglog | — |
| **Phi tuyến** | BoostedCox, DeepSurv, Cloglog-theory | RSF, CoxTime, DeepHit, CBNN |

### 4.3. Contrast thiết kế trước

| Contrast | So sánh | Giả định được cô lập |
|---|---|---|
| A | CoxPH → BoostedCox / DeepSurv | Thêm phi tuyến, giữ PH |
| B | DeepSurv → CoxTime | Bỏ PH, giữ họ neural |
| C | BoostedCox → RSF | Bỏ PH, giữ họ cây |
| D | DeepHit / CoxTime → CBNN | Đưa thời gian trực tiếp vào mô hình |
| E | CoxPH → CoxNet | Chỉ thêm regularization |
| F | Cloglog → Cloglog-theory | Baseline truyền thống có bị làm yếu giả tạo không |

### 4.4. Ngân sách huấn luyện

Ngân sách như nhau giữa các họ mô hình:
- Số lần thử hyperparameter: 3 (mô hình rẻ), 2 (cây), 2 (deep).
- Deep models: 1 seed, tối đa 20 epoch, early stopping patience 3.
- Hyperparameter được chọn theo **IPCW Brier 1 năm trên validation**, vì validation chỉ có 1 năm follow-up.
- RSF và BoostedCox giới hạn 8.000 dòng train/cell, do thời gian fit tăng nhanh hơn tuyến tính theo số dòng. Giới hạn này bất lợi cho họ cây.

Vì ngân sách thấp, kết quả là **so sánh có kiểm soát** giữa các mô hình, không phải hiệu năng tối đa của từng mô hình.

---

## 5. Metrics

### 5.1. Quy ước censoring và hiệu chỉnh so với các bản trước

Theo §3.4, dòng censor tại $c$ đã biết là sống qua $c$ năm. Mọi metric dùng chung hai định nghĩa:

$$
\text{đã chết trước } u:\ D_i\le u,\ \delta_i=1;\qquad
\text{đã biết còn sống tại } u:\ D_i>u\ \text{hoặc}\ (\delta_i=0,\ D_i=u).
$$

Trọng số IPCW dùng $P(C\ge t)=G(t-1)$, với $G$ là Kaplan–Meier của phân phối censoring. Một ca chết tại $D$ chỉ cho biết $C\ge D$, nên ca đó rời risk set của censoring từ sau $D-1$.

**Vì sao phải nêu rõ.** Ở `v1` và `eu27_v1`, metric chỉ tính "còn sống tại $u$" khi $D_i>u$, tức bỏ qua mọi dòng censor đúng tại $u$. Trên block chỉ có 1 năm follow-up, trong đó có **mọi block validation dùng để chọn hyperparameter**, Brier score khi đó chỉ còn phạt các ca chết, nên mô hình càng bi quan càng được điểm tốt. Mô phỏng với xác suất sống sót thật đã biết minh họa rõ:

| Kịch bản (Brier 1 năm, follow-up 1 năm) | Giá trị thật | Metric cũ | Metric mới |
|---|---:|---:|---:|
| Mô hình đúng | 0,1357 | 0,1048 | 0,1357 |
| Mô hình bi quan ($\hat S = 0{,}5\,S$) | 0,3062 | **0,0262** (thắng sai) | 0,3062 |

Với follow-up hỗn hợp 1–5 năm, Brier 3 năm cũ cho 0,1851 so với giá trị thật 0,2039; metric mới cho 0,2037. Kiểm thử tự động: [`test_censoring_convention.py`](../benchmark/evaluation/test_censoring_convention.py). **Vì vậy các con số của `v1` và `eu27_v1` không nên được trích dẫn.**

### 5.2. Brier Score và Integrated Brier Score (metric chính)

$$
BS(u)=\frac1n\sum_i\left[\frac{\mathbf 1\{D_i\le u,\delta_i=1\}\,\hat S_i(u)^2}{G(D_i-1)}+\frac{\mathbf 1\{\text{biết còn sống tại }u\}\,(1-\hat S_i(u))^2}{G(u-1)}\right],
\qquad IBS_{1\text{–}3}=\frac12\int_1^3 BS(u)\,du.
$$

$BS(u)$ trả về NaN khi không dòng nào được biết còn sống tại $u$, tức horizon $u$ không quan sát được trong block đó. **IBS 1–3 năm** quan sát được ở cả 3 fold leaderboard. IBS 1–5 năm chỉ quan sát được ở fold 1–2. Brier là proper scoring rule: điểm kỳ vọng thấp nhất khi dự báo đúng xác suất thật, phù hợp với việc Stage 2 nhân $S$ với giá trị thương mại. Đọc chỉ số: thấp hơn là tốt hơn; không đọc thành "độ chính xác %".

### 5.3. Antolini time-dependent concordance

$C_{td}=P\big(\hat S_i(T_i)<\hat S_j(T_i)\mid T_i<T_j,\ \delta_i=1\big)$. Một dòng censor đúng tại $T_i$ vẫn là cặp so sánh hợp lệ. Các cặp được lấy mẫu có seed (2 triệu cặp). Chỉ số này không giả định PH, nên công bằng giữa hai họ mô hình.

### 5.4. Dynamic AUC

AUC cumulative/dynamic kiểu Uno có trọng số IPCW tại $u\in\{1,3,5\}$. Case là quan hệ đã chết trước $u$; control là quan hệ đã biết còn sống tại $u$.

### 5.5. Expected Calibration Error

Chia dự báo $\hat S(u)$ thành 10 bin theo thứ hạng. Trong mỗi bin, survival quan sát được ước lượng bằng Kaplan–Meier. ECE là trung bình có trọng số của $|\hat S-S_{KM}|$. ECE trả NaN nếu follow-up trong một bin không tới $u$; bản cũ khi đó mang giá trị KM của năm trước sang.

### 5.6. Paired spell bootstrap

Hiệu số IBS có ghép cặp (cùng dòng test) so với CoxPH, 200 lần resample theo spell, CI 95% percentile, trên tập F0F1F2F3 và F0F1F2F3F4. Ở fold phụ, bootstrap thực hiện trên Brier 1 năm.

---

## 6. Results

### 6.1. Quy tắc xếp hạng

Trung bình IBS 1–3 năm qua **3 fold leaderboard**, thấp hơn là tốt hơn. Fold phụ EVFTA không vào leaderboard.

### 6.2. Xếp hạng theo từng tập feature

Nguồn: [`leaderboard.csv`](../benchmark/reports/eu27_v3/leaderboard.csv). Số trong ngoặc là IBS 1–3y trung bình 3 fold.

| Tập feature | Xếp hạng IBS 1–3y, tốt → kém |
|---|---|
| F0 | RSF (0,1104) ≈ CBNN (0,1104) > CoxTime (0,1105) ≈ DeepSurv (0,1105) > CoxPH (0,1106) > Cloglog (0,1108) ≈ Cloglog-theory (0,1108) > CoxNet (0,1110) > BoostedCox (0,1115) > KM (0,1365) > DeepHit (0,1499) |
| F0F1 | RSF (0,1018) > DeepSurv (0,1025) > CoxPH (0,1027) > CoxNet (0,1031) > BoostedCox (0,1034) > CBNN (0,1035) > Cloglog (0,1048) > Cloglog-theory (0,1053) > CoxTime (0,1054) > KM (0,1365) > DeepHit (0,3076) |
| F0F1F2 | CoxPH (0,1023) > RSF (0,1027) > CoxNet (0,1029) > BoostedCox (0,1035) > DeepSurv (0,1039) > Cloglog (0,1043) > Cloglog-theory (0,1048) > CBNN (0,1049) > CoxTime (0,1067) > DeepHit (0,1331) > KM (0,1365) |
| F0F1F2F3 | CoxPH (0,1010) > RSF (0,1012) > CoxNet (0,1025) > Cloglog (0,1028) > CBNN (0,1033) > Cloglog-theory (0,1038) > BoostedCox (0,1042) > CoxTime (0,1052) > DeepSurv (0,1133) > KM (0,1365) > DeepHit (0,1613) |
| F0F1F2F3F4 | CoxPH (0,1013) > RSF (0,1018) > CoxNet (0,1033) > CoxTime (0,1035) ≈ BoostedCox (0,1035) > Cloglog (0,1040) > Cloglog-theory (0,1053) > DeepSurv (0,1105) > CBNN (0,1271) > KM (0,1365) > DeepHit (0,2078) |
| F0F1F2F3F4F5 | RSF (0,1012) > CoxPH (0,1015) > BoostedCox (0,1032) > Cloglog (0,1037) > Cloglog-theory (0,1050) > CoxNet (0,1068) > DeepSurv (0,1086) > CBNN (0,1177) > CoxTime (0,1193) > KM (0,1365) > DeepHit (0,1556) |

RSF và CoxPH luôn nằm trong top 2 ở mọi tập có F1 trở lên. Thứ hạng của các mô hình deep nhảy mạnh giữa các tập feature. Điều này khớp với cảnh báo về độ bất ổn của deep models ở §6.12, hơn là phản ánh giá trị của từng block feature.

### 6.3. Leaderboard trên tập feature đầy đủ

Tập F0F1F2F3F4F5, trung bình 3 fold. "±" là độ lệch chuẩn qua fold.

| Model | IBS 1–3y ↓ | Brier 1y ↓ | Brier 3y ↓ | Antolini C ↑ | AUC 1y ↑ | AUC 3y ↑ | ECE 1y ↓ | ECE 3y ↓ | Giây/cell |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RSF | **0,1012** ± 0,0003 | **0,0804** | **0,1188** | 0,8307 | 0,8651 | 0,8508 | **0,0167** | 0,0299 | 6,0 |
| CoxPH | 0,1015 ± 0,0013 | 0,0814 | **0,1188** | **0,8359** | **0,8696** | **0,8539** | 0,0275 | 0,0342 | 2,1 |
| BoostedCox | 0,1032 ± 0,0012 | 0,0828 | 0,1202 | 0,8287 | 0,8649 | 0,8508 | 0,0389 | 0,0456 | 93,6 |
| Cloglog | 0,1037 ± 0,0004 | 0,0835 | 0,1215 | 0,8327 | 0,8695 | 0,8532 | 0,0339 | 0,0350 | 2,7 |
| Cloglog-theory | 0,1050 ± 0,0006 | 0,0840 | 0,1232 | 0,8330 | 0,8692 | 0,8528 | 0,0369 | 0,0419 | 3,4 |
| CoxNet | 0,1068 ± 0,0013 | 0,0854 | 0,1248 | 0,8232 | 0,8578 | 0,8442 | 0,0457 | 0,0560 | 1,3 |
| DeepSurv | 0,1086 ± 0,0100 | 0,0853 | 0,1269 | 0,8170 | 0,8500 | 0,8426 | 0,0394 | 0,0715 | 5,8 |
| CBNN | 0,1177 ± 0,0237 | 0,0869 | 0,1430 | 0,8073 | 0,8402 | 0,8304 | 0,0330 | 0,0982 | 5,2 |
| CoxTime | 0,1193 ± 0,0164 | 0,0950 | 0,1391 | 0,8046 | 0,8366 | 0,8285 | 0,0481 | 0,0756 | 2,6 |
| Kaplan–Meier | 0,1365 ± 0,0035 | 0,1037 | 0,1653 | 0,5000 | 0,5000 | 0,5000 | 0,0193 | **0,0287** | 0,0 |
| DeepHit | 0,1556 ± 0,0756 | 0,0859 | 0,3143 | 0,7464 | 0,8497 | 0,6035 | 0,0344 | 0,2498 | 38,5 |

- **#1 theo IBS là RSF (0,1012), kém hơn 0,0003 là CoxPH (0,1015).** RSF tốt hơn KM 0,0353 IBS (khoảng 26%). Khoảng cách RSF–CoxPH nằm trong biến thiên giữa các fold (sd của CoxPH là 0,0013), và ở hai tập có bootstrap thì CoxPH lại đứng trên RSF (§6.6).
- **Mô hình phân biệt tốt nhất là CoxPH**, cao nhất ở cả Antolini C (0,8359), AUC 1y (0,8696) và AUC 3y (0,8539). Mô hình có IBS tốt nhất (RSF) không trùng với mô hình phân biệt tốt nhất. IBS của RSF tốt hơn chủ yếu nhờ calibration (ECE 1y 0,0167 so với 0,0275).
- **Chi phí tính toán:** CoxNet, CoxPH và Cloglog mất 1–3 giây/cell. RSF mất 6 giây, nhưng đó là khi đã giới hạn 8.000 dòng train (§4.4). BoostedCox chậm nhất (94 giây/cell, cũng với giới hạn 8.000 dòng) mà không tốt hơn CoxPH.

### 6.4. Feature ablation

Nguồn: [`feature_ablation.csv`](../benchmark/reports/eu27_v3/feature_ablation.csv). IBS 1–3y trung bình 3 fold; cột là tập cộng dồn.

| Model | F0 | +F1 | +F2 | +F3 | +F4 | +F5 | Tập tốt nhất |
|---|---:|---:|---:|---:|---:|---:|---|
| BoostedCox | 0,1115 | 0,1034 | 0,1035 | 0,1042 | 0,1035 | 0,1032 | +F5 |
| CBNN | 0,1104 | 0,1035 | 0,1049 | 0,1033 | 0,1271 | 0,1177 | +F3 |
| Cloglog | 0,1108 | 0,1048 | 0,1043 | 0,1028 | 0,1040 | 0,1037 | +F3 |
| Cloglog-theory | 0,1108 | 0,1053 | 0,1048 | 0,1038 | 0,1053 | 0,1050 | +F3 |
| CoxNet | 0,1110 | 0,1031 | 0,1029 | 0,1025 | 0,1033 | 0,1068 | +F3 |
| CoxPH | 0,1106 | 0,1027 | 0,1023 | **0,1010** | 0,1013 | 0,1015 | +F3 |
| CoxTime | 0,1105 | 0,1054 | 0,1067 | 0,1052 | 0,1035 | 0,1193 | +F4 |
| DeepHit | 0,1499 | 0,3076 | 0,1331 | 0,1613 | 0,2078 | 0,1556 | F0 |
| DeepSurv | 0,1105 | 0,1025 | 0,1039 | 0,1133 | 0,1105 | 0,1086 | +F1 |
| Kaplan–Meier | 0,1365 | 0,1365 | 0,1365 | 0,1365 | 0,1365 | 0,1365 | — |
| RSF | 0,1104 | 0,1018 | 0,1027 | 0,1012 | 0,1018 | 0,1012 | +F3 (0,101225 so với +F5 0,101249) |

- **F1 mang gần như toàn bộ phần cải thiện:** từ F0 lên F0F1, IBS giảm 0,0050–0,0086 ở cả 9 mô hình có covariate trừ DeepHit. Riêng F0 (tuổi quan hệ) đã giảm IBS khoảng 0,026 so với KM.
- **F2 và F3 thêm rất ít.** Ở CoxPH, F2 giảm 0,0004 và F3 giảm thêm 0,0013. Ở RSF, F2 làm tăng 0,0008, rồi F3 giảm 0,0014. Sáu trên mười mô hình có covariate đạt tốt nhất ở F0F1F2F3. Cần nhớ rằng trên EU-27, F3 chỉ còn 4 biến (§3.7bis).
- **F4 và F5 không cải thiện** ở các mô hình ổn định: CoxPH 0,1010 → 0,1013 → 0,1015; Cloglog 0,1028 → 0,1040 → 0,1037. Trong 3 fold leaderboard, biến EVFTA duy nhất còn lại trong F4 là `tariff_applied_lag` (§3.7bis). Các thay đổi lớn ở CBNN, CoxTime và DeepHit khi thêm F4/F5 lớn hơn nhiều so với ở các mô hình khác, nên phản ánh độ bất ổn khi tuning hơn là giá trị của block.

### 6.5. Độ ổn định qua fold

IBS 1–3 năm, tập feature đầy đủ:

| Model | Fold 1 · test 2018–19 (trước EVFTA) | Fold 2 · test 2020–21 (COVID) | Fold 3 · test 2022–23 (sau EVFTA) | Mean | Range |
|---|---:|---:|---:|---:|---:|
| RSF | **0,1010** | 0,1012 | 0,1015 | **0,1012** | **0,0005** |
| CoxPH | 0,1028 | **0,1002** | **0,1015** | 0,1015 | 0,0026 |
| BoostedCox | 0,1046 | 0,1027 | 0,1023 | 0,1032 | 0,0023 |
| Cloglog | 0,1034 | 0,1041 | 0,1037 | 0,1037 | 0,0007 |
| Cloglog-theory | 0,1043 | 0,1052 | 0,1054 | 0,1050 | 0,0012 |
| CoxNet | 0,1078 | 0,1053 | 0,1074 | 0,1068 | 0,0025 |
| DeepSurv | 0,1027 | 0,1202 | 0,1030 | 0,1086 | 0,0175 |
| CBNN | 0,1054 | 0,1451 | 0,1027 | 0,1177 | 0,0424 |
| CoxTime | 0,1214 | 0,1347 | 0,1020 | 0,1193 | 0,0327 |
| Kaplan–Meier | 0,1389 | 0,1324 | 0,1380 | 0,1365 | 0,0064 |
| DeepHit | 0,2428 | 0,1163 | 0,1077 | 0,1556 | 0,1351 |

Mỗi giai đoạn trùng đúng một fold, nên so sánh giữa các giai đoạn còn lẫn hiệu ứng khác biệt train giữa các fold. Đây là đọc mô tả, không phải bằng chứng nhân quả về EVFTA.

- **Mô hình thắng từng fold:** fold 1 là RSF; fold 2 là CoxPH; fold 3 là CoxPH, nhưng chỉ hơn RSF 0,00003 (0,10148 so với 0,10151), tức coi như hòa.
- **Ổn định nhất là RSF** (range 0,0005), rồi đến Cloglog (0,0007). Các mô hình deep có range từ 0,0175 (DeepSurv) đến 0,1351 (DeepHit), và fold tệ nhất không giống nhau giữa các mô hình. Như vậy không có "giai đoạn khó" chung cho mọi mô hình; độ biến thiên chủ yếu đến từ tuning.
- Các mô hình ổn định không có IBS tăng rõ ở fold COVID. CoxPH còn tốt nhất ở fold 2.

### 6.6. Paired bootstrap so với CoxPH

Nguồn: [`delta_ibs_bootstrap.csv`](../benchmark/reports/eu27_v3/delta_ibs_bootstrap.csv). Δ = IBS(mô hình) − IBS(CoxPH), nên Δ < 0 nghĩa là tốt hơn CoxPH. Bootstrap chỉ chạy trên F0F1F2F3 và F0F1F2F3F4 (§5.6), không chạy trên tập đầy đủ.

| Tập feature | Fold | RSF − CoxPH | CI 95% | Kết luận |
|---|---:|---:|---|---|
| F0F1F2F3 | 1 | −0,0010 | [−0,0019; −0,0001] | RSF tốt hơn |
| F0F1F2F3 | 2 | +0,0015 | [+0,0010; +0,0021] | CoxPH tốt hơn |
| F0F1F2F3 | 3 | +0,0001 | [−0,0006; +0,0010] | Không phân biệt được |
| F0F1F2F3F4 | 1 | −0,0008 | [−0,0018; +0,0000] | Không phân biệt được (sát biên) |
| F0F1F2F3F4 | 2 | +0,0013 | [+0,0005; +0,0018] | CoxPH tốt hơn |
| F0F1F2F3F4 | 3 | +0,0010 | [+0,0004; +0,0017] | CoxPH tốt hơn |

- **RSF so với CoxPH:** thắng 1, thua 3, không phân biệt được 2 trên 6 cặp (tập, fold).
- **Toàn bộ 60 so sánh** (10 mô hình × 2 tập × 3 fold, gồm cả RSF và KM): chỉ **4** so sánh tốt hơn CoxPH có ý nghĩa, mỗi mô hình chỉ ở một fold: CBNN (F0F1F2F3 fold 1, −0,0016), DeepSurv (F0F1F2F3 fold 1, −0,0009, CI chạm 0), RSF (F0F1F2F3 fold 1, ở trên) và CoxTime (F0F1F2F3F4 fold 3, −0,0014). CoxNet không phân biệt được với CoxPH ở 3/6 cặp và kém hơn có ý nghĩa ở 3/6; Cloglog không phân biệt được ở 1/6 và kém hơn có ý nghĩa ở 5/6. KM kém CoxPH khoảng 0,032–0,037 ở mọi fold.

### 6.7. Contrast kiến trúc

Nguồn: [`contrasts.csv`](../benchmark/reports/eu27_v3/contrasts.csv). Ghép cặp theo (tập feature, fold), tổng 18 cells. ΔIBS = mô hình đích − mô hình gốc, âm là cải thiện.

| So sánh | ΔIBS trung bình (sd) | Cells cải thiện (/18) | ΔAntolini C | Kết luận |
|---|---:|---:|---:|---|
| A: CoxPH → BoostedCox | +0,0017 (0,0010) | 0 | −0,0048 | Phi tuyến bằng boosting (giữ PH) không giúp |
| A: CoxPH → DeepSurv | +0,0050 (0,0078) | 7 | −0,0084 | Không giúp; biến thiên lớn |
| B: DeepSurv → CoxTime | +0,0002 (0,0094) | 6 | −0,0044 | Không kết luận được; nhiễu tuning lấn át |
| C: BoostedCox → RSF | **−0,0017** (0,0013) | **16** | +0,0015 | **Bỏ PH trong họ cây cải thiện nhất quán** |
| D: DeepHit → CBNN | −0,0747 (0,1205) | 17 | +0,0373 | CBNN tốt hơn, nhưng chủ yếu do DeepHit bất ổn |
| D: CoxTime → CBNN | +0,0027 (0,0129) | 7 | −0,0032 | Không giúp |
| E: CoxPH → CoxNet | +0,0017 (0,0021) | 2 | −0,0041 | Regularization không giúp (n ≫ p) |
| F: Cloglog → Cloglog-theory | +0,0007 (0,0006) | 0 | −0,0001 | Spline và tương tác lý thuyết không giúp; baseline cổ điển không bị làm yếu giả tạo |

**Contrast rõ nhất là C**: RSF tốt hơn BoostedCox ở 16/18 cells. Contrast này không cô lập hoàn toàn giả định PH vì hai mô hình còn khác thuật toán (bagging so với boosting); cả hai cùng giới hạn 8.000 dòng train. Ở phía ngược lại, việc CoxPH đứng top cho thấy trên mẫu này **phi tuyến chưa mang lại lợi ích** khi PH được giữ nguyên (A, E, F). Theo [`ph_vs_nonph.csv`](../benchmark/reports/eu27_v3/ph_vs_nonph.csv), trung bình nhóm non-PH kém nhóm PH ở mọi tập feature (0,008–0,051 IBS); nhưng con số này bị kéo bởi DeepHit, CBNN và CoxTime, nên không đọc thành "vi phạm PH không đáng kể".

### 6.8. Theo tuổi quan hệ (F0F1F2F3F4)

Nguồn: [`subgroups.csv`](../benchmark/reports/eu27_v3/subgroups.csv). IBS 1–3y trung bình 3 fold.

| Nhóm tuổi | Tốt nhất | IBS | Nhì | Kém nhất |
|---|---|---:|---|---|
| Tuổi 1 | RSF | 0,2274 | CoxPH (0,2300) | KM (0,3339); có covariate: DeepHit (0,2578) |
| Tuổi 2–3 | CoxPH | 0,1685 | Cloglog (0,1714) | DeepHit (0,2572) |
| Tuổi 4+ | CoxPH | 0,0550 | Cloglog (0,0553) | DeepHit (0,1844) |

- IBS của quan hệ mới 1 tuổi (0,23) cao gấp khoảng 4 lần quan hệ từ 4 tuổi (0,055). Phần lớn sai số dự báo nằm ở quan hệ mới.
- RSF chỉ đứng đầu ở nhóm tuổi 1, và hơn CoxPH 0,0026. Ở nhóm tuổi 2+, CoxPH tốt nhất. Lợi ích của việc chọn mô hình phi tuyến, nếu có, tập trung ở quan hệ mới, nhưng biên độ nhỏ. Khoảng cách lớn nhất ở nhóm tuổi 1 là giữa KM và các mô hình có covariate (khoảng 0,10), tức giá trị đến từ covariate chứ không đến từ kiến trúc.

### 6.9. Fold phụ EVFTA: biến cắt thuế có thêm thông tin dự báo 1 năm không?

Train gồm origin 2012–2021, trong đó 2021 là năm đầu `evfta_cut_cum_pp_lag` khác 0; test là origin 2024. Chỉ chấm các chỉ số 1 năm. So sánh chính là **F0F1F2F3F4 − F0F1F2F3 trên cùng mô hình, cùng dòng test**. F4 gồm cả các biến thuế/NTM khác, nên đây là đóng góp của **cả block chính sách**, không riêng biến EVFTA.

Nguồn: [`evfta1y/delta_brier1y_F4_minus_F3_bootstrap.csv`](../benchmark/reports/eu27_v3/evfta1y/delta_brier1y_F4_minus_F3_bootstrap.csv). Bootstrap ghép cặp theo spell, 200 lần, seed 4246. File này tính ngoài `make_reports.py`, vì script đó chỉ bootstrap so với CoxPH. Kiểm tra: Brier 1y tính lại trùng `metrics.parquet`.

| Model | Brier 1y F0–F3 | Brier 1y F0–F4 | Δ (F4 − F3) | CI 95% bootstrap |
|---|---:|---:|---:|---|
| DeepSurv | 0,0891 | 0,0897 | +0,0006 | [−0,0003; +0,0018] |
| RSF | 0,0902 | 0,0906 | +0,0003 | [−0,0001; +0,0007] |
| CBNN | 0,0905 | 0,0905 | −0,0001 | [−0,0006; +0,0004] |
| CoxPH | 0,0926 | 0,0949 | **+0,0023** | [+0,0021; +0,0026] |
| CoxNet | 0,0927 | 0,0945 | **+0,0018** | [+0,0015; +0,0021] |
| CoxTime | 0,0930 | 0,0930 | +0,0000 | [−0,0006; +0,0006] |
| BoostedCox | 0,0943 | 0,0952 | **+0,0008** | [+0,0006; +0,0012] |
| Cloglog | 0,0950 | 0,1000 | **+0,0049** | [+0,0046; +0,0054] |
| DeepHit | 0,0960 | 0,0977 | **+0,0017** | [+0,0014; +0,0020] |
| Cloglog-theory | 0,0988 | 0,0998 | **+0,0010** | [+0,0009; +0,0011] |
| Kaplan–Meier | 0,1157 | 0,1157 | 0 | — (không dùng covariate) |

- **Không mô hình nào cải thiện có ý nghĩa khi thêm F4.** 6/10 mô hình có covariate kém đi có ý nghĩa (in đậm), và kém nhất chính là các mô hình tuyến tính/PH: Cloglog +0,0049, CoxPH +0,0023. 4 mô hình còn lại không phân biệt được.
- **Đọc thận trọng.** Train chỉ có một năm có cắt thuế EVFTA (2021, vẫn còn COVID), và test chỉ có một năm (2024). Mô hình tuyến tính kém đi khi thêm F4 phù hợp với việc `evfta_cut_cum_pp_lag` khác 0 chỉ ở origin 2021 trong train, nên gần như trùng với chỉ báo năm, rồi phải ngoại suy khi áp lên 2024 (cắt thuế lũy kế lớn hơn). Đây là cách giải thích khả dĩ; run này chưa kiểm chứng nó. Kết quả không cho thấy block chính sách vô ích về kinh tế; nó chỉ cho thấy thiết kế này chưa trích được thông tin dự báo từ block đó.
- Để tham khảo, trên tập đầy đủ ở fold phụ, mô hình có Brier 1y tốt nhất là DeepSurv (0,0897), rồi RSF (0,0900) và CBNN (0,0902). Thứ tự này khác leaderboard 3 fold, nhưng fold phụ chỉ có một fold và một mức ngẫu nhiên khi tuning.

Đây là bằng chứng **dự báo**, không phải identification: đánh giá tác động nhân quả của EVFTA thuộc B6.

### 6.10. Calibration (tập đầy đủ)

| Model | ECE 1y ↓ | ECE 3y ↓ |
|---|---:|---:|
| RSF | **0,0167** | 0,0299 |
| Kaplan–Meier | 0,0193 | **0,0287** |
| CoxPH | 0,0275 | 0,0342 |
| CBNN | 0,0330 | 0,0982 |
| Cloglog | 0,0339 | 0,0350 |
| DeepHit | 0,0344 | 0,2498 |
| Cloglog-theory | 0,0369 | 0,0419 |
| BoostedCox | 0,0389 | 0,0456 |
| DeepSurv | 0,0394 | 0,0715 |
| CoxNet | 0,0457 | 0,0560 |
| CoxTime | 0,0481 | 0,0756 |

- **Hiệu chuẩn tốt nhất là RSF** ở 1 năm (0,0167), và đứng nhì sau KM ở 3 năm (0,0299 so với 0,0287).
- **KM tốt hơn 9/10 mô hình có covariate ở ECE 1y và tốt hơn cả 10/10 ở ECE 3y.** Điều này dễ hiểu: KM khớp đúng tỷ lệ sống trung bình, và ECE chia bin theo thứ hạng dự báo nên không phạt việc thiếu phân biệt. ECE vì vậy phải đọc cùng Brier/IBS, không đứng riêng.
- Mô hình deep hiệu chuẩn kém ở 3 năm (0,07–0,25), khớp với việc chúng chỉ được chọn hyperparameter theo Brier 1 năm trên validation (§4.4).

### 6.11. Kết luận

1. **Mô hình đề xuất cho B7: CoxPH làm mô hình chính, RSF làm mô hình đối chứng song song.** CoxPH có phân biệt tốt nhất (Antolini C, AUC 1y/3y), đứng #1 IBS ở F0F1F2 đến F0F1F2F3F4, rẻ nhất và diễn giải được. RSF có IBS và ECE 1y tốt nhất trên tập đầy đủ và ổn định nhất qua fold, nhưng chỉ hơn CoxPH 0,0003 IBS, và không hơn có ý nghĩa ở 5/6 cặp bootstrap.
2. **Baseline nên giữ:** KM (cận dưới, và là mốc calibration khó vượt ở 3 năm), CoxPH và Cloglog (baseline kinh tế lượng; Cloglog-theory không tốt hơn Cloglog ở cả 18/18 cells, nên không cần giữ bản theory làm baseline chính).
3. **Tập feature hợp lý: F0F1F2F3.** Sáu trên mười mô hình có covariate đạt tốt nhất ở tập này. F4 và F5 không thêm thông tin dự báo trong 3 fold leaderboard.
4. **EVFTA:** trong thiết kế hiện tại, block chính sách (gồm biến cắt thuế EVFTA) **không cải thiện dự báo 1 năm** ở fold phụ, và làm xấu mô hình tuyến tính. Chưa thể dùng benchmark này để khẳng định vai trò dự báo của EVFTA. Cần thêm năm sau EVFTA trong train, hoặc chuyển câu hỏi sang B6.
5. **Deep learning so với classical:** chưa có mô hình deep nào vượt classical một cách nhất quán. Với ngân sách tuning hiện tại (2 lần thử, 1 seed), deep models bất ổn giữa fold và giữa tập feature (range IBS 0,02–0,14), nên kết quả của họ này chỉ nên đọc như cận dưới.
6. **Contrast rõ nhất:** bỏ PH trong họ cây (BoostedCox → RSF, 16/18 cells). Thêm phi tuyến hoặc regularization mà giữ PH (A, E, F) thì không giúp gì.

**Việc cần thầy quyết định:**
- Nguồn dữ liệu và revision HS: giữ mirror data + product family (ghi rõ là lệch B0), hay dựng lại panel từ BACI HS2012 (§3.1bis).
- Có chạy mẫu mở rộng (UK riêng, 147 thị trường) làm robustness trên phiên bản metric hiện tại hay không.

### 6.12. Giới hạn và lịch sử phiên bản

**Giới hạn:**
- Ngân sách tuning thấp: 2–3 lần thử, 1 seed cho deep models, giới hạn 8.000 dòng train cho mô hình cây (§4.4).
- Chỉ 3 fold leaderboard, và mỗi giai đoạn EVFTA trùng đúng một fold (§6.5).
- Biến cắt thuế EVFTA chỉ học được ở fold phụ, và chỉ chấm được ở chân trời 1 năm (§3.7bis, §6.9).
- F3 và F5 mỏng hơn thiết kế gốc do loại các biến chỉ biến thiên theo năm (§3.7bis). HHI theo sản phẩm/nước muốn dùng lại thì phải dựng lại ở tầng panel.
- Mô hình deep chưa ổn định: với 2 lần thử hyperparameter và 1 seed, cùng một cell chạy lại có thể cho IBS rất khác nhau. Kết quả deep nên đọc như cận dưới.
- Tầng dữ liệu còn lệch B0 về nguồn và revision HS (§3.1bis).
- Bootstrap so với CoxPH chỉ có trên F0F1F2F3 và F0F1F2F3F4, nên thứ tự RSF > CoxPH trên tập đầy đủ chưa có CI (§6.6). Bootstrap F4 − F3 ở §6.9 được tính bằng script riêng, chưa đưa vào `make_reports.py`.

**Lịch sử phiên bản:**

| Run | Mẫu | Thiết kế | Tình trạng |
|---|---|---|---|
| `v1` | 147 nước × origin 2003–2023 | 4 fold, metric cũ | Mẫu robustness được dùng nhầm làm mẫu chính; metric cũ ưu tiên dự báo bi quan khi tuning |
| `eu27_v1` | EU-27 **gồm UK tới 2020**, origin 2012–2024 | 4 fold, fold 4 test 2024; metric cũ | UK chưa tách theo B0; IBS 1–3 và Brier 3y ở fold 4 không quan sát được nhưng vẫn tính vào trung bình; `years_since_evfta_policy` thực chất là biến năm |
| `eu27_v2` | EU-27 không UK, origin 2012–2024 | 3 fold leaderboard + 1 fold phụ EVFTA 1 năm; metric hiệu chỉnh; bỏ biến đếm năm; train không giới hạn | Còn 5 biến liên tục theo năm, làm lệch hạng mô hình (§3.7bis) |
| **`eu27_v3`** | Như `eu27_v2` | Như `eu27_v2`, bỏ thêm 5 biến liên tục theo năm | Bản hiện hành |

---

## Tài liệu tham khảo và nguồn tái lập

### Bốn seed papers

- [Nitsch (2007), *Die Another Day: Duration in German Import Trade*](https://www.ifo.de/DocDL/cesifo1_wp2085.pdf) — feature kinh tế thương mại, KM và CoxPH; bản journal: *Review of World Economics* 145 (2009), 133–154
- [Lawless & Studnicka (2024), *Old Firms and New Export Flows: Does Experience Increase Survival?*](https://doi.org/10.1007/s11079-023-09727-4) — experience/diversification, interactions và random-effects cloglog
- [Islam et al. (2024), *Case-Base Neural Network*](https://doi.org/10.1016/j.mlwa.2024.100535) — CBNN, time-as-input và time-varying higher-order interactions
- [Birolo et al. (2025), *Beyond Cox Models*](https://doi.org/10.1016/j.compbiomed.2025.111176) — lưới PH/non-PH × linear/nonlinear, model benchmark và metric

### Tài liệu thiết kế và artifact tái lập

- [Trao đổi nền về phân loại feature và hazard models](https://chatgpt.com/share/6aaa9afc-8bdc-83ec-8fac-5ff7b919cc7f) — nguồn thảo luận dẫn tới literature review; các claim học thuật trong tài liệu này được dẫn về bốn paper ở trên
- [`SRT_Literature_Review_and_Benchmark_Plan.md`](SRT_Literature_Review_and_Benchmark_Plan.md) — literature review đầy đủ và benchmark plan làm căn cứ cho §2
- [`Stage1_Research_Framework.md`](../../Stage1_Research_Framework.md) — khung nghiên cứu, khối B0
- [`benchmark/config/benchmark_eu27_v2.yaml`](../benchmark/config/benchmark_eu27_v2.yaml) — config của run (dùng chung cho `eu27_v2` và `eu27_v3`)
- [`benchmark/config/splits_eu27_v2.yaml`](../benchmark/config/splits_eu27_v2.yaml), [`splits_eu27_v2_evfta1y.yaml`](../benchmark/config/splits_eu27_v2_evfta1y.yaml) — chia fold
- [`benchmark/features/feature_registry_eu27_v3.yaml`](../benchmark/features/feature_registry_eu27_v3.yaml) — feature registry
- [`benchmark/features/eu27_scope.py`](../benchmark/features/eu27_scope.py) — định nghĩa mẫu EU-27
- [`benchmark/evaluation/`](../benchmark/evaluation/) — metric và kiểm thử quy ước censoring
- [`docs/DU_LIEU_EVFTA_VA_THUE_EU.md`](../../docs/DU_LIEU_EVFTA_VA_THUE_EU.md) — dữ liệu EVFTA staging và thuế EU
- [`benchmark/runs/eu27_v3/`](../benchmark/runs/eu27_v3/), [`benchmark/runs/eu27_v3_evfta1y/`](../benchmark/runs/eu27_v3_evfta1y/) — kết quả từng cell
- [`benchmark/reports/eu27_v3/`](../benchmark/reports/eu27_v3/) — bảng tổng hợp và hình
