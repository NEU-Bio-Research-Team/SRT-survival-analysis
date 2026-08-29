# Tiến độ so với brief "Sinking Relationships"

*Đối chiếu trực tiếp từng mục của `Sinking Relationships.md` với những gì thực
sự có trên đĩa. Số liệu đếm trực tiếp trên file, cập nhật **25/08/2026** sau đợt
bổ sung NTM / thuế Mỹ / CBAM / EPI.*

> 📄 **Bản kiểm kê đầy đủ cho cộng sự, kèm cách đọc từng cột mới:**
> [DATA_HANDOFF.md](DATA_HANDOFF.md). Tài liệu này giữ lại phần bối cảnh và các
> quyết định đã chốt.

**Panel hiện tại:** `analysis/panel_final.csv` — **747.719 episode × 154 cột**,
cửa sổ **2003–2025**, 147 nước nhập khẩu, 4.599 nhóm sản phẩm, **228.175 spell**
(170.486 chết, 57.689 right-censored = 25,3%).

Bản tiếng Anh chi tiết hơn: [BRIEF_SINKING_COVERAGE.md](BRIEF_SINKING_COVERAGE.md).
Kiểm kê dữ liệu: [DATA_INVENTORY_VN.md](DATA_INVENTORY_VN.md).

---

## 1. Một màn hình: đang ở đâu

```
THU THẬP DỮ LIỆU
  §1 Xuất khẩu VN×nước×HS6×năm    █████████████████████ 100%  2002–2025
  §1 Dựng spell (start/end/censor) █████████████████████ 100%  228.175 spell
  §2 Thuế MFN                      ██████████████████░░░  90%  2024–25 không có số thật
  §2 Thuế ưu đãi FTA               ████████████░░░░░░░░   60%  dừng 2021, không gỡ được
  §2 Thuế đối ứng Mỹ 2025          █████████████████████ 100%  25/08: theo tháng + phạm vi sản phẩm
  §3 Distance / GDP / RTA          █████████████████████ 100%
  §3 Product complexity            █████████████████████ 100%
  §4 Green LPI (robustness)        █████████████████████ 100%  4 công thức
  §4 NTM (UNCTAD TRAINS)           █████████████████████ 100%  25/08: HS6 × năm, 95,2% episode
  §4 CBAM của EU                   █████████████████████ 100%  25/08: brief có yêu cầu, trước đó trống
  §5 Panel sạch + tài liệu độ phủ  █████████████████████ 100%

CHUẨN BỊ MÔ HÌNH
  Đo độ nhạy ngưỡng spell          █████████████████████ 100%  đã có bằng chứng
  Kaplan–Meier / baseline hazard   █████████████████████ 100%  đã chạy, §2d
  L0 benchmark → L1 → L2/L3        ░░░░░░░░░░░░░░░░░░░░    0%
```

**Câu trả lời một dòng (25/08):** phần **thu thập dữ liệu đã xong** — không còn
hạng mục nào chờ người, và không còn hạng mục nào máy làm được mà chưa làm. Ba
thứ còn thiếu là thiếu vĩnh viễn ở nguồn (thuế ưu đãi theo mã nhóm, thuế
2024–2025, NTM trước 2010). Điểm nghẽn nằm trọn ở **chưa chạy mô hình nào** và ở
**các định nghĩa cần cả nhóm chốt**.

---

## 2. Brief yêu cầu gì, đã có gì

### §1. Dữ liệu xuất khẩu — ✅ xong

| Brief yêu cầu | Thực tế |
|---|---|
| VN × nước nhập khẩu × HS6 × năm | ✅ 147 nước, 4.599 nhóm sản phẩm ổn định |
| Kim ngạch (value) | ✅ 100% |
| **Khối lượng (quantity)** | ✅ 96,5% — `net_weight_kg` và `unit_value_usd_per_kg`. Brief có hỏi mục này, trước 22/08 chưa bao giờ được đưa vào panel |
| Giai đoạn ≥ 2002–2024 | ✅ **2002–2025**, vượt yêu cầu của brief một năm |
| Dựng spell: năm bắt đầu, năm kết thúc, right-censored | ✅ **228.175 spell**; có sẵn cả `spell_start_year`, `spell_end_year`, `right_censored` lẫn dạng counting-process `(t_start, t_stop, event)` để chạy thẳng Cox |

