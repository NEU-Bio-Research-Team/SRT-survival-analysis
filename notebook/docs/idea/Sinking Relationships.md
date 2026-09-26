## **"Sinking Relationships: Survival-Constrained Dynamic Reconfiguration of Vietnam's Export Portfolio under Tariff Policy Uncertainty"**

## **(Tên phụ tiếng Việt, dùng cho báo cáo nội bộ): "Tái cấu trúc động danh mục xuất khẩu Việt Nam dựa trên xác suất tồn tại của quan hệ thương mại dưới bất định chính sách thuế quan"**

## **Câu hỏi nghiên cứu cụ thể**

**Câu hỏi chính:** Việt Nam nên tái cấu trúc động (dynamically reconfigure — maintain/expand/reduce/enter/exit) danh mục các quan hệ xuất khẩu (nhà nhập khẩu × sản phẩm HS6) như thế nào để tối đa hóa giá trị xuất khẩu kỳ vọng dài hạn, trong khi vẫn duy trì một ngưỡng "khả năng tồn tại" (survivability) tối thiểu cho toàn bộ danh mục, khi các cú sốc chính sách thuế quan (như thuế đối ứng Mỹ 2025\) làm tăng xác suất chấm dứt (hazard) của các quan hệ xuất khẩu một cách không đồng đều giữa các ngành/thị trường?

**Câu hỏi phụ (robustness):** Kết quả trên có còn đứng vững khi kiểm soát thêm yếu tố hiệu suất logistics xanh (Green Logistics Performance Index) như một covariate bổ sung trong mô hình hazard không?

## **Ai có lợi nếu giải quyết được**

| Đối tượng | Lợi ích cụ thể |
| ----- | ----- |
| Doanh nghiệp xuất khẩu (đặc biệt dệt may, điện tử, thủy sản) | Biết trước quan hệ xuất khẩu nào (thị trường-sản phẩm) đang có hazard tăng cao để chủ động điều chỉnh trước khi mất đơn hàng, thay vì phản ứng sau khi đã đứt gãy |
| Hiệp hội ngành (VITAS, VASEP, VCCI) | Có công cụ early-warning cấp ngành để tư vấn thành viên tái phân bổ thị trường, đàm phán chính sách kịp thời |
| Nhà hoạch định chính sách (Bộ Công Thương, Bộ Tài chính) | Có bằng chứng định lượng về mức độ mong manh của cấu trúc xuất khẩu quốc gia, dùng để thiết kế chính sách hỗ trợ đa dạng hóa thị trường hoặc đàm phán FTA có mục tiêu |
| Nhà đầu tư/quỹ | Đánh giá rủi ro danh mục xuất khẩu của doanh nghiệp niêm yết phụ thuộc cao vào 1-2 thị trường |
| Học thuật quốc tế | Cung cấp khung lý thuyết nối survival analysis với portfolio optimization cho trade — áp dụng được cho các nước xuất khẩu tập trung khác (Bangladesh, Cambodia, Mexico) |

## **Đánh giá theo bảng tiêu chuẩn Q1 (đã cập nhật lại điểm dựa trên toàn bộ thảo luận)**

| Criterion | Weight | Score (1-10) | Weighted | Giải thích |
| ----- | ----- | ----- | ----- | ----- |
| Novelty | 20 | 8 | 160 | Chưa tìm thấy paper nối survival probability với optimization ra quyết định portfolio xuất khẩu cấp quốc gia; TPU-reallocation 2025 chỉ nhìn từ phía importer Mỹ |
| Gap significance | 15 | 8 | 120 | Giải quyết đúng khoảng trống giữa "giải thích duration" (literature cũ) và "ra quyết định dưới risk" (chưa ai làm cho trade) |
| Q1 journal fit | 15 | 7 | 105 | Fit với The World Economy, JIE nếu phần kinh tế mạnh; EJOR nếu phần OR đủ chặt — nhưng rủi ro "kẹt giữa 2 cộng đồng" |
| Theoretical contribution | 10 | 8 | 80 | Khung mới nối risk-of-termination vào decision-under-uncertainty cho trade |
| Methodological appropriateness | 10 | 8 | 80 | Survival \+ optimization cần thiết thật, pass được method-stuffing test |
| Data feasibility | 10 | 8 | 80 | UN Comtrade 2002-2021 đã có sẵn (1.1M dòng, 87 thị trường, HS6) — điểm mạnh nhất |
| Identification credibility | 10 | 6 | 60 | Endogeneity giữa tariff và chất lượng quan hệ vẫn là rủi ro chưa giải quyết hoàn toàn |
| Vietnam policy relevance | 5 | 8 | 40 | Trực tiếp giải quyết macro pain "mong manh cấu trúc xuất khẩu" |
| International/generalizability | 3 | 8 | 24 | Áp dụng được cho mọi nền kinh tế xuất khẩu tập trung |
| Execution feasibility | 2 | 6 | 12 | Khả thi nếu giữ ở Level 1-2, rủi ro tăng nếu cố lên Level 3 |
| **TỔNG (÷10)** | 100 |  | **76.1** |  |

## **Mô tả để giao cho người đi tìm dataset**

---

**Brief tìm dữ liệu cho đề tài: "Survival-Constrained Dynamic Reconfiguration of Vietnam's Export Portfolio under Tariff Policy Uncertainty"**

