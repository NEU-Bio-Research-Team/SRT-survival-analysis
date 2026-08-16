# Tiến trình thực hiện Phần 5 — thu thập và dựng bộ dữ liệu survival

*Cập nhật: 16/08/2026. Tài liệu này ghi lại những gì đã chạy thật, quyết định nào đã chốt và vì sao. Bổ sung cho [KIEM_CHUNG_DU_LIEU_WITS.md](KIEM_CHUNG_DU_LIEU_WITS.md).*

> **16/08/2026 — đổi thiết kế.** Exporter thu về **chỉ còn Việt Nam**; importer
> không còn chốt ở 53 nước mà lấy **tất cả nước đủ dữ liệu (147)**. Mục 3 và mục
> 5–7 dưới đây mô tả thiết kế cũ; phần thay thế nằm ở
> [THIET_KE_VIET_NAM.md](THIET_KE_VIET_NAM.md). Các mục còn lại (hướng biến
> thuế, giới hạn API, xử lý HS revision, NTM) vẫn đúng nguyên vẹn.

---

## Trạng thái các đầu việc

| # | Đầu việc (Phần 5) | Trạng thái |
|---|---|---|
| 1 | Xác nhận hướng biến Tariff | **Đã chốt** — xem mục 1 |
| 2 | API key UN Comtrade | **Xong** — key đã hoạt động, đo được giới hạn thật |
| 3 | Chọn nước bằng dữ liệu | **Xong, đã làm lại 16/08** — exporter = VNM, 147 importer hạng A+B |
| 4 | Chốt cửa sổ thời gian | **Xong** — 2002–2021 |
| 5 | Kéo tariff HS6 | **Đang chạy** — MFN + PREF cho partner 704 |
| 6 | Kéo trade value HS6 + dựng spell | **Đang chạy** — partner = VN, nhẹ hơn ~100 lần |
| 7 | Tự tính RCA/HHI ở HS6 | **Xong, đã định nghĩa lại** — growth theo sản phẩm, RCA có mẫu số thế giới |
| 8 | Quyết định NTM | **Đã làm phương án time-invariant** — xem mục 8 |

---

## 1. Hướng của biến Tariff — đã chốt

Tôi dùng cách hiểu tiêu chuẩn: **thuế mà nước nhập khẩu j áp lên sản phẩm k đến từ nước i**. Trong TRAINS, `reporter` = **importer**, `partner` = **exporter**.

Cụ thể hơn, biến được lấy là **thuế thực tế mà nhà xuất khẩu phải đối mặt**:

- `partner = 000` → MFN (thuế tối huệ quốc, áp cho mọi đối tác không có ưu đãi);
- `partner = <mã nước/nhóm>` → PREF (thuế ưu đãi theo FTA);
- Khi một cặp có cả hai, lấy **mức thấp hơn** — đó mới là mức thuế thực tế áp dụng.

Nếu bạn muốn hướng ngược lại (thuế nước xuất khẩu áp), chỉ cần đảo `reporter` và `partner` trong `fetch_tariffs.py`; phần còn lại của pipeline không đổi.

## 2. API key Comtrade — giới hạn thật đã đo

| Đặc điểm | Kết quả đo |
|---|---|
| Endpoint đầy đủ `/data/v1/get` | Hoạt động, không còn trần 500 dòng của bản public |
| Trần bản ghi mỗi call | **100.000** — vượt thì response bị cắt âm thầm, không báo lỗi |
| Endpoint `bulk/v1` | **401** — không nằm trong gói "Free APIs" |
| Rate limit | **Không phải quota ngày**; là throttle tức thời. Gọi liên tiếp thỉnh thoảng dính `429`, chờ ~20s là qua |
| Gộp tham số | Gộp nhiều partner và nhiều năm trong một call đều được |

**Bẫy đã gặp và đã xử lý:** request 82 exporters cùng lúc tạo response ~90MB, mất ~110 giây, và **thỉnh thoảng trả về rỗng thay vì báo lỗi**. Pipeline vì thế chia lô 20 exporters, thử lại một lần khi gặp lô rỗng, và **không bao giờ ghi cache một importer-year rỗng** (nếu rỗng thì coi là thất bại để lần chạy sau kéo lại).

