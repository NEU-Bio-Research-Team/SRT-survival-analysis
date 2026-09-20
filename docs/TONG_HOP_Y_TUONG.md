# Tổng hợp ý tưởng nghiên cứu — hợp nhất hai tài liệu định hướng

*Viết 21/08/2026. Nguồn: `docs/idea/TÓM TẮT DỰ ÁN NGHIÊN CỨU.md` (từ đây gọi là **Doc A**)
và `docs/idea/detail idea.md` (**Doc B**). Tài liệu này không thêm ý tưởng mới — nó đặt hai
tài liệu cạnh nhau, chỉ ra chỗ trùng, chỗ lệch, và đề xuất một cách hợp nhất.*

**Tiến độ dữ liệu tương ứng:** [MAPPING_IDEA_DATA.md](MAPPING_IDEA_DATA.md).

---

## 0. Kết luận đọc trước

Hai tài liệu **không phải hai phiên bản của cùng một đề tài**. Chúng là hai đề
tài khác nhau, khác cả câu hỏi, khác dữ liệu, khác đầu ra dự kiến:

| | Doc A (`TÓM TẮT DỰ ÁN NGHIÊN CỨU.md`) | Doc B (`detail idea.md`) |
|---|---|---|
| Bản chất | 5 ý tưởng ứng viên + 1 bản thẩm định chọn ra 1 | 1 kiến trúc nghiên cứu 6 tầng (L0–L5) |
| Cú sốc trung tâm | Thuế đối ứng Mỹ **2025** (46%→10%→20%/40%) | Rủi ro chấm dứt quan hệ xuất khẩu **2002–2023** |
| Đơn vị phân tích | Cặp quốc gia × hành động thuế (Tab 6); hoặc DN, hoặc HS10-tháng | `VN × importer × product family × năm` |
| Tần suất | Ngày / tháng / quý | Năm |
| Nguồn dữ liệu chính | WTO–IMF Tariff Tracker, US Census HS10, BCTC quý HOSE/HNX | UN Comtrade + WITS TRAINS |
| Đích ngắm | Giải thưởng / cuộc thi, timeline ngắn | Bài báo Q1/Q2, timeline dài |
| Phương pháp | Event study, DiD, Granger/Hawkes, MILP stochastic | Survival (Cox / discrete hazard) → optimization |

**Toàn bộ dữ liệu đã dựng trong workspace này phục vụ Doc B, không phục vụ
Doc A.** Panel dừng ở 2023 và biểu thuế dừng ở 2021, nên cú sốc thuế 2025 —
trục xương sống của cả 5 tab trong Doc A — **không nằm trong dữ liệu**. Đây là
điều phải quyết trước mọi thứ khác.

---

## 1. Doc A — năm ý tưởng ứng viên và bản thẩm định

Doc A gồm 5 tab ý tưởng, mỗi tab lập luận theo cùng một khung (tính cấp bách →
ai hưởng lợi → khả năng tối ưu hóa → research gap), rồi Tab 7 thẩm định và xếp
hạng cả 5.

### 1.1. Bảng năm ý tưởng

| Tab | Ý tưởng lõi | Phương pháp | Dữ liệu cần | Điểm mạnh | Rủi ro chí mạng |
|---|---|---|---|---|---|
| **1** | DSS logistics: dự báo rủi ro cước biển + tối ưu spot/contract, tồn kho đệm, định tuyến đa phương thức | Forecast + stochastic/inventory optimization | Booking, lead time, giá cước theo lane, tồn kho, chi phí stock-out | Pain point DN rõ nhất; có thể ra demo dashboard | Ôm 3 bài toán lớn cùng lúc; dữ liệu vi mô **không công khai** |
| **2** | Event-study/DiD đo trade diversion VN–Bangladesh–Ấn Độ–Trung Quốc | Event study, DiD | US Census HS10 **theo tháng** | Thiết kế causal chuẩn nhất; observation rất lớn | Xác định event date (công bố / hiệu lực / kỳ vọng); parallel trends khó vì VN vốn đã tăng thị phần |
| **4** | Tối ưu sourcing stochastic dưới bất định thuế Mỹ–VN, có mô hình hoá **phạt trung chuyển 40%** | MILP / stochastic optimization + SAA | Lịch sử thuế 2025, cấu trúc chi phí DN | Problem–method fit rất tốt; transshipment risk là cơ chế chính sách mới, chưa ai mô hình hoá | Cần decision-maker **thật sự có quyền chọn**; nếu tham số bị giả định thì đúng toán, sai kinh tế |
| **5** | I-O / Markowitz hoá cho 9 DN niêm yết, đối chiếu benchmark FEDEA/CESifo | Ước lượng co giãn + tối ưu danh mục thị trường | BCTC quý HOSE/HNX 2025 | Puzzle hay: GDP giảm <1% nhưng doanh thu DN giảm 18–69% | n = 9 và chuỗi thời gian ~4 quý → suy luận rất yếu; nhiễu từ order cycle, tỷ giá, giá bông |
| **6** | Vòng xoáy trả đũa thuế quan; VN là **nền kinh tế chịu spillover mà không trả đũa** | Event sequencing + distributed-lag / Hawkes (Granger chỉ là robustness) | WTO–IMF Tariff Tracker (ngày hiệu lực, HS6, song phương) | Câu hỏi hẹp, dữ liệu công khai sẵn, gap được định lượng bởi review 2026 | Dễ overclaim nhân quả nếu bám Granger |

