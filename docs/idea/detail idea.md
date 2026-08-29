**RESEARCH PROPOSAL**  
 **SURVIVAL-AWARE EXPORT NETWORK & DYNAMIC OPTIMIZATION**

*Bản định hướng để nhóm thống nhất idea, architecture, cách triển khai và kế hoạch hành động*

# **1\. Mục đích của tài liệu**

Tài liệu này dùng để cả nhóm thống nhất cùng một cách hiểu trước khi modeling, coding và tìm journal. Mục tiêu không phải khóa ngay một model tối đa, mà xây một research ladder: mỗi level có một câu hỏi và contribution riêng; level cao hơn phát triển từ level thấp hơn bằng cách thêm một vấn đề nghiên cứu mới. Nhóm chỉ đi lên level tiếp theo khi data, phương pháp và thời gian cho phép.

Điểm quan trọng: đây là một research architecture, không phải 6 topic độc lập. Level 0 là baseline; Level 1–5 là các mức mở rộng. Mỗi level phải đủ logic để có thể trở thành một paper nếu nhóm dừng ở đó.

# **2\. Ý tưởng gốc – nhóm thực sự đang nghiên cứu gì?**

Đối tượng trung tâm là export market–product relationship của Việt Nam, có thể biểu diễn là Vietnam → importing country → HS6 product. Đây không phải bài tối ưu tuyến vận tải, xe, kho hay shipment.

Bài toán gốc: Việt Nam nên lựa chọn/tái phân bổ các export relationships như thế nào để đạt export performance tốt nhưng không xây một portfolio/network quá dễ tổn thương? Điểm mới được định hướng là không coi mọi trade relationship có độ bền giống nhau; survival risk được đưa từ một kết quả mô tả sang đầu vào của decision/optimization. File idea mô tả decision problem là market-product strategy, với objective là expected export performance và các nhóm constraint về risk, concentration, tariff và số market. fileciteturn5file8L611-L629

# **3\. Research ladder tổng thể**

| Level | Tên | Câu hỏi chính | Điểm mới thêm vào |
| :---- | :---- | :---- | :---- |
| 0 | Traditional Export Portfolio Optimization | Chọn market–product nào để tối đa hóa export performance? | Baseline; chưa có survival. |
| 1 | Survival-Adjusted Export Portfolio | Nếu mỗi relationship có xác suất sống khác nhau, lựa chọn tối ưu có thay đổi không? | Survival → điều chỉnh expected export. |
| 2 | Survival-Constrained Export Diversification | Portfolio vừa profitable vừa đạt survivability tối thiểu như thế nào? | Survival → network constraint; thêm diversification/concentration. |
| 3 | Dynamic Survival-Aware Export Network Reconfiguration | Khi risk/state thay đổi theo thời gian, network nên maintain/expand/reduce/enter/exit thế nào? | Time \+ state transition \+ dynamic decision. |
| 4 | Export Network Reliability Optimization | Khi relationships là các edges của một system, network còn đạt performance/reliability khi edges fail thế nào? | Individual survival → system reliability. |
| 5 | Correlated Failure / Common-Shock Resilience | Nếu nhiều relationships cùng chịu một shock và failure không độc lập, network nên được thiết kế thế nào? | Dependence/correlated failure \+ stress testing. |

# **4\. Nguyên tắc của research ladder**

·        Level cao hơn không mặc nhiên tốt hơn. Novelty tăng cùng với difficulty và data requirement.

·        Không thêm thuật toán chỉ để model phức tạp hơn. Mỗi level phải có research question mới.

·        Level cao phải giữ được logic của level thấp; lower levels có thể trở thành baseline/building blocks.

·        Level 0 là benchmark. Level 1–2 là fallback khả thi. Level 3 là core target đề xuất. Level 4–5 là extensions có điều kiện.

·        Journal không quyết định research question. Nhóm xác định contribution trước, sau đó map sang journal community và journal cụ thể.

# **5\. LEVEL 0 – Traditional Export Portfolio Optimization**

## **5.1. Research question**

Among observed Vietnam export market–product relationships, which portfolio maximizes export performance under feasible concentration, tariff and other constraints?

## **5.2. Thành phần**

·        Decision variable: chọn/không chọn hoặc phân bổ cho country × product relationship.

·        Objective: maximize export performance.

·        Constraints: concentration/diversification, tariff exposure, số lượng market hoặc các giới hạn thực sự có thể parameterize.

·        Optimization algorithm chỉ chọn sau khi mathematical formulation được chốt.

## **5.3. Vai trò**

Đây là baseline, không phải contribution cuối cùng. Nó cần để so sánh: traditional optimization cho kết quả gì trước khi survival được đưa vào.

