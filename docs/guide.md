# Kết luận toàn diện: WITS – từng thành phần, tính năng, cách lấy dữ liệu

WITS cung cấp **đủ tất cả các nhóm biến bạn cần** (trade value, tariff, RCA, product/partner share, growth, HHI, NTM, GDP) thông qua 4 kênh khác nhau, mỗi kênh phù hợp với một mục đích riêng — và quan trọng nhất, module "Trade Outcomes / Survival of Export Relationships" đã **có sẵn chỉ số Export Duration** gần đúng với bài toán survival analysis của bạn, dù chưa ở dạng spell-level thô để tự chạy Kaplan-Meier/Cox.

## 1. Bulk Download portal (link đầu tiên bạn gửi)

Đây là danh mục các "Trade Indicators" và "Derived Nomenclatures" có thể tải hàng loạt (bulk), không phải API. Các chỉ số liên quan trực tiếp đến yêu cầu của bạn nằm trong danh sách này: [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1)

| Chỉ số trong Bulk Download | Liên quan đến yêu cầu của bạn |
|---|---|
| Export Duration / Export Duration (Mirrored) | Survival của quan hệ export — cốt lõi cho bài toán censoring  [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1) |
| Sectoral Composition Comparative Advantage and growth (RCA) | RCA bạn cần  [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1) |
| Herfindahl-Hirschman Market/Product Concentration Index | HHI bạn cần  [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1) |
| Growth Orientation of Markets (Country Growth field / World Growth field) | Country Growth và World Growth bạn cần  [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1) |
| Primary Products Shares & Growth Export/Import | Product share  [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1) |
| Market Composition & Growth Export/Import | Partner share  [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1) |
| Number of Products and Markets | Đếm sản phẩm/thị trường theo năm — dùng để phát hiện birth/death của spell  [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1) |

**Cách lấy:** Vào trang bulk download, chọn chỉ số, reporter, năm, tradeflow, rồi tải file (thường CSV/Excel) theo lô — đây là cách nhanh nhất, không cần viết code, nhưng giới hạn theo trang (pagesize=50) nên với 82×53 nước×20 năm bạn sẽ phải tải nhiều lượt và ghép lại. [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1)

## 2. WITS API User Guide (REST API)

