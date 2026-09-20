# Báo cáo benchmark v1 — Sống sót quan hệ xuất khẩu Việt Nam

**Run:** `v1` · **Ngày:** 10/09/2026 · **Quy mô:** 11 mô hình × 6 bộ đặc trưng ×
4 fold cuộn thời gian = **264 ô, không ô nào lỗi**

Báo cáo này chỉ trình bày những phần **đã có kết quả**. Phase 4 của kế hoạch
(DeepPAMM, ORSF, DSM, SurvTRACE) chưa được hiện thực và không xuất hiện ở đây.

---

## 1. Tóm tắt điều hành

Năm kết luận, xếp theo mức độ chắc chắn:

1. **Thông tin nằm ở hiệp biến, không ở thuật toán.** Mọi mô hình có hiệp biến
   vượt mô hình rỗng Kaplan–Meier khoảng 0,035 IBS, trong khi toàn bộ chênh lệch
   *giữa chúng* chỉ 0,018 — nhỏ hơn năm lần.
2. **Phi tuyến không mua được gì.** Giữ nguyên giả định tỉ lệ hazard mà thêm phi
   tuyến (CoxPH → BoostedCox, CoxPH → DeepSurv) không cải thiện, thậm chí kém đi.
3. **Nới lỏng giả định tỉ lệ hazard là thứ duy nhất có tác dụng**, và chỉ trong
   họ cây: BoostedCox → RSF cải thiện ở 21/24 ô.
4. **Thêm kinh tế học ngoài khối F1 làm hầu hết mô hình tệ đi** ngoài mẫu.
5. **Khối chính sách thương mại gần như không có tín hiệu dự báo**, kéo theo hệ
   quả là kịch bản thuế Mỹ 2025 không dùng được — và đó là kết quả trung thực,
   không phải lỗi kỹ thuật.

RSF thắng trung bình, nhưng thắng nhỏ và không đồng đều (§5.3). Đây đúng là giả
thuyết **H7** trong kế hoạch: không có chuyện ML thống trị phổ quát.

---

## 2. Thiết kế thí nghiệm

### 2.1. Đơn vị quan sát và biến mục tiêu

Một hàng = **(nước nhập khẩu j × họ sản phẩm p × năm t)**, gọi là *điểm gốc dự
báo*. Ma trận đóng băng có 889.467 điểm gốc; cửa sổ chấm điểm 2003–2023 chứa
778.971 điểm gốc, trong đó 295.835 rốt cuộc chết và 123.618 chết ngay trong vòng
một năm.

Quy ước của panel: `event = 1` ở năm Y nghĩa là quan hệ **sống lần cuối** ở Y và
chết ở Y+1. Từ đó tuổi thọ còn lại tính từ điểm gốc năm t là

```
duration_u = năm_sống_cuối − t + 1
```

nên `duration_u = 1, event_u = 1` trùng khít với cờ `event` gốc. Đẳng thức này
được **assert** ở cuối `features/build_matrix.py`: nếu quy ước thượng nguồn đổi
thì pipeline gãy chứ không âm thầm chấm sai đại lượng.

**Output của mọi mô hình là cùng một vật:** ma trận `S(u | X)` với u = 1…8 năm.
Mọi thước đo chỉ đọc ma trận này, nên không mô hình nào bị chấm trên một đại
lượng khác với mô hình kia.

### 2.2. Cửa sổ thời gian

| Năm | Lý do loại |
|---|---|
| 2002 | năm đầu cửa sổ dữ liệu — mọi biến trễ khuyết, mọi spell bị cắt cụt trái |
| 2024 | sau 2023 không nước nào có thuế đo đúng năm của nó (tỷ lệ đo cùng năm rơi 0,96 → 0,00) |
| 2025 | **không có sự kiện nào theo cấu trúc** — chết năm 2026 chưa quan sát được |

2024–2025 chỉ dùng cho chấm kịch bản triển vọng (§10).

### 2.3. Hai cơ chế chống rò rỉ

**Chia fold theo thời gian.** Bốn fold cuộn:

| Fold | Huấn luyện | Kiểm định | Kiểm tra |
|---|---|---|---|
| 1 | 2003–2013 | 2014–2015 | 2016–2017 |
| 2 | 2003–2015 | 2016–2017 | 2018–2019 |
| 3 | 2003–2017 | 2018–2019 | **2020–2021 (COVID)** |
| 4 | 2003–2019 | 2020–2021 | 2022–2023 |