**Mục tiêu dữ liệu:** Xây dựng một panel dữ liệu ở cấp độ *quan hệ xuất khẩu* (Việt Nam × quốc gia nhập khẩu × mã sản phẩm HS6 × năm), đủ để (1) ước lượng mô hình survival/hazard cho từng quan hệ, và (2) chạy bài toán tối ưu hóa phân bổ portfolio.

**Đơn vị phân tích:** Một dòng dữ liệu \= (Vietnam, quốc gia nhập khẩu j, mã HS6 k, năm t).

**1\. Dữ liệu xuất khẩu (bắt buộc, nền tảng)**

* Nguồn: UN Comtrade (comtrade.un.org) hoặc CEPII BACI (baci đã làm sạch UN Comtrade, khuyến nghị dùng vì clean hơn).  
* Cần: kim ngạch xuất khẩu (value), khối lượng (quantity nếu có), theo Việt Nam-đối tác-HS6-năm.  
* Giai đoạn: tối thiểu 2002–2024 (dài hơn thì tốt, để có nhiều "spell" export quan sát được cả bắt đầu và kết thúc).  
* Việc cần làm: dựng "export spell" — với mỗi quan hệ (j,k), xác định năm bắt đầu xuất khẩu, năm kết thúc (nếu kim ngạch về gần 0 trong ≥2 năm liên tiếp thì coi là "chết"), và các quan hệ vẫn đang tồn tại đến năm cuối mẫu thì đánh dấu right-censored.

**2\. Dữ liệu thuế quan (bắt buộc, biến covariate chính)**

* Nguồn: WTO Tariff Analysis Online (TAO), WITS (World Bank), hoặc USITC DataWeb cho lịch sử thuế Mỹ áp lên hàng Việt Nam 2024-2025.  
* Cần: mức thuế MFN, thuế ưu đãi FTA (nếu có), và đặc biệt lịch sử thuế đối ứng Mỹ theo tháng/quý 2025 (46%→10%→20%/40%) theo ngành hàng.

**3\. Dữ liệu covariates chuẩn của gravity/survival model (bắt buộc)**

* Khoảng cách địa lý Việt Nam-đối tác (CEPII Gravity dataset — có sẵn, miễn phí).  
* GDP, GDP per capita đối tác (World Bank WDI).  
* Có FTA/RTA với Việt Nam hay không, năm có hiệu lực (WTO RTA database).  
* Độ phức tạp sản phẩm (product complexity index — Harvard Growth Lab Atlas of Economic Complexity, có sẵn).

**4\. Dữ liệu bổ sung cho robustness check (không bắt buộc ngay, làm sau)**

* Green Logistics Performance Index: xây từ World Bank Logistics Performance Index (LPI) components — công thức PCA đã có sẵn trong vài paper đã công bố (có thể xin tham khảo cách xây từ các bài GLPI Việt Nam 2024-2026).  
* Non-tariff measures (NTM): UNCTAD TRAINS database.

**5\. Output kỳ vọng từ người tìm dữ liệu**

* Một bảng panel sạch: (Vietnam, 87 or more partner, HS6, year) × \[export\_value, tariff\_rate, distance, GDP\_partner, RTA\_dummy, product\_complexity\].  
* Một cột đánh dấu spell\_start, spell\_end, censored (1/0) cho từng quan hệ.  
* Ghi rõ coverage: bao nhiêu quốc gia đối tác có dữ liệu đầy đủ, bao nhiêu năm liên tục, có lỗ hổng dữ liệu ở đâu.

**Lưu ý quan trọng:** Ưu tiên chất lượng và độ liên tục của time-series hơn là số lượng quốc gia — vì mô hình survival cần quan sát được cả sự kiện "sống" và "chết" theo thời gian, dữ liệu bị gián đoạn giữa các năm sẽ làm hỏng việc xác định spell.

# Ưu tiên nước khi tìm partner:

| Nhóm partner | Vai trò trong mô hình | Vì sao cần |
| :---- | :---- | :---- |
| Mỹ | Nguồn tariff shock chính (biến động 46%→10%→20%/40%) | Đây là biến covariate quan trọng nhất của toàn bộ đề tài |
| EU (27 nước) | Nguồn CBAM shock, khác loại risk với Mỹ | Cho phép so sánh hazard giữa 2 loại shock khác nhau (thuế thông thường vs carbon border) |
| ASEAN \+ Trung Quốc, Ấn Độ, Bangladesh | Nhóm cạnh tranh trực tiếp (trade diversion) | Giúp kiểm soát confound: quan hệ "chết" có thể do dịch chuyển thị trường, không chỉ do thuế |
| Nhật, Hàn, Úc (CPTPP/FTA có sẵn) | Nhóm có RTA ổn định, ít bị shock chính sách | Làm baseline/control group để so sánh hazard giữa nhóm có FTA bảo vệ và không có |
| Các thị trường nhỏ/mới nổi (châu Phi, Trung Đông, Mỹ Latinh) | Nhóm quan hệ dễ "chết" tự nhiên (thấp kim ngạch, ít ổn định) | Cần giữ để có đủ variation trong outcome (không phải tất cả quan hệ đều với thị trường lớn) |