**Quy tắc "chết":** kim ngạch tụt dưới 10.000 USD thì spell đứt. Nước ngừng nộp
báo cáo (Nga, Belarus từ 2022…) được **kiểm duyệt hành chính**, không tính là
chết — nếu không mô hình sẽ đọc thành "FTA giết chết quan hệ".

### §2. Dữ liệu thuế — ⚠️ xong phần chính, còn hai hạn chế

| Brief yêu cầu | Thực tế |
|---|---|
| Thuế MFN | ⚠️ **96,9% episode có thuế**, nhưng chỉ **83,8% đo đúng năm**: 2003–2023 đạt 95–99%, còn **2024–2025 bằng 0%** vì TRAINS trả 404 cho hai năm này. Cột `tariff_source_year` ghi rõ giá trị lấy từ năm nào |
| Thuế ưu đãi FTA | ⚠️ chỉ 13 nước khai riêng cho VN, và **không nước nào khai cho 2022–2023** |
| **Lịch sử thuế đối ứng Mỹ 2025 (46%→10%→20%/40%)** | ✅ lấy được đầy đủ ở **cấp quốc gia** — xem dưới |

**Thuế Mỹ 2025 — đúng như brief mô tả.** Ghi chú cũ của dự án nói cần key trả
tiền của WTO I-TIP; **sai**. Nó nằm ngay trong chương 99 biểu thuế Mỹ, USITC mở
REST API công khai:

| Dòng thuế | Mức | Từ ngày | Trạng thái |
|---|---|---|---|
| 9903.01.72 | **+46%** | 9/4/2025 | đã bị thay thế |
| 9903.01.25 | +10% | sàn chung mọi nước | còn hiệu lực |
| 9903.02.69 | **+20%** | 7/8/2025 | còn hiệu lực |
| 9903.02.01 | **+40%** | hàng bị xác định trung chuyển | còn hiệu lực |

Toàn bộ **85 nước** đều có, nên nhóm cạnh tranh mà brief liệt kê đã sẵn sàng cho
kiểm soát trade diversion: Campuchia 49→19%, Bangladesh 37→20%, Thái Lan 36→19%,
Đài Loan 32→20%, Indonesia 32→19%, Ấn Độ 26→25%, Malaysia 24→19%, Trung Quốc 34%.

> ⚠️ **Hạn chế 1 — thuế Mỹ 2025 mới ở cấp quốc gia, chưa ở cấp sản phẩm.**
> Danh sách hàng được miễn nằm trong ghi chú pháp lý *U.S. note 2(v)(iii)(a)*,
> REST API không trả về. File PDF đã tải sẵn (14 MB), chưa bóc tách. Với Việt
> Nam đây không phải chi tiết nhỏ: **điện tử vừa là mặt hàng xuất sang Mỹ lớn
> nhất, vừa là nhóm dễ được miễn nhất**.

> ⚠️ **Hạn chế 2 — TRAINS không phát hành biểu thuế ưu đãi nào cho 2022–2023.**
> Đã hỏi thẳng Nhật (392), Hàn (410), Ấn (152), EU (918) với partner = VN (704):
> đều trả 404, trong khi 2021 trả dữ liệu thật. Hệ quả: hai năm cuối có
> **101.280 episode MFN so với 239 PREF**, tức **mức thuế bị khai cao hơn thực
> tế** với khoảng 39% episode đang có FTA hiệu lực. Cột `fta_in_force` đánh dấu
> đúng những dòng đó nên sai lệch *nhìn thấy được*, nhưng không nguồn công khai
> nào sửa được. **Phải nêu trong Limitations.**

### §3. Covariate gravity/survival — ✅ xong cả bốn

| Brief yêu cầu | Nguồn | Độ phủ |
|---|---|---|
| Khoảng cách địa lý | CEPII Gravity V202211 | **100%** (nguồn dừng 2021, mang sang các năm sau và có cột `gravity_source_year` đánh dấu) |
| GDP, GDP/người đối tác | World Bank WDI | **100%** |
| Có FTA/RTA với VN, năm hiệu lực | DESTA, đã kiểm chứng 19/19 mốc | **100%**, biến thiên theo thời gian tốt |
| **Độ phức tạp sản phẩm (PCI)** | Atlas of Economic Complexity v18 (Harvard) | **100%** |

