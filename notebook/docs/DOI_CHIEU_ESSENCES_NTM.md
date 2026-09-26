# Đối chiếu `essences.txt` với workspace — và những gì đã làm xong

*Kiểm tra lần đầu 13/08/2026 sáng; cập nhật cùng ngày sau khi thực hiện các
phần làm được ngay. Mọi con số đến từ việc đọc file và gọi API thật.*

---

## Kết luận

| Trạng thái | Trước | Sau |
|---|---|---|
| Yêu cầu của `essences.txt` đã đáp ứng | 1/6 | **4/6** |
| Cột NTM trong `panel_final.csv` | 0 | **13** |
| Importer có dữ liệu NTM | 0 | **34/53** |

Hai yêu cầu còn lại **không thể tự làm được** vì cần tài khoản đăng ký — chi
tiết ở phần "Vướng mắc" cuối tài liệu.

---

## Phần 1 — Đã làm xong

### 1.1. NTM đã vào panel, tách theo loại — [build_ntm.py](../scripts/build_ntm.py)

Yêu cầu số 5 của `essences.txt` (ba chỉ số chuẩn, **tách riêng từng loại NTM**)
nay đã đạt ở mức mà dữ liệu công khai cho phép. Điểm mấu chốt: file
`NTM-Indicators-Measure-Sector.csv` có cột `NTMCode`, trong đó **giá trị một ký
tự chính là chương MAST của UNCTAD** (A = SPS, B = TBT, E = quantity control…)
còn giá trị bốn ký tự là biện pháp con nằm trong chương đó. Chỉ đọc hàng một ký
tự là có ngay bản tách loại — trước đây `fetch_macro.py` tải file này về rồi bỏ
không.

13 cột mới trong `analysis/panel_final.csv`:

| Cột | Nội dung |
|---|---|
| `ntm_reporter` | nước áp dụng (EU đọc bản ghi `EUN`) |
| `ntm_survey_year` | năm khảo sát của giá trị đang dùng — 2012–2017 |
| `ntm_sector` | ngành WITS suy ra từ 2 chữ số đầu mã HS |
| `ntm_coverage_ratio`, `ntm_frequency_ratio` | cấp quốc gia, luồng nhập khẩu |
| `ntm_sector_freq_any` | % dòng hàng trong ngành chịu **ít nhất một** NTM |
| `ntm_sector_share_3plus` | % dòng hàng chịu **từ 3 loại NTM trở lên** — biến cường độ |
| `ntm_sps_coverage` | chương A — chuẩn vệ sinh dịch tễ |
| `ntm_tbt_coverage` | chương B — hàng rào kỹ thuật |
| `ntm_quantity_coverage` | chương E — hạn ngạch, giấy phép, cấm |
| `ntm_technical_coverage` | max các chương kỹ thuật A–C |
| `ntm_nontechnical_coverage` | max các chương phi kỹ thuật D–O |
| `ntm_n_types` | số chương MAST khác nhau đang áp lên ngành đó |

Đúng ý Calì et al. (2021) mà txt trích: SPS/TBT (đặt chuẩn) và quantity
control (bảo hộ) nay là **ba biến riêng**, không gộp thành một chỉ số bình quân
triệt tiêu hai hiệu ứng ngược dấu.

Hai file trung gian cũng được xuất để kiểm tra: `analysis/ntm_by_type.csv`
(3.944 dòng, nước × ngành × chương MAST) và `analysis/ntm_sector.csv`
(1.200 dòng, bảng ghép trực tiếp vào panel).

### 1.2. Ba quyết định phương pháp đã chốt, có lý do

**Coverage ratio của các chương không cộng được.** Một dòng hàng có thể vừa
chịu SPS vừa chịu TBT, nên tổng các chương vượt 100%. Vì vậy `ntm_technical_coverage`
lấy **max** trong nhóm — một cận dưới của hợp, và được ghi rõ trong code là cận
dưới chứ không phải giá trị thật.

**"Có ít nhất một NTM" lấy từ file prevalence, không phải file measures.**
`NTM-Prevalence-Sector.csv` chia mỗi ngành thành No NTMs / 1 type / 2 types /
3+ types, cộng lại đúng 100%. Nên `100 − No NTMs` là một frequency ratio thật
sự ở cấp ngành, thứ mà file measures không cho được.

**Chương vắng mặt = 0, nước vắng mặt = trống.** Đây chính là chỗ mơ hồ mà
Carrère (2011) nêu và `essences.txt` nhắc: thiếu dữ liệu hay không có biện
pháp? Cách giải: nếu nước-ngành *có* trong khảo sát mà chương A không xuất
hiện thì đó là "không có biện pháp SPS nào" → 0; còn nước không nằm trong khảo
sát thì để trống, không suy diễn. Ghi rõ trong docstring của `build_ntm.py`.