### 1.2. Bản thẩm định của Tab 7

Thứ tự ưu tiên Doc A đề xuất:

1. **Tab 6 (Idea 3)** — chọn để thi.
2. Tab 2 — dự phòng, nếu đội mạnh về DiD/econometrics.
3. Tab 4 — nếu cuộc thi chấm cao innovation/optimization hơn causal research.
4. Tab 1 — chỉ khi có dữ liệu/mentor logistics thật.
5. Tab 5 — không nên làm phương án chính.

Ba lý do Tab 6 thắng: câu hỏi hẹp và trả lời được trong nguồn lực sinh viên;
data–method fit tốt; novelty rõ nhờ góc "VN là nước không trả đũa nhưng chịu
phơi nhiễm".

### 1.3. Điều chỉnh bắt buộc mà Doc A yêu cầu với Tab 6

> **Không được viết:** "Granger causality chứng minh nước A gây ra nước B trả đũa."

Granger chỉ nói quá khứ của A giúp dự báo B tốt hơn trong tập thông tin của mô
hình; nó không tự tạo nhận dạng nhân quả, nhất là khi hai nước cùng phản ứng với
một cú sốc chung.

Framing được đề xuất thay thế:

> **"Dynamic retaliation and spillover in tariff escalations: Evidence from
> high-frequency tariff actions and Vietnam's exposure."**

Ba câu hỏi nghiên cứu:

1. Các cặp quốc gia có tồn tại chuỗi hành động thuế mang tính phản ứng có hệ
   thống theo độ trễ không?
2. Phản ứng khác nhau ra sao giữa Mỹ–Trung, Mỹ–EU, Mỹ–Ấn Độ: tức thời, có điều
   kiện, hay trì hoãn?
3. Khi escalation tăng, VN đối mặt exposure nào theo ngành và theo kênh nào:
   trade diversion, quy tắc xuất xứ/transshipment, hay cầu nhập khẩu suy yếu?

Thiết kế 4 tầng:

| Tầng | Nội dung | Độ chắc chắn |
|---|---|---|
| 1 | Tariff-action panel theo country-pair, ngành/HS, ngày công bố + ngày hiệu lực | Chắc, nếu có dữ liệu |
| 2 | Descriptive event sequencing: độ trễ, chuỗi escalation/de-escalation | **Chắc nhất** |
| 3 | Distributed-lag / panel event study / Hawkes process cho tính self-exciting; Granger chỉ là robustness | Vừa |
| 4 | Vietnam spillover module: exposure index theo tỷ trọng xuất khẩu / phụ thuộc thị trường | Chắc |

---

## 2. Doc B — kiến trúc nghiên cứu 6 tầng

Doc B **không phải 6 đề tài độc lập**. Đó là một cái thang: L0 là baseline,
mỗi bậc trên thêm đúng **một** vấn đề nghiên cứu mới, và mỗi bậc phải đủ hoàn
chỉnh để thành một paper nếu nhóm dừng ở đó.

Đối tượng trung tâm: **export market–product relationship** của Việt Nam, biểu
diễn là `Việt Nam → nước nhập khẩu → HS6`. **Không phải** bài tối ưu tuyến vận
tải, xe, kho hay shipment.