Về PCI: Atlas công bố ở HS92 **4 số**, panel dựng trên nhóm 6 số khoá theo H0 —
mà **H0 chính là HS1992** — nên phép nối chỉ là lấy 4 ký tự đầu, không qua bảng
chuyển đổi nào và **không mất dòng nào**: 1.216/1.216 nhóm khớp.

### §4. Robustness — ✅ Green LPI xong · ⏳ NTM chờ bạn

**Green LPI: có 3 công thức đã công bố, và chúng không đồng ý với nhau.** Đã
kiểm chứng metadata qua Crossref và Emerald (không lấy từ trí nhớ), dựng cả 4
biến thể vào `analysis/glpi.csv`:

| Cột | Cách dựng | Nguồn |
|---|---|---|
| `glpi_pca_lpi_epi` ← **chính** | min–max rồi PCA trên LPI + EPI | El-Nakib & Elzarka (2026), *Logistics* 10:56 |
| `glpi_ratio_lpi_epi` | dạng tỷ số LPI/EPI | họ công thức của Starostka-Patyk, Bajdor & Białas (2024), *Ecological Indicators* 158:111396 |
| `glpi_pca_components` | PCA trên 6 chỉ số thành phần LPI + CO2/người + tỷ lệ năng lượng tái tạo | Lau (2011), *Benchmarking* 18(6):873–896 |
| `glpi_equal_weights` | trung bình đều, cùng đầu vào với trên | đối chứng: kết quả có phụ thuộc PCA không |

**Ba điều đo được, đáng để biết trước khi chọn:**

1. **Biến thể tỷ số xếp hạng gần như ngược với biến thể PCA** (tương quan hạng
   Spearman **−0,463**). Nước giàu có cả LPI cao lẫn EPI cao; chia cho nhau thì
   triệt tiêu, phần còn lại đo "logistics tốt so với môi trường kém". Chọn công
   thức nào **sẽ đổi kết luận**, không phải khác biệt nhỏ.
2. **Với đúng 2 đầu vào, "PCA-weighted" chính là trung bình trọng số bằng nhau**
   (0,707/0,707). Biến thể 1 nghe kêu hơn thực chất.
3. **Trong dữ liệu công khai, logistics tốt đi kèm môi trường xấu.** Ở biến thể
   3, CO2 (đã đảo dấu) tải **−0,241** và năng lượng tái tạo **−0,223**, ngược
   dấu với cả 6 chỉ số LPI. Nên mọi chỉ số gộp hai trụ cột sẽ bị chi phối bởi
   trụ cột nào được cho trọng số lớn hơn.

> ⚠️ **GLPI chỉ phủ 22–25% country-year.** LPI là khảo sát **theo đợt** (2007,
> 2010, 2012, 2014, 2016, 2018, 2022), không phải chuỗi hàng năm; EPI hiện chỉ
> lấy được **một lát cắt 2026** (API kho lưu trữ của Yale đang lỗi 500). Không
> công thức nào gỡ được — đây là thuộc tính của nguồn. Trong panel, GLPI được
> nối theo **đúng đợt khảo sát LPI**, có cột `importer_lpi_source_year` ghi rõ
> giá trị lấy từ đợt nào.

**NTM — hoá ra máy tự lấy được, không cần tài khoản.** Đây là đính chính một
điều mà **mọi tài liệu trước của dự án đều nói sai**, kể cả lời tôi.

Ba file NTM công khai của WITS không có chiều năm ở mức sản phẩm: mọi sản phẩm
cùng ngành (16 nhóm) nhận cùng một giá trị, một lát cắt duy nhất, và **20,4%
episode không có bản ghi nào** — trong đó có Trung Quốc và Hàn Quốc.

Ghi chú cũ nói phải có tài khoản Azure AD của TRAINS Online mới lấy được bản
HS6 × năm. **Sai.** Endpoint `POST api-trains2.unctad.org/denormalisedMeasures`
trả lời **không cần đăng nhập**: cURL bạn gửi không có header `Authorization`,
không có cookie, và replay nguyên văn từ máy chưa từng đăng nhập vẫn nhận về
157 KB dữ liệu thật.