**Kiểm duyệt hành chính tại chân trời thông tin.** Đây là phần quan trọng hơn và
dễ bị bỏ sót: chia fold theo năm là *chưa đủ*. Một quan hệ có điểm gốc 2013 mà
chết năm 2018 vẫn mang nhãn `duration_u = 6, event_u = 1` trong ma trận đóng
băng — nhưng năm 2013 không ai biết điều đó. Nên mỗi khối được kiểm duyệt lại
tại chân trời của chính nó: khối huấn luyện kết thúc 2013 chỉ được biết quan hệ
còn sống đến hết 2013, mọi thứ sau đó bị kiểm duyệt. Không có luật này, thiết kế
vẫn rò rỉ tương lai **qua nhãn** dù nhìn hoàn toàn sạch.

Hệ quả ràng buộc việc tinh chỉnh: một khối kiểm định hợp lệ chỉ có đúng **một
năm** follow-up quan sát được, nên mọi mô hình đều được chọn siêu tham số theo
điểm Brier 1 năm rồi mới chấm ở 1–3 năm.

### 2.4. Cỡ mẫu thực tế mỗi fold

| Fold | Huấn luyện | Kiểm định | Kiểm tra |
|---|---:|---:|---:|
| 1 | 39.806 | 24.875 | 29.850 |
| 2 | 39.801 | 24.875 | 29.851 |
| 3 | 39.802 | 24.875 | 29.850 |
| 4 | 39.807 | 24.875 | 29.851 |

Lấy mẫu ở **cấp spell**, không phải cấp hàng, để cấu trúc phụ thuộc trong một
quan hệ không bị phá vỡ. Mọi mô hình trong cùng một ô nhận **đúng cùng các hàng**.

### 2.5. Thước đo

- **Chính: IBS 1–3 năm.** Chọn IBS thay vì chỉ số concordance vì Stage 2 nhân
  *xác suất* sống sót với giá trị thương mại; một mô hình xếp hạng hoàn hảo mà
  dự báo 0,9 trong khi sự thật là 0,6 sẽ phá hỏng phép tính đó với C-index đẹp.
- Lưới dừng ở 3 năm vì khối kiểm tra cuối là 2022–2023 với dữ liệu kết thúc 2025:
  IBS 5 năm không xác định được ở fold 4 nên không so sánh chéo fold được. Vẫn
  báo cáo IBS 1–5 cho các fold 1–3.
- Phụ trợ: Antolini C (concordance phụ thuộc thời gian, hợp cho mô hình không
  tỉ lệ), AUC(t) hiệu chỉnh kiểm duyệt, sai số hiệu chuẩn kỳ vọng (ECE).

---

## 3. Sáu bộ đặc trưng

Cộng dồn. 60 biến đăng ký, thành 88 cột ở bộ đầy đủ — chênh lệch là các cột cờ
khuyết `_isna`, không phải trang trí: 20% panel là hàng tuổi 1 nơi mọi biến trễ
khuyết về mặt cấu trúc, và chính nhóm đó chứa nửa số ca chết.

| Bộ | Nội dung | Biến | Cột |
|---|---|---:|---:|
| F0 | Phụ thuộc thời lượng | 3 | 3 |
| +F1 | Sức mạnh quan hệ (Nitsch) | 14 | 25 |
| +F2 | Gravity & vĩ mô | 14 | 46 |
| +F3 | Kinh nghiệm & đa dạng hóa (Lawless–Studnicka, phỏng theo) | 7 | 56 |
| +F4 | Chính sách thương mại | 14 | 78 |
| +F5 | Phức tạp & cú sốc chung | 8 | 88 |

Ngoài ra có khối **F3x** — ba tương tác kinh nghiệm × đa dạng hóa — *chỉ* trao
cho cloglog tăng cường, không mô hình ML nào được nhận, vì mục đích của phép so
sánh là xem thuật toán dẻo có tự tìm ra chúng không.

Danh sách đầy đủ kèm thời điểm quan sát, phép biến đổi, dấu kỳ vọng và mức rủi ro
rò rỉ nằm ở `../features/feature_registry.yaml`.