**Bẫy nghiêm trọng hơn — mã nước lịch sử:** bảng `partnerAreas.json` chứa nhiều bản ghi cùng mã ISO3. `USA` xuất hiện dưới 840, 842 và **841 = "USA and Puerto Rico (...1980)"**; Đức có 276 và **280 = "Fed. Rep. of Germany (...1990)"**. Nếu tra bảng theo kiểu ghi đè, bạn nhận mã đã ngừng dùng và **API trả về 0 dòng mà không báo lỗi** — đúng lỗi tôi gặp lúc đầu. Cách xử lý: bỏ mọi bản ghi có `entryExpiredDate`, bỏ nhóm (`isGroup`), rồi lấy bản ghi có `entryEffectiveDate` mới nhất. Kết quả đúng: USA 842, Đức 276, Pháp 251, Việt Nam 704, Serbia 688.

## 3. Chọn nước bằng dữ liệu

Ba nguồn được giao nhau trong [select_countries.py](../scripts/select_countries.py):

1. **Comtrade `getDA`** — nước nào thực sự nộp báo cáo HS hằng năm. Đây là tiêu chí ràng buộc với importer: **131 nước** nộp đủ cả 20 năm.
2. **TRAINS `dataavailability`** — nước nào có biểu thuế. Sau khi xử lý EU (mục dưới), **105 nước** vừa nộp đủ 20 năm vừa có ≥15 năm thuế.
3. **World Bank API** — nhóm thu nhập và khu vực, để bảo đảm 53 importers trải đều các nhóm.

**Phát hiện quan trọng — thuế EU:** TRAINS chỉ khai biểu thuế chung một lần dưới mã `EUN` (918); Đức, Pháp, Ý, Hà Lan, Bỉ, Tây Ban Nha đều hiển thị **0 năm thuế**. Nếu không xử lý, **toàn bộ thị trường EU biến mất** khỏi danh sách importer — mất đi những thị trường nhập khẩu lớn nhất thế giới. Pipeline vì thế ánh xạ từng thành viên EU sang biểu thuế `EUN` kể từ năm gia nhập (Anh dùng EUN đến hết 2020, dùng biểu riêng từ 2021).

### 53 importers đã chọn

| Nhóm thu nhập | Số nước | Danh sách |
|---|---|---|
| High income | 16 | USA, DEU, NLD, JPN, ITA, FRA, KOR, BEL, HKG, ARE, CAN, GBR, SGP, RUS, ESP, CHE |
| Upper middle | 15 | CHN, MEX, VNM, BRA, MYS, IDN, TUR, ZAF, PHL, ARG, PER, COL, BLR, UKR, ECU |
| Lower middle | 14 | IND, EGY, MAR, CIV, BOL, ZMB, NIC, TZA, NAM, SEN, BEN, KGZ, SWZ, LSO |
| Low income | 8 | MOZ, UGA, BFA, MDG, RWA, NER, BDI, CAF |

Ràng buộc thực tế: chỉ 8 nước thu nhập thấp vừa nộp Comtrade đủ 20 năm vừa có biểu thuế — nhóm này vốn báo cáo thưa, không thể ép thêm.

### 82 exporters đã chọn

Xếp hạng theo giá trị xuất khẩu hàng hóa (WDI `TX.VAL.MRCH.CD.WT`). **Exporter không cần tự báo cáo** vì họ vào panel với tư cách *partner* trong báo cáo của importer — đây là lý do tiêu chí "báo cáo đều đặn" chỉ áp cho importer.

Danh sách đầy đủ trong [selection/exporters_selected.csv](../selection/exporters_selected.csv); 34 nước vừa là importer vừa là exporter.

## 4. Cửa sổ thời gian: 2002–2021

Bị chặn ở hai đầu:

- **Trần trên 2021**: TRAINS trả về **0 nước có biểu thuế cho 2022 và 2023**. Trade data có đến 2023 nhưng lấy thêm 2 năm đó thì mất hẳn biến Tariff.
- **Đáy 2002**: lùi 20 năm. Kiểm chứng: Comtrade có 171 nước báo cáo năm 2002, TRAINS có 133 nước — đủ dày.

## 5. Kéo tariff HS6

[fetch_tariffs.py](../scripts/fetch_tariffs.py), hai pha:

- **Pha MFN**: mỗi (reporter thuế, năm) một call với `product=ALL`. Sau khi gộp EU, 53 importers × 20 năm rút còn **941 call**.
- **Pha PREF**: thay vì thử toàn bộ 53 × 82 × 20 = 86.920 cặp, pipeline đọc trường `partnerlist` trong `dataavailability` — TRAINS liệt kê sẵn đối tác nào có biểu thuế ưu đãi trong năm đó. Ví dụ Việt Nam 2021 chỉ có 15 mục thay vì 82.