**Vì sao kết luận sai đó tồn tại lâu:** endpoint trả `200` kèm **mảng rỗng** khi
body sai — nhìn y hệt bị chặn quyền. Lỗi cụ thể: trường `affectedCountries`
**bắt buộc phải chứa đủ danh sách id các nước**, kể cả khi đã bật
`allAffectedCountries: true`. Gửi rỗng thì luôn nhận mảng rỗng, đăng nhập hay
không cũng vậy. Bài học rộng hơn: **"thành công nhưng rỗng" không phải bằng
chứng của lỗi phân quyền** — đáng lẽ phải thử một body chuẩn trước khi viết hạn
chế đó vào bốn tài liệu.

**Dữ liệu lấy được đúng thứ cần.** Mỗi bản ghi là một *biện pháp*, kèm `hsCode`
(danh sách HS6 mà biện pháp phủ), `implementationDate`, `repealDate`,
`yearsOfDataCollection`, `ntmCode` (mã MAST như `A14`), nước áp dụng và nước bị
ảnh hưởng. Có ngày hiệu lực **và** ngày thu hồi nghĩa là dựng được NTM **biến
thiên theo năm ở mức HS6**.

**Độ phủ:** `selection/trains_countries.csv` — 165 nước áp dụng, **133 nước
trong panel của ta**, cộng **EU dạng khối** (`trains_id` 279, đúng cách EU khai
biện pháp, y như thuế). 15 nước thật sự không có: AGO, BLZ, BMU, CAF, DOM,
**GBR**, KNA, LCA, MAC, MDG, MDV, MNG, PYF, UKR, VCT.

> ❌ **ĐÃ CHỐT (24/08): không kéo được bằng script từ máy này.** Probe chạy hết
> lịch backoff để có số đo thay vì cảm tính: **6 lần 429 liên tiếp**, tổng chờ
> ~31 phút (60+120+240+480+960 giây), giãn tới **61 giây/request** vẫn bị từ
> chối. Trong suốt thời gian đó các endpoint GET tra cứu vẫn trả 200 bình
> thường — nghĩa là giới hạn áp riêng cho route POST tốn kém, không phải sự cố
> chung. Ở `pageSize` 20 thì một lần kéo đầy đủ là vài nghìn request; một route
> từ chối request thứ hai sau một phút nghỉ không thể phục vụ việc đó.
>
> **Nên phải đi đường trình duyệt.** Xem §4.
>
> ⚠️ **Chi tiết đo được về rào cản:** `pageSize` bị chặn ở **20**
> (từ 50 trở lên trả 400), và host nằm sau Cloudflare: **error 1015 sau khoảng
> sáu request liên tiếp**, vẫn dính ngay cả khi giãn 6 giây/request; backoff 45,
> 90 và 135 giây đều chưa được thả. Nên bản kéo dữ liệu phải chạy chậm, có
> resume, và biết dừng. `scripts/fetch_ntm_trains.py` đã viết theo đúng dạng đó:
> mỗi trang lưu một file, chạy lại thì bỏ qua trang đã có, và **nhịp chờ học
> được sẽ ghi xuống đĩa** để lần chạy sau không phải dò lại từ đầu.

### §5. Sản phẩm giao ra — ✅ đủ

Brief đòi "một bảng panel sạch × 6 cột" và "cột spell_start/spell_end/censored":

| Cột brief nêu | Độ phủ |
|---|---|
| `import_value_usd` | 100% |
| `tariff_rate` | 96,9% (xem cảnh báo §2 về 2024–2025) |
| `dist` | 100% |
| `importer_gdp_usd`, `importer_gdp_per_capita_usd` | 100% |
| `fta_in_force` | 100% |
| `pci` | 100% |
| `spell_start_year` / `spell_end_year` / `right_censored` | 100% |
| `net_weight_kg` / `unit_value_usd_per_kg` | 96,2% |
| `importer_glpi_*` (4 biến thể) | 98,8% |

---

## 2b. Cú sốc thuế Mỹ 2025 hiện ra trong dữ liệu như thế nào

Đây là phần quan trọng nhất của cả đợt mở cửa sổ, và có **một quy ước ngày tháng
phải nắm cho đúng, nếu không sẽ đọc sai hoàn toàn**.

**Quy ước:** `event = 1` ở năm Y nghĩa là **năm cuối cùng quan hệ còn sống là
Y** — tức nó **chết trong năm Y+1**. Vậy nên:

* `event` ở **2023** = quan hệ chết trong **2024**
* `event` ở **2024** = quan hệ chết trong **2025** ← đây là cú sốc thuế Mỹ
* `event` ở **2025** = **luôn bằng 0**, vì 2025 là năm cuối panel nên mọi quan hệ
  còn sống đều bị right-censored theo định nghĩa

