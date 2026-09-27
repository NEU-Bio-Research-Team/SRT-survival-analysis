# Đề xuất feature và thiết kế thí nghiệm SRT survival analysis

Ngày rà soát: 26/09/2026. Ngôn ngữ: tiếng Việt.

## 1. Kết luận nghiên cứu

Dataset Stage 1 phù hợp để nghiên cứu **sự tồn tại của quan hệ xuất khẩu Việt Nam – thị trường nhập khẩu – họ sản phẩm**. Có thể triển khai một chương trình gồm:

- **8 gói feature**, được xây từ 8 khối kinh tế và một khối cấu trúc thời gian.
- **16 mô hình chính**: 6 mô hình cho rủi ro một năm và 10 mô hình cho đường sống sót tại landmark.
- **32 cấu hình sàng lọc**, sau đó mở rộng tối đa **128 cấu hình model–feature chính**.
- **12 nhóm câu hỏi nghiên cứu**, gồm feature, phi tuyến, non-PH, tái gia nhập, frailty, lựa chọn biến, độ nhạy định nghĩa spell và khả năng khái quát.
- Một nhánh kinh tế lượng riêng để giải thích experience/EVFTA; các hệ số của nhánh này không tự động là tác động nhân quả.

Không nên mặc định mô hình nhiều feature nhất hoặc mô hình DL sẽ tốt nhất. Kết quả lưu trong repo đã gợi ý nhóm biến nhỏ có thể tốt hơn nhóm đầy đủ. Ưu tiên đầu tiên là đúng nhãn, đúng thời điểm thông tin, sau đó mới tăng số mô hình.

**Trạng thái bằng chứng:** đã đọc hai sheet của Extraction matrix.xlsx, 21 tài liệu gốc liên quan, README, framework, audit, các script Stage 1 và benchmark lịch sử. Các con số dataset và hiệu năng dưới đây là số trong repo, không phải kết quả chạy lại. Chưa có file parquet/raw khoảng 5,8 GB trong phiên làm việc; chưa kiểm tra lại phân phối/missingness trên dữ liệu thực và chưa huấn luyện mô hình mới.

## 2. Hiểu đúng Stage 1 hiện tại

### 2.1. Phiên bản và đơn vị dữ liệu

Nguồn chính: main tại commit `672e0a9993774769243b8be8218e4105e0060211`, panel v2. Benchmark lịch sử xem tại ref `dbae191`.

| Nội dung | Stage 1 hiện tại |
|---|---|
| Exporter | Việt Nam, cố định |
| Quan hệ | importer × product_family |
| Quan sát | một năm trong một spell của quan hệ |
| Toàn panel, theo audit | 932.204 dòng, 209 cột; 147 importers; 4.365 families có mặt |
| Spell / event | 189.830 spells / 112.885 events được xác nhận |
| Khoảng năm | 2002–2025 |
| B0 EU27 | 146.042 dòng đang hoạt động, 15.958 events, origins 2012–2024 |
| Nguồn trade | Comtrade, importer-reported CIF |
| Product family | family trên nền H0, xử lý orphan trong cùng HS4; không đồng nhất với HS2012 thuần |
| Ngưỡng hoạt động | 10.000 USD/năm |
| Khoảng gián đoạn cho phép | 1 năm |

Một số tài liệu cũ còn mô tả BACI, panel v1, feature hoặc gap rule cũ. Khi có xung đột, ưu tiên **script hiện tại + audit v2 + README hiện tại**. Không chép tỷ lệ missingness của v1 sang v2.

Đây không phải dữ liệu doanh nghiệp: không có firm ID, năng suất, lao động, ownership, management hay kinh nghiệm của từng firm. Kết quả áp dụng cho quan hệ thương mại tổng hợp. Một quan hệ tiếp tục tồn tại có thể do doanh nghiệp mới thay doanh nghiệp cũ.

### 2.2. Nhãn event: khác biệt quan trọng nhất

Với gap tolerance = 1, năm hoạt động cuối cùng là E chỉ được gán event nếu:

1. E+1 và E+2 đều thực sự có dữ liệu HS6 được công bố;
2. sản phẩm vẫn có thể biểu diễn qua mapping ở các năm đó;
3. quan hệ không trở lại trạng thái hoạt động trong khoảng cho phép.

Nhãn đặt tại năm hoạt động cuối E. Thời điểm bắt đầu ngừng hoạt động là E+1; nhãn chỉ được xác nhận ở E+2.

Ví dụ:

| Chuỗi trạng thái | Diễn giải |
|---|---|
| Có trade 2021; dưới ngưỡng 2022; có trade 2023 | Cùng một spell; 2022 là bridge retrospectively xác định |
| Có trade 2021; không hoạt động 2022 và 2023, cả hai năm quan sát đầy đủ | Event gán ở 2021, xác nhận năm 2023 |
| Có trade 2024; không hoạt động 2025 | Chưa đủ xác nhận với gap=1; không gán death |
| Không thấy trade vì importer không báo cáo hoặc family không còn map được | Censor/không quan sát; không suy thành thất bại |

Trong audit EU27, số events năm 2024 và 2025 đều bằng 0. **Đây là giới hạn xác nhận nhãn, không phải bằng chứng doanh nghiệp/quan hệ không còn rời thị trường.**

Với origin L, horizon h, gap g, dữ liệu quan sát tin cậy đến D, một cohort đầy đủ về thời gian xác nhận cần:

`L + h + g <= D`.

Với D=2025 và g=1:

| Horizon | Origin cuối đủ cửa sổ xác nhận cả cohort |
|---|---:|
| 1 năm | 2023 |
| 3 năm | 2021 |
| 5 năm | 2019 |

Điều kiện này là cần, chưa đủ: vẫn kiểm tra coverage theo importer/family. Có thể quan sát một số quan hệ còn sống ở origin muộn hơn, nhưng chỉ chọn các quan hệ đã biết sống sẽ tạo selection bias.

### 2.3. Những cột không được dùng làm predictor

Không đưa vào X: `event`, `spell_end_year`, `right_censored`, `censor_reason`, full-spell duration và mọi thống kê dùng tương lai. Các cờ censor được broadcast cho cả spell vẫn là thông tin kết quả.

`gap_filled` được biết hồi cứu sau khi quan hệ quay lại. Có thể dùng để kiểm tra cấu trúc panel; không dùng như một feature biết trước. Chọn origin đang hoạt động bằng giá trị trade quan sát được và ngưỡng đã định.

`left_trunc` có thể biểu thị tuổi thật không biết do đầu cửa sổ, missing reporting hoặc HS revision. Đây không tự động là delayed entry với thời gian khởi đầu đã biết. Nên:

- Phân tích chính trên incident spells có khởi đầu xác định, kèm phân tích mở rộng toàn bộ.
- Với spell khởi đầu trước 2012 nhưng đã thấy từ lịch sử 2002, giữ tuổi lịch sử.
- Với tuổi thật không biết, ghi rõ “observed age”, thêm cờ và sensitivity; không diễn giải tuổi 1 là lần xuất khẩu đầu tiên.
- Với mô hình từ đầu spell và entry age đã biết, sử dụng likelihood/risk set hỗ trợ delayed entry.

## 3. Literature matrix: nên lấy gì, không nên chuyển nguyên xi?