Bài toán gốc: VN nên lựa chọn/tái phân bổ các export relationship như thế nào
để đạt export performance tốt mà không xây một portfolio quá dễ tổn thương?
Điểm mới: **không coi mọi trade relationship có độ bền như nhau** — survival risk
được đưa từ một *kết quả mô tả* thành một *đầu vào của quyết định*.

### 2.1. Sáu bậc thang

| Level | Tên | Câu hỏi chính | Điểm mới thêm vào | Vị trí |
|---|---|---|---|---|
| **L0** | Traditional Export Portfolio Optimization | Chọn market–product nào để tối đa hoá export performance? | Baseline, chưa có survival | Benchmark |
| **L1** | Survival-Adjusted Export Portfolio | Nếu mỗi relationship có xác suất sống khác nhau, lựa chọn tối ưu có đổi không? | Survival **điều chỉnh** expected export | Fallback khả thi |
| **L2** | Survival-Constrained Export Diversification | Portfolio vừa profitable vừa đạt survivability tối thiểu như thế nào? | Survival thành **ràng buộc**; thêm HHI/diversification | Target trung gian |
| **L3** | Dynamic Survival-Aware Export Network Reconfiguration | Khi risk/state đổi theo thời gian, network nên maintain/expand/reduce/enter/exit thế nào? | **Thời gian + state transition + quyết định động** | **CORE TARGET** |
| **L4** | Export Network Reliability Optimization | Khi relationship là edge của một hệ thống, network còn giữ được performance khi edge fail thế nào? | Individual survival → **system reliability** | Extension có điều kiện |
| **L5** | Correlated Failure / Common-Shock Resilience | Nếu nhiều relationship cùng chịu một shock và failure không độc lập, network nên thiết kế thế nào? | **Dependence / correlated failure** + stress testing | Frontier, khó nhất |

Chuỗi logic:

> Export value → Survival → Diversification/Resilience → Dynamic Reconfiguration
> → Network Reliability → Common-Shock Resilience

Mỗi mũi tên phải tương ứng với **một câu hỏi nghiên cứu mới, một thành phần mô
hình mới và một contribution kiểm chứng được** — không được chỉ là thêm thuật
toán hoặc thêm ràng buộc cho phức tạp.

### 2.2. Bốn nguyên tắc Doc B nhấn mạnh

1. **Level cao hơn không mặc nhiên tốt hơn.** Novelty tăng cùng difficulty và
   data requirement.
2. **Không thêm thuật toán chỉ để mô hình phức tạp hơn.** Không được chốt
   GA/ACO/MDP trước khi có formulation.
3. **Survival analysis không phải contribution tự thân.** Contribution nằm ở
   *cách survival information được dùng cho network decision*.
4. **Chọn level cao nhất mà chứng minh được đầy đủ** bằng data + model +
   validation trong thời gian có — không chọn level cao nhất vì nó nghe hay.

### 2.3. Mười hai thứ Doc B bắt buộc chốt trước khi code

| # | Câu hỏi | Trạng thái trong workspace |
|---|---|---|
| 1 | Decision-maker: chính phủ hay export planner đại diện? | ❌ chưa chốt |
| 2 | Unit of analysis: `VN × importer × HS6 × năm` | ✅ đã hiện thực hoá (product family thay HS6 thô) |
| 3 | Spell: threshold, start, end, event, right-censoring | ✅ đã chốt và đã dựng |
| 4 | Export performance: value, expected value, growth hay metric khác | ❌ chưa chốt |
| 5 | Survival horizon: 1/3/5 năm | ❌ chưa chốt |
| 6 | Network definition: node/edge và mức gộp | ❌ chưa chốt |
| 7 | Network survival/reliability: định nghĩa toán **và** kinh tế | ❌ chưa chốt |
| 8 | Actions: maintain/expand/reduce/enter/exit đo bằng gì | ❌ chưa chốt |
| 9 | Tariff: dùng MFN / faced / preferential nào, hạn chế gì | ⚠️ đã dựng, còn hạn chế mã nhóm |
| 10 | Objective/constraints: mỗi thành phần phải có ý nghĩa kinh tế | ❌ chưa chốt |
| 11 | Algorithm: chọn **sau** formulation | ❌ chưa tới |
| 12 | Validation: benchmark, backtest, sensitivity/stress test | ❌ chưa thiết kế |