### 1.3. Độ phủ EU: 27 → 34 importer

Biện pháp NTM được khai một lần dưới mã `EUN`, y hệt biểu thuế chung. Pipeline
đã có sẵn `selection/eu_tariff_mapping.csv` cho thuế, nay dùng lại đúng bảng đó
cho NTM. BEL, DEU, ESP, FRA, GBR, ITA, NLD nhờ vậy có dữ liệu — nếu không sẽ
mất trắng nhóm thị trường nhập khẩu lớn nhất mẫu.

### 1.4. Đã đo được chính xác cái giá của TRAINS Online — [fetch_ntm_availability.py](../scripts/fetch_ntm_availability.py)

`essences.txt` khuyến nghị TRAINS Online nhưng không nói rõ **được thêm bao
nhiêu**. Tôi gọi thẳng backend của trang đó (`api-trains2.unctad.org`) và đo:

| Chỉ tiêu | WITS công khai (đang dùng) | TRAINS Online (cần tài khoản) |
|---|---|---|
| Importer có dữ liệu | 34/53 | **50/53** — chỉ thiếu MDG, CAF, UKR |
| Có ≥1 đợt thu thập trong 2002–2021 | 34 | **43** |
| **Có ≥2 đợt trong cửa sổ** → biến đổi theo năm | **0** | **28** |
| Độ chi tiết sản phẩm | Ngành (16 nhóm) | HS6 |
| EU | 1 lát cắt (2016) | 15 năm (2010–2025) |
| Mỹ | 1 lát cắt (2014) | 4 đợt (2014, 2017, 2018, 2019) |

Đây là con số để bạn quyết định: đăng ký TRAINS Online đổi được **28 nước từ
time-invariant sang time-varying**, tức đúng ranh giới giữa "biến kiểm soát cố
định" và "biến trung tâm" mà `essences.txt` nói tới. Danh sách từng nước kèm
các năm cụ thể: [selection/ntm_availability.csv](../selection/ntm_availability.csv).

Kèm theo: `selection/ntm_types.csv` — 16 chương MAST hiện hành. Lưu ý một khác
biệt sẽ gây lỗi nếu bỏ qua: file WITS cũ ghi **D = Price control measures**,
còn TRAINS Online hiện hành ghi **D = Contingent trade protective measures**
(chống bán phá giá, tự vệ). Hai bảng phân loại khác thế hệ, không được trộn mã
D của hai nguồn với nhau.

### 1.5. Đã khởi động lại toàn bộ tiến trình tải

Các tiến trình tải đã **dừng từ 12/08 02:01**, không phải đang chạy. Tôi khởi
động lại bằng `nohup` nên chúng sống độc lập với phiên làm việc:

| Tiến trình | Log | Nội dung |
|---|---|---|
| `fetch_tariffs.py --pass all` | `logs/tariff_all.log` | MFN còn dở (dừng ở `MAR`) rồi chạy tiếp PREF |
| `fetch_trade.py` × 4 luồng | `logs/trade_b0..b3.log` | 53 importers chia 4 lô |

Mọi script đều bỏ qua file đã có nên không tải lại thứ đã xong. Theo dõi bằng:

```bash
ls data_raw/trade | wc -l          # đích: 1.060
ls data_raw/tariffs/mfn | wc -l    # đích: ~941
ls data_raw/tariffs/pref | wc -l   # hiện 0
tail -f logs/trade_b0.log
```

---

## Phần 2 — Vướng mắc, cần bạn ra tay

### 2.1. TRAINS Online: endpoint dữ liệu đòi đăng nhập

Tôi đã dò backend và xác định rõ ranh giới:

| Endpoint | Không đăng nhập |
|---|---|
| `/countriesWithYearsOfDataCollection` | **200, có dữ liệu** — đã khai thác, xem 1.4 |
| `/ntmTypes`, `/hsCodes` (7.687 mã), `/imposingCountries` | **200, có dữ liệu** |
| `/denormalisedMeasures` (bản ghi biện pháp thật) | **200 nhưng mảng rỗng**, gọi vài lần thì `403` |

`/downloadLimit` tự khai: 1.000 bản ghi cho khách vãng lai, 9.588 cho tài khoản
đã đăng nhập. Trang dùng Azure AD (MSAL) nên cần tài khoản thật, không thể vòng
qua.

**Việc bạn cần làm:** đăng ký tài khoản tại `trainsonline.unctad.org`, vào mục
**Bulk Data Download** tải "researcher file" (có sẵn định dạng CSV/STATA), đặt
file vào `data_raw/ntm/trainsonline/`. Sau đó tôi viết phần đọc file và thay
biến NTM time-invariant hiện tại bằng biến HS6 × năm. Nếu bạn lấy được token
đăng nhập, tôi có thể tự động hóa luôn phần tải.