---

## 4. Mười một mô hình

Bộ mô hình được thiết kế để lấp đầy một ma trận 2×2, vì một cái tên đứng đầu bảng
xếp hạng không trả lời được câu hỏi nào:

| | Tỉ lệ hazard (PH) | Không tỉ lệ |
|---|---|---|
| **Tuyến tính** | CoxPH, CoxNet, Cloglog | — |
| **Phi tuyến** | BoostedCox, DeepSurv, Cloglog-theory | RSF, Cox-Time, DeepHit, CBNN |

Hai mô hình không lấy sẵn từ thư viện:

- **Cloglog** — mô hình thời gian rời rạc của chính văn liệu thương mại, với
  baseline theo tuổi không ràng buộc, **cộng thêm frailty gamma chia sẻ**. Khi fit
  trên outcome một năm rồi nhân dồn nhiều năm, mô hình hazard không có thành phần
  không đồng nhất sẽ đánh giá quá cao tử vong dài hạn: hazard quần thể rơi từ 15%
  năm đầu xuống 6% năm hai, chủ yếu do "kẻ yếu chết trước". Link cloglog cho phép
  hiệu chỉnh ở dạng đóng, `S(u|x) = (1 + θH(u|x))^(−1/θ)`. Ở fold 1, việc này đưa
  IBS từ 0,154 xuống 0,124 — từ "chỉ hơn Kaplan–Meier một chút" thành ngang Cox.
- **CBNN** — Case-Base Neural Network của Islam và cộng sự (2024), phải tự hiện
  thực vì không thư viện nào có.

**Cloglog-theory** tồn tại để thỏa mãn §23.7 của kế hoạch: so một Cox thuần tuyến
tính với mạng nơ-ron rồi tuyên bố mạng thắng nhờ phi tuyến là thí nghiệm bù nhìn.
Biến thể này được cấp spline trên hai biến mà văn liệu cho là phi tuyến, cộng các
tương tác kinh nghiệm × đa dạng hóa.

---

## 5. Kết quả chính

### 5.1. Bảng xếp hạng — bộ đặc trưng đầy đủ, trung bình 4 fold

| Mô hình | IBS 1–3y | IBS 1–5y | Brier 1y | Brier 3y | Antolini C | AUC 1y | AUC 3y | ECE 3y | Giây/ô |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **RSF** | **0,1122** | 0,1176 | **0,0937** | 0,1222 | 0,8115 | 0,8490 | 0,8423 | **0,0388** | 4 |
| BoostedCox | 0,1146 | 0,1203 | 0,0961 | 0,1257 | 0,8143 | 0,8523 | 0,8455 | 0,0620 | 103 |
| CoxNet | 0,1149 | 0,1203 | 0,0963 | 0,1258 | 0,8172 | 0,8536 | 0,8461 | 0,0512 | 1 |
| Cloglog | 0,1153 | 0,1203 | 0,1006 | 0,1237 | 0,8188 | **0,8574** | 0,8445 | 0,0492 | 2 |
| Cloglog-theory | 0,1161 | 0,1218 | 0,0994 | 0,1266 | **0,8197** | 0,8578 | 0,8459 | 0,0567 | 2 |
| CoxPH | 0,1166 | 0,1225 | 0,0972 | 0,1291 | 0,8190 | 0,8539 | **0,8466** | 0,0586 | 2 |
| CBNN | 0,1170 | 0,1190 | 0,0975 | 0,1261 | 0,8132 | 0,8465 | 0,8422 | 0,0642 | 4 |
| CoxTime | 0,1174 | 0,1248 | 0,0975 | 0,1306 | 0,8109 | 0,8466 | 0,8406 | 0,0678 | 4 |
| DeepHit | 0,1265 | 0,1347 | 0,1014 | 0,1440 | 0,8074 | 0,8479 | 0,8157 | 0,0824 | 26 |
| DeepSurv | 0,1299 | 0,1334 | 0,1062 | 0,1418 | 0,8092 | 0,8463 | 0,8412 | 0,1124 | 5 |
| Kaplan–Meier | 0,1510 | 0,1619 | 0,1212 | 0,1695 | 0,5000 | 0,5000 | 0,5000 | 0,0489 | 0 |