# **6\. LEVEL 1 – Survival-Adjusted Export Portfolio**

## **6.1. Logic**

Một relationship có export value cao chưa chắc là lựa chọn dài hạn tốt nếu xác suất termination cao. Survival model được dùng để estimate relationship-specific survival probability rồi đưa probability này vào expected long-term export value. File đặt trực tiếp research question của hướng này là portfolio nào tối đa hóa long-term expected export value sau khi accounting cho probability of relationship termination. fileciteturn6file1L85-L95

## **6.2. Pipeline**

1\.     Historical export data → construct export spells.

2\.     Estimate duration/survival model (ví dụ Cox hoặc discrete-time hazard; chưa chốt model).

3\.     Estimate P(survival over chosen horizon).

4\.     Combine survival probability với export value/expected export.

5\.     Optimize portfolio using survival-adjusted objective.

6\.     Compare với Level 0 baseline.

## **6.3. Contribution**

Chuyển từ “maximize current export” sang “maximize long-term expected export after accounting for relationship termination risk”.

## **6.4. Giới hạn**

Nếu chỉ dừng ở survival-adjusted objective, novelty có thể chưa đủ cao. File đánh giá hướng này rất hợp data nhưng thấp hơn các hướng dynamic/network về độ sâu. fileciteturn6file0L56-L66

# **7\. LEVEL 2 – Survival-Constrained Export Diversification**

## **7.1. Research question**

Can Vietnam construct an export portfolio that maximizes export performance while maintaining a minimum level of network survivability?

## **7.2. Insight**

Diversification nhiều không đồng nghĩa với resilience cao. File đưa ví dụ 10 markets có survival 0.45 có thể kém resilient hơn 5 markets có survival 0.95. fileciteturn6file3L238-L250

## **7.3. Thành phần**

·        Export value/performance.

·        Relationship survival probability.

·        Partner share, product share và HHI.

·        Minimum network survivability constraint.

·        HHI/concentration constraint.

·        Tariff exposure constraint nếu measurement đủ tin cậy.

·        Optimization và comparison với portfolio không có survival constraint.

## **7.4. Contribution**

Survival không còn chỉ điều chỉnh value; nó trở thành điều kiện mà portfolio phải đạt. Câu hỏi chuyển từ “portfolio kiếm nhiều tiền nhất” sang “portfolio kiếm nhiều tiền nhưng vẫn đủ survivable”. File formulation minh họa network survival ≥ α, HHI ≤ Hmax và tariff exposure ≤ Tmax. fileciteturn6file3L250-L265

# **8\. LEVEL 3 – Dynamic Survival-Aware Export Network Reconfiguration**

## **8.1. Vì sao đây là core target đề xuất?**

Level 2 vẫn thiên về chọn portfolio. Level 3 đưa time vào decision: risk thay đổi → trạng thái relationship thay đổi → decision cũng phải thay đổi. File gọi đây là dynamic optimization và cho các action maintain/expand/reduce/exit/enter. fileciteturn6file1L103-L145

## **8.2. Research question**

How should Vietnam dynamically reconfigure its export market–product relationships to maximize long-term export performance while maintaining a minimum level of network survivability under trade-barrier shocks?

## **8.3. Thành phần**

| Thành phần | Ý nghĩa |
| :---- | :---- |
| Relationship state | Trạng thái theo thời gian, ví dụ alive/dead hoặc state phù hợp với dữ liệu. |
| Survival model | Ước lượng hazard/survival từ duration, event và covariates. |
| Expected performance | Export value/growth hoặc metric performance đã được định nghĩa. |
| Trade barriers | Tariff/NTM được đưa vào risk, attractiveness hoặc constraint theo formulation được kiểm chứng. |
| Dynamic decisions | Maintain, expand, reduce, enter, exit. |
| Constraints | Network survivability, HHI/concentration, tariff exposure và feasibility. |
| Time loop | Observe state/risk → optimize → update portfolio/network → evaluate next period. |
| Benchmark | Static diversification và survival-adjusted static optimization. |

## **8.4. Early warning**

Nếu hazard tăng, optimizer có thể giảm exposure hoặc chuẩn bị replacement trước failure thay vì chờ relationship chết. File mô tả đây là proactive reallocation/reconfiguration. fileciteturn6file1L116-L145

## **8.5. Scope warning**

Không mặc định Level 3 \= Cox \+ MDP \+ GA \+ stochastic optimization \+ multi-objective. State, action, transition, objective và constraints phải được định nghĩa trước; algorithm đến sau. File cũng khuyến nghị đi từng tầng thay vì nhảy thẳng vào một model quá lớn. fileciteturn6file8L592-L604

# **9\. LEVEL 4 – Export Network Reliability Optimization**

