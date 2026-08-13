# Bộ dữ liệu survival analysis cho quan hệ xuất khẩu (WITS + Comtrade)

Dự án thu thập và dựng bộ dữ liệu **spell-level** để chạy mô hình survival
(Kaplan-Meier / Cox) trên tuổi thọ của quan hệ xuất khẩu ở mức tariff-line.

*Trạng thái trong tài liệu này được đo trực tiếp trên đĩa lúc **13/08/2026, 19:35**.
Mọi con số đều là số thật, không phải ước lượng từ tài liệu cũ.*

---

## ĐỌC TRƯỚC TIÊN — 3 điều quan trọng nhất

1. **Bộ dữ liệu trong `analysis/` HIỆN CHƯA DÙNG ĐƯỢC để chạy mô hình.** Nó được
   dựng lúc 09:08 sáng nay khi mới có **12 file trade**, và có dấu hiệu hỏng rõ
   ràng: **157.101 spell nhưng 0 spell right-censored** — điều bất khả thi trong
   một bộ survival đúng. Chỉ 4 importer có mặt, chỉ 6,2% episode ghép được thuế.
2. **Toàn bộ tiến trình tải đã CHẾT lúc 13:04 hôm nay**, không có tiến trình nào
   đang chạy. Trade mới đạt **119/1.060 file (11%)**, PREF đạt **784/8.078 (10%)**.
   Muốn có dữ liệu thật thì phải khởi động lại — xem mục [Chạy tiếp](#chạy-tiếp-từ-đúng-chỗ-đang-dở).
3. **Điểm nghẽn cần bạn ra tay (không tự động hoá được):** tài khoản
   **UNCTAD TRAINS Online** để lấy NTM ở mức HS6 × năm. Không có nó, NTM mãi
   là biến cố định theo thời gian ở cấp ngành — xem mục [Cần bạn làm](#4-hai-việc-chỉ-bạn-mới-làm-được).

---

## 1. Thiết kế nghiên cứu (đã chốt)

| Chiều | Giá trị đã chốt | Chốt bằng cách nào |
|---|---|---|
| Cửa sổ thời gian | **2002–2021** (20 năm) | TRAINS không có biểu thuế cho 2022–2023 → trần trên bị chặn cứng |
| Đơn vị sản phẩm | **HS 6-digit**, gom thành *product family* ổn định qua các phiên bản HS | 25.981 liên kết concordance H1→H0 … H5→H0 |
| Importer | **53 nước**, trải đều 4 nhóm thu nhập | Comtrade `getDA` + TRAINS `dataavailability`, không chọn cảm tính |
| Exporter | **82 nước** | Xếp hạng giá trị xuất khẩu hàng hoá (WDI) |
| Đơn vị quan sát | spell của bộ ba `(exporter i, importer j, product family k)` | |
| Ngưỡng tồn tại | nhập khẩu ≥ **10.000 USD**/năm | đúng ngưỡng WITS dùng trong Trade Outcomes |
| Kiểm duyệt | spell bắt đầu 2002 → **left-censored, loại**; còn sống 2021 → **right-censored, giữ, `event=0`** | |
| Hướng biến thuế | thuế **nước nhập khẩu áp lên hàng của nước xuất khẩu** (TRAINS: reporter = importer) | |

Việt Nam có mặt **cả hai vai**: vừa nằm trong 82 exporters vừa nằm trong 53 importers.

**53 importers:** 16 high income · 15 upper-middle · 14 lower-middle · 8 low income
(chỉ 8 nước thu nhập thấp vừa nộp Comtrade đủ 20 năm vừa có biểu thuế — không ép thêm được).
Danh sách đầy đủ: [selection/importers_selected.csv](selection/importers_selected.csv),
[selection/exporters_selected.csv](selection/exporters_selected.csv).

---

## 2. Đã lấy được những gì

### 2.1. Bảng tiến độ tải (đo trên đĩa hôm nay)

| Nguồn | Đã có | Đích | % | Trạng thái |
|---|---|---|---|---|
| **Trade value HS6** (Comtrade) | **119 file** (~121 MB) | 1.060 (53 importer × 20 năm) | **11%** | ⏸ dừng lúc 13:02 |
| **Tariff MFN** (WITS TRAINS) | **912 file** | ~941 | **97%** | ⏸ gần xong |
| **Tariff PREF** (WITS TRAINS) | **784 file** | 8.078 call | **10%** | ⏸ dừng ở BRA 2007 |
| **Concordance HS** | 5/5 bảng (H1→H0 … H5→H0) | 5 | **100%** | ✅ |
| **NTM công khai** (3 file WITS) | 3/3 | 3 | **100%** | ✅ |
| **Vĩ mô** (GDP growth, GDP, GNI) | 1.940 dòng nước-năm | — | **100%** | ✅ |
| **Metadata chọn nước** | 9 file trong `selection/` | — | **100%** | ✅ |
| **Kiểm chứng API** | 22 phép thử trong `probe_out/` | — | **100%** | ✅ |

**Trade — chi tiết 119 file đã có** (chỉ 3 importer xong trọn 20 năm):

```
CHN 20/20 ✅   NIC 20/20 ✅   USA 20/20 ✅
NLD 14/20      IND 11/20      BDI 10/20      PER  8/20
BRA  6/20      DEU  6/20      MOZ  3/20      RWA  1/20
42 importer còn lại: 0/20
```

**Tariff MFN — 48 reporter đã có** (47 nước + `EUN` dùng chung cho toàn EU):
ARE ARG BDI BEN BFA BLR BOL BRA CAF CAN CHE CHN CIV COL ECU EGY EUN GBR HKG IDN
IND JPN KGZ KOR LSO MAR MDG MEX MOZ MYS NAM NER NIC PER PHL RUS RWA SEN SGP SWZ
TUR TZA UGA UKR USA VNM ZAF ZMB.

**Tariff PREF — mới xong 8 reporter đầu bảng chữ cái**: ARE, ARG, BDI, BEN, BFA,
BLR, BOL, BRA (dở). Còn 40 reporter chưa bắt đầu, trong đó có VNM, USA, EUN, CHN, JPN.

### 2.2. Bộ dữ liệu đã dựng trong `analysis/`

| File | Kích thước | Nội dung | Dùng được chưa |
|---|---|---|---|
| `spells.csv` | 12 MB · 157.101 dòng | một dòng/spell: `start_year`, `end_year`, `duration`, `event`, `right_censored` | ❌ chạy thử |
| `episodes.csv` | 19 MB · 176.808 dòng | một dòng/spell-năm (`t_start`/`t_stop`) để chạy Cox có biến thay đổi theo thời gian | ❌ chạy thử |
| `panel_final.csv` | 45 MB · 176.808 dòng · **36 cột** | episodes + thuế + vĩ mô + 13 cột NTM — **đây là file đích cuối cùng** | ❌ chạy thử |
| `macro_panel.csv` | 148 KB · 1.940 dòng | GDP growth, GDP, GDP/người, xuất khẩu %GDP theo nước-năm | ✅ |
| `ntm_sector.csv` | 100 KB · 1.200 dòng | bảng NTM nước × ngành, ghép thẳng vào panel | ✅ |
| `ntm_by_type.csv` | 235 KB · 3.944 dòng | NTM tách theo chương MAST (A/B/E…) | ✅ |
| `ntm_country.csv` | 7,6 KB · 150 dòng | coverage/frequency ratio cấp quốc gia | ✅ |

**36 cột của `panel_final.csv`** — độ phủ đo hôm nay:

| Nhóm | Cột | Có giá trị |
|---|---|---|
| Định danh | `spell_id`, `importer`, `exporter`, `product_family`, `year`, `t_start`, `t_stop`, `event` | 100% |
| Trade | `import_value_usd` | 100% |
| Tự tính ở mức HS6 | `rca`, `product_share_pct`, `partner_share_pct`, `hhi_market`, `hhi_product`, `country_growth_pct`, `world_growth_pct` | 100% |
| Thuế | `tariff_rate`, `tariff_type`, `tariff_source_year`, `tariff_reporter` | **6,2%** ⚠ |
| Vĩ mô | `exporter_gdp_growth_pct`, `exporter_gdp_usd`, `importer_gdp_growth_pct`, `importer_gdp_usd` | 98,7% |
| NTM (13 cột) | `ntm_reporter`, `ntm_survey_year`, `ntm_sector`, `ntm_coverage_ratio`, `ntm_frequency_ratio`, `ntm_sector_freq_any`, `ntm_sector_share_3plus`, `ntm_sps_coverage`, `ntm_tbt_coverage`, `ntm_quantity_coverage`, `ntm_technical_coverage`, `ntm_nontechnical_coverage`, `ntm_n_types` | 86,9% |

### 2.3. Đối chiếu 11 biến yêu cầu ban đầu

| # | Biến | Nguồn thật sự dùng | Mức chi tiết đạt được | Tình trạng |
|---|---|---|---|---|
| 1–2 | Trade value XK/NK | **UN Comtrade API** (có key) | HS6 × importer × exporter × năm | ⏳ mới 11% |
| 3 | Tariff | WITS `TRN`, MFN + PREF, lấy mức thấp hơn | HS6 | ⏳ MFN 97%, PREF 10% |
| 4 | RCA (Balassa) | **tự tính** từ panel Comtrade | HS6 family | ✅ |
| 5 | Product share | tự tính | HS6 family | ✅ |
| 6 | Partner share | tự tính | HS6 family | ✅ |
| 7 | Country growth | tự tính | HS6 family | ✅ |
| 8 | World growth | tự tính (thế giới = tổng trong mẫu) | HS6 family | ✅ |
| 9 | HHI thị trường + sản phẩm | tự tính (Herfindahl) | HS6 family | ✅ |
| 10 | **NTM** | 3 file công khai WITS | **cấp ngành, 1 lát cắt/nước** | ⚠ xem mục 3 |
| 11 | GDP growth | WITS `tradestats-development` (WDI) | nước × năm | ✅ |

> **Vì sao biến 4–9 phải tự tính:** WITS API chỉ cho các chỉ số này ở **31 nhóm
> ngành**, không có HS6 (`Invalid_Product` khi truyền mã HS6). Đây là phát hiện
> quan trọng nhất của vòng kiểm chứng — chi tiết ở [docs/KIEM_CHUNG_DU_LIEU_WITS.md](docs/KIEM_CHUNG_DU_LIEU_WITS.md) §3.1.
> Số liệu WITS cấp ngành vẫn nên dùng để **kiểm tra chéo** hướng và độ lớn.

---

## 3. Còn thiếu những gì

### 3.1. Thiếu do tải chưa xong (chỉ cần thời gian máy)

| Hạng mục | Còn thiếu | Ước tính thời gian |
|---|---|---|
| Trade HS6 | **941/1.060 file** | **~150 giờ** (≈6,5 ngày) với 4 luồng song song — theo log của luồng chậm nhất |
| Tariff MFN | ~29 file | vài chục phút |
| Tariff PREF | **~7.300 call** | ~15–20 giờ |
| Dựng lại `spells.csv` → `panel_final.csv` | phải chạy lại sau khi tải xong | ~15–30 phút |

Dung lượng `data_raw/` sẽ tăng từ **157 MB → ~1,2 GB** khi trade tải đủ.

### 3.2. Thiếu do bản chất nguồn dữ liệu (NTM — điểm nghẽn lớn nhất)

Cả 3 file NTM công khai của WITS đều **không có chiều năm ở mức sản phẩm**:

| File | Dòng | Vấn đề |
|---|---|---|
| `NTM-Trade-Frequency-Coverage-Ratio` | 152 | chỉ 76 nước, chỉ 2012–2017, **không có chiều sản phẩm** |
| `NTM-Prevalence-Sector` | 3.943 | **không có cột year** |
| `NTM-Indicators-Measure-Sector` | 24.264 | **không có cột year**, sản phẩm chỉ ở mức Sector |

Đã vắt kiệt những gì 3 file này chứa (13 cột NTM, tách theo chương MAST, độ phủ
EU nhờ ánh xạ `EUN`), nhưng vẫn còn **ba hạn chế cố hữu**:

1. **NTM là time-invariant** — một lát cắt/nước (2012–2017), đã ghi rõ trong cột
   `ntm_survey_year`. Đây là *thiết kế có chủ ý*, không phải sơ suất.
2. **NTM ở cấp ngành (16 nhóm), không phải HS6** — mọi sản phẩm trong cùng ngành
   nhận cùng một giá trị, nên biến không giải thích được biến thiên **trong** ngành.
3. **19/53 importer không có bản ghi NTM nào**, trong đó có **Trung Quốc và Hàn Quốc**:
   BDI, BLR, CAF, CHN, EGY, HKG, KGZ, KOR, LSO, MDG, MOZ, NAM, RWA, SWZ, TZA, UGA, UKR, ZAF, ZMB.

**Cái giá của việc gỡ được cả ba** đã được đo bằng cách gọi thật backend TRAINS Online:

| Chỉ tiêu | WITS công khai (đang dùng) | TRAINS Online (cần tài khoản) |
|---|---|---|
| Importer có dữ liệu | 34/53 | **50/53** (chỉ thiếu MDG, CAF, UKR) |
| Có ≥2 đợt khảo sát trong 2002–2021 → **biến đổi theo năm** | **0** | **28** |
| Độ chi tiết sản phẩm | ngành (16 nhóm) | **HS6** |
| EU | 1 lát cắt (2016) | 15 năm (2010–2025) |

→ Đăng ký tài khoản đổi được **28 nước từ time-invariant sang time-varying**, đúng
ranh giới giữa "biến kiểm soát" và "biến trung tâm" của bài.
Chi tiết từng nước: [selection/ntm_availability.csv](selection/ntm_availability.csv).

### 3.3. Thiếu do nguồn đã biến mất khỏi WITS

Các chỉ số dựng sẵn (**Export Duration**, RCA bulk, HHI bulk…) **không còn tải
được từ WITS** — trang bulk download nay chỉ là link trỏ sang World Bank Data
Catalog, và 2/4 file trên `datadownload.aspx` trả về trang 404. Không chặn dự án
(vì các biến này đã tự tính được), chỉ mất kênh đối chiếu.

### 3.4. Đối chiếu 6 yêu cầu trong [docs/essences.txt](docs/essences.txt)

| # | Yêu cầu | Tình trạng |
|---|---|---|
| 1 | NTM là biến trung tâm, không bỏ | ✅ 13 cột trong panel |
| 2 | Hiểu vì sao 3 file WITS không đủ | ✅ đã kiểm chứng, ghi rõ |
| 3 | Lấy TRAINS Online ở mức HS6 | ⚠️ **đã đo được giá trị; tải cần tài khoản** |
| 4 | Lấy WTO I-TIP | ❌ **cần API key miễn phí** |
| 5 | Coverage / frequency / tách theo loại NTM | ✅ cả ba, cấp nước và cấp ngành |
| 6 | Phương án dự phòng time-invariant | ✅ đã hiện thực hoá, có `ntm_survey_year` |

Ba ghi chú cuối `essences.txt` cũng đã xử lý: (1) chọn importer bằng dữ liệu
thay vì cảm tính, có fallback EU — ✅; (2) NTM hai đường — đường 1 xong, đường 2
chờ tài khoản; (3) hướng biến thuế = nước nhập khẩu áp lên hàng exporter — ✅.

### 3.5. Hai việc chỉ bạn mới làm được

| # | Việc | Vì sao tôi không tự làm được | Làm xong thì được gì |
|---|---|---|---|
| 1 | Đăng ký **trainsonline.unctad.org** → mục *Bulk Data Download* → tải "researcher file" (CSV/STATA) → đặt vào `data_raw/ntm/trainsonline/` | Endpoint dữ liệu trả mảng rỗng rồi `403` nếu chưa đăng nhập; trang dùng Azure AD (MSAL), không vòng qua được | NTM lên **HS6 × năm**, 50/53 importer, 28 nước có biến đổi theo thời gian |
| 2 | Đăng ký API key miễn phí ở **apiportal.wto.org** (WTO I-TIP) | `data.wto.org` trả 403, `api.wto.org` trả 401 vì thiếu subscription key | Phương án dự phòng: dummy theo **năm bắt đầu/kết thúc** từng biện pháp. Chỉ cần nếu việc 1 không thành |

Có file rồi, phần đọc và ghép vào panel tôi viết tiếp được ngay.

---

## 4. Bản đồ thư mục

```
wits/
├── README.md                     ← bạn đang đọc; trạng thái tổng thể
├── .env                          ← API key Comtrade (chmod 600, ĐÃ gitignore, KHÔNG gửi ai)
├── .gitignore
│
├── docs/                         Tài liệu — đọc theo thứ tự này
│   ├── essences.txt              yêu cầu gốc về NTM + 3 ghi chú của bạn
│   ├── guide.md                  khảo sát ban đầu về WITS (lý thuyết, có chỗ sai)
│   ├── KIEM_CHUNG_DU_LIEU_WITS.md  kiểm chứng thật 22 phép thử API — sửa lại guide.md
│   ├── TIEN_TRINH_THU_THAP.md    nhật ký thi công: quyết định nào, vì sao
│   └── DOI_CHIEU_ESSENCES_NTM.md  đối chiếu essences.txt ↔ workspace
│
├── scripts/                      Mã nguồn (chạy từ bất kỳ đâu, tự tìm gốc dự án)
│   ├── wits_probe.py             kiểm chứng API WITS → probe_out/
│   ├── select_countries.py       chọn 53 importer + 82 exporter → selection/
│   ├── fetch_tariffs.py          thuế HS6, hai pha mfn/pref → data_raw/tariffs/
│   ├── fetch_trade.py            trade value HS6 từ Comtrade → data_raw/trade/
│   ├── fetch_macro.py            GDP + tải 3 file NTM thô → analysis/, data_raw/ntm/
│   ├── fetch_ntm_availability.py bản đồ độ phủ NTM của TRAINS Online
│   ├── build_ntm.py              13 biến NTM tách theo chương MAST
│   ├── build_spells.py           dựng spell + RCA/HHI ở HS6
│   └── merge_panel.py            ghép tất cả → analysis/panel_final.csv
│
├── selection/    (9 file, 224 KB)  danh sách nước, data availability, ánh xạ thuế EU,
│                                   độ phủ NTM của TRAINS Online — TRACKED trong git
├── data_raw/     (157 MB → ~1,2 GB)  dữ liệu thô tải về — GITIGNORED
│   ├── trade/         119 file .csv.gz (HS6 theo importer-năm)
│   ├── tariffs/mfn/   912 file · tariffs/pref/ 784 file · _partnerlists.csv
│   ├── ntm/           3 file NTM công khai của WITS
│   └── concordance/   5 bảng chuyển đổi HS
├── analysis/     (75 MB)   kết quả dựng ra — GITIGNORED, gửi qua Drive
├── logs/         (108 KB)  log các luồng tải — GITIGNORED
└── probe_out/    (940 KB)  output 22 phép thử — GITIGNORED trừ _probe_log.csv
```

Thư mục này **chưa phải git repo**. Muốn dùng git: `git init && git add . && git commit`
— `.gitignore` đã sẵn sàng, dữ liệu nặng và `.env` sẽ tự động bị loại.

---

## 5. Chạy tiếp từ đúng chỗ đang dở

**Mọi script đều bỏ qua file đã tải xong**, nên cứ chạy lại là nó tiếp tục, không
tải lại thứ đã có. Dừng lúc nào cũng được.

```bash
cd /home/minhquang/wits

# 1) Tải nốt thuế (MFN gần xong, PREF mới 10%)
nohup python3 scripts/fetch_tariffs.py --pass all > logs/tariff_all.log 2>&1 &

# 2) Tải trade — chia 4 luồng, đây là đường găng (~150 giờ)
nohup python3 scripts/fetch_trade.py --importers USA,DEU,NLD,JPN,ITA,FRA,KOR,BEL,HKG,ARE,CAN,GBR,SGP > logs/trade_b0.log 2>&1 &
nohup python3 scripts/fetch_trade.py --importers CHN,MEX,VNM,BRA,MYS,IDN,TUR,ZAF,PHL,ARG,PER,COL,BLR > logs/trade_b1.log 2>&1 &
nohup python3 scripts/fetch_trade.py --importers IND,EGY,MAR,CIV,BOL,ZMB,NIC,TZA,NAM,SEN,BEN,KGZ,SWZ > logs/trade_b2.log 2>&1 &
nohup python3 scripts/fetch_trade.py --importers MOZ,UGA,BFA,MDG,RWA,NER,BDI,CAF,RUS,ESP,CHE,UKR,ECU,LSO > logs/trade_b3.log 2>&1 &

# 3) Sau khi tải xong — dựng lại toàn bộ (BẮT BUỘC, kết quả hiện tại đã cũ)
python3 scripts/build_ntm.py
python3 scripts/build_spells.py
python3 scripts/merge_panel.py
```

Bốn luồng là ngưỡng hợp lý; nhiều hơn thì `429` xuất hiện dày mà không nhanh thêm.

**Theo dõi tiến độ:**

```bash
ls data_raw/trade | wc -l          # đích 1.060
ls data_raw/tariffs/mfn | wc -l    # đích ~941
ls data_raw/tariffs/pref | wc -l   # đích ~8.078
tail -f logs/trade_b1.log
ps aux | grep fetch_ | grep -v grep   # rỗng = đã chết, cần chạy lại
```

**Kiểm tra bắt buộc sau khi dựng lại** — chưa đạt thì đừng tin kết quả mô hình:

```bash
python3 -c "
import pandas as pd
s = pd.read_csv('analysis/spells.csv')
p = pd.read_csv('analysis/panel_final.csv', low_memory=False)
print('right-censored:', int(s.right_censored.sum()), '(PHẢI > 0)')
print('số importer:', s.importer.nunique(), '(đích 53)')
print('episode có thuế: %.1f%%' % (100*p.tariff_rate.notna().mean()), '(đích > 90%)')
"
```

---

## 6. Những cái bẫy đã gặp — đừng đạp lại

Đây là phần dễ mất thời gian nhất nếu ai đó dựng lại pipeline từ đầu.

1. **Mã nước lịch sử của Comtrade.** `partnerAreas.json` có nhiều bản ghi cùng
   một mã ISO3: USA nằm ở cả 840, 842 và **841 = "USA and Puerto Rico (…1980)"**;
   Đức có 276 và **280 = "Fed. Rep. of Germany (…1990)"**. Tra bảng kiểu ghi đè
   → nhận mã đã ngừng dùng → **API trả 0 dòng mà không báo lỗi**. Cách đúng: bỏ
   bản ghi có `entryExpiredDate`, bỏ nhóm (`isGroup`), lấy `entryEffectiveDate`
   mới nhất. Kết quả đúng: USA 842, DEU 276, FRA 251, VNM 704, SRB 688.
2. **Thuế EU khai một lần dưới `EUN`.** Đức, Pháp, Ý, Hà Lan, Bỉ, Tây Ban Nha
   đều hiển thị **0 năm thuế** trong TRAINS. Không xử lý → **mất trắng toàn bộ
   thị trường EU**. Đã ánh xạ từng thành viên sang `EUN` từ năm gia nhập
   ([selection/eu_tariff_mapping.csv](selection/eu_tariff_mapping.csv)); Anh dùng
   EUN đến hết 2020, biểu riêng từ 2021. Bảng này dùng lại cho cả NTM.
3. **Đổi phiên bản HS giữa chừng.** Cùng năm 2019 Rwanda dùng H4 còn Mỹ dùng H5;
   mỗi nước còn đổi vài lần trong 20 năm. Một mã bị đánh số lại trông y hệt
   **một quan hệ chết đi và một quan hệ mới sinh ra** → hỏng toàn bộ phân tích
   duration. Cách xử lý: gom mã qua **thành phần liên thông** của đồ thị
   concordance → *product family* ổn định. Kiểm chứng: **14.042/14.042 mã khớp**.
4. **Comtrade cắt âm thầm ở 100.000 bản ghi/call** — không báo lỗi. Pipeline chia
   lô 20 exporter, tự tách nhỏ khi chạm trần, thử lại khi lô rỗng, và **không bao
   giờ cache một importer-year rỗng**.
5. **Endpoint `bulk/v1` của Comtrade trả 401** — không nằm trong gói Free API.
   `429` là throttle tức thời, không phải quota ngày; chờ ~20s là qua.
6. **WITS API: `product=ALL` + `year=ALL` → HTTP 413.** Tối đa 2 chiều `ALL`;
   với TRAINS phải cố định năm.
7. **Sai `partner`/`product` → 404 dù chỉ số vẫn tồn tại.** Mỗi indicator có quy
   định riêng (`999` cho partner, `999999` cho product khi "không áp dụng"), đọc
   ở endpoint `.../indicator/ALL`.
8. **Hai chỗ `guide.md` nói sai**, đã sửa trong tài liệu kiểm chứng: header
   `Accept: application/vnd.sdmx.data+json` **không có tác dụng** (phải dùng
   `?format=JSON`); mã `GDP-CURRENT-USD` **không tồn tại** (dùng `NY-GDP-MKTP-KD-ZG`).
9. **Đơn vị lệch nhau:** WITS tính bằng **nghìn USD**, Comtrade tính bằng **USD**.
10. **Mã D của hai bảng NTM khác thế hệ:** file WITS cũ ghi *D = Price control*,
    TRAINS Online hiện hành ghi *D = Contingent trade protective measures*.
    **Không được trộn mã D của hai nguồn.**

---

## 7. Ba hạn chế cần nêu chủ động trong phần Discussion

Reviewer trong ngành đã quen với các hạn chế này, nhưng chỉ chấp nhận khi tác giả
nói trước:

1. **NTM là time-invariant** — dữ liệu công khai chỉ có một đợt khảo sát mỗi nước
   (2012–2017), đã ghi trong `ntm_survey_year`.
2. **NTM ở cấp ngành** — không tách được biến thiên trong nội bộ ngành.
3. **"Thiếu dữ liệu" hay "không có biện pháp"?** — đúng vấn đề Carrère (2011) nêu.
   Trong pipeline này sự mơ hồ đó được xử lý ở **đúng một chỗ** và ghi rõ trong
   docstring của `build_ntm.py`: chương vắng mặt trong một nước-ngành *đã được
   khảo sát* tính là **0**; nước **không** được khảo sát để **trống**, không suy diễn.

Thêm một hạn chế về phạm vi: **"thế giới" trong RCA/HHI là tổng trong mẫu
53 importer × 82 exporter**, không phải toàn cầu — nên dùng số liệu WITS cấp
ngành để kiểm tra chéo hướng và độ lớn.

---

## 8. Gửi gì cho cộng sự

**Gửi 3 thư mục + README** (tổng ~76 MB, nén còn ~20 MB):

| Gửi | Dung lượng | Vì sao |
|---|---|---|
| **`analysis/`** | 75 MB | Bộ dữ liệu đích. `panel_final.csv` là file để chạy mô hình |
| **`selection/`** | 224 KB | Danh sách nước, ánh xạ EU, độ phủ NTM — cần để hiểu mẫu |
| **`docs/`** | 60 KB | Vì sao mọi thứ được quyết định như vậy |
| **`README.md`** | — | Bản đồ tổng thể |

**KHÔNG gửi:**

- **`.env`** — chứa API key Comtrade của bạn. Tuyệt đối không.
- `data_raw/` (157 MB → 1,2 GB) — chỉ gửi nếu cộng sự cần **tự dựng lại** panel;
  khi đó gửi kèm `scripts/`.
- `logs/`, `probe_out/`, `__pycache__/` — không có giá trị với người nhận.

```bash
cd /home/minhquang/wits
tar czf wits_data_$(date +%Y%m%d).tar.gz analysis selection docs README.md
```

> ⚠️ **Kèm cảnh báo khi gửi:** dữ liệu trong `analysis/` hiện là **bản chạy thử**
> (11% trade, 0 right-censored). Chỉ dùng để **kiểm tra cấu trúc cột và viết sẵn
> code mô hình**, không dùng để đọc kết quả. Gửi lại bản đầy đủ sau khi tải xong.

---

## 9. Việc tiếp theo, theo thứ tự ưu tiên

| # | Việc | Ai làm | Chặn cái gì |
|---|---|---|---|
| 1 | Khởi động lại 4 luồng `fetch_trade.py` + `fetch_tariffs.py --pass all` | máy | **mọi thứ** — đường găng ~150 giờ |
| 2 | Đăng ký TRAINS Online, tải researcher file vào `data_raw/ntm/trainsonline/` | **bạn** | NTM lên HS6 × năm |
| 3 | Sau khi tải xong: chạy lại `build_ntm` → `build_spells` → `merge_panel` | máy | panel dùng được |
| 4 | Kiểm tra right-censored > 0, importer = 53, thuế > 90% | máy | tin được kết quả |
| 5 | Viết phần đọc file TRAINS Online, thay 13 cột NTM time-invariant | máy | phụ thuộc #2 |
| 6 | (dự phòng) API key WTO I-TIP nếu #2 không thành | **bạn** | chỉ cần nếu #2 hỏng |