### 3.1. Nhóm trade-survival và nghiên cứu tổng hợp

| Dòng sheet Survival | Tài liệu | Đóng góp nên dùng | Giới hạn khi áp dụng |
|---|---|---|---|
| 2 | Brenton, Saborowski & von Uexkull — Low Survival | Initial value, gravity, learning, previous spell; grouped-time cloglog và gamma frailty | Không kết luận PH luôn đúng; frailty không sửa mọi dạng non-PH |
| 3 | Islam và cộng sự — CBNN | Time-as-input, nonlinear non-PH hazard; case-base sampling | Cần đúng sampling offset, likelihood và tích phân; không tự động là longitudinal NN |
| 4 | Biró và cộng sự — Beyond Cox | Tách linear/nonlinear và PH/non-PH; so sánh nhiều họ mô hình, C-index và Brier | Dataset y tế không cung cấp feature kinh tế cho repo |
| 5 | Nitsch — Die Another Day | KM/Cox, initial value, gravity, tính khác biệt theo nhóm | Đơn vị German import khác Việt Nam export; kiểm tra biến có variation |
| 6 | Che — Intelligent Export Diversification | Ý tưởng RCA, relatedness, embedding cho cấu trúc sản phẩm | Recommender, không phải survival; cần ma trận nhiều nước xuất khẩu để tái lập |
| 7 | Lawless & Studnicka — Old Firms and New Export Flows | Experience × diversification; learning theo thị trường/sản phẩm | Firm-level: chỉ chuyển thành proxy ở cấp quan hệ/thị trường |
| 8 | Stirbat và cộng sự — Experience of Survival | Previous spell, kinh nghiệm và sự khác nhau giữa các kiểu flow | Dữ liệu firm và tháng; không suy firm upgrading từ aggregate panel |
| 9 | Besedeš & Prusa — Ins, Outs, Duration | KM, tái gia nhập, độ nhạy ngưỡng và gap | Vai trò định nghĩa outcome quan trọng hơn bổ sung một “model mới” |
| 10 | Besedeš, Moreno-Cruz & Nitsch — Depth and Death | Agreement × incumbent/new entrant; random-effects probit | Khác biệt nhóm không tự động là causal policy effect |
| 11 | Lejour — Dutch Export Relations | Logit/probit RE; first versus recurrent spells | Thiếu firm ID; recurrent relation khác recurrent firm |
| 12 | Fugazza & Molina — Determinants | Extended Cox, time interaction, cạnh tranh và đặc tính sản phẩm | Full-spell mean hay future multiple-spells không dùng cho dự báo |

### 3.2. Nhóm method

| Dòng sheet Method | Tài liệu | Vai trò trong thiết kế |
|---|---|---|
| 2 | Ishwaran và cộng sự — RSF | Phi tuyến, tương tác, survival forest |
| 3 | Lee và cộng sự — DeepHit | PMF theo thời gian, likelihood + ranking; dùng single-event head |
| 4 | Katzman và cộng sự — DeepSurv | Phi tuyến nhưng vẫn PH |
| 5 | Kvamme và cộng sự — CoxTime | Non-PH thông qua effect phụ thuộc thời gian |
| 6 | Simon và cộng sự — CoxNet | Linear PH có regularization; baseline rất quan trọng |
| 7 | Prentice & Gloeckler | Grouped survival; cloglog phù hợp khoảng quan sát năm |
| 8 | Graf và cộng sự | Brier/IBS, là metric chứ không thêm một model |
| 9 | Antolini và cộng sự | Time-dependent concordance, là metric chứ không thêm một model |
| 10 | Wang & Sun — SurvTRACE | Transformer trên feature tabular; extension sau benchmark cơ bản |
| 11 | Asghar và cộng sự | Ý tưởng feature-selection consensus, phải làm trong training fold |

### 3.3. Các điểm nên chỉnh trong matrix trước khi dùng làm đặc tả

1. **PG/cloglog:** nền tảng continuous proportional hazard với dữ liệu quan sát theo nhóm thời gian; không nên gán đơn giản vào “continuous model” rồi bỏ qua cấu trúc annual panel.
2. **DeepSurv:** nonlinear PH. Dùng neural network không đồng nghĩa đã bỏ PH.
3. **CoxTime và CBNN:** thời gian đi vào hàm dự báo không đồng nghĩa đã xử lý chuỗi covariate thay đổi hàng năm.
4. **SurvTRACE:** code tác giả dùng `softplus` cho intensity và `exp(-cumsum(hazard))` cho survival. Không dùng `cumprod(1-softplus(...))`: intensity có thể lớn hơn 1. Công thức bài/matrix có chỗ không thống nhất, cần lấy implementation được kiểm chứng làm đặc tả.
5. **Graf/Antolini:** đưa vào evaluation registry, không tính vào số model.
6. **Asghar:** mô tả majority ≥3/4 và biểu thức intersection có khác biệt; nếu dùng ≥3/4, ghi rõ quy tắc adaptation. Không coi kết quả DL chưa tune kỹ trong paper là bằng chứng DL kém tổng quát.
7. **Intelligent Export Diversification:** đưa vào mục feature extension/recommendation, không xếp trực tiếp cùng survival models.

## 4. Feature registry đề xuất

### 4.1. Chín khối: một khối cấu trúc và tám khối kinh tế

| Khối | Feature đề xuất | Tình trạng / xử lý | Liên hệ literature |
|---|---|---|---|
| D — cấu trúc | observed spell age, log-age, age bins/spline, known-start flag | Có/tính đơn giản; duration baseline trong annual model | PG, Brenton, Nitsch |
| R — sức mạnh quan hệ | log current trade, lag log trade, initial observed value, lag market share, unit value, volatility | Phần lớn có; initial phải tính theo spell và origin; unit value optional | Brenton, Nitsch, Fugazza–Molina |
| M — thị trường, gravity | lag GDP, GDP/capita, log distance, GDP growth, inflation, import demand | Có; constant/identity xử lý theo fold | Trade-survival papers |
| E — experience, portfolio | lag số products tới importer, lag số markets cho product, HS2 share, RCA, VN-product growth, world-product growth | Có; ghi đúng grain, history coverage | Lawless, Stirbat, Lejour |
| P — tariff/policy | applied tariff lag, preference margin lag, cumulative EVFTA cut lag | Có; lịch thông tin và biến đồng tuyến cần kiểm soát | Depth and Death; Stage 1 policy design |
| N — NTM | log1p SPS/TBT/other in-force counts, source age, observed/mappable flags | Có nhưng cần as-of filter; snapshot future không vào core | Policy mechanism extension |
| C — complexity | PCI, importer ECI/diversity và source-year | Có; tạo lag/as-of theo nguồn thực tế | Diversification mechanism |
| L — logistics | LPI overall hoặc components, age since observed survey | Có nhưng thưa; không backfill từ tương lai | Chi phí thương mại, extension |
| H — lịch sử sâu | prior completed spells, time since prior exit, observed active years, trailing trend, conditional HHI | Phải build thêm từ lịch sử prefix | Learning/re-entry và extension |