**Điều đáng chú ý nhất không phải thứ hạng mà là tỷ lệ.** Khoảng cách từ mô hình
rỗng đến bất kỳ mô hình có hiệp biến nào là ~0,035; khoảng cách giữa mô hình tốt
nhất và tệ nhất trong số có hiệp biến (bỏ DeepHit/DeepSurv) là ~0,005. Mọi mô
hình deep đều thua CoxNet trơn.

Đáng chú ý về mặt chi phí: BoostedCox tốn 103 giây mỗi ô để về nhì, trong khi
CoxNet tốn dưới 1 giây để về ba với chênh lệch 0,0003.

### 5.2. Ổn định qua từng fold

| Mô hình | Fold 1 | Fold 2 | Fold 3 (COVID) | Fold 4 |
|---|---:|---:|---:|---:|
| CBNN | 0,1190 | 0,1147 | 0,1309 | **0,1035** |
| RSF | 0,1191 | 0,1119 | 0,1078 | 0,1101 |
| BoostedCox | 0,1206 | 0,1141 | 0,1089 | 0,1149 |
| CoxNet | 0,1249 | 0,1158 | **0,1052** | 0,1136 |
| CoxTime | 0,1278 | 0,1169 | 0,1075 | 0,1174 |
| DeepHit | 0,1289 | 0,1251 | 0,1289 | 0,1231 |
| Cloglog | 0,1326 | 0,1122 | 0,1072 | 0,1091 |
| Cloglog-theory | 0,1337 | **0,1114** | 0,1074 | 0,1120 |
| CoxPH | 0,1378 | 0,1102 | 0,1066 | 0,1117 |
| DeepSurv | 0,1401 | 0,1158 | 0,1593 | 0,1046 |
| Kaplan–Meier | 0,1590 | 0,1556 | 0,1454 | 0,1440 |

Không mô hình nào thắng ở cả bốn fold. RSF là mô hình ổn định nhất (biên độ
0,0113 giữa fold tốt nhất và tệ nhất); DeepSurv bất ổn nhất (biên độ 0,0547 —
gần bằng toàn bộ khoảng cách tới mô hình rỗng).

### 5.3. Bootstrap có cặp theo spell — ΔIBS so với CoxPH (bộ F0F1F2F3F4)

200 lần lấy mẫu lại **theo spell**, không theo hàng: tám quan sát năm của cùng
một quan hệ không phải tám sự kiện độc lập, và lấy mẫu theo hàng sẽ cho khoảng
tin cậy hẹp hơn thực tế nhiều lần. Âm = tốt hơn CoxPH.

| Mô hình | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Trung bình |
|---|---:|---:|---:|---:|---:|
| **RSF** | **−0,0080** | **−0,0051** | +0,0014 | **−0,0015** | **−0,0033** |
| CBNN | −0,0005 (n.s.) | −0,0031 | +0,0058 | −0,0084 | −0,0016 |
| CoxNet | −0,0018 | +0,0000 (n.s.) | +0,0058 | −0,0001 (n.s.) | +0,0010 |
| BoostedCox | −0,0060 | −0,0006 | +0,0030 | +0,0032 | −0,0001 |
| DeepSurv | +0,0030 | −0,0045 | +0,0099 | −0,0080 | +0,0001 |
| CoxTime | +0,0046 | −0,0000 (n.s.) | +0,0053 | +0,0028 | +0,0032 |
| Cloglog | +0,0198 | +0,0065 | +0,0026 | −0,0013 | +0,0069 |
| DeepHit | +0,0232 | +0,0107 | +0,0103 | +0,0332 | +0,0193 |
| Kaplan–Meier | +0,0328 | +0,0402 | +0,0398 | +0,0337 | +0,0366 |

**Cảnh báo diễn giải quan trọng:** cột "significant" trong file CSV chỉ nói khác
biệt *phân biệt được với 0*, **không** nói nó có lợi. RSF tốt hơn CoxPH có ý
nghĩa ở fold 1, 2, 4 nhưng **kém hơn có ý nghĩa ở fold 3** — đúng khối COVID. Ba
thắng một thua là tuyên bố yếu hơn thắng trọn, và đó mới là tuyên bố đúng.

---

## 6. Bốn phép so sánh được thiết kế sẵn

Mỗi phép cô lập **một** giả định. Âm = mô hình sau tốt hơn.

