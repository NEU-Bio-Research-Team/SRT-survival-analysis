# Kiểm chứng thực tế khả năng lấy dữ liệu từ WITS

*Ngày kiểm chứng: 11/08/2026. Toàn bộ kết quả dưới đây đến từ việc gọi thật API/tải thật file, không phải suy đoán từ tài liệu. Script: [wits_probe.py](../scripts/wits_probe.py), output: [probe_out/](../probe_out/).*

---

## Phần 1 — Tổng hợp lại các thành phần dữ liệu bạn cần

### 1.1. Khung thiết kế nghiên cứu

| Chiều | Yêu cầu của bạn |
|---|---|
| Thời gian | 20 năm gần nhất, tần suất năm — đủ dài để survival analysis có ý nghĩa |
| Đơn vị sản phẩm | Tariff-line level: HS 5-digit (~1.271 sản phẩm), **ưu tiên HS 6-digit** |
| Nước xuất khẩu | 82 exporters |
| Nước nhập khẩu | 53 importers, trải đều low / middle / high income |
| Tiêu chí chọn nước | Chỉ giữ nước **báo cáo số liệu nhập khẩu đều đặn hàng năm** (consistent reporters) |

### 1.2. Đơn vị quan sát và bài toán thống kê

- Quan sát cơ bản = **spell** của một quan hệ xuất khẩu: bộ ba `(exporter i, importer j, product k)` được theo dõi qua các năm.
- **Right-censored**: quan hệ vẫn còn sống ở năm cuối của cửa sổ quan sát → giữ lại, đánh dấu censored = 1.
- **Left-censored**: quan hệ đã tồn tại từ trước năm đầu tiên của cửa sổ → **loại bỏ** khỏi mẫu.
- Biến phụ thuộc = thời lượng sống sót (duration) của spell + biến sự kiện (chết / bị kiểm duyệt).

### 1.3. Danh sách biến

**Biến lõi (bắt buộc, ở mức tariff-line):**

| # | Biến | Mức chi tiết cần có |
|---|---|---|
| 1 | Trade value — export value (USD), theo năm | exporter × importer × HS6 × year |
| 2 | Trade value — import value (USD), theo năm | exporter × importer × HS6 × year |

**Biến bổ sung (giải thích / kiểm soát):**

| # | Biến | Vai trò dự kiến |
|---|---|---|
| 3 | Tariff | Rào cản thuế quan mà nước nhập khẩu áp lên sản phẩm |
| 4 | RCA (Revealed Comparative Advantage) | Lợi thế so sánh của exporter ở sản phẩm đó |
| 5 | Product share | Tỷ trọng sản phẩm k trong tổng xuất khẩu của i |
| 6 | Partner share | Tỷ trọng đối tác j trong tổng xuất khẩu của i |
| 7 | Country growth | Tốc độ tăng trưởng thương mại của nước |
| 8 | World growth | Tốc độ tăng trưởng thương mại của thế giới (benchmark) |
| 9 | HHI (Herfindahl-Hirschman) | Mức độ tập trung thị trường / sản phẩm |
| 10 | NTM indicators | Rào cản phi thuế quan, theo cấu trúc coverage × year × product |
| 11 | GDP growth | Biến vĩ mô, lấy từ WDI qua WITS Development |

> **Chỗ cần bạn xác nhận:** tôi hiểu Tariff ở đây là **thuế mà nước nhập khẩu j áp lên sản phẩm k đến từ nước i** (tức reporter = importer trong TRAINS), chứ không phải thuế nước xuất khẩu áp. Nếu ngược lại thì phải đảo chiều reporter khi gọi API.

---

## Phần 2 — Kết quả kiểm chứng thực tế

Đã chạy 22 phép thử. **20 thành công, 2 thất bại đúng như dự kiến** (chính là hai giới hạn cần biết).

### 2.1. Ba nguồn API hợp lệ duy nhất

WITS chỉ mở đúng 3 datasource; mọi tên khác trả về `403`:

| Datasource | Nội dung | Trạng thái |
|---|---|---|
| `TRN` | UNCTAD TRAINS — thuế quan mức HS6 | Hoạt động |
| `tradestats-trade` | Trade value + 20 chỉ số phái sinh | Hoạt động |
| `tradestats-development` | GDP, GNI... lấy từ WDI | Hoạt động |