“Có” nghĩa là có cột/nguồn trong Stage 1, không đảm bảo đã đạt chuẩn prediction-time availability. Không phải mọi feature đề xuất đều đã có cùng định nghĩa trong literature; phần N/C/L và một số H là extension có cơ chế kinh tế, phải ghi rõ.

### 4.2. Những tên cột dễ hiểu sai

| Cột/khái niệm | Định nghĩa theo code hiện tại | Hệ quả |
|---|---|---|
| `growth_lag_pct` | Growth tổng xuất khẩu VN của product family, lag theo năm | Không gọi là tăng trưởng bilateral relation |
| `partner_share_pct` | Share của importer trong tổng xuất khẩu VN | Không phải share importer trong riêng product |
| `product_share_pct` | Share product trong tổng xuất khẩu VN | Không phải product share trong riêng importer |
| `n_markets_for_p_lag1` | Số markets trong universe toàn panel 147 importers | Muốn EU27 phải tính thêm biến EU27 riêng |
| `hhi_market`, `hhi_product` | Concentration của toàn bộ basket VN theo năm | Không thay thế conditional HHI của product hoặc importer |
| RCA | Tính từ trade/denominator trong coverage đang có | Không phải firm RCA; cần kiểm tra coverage của world denominator |
| Unit value | USD/kg | Proxy giá/cơ cấu, không phải phép đo chất lượng sản phẩm thuần |
| `tariff_rate_lag1` và applied tariff | Có đường nguồn/alias lịch sử khác nhau | Chọn biến EU đã reconcile, không đưa duplicate vào model |

Registry cũ mô tả sai grain của một số biến share/growth. Đây là lỗi quan trọng cho diễn giải, kể cả khi code vẫn chạy.

Các biến mới nên định nghĩa rõ:

- Bilateral growth: `log1p(value[c,p,t-1]) - log1p(value[c,p,t-2])`.
- Product destination HHI: `sum_c (value[c,p,t-1] / sum_c value[c,p,t-1])^2`.
- Importer product HHI: `sum_p (value[c,p,t-1] / sum_p value[c,p,t-1])^2`.
- Prior-spell count: chỉ đếm spell trước đã kết thúc và được xác nhận trước information cutoff.
- Initial value: giá trị tại năm đầu quan sát spell; chỉ biết sau năm đầu trade, không dùng dự báo trước entry.
- Experience: số năm hoạt động đã quan sát trong prefix, không “biết” lịch sử trước 2002.
- Volatility/trend 3 hoặc 5 năm: dùng cửa sổ trước origin, kèm số năm quan sát và minimum-support rule.

Không thay missing reporter bằng zero để tính growth, HHI hoặc kinh nghiệm.

### 4.3. Biến cần loại/hoãn trong benchmark prospective

**GLPI là vấn đề cụ thể:** `build_glpi.py` đọc `epi2026results.xlsx`, dùng một cross-section EPI2026 cho các năm lịch sử; scaling/PCA còn fit trên toàn bộ macro rows. Vì vậy, các GLPI có EPI này không được coi là predictor có sẵn ở origin 2012–2025. Muốn dùng phải có vintage lịch sử hợp lệ và fit transformation trong train. GLPI không có EPI nhưng PCA toàn dữ liệu cũng phải refit theo fold.

**NTM snapshot/AVE:** audit A12 chấp nhận một số static future-dated sources. B0 có tỷ lệ source-year tương lai khoảng 30,99% ở NTM AVE và 24,26% ở NTM survey trong audit. Audit “PASS” là đạt hợp đồng Stage 1, không chứng minh feature biết được tại thời điểm dự báo. Loại snapshot chưa có vào thời điểm origin; không thay chúng bằng zero.

**CBAM:** definitive phase không có quan sát thực hiện trong panel kết thúc 2025; cờ definitive là constant. Transition chỉ phản ánh giai đoạn reporting, không diễn giải như đã chịu đầy đủ phí carbon. Không dùng US tariff 2025 để kết luận hiệu ứng survival đã được xác nhận.

**TTBD:** nguồn chỉ phủ đến 2015; sau đó không biến missing thành không có trade remedy.

**Firm-level variables, Rauch class, số đối thủ cạnh tranh toàn cầu, product-space embedding:** chưa đủ dữ liệu để tái tạo đầy đủ. Cần firm microdata hoặc nguồn bổ sung tương ứng. Tổng trade VN và tổng world imports không thay cho toàn bộ ma trận exporter × product.

### 4.4. Kiểm soát redundancy và thời điểm

- Với log GDP ≈ log GDP/capita + log population, tránh đưa cả ba vào regression tuyến tính không regularization.
- MFN = applied tariff + preference margin: chọn hai thành phần phù hợp, không cả ba như các predictor độc lập.
- Importer FE hấp thụ distance/static importer traits; family FE hấp thụ product-static traits.
- Calendar FE hấp thụ nhiều macro VN, GEPU, years-since-EVFTA. Các biến này chỉ có ít unique yearly values, không tương đương hàng trăm nghìn quan sát độc lập.
- SPS/TBT nằm trong total NTM: dùng components + other hoặc một total, tránh đếm lặp tùy mục tiêu.
- Một số gravity variables constant trong EU27; loại theo training fold, không theo toàn bộ panel.
- Chế độ prediction dùng thông tin biết ở cuối origin; current trade hợp lệ nếu dự báo exit bắt đầu năm sau.
- Chế độ giải thích dùng lagged X như một specification riêng; lag một năm không tự động làm biến ngoại sinh.
- Không có release-date vintage đầy đủ: gọi kết quả là calendar-time backtest. Không tuyên bố đã mô phỏng realtime data availability hoàn chỉnh.

## 5. Tám gói feature để chạy có tổ chức

Mọi gói đều giữ cùng structural controls D. Đối với landmark remaining lifetime, observed spell age là predictor tại origin; đối với annual hazard, age tạo baseline duration.

| ID | Thành phần | Câu hỏi |
|---|---|---|
| S1 | D + R | Sức mạnh quan hệ có đủ để dự báo tốt không? |
| S2 | S1 + M | Thông tin thị trường/gravity có tăng ích không? |
| S3 | S2 + E | Experience và portfolio có thêm tín hiệu không? |
| S4 | S3 + P | Tariff/EVFTA có tăng ích ngoài trade fundamentals không? |
| S5 | S4 + N | NTM có giá trị riêng khi kiểm soát availability không? |
| S6 | S4 + C | Complexity có đóng góp riêng không? |
| S7 | S4 + L | Logistics có đóng góp riêng không? |
| S8 | S4 + N + C + L + H | Gói mở rộng tốt nhất có thắng gói nhỏ sau selection không? |

D-only, Kaplan–Meier và empirical age-only hazard là reference, không cần lặp dưới 8 tên gói.

S1–S4 giúp tăng dần theo lý thuyết. S5–S7 tách các block phụ thay vì gộp chúng vào một lần. S8 kiểm tra joint information. Với model shortlist, thêm leave-one-block-out: S8 bỏ R/M/E/P/N/C/L/H để nhận diện phần thông tin trùng lặp.

Đây là **8 gói thiết kế ban đầu**, không phải tuyên bố chúng đã đủ coverage để fit. Nếu block không có thông tin ở train origin nào, đánh dấu cấu hình “ineligible” với lý do; không impute toàn bộ một block không tồn tại rồi coi đã kiểm nghiệm nó.