---

## 3. Chỗ hai tài liệu gặp nhau

Bốn điểm chung, và đây là phần dùng lại được cho bất kỳ hướng nào:

1. **Cùng một đối tượng lo lắng:** cấu trúc xuất khẩu của VN quá tập trung và
   quá dễ tổn thương trước cú sốc ngoại sinh.
2. **Cùng một kiểu đầu ra:** không dừng ở mô tả, phải ra được một công cụ hoặc
   một khuyến nghị phân bổ.
3. **Cùng một biến then chốt:** mức độ tập trung thị trường/sản phẩm (HHI,
   partner share, product share) và mức phơi nhiễm theo đối tác.
4. **Cùng một cảnh báo phương pháp:** cả hai tài liệu đều tự cảnh báo không được
   overclaim — Doc A về Granger, Doc B về việc gọi tên "reliability" cho một chỉ
   số thật ra chỉ là tổng xuất khẩu hoặc HHI đổi tên.

Thêm một cầu nối cụ thể: **Tầng 4 của Tab 6 (Vietnam spillover exposure index)
tính được từ chính panel đã dựng** — product share, partner share,
`vn_market_share_pct`, HHI đều đã có ở mức `importer × product family × năm`.

---

## 4. Chỗ hai tài liệu lệch nhau — phần quan trọng nhất

| Chiều | Doc A | Doc B | Hệ quả |
|---|---|---|---|
| **Cửa sổ thời gian** | 2025 là toàn bộ nội dung | 2002–2023 | Không giao nhau. Dữ liệu hiện có **không chạm tới** cú sốc 2025 |
| **Tần suất** | Ngày/tháng/quý | Năm | Panel năm không đo được chuỗi phản ứng "trong 30 ngày" |
| **Rủi ro trung tâm** | Bất định *chính sách thuế* | Rủi ro *chấm dứt quan hệ* | Hai hazard khác nhau; không thay thế cho nhau |
| **Vai trò của VN** | Bên chịu spillover, thụ động | Bên ra quyết định, chủ động tái phân bổ | Decision-maker khác nhau hoàn toàn |
| **Kiểu đóng góp** | Đo lường + kiểm định | Formulation + optimization | Cộng đồng journal khác nhau |
| **Timeline** | Ngắn, chạy đua với cửa sổ chính sách | Dài, chịu được nhiều vòng review | Không cùng lịch |

**Điều này có nghĩa gì trên thực tế:**

- Nếu chọn **Doc A / Tab 6**: gần như phải bắt đầu lại phần dữ liệu. Cần WTO–IMF
  Tariff Tracker (đang chờ API key I-TIP), và panel hiện có chỉ đóng góp được ở
  Tầng 4 (exposure index) — mà cũng chỉ với dữ liệu đến 2023, tức là *trước* cú
  sốc cần giải thích.
- Nếu chọn **Doc B / L1–L3**: dữ liệu đã sẵn sàng ở mức cao. Việc còn lại là
  **modeling**, không phải thu thập.
- **Không nên** cố ghép cưỡng bức hai cái làm một paper. Cái giá là một bài vừa
  không đủ sâu về survival vừa không đủ tần suất về retaliation.

---

## 5. Đề xuất hợp nhất

Đề xuất: giữ **Doc B làm cây chính**, coi **Doc A là nguồn động lực và là hai
đầu ra phụ**, thay vì bắt hai tài liệu phải thắng nhau.

```
                    Panel survival VN 2002–2023 (đã có)
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   NHÁNH JOURNAL            NHÁNH THI                NHÁNH MỞ RỘNG
   (Doc B, L1 → L2 → L3)    (Doc A, Tab 6 T4)        (Doc B, L4 → L5)
        │                        │                        │
  survival-aware           exposure index VN         reliability +
  export portfolio         theo ngành/đối tác        correlated shock
  + dynamic reconfig       + timeline 2025 nếu       (cần dữ liệu sốc,
                           có I-TIP key              đã có shocks_annual)
```

**Lý do:**

- Nhánh journal đứng trên dữ liệu đã kiểm chứng, không phụ thuộc vào bất kỳ
  hành động đăng ký tài khoản nào.
- Nhánh thi tái sử dụng đúng các biến đã tính (share, HHI, market share) nên
  chi phí biên thấp; phần bổ sung duy nhất là timeline hành động thuế 2025.