Mẫu URL chuẩn:

```
https://wits.worldbank.org/API/V1/SDMX/V21/datasource/{ds}/reporter/{r}/year/{y}/partner/{p}/product/{pr}/indicator/{ind}
```

- Trả về XML (SDMX). Thêm **`?format=JSON`** thì ra JSON — **đã kiểm chứng, hoạt động**.
- Header `Accept: application/vnd.sdmx.data+json` **không có tác dụng**, vẫn trả XML. Guide gốc nói sai chỗ này.

### 2.2. Quy tắc `partner` / `product` — nguồn gây lỗi 404 nhiều nhất

Đây là phát hiện quan trọng nhất khi build pipeline. Mỗi chỉ số có quy định riêng, đọc được từ endpoint metadata:

```
https://wits.worldbank.org/API/V1/wits/datasource/tradestats-trade/indicator/ALL
```

Trong đó `ispartnerequired` / `isproductrequired` cho biết phải truyền giá trị thật hay giá trị "không áp dụng" (`999` cho partner, `999999` cho product). Truyền sai → **404 dù chỉ số vẫn tồn tại**.

| Chỉ số | partner | product | Kết quả thử (VNM, 2000–2023) |
|---|---|---|---|
| `XPRT-TRD-VL` — export value | tên nước | nhóm sản phẩm | 24 năm dữ liệu |
| `MPRT-TRD-VL` — import value | tên nước | nhóm sản phẩm | 24 năm |
| `RCA` | tên nước | nhóm sản phẩm | 24 năm, VD 4.47 (dệt may VN→US 2019) |
| `XPRT-PRDCT-SHR` — product share | tên nước | nhóm sản phẩm | 24 năm |
| `XPRT-PRTNR-SHR` — partner share | tên nước | **999999** | 24 năm, VD 23.21% (US 2019) |
| `CNTRY-GRWTH` | tên nước | nhóm sản phẩm | 24 năm |
| `WRLD-GRWTH` | tên nước | nhóm sản phẩm | 24 năm |
| `HH-MKT-CNCNTRTN-NDX` — HHI | **999** | **999999** | 24 năm, VD 0.0945 (2019) |
| `NDX-XPRT-MKT-PNRTTN` | **999** | **999999** | 24 năm |
| `NMBR-XPRT-HS6-PRDCT` | tên nước | **999999** | 24 năm, VD 2.078 sản phẩm HS6 (VN→US 2019) |
| `NMBR-XPRT-PRTNR` | **999** | **999999** | 24 năm |
| `NMBR-PRDCT-XPRTD` | **999** | **999999** | 24 năm |

Phạm vi thời gian của `tradestats-trade`: **2000–2023** (24 năm) → thừa đủ cho cửa sổ 20 năm 2004–2023.

### 2.3. GDP growth — lấy được, không cần join WDI riêng

```
.../datasource/tradestats-development/reporter/vnm/year/ALL/indicator/NY-GDP-MKTP-KD-ZG
```
→ 36 năm dữ liệu. Lưu ý: endpoint này **không nhận** `partner`/`product`. Các mã đã thử OK: `NY-GDP-MKTP-KD-ZG` (GDP growth %), `NY-GDP-MKTP-CD`, `NY-GDP-PCAP-CD`, `NY-GNP-PCAP-CD`. Guide gốc gợi ý mã `GDP-CURRENT-USD` — **mã này không tồn tại, trả 404**.

### 2.4. Tariff HS6 — lấy tốt, đây là điểm mạnh nhất

```
.../datasource/TRN/reporter/{numeric}/partner/{numeric}/product/{HS6|ALL}/year/{y}/datatype/reported
```

- TRAINS dùng **mã số** (704 = VN, 840 = US), không dùng ISO3 chữ.
- `partner=000` → **MFN**; `partner=<mã nước>` → **PREF** (thuế ưu đãi). Đã xác nhận cả hai.
- `product=ALL` cho **một năm** → trả về **5.388 dòng HS6** trong ~2,7 giây. Rất hiệu quả.
- Mỗi dòng có: `OBS_VALUE` (SimpleAverage), `MIN_RATE`, `MAX_RATE`, `TOTALNOOFLINES`, `NBR_PREF_LINES`, `NBR_MFN_LINES`, `NOMENCODE` (VD H5).
- Danh mục sản phẩm TRAINS có **6.882 mã HS6** → đủ độ chi tiết bạn cần.