Các gói phải so sánh trên cohort chung. Khi dữ liệu NTM/LPI buộc thu hẹp sample, chạy lại core S4 trên cùng subset và báo riêng hiệu ứng sample selection.

## 6. Tách bài toán trước khi chọn mô hình

### 6.1. Ba nhánh phân tích

| Nhánh | Đầu vào và nhãn | Đầu ra | Mục đích |
|---|---|---|---|
| D: annual active-origin risk | X biết tại origin đang hoạt động; event bắt đầu ngừng vào năm sau, đã xác nhận | q(exit next interval | history, currently active) | Cảnh báo rủi ro một năm |
| L: landmark survival | X tại origin + historical summaries; remaining time, censor indicator | S(u | alive at origin, X_origin) | Xác suất còn tồn tại 1–3 năm; 5 năm nếu đủ follow-up |
| I: inference | Spell/person-period, duration, lagged covariates, policy/experience specification | Association, time interaction, frailty/heterogeneity | Giải thích cơ chế và đối chiếu kinh tế lượng |

Nhánh D dùng row-level covariates thay đổi theo origin. Nhánh L khóa X ở origin, không đưa actual future tariff, GDP hay trade vào dự báo. Nhánh I phải định nghĩa risk set và likelihood từ đầu, không chỉ đọc hệ số từ model thắng leaderboard.

Một annual active-origin classifier với cloglog link không tự động tái lập toàn bộ PG spell likelihood: panel có bridge years và selection vào active origins. Muốn replicate paper, tạo person-period view và likelihood phù hợp tất cả risk intervals. Giữ “paper replication” và “prediction adaptation” thành hai nhãn rõ ràng.

Với nhánh L, khi event được xác nhận ở năm hoạt động cuối E:

`remaining_event_time = E - origin + 1`.

Nếu censor, follow-up kết thúc tại năm thực sự biết còn sống A:

`remaining_censor_time = A - origin`.

Không kéo mọi censor đến 2025; không dùng thời gian kết thúc spell biết từ tương lai khi dựng training cutoff. Rows follow-up bằng 0 không cung cấp survival likelihood hữu ích và phải xử lý riêng.

Không lấy tích của các annual active-origin predictions để tuyên bố có survival curve nhiều năm nếu chưa định nghĩa future covariate path và risk state trong bridge years. Cần landmark adapter, mô hình joint/path giả định rõ, hoặc mô hình trạng thái riêng.

### 6.2. Hazard functions và 16 mô hình chính

Đặt q_j là xác suất failure trong interval j có điều kiện sống đến đầu interval; λ(u) là continuous intensity. Hai đại lượng không đồng nhất:

- `S(k) = product_{j<=k}(1-q_j)`.
- `S(u) = exp(-integral_0^u λ(s) ds)`.
- Nếu intensity hằng trong interval dài Δ: `q_j = 1-exp(-λ_j Δ)`.

| ID | Model | Nhánh | Hàm/giả định chính | Vai trò |
|---|---|---|---|---|
| D01 | Cloglog | D | q=1-exp[-exp(α(age)+Xβ)] | Grouped-PH baseline, hợp dữ liệu năm |
| D02 | Logit | D | q=sigmoid(α(age)+Xβ) | Discrete risk, odds interpretation |
| D03 | Probit | D | q=Φ(α(age)+Xβ) | Comparator theo trade literature |
| D04 | Flexible cloglog | D | Spline covariates + selected X×age interactions | Tách phi tuyến và time-varying effects có kiểm soát |
| D05 | Boosted discrete hazard | D | Boosted function → sigmoid/cloglog probability | ML phi tuyến, tương tác |
| D06 | MLP discrete hazard | D | Neural function(age,X) → probability | DL annual baseline |
| L01 | CoxPH | L | λ(u|X)=λ0(u)exp(Xβ) | Linear PH |
| L02 | CoxNet | L | Cox + elastic-net penalty | Regularized linear PH |
| L03 | Weibull AFT | L | log T=μ(X)+σε, Weibull family | Parametric traditional baseline |
| L04 | Log-normal AFT | L | log T=μ(X)+σε, normal ε | Parametric non-PH alternative |
| L05 | RSF | L | Ensemble survival/cumulative hazard | Nonlinear, no global PH assumption |
| L06 | Gradient-boosted Cox | L | λ=λ0 exp(f_boost(X)) | Nonlinear score nhưng vẫn PH |
| L07 | DeepSurv | L | λ=λ0 exp(f_NN(X)) | Nonlinear PH |
| L08 | CoxTime | L | λ=λ0 exp(f_NN(u,X)) | Nonlinear non-PH |
| L09 | DeepHitSingle | L | PMF p_j(X), S(k)=1−Σ_{j<=k}p_j | Discrete non-PH; likelihood + ranking |
| L10 | CBNN | L | log λ(u,X)=f_NN(u,X), case-base offset khi train | Nonlinear non-PH, direct hazard |

Trong landmark remaining-time models, “time” là thời gian kể từ origin, không phải calendar year. Tuổi spell ở origin vẫn là một covariate. Trong D/I, baseline duration thường theo tuổi spell. Luôn ghi rõ đồng hồ thời gian.

Cox không “sai” chỉ vì có ties hàng năm; chọn Efron/Breslow và công bố. Cloglog tự nhiên hơn cho grouped intervals nhưng không loại bỏ nhu cầu so sánh Cox.

CoxNet vs DeepSurv giúp xem regularized linear PH và nonlinear PH. DeepSurv vs CoxTime giúp xem PH/non-PH với thiết kế neural gần nhau. Các so sánh vẫn cần khớp preprocessing, capacity/tuning và sample để tránh quy chênh lệch hoàn toàn cho một giả định.

### 6.3. Nhánh frailty và các extension

Frailty thực sự cần random effect được tích phân/ước lượng trong likelihood, ví dụ:

`λ_i(u | v_i, X)=v_i λ0(u)exp(Xβ), v_i~Gamma(mean=1,var=θ)`.

Có thể dùng shared frailty ở cấp importer–product relationship để liên kết các recurrent spells, hoặc cấu trúc country/product khác nếu có cơ sở. Phải xem số nhóm, event/group và sự ổn định trước khi mở rộng crossed effects.

- `cluster_col`/robust sandwich điều chỉnh uncertainty; không tự tạo shared-frailty model.
- Cluster theo cặp importer–HS2 không giống two-way clustering theo importer và HS2.
- Với EU27, chỉ 27 country clusters; cần sensitivity cho small-cluster inference.
- Gamma frailty không phải giải pháp tổng quát cho mọi non-PH, dù marginal hazard có thể mất PH sau khi tích phân.

Dự kiến chạy nhánh I trên S1/S3/S4, so sánh pooled cloglog, true shared-frailty cloglog và random-effects logit/probit. Đây là analysis riêng, không tính như những bản sao trong 128 cấu hình.

**Extension sau khi core ổn định:** LogisticHazard, PCHazard, DSM, SurvTRACE. Lý do: thêm khác biệt về output/loss/distribution/feature interaction. Sequence GRU/LSTM/Dynamic-DeepHit chỉ nên mở khi đã dựng chuỗi historical covariates, masking và causal attention; SurvTRACE mặc định không phải temporal transformer của lịch sử xuất khẩu.