Đo trên panel:

| | Số quan hệ |
|---|---|
| Chết trong năm 2025 (event dated 2024) | **7.157** |
| Trong đó nước nhập khẩu **thực sự có nộp báo cáo 2025** | **7.157 — 100%** |
| Riêng thị trường Mỹ: chết trong 2024 · chết trong 2025 | **149 · 157** |
| Quan hệ với Mỹ còn sống tới 2025 | **1.863** |

**Con số 100% ở dòng thứ hai không phải trùng hợp — đó là cơ chế bảo vệ đang
chạy đúng.** Nước nào không nộp 2025 thì năm quan sát cuối của nó là 2024, nên
spell chạy tới 2024 bị kiểm duyệt hành chính chứ không tính là chết. Nghĩa là
**không có cái chết giả nào** sinh ra từ việc 58 nước chưa nộp báo cáo.

Mười thị trường có nhiều quan hệ chết trong 2025 nhất: Philippines 230,
Singapore 226, Malaysia 225, Indonesia 217, Hàn Quốc 212, Ấn Độ 198, Thái Lan
174, Ả Rập Xê Út 162, Úc 160, **Mỹ 157**.

> ⚠️ **Hai điều phải xử lý ở khâu mô hình, không phải khâu dữ liệu:**
>
> 1. **Lệch pha giữa biến và sự kiện.** Thuế Mỹ có hiệu lực tháng 4 và tháng
>    8/2025, nhưng cái chết do nó gây ra được ghi ở episode **năm 2024**. Mô
>    hình phải hoặc dùng biến thuế dạng *lead*, hoặc định nghĩa lại năm sự kiện
>    là `end + 1`. Nếu ghép thẳng thuế-2024 với event-2024 là ghép sai năm.
> 2. **2024–2025 không có biến thiên thuế thật.** TRAINS trả 404 cho cả hai năm,
>    nên `tariff_rate` ở đó là giá trị 2023 mang sang (`tariff_source_year` ghi
>    rõ). Biến thuế duy nhất *thật sự* biến thiên trong 2025 là bảng thuế Mỹ
>    trong `analysis/us_tariffs_2025.csv`, và nó ở **cấp quốc gia**. Nói cách
>    khác: cú sốc nhận dạng được cho **thị trường Mỹ**, chưa nhận dạng được ở
>    mức sản phẩm.

---

## 2c. Spell một năm: đã đo, và kết luận là đừng nâng ngưỡng

Bạn bảo "ok nếu nó giúp cải thiện". Tôi đã đo thay vì đoán —
[analysis/threshold_sensitivity.csv](../analysis/threshold_sensitivity.csv),
dựng lại spell ở 5 ngưỡng từ cùng một lượt đọc dữ liệu:

| Ngưỡng | Spell | Sự kiện | **Spell 1 năm** | Trung vị | ≥10 năm | Giá trị XK giữ được |
|---|---|---|---|---|---|---|
| 1.000 USD | 345.740 | 266.410 | **55,3%** | 1 năm | 7,9% | 100,00% |
| **10.000 USD** ← đang dùng | 228.175 | 170.486 | **52,7%** | 1 năm | 8,9% | **99,97%** |
| 50.000 USD | 140.912 | 100.195 | 48,9% | 2 năm | 10,5% | 99,81% |
| 100.000 USD | 108.051 | 74.427 | 46,6% | 2 năm | 11,3% | 99,64% |
| 500.000 USD | 53.340 | 33.924 | **41,9%** | 2 năm | 13,1% | 98,55% |

**Đọc bảng này:** nâng ngưỡng **500 lần** thì mất **85% số spell** nhưng chỉ mất
**1% giá trị xuất khẩu** — tức các quan hệ nhỏ đúng là không đáng kể về kinh tế.
**Nhưng** tỷ lệ spell-1-năm chỉ giảm **13,4 điểm** (55,3% → 41,9%).

Đó là hình dạng của **hành vi thật**, không phải của một sản phẩm phụ do ngưỡng
tạo ra. Khối quan hệ chết sau một năm sống sót qua **mọi** ngưỡng còn để lại mẫu
dùng được. Nâng ngưỡng mua được một chút thời lượng với cái giá rất lớn về cỡ
mẫu, **mà không giải quyết được vấn đề**.