**Kiểm tra độ phủ trước khi chạy** bằng endpoint availability (rất nhanh, 1,2 giây cho toàn thế giới):

```
https://wits.worldbank.org/API/V1/wits/datasource/trn/dataavailability/country/ALL/year/2019
→ 121 nước có dữ liệu thuế năm 2019
https://wits.worldbank.org/API/V1/wits/datasource/trn/dataavailability/country/704/year/ALL
→ Việt Nam: 22 năm, nhưng có lỗ hổng (thiếu 2000, 2011) và dừng ở 2021
```

> **Cảnh báo lịch trình:** tariff của TRAINS **trễ hơn trade data**. Việt Nam mới nhất là **2021**, trong khi trade value có đến **2023**. Phải kiểm tra `dataavailability` cho từng nước trước khi chốt cửa sổ 20 năm, nếu không panel sẽ thủng ở các năm cuối.

### 2.5. Giới hạn kỹ thuật đã đo được

| Phép thử | Kết quả |
|---|---|
| `partner=ALL` + `year=ALL` (TradeStats) | **200 OK** — 3.759 quan sát, 237 đối tác, trong 2,2 giây |
| `product=ALL` + `year=ALL` (TRAINS) | **HTTP 413** — quá tải, phải lặp theo từng năm |

→ Quy tắc thực tế: **tối đa 2 chiều `ALL`**, và với TRAINS thì `product=ALL` đã "ăn" gần hết ngân sách nên phải cố định năm. Guide gốc mô tả đúng điểm này.

---

## Phần 3 — Ba điểm nghẽn thật sự (khác với những gì guide gốc nói)

### 3.1. NGHẼN LỚN NHẤT — WITS API **không** cung cấp trade value ở mức HS6

Đây là sai lệch nghiêm trọng nhất giữa guide và thực tế.

```
.../tradestats-trade/reporter/vnm/year/2019/partner/usa/product/610910/indicator/XPRT-TRD-VL
→ HTTP 400 Invalid_Product
```

Lý do: danh mục sản phẩm của `tradestats-trade` **chỉ có 31 mã**, toàn là **nhóm ngành** — kiểm chứng bằng:

```
https://wits.worldbank.org/API/V1/wits/datasource/tradestats-trade/product/all
```

Danh sách đầy đủ 31 mã đó: `Total`, `01-05_Animal`, `06-15_Vegetable`, `16-24_FoodProd`, `25-26_Minerals`, `27-27_Fuels`, `28-38_Chemicals`, `39-40_PlastiRub`, `41-43_HidesSkin`, `44-49_Wood`, `50-63_TextCloth`, `64-67_Footwear`, `68-71_StoneGlas`, `72-83_Metals`, `84-85_MachElec`, `86-89_Transport`, `90-99_Miscellan`, cùng vài nhóm SITC (`Food`, `Fuels`, `manuf`, `Textiles`, `OresMtls`, `AgrRaw`, `Chemical`...).

**Hệ quả: biến lõi số 1 và số 2 — thứ để dựng spell-level dataset — không lấy được qua API này.** Ba lối đi thay thế:

| Lối đi | Đánh giá |
|---|---|
| **WITS Advanced Query** (giao diện web, phải Register/Login) | Cho phép trích trade value HS6 và tải CSV. Đây là con đường "chính thống" của WITS nhưng **thủ công**, không script được, và có hạn mức mỗi truy vấn. |
| **UN Comtrade API** (nguồn gốc của WITS) | **Đã kiểm chứng chạy được**: `comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=704&period=2019&partnerCode=842&cmdCode=610910&flowCode=X` trả đúng giá trị HS6 (VN→US, áo dệt kim 2019 = 619.933.081 USD). **Nhưng endpoint `preview` chặn cứng ở 500 dòng** — thử lấy toàn bộ HS6 cho một cặp nước-năm chỉ nhận được 500/≈4.000 dòng. Cần **đăng ký API key miễn phí** để dùng endpoint đầy đủ. |
| Bulk file HS6 | Comtrade có gói bulk theo reporter-year, nhanh hơn nhiều so với lặp từng dòng. |