Stage 1 chỉ có exit event, không có nguyên nhân kết thúc được xác minh. Không dựng competing risks “upgrade vs failure” từ censor reason, HS revision hoặc tên sản phẩm.

### 6.4. Cần audit implementation cũ trước khi tái sử dụng

- Cloglog legacy fit β trước rồi profile θ/correction sau; không tương đương joint shared-frailty likelihood chuẩn.
- CBNN legacy dùng grid năm, ratio base samples 2/5 và phép tích phân đơn giản; đây là adaptation, không khẳng định tái lập đúng thiết lập paper (paper dùng base sample lớn hơn nhiều).
- RSF/BoostedCox legacy cap khoảng 8.000 training rows trong khi các model khác dùng nhiều hơn. Phải báo cả full-data và equal-row budget.
- DeepHit có thể nhạy với ranking-loss weight, discretization và early stopping. Kết quả xấu với vài trial không đủ kết luận architecture không phù hợp.

## 7. Benchmark cũ: kế thừa điều gì?

Benchmark eu27_v4 là benchmark lịch sử trên panel v2, gồm 11 model × 6 cumulative feature sets × 3 folds = 198 cells. Main hiện tại chỉ giữ Stage 1; code/report cũ còn ở git history.

Ví dụ mean IBS 1–3, thấp hơn tốt hơn:

| Model | F0F1 nhỏ | F0F1F2F3F4F5 đầy đủ |
|---|---:|---:|
| RSF | 0,09772 | 0,10360 |
| DeepSurv | 0,09926 | 0,11002 |
| CoxPH | 0,09941 | 0,11247 |
| CoxTime | 0,10071 | 0,12630 |
| Cloglog | 0,10115 | 0,10637 |
| CBNN | 0,10240 | 0,10229 |

Các số trên là **kết quả lưu trữ**, không phải benchmark sạch đã chạy lại. Full-feature registry có GLPI/NTM với vấn đề timing nêu trên, tuning chỉ 2–3 trials tùy họ, 1 seed; cap sample không đồng đều. S1 mới cũng không phải bản sao nguyên xi F0F1 cũ.

Điều có thể rút ra: phải kiểm tra incremental feature value; “CBNN tốt nhất ở full set” không có nghĩa CBNN tốt nhất ở mọi feature set. Không lấy bảng này làm kết luận model thắng cuối cùng.

Nên kế thừa logic re-censor theo cutoff và ý tưởng landmark. Cần sửa feature semantics, source availability, budgets, uncertainty và validation horizon.

## 8. Splits và evaluation protocol

### 8.1. Tái lập benchmark cũ trước để kiểm tra adapter

| Fold cũ | Train origins | Validation origins | Test origin |
|---|---|---|---:|
| 1 | 2012–2015 | 2016–2018 | 2019 |
| 2 | 2012–2016 | 2017–2019 | 2020 |
| 3 | 2012–2017 | 2018–2020 | 2021 |

Train/validation được dựng nhãn lại theo block endpoint. Test outcome có thể đọc đến 2025. IBS 1–3 có đủ cửa sổ ở ba test origins; horizon 5 chỉ đủ ở 2019.

Legacy chọn hyperparameter bằng Brier 1 năm rồi báo primary IBS 1–3. Không được chỉ đổi validation metric sang IBS 1–3 trong các block ngắn này: validation có thể không đủ nhãn cho horizon 3.

### 8.2. Protocol mới để tune đúng horizon

Một phương án đủ rõ và có thể thực hiện, dùng lịch sử toàn panel cho huấn luyện:

- Training origins bắt đầu 2005, lịch sử 2002–2004 dùng tạo covariates.
- Prediction ở cuối năm origin; đây là calendar-time convention, chưa phản ánh mọi độ trễ công bố.
- Inner model được fit chỉ bằng nhãn đã biết trước validation origin.
- Sau chọn hyperparameters, refit tại cutoff trước test; không dùng test outcome.
- So sánh ở cùng test origins 2019/2020/2021; mọi feature đều cần as-of rule.

| Task | Test origin | Validation origin | Initial training label cutoff | Validation outcomes đến / refit cutoff |
|---|---:|---:|---:|---:|
| D, H1 | 2019 | 2016 | 2015 | 2018 |
| D, H1 | 2020 | 2017 | 2016 | 2019 |
| D, H1 | 2021 | 2018 | 2017 | 2020 |
| L, H1–3 | 2019 | 2014 | 2013 | 2018 |
| L, H1–3 | 2020 | 2015 | 2014 | 2019 |
| L, H1–3 | 2021 | 2016 | 2015 | 2020 |

Ví dụ L fold test2019: fit/tune candidate từ dữ liệu đã biết đến 2013, dự báo cohort2014, đọc outcomes đến2018 để chấm IBS1–3; chọn cấu hình, refit trên dữ liệu biết đến2018, rồi dự báo cohort2019. Initial training sample nhỏ hơn refit; báo rõ và kiểm tra đủ events. Có thể thêm inner validation origins sớm hơn nếu đủ data và compute.

Mở training về 2005 là một thay đổi scope có chủ ý để có history đủ dài cho horizon-matched tuning. Phải báo riêng với benchmark B0-training≥2012. Nếu buộc giữ training≥2012, các test origins sớm có rất ít/không đủ confirmed events cho thiết kế H3 nghiêm ngặt; không chữa bằng cách dùng nhãn tương lai.

Có thể dựng thêm **final H1 test origin2023**, tune bằng validation2020 có outcomes đến2022, rồi refit cutoff2022. Chỉ gọi là untouched test nếu nhóm chưa từng dùng cohort này để ra quyết định. Các test2019–2021 đã được dùng trong report cũ, nên xem là development/reproduction; không quảng bá như holdout hoàn toàn mới.

Muốn final H3 holdout thật mới: cần nguồn tương lai hoặc nhóm importer/product được khóa trước khi xem kết quả, với sự thay đổi estimand được nói rõ.

### 8.3. Không dùng random row split

- Cùng relation có nhiều spells, cùng spell có nhiều landmarks. Random rows gây overlap history/outcome.
- Chronological split có thể cho cùng relation/spell xuất hiện ở train và test nếu đúng mục tiêu “dự báo các quan hệ đã theo dõi”, và labels/features được cắt theo thông tin có sẵn.
- Cold-start relation: hold out toàn bộ spells của relation, không chỉ spell ID.
- Market generalization: leave-country-out; product generalization: holdout product family hoặc HS4 group.
- Các bài toán này khác mục tiêu, nên có leaderboard riêng.
- Nhãn death chưa xác nhận phải mask/censor, không coi là class 0.

### 8.4. Metrics và uncertainty

| Task | Primary | Secondary |
|---|---|---|
| D: annual risk | Brier 1y trên cohort/nhãn hợp lệ | Log-loss, PR-AUC, ROC-AUC, calibration slope/intercept, reliability plot |
| L: survival curves | IPCW IBS 1–3 | Antolini Ctd, time-dependent AUC tại 1/3 năm, Brier từng horizon, calibration, runtime |
| L: extended | IBS 1–5 chỉ trên origins đủ follow-up | Báo riêng, không gộp với cohorts H3 |
| I: inference | Coefficients/marginal effects và uncertainty đúng dependency | PH diagnostics, time interactions, sensitivity theo specification |