Dữ liệu lưu dạng CSV nén theo từng reporter-năm, **chạy lại sẽ tự bỏ qua file đã có** nên có thể dừng/tiếp bất cứ lúc nào.

## 6. Kéo trade value và dựng spell

[fetch_trade.py](../scripts/fetch_trade.py) lấy `flowCode=M` (báo cáo phía nhập khẩu) ở mức HS6 cho 82 exporters, từng importer-năm một.

[build_spells.py](../scripts/build_spells.py) biến panel thô thành bộ dữ liệu survival, xử lý ba vấn đề:

**(a) Đổi phiên bản HS — vấn đề dễ bị bỏ qua nhất.** Các nước báo cáo theo phiên bản HS khác nhau *trong cùng một năm*: kiểm tra dữ liệu thật cho thấy năm 2019 Rwanda dùng H4 còn Mỹ dùng H5. Qua 20 năm, mỗi nước còn đổi phiên bản vài lần. Một mã bị đánh số lại sẽ trông y hệt **một quan hệ chết đi và một quan hệ mới sinh ra** — làm hỏng toàn bộ phân tích duration.

Cách xử lý: tải 5 bảng concordance của WITS (H1→H0 … H5→H0, tổng **25.981 liên kết**), dựng đồ thị nối các mã tương ứng qua mọi phiên bản, rồi lấy **thành phần liên thông** làm "product family". Family ổn định suốt 20 năm. Kiểm chứng trên dữ liệu đã tải: **14.042/14.042 mã báo cáo đều khớp được vào một family**.

**(b) Ngưỡng tồn tại.** Quan hệ được coi là sống trong một năm khi giá trị nhập khẩu ≥ **10.000 USD** — đúng ngưỡng WITS dùng trong Trade Outcomes.

**(c) Kiểm duyệt.** Spell bắt đầu đúng năm 2002 → **left-censored, loại bỏ** theo thiết kế. Spell còn sống ở 2021 → **right-censored, giữ lại với `event = 0`**.

Đầu ra: `analysis/spells.csv` (một dòng/spell) và `analysis/episodes.csv` (một dòng/spell-năm, dạng `t_start`/`t_stop` để chạy Cox có biến thay đổi theo thời gian).

## 7. RCA và HHI ở mức HS6 — tự tính

Như đã nêu ở tài liệu trước, WITS chỉ cho các chỉ số này ở mức nhóm ngành. `build_spells.py` tính lại ở mức family từ chính panel:

- **RCA (Balassa)**: `(x_ik/X_i) / (x_wk/X_w)`
- **Product share**: tỷ trọng sản phẩm k trong tổng xuất khẩu của i
- **Partner share**: tỷ trọng đối tác j trong tổng xuất khẩu của i
- **HHI thị trường**: tổng bình phương tỷ trọng đối tác
- **HHI sản phẩm**: tổng bình phương tỷ trọng sản phẩm
- **Country growth / World growth**: tốc độ tăng trưởng năm

Lưu ý: "thế giới" ở đây là **tổng trong mẫu 53 importers × 82 exporters**, không phải toàn cầu. Số liệu WITS ở mức nhóm ngành vẫn nên dùng để kiểm tra chéo hướng và độ lớn.

[merge_panel.py](../scripts/merge_panel.py) ghép thuế và biến vĩ mô vào `episodes.csv`, cho ra `analysis/panel_final.csv`. Thuế được khớp qua cùng hệ family, ưu tiên PREF nếu thấp hơn MFN, và **năm thiếu thì lấy năm gần nhất trong vòng 3 năm, có cột `tariff_source_year` đánh dấu** để bạn thấy rõ chỗ nào là nội suy.

## 8. NTM — đã làm phương án 1, đã đo được giá của phương án 2

*Cập nhật 13/08/2026.* Trước đây mục này để ngỏ ba lựa chọn. Nay phương án 1 đã
được hiện thực hóa, và phương án 2 đã được kiểm chứng bằng cách gọi thật API.

**Đã làm — [build_ntm.py](../scripts/build_ntm.py):** rút ra khỏi 3 file WITS công khai mọi
thứ chúng thực sự chứa, thay vì chỉ dùng file coverage như trước:

- **Tách theo loại NTM.** `NTM-Indicators-Measure-Sector.csv` có cột `NTMCode`;
  giá trị một ký tự chính là chương MAST của UNCTAD (A = SPS, B = TBT,
  E = quantity control...), giá trị bốn ký tự là biện pháp con nằm trong đó.
  Chỉ đọc hàng một ký tự. Đây là điều Calì et al. (2021) nhấn mạnh: chương
  bảo hộ làm giảm survival còn chương đặt chuẩn thì không, gộp chung là triệt
  tiêu hai hiệu ứng ngược dấu thành nhiễu.