## **9.1. Research question**

How reliable/resilient is the export network when individual trade relationships can terminate, and how should the network be designed to preserve system-level export performance?

## **9.2. Conceptual bridge**

File lấy tư duy từ reliability của physical system: component failure → system reliability, rồi chuyển sang export network: relationship termination → network reliability. Mỗi relationship là một edge; khi edge chết, network mất một connection. fileciteturn6file2L198-L227

## **9.3. Thành phần**

·        Network definition: nodes, edges và aggregation level phải chốt.

·        Edge survival probabilities từ survival model.

·        Failure scenario.

·        System/network performance threshold.

·        Network reliability metric.

·        Optimization để chọn/reconfigure network.

## **9.4. Điều kiện để làm**

Phải định nghĩa network reliability có ý nghĩa kinh tế và toán học; không chỉ đổi tên tổng export hoặc HHI thành 'reliability'.

# **10\. LEVEL 5 – Correlated Failure / Common-Shock Resilience**

## **10.1. Vấn đề**

Các relationships có thể không fail độc lập. Global recession, tariff war, shipping disruption hoặc geopolitical shock có thể làm nhiều relationships tăng risk hoặc terminate cùng lúc. File nêu trực tiếp vấn đề correlated failure/common shocks. fileciteturn6file3L250-L277

## **10.2. Thành phần**

·        Individual relationship hazard/survival.

·        Common shock variables hoặc scenario definitions.

·        Dependence/correlation structure giữa failures.

·        Network reliability dưới correlated failure.

·        Stress testing.

·        Robust/stochastic optimization nếu data và formulation đủ mạnh.

## **10.3. Vị trí**

Đây là extension research-y nhất nhưng cũng khó nhất; không nên cam kết làm ngay.

# **11\. Core, fallback và extension**

| Mức | Đề xuất |
| :---- | :---- |
| L0 | Baseline/benchmark. |
| L1 | Fallback paper khả thi nếu muốn ưu tiên chắc chắn. |
| L2 | Target trung gian có contribution tốt. |
| L3 | CORE TARGET đề xuất: Dynamic Survival-Aware Export Network Reconfiguration. |
| L4 | Advanced extension nếu network-reliability formulation đủ chặt. |
| L5 | Frontier extension; chỉ làm nếu dependence/common-shock model đủ mạnh. |

# **12\. Data hiện tại hỗ trợ architecture như thế nào?**

| Data/feature | Vai trò |
| :---- | :---- |
| 2002–2021 trade history | Time dimension và historical export performance. |
| 1.1m HS6 records; 87 importers hiện có | Market × product × time relationships. |
| Spell / duration / event / right-censoring | Survival analysis. |
| Tariff | Trade-barrier/risk/constraint layer; cần xử lý limitation của preferential codes. |
| NTM | Non-tariff barrier layer. |
| GDP/macro | Covariates/predictors trong survival/performance models. |
| Partner share / product share / HHI | Diversification/concentration. |
| Growth | Performance dimension. |

Data inventory xác nhận nhóm mạnh ở market × product × time, trade barriers, dynamic relationships và diversification. Inventory ghi 1,101,870 HS6 records, 87 importer có dữ liệu và 2002–2021. fileciteturn5file7L546-L567

Cần lưu ý: mới 87/147 importer hoàn chỉnh; world denominator chưa hoàn thiện; tariff preferential group codes chưa resolve hoàn toàn. Vì vậy không được mặc định claim “optimal strategy for all Vietnam export markets” nếu coverage chưa đủ. fileciteturn6file8L619-L630

# **13\. Những thứ bắt buộc phải chốt trước khi coding**

| Câu hỏi | Phải chốt |
| :---- | :---- |
| Decision-maker | Government/policymaker hay representative export planner? Không thay đổi tùy đoạn. |
| Unit of analysis | Vietnam × importer × HS6 × year relationship. |
| Spell definition | Threshold, start, end, event và right-censoring. |
| Export performance | Current value, expected value, growth hay metric khác. |
| Survival horizon | 1/3/5 năm hoặc horizon khác, có lý do. |
| Network definition | Country-product edges/nodes và aggregation. |
| Network survival/reliability | Mathematical \+ economic definition cụ thể. |
| Actions | Maintain/expand/reduce/enter/exit và ý nghĩa đo lường. |
| Tariff | MFN/faced/preferential treatment nào được dùng; limitation nào. |
| Objective/constraints | Mỗi thành phần phải có economic meaning. |
| Algorithm | Chọn sau formulation, không chọn GA/ACO trước. |
| Validation | Benchmark, backtest, sensitivity/stress test phải được thiết kế trước claim. |

# **14\. Cách chọn level**