IBS đo probabilistic prediction accuracy, kết hợp discrimination và calibration; không gọi là “metric calibration thuần”. C-index cũng không đủ để đánh giá xác suất dự báo.

- Chốt time grid, event-at-boundary và ties rule trước khi chạy.
- Với censoring weights, nêu rõ cách ước lượng G, support và giả định independent/conditional independent censoring. Missing reporting có thể liên hệ importer/year; unconditional KM không tự giải quyết điều đó.
- Nếu G quá nhỏ hoặc validation không có support, đánh dấu horizon ineligible; không âm thầm bỏ NaN để có điểm đẹp.
- Bootstrap paired theo **relation importer×family**, giữ các spells/landmarks cùng relation; không dùng row bootstrap.
- Bổ sung sensitivity country/product clustering khi nghiên cứu common shocks. Không coi ba temporal folds là ba mẫu iid để t-test đơn giản.
- Báo từng fold, mean, paired difference CI, seed variation, training time/memory và số rows/events.
- Reference KM/age-only fit lại mỗi training fold. Có thể báo Brier skill = 1−IBS(model)/IBS(reference).
- Một model fit censor-aware likelihood khác một classifier được train sau khi drop toàn bộ censored cases. Không trộn hai cách này trong một survival leaderboard.

## 9. Bao nhiêu case và bao nhiêu lượt chạy?

### 9.1. Đếm rõ để tránh phóng đại

| Mức | Cấu hình | Số lượng |
|---|---|---:|
| Screening | S1–S4 × 8 models: D01,D02,D05,D06,L02,L05,L07,L10 | 32 |
| Expanded D | 8 sets × 6 models | 48 |
| Expanded L | 8 sets × 10 models | 80 |
| Tổng core | D + L | 128 |
| Core × 3 temporal folds × 1 seed | Selected-configuration fits, chưa tính tuning | 384 |
| Core, 3 seeds cho stochastic profiles | 8 sets × 3 folds × (8 deterministic + 8 stochastic×3) | 768 |

Hai task D và L có leaderboard riêng. Có thể so sánh xác suất failure H1 khi target/cohort khớp, nhưng không xếp Brier1 và IBS3 vào cùng một cột “performance”.

Trong phép đếm 768: deterministic profiles là D01–D04,L01–L04; stochastic profiles là D05,D06,L05–L10. Đặt stochastic boosting/subsampling rõ trong model config; nếu chọn implementation deterministic thì chỉnh số seeds/count cho đúng. Không nhân ba lần model deterministic để tạo thêm “experiments”.

Các số này là **kế hoạch tối đa trước eligibility gates**, chưa gồm tuning, inner fits, baselines, frailty và robustness. 32 screening là tập con của 128, không cộng thành160. Horizon1/3/5 từ cùng survival curve thường không cần fit ba lần.

Tuning đề xuất: linear/parametric dùng grid có chủ đích; tree/neural dùng budget trials hoặc wall-clock công bố trước. Có thể bắt đầu 15–20 candidates/family và tăng cho shortlist nếu validation chưa ổn định; đây là lựa chọn thiết kế, không phải số được literature chứng minh tối ưu. Report best-vs-budget curves để nhận biết model chưa hội tụ.

### 9.2. Mười hai nhóm câu hỏi khoa học

| Case | Câu hỏi | Đối chiếu cần làm | Ưu tiên |
|---|---|---|---|
| C01 | Thêm feature có giúp không? | S1→S4, S4 vs S5/S6/S7, S8; block ablation trên shortlist | Cao nhất |
| C02 | Phi tuyến có cần không? | Linear PH vs spline/boosted/DeepSurv PH với budget phù hợp | Cao |
| C03 | PH có đủ không? | DeepSurv vs CoxTime; cloglog có/không time interactions; diagnostics | Cao |
| C04 | Unobserved heterogeneity có quan trọng không? | Pooled vs true frailty/RE; recurrence structure | Cao cho inference |
| C05 | Selection có cải thiện generalization không? | No selection, elastic-net/stability, explicit ≥3/4 consensus | Cao |
| C06 | Lịch sử và timing nào hữu ích? | Current+past vs lag-only; history3/5; recurrent features | Cao |
| C07 | First/recurrent spells khác nhau không? | Stratified performance, group interaction; known-start vs unknown-start | Cao |
| C08 | Policy liên hệ khác nhau theo cohort không? | Pre-EVFTA incumbents vs entrants; tariff-cut intensity × cohort | Riêng inference |
| C09 | Kết quả có phụ thuộc định nghĩa survival không? | Threshold5k/10k/50k × gap0/1/2, representative models | Bắt buộc robustness |
| C10 | Coverage/vintage làm thay đổi kết luận không? | Strict as-of vs source-available subset; core re-run trên same subset | Bắt buộc |
| C11 | Model khái quát sang nơi/sản phẩm/thời gian khác không? | EU27 vs broad147; country/HS4 holdout; COVID/EVFTA cohorts | Sau core |
| C12 | Lợi ích có bền theo ngân sách và calibration không? | Equal-row vs full-data; tuning budget; seed; calibrated vs raw on heldout | Sau shortlist |

C09 phải rebuild spell/target từ raw trade và reporting coverage. Không thể mô phỏng threshold5k chỉ bằng lọc panel đã tạo ở10k; không thể đổi gap bằng đổi một cột event. Đây là lý do cần raw/intermediate source cho robustness.

C08: incumbent tồn tại trước EVFTA và entrants sau EVFTA có selection khác nhau. Tách năm2020 transition; nếu định nghĩa post full-year thì từ2021. PostEVFTA đồng loạt với calendar time trong EU27; không thể đồng thời dùng đầy đủ year FE và đọc một hệ số post thuần. Tariff-cut variation theo product có thể giúp specification nhưng chưa đủ chứng minh identification. Không dùng feature importance/SHAP như causal effect.

Ưu tiên chạy C01–C03,C06 trước; sau đó C05,C07,C09,C10 trên 3–4 models đại diện. C04/C08 là nhánh cần specification kinh tế lượng. C11/C12 mở rộng khi pipeline đã ổn. Không full-cross 12 dimensions vì vừa tốn compute vừa tạo quá nhiều lựa chọn sau khi nhìn test.

## 10. Quy trình chọn lọc và tổ chức thực thi

### 10.1. Selection theo bốn tầng

1. **Economic admissibility:** đơn vị phân tích phù hợp, có cơ chế, định nghĩa/grain đúng. Loại firm feature không quan sát được.
2. **Information admissibility:** observed/source/available year không vượt cutoff; không outcome-derived; phân biệt unreported, no-history và true zero.
3. **Statistical admissibility trong train:** constant, exact duplicate/identity, extreme missingness, scale/outliers, high-cardinality. Missingness threshold là config cần kiểm nghiệm, không tự động universal.
4. **Predictive selection nested:** elastic-net, permutation/stability hoặc consensus; fit selector bằng inner training, chấm validation, rồi refit. Không select bằng correlation với event trên toàn dataset.

