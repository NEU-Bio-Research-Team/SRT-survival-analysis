# -*- coding: utf-8 -*-
"""Short deck: what the final df contains, and which raw groups built it."""
C = {}

C["vi"] = dict(
tag="stage1_panel",
title="Final dataframe",
sub="data/final/stage1_panel.parquet",
kicker="Dữ liệu gồm gì và lấy từ đâu",
group=["Nhóm nghiên cứu", "Người trình bày: [điền tên]"],
group_note="Số liệu đọc trực tiếp trên file · 04/09/2026",

# 1 — một dòng là gì
s1_t="Một dòng là gì",
s1_q="Một quan hệ xuất khẩu, trong một năm.",
s1_key=[("importer", "nước nhập khẩu"), ("product_family", "nhóm sản phẩm"), ("year", "năm")],
s1_kpi=[("949.537", "dòng"), ("205", "cột"), ("147", "nước nhập"),
        ("4.637", "nhóm sản phẩm"), ("2002–2025", "khoảng năm")],
s1_n="Exporter luôn là Việt Nam.",

# 2 — trong df có gì
s2_t="Trong df có gì",
s2_n="205 cột · nhóm theo khối, không phải 205 biến đầu vào của mô hình.",

# 3 — dựng từ đâu
s3_t="Dựng từ 6 nhóm dữ liệu thô",
s3_n="Mọi nguồn nối vào cùng một khóa (importer, product_family, year).",

# 4 — nguồn nào cho cột nào
s4_t="Nguồn nào cho cột nào",
s4_tbl=[["Nhóm thô", "Cho ra", "Số cột"],
  ["UN Comtrade", "kim ngạch, thị phần, RCA, HHI, tăng trưởng", "12"],
  ["WITS TRAINS + EVFTA Annex + biểu thuế EU", "thuế MFN, thuế thực chịu, lộ trình EVFTA", "14"],
  ["WITS / UNCTAD NTM", "rào cản phi thuế theo HS6 và theo ngành", "29"],
  ["World Bank WDI", "GDP, dân số, lạm phát, tỷ giá", "16"],
  ["World Bank LPI + Yale EPI", "logistics, môi trường", "12"],
  ["World Bank Pink Sheet + GEPU", "giá hàng hóa, bất định toàn cầu", "18"],
  ["CEPII Gravity", "khoảng cách, ngôn ngữ, thể chế", "21"],
  ["DESTA / TTBD / Atlas", "hiệp định, phòng vệ, độ phức tạp", "22"],
  ["EU 2023/956 + HTS Ch.99 Mỹ", "CBAM, thuế Mỹ 2025", "14"],
  ["Tự dựng trong dự án", "khóa, nhãn sống/chết, biến lag, biến cấu trúc", "47"]],

# 5 — nhãn
s5_t="Năm cột nói quan hệ sống hay chết",
s5_tbl=[["Cột", "Nghĩa"],
  ["spell_id", "một lần bán liên tục"],
  ["t_start, t_stop", "quan hệ đã sống được bao nhiêu năm"],
  ["event", "1 = năm đó quan hệ chấm dứt · 0 = chưa"],
  ["right_censored", "dữ liệu dừng khi quan hệ vẫn còn sống"],
  ["gap_filled", "năm dưới ngưỡng, giữ để nối spell"]],
s5_c=("Ngưỡng", "Nước nhập khai từ 10.000 USD/năm trở lên. Đứt đúng 1 năm thì nối lại."),

# 6 — nhãn mục tiêu
s6_t="Nhãn mục tiêu: event",
s6_l="Mỗi dòng một nhãn nhị phân. Chỉ năm cuối của một spell mới có thể bằng 1.",
s6_kpi=[("194.461", "spell"), ("131.675", "chấm dứt · 67,7%"),
        ("62.786", "còn sống khi dữ liệu dừng · 32,3%"), ("13.178", "left-truncated")],
s6_c=("right_censored không phải “sống mãi”", "Chỉ là chưa thấy chấm dứt trong khoảng dữ liệu."),
s6_n="S(t) là output của mô hình, chưa có trong file.",

thanks="Cảm ơn thầy",
thanks_sub="data/final/stage1_panel.parquet · 04/09/2026",
)

C["en"] = dict(
tag="stage1_panel",
title="Final dataframe",
sub="data/final/stage1_panel.parquet",
kicker="What is in it and where it came from",
group=["Research group", "Presenter: [name]"],
group_note="Numbers read directly off the file · 04/09/2026",

s1_t="What one row is",
s1_q="One export relationship, in one year.",
s1_key=[("importer", "importing country"), ("product_family", "product group"), ("year", "year")],
s1_kpi=[("949,537", "rows"), ("205", "columns"), ("147", "importers"),
        ("4,637", "product groups"), ("2002–2025", "year range")],
s1_n="The exporter is always Vietnam.",

s2_t="What is in the df",
s2_n="205 columns · grouped into blocks, not 205 model inputs.",

s3_t="Built from 6 raw data groups",
s3_n="Every source joins on the same key (importer, product_family, year).",

s4_t="Which source gives which columns",
s4_tbl=[["Raw group", "Gives", "Columns"],
  ["UN Comtrade", "value, market share, RCA, HHI, growth", "12"],
  ["WITS TRAINS + EVFTA Annex + EU tariff", "MFN, applied tariff, EVFTA schedule", "14"],
  ["WITS / UNCTAD NTM", "non-tariff measures, HS6 and sector", "29"],
  ["World Bank WDI", "GDP, population, inflation, exchange rate", "16"],
  ["World Bank LPI + Yale EPI", "logistics, environment", "12"],
  ["World Bank Pink Sheet + GEPU", "commodity prices, global uncertainty", "18"],
  ["CEPII Gravity", "distance, language, institutions", "21"],
  ["DESTA / TTBD / Atlas", "agreements, remedies, complexity", "22"],
  ["EU 2023/956 + US HTS Ch.99", "CBAM, US 2025 tariffs", "14"],
  ["Built in the project", "keys, alive/dead label, lags, structure", "47"]],

s5_t="Five columns say whether a relationship lives or dies",
s5_tbl=[["Column", "Meaning"],
  ["spell_id", "one continuous run"],
  ["t_start, t_stop", "how many years the relationship has lived"],
  ["event", "1 = it ended that year · 0 = not yet"],
  ["right_censored", "the data stops while it is still alive"],
  ["gap_filled", "a year under the threshold, kept to bridge the spell"]],
s5_c=("Threshold", "The importer reports USD 10,000 a year or more. A one-year break gets bridged."),

s6_t="Target label: event",
s6_l="One binary label per row. Only the last year of a spell can be 1.",
s6_kpi=[("194,461", "spells"), ("131,675", "ended · 67.7%"),
        ("62,786", "alive when the data stops · 32.3%"), ("13,178", "left-truncated")],
s6_c=("right_censored is not “alive forever”", "It only means no ending was seen inside the data window."),
s6_n="S(t) is a model output, not in the file.",

thanks="Thank you",
thanks_sub="data/final/stage1_panel.parquet · 04/09/2026",
)