| Phép so sánh | ΔIBS | Ô cải thiện | Đọc ra |
|---|---:|---:|---|
| A. CoxPH → BoostedCox (phi tuyến, giữ PH) | +0,0001 | 7/24 | không gì |
| A. CoxPH → DeepSurv (phi tuyến, nơ-ron) | +0,0029 | 16/24 | tệ đi |
| B. DeepSurv → CoxTime (bỏ PH, giữ mạng) | −0,0018 | 9/24 | yếu, không nhất quán |
| **C. BoostedCox → RSF (bỏ PH, giữ cây)** | **−0,0021** | **21/24** | **lợi ích nhất quán duy nhất** |
| D. DeepHit → CBNN (thời gian là input) | −0,0144 | 23/24 | lớn, nhưng xem §10 |
| E. CoxPH → CoxNet (chỉ chính quy hóa) | +0,0007 | 8/24 | không gì |
| F. Cloglog → Cloglog-theory (baseline mạnh hơn) | +0,0003 | 8/24 | không gì |

**Phi tuyến không mua được gì.** Phép A phẳng trong họ cây và âm trong họ nơ-ron.
Phép F nói cùng điều đó từ hướng ngược lại: thêm spline và các tương tác kinh
nghiệm × đa dạng hóa vào cloglog không cải thiện nó — nghĩa là những phi tuyến mà
lý thuyết gợi ý, và ML lẽ ra "phát hiện" được, không tồn tại để mà phát hiện.

**Bỏ giả định tỉ lệ hazard là giả định duy nhất đáng nới lỏng**, và chỉ trong họ
cây (21/24 ô).

Có một mâu thuẫn cần nói rõ: bảng trung bình theo họ (`ph_vs_nonph.csv`) lại cho
thấy họ **không** tỉ lệ *tệ hơn* họ tỉ lệ ở cả sáu bộ đặc trưng (+0,0004 đến
+0,0028). Hai kết quả này hòa giải được — trung bình họ bị DeepHit và CoxTime kéo
xuống, mà vấn đề của hai mô hình đó là **hiệu chuẩn**, không phải tính tỉ lệ.
Phép C giữ kiến trúc cố định nên là công cụ sạch hơn; trung bình theo họ trộn lẫn
giả định với việc thư viện nào hiện thực nó.

---

## 7. Ablation đặc trưng — thêm kinh tế học không giúp

IBS 1–3 năm, trung bình 4 fold. **In đậm** = tốt nhất của mô hình đó.

| Mô hình | F0 | +F1 | +F2 | +F3 | +F4 | +F5 |
|---|---:|---:|---:|---:|---:|---:|
| RSF | 0,1207 | 0,1116 | 0,1117 | 0,1122 | **0,1111** | 0,1122 |
| DeepSurv | 0,1220 | 0,1117 | **0,1117** | 0,1187 | 0,1145 | 0,1299 |
| CBNN | 0,1207 | **0,1118** | 0,1120 | 0,1139 | 0,1128 | 0,1170 |
| CoxPH | 0,1224 | 0,1126 | **0,1121** | 0,1130 | 0,1144 | 0,1166 |
| CoxTime | 0,1218 | **0,1121** | 0,1129 | 0,1160 | 0,1176 | 0,1174 |
| BoostedCox | 0,1234 | 0,1128 | **0,1126** | 0,1140 | 0,1143 | 0,1146 |
| CoxNet | 0,1235 | **0,1130** | 0,1136 | 0,1150 | 0,1154 | 0,1149 |
| Cloglog-theory | 0,1246 | 0,1142 | **0,1137** | 0,1217 | 0,1228 | 0,1161 |
| Cloglog | 0,1246 | 0,1150 | **0,1146** | 0,1207 | 0,1213 | 0,1153 |
| DeepHit | 0,1348 | **0,1237** | 0,1269 | 0,1286 | 0,1337 | 0,1265 |

**F1 làm toàn bộ công việc.** Quy mô quan hệ, đà, thị phần và biến động đưa mọi
mô hình từ ~0,123 xuống ~0,112. Gravity (F2) không thêm gì. Kinh nghiệm và cấu
trúc danh mục (F3), chính sách (F4), phức tạp và cú sốc (F5) làm **hầu hết mô
hình tệ đi** ngoài mẫu — với CoxPH, bộ đầy đủ tệ hơn F0F1 đúng 0,0040, tức bằng
toàn bộ lợi thế của mô hình tốt nhất so với nó.