**Khuyến nghị: đăng ký API key Comtrade miễn phí và lấy trade value HS6 từ đó, giữ WITS cho tariff + các chỉ số phái sinh.** Dữ liệu WITS vốn cũng lấy từ Comtrade nên hai nguồn nhất quán về gốc.

### 3.2. NGHẼN THỨ HAI — Dữ liệu NTM công khai gần như vô dụng cho panel

Đã tải và mở cả 3 file:

| File | Dòng | Cấu trúc thật | Vấn đề |
|---|---|---|---|
| `NTM-Trade-Frequency-Coverage-Ratio.zip` | **152** | CountryISO3, year, TradeFlow, coverage ratio, frequency ratio | Chỉ **76 nước**, chỉ các năm **2012–2017** (riêng 2015 và 2016 chiếm 116/152 dòng), **không có chiều sản phẩm**, có cả dòng rác (`year = 75`) |
| `NTM-Prevalence-Sector.zip` | 3.943 | ReporterISO3, Sector, NTM Type Count, Share % | **Không có cột year** — chỉ là lát cắt một thời điểm |
| `NTM-Indicators-Measure-Sector.zip` | 24.264 | ReporterISO3, NTMCode, NTMDescription, Sector, coverage/frequency ratio | **Không có cột year**, sản phẩm chỉ ở mức **Sector**, không phải HS6 |

→ **Không thể xây biến NTM theo cấu trúc `coverage × year × product` như bạn muốn từ nguồn công khai này.** Ba lựa chọn:

1. Hạ yêu cầu: dùng NTM như biến **cross-section** (một giá trị/nước, hoặc nước × ngành), coi như đặc trưng cố định.
2. Lấy dữ liệu chi tiết hơn từ **UNCTAD TRAINS Online** (`trainsonline.unctad.org`) — nơi có file HS6 dạng STATA.
3. Bỏ NTM khỏi mô hình chính, để phần robustness check.

### 3.3. NGHẼN THỨ BA — Các chỉ số dựng sẵn (Export Duration, RCA bulk...) đã rời khỏi WITS

Trang bulk download mà guide dẫn tới **không còn chứa file tải về**. Toàn bộ mục "Trade Indicators" nay chỉ là **link trỏ sang World Bank Data Catalog**:

- Export Duration → `datacatalog.worldbank.org/search/dataset/0064728`
- Export Duration (Mirrored) → `.../0064723`
- Decomposition of Export Growth along Margins of Trade → `.../0064706`
- Growth Orientation of Markets → `.../0064704`
- Export Portfolio and Factor Endowments → `.../0064717`
- (cùng các mục HHI Market/Product Concentration, Sectoral Composition RCA/CAGR...)

Tôi **chưa xác minh được nội dung file thật** vì API của Data Catalog liên tục trả `HTTP 429 rate limit` từ máy này qua nhiều lần thử. **Bạn nên mở trực tiếp các link trên bằng trình duyệt** để xem định dạng và độ phủ năm.

Ngoài ra, trên `datadownload.aspx`: **2 trong 4 link đã chết** — `wits_en_at-a-glance_allcountries_allyears.zip` và `wits_en_trade_summary_allcountries_allyears.zip` đều trả về trang HTML "Page not found" (2.994 byte) thay vì file zip.

> Điểm tích cực: **RCA, HHI, product share, partner share, country/world growth đều lấy được trực tiếp qua API** (mục 2.2), nên việc bulk download hỏng **không chặn** bạn — chỉ mất kênh đối chiếu.

---

## Phần 4 — Bảng nguồn cuối cùng cho từng biến