### 2.2. WTO I-TIP: cần API key miễn phí

| Đường vào | Kết quả thử |
|---|---|
| `data.wto.org/dataset/ext_itip_1` | **HTTP 403** |
| `api.wto.org/timeseries/v1/...` | **HTTP 401** — thiếu subscription key |

Key miễn phí đăng ký ở `apiportal.wto.org`. Đây là nguồn cho phương án dự
phòng số 2 của `essences.txt` (dummy theo năm bắt đầu/kết thúc từng biện pháp).
Chỉ cần thiết nếu 2.1 không thành.

### 2.3. 19 importer không có NTM trong dữ liệu công khai

BDI, BLR, CAF, **CHN**, EGY, HKG, KGZ, KOR, LSO, MDG, MOZ, NAM, RWA, SWZ, TZA,
UGA, UKR, ZAF, ZMB.

Trung Quốc và Hàn Quốc trống là mất mát thật sự về mặt kinh tế. Tin tốt: TRAINS
Online **có** 16 trong 19 nước này (chỉ MDG, CAF, UKR là không), nên 2.1 giải
quyết luôn vấn đề này. Nếu không làm 2.1, phải chấp nhận `NA` cho các nước đó
và nêu trong phần hạn chế.

### 2.4. NTM vẫn ở cấp ngành, không phải HS6

Ánh xạ hiện tại là HS2 → 16 nhóm ngành WITS. Trong cùng một ngành, mọi sản phẩm
nhận cùng một giá trị NTM, nên biến này **không giải thích được biến thiên giữa
các sản phẩm trong ngành** — chỉ giữa các ngành. Đây là hạn chế cố hữu của
nguồn công khai, chỉ 2.1 mới gỡ được.

### 2.5. Panel vẫn là bản chạy thử — chưa dùng để chạy mô hình

Không liên quan NTM nhưng chặn mọi kết quả:

| Hạng mục | Hiện tại | Đích |
|---|---|---|
| Trade HS6 | ~6% (7/53 importers) | 1.060 file |
| Tariff MFN | ~55% | ~941 file |
| Tariff PREF | **0** | theo `partnerlist` |
| Ghép thuế vào panel | **6,2%** episode có thuế | > 90% |

`spells.csv` hiện có **157.101 spell nhưng 0 spell right-censored** — con số bất
khả thi trong một bộ survival đúng, và là hệ quả trực tiếp của việc dựng spell
khi mới có 12 file trade. **Sau khi tải xong phải chạy lại**
`build_spells.py` rồi `merge_panel.py`, và kiểm tra ngay số right-censored > 0
trước khi tin bất cứ kết quả nào.

Ước tính từ log: còn ~27 giờ cho phần trade.

---

## Phần 3 — Bảng đối chiếu 6 yêu cầu của `essences.txt`

| # | Yêu cầu | Trước | Sau | Ghi chú |
|---|---|---|---|---|
| 1 | NTM là biến trung tâm | ❌ | ✅ | 13 cột trong panel, tách theo loại |
| 2 | Hiểu vì sao 3 file WITS không đủ | ✅ | ✅ | — |
| 3 | Lấy TRAINS Online HS6 | ❌ | ⚠️ | Đã đo được giá trị; tải cần tài khoản (2.1) |
| 4 | Lấy WTO I-TIP | ❌ | ❌ | Cần API key (2.2) |
| 5 | Coverage / frequency / tách loại | ⚠️ | ✅ | Cả ba, ở cấp nước và cấp ngành |
| 6 | Phương án dự phòng time-invariant | ❌ | ✅ | Đã hiện thực hóa, có `ntm_survey_year` |

---

## Phần 4 — Câu chữ cho phần Discussion

Ba hạn chế dưới đây nên nêu chủ động, đúng như `essences.txt` gợi ý — reviewer
trong ngành đã quen, nhưng chỉ chấp nhận khi tác giả nói trước:

1. **NTM là time-invariant.** Dữ liệu công khai chỉ có một đợt khảo sát mỗi
   nước (2012–2017), đã ghi trong `ntm_survey_year`. Đây là cách nhiều paper
   xử lý khi NTM chưa đủ dày theo năm.
2. **NTM ở cấp ngành.** Không tách được biến thiên trong nội bộ ngành.
3. **Thiếu hay không có?** Missing entries ở cấp HS6 không phân biệt được
   "chưa thu thập" với "không có biện pháp" — đúng vấn đề Carrère (2011) nêu.
   Trong workspace này, sự mơ hồ đó được xử lý ở đúng một chỗ và được ghi rõ:
   chương vắng mặt trong một nước-ngành *đã được khảo sát* tính là 0; nước
   không được khảo sát để trống.