- Nhánh mở rộng dùng `shocks_annual.csv` (17 chỉ số giá hàng hoá + chỉ số bất
  định chính sách toàn cầu) — đã tải sẵn, chính là thứ L5 cần.

**Thứ tự làm, theo đúng tinh thần thang bậc của Doc B:**

| Bước | Việc | Chặn cái gì |
|---|---|---|
| 1 | Chốt 12 định nghĩa ở §2.3 — đặc biệt decision-maker, export performance, survival horizon | Mọi thứ phía sau |
| 2 | Kaplan–Meier + Cox baseline trên `spells.csv` / `panel_final.csv`; kiểm tra survival có **phương sai thật** giữa các relationship | L1 trở đi. Nếu survival không phân biệt được relationship thì cả cái thang sụp |
| 3 | Dựng L0 benchmark (tối ưu không có survival) | Điểm so sánh |
| 4 | L1: đưa xác suất sống vào hàm mục tiêu | Paper fallback |
| 5 | L2: thêm ràng buộc survivability + HHI | Target trung gian |
| 6 | L3: định nghĩa state/action/transition, backtest chính sách động | Core target |
| 7 | Song song: exposure index cho nhánh thi | Không chặn nhánh journal |

**Cửa quyết định:** sau bước 2. Nếu survival model cho thấy hazard phân biệt
được rõ giữa các relationship → đi tiếp L2/L3. Nếu không → dừng ở L1, và cân
nhắc chuyển trọng tâm sang nhánh thi.

---

## 6. Những cảnh báo cả hai tài liệu đều nêu, gộp lại

1. **Không gọi bài này là transportation optimization.** Đối tượng là quan hệ
   thị trường–sản phẩm, không phải tuyến vận tải. (Doc B §17)
2. **Không overclaim nhân quả từ Granger.** (Doc A, Tab 7)
3. **Không đổi tên một chỉ số cũ thành "reliability".** Network reliability phải
   có định nghĩa toán học *và* kinh tế riêng. (Doc B §9.4)
4. **Không claim "optimal strategy for all Vietnam export markets"** khi độ phủ
   chưa đủ. (Doc B §12)
5. **Không chốt thuật toán trước formulation.** (Doc B §8.5)
6. **Mô hình tối ưu phải có decision-maker thật sự có quyền chọn** — nếu không
   có phương án thay thế thực tế, bài toán suy biến về một phương án duy nhất.
   (Doc A, Tab 4 và Tab 7)
7. **Mẫu nhỏ + chuỗi ngắn = suy luận yếu.** (Doc A, Tab 5)
8. **Journal được map sớm nhưng không được kéo sai research question.**
   (Doc B §15)

---

## 7. Map cộng đồng journal (theo Doc B §15)

| Level | Cộng đồng cần khảo sát |
|---|---|
| L1 | International Trade / Applied Economics + Survival/Econometric Methods + Optimization |
| L2 | International Trade + Trade Diversification/Resilience + Operations Research |
| L3 | Supply Chain / Network Resilience + Operations Research + International Trade |
| L4 | Reliability / Network Science + Operations Research + Trade Supply Network Resilience |
| L5 | Reliability/Resilience + Stochastic/Robust Optimization + Network Science + International Trade |

Bộ lọc sau đó: Scopus indexing → Q1/Q2 đúng subject category → scope → paper gần
topic/method trong 3 năm gần đây → article type → kỳ vọng phương pháp →
empirical/mathematical fit → novelty và feasibility.

---

## 8. Ba câu hỏi phải trả lời trước cuộc họp nhóm tiếp theo

1. **Đích của nhóm là cuộc thi hay bài báo?** Hai đích này dẫn tới hai bộ dữ
   liệu khác nhau và hai timeline khác nhau. Không trả lời được câu này thì mọi
   việc phía sau đều có thể phải làm lại.
2. **Có lấy được API key WTO I-TIP không, và khi nào?** Đây là điều kiện cần
   *duy nhất* cho toàn bộ Doc A. Nếu không có, Doc A phải bỏ hoặc đổi nguồn.
3. **Decision-maker là ai?** Chính phủ hay một export planner đại diện? Doc B
   nói rõ không được thay đổi tuỳ đoạn — và câu trả lời quyết định luôn hình
   dạng của objective function.