| # | Biến | Nguồn thật sự dùng được | Đã kiểm chứng |
|---|---|---|---|
| 1-2 | Trade value HS6 (export/import) | **UN Comtrade API** (cần key miễn phí) hoặc WITS Advanced Query thủ công | Chạy được ở mức 1 sản phẩm; cần key để lấy đủ |
| 3 | Tariff (MFN + Preferential) | WITS API `TRN`, mức HS6 | 5.388 dòng/nước/năm |
| 4 | RCA | WITS API `tradestats-trade`, `indicator=RCA` | 24 năm |
| 5 | Product share | `XPRT-PRDCT-SHR` | 24 năm |
| 6 | Partner share | `XPRT-PRTNR-SHR` (product = 999999) | 24 năm |
| 7 | Country growth | `CNTRY-GRWTH` | 24 năm |
| 8 | World growth | `WRLD-GRWTH` | 24 năm |
| 9 | HHI | `HH-MKT-CNCNTRTN-NDX` (partner = 999, product = 999999) | 24 năm |
| 10 | NTM | File công khai WITS **không đủ**; cần TRAINS Online | Đã tải, xác nhận thiếu chiều year/product |
| 11 | GDP growth | `tradestats-development`, `NY-GDP-MKTP-KD-ZG` | 36 năm |
| — | Export Duration (đối chiếu) | World Bank Data Catalog (link ngoài) | Chưa xác minh được (429) |

**Lưu ý về đơn vị:** trade value của WITS tính bằng **nghìn USD**, còn Comtrade trả **USD**. Phải quy đổi khi ghép hoặc đối chiếu hai nguồn.

Điểm quan trọng: **RCA, product share, partner share, HHI, growth từ WITS đều ở mức nhóm ngành, không phải HS6.** Nếu mô hình cần các biến này ở mức tariff-line, bạn phải **tự tính từ trade value HS6 của Comtrade** theo công thức Balassa (RCA) và Herfindahl (HHI) — chứ không lấy sẵn được.

---

## Phần 5 — Việc cần làm tiếp, theo thứ tự

1. **Xác nhận với tôi hướng của biến Tariff** (mục 1.3) trước khi kéo dữ liệu — sai chiều là phải kéo lại toàn bộ.
2. **Đăng ký API key miễn phí của UN Comtrade** — đây là đường găng, mọi thứ khác phụ thuộc vào trade value HS6.
3. **Chốt danh sách nước bằng dữ liệu, không bằng cảm tính**: chạy `dataavailability` của TRAINS cho toàn bộ nước qua từng năm, giao với số năm có mặt trong `tradestats-trade`, rồi mới chọn 82 exporters × 53 importers thỏa tiêu chí "báo cáo đều đặn".
4. **Chốt cửa sổ thời gian** sau khi có kết quả bước 3 — nhiều khả năng phải là **2004–2023** cho trade và chấp nhận tariff thiếu 1–2 năm cuối.
5. **Kéo tariff HS6** qua WITS API: lặp theo `reporter × year`, mỗi call `product=ALL`. Với 53 importers × 20 năm ≈ 1.060 call, mỗi call ~3 giây → khoảng **1 giờ**. Rất khả thi.
6. **Kéo trade value HS6** qua Comtrade, rồi **dựng spell-level dataset**: xác định năm bắt đầu/kết thúc mỗi bộ ba (i, j, k), áp ngưỡng tồn tại (WITS dùng **10.000 USD**), gắn cờ right-censored, loại left-censored.
7. **Tự tính RCA/HHI ở mức HS6** từ panel Comtrade; dùng số liệu WITS mức nhóm ngành làm kiểm tra chéo.
8. **Quyết định số phận biến NTM** theo 3 lựa chọn ở mục 3.2.

---

## Phụ lục — Cách chạy lại kiểm chứng

```bash
cd /home/minhquang/wits
python3 scripts/wits_probe.py
```

Script chạy khoảng 1 phút, ghi ra `probe_out/`:

- `_probe_log.csv` — nhật ký đầy đủ 22 phép thử: nhãn, mã HTTP, số dòng, giá trị mẫu, URL gốc.
- `trade_*.csv`, `dev_*.csv` — panel 24/36 năm cho từng chỉ số.
- `tariff_mfn_all.csv`, `tariff_usa_all.csv` — biểu thuế HS6 đầy đủ (5.388 dòng mỗi file).
- `panel_demo.csv` — panel mẫu 2 exporters × 2 importers × 3 năm, đúng hình dạng dữ liệu cuối cùng.