- **"Có ít nhất một NTM" ở cấp ngành.** Coverage ratio của các chương chồng lấn
  nhau nên không cộng được. Tỷ lệ dòng hàng chịu ít nhất một biện pháp lấy từ
  `NTM-Prevalence-Sector.csv`: các nhóm No NTMs / 1 type / 2 types / 3+ types
  cộng lại đúng 100%, nên `100 − No NTMs` là một frequency ratio thật.
- **Ghép qua ngành.** Nhãn Sector của file NTM chính là nhóm chương HS của WITS
  (01–05 Animal, 06–15 Vegetable, …), nên `product_family` ánh xạ được về ngành
  qua hai chữ số đầu của mã HS.
- **EU.** Biện pháp NTM khai một lần dưới `EUN` y hệt biểu thuế chung, nên các
  thành viên EU đọc bản ghi EUN qua đúng `eu_tariff_mapping.csv` đang dùng cho
  thuế. Nhờ đó độ phủ importer tăng từ 27 lên **34/53**.

13 cột NTM đã có trong `analysis/panel_final.csv`, kèm `ntm_survey_year` ghi rõ
giá trị được đo năm nào — biến là **time-invariant theo đúng thiết kế**, không
phải do sơ suất.

**Đã đo — phương án 2 (TRAINS Online).** [fetch_ntm_availability.py](../scripts/fetch_ntm_availability.py)
gọi thẳng backend của `trainsonline.unctad.org` (`api-trains2.unctad.org`).
Các endpoint tra cứu **trả lời không cần đăng nhập**; endpoint dữ liệu thì không
(trả 200 với mảng rỗng). Kết quả đáng để cân nhắc:

| Chỉ tiêu | WITS công khai (đang dùng) | TRAINS Online (cần tài khoản) |
|---|---|---|
| Importer có dữ liệu | 34/53 | **50/53** (thiếu MDG, CAF, UKR) |
| Có ≥1 đợt thu thập trong 2002–2021 | 34 | **43** |
| Có ≥2 đợt trong cửa sổ → biến đổi theo thời gian | **0** | **28** |
| Độ chi tiết sản phẩm | Ngành (16 nhóm) | HS6 |
| EU | 1 lát cắt (2016) | 15 năm (2010–2025) |

Nói cách khác, đăng ký TRAINS Online đổi được **28 nước từ time-invariant sang
time-varying** và đưa NTM từ cấp ngành xuống HS6. Đó là ranh giới giữa "biến
kiểm soát cố định" và "biến trung tâm" của bài.

Chi tiết từng nước: [selection/ntm_availability.csv](../selection/ntm_availability.csv).

---

## Cách chạy lại toàn bộ

```bash
cd /home/minhquang/wits

python3 scripts/select_countries.py           # chọn nước + cửa sổ thời gian
python3 scripts/fetch_tariffs.py --pass mfn   # thuế MFN
python3 scripts/fetch_tariffs.py --pass pref  # thuế ưu đãi
python3 scripts/fetch_trade.py                # trade value HS6 (lâu nhất)
python3 scripts/fetch_macro.py                # GDP growth + tải 3 file NTM thô
python3 scripts/fetch_ntm_availability.py     # bản đồ độ phủ NTM của TRAINS Online
python3 scripts/build_ntm.py                  # dựng biến NTM theo loại + theo ngành
python3 scripts/build_spells.py               # dựng spell + RCA/HHI
python3 scripts/merge_panel.py                # ghép thuế + vĩ mô + NTM -> panel_final.csv
```

Mọi script đều **có thể dừng và chạy tiếp**: file đã tải xong sẽ được bỏ qua.

Chạy nhiều luồng cho nhanh (chia theo importer):

```bash
python3 scripts/fetch_trade.py --importers USA,DEU,NLD,JPN &
python3 scripts/fetch_trade.py --importers CHN,MEX,VNM,BRA &
```

Bốn luồng là ngưỡng hợp lý; nhiều hơn thì `429` xuất hiện dày và không nhanh thêm.

## Cấu trúc thư mục

Xem [../README.md](../README.md) — mục "Bản đồ thư mục". Tóm tắt: mã nguồn ở
`scripts/`, tài liệu ở `docs/`, dữ liệu thô ở `data_raw/`, kết quả ở `analysis/`,
metadata chọn nước ở `selection/`, khóa API ở `.env` (quyền 600, đã gitignore).