Nhóm không chọn level cao nhất vì nó nghe hay. Nhóm chọn level cao nhất mà có thể chứng minh đầy đủ bằng data \+ model \+ validation trong thời gian hiện có.

·        Nếu survival model \+ static optimization chắc → Level 1\.

·        Nếu thêm network survivability và diversification constraints chắc → Level 2\.

·        Nếu định nghĩa được state/action/transition và backtest dynamic policy → Level 3\.

·        Nếu định nghĩa được system-level reliability chặt → Level 4\.

·        Nếu chứng minh được common-shock dependence/correlated failure → Level 5\.

# **15\. Journal strategy – không để cuối cùng mới lo journal**

Ngay sau khi chốt research architecture, nhóm nên map từng level sang journal community; sau đó mới lọc journal cụ thể. Không tìm theo keyword chung kiểu 'optimization journal'.

| Level | Journal communities cần khảo sát |
| :---- | :---- |
| L1 | International Trade / Applied Economics \+ Survival/Econometric Methods \+ Optimization |
| L2 | International Trade \+ Trade Diversification/Resilience \+ Operations Research/Optimization |
| L3 | Supply Chain/Network Resilience \+ Operations Research/Optimization \+ International Trade |
| L4 | Reliability/Network Science \+ Operations Research \+ Trade/Supply Network Resilience |
| L5 | Reliability/Resilience \+ Stochastic/Robust Optimization \+ Network Science \+ International Trade |

Sau đó lọc theo: Scopus indexing → Q1/Q2 đúng subject category → scope → recent papers gần topic/method → article type → methodological expectations → empirical/mathematical fit → novelty và feasibility.

# **16\. Công việc nếu nhóm đồng ý**

7\.     Cả nhóm đọc và thống nhất định nghĩa export relationship: Vietnam × importer × HS6.

8\.     Chốt decision-maker và decision variables.

9\.     Chốt spell, duration, event và right-censoring.

10\.  Audit data inventory: coverage, missing importers, tariff limitations, NTM và variables thực sự dùng được.

11\.  Chốt Level 1 formulation làm nền.

12\.  Xây survival baseline và kiểm tra quality/variation của relationship survival.

13\.  Xây Level 0 benchmark.

14\.  Xây Level 1 survival-adjusted optimization.

15\.  Nếu Level 1 ổn, phát triển Level 2 survivability/diversification constraints.

16\.  Nếu Level 2 ổn và state/action/transition khả thi, phát triển Level 3 dynamic reconfiguration.

17\.  Sau khi target level rõ, map journal communities và lập shortlist Q1/Q2.

18\.  Chỉ sau đó refine literature gap, model, experiments và paper framing theo journal target.

19\.  Đánh giá feasibility của Level 4–5 như extension; không cam kết trước.

# **17\. Decision checklist – phải đồng ý trước khi bắt đầu**

·        Chúng ta cùng hiểu export relationship là Vietnam × importer × HS6.

·        Chúng ta phân biệt prediction/estimation với optimization/decision.

·        Survival analysis không phải contribution tự thân; contribution nằm ở cách survival information được dùng cho network decision.

·        Level 0 là baseline.

·        Level 3 là core target hiện tại nhưng không ép nhóm nếu data/model không đủ.

·        Không thêm thuật toán trước khi research question, decision variables, objective và constraints rõ.

·        Không gọi bài là transportation optimization.

·        Định vị theo export network/international trade/resilience/dynamic optimization tùy level thực tế.

·        Journal được map sớm nhưng không để journal kéo sai research question.

·        Mọi claim về novelty, Q1/Q2 và literature gap phải được kiểm chứng trước khi đưa vào manuscript.

# **18\. Kết luận đề xuất**

Architecture đề xuất là: export portfolio optimization → survival-aware portfolio → survival-constrained diversification → dynamic survival-aware reconfiguration → network reliability → correlated/common-shock resilience.

CORE TARGET đề xuất: SURVIVAL-AWARE DYNAMIC EXPORT NETWORK RECONFIGURATION. Level 1–2 là nền và fallback; Level 4–5 là extension có điều kiện. Mục tiêu của strategy này là vừa giữ ambition nghiên cứu cao, vừa bảo đảm nhóm luôn có một phiên bản hoàn chỉnh và có thể submit nếu không đủ điều kiện đi tiếp.

**Export value → Survival → Diversification/Resilience → Dynamic Reconfiguration → Network Reliability → Common-Shock Resilience**

Mỗi mũi tên phải tương ứng với một câu hỏi nghiên cứu mới, một thành phần mô hình mới và một contribution có thể kiểm chứng; không được chỉ là thêm thuật toán hoặc thêm constraint cho phức tạp.