> **Đề xuất: giữ nguyên ngưỡng 10.000 USD** (đã giữ 99,97% giá trị xuất khẩu),
> và **mô hình hoá năm đầu một cách tường minh** — split-population/cure model,
> hoặc tách riêng hazard năm thứ nhất. Tức là xử lý khối một năm như một hiện
> tượng cần giải thích, chứ không định nghĩa nó ra khỏi mẫu.

---

## 2d. Đã chạy baseline survival — panel dùng được, và lộ ngay vấn đề nhận dạng

Đây **không phải** ước lượng của bài báo. Đây là phép kiểm tra đáng lẽ phải làm
trước khi ai đó xây tiếp: panel có thật sự chạy được mô hình duration không, hay
mới chỉ được mô tả đẹp trên giấy. Script:
[scripts/survival_baseline.py](../scripts/survival_baseline.py), chạy 12 giây,
đỉnh RAM 1,1 GB.

### Kaplan–Meier — xác suất sống sót S(t)

| t (năm) | Tất cả | Có FTA | Không FTA |
|---|---|---|---|
| 1 | 0,531 | **0,629** | **0,454** |
| 2 | 0,389 | 0,506 | 0,297 |
| 3 | 0,320 | 0,443 | 0,225 |
| 5 | 0,253 | 0,378 | 0,156 |
| 10 | 0,189 | **0,313** | **0,095** |
| **Trung vị** | **2 năm** | **3 năm** | **1 năm** |

**47% quan hệ chết ngay trong năm đầu.** Và khoảng cách FTA rất lớn: đến năm thứ
10, nhóm có FTA còn sống **31,3%** so với **9,5%** ở nhóm không FTA — gấp hơn ba
lần. Đây là đường cong chưa kiểm soát biến nào, nên một phần phản ánh việc đối
tác FTA thường là thị trường lớn và giàu; nhưng với mục đích kiểm chứng thì nó
cho thấy dữ liệu mang tín hiệu thật, không phải nhiễu.

### Mô hình hazard rời rạc (complementary log-log)

Cox là phản xạ quen thuộc nhưng **sai công cụ cho panel này**: thời lượng là số
năm nguyên nên "trùng hạng" (ties) không phải ngoại lệ mà là phổ biến tuyệt đối,
và partial likelihood của Cox khi đó phụ thuộc hoàn toàn vào một phép xấp xỉ xử
lý ties. Mô hình grouped-data proportional hazards (cloglog trên episode-năm)
đúng là cùng giả định tỷ lệ hazard, áp lên dữ liệu vốn dĩ bị kiểm duyệt theo
khoảng — mà khai báo hải quan theo năm chính là như vậy. Hệ số đọc y hệt Cox:
log hazard ratio.

Trên **724.270 episode dùng được (96,9%)**, hội tụ sau 9 vòng lặp:

| Biến | Hazard ratio | z | Đọc thế nào |
|---|---|---|---|
| `log_value` | **0,547** | −142 | Quan hệ càng lớn càng khó chết — hiệu ứng mạnh nhất, đúng như literature |
| `log_rca_1p` | **0,787** | −74 | Có lợi thế so sánh thì bền hơn |
| `fta_in_force` | **0,768** | −39 | **FTA giảm hazard ~23%** |
| `log_gdp` | 0,928 | −22 | Thị trường lớn bền hơn |
| `log_dist` | 0,935 | −21 | ⚠️ **ngược dấu kỳ vọng** |
| `pci` | 0,954 | −17 | Sản phẩm phức tạp hơn thì bền hơn chút |
| `partner_share_pct` | 0,983 | −4,4 | |
| `log_tariff_1p` | **0,987** | **−4,9** | ⚠️ **ngược dấu — thuế cao đi kèm hazard THẤP** |