Imputer, scaler, winsorization, PCA, vocabulary/encoder, feature selector và calibrator đều thuộc fitted pipeline của training fold. Feature engineering lịch sử phải prefix-safe ngay từ đầu; train-only preprocessing không sửa được feature đã nhìn tương lai.

Không ép dấu hệ số “đúng literature” rồi coi dấu khác là lỗi dữ liệu. Kiểm tra định nghĩa và uncertainty trước.

### 10.2. Cấu trúc mã đề xuất

| Đường dẫn tương đối | Trách nhiệm |
|---|---|
| notebook/stage2_benchmark/configs/feature_registry.yaml | Định nghĩa/grain/availability của từng feature |
| notebook/stage2_benchmark/configs/feature_sets.yaml | S1–S8, reference và ablation |
| notebook/stage2_benchmark/configs/tasks.yaml | D/L/I, target, horizon, censoring conventions |
| notebook/stage2_benchmark/configs/splits.yaml | Train cutoff, validation origin, outcome cutoff, test origin |
| notebook/stage2_benchmark/configs/models.yaml | Implementation, search space, seed/sample budgets |
| notebook/stage2_benchmark/configs/experiments.yaml | Chỉ những tổ hợp hợp lệ và research question |
| notebook/stage2_benchmark/data/ | Profile, build prefix features, re-censor targets, views |
| notebook/stage2_benchmark/models/ | Adapters dynamic / landmark / inference |
| notebook/stage2_benchmark/evaluation/ | Metrics, calibration, clustered bootstrap, eligibility |
| notebook/stage2_benchmark/runners/ | Plan, run, resume, aggregate |
| notebook/stage2_benchmark/reports/ | Frozen manifests, leaderboards, figures, model cards |

Giữ Stage1 immutable; tạo Stage2 views/configs. Có thể port adapter từ legacy sau audit, không copy toàn bộ benchmark cũ rồi đổi tên version.

Feature registry tối thiểu:

```yaml
bilateral_growth_lag1:
  block: H
  source: stage1_trade_history
  grain: [importer, product_family, year]
  formula: log1p(value_t_minus_1) - log1p(value_t_minus_2)
  available_at: origin
  history_requirement: two_observed_prior_years
  missing_semantics: not_observed_is_not_zero
  transform_fit_scope: train_fold
  allowed_tasks: [D, L, I]
  future_derived: false
  literature_role: adaptation_learning_strength
```

Model adapter cho L phải trả survival probabilities trên cùng grid, không chỉ risk score. D adapter trả one-year probability. I adapter trả coefficients/random-effects specification và inference metadata; không giả vờ chúng cùng một output contract.

Manifest tối thiểu cho một run:

```yaml
run:
  panel_version: stage1_v2
  panel_hash: REQUIRED
  code_commit: REQUIRED
  target_version: exit_gap1_threshold10000_v1
  scope: EU27
  task: landmark_remaining_lifetime
  feature_set: S3
  selector: none
  model: CoxTime
  validation_origin: 2014
  inner_label_cutoff: 2013
  validation_outcome_cutoff: 2018
  refit_label_cutoff: 2018
  test_origin: 2019
  test_outcome_cutoff: 2025
  horizons: [1, 2, 3]
  seed: 1
  sample_budget: full_eligible
```

Run identity phải bao gồm cả selector, hyperparameter hash, source-vintage policy và cohort hash. Lưu predictions ở cấp origin–relation để làm paired comparison mà không phải retrain.

### 10.3. Các kiểm tra cần có trước chạy lớn

- Rebuild cùng input sinh cùng target và cohort hash.
- Thêm các năm tương lai vào source không làm feature/label-as-of ở cutoff cũ thay đổi.
- Threshold/gap ví dụ nhỏ đúng theo quy tắc; thiếu reporter không thành death.
- Trong training cutoff, event cần đủ hai năm xác nhận với gap1.
- Censor/outcome-derived columns không lọt vào X.
- Trong mỗi view, relation/spell/origin keys và follow-up không mâu thuẫn.
- Survival trong [0,1], không tăng theo horizon; probabilities không NaN và intensity chuyển đúng sang probability.
- Những model so sánh trực tiếp nhận cùng cohort/horizon; sample cap phải được lưu.
- IPCW support và eligible rows/events được báo; failure/config ineligible có lý do.
- Không có preprocessing fit bằng validation/test; provenance/source date kiểm tra riêng với feature timing.

Đây là những kiểm tra đánh vào rủi ro thực của repo, không chỉ test wrapper có chạy.

### 10.4. Lộ trình thực hiện

| Bước | Deliverable | Điều kiện chuyển bước |
|---|---|---|
| 1. Profile v2 | Counts/missingness/variation theo origin, importer, block; source-availability map | Xác minh số audit và grain |
| 2. Dựng target/view | D/L/I contracts; cutoff-aware labels; incident/recurrent flags | Các case nhãn/censor đúng |
| 3. Reproduce nhỏ | KM, CoxNet, RSF, cloglog với feature đơn giản | Sai khác legacy được giải thích |
| 4. Screening32 | Validation tables, runtime, calibration; chưa chọn bằng final test | Loại lỗi pipeline và model không đủ support |
| 5. Core128 | Frozen configs; temporal-fold metrics; stochastic repeats | Models/covariates đủ eligibility |
| 6. Focused robustness | C04–C12 trên shortlist theo câu hỏi | Paired analysis và uncertainty |
| 7. Final report | 1 leaderboard/task, feature increment table, model assumptions table, limitations | Không diễn giải historical test là untouched |

Nếu compute hạn chế, hoàn thành screening32 + targeted robustness có giá trị hơn chạy nhiều model với tuning quá ít. Nếu compute rộng, mở128 rồi thêm extension có câu hỏi riêng. Không thể ước tính GPU-hours đáng tin chỉ từ số rows; cần benchmark pilot theo model, RAM, device và feature width.

## 11. Những gì chưa kết luận được từ thông tin hiện có

- Chưa biết chính xác sau strict availability/filtering, mỗi S1–S8 còn bao nhiêu rows/events ở từng fold.
- Chưa biết feature quan trọng nhất hay model thắng sau khi sửa leakage, budgets và target.
- Chưa kiểm định PH trên panel v2, độ ổn định frailty hay khả năng neural training hội tụ.
- Chưa đủ cơ sở xác định tác động nhân quả EVFTA/CBAM chỉ từ thiết kế dự báo.
- Chưa xác minh vintage lịch sử cho mọi nguồn; đây là dữ liệu cần bổ sung nếu muốn realtime backtest.

Để thực thi, cần stage1_panel.parquet, mapping/source-year metadata và raw/intermediate trade/reporting để rebuild threshold/gap. Không cần thêm firm data cho core relation-level survival; cần firm data nếu muốn trả lời câu hỏi về doanh nghiệp.

## 12. Nguồn và cách kiểm chứng

### Repo đã đối chiếu