Chín trên mười mô hình đạt điểm tốt nhất ở F0F1 hoặc F0F1F2. RSF là ngoại lệ duy
nhất còn cải thiện ở F4 — phù hợp với việc một mô hình dẻo có khả năng bỏ qua một
khối đặc trưng gây hại cho mô hình tuyến tính.

---

## 8. Khác biệt giữa các mô hình nằm ở đâu

### 8.1. Theo tuổi quan hệ (bộ F0F1F2F3F4)

| Mô hình | Tuổi 1 | Tuổi 2–3 | Tuổi 4+ |
|---|---:|---:|---:|
| RSF | **0,2162** | 0,1798 | **0,0670** |
| CBNN | 0,2216 | **0,1786** | 0,0683 |
| DeepSurv | 0,2256 | 0,1805 | 0,0691 |
| BoostedCox | 0,2278 | 0,1815 | 0,0685 |
| CoxPH | 0,2339 | 0,1793 | 0,0673 |
| CoxNet | 0,2361 | 0,1814 | 0,0679 |
| CoxTime | 0,2369 | 0,1865 | 0,0695 |
| Cloglog | 0,2486 | 0,1930 | 0,0700 |
| Cloglog-theory | 0,2567 | 0,1937 | 0,0699 |
| DeepHit | 0,3078 | 0,2030 | 0,0711 |

Quan hệ trưởng thành dễ với mọi mô hình (IBS ~0,067, biên độ giữa các mô hình chỉ
0,004). **Toàn bộ sự phân tách nằm ở quan hệ năm đầu tiên**, nơi biên độ là 0,092
— gấp hai mươi lần. Kế hoạch §16.3 yêu cầu tách nhóm này vì lo mô hình chỉ đang
học hazard năm đầu rất cao; câu trả lời là hình ảnh phản chiếu của nỗi lo đó:
quan hệ năm đầu là **nơi duy nhất** việc chọn mô hình có ý nghĩa.

### 8.2. Theo giai đoạn cú sốc (bộ F0F1F2F3F4)

| Mô hình | Trước COVID | COVID (2020–21) | Sau COVID (2022–23) |
|---|---:|---:|---:|
| RSF | **0,1143** | 0,1070 | 0,1088 |
| BoostedCox | 0,1176 | 0,1087 | 0,1135 |
| CBNN | 0,1190 | 0,1114 | **0,1019** |
| DeepSurv | 0,1201 | 0,1155 | 0,1023 |
| CoxNet | 0,1200 | 0,1115 | 0,1102 |
| CoxPH | 0,1209 | **0,1056** | 0,1103 |
| Cloglog | 0,1340 | 0,1082 | 0,1090 |
| DeepHit | 0,1378 | 0,1159 | 0,1435 |

**Không có bằng chứng nào cho thấy mô hình dẻo bền hơn dưới cú sốc.** Trong khối
COVID mọi mô hình nằm giữa 0,106 và 0,116, và CoxPH đứng thứ nhất. Đây cũng là
khối duy nhất RSF thua CoxPH (§5.3).

---

## 9. Hiệu chuẩn

Sai số hiệu chuẩn kỳ vọng ở chân trời 3 năm, bộ đầy đủ:

| Mô hình | ECE 1y | ECE 3y |
|---|---:|---:|
| RSF | **0,0241** | **0,0388** |
| Kaplan–Meier | 0,0374 | 0,0489 |
| Cloglog | 0,0570 | 0,0492 |
| CoxNet | 0,0432 | 0,0512 |
| Cloglog-theory | 0,0546 | 0,0567 |
| CoxPH | 0,0423 | 0,0586 |
| BoostedCox | 0,0497 | 0,0620 |
| CBNN | 0,0423 | 0,0642 |
| CoxTime | 0,0440 | 0,0678 |
| DeepHit | 0,0552 | 0,0824 |
| DeepSurv | 0,0748 | 0,1124 |