Tài liệu API mô tả rõ **3 dataset chính** truy cập được qua lập trình (Python/requests), phù hợp nhất cho việc xây dựng panel 20 năm tự động: [wits.worldbank](https://wits.worldbank.org/data/pub)

- **UNCTAD TRAINS** (tariff): dữ liệu MFN/preferential tariff ở mức HS6, có `SimpleAverage`, `MIN_RATE`, `MAX_RATE`, `TOTALNOOFLINES` theo reporter-partner-product-year — chính là biến Tariff bạn cần. [wits.worldbank](https://wits.worldbank.org/data/pub)
- **Trade Stats – Trade**: export/import trade value, số sản phẩm, số đối tác, và **built-in indicators** gồm Hirschman-Herfindahl index, Index of Market Penetration, World Growth, Country Growth. [wits.worldbank](https://wits.worldbank.org/data/pub)
- **Trade Stats – Development**: GDP, GNI per capita, Trade Balance, Trade (% GDP) — lấy trực tiếp từ WDI, giải quyết nhu cầu GDP growth của bạn mà không cần join riêng. [wits.worldbank](https://wits.worldbank.org/data/pub)

**Giới hạn quan trọng cần lưu ý khi build pipeline 82×53×20 năm:**
- Không được để tất cả các chiều (reporter, partner, product, year) đều là "ALL" cùng lúc — tối đa 2 chiều được "ALL". [wits.worldbank](https://wits.worldbank.org/data/pub)
- Nếu request quá lớn, API trả lỗi 400/413 "request yield large data to return" — bạn phải chia nhỏ vòng lặp theo từng cặp reporter-year hoặc theo batch. [wits.worldbank](https://wits.worldbank.org/data/pub)
- Response mặc định XML, nhưng có thể thêm `?format=JSON` hoặc header `Accept: application/vnd.sdmx.data+json` để lấy JSON — thuận tiện hơn cho pipeline Python. [wits.worldbank](https://wits.worldbank.org/data/pub)

Đây là cách phù hợp nhất để bạn **tự động hóa việc lấy 82 exporters × 53 importers × HS6 × 20 năm** bằng vòng lặp requests thay vì tải thủ công từng file.

## 3. Analytical Databases page

Trang này chứa các **cơ sở dữ liệu phái sinh** (không phải dữ liệu thô), gồm Export of Value Added (EVA — giá trị gia tăng nội địa trong xuất khẩu, 118 nước, 27 ngành, 1997–2011), Labor Content of Exports, và E-Trade Indicators. Các dataset này **không cần thiết** cho bài toán survival analysis tariff-line của bạn — chúng đo lường value-added/labor content chứ không phải trade value hay censoring, nên có thể bỏ qua để tập trung nguồn lực. [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1)

## 4. Data Download page (datadownload.aspx)

Trang này chỉ có 4 file zip cố định: Trade Stats Country-at-a-Glance, Trade Stats Country Summary, EVA Database, Trade in Services Database. Đây là dữ liệu **tổng hợp cấp quốc gia**, không đạt độ chi tiết HS6/tariff-line, nên **không đủ** cho yêu cầu tariff-line-level của bạn — chỉ dùng để kiểm tra chéo (cross-validation) ở cấp vĩ mô. [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1)

## Chỉ số Export Duration — chi tiết cách tính và giới hạn

Tài liệu "Online Trade Outcomes Indicators User Manual" mô tả rõ công thức: [wits.worldbank](https://wits.worldbank.org/WITS/docs/TradeOutcomes-UserManual.pdf)

\[
share_{ijt} = 100 \times \frac{n_{ijt}}{n_{ij,start}}
\]

trong đó \(n_{ijt}\) là số sản phẩm xuất khẩu từ nước i sang đối tác j tại năm t, và \(n_{ij,start}\) là số sản phẩm ở năm gốc. Chỉ số này đếm **tỷ lệ phần trăm quan hệ sản phẩm-đối tác còn sống sót** qua các năm kế tiếp so với năm bắt đầu. Đây chính là ý tưởng nền tảng của survival analysis xuất khẩu, nhưng nó là **chỉ số tổng hợp đã tính sẵn (aggregate)**, không phải dữ liệu spell-level thô (start_year, end_year, censored flag cho từng cặp exporter-importer-product) mà mô hình Cox/Kaplan-Meier của bạn cần. Bạn vẫn phải tự dựng spell-level dataset bằng cách tải trade value panel thô (`XPRT-TRD-VL` theo reporter-partner-product-year) và viết code xác định thời điểm bắt đầu/kết thúc quan hệ export dựa trên ngưỡng giá trị (WITS dùng ngưỡng 10.000 USD để coi là "có tồn tại quan hệ"). [wits.worldbank](https://wits.worldbank.org/WITS/docs/TradeOutcomes-UserManual.pdf)

Manual cũng nêu chỉ số liên quan khác trong cùng "Section 4 – Survival of Export Relationships": **Export Suspension and Factor Endowments** và **Decomposition of Export Growth along Margins of Trade** — chỉ số thứ hai này tách tăng trưởng xuất khẩu thành margin nội bộ (surviving relationships) và margin mở rộng (new relationships), rất hữu ích để diễn giải kết quả survival model của bạn sau này. [wits.worldbank](https://wits.worldbank.org/WITS/docs/TradeOutcomes-UserManual.pdf)

## Chỉ số RCA — công thức chính xác

RCA của WITS dùng định nghĩa Balassa (1965): [wits.worldbank](https://wits.worldbank.org/WITS/docs/TradeOutcomes-UserManual.pdf)

\[
RCA_{ijk} = \frac{x_{ijk}/X_{ij}}{x_{wjk}/X_{wj}}
\]

với \(x\) là giá trị xuất khẩu sản phẩm k từ i sang j, X là tổng xuất khẩu, w là thế giới. RCA trên 1 nghĩa là có lợi thế so sánh. Chỉ số này có sẵn trong module "Sectoral Composition, Comparative Advantage, and Growth" và tải được qua cả bulk download lẫn API. [wits.worldbank](https://wits.worldbank.org/WITS/docs/TradeOutcomes-UserManual.pdf)

## Dữ liệu NTM — thực trạng độ phủ (điểm nghẽn bạn cần biết)

NTM có trang download riêng với 3 file: NTM Trade Frequency Coverage Ratio, NTM Prevalence Sector, NTM Indicators Measure Sector. Tuy nhiên theo tài liệu UNCTAD chính thức, dữ liệu NTM được thu thập **không liên tục theo năm** — mỗi nước chỉ được khảo sát vào một số năm nhất định (không phải hàng năm như trade/tariff), và độ phủ quốc gia dao động mạnh theo từng đợt thu thập. Trang "NTM Data Availability" cho phép kiểm tra chính xác nước nào có dữ liệu năm nào trước khi đưa vào panel của bạn. Nếu cần độ chi tiết cao hơn, UNCTAD TRAINS Online (trainsonline.unctad.org) còn cung cấp file nghiên cứu định dạng STATA sẵn ở mức HS6, thuận tiện hơn cho việc nạp trực tiếp vào Python/R. [wits.worldbank](https://wits.worldbank.org/tariff/non-tariff-measures/en/ntm-datadownload)

## Bảng tổng hợp: nguồn lấy dữ liệu cho từng biến bạn cần

| Biến cần lấy | Nguồn WITS phù hợp nhất | Phương thức lấy |
|---|---|---|
| Trade value (export/import) | Trade Stats – Trade (API) hoặc Bulk Download | API loop theo reporter-partner-year, hoặc CSV bulk  [wits.worldbank](https://wits.worldbank.org/data/pub) |
| Tariff (MFN/applied) | UNCTAD TRAINS (API) | `SDMX/V21/rest/data/DF_WITS_Tariff_TRAINS`  [wits.worldbank](https://wits.worldbank.org/data/pub) |
| RCA | Sectoral Composition RCA (Bulk Download) | Tải trực tiếp file RCA đã tính sẵn  [wits.worldbank](https://wits.worldbank.org/WITS/docs/TradeOutcomes-UserManual.pdf) |
| Product/Partner share | Primary Products Shares / Market Composition (Bulk) | File bulk đã tính sẵn phần trăm  [wits.worldbank](https://wits.worldbank.org/module/ALL/sub-module/ALL/reporter/ALL/year/ALL/tradeflow/ALL/pagesize/50/page/1) |
| Country/World Growth | Growth Orientation of Markets (Bulk) hoặc Trade Stats indicator | Cả hai kênh đều có  [wits.worldbank](https://wits.worldbank.org/data/pub) |
| HHI | Herfindahl-Hirschman Index (Bulk hoặc API indicator HH-MKT-CNCNTRTN-NDX) | Bulk file hoặc API indicator code  [wits.worldbank](https://wits.worldbank.org/data/pub) |
| NTM (coverage/year/product) | NTM Data Download page | Kiểm tra Data Availability trước, tải CSV/STATA rời rạc theo năm khảo sát  [wits.worldbank](https://wits.worldbank.org/tariff/non-tariff-measures/en/ntm-datadownload) |
| GDP/GDP growth | Trade Stats – Development (nguồn WDI) | API `tradestats-development` indicator  [wits.worldbank](https://wits.worldbank.org/data/pub) |
| Export survival/spell | Export Duration (Bulk) + tự dựng từ trade value panel | Tải chỉ số tổng hợp để đối chiếu, nhưng phải tự code spell-level từ raw panel  [wits.worldbank](https://wits.worldbank.org/WITS/docs/TradeOutcomes-UserManual.pdf) |

Tóm lại, chiến lược tối ưu là: dùng **WITS API** (không phải bulk download thủ công) để tự động kéo trade value + tariff cho toàn bộ 82×53×HS6×20 năm bằng vòng lặp Python, dùng **Bulk Download** để lấy nhanh các chỉ số đã tính sẵn (RCA, HHI, growth, share) làm biến kiểm chứng, dùng **Trade Stats-Development API** cho GDP growth, và xử lý riêng NTM bằng cách kiểm tra Data Availability trước khi ghép vào panel vì độ phủ theo năm rất thưa.

Đúng một phần — đây là **trang chủ tổng hợp**, dẫn lối tới mọi module (Trade, Tariff, NTM, Trade Outcomes, Country Profile), nhưng **không phải nơi chứa dữ liệu**; nó chỉ là cổng điều hướng đến các trang con mà chúng ta đã phân tích trước đó. [wits.worldbank](https://wits.worldbank.org/Default.aspx?lang=en)

## Trang chủ Default.aspx thực chất là gì

Đây là landing page liệt kê các module chính: Trade, Tariff, Non-Tariff Measures (NTM), Trade Outcomes, và Country Profile (theo Country/Indicator/Product HS 6-digit). Mỗi mục chỉ là **link dẫn**, không tự nó chứa dữ liệu tải về — bạn vẫn phải vào từng module con để thực sự lấy dữ liệu, giống các link cụ thể (bulk download, API, NTM download) bạn đã gửi ở lượt trước. [wits.worldbank](https://wits.worldbank.org/Default.aspx?lang=en)

## Vì sao chưa đủ cho việc thực sự lấy dữ liệu

| Cái bạn cần | Có ở Default.aspx? | Thực tế nằm ở đâu |
|---|---|---|
| Duyệt nhanh, định hướng module | Có | Chính là mục đích của trang này |
| Tải dữ liệu tariff-line HS6 hàng loạt | Không | `bulkdownload.aspx` hoặc WITS API  [wits.worldbank](https://wits.worldbank.org/Default.aspx?lang=en) |
| RCA, HHI, Growth, Export Duration đã tính sẵn | Không | Trang Bulk Download (Trade Indicators) đã phân tích trước |
| Tự động hóa pipeline 82×53×20 năm | Không | WITS API User Guide (SDMX/JSON) |
| NTM coverage theo năm | Không | `tariff/non-tariff-measures/en/ntm-datadownload` |
| GDP/GDP growth | Không | Trade Stats – Development (qua WDI, trong API) |

## Điểm hữu ích duy nhất của trang này cho bạn

Nó xác nhận rằng Country Profile hỗ trợ ba chế độ xem — **By Country, By Indicator, By Product (HS 6-digit)** — nghĩa là bạn có thể duyệt dữ liệu ở cấp HS6 ngay từ giao diện web mà không cần API, hữu ích để kiểm tra nhanh trước khi viết code tải hàng loạt. Ngoài ra, nó nhắc rằng cần **Register/Login** để dùng công cụ phân tích tùy chỉnh (custom analysis) — nếu bạn định chạy truy vấn lớn qua giao diện Advanced Query hoặc API với quota cao hơn, nên tạo tài khoản trước. [wits.worldbank](https://wits.worldbank.org/Default.aspx?lang=en)

Tóm lại: trang này là **bản đồ**, không phải **kho dữ liệu**. Bạn vẫn cần dùng đúng 4 con đường đã xác định trước đó (Bulk Download, WITS API, NTM Download, Trade Stats-Development) để thực sự kéo được toàn bộ dữ liệu cho nghiên cứu survival analysis của mình.