> ⚠️ **Hai hệ số ngược dấu, và cái thứ hai đánh thẳng vào giả định của đề tài.**
>
> **Thuế** ra dấu âm: thuế cao đi kèm xác suất chết *thấp hơn*. Nếu đọc ngây thơ
> thì trái ngược toàn bộ lập luận của brief. Ba cách giải thích, phải phân biệt
> được mới đi tiếp:
> 1. **Chưa có fixed effects.** Đây là so sánh chéo: ngành có thuế MFN cao (dệt
>    may, nông sản) cũng chính là ngành Việt Nam có quan hệ lớn và lâu đời.
> 2. **Thuế bị đo sai có hệ thống** — ưu đãi khai theo mã nhóm nên nhiều episode
>    bị gán MFN cao hơn thực tế, và `fta_in_force` trong cùng mô hình đang hút
>    mất phần hiệu ứng ưu đãi.
> 3. **Nội sinh** — đúng thứ bảng thẩm định của brief tự chấm 6/10 ở mục
>    *Identification credibility*.
>
> **Khoảng cách** cũng ra dấu âm, nhiều khả năng do chọn lọc: thị trường xa mà
> Việt Nam còn xuất được thì thường là thị trường đã được sàng lọc, quy mô lớn.
>
> Nói cách khác: **baseline xác nhận cỗ máy chạy, đồng thời xác nhận rủi ro nhận
> dạng mà brief đã tự cảnh báo là có thật và đo được.** Bước tiếp theo về mô hình
> phải là fixed effects (importer × năm, product) và clustering theo quan hệ.

**Cảnh báo phải giữ khi trích dẫn:** mô hình này **không có fixed effects, không
clustering**, và sai số chuẩn coi các episode là độc lập trong khi chúng là quan
sát lặp của cùng một quan hệ. Đọc **dấu và độ lớn**, đừng đọc mức ý nghĩa.

---

## 3. Bốn quyết định bạn đã chốt, và tôi đã làm gì

| Quyết định | Bạn chọn | Trạng thái |
|---|---|---|
| Mở cửa sổ sang 2024–2025? | **Có** | ✅ **xong** — panel nay 2003–**2025**, 747.719 episode. Thêm **100.705 episode** và **7.157 sự kiện chết trong 2025** so với bản cũ |
| Công thức Green LPI | **Chọn cái hợp lý nhất, giữ backup** | ✅ **xong** — 4 biến thể trong `analysis/glpi.csv`, đã merge vào panel (98,8%), mặc định là bản 2026 |
| Comtrade hay BACI | **Comtrade** | ✅ giữ nguyên, không đổi nguồn |
| Xử lý spell 1 năm | **Ok nếu cải thiện** | ✅ **đã đo — kết luận: không nâng ngưỡng**, xem §2c |

**Cái giá của việc mở cửa sổ, nói thẳng:** độ phủ mỏng dần **147 → 126 → 89**
nước; Việt Nam **chưa nộp** 2024 lẫn 2025 nên mất đối chiếu mirror; TRAINS
**không có thuế 2024–2025** (trả 404) nên hai năm này dùng thuế mang sang từ
2023; CEPII gravity dừng 2021 nên phải mang sang 4 năm. Cái được: **năm 2025 là
năm duy nhất quan sát được cú sốc thuế Mỹ** — biến trung tâm của cả đề tài.

Điều làm việc mở cửa sổ **an toàn** là `observation_windows()`: mỗi nước chỉ được
coi là quan sát tới năm cuối nó thực sự nộp báo cáo, spell chạy tới năm đó bị
kiểm duyệt hành chính chứ không tính là chết. Nên độ phủ mỏng đi tạo ra **ít sự
kiện quan sát được hơn**, chứ không tạo ra cái chết giả.

---

## 4. Việc còn lại

### Chờ bạn — không còn việc nào

**Việc duy nhất tôi từng nói "chỉ bạn làm được" — lấy NTM từ TRAINS Online —
hoá ra máy tự làm được**, xem §2. Bạn không cần đăng ký hay thao tác gì thêm.
Phần dưới đây giữ lại để tham chiếu, phòng khi rate-limit khiến phải quay về
cách tải thủ công bằng nút *Export to Excel* trên portal.

<details><summary>Cách làm thủ công, chỉ dùng khi rate-limit chặn hẳn</summary>


**Đăng ký/đăng nhập TRAINS Online rồi lấy dữ liệu NTM ở mức HS6 × năm.** Backend
là `api-trains2.unctad.org`, chỉ có một route dữ liệu `POST /denormalisedMeasures`
và nó cần token đăng nhập. Hai đường:

* **Đường A** — tìm mục tải hàng loạt trong portal, chọn NTM ở mức **HS6**, tất
  cả nước áp dụng, tất cả các năm, rồi đặt file vào `data_raw/ntm/trainsonline/`.