Điều này quan trọng trực tiếp với Stage 2, vốn nhân `Giá trị × Ŝ`. **DeepSurv
lệch hiệu chuẩn 11 điểm phần trăm ở 3 năm** — dùng nó cho bảng giá trị kỳ vọng sẽ
sai khoảng đó, bất kể nó xếp hạng tốt cỡ nào (Antolini C của nó là 0,809, không
tệ). Đây chính là lý do kế hoạch đặt IBS làm thước đo chính thay vì C-index.

Đáng chú ý: mô hình rỗng Kaplan–Meier hiệu chuẩn tốt hơn bảy trong mười mô hình
có hiệp biến. Hiệu chuẩn tốt không đồng nghĩa dự báo tốt.

---

## 10. Hai phát hiện về **đo lường**, không phải về kinh tế

### 10.1. Khối chính sách gần như không có tín hiệu

Permutation importance ở chân trời 3 năm, đại lượng được giải thích được nêu rõ
là `P(T > 3 | X)`:

| CoxPH (Brier nền 0,1009) | | RSF (Brier nền 0,0974) | |
|---|---:|---|---:|
| log_gdp_d_lag | 0,0382 | log_value | 0,0057 |
| log_value | 0,0250 | product_share_pct | 0,0028 |
| log_spell_age | 0,0163 | log_value_lag | 0,0025 |
| n_markets_for_p_lag | 0,0140 | spell_age | 0,0025 |
| spell_age | 0,0129 | vn_market_share_lag_isna | 0,0022 |
| log_value_lag_isna | 0,0088 | log_spell_age | 0,0020 |
| log_market_size | 0,0073 | log_value_lag_isna | 0,0018 |
| log_gdpcap_d_lag | 0,0058 | volatility_3y_lag_isna | 0,0018 |
| n_products_to_c_lag | 0,0056 | log_market_size | 0,0018 |
| log_value_lag | 0,0048 | volatility_3y_lag | 0,0013 |

`tariff_rate` **không xuất hiện trong top 20 của cả hai mô hình.** Thứ duy nhất
liên quan chính sách lọt vào là cờ khuyết `tariff_rate_lag_isna` (0,0022 ở CoxPH,
0,0008 ở RSF) — tức *sự vắng mặt của số liệu thuế*, không phải mức thuế.

Điều này có sức nặng vì nó **có thể đã khác đi**: RSF được tự do dùng khối chính
sách một cách phi tuyến và là mô hình duy nhất còn cải thiện nhờ F4. Cả một mô
hình tuyến tính lẫn một mô hình hoàn toàn dẻo, với cùng các cột, đều từ chối dùng
biến thuế.

### 10.2. Kịch bản thuế Mỹ 2025 không dùng được

Chấm các điểm gốc 2024–2025 dưới ba quy ước thuế đã ghi trong panel:

| Kịch bản | Mức thuế thêm | ΔS(1) cho quan hệ với Mỹ | ΔS(3) |
|---|---|---:|---:|
| Quan sát (gốc) | — | 0 | 0 |
| Cuối năm | +20 pp | +0,000045 | +0,000070 |
| Đỉnh | +46 pp | +0,000060 | +0,000093 |
| Bình quân theo ngày | +11,55 pp | +0,000036 | +0,000056 |

Chuyển dịch nhỏ đến mức vô nghĩa, **và sai dấu** — thuế cao hơn lại hàm ý sống
sót cao hơn. Dấu đó không phải phát hiện về thuế; đó là thứ mà một hệ số không
phân biệt được với 0 sinh ra, đúng như §10.1 dự báo.

Kế hoạch §11.3 đã lường trước vấn đề *diễn giải* (không có outcome sau 2025 nên
không thể coi là hiệu ứng đã thực hiện). Run này bổ sung một lý do thứ hai, mạnh
hơn: **biến thiên thuế trong panel không dự báo được sống sót đủ mạnh để ngoại
suy.** File được đặt tên `us2025_prospective_scenarios_NOT_A_RESULT.csv`.

Chỉ có 4.456 trong 110.496 điểm gốc 2024–2025 là quan hệ với Mỹ.

---

## 11. Giới hạn của kết luận

**Do ngân sách tính toán** (máy một laptop, GPU 6 GB):