- [Repository](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis)
- [README tại commit được rà soát](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/672e0a9993774769243b8be8218e4105e0060211/README.md)
- [Audit Stage1 v2](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/672e0a9993774769243b8be8218e4105e0060211/notebook/docs/audit/stage1_v2.md)
- [Build spells](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/672e0a9993774769243b8be8218e4105e0060211/notebook/scripts/build_spells.py)
- [Build covariates](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/672e0a9993774769243b8be8218e4105e0060211/notebook/scripts/build_covariates.py)
- [Build GLPI](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/672e0a9993774769243b8be8218e4105e0060211/notebook/scripts/build_glpi.py)
- [Legacy feature registry eu27_v4](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/dbae191/legacy/benchmark/features/feature_registry_eu27_v4.yaml)
- [Legacy feature ablation](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/dbae191/legacy/benchmark/reports/eu27_v4/feature_ablation.csv)
- [Legacy benchmark config](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/dbae191/legacy/benchmark/config/benchmark_eu27_v3.yaml)
- [Legacy temporal splits](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/dbae191/legacy/benchmark/config/splits_eu27_v3.yaml)
- [Legacy cloglog implementation](https://github.com/NEU-Bio-Research-Team/SRT-survival-analysis/blob/dbae191/legacy/benchmark/models/cloglog.py)

### Matrix và 21 bài gốc

Nguồn tổng hợp: Extraction matrix.xlsx, sheet Survival 11 bài và Method 10 bài. Các tài liệu gốc dưới đây là các PDF trong Drive đã được dùng để đối chiếu.

1. [Lawless & Studnicka — *Old Firms and New Export Flows: Does Experience Increase Survival?*](https://drive.google.com/file/d/1TCW6u0u-wReIimT0bPXNUKNR-ohXaM0z/view?usp=drivesdk)
2. [Fugazza & Molina — *On the Determinants of Exports Survival*](https://drive.google.com/file/d/1FBfWlihftLi2Txt5JZJI6HJx3e4pEyEu/view?usp=drivesdk)
3. [Lejour — *The Duration of Dutch Export Relations*](https://drive.google.com/file/d/1-JT0WhtMpe40ZMmfhfFNcO39wOXLH8hN/view?usp=drivesdk)
4. [Besedeš, Moreno-Cruz & Nitsch — *Depth and Death: Trade Agreements and Trade Duration*](https://drive.google.com/file/d/1Lt-IjKTAMhURl4fxpHR3k3Cj7aK03wzS/view?usp=drivesdk)
5. [Besedeš & Prusa — *Ins, Outs, and the Duration of Trade*](https://drive.google.com/file/d/1cZwHOd03Q6mI-wV9QmBkwYPTzw-uIqSD/view?usp=drivesdk)
6. [Stirbat, Record & Nghardsaysone — *The Experience of Survival*](https://drive.google.com/file/d/1G34769AGzsr2Ydg0fYoHF_TBhS4Y8ozL/view?usp=drivesdk)
7. [Che và cộng sự — *Intelligent Export Diversification*](https://drive.google.com/file/d/1Zg4q7BaXg1wz0uJTiKCbu1wbYQK_vnc0/view?usp=drivesdk)
8. [Nitsch — *Die Another Day: Duration in German Import Trade*](https://drive.google.com/file/d/1RaYmdv_yZxjcdZk_lLLnjQKw_wCXGrNH/view?usp=drivesdk)
9. [Biró và cộng sự — *Beyond Cox Models: A Comparative Study of Machine Learning Methods for Survival Analysis*](https://drive.google.com/file/d/1gSaNnwmO1GSJzYTgYK1QqeBJDvzr50Rn/view?usp=drivesdk)
10. [Islam và cộng sự — *Case-Base Neural Network for Survival Analysis*](https://drive.google.com/file/d/16DACN67dkHhd_RX4DpvxG8BOYg_KrpHC/view?usp=drivesdk)
11. [Brenton, Saborowski & von Uexkull — *What Explains the Low Survival Rate of Developing Country Export Flows?*](https://drive.google.com/file/d/18p33ufIhXK5IJIQsRDivCJImA_40zf81/view?usp=drivesdk)
12. [Simon và cộng sự — *Regularization Paths for Cox’s Proportional Hazards Model via Coordinate Descent*](https://drive.google.com/file/d/1PaclzFOMw2WWVTinzVhX-hR6FWa_Ov_Q/view?usp=drivesdk)
13. [Prentice & Gloeckler — *Regression Analysis of Grouped Survival Data*](https://drive.google.com/file/d/1twfymKN1UI5BZxAiT8d42huEz_kTDmqA/view?usp=drivesdk)
14. [Kvamme, Borgan & Scheel — *Time-to-Event Prediction with Neural Networks and Cox Regression*](https://drive.google.com/file/d/16Jy5MRiS08Bj_XBGJaZefN8lR1D4F3l2/view?usp=drivesdk)
15. [Katzman và cộng sự — *DeepSurv: Personalized Treatment Recommender System Using a Cox Proportional Hazards Deep Neural Network*](https://drive.google.com/file/d/1GQxYQNMshPckm1EyksCTRTXuQpETfniO/view?usp=drivesdk)
16. [Asghar và cộng sự — *Improved Nonparametric Survival Prediction Using CoxPH, Random Survival Forest and DeepHit*](https://drive.google.com/file/d/1kDyRO3quGzxZnuYerdrdkDEhTRAOWVv9/view?usp=drivesdk)
17. [Wang & Sun — *SurvTRACE: Transformers for Survival Analysis with Competing Events*](https://drive.google.com/file/d/1uLHSu9UaOV3Eifm_u0S5YuZEd4Tx3Xiv/view?usp=drivesdk)
18. [Antolini, Boracchi & Biganzoli — *A Time-Dependent Discrimination Index for Survival Data*](https://drive.google.com/file/d/1UWzcTIC7oMsGt33KRLGRulQGP7rxXbLc/view?usp=drivesdk)
19. [Ishwaran và cộng sự — *Random Survival Forests*](https://drive.google.com/file/d/1th7rQkqUPgrGvGqeNh577bdZwYyaVJCk/view?usp=drivesdk)
20. [Lee và cộng sự — *DeepHit: A Deep Learning Approach to Survival Analysis with Competing Risks*](https://drive.google.com/file/d/1MtC66SVJGw0wUKO-7qpsonrqHJmU0NWs/view?usp=drivesdk)
21. [Graf và cộng sự — *Assessment and Comparison of Prognostic Classification Schemes for Survival Data*](https://drive.google.com/file/d/1n6nrqv9l2UqLhE-dJYS6tbIFB-3KZuTS/view?usp=drivesdk)

Các paper được dùng theo đúng vai trò: paper trade-survival để xây giả thuyết/feature và specification; paper method để định nghĩa model/loss; Graf và Antolini để định nghĩa evaluation. Một feature mới được đề xuất từ cơ chế và dữ liệu Stage 1 phải ghi là adaptation/extension, không gắn nhãn “paper X đã dùng đúng biến này”.

### Thứ tự bằng chứng khi triển khai

1. Target/censoring: script tạo spell, reporting coverage và audit Stage 1 tại commit khóa.
2. Feature definition: code tính feature + registry có grain/formula/availability.
3. Model: bài gốc + implementation version được pin.
4. Kết quả: frozen manifest, predictions và run artifacts; không suy từ README.
5. Diễn giải: giới hạn theo unit of analysis, data vintage và design identification.

Đề xuất này là đặc tả nghiên cứu và kế hoạch benchmark. Kết quả hiệu năng cuối cùng chỉ có sau khi materialize panel v2, chạy profile availability, khóa configs và thực thi các folds.