* **Đường B** (khuyên dùng nếu không có nút tải hàng loạt) — mở DevTools →
  Network, bấm tìm kiếm NTM cho **một nước, một năm bất kỳ**, tìm request tới
  `denormalisedMeasures`, chuột phải → *Copy as cURL*, dán vào `~/.trains_request.txt`
  rồi báo tôi. Tôi đọc file đó lấy endpoint/header/body rồi lặp cho toàn bộ.
  Chuỗi đó chứa **bearer token của bạn**, ngắn hạn; tôi không ghi nó vào repo,
  không commit, không gửi đi đâu.

Lấy được thì đổi được: **28 nước** từ "cố định theo thời gian" sang "biến thiên
theo năm", và NTM từ cấp ngành xuống **HS6**. Đó là ranh giới giữa một biến kiểm
soát cố định và một biến trung tâm.

</details>

### Máy tự làm được — đang và sẽ làm

| # | Việc | Trạng thái |
|---|---|---|
| 1 | Dựng lại panel với cửa sổ 2003–2025 | ✅ xong |
| 2 | Đo độ nhạy theo ngưỡng cho spell 1 năm | ✅ xong — §2c |
| 3 | **Chạy Kaplan–Meier + baseline hazard** | ✅ **xong** — §2d. Panel chạy được mô hình; lộ ngay vấn đề nội sinh của biến thuế |
| 4 | Bóc danh sách miễn trừ HS8 từ PDF chương 99 | ✅ **xong 25/08** — 1.087 dòng HTS8, 547 nhóm H0. Chiếm **39,0% giá trị xuất sang Mỹ** |
| 5 | Kiểm duyệt biến trade-remedy ở 2015 | ✅ **đã có sẵn** — `ttbd_observed` = 1 tới 2015, 0 từ 2016. Kiểm lại 25/08 |
| 6 | Lấy EPI các năm cũ để GLPI biến thiên theo thời gian | ✅ **xong 25/08** — điểm EPI quá khứ không ai công bố, nhưng **chỉ báo thành phần theo năm thì có**: 184.827 giá trị, 1996–2025 |
| 7 | ~~Kéo NTM bằng script qua `denormalisedMeasures`~~ | ✅ **xong 25/08 bằng đường khác** — file researcher 10,5 GB tải qua một GET duy nhất, không bị rate-limit. Xem [DATA_HANDOFF.md](DATA_HANDOFF.md) §2.1 |
| 8 | Phạm vi CBAM của EU | ✅ **xong 25/08** — 269 nhóm H0. Nhưng giai đoạn 2023–2025 **chỉ là nghĩa vụ báo cáo**, chế độ chính thức từ 1/1/2026, tức ngoài panel |

### Cần cả nhóm quyết

* **12 định nghĩa** ở §2.3 của doc L0–L5 — chặn từ L0 trở đi.
* **Định nghĩa "network survivability"** — chặn L2, L4, L5. Đây là lỗ hổng khái
  niệm chứ không phải lỗ hổng dữ liệu, và phải chốt **trước** khi viết code tối
  ưu. Không được đổi tên tổng xuất khẩu hay HHI thành "reliability".

---

## 5. Hai điều về hạ tầng, để lần sau không vấp lại

**`merge_panel.py` từng làm nổ máy.** Bản cũ giữ 11,6 triệu ô thuế và 647.014
episode trong RAM cùng lúc → đỉnh **5,2 GB trên máy 5,6 GB**. Bản hiện tại xử lý
**từng nước một**: đỉnh **371 MB, chạy 71 giây**, kết quả y hệt. Mọi thứ thêm
vào merge sau này phải giữ đúng dạng đó.

**Một cái bẫy suýt lọt.** `selection/eu_tariff_mapping.csv` dừng ở 2021, nên với
2022–2023 thì 27 nước EU tự ánh xạ về chính mình — mà TRAINS không có mã riêng
cho từng nước EU, nên chúng bị **loại khỏi danh sách tải trong im lặng, không cả
một mã 404**. Pha tải vẫn báo "0 without data" trong khi một phần năm panel
không có thuế. Chỉ lộ ra vì bài test nhanh trên 3 nước tình cờ bốc trúng Đức.
Bài học: **"0 lỗi" không đồng nghĩa với "0 thiếu sót"** — phải kiểm tra độ phủ
trên panel đầu ra, không chỉ nhìn log của pha tải.