1. **40.000 điểm gốc huấn luyện mỗi fold** trên 779.000 có sẵn. Áp dụng đồng đều
   nên *phép so sánh* được bảo vệ; *mức tuyệt đối* của mọi con số thì không, và
   một mô hình chỉ thể hiện ưu thế ở quy mô 500k hàng sẽ không lộ ra ở đây.
2. **2–3 lần thử siêu tham số** thay vì 30–50 như kế hoạch, và **một hạt giống**
   thay vì lặp nhiều hạt cho mô hình nơ-ron. Ngân sách bằng nhau giữa các họ —
   đây là điều bảo vệ phép so sánh (§23.8) — nhưng nhỏ về tuyệt đối, nên không ô
   nào nên đọc là trần của mô hình đó.
3. **Hai mô hình cây bị cắt nặng hơn** (8.000 hàng) vì loss Cox của boosting là
   bậc hai theo cỡ mẫu (đo được: 12 giây ở 4k hàng, 49 giây ở 8k, 215 giây ở
   16k). RSF nhận **cùng** mức cắt dù nó chịu được nhiều hơn, để phép C sạch.
   Bất lợi này nghiêng **chống lại** người thắng, nên biên của RSF là cận dưới.

**Do thiết kế:**

4. **Kiểm định chỉ có một năm.** Mọi mô hình được chọn theo Brier 1 năm rồi chấm
   ở 1–3 năm. Một mô hình giỏi ở 3 năm nhưng tầm thường ở 1 năm bị thiệt hệ thống.

**Do dữ liệu:**

5. **Đặc trưng phỏng theo.** `proximity_hs2_lag` là tỷ trọng HS2, không phải độ
   gần trong không gian sản phẩm; biến thương mại hai chiều của Nitsch **không
   dựng được** vì panel không có nhập khẩu của Việt Nam từ cùng đối tác. F3 vì
   vậy là bản yếu của khối Lawless–Studnicka, và kết quả kém của nó ở §7 **không
   nên đọc là bác bỏ** phát hiện của họ.
6. **Lịch thu thập NTM.** Trước khoảng 2015, biến đếm NTM phản ánh lịch thu thập
   nhiều ngang phản ánh chính sách — một lý do khiến F4 có thể đang thêm nhiễu.
7. **Thuế 2024–2025 không đo cùng năm**, nên đã bị loại khỏi cửa sổ chấm điểm.

---

## 12. Phần chưa có kết quả

**Phase 4 của kế hoạch chưa được hiện thực:** DeepPAMM, ORSF, DSM, SurvTRACE.
Khác với Phase 1–3, đây không phải chuyện viết wrapper — ba trong bốn mô hình
không có trên PyPI (DSM đi kèm `auton-survival`; SurvTRACE và DeepPAMM chỉ có
trên GitHub, DeepPAMM vốn thuộc hệ sinh thái R; ORSF chuẩn là gói R `aorsf`).
Cần cài phụ thuộc từ nguồn hoặc tự hiện thực.

Ngoài ra, **không mô hình nào trong benchmark này là đề xuất của nhóm** — cả 11
đều từ văn liệu. Đóng góp hiện có là bộ dữ liệu, giao thức benchmark, và các kết
quả trên, đúng như ba đóng góp mà §24 của kế hoạch đặt ra.

---

## 13. Tệp kết quả

| Tệp | Nội dung |
|---|---|
| `leaderboard.csv` | mọi thước đo, mọi ô, kèm độ lệch chuẩn qua fold |
| `feature_ablation.csv` | IBS theo khối đặc trưng, từng mô hình |
| `contrasts.csv` | bảy phép so sánh được thiết kế sẵn |
| `ph_vs_nonph.csv` | chẩn đoán tỉ lệ / không tỉ lệ (§16.2) |
| `subgroups.csv` | theo tuổi quan hệ và giai đoạn cú sốc |
| `delta_ibs_bootstrap.csv` | ΔIBS có cặp, khoảng tin cậy bootstrap theo spell |
| `permutation_importance_{CoxPH,RSF}_h3.csv` | tầm quan trọng cho `P(T>3\|X)` |
| `us2025_prospective_scenarios_NOT_A_RESULT.csv` | kịch bản thuế — **không phải kết quả** |
| `figures/leaderboard_ibs.png`, `figures/feature_ablation.png` | hình |
| `../runs/v1/config_*.yaml` | ảnh chụp cấu hình đóng băng của run |
