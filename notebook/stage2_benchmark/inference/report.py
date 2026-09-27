"""Đợt 4 report: reports/batch4/REPORT.md from the spec checkpoints.

    python -m stage2_benchmark.inference.report
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

D = os.path.join(paths.REPORTS, "batch4")
SHOW = ["log_value_lag", "log_initial_value", "vn_market_share_lag1", "volatility_3y_lag1",
        "log_gdp_d_lag1", "log_gdpcap_d_lag1", "log_total_import_cp_lag1",
        "log_n_products_to_c_lag1", "log_n_markets_eu27_for_p_lag1", "log_rca_lag",
        "tariff_applied_lag", "pref_margin_lag"]


def load(s):
    p = os.path.join(D, "specs", f"{s}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def coef_map(r):
    return {c["term"]: c for c in r["coefs"]}


def star(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


def main():
    L = ["# Đợt 4 — Nhánh suy luận I (B0 EU27, person-period)", "",
         "Mẫu: dòng active EU27, origin 2012–2023, kết cục 1 năm đã xác nhận với dữ liệu tới 2025. "
         "Mẫu chính = spell known-start. Covariate **chỉ lag** (explanatory mode), chuẩn hoá trên mẫu; "
         "missing → median + cờ. Hệ số cloglog = log hazard ratio **trên 1 SD**. SE chính: cluster hai chiều "
         "importer × HS2 (CGM). Wild score bootstrap (Webb, 999) một chiều theo importer (27) và theo HS2 (~96) "
         "chỉ là kiểm tra bổ sung. **Mọi hệ số là association**, trừ khi có lập luận nhận diện riêng.", ""]
    rs = {s: load(s) for s in ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I7p", "I8", "I9",
                               "I10", "I11", "I12", "I13", "I14", "I15", "I16"]}
    # ---- M0-M3 ladder
    L += ["## I1–I5: thang M0–M3 (pooled cloglog, dummy tuổi 1..10+)", "",
          "| | I1 D | I2 S1 | I3 S2 | I4 S3 | I5 S4 | I15 S4 (mọi spell) |", "|---|---:|---:|---:|---:|---:|---:|"]
    ids = ["I1", "I2", "I3", "I4", "I5", "I15"]
    L.append("| n / events | " + " | ".join(f"{rs[i]['n']:,} / {rs[i]['events']:,}" for i in ids) + " |")
    L.append("| log-lik | " + " | ".join(f"{rs[i]['loglik']:.1f}" for i in ids) + " |")
    L.append("| #params | " + " | ".join(str(rs[i]["k"]) for i in ids) + " |")
    for t in SHOW:
        cells = []
        for i in ids:
            c = coef_map(rs[i]).get(t)
            cells.append("" if c is None else f"{c['hazard_ratio']:.3f}{star(c['p_2way'])}")
        L.append(f"| HR `{t}` | " + " | ".join(cells) + " |")
    L += ["", "HR trên 1 SD; `*` p < 0,1, `**` < 0,05, `***` < 0,01 (cluster hai chiều).", ""]

    # ---- heterogeneity
    L += ["## I6–I9, I16, I7p: dị biệt ẩn theo relation (C04)", "",
          "| spec | mẫu | nhóm | tham số RE | log-lik (pooled) | LR vs pooled | ghi chú |",
          "|---|---|---:|---|---|---:|---|"]
    for i in ["I6", "I7", "I7p", "I16"]:
        r = rs[i]
        L.append(f"| {i} {r['spec']} | {r['sample']} | {r['groups']:,} | θ = {r['theta']:.2e} | "
                 f"{r['loglik']:.1f} ({r['loglik_pooled']:.1f}) | {r['LR_theta0']:.3f} (p = {r['p_LR_theta0_boundary']:.2f}) | "
                 f"max {r.get('max_events_per_group', '—')} spell chết/relation |")
    for i in ["I8", "I9"]:
        r = rs[i]
        L.append(f"| {i} {r['spec']} | {r['sample']} | {r['groups']:,} | σ_u = {r['sigma_u']:.2e}, ρ = {r['rho']:.1e} | "
                 f"{r['loglik']:.1f} ({r['loglik_pooled']:.1f}) | {2 * (r['loglik'] - r['loglik_pooled']):.3f} | |")
    L += ["", "**Đọc:** phương sai frailty/intercept ngẫu nhiên theo relation hội tụ về biên 0 trong mọi đặc tả, "
          "kể cả khi baseline là tham số (I7p) thay vì dummy tự do. Nên hệ số pooled và hệ số frailty trùng nhau. "
          "Sau khi kiểm soát sức mạnh quan hệ (giá trị lag, giá trị khởi đầu, biến động) thì **không còn dị biệt ẩn đáng kể ở cấp "
          "importer × family**. Kết luận này không có nghĩa quan hệ đồng nhất: phần dị biệt đã được covariate quan sát "
          "hấp thụ. Phương pháp của I6/I7 là likelihood frailty đúng (tích phân dạng đóng); đã kiểm chứng trên dữ liệu mô phỏng "
          "(θ = 0,8 → ước lượng 0,83).", ""]

    # ---- PH in age, recurrence
    r = rs["I10"]
    L += ["## I10: effect có đổi theo tuổi spell không? (C03 phía suy luận)", "",
          f"Wald chung cho 5 tương tác X × log(tuổi): χ² = {r['wald_all_interactions_2way']['chi2']:.1f}, "
          f"df = {r['wald_all_interactions_2way']['df']}, p = {r['wald_all_interactions_2way']['p']:.1e}.", "",
          "| tương tác | hệ số | SE 2 chiều | p |", "|---|---:|---:|---:|"]
    for c in r["coefs"]:
        if c["term"].endswith("_x_logage"):
            L.append(f"| {c['term']} | {c['coef']:+.3f} | {c['se_2way']:.3f} | {c['p_2way']:.3f} |")
    L += ["", "Giả định PH theo tuổi **bị bác bỏ** cho hai biến R: tác động bảo vệ của giá trị lag mạnh lên theo tuổi, "
          "còn của giá trị khởi đầu yếu đi theo tuổi (hệ số dương). Biến thuế quan không có tương tác đáng kể.", ""]
    r = rs["I11"]
    L += ["## I11: spell tái gia nhập và spell không rõ điểm bắt đầu (C07)", "",
          "| hạng tử | hệ số | SE 2 chiều | p |", "|---|---:|---:|---:|"]
    for c in r["coefs"]:
        if c["term"].startswith(("recurrent", "unknown_start")):
            L.append(f"| {c['term']} | {c['coef']:+.3f} | {c['se_2way']:.3f} | {c['p_2way']:.3f} |")
    L += ["", f"Wald tương tác recurrent: p = {r['wald_recurrent_x_2way']['p']:.2f}; "
          f"unknown-start: p = {r['wald_unknown_start_x_2way']['p']:.1e}.", ""]

    # ---- EVFTA
    r = rs["I12"]
    L += ["## I12–I14: EVFTA (C08)", "",
          f"Cường độ = mức cắt thuế EVFTA tích luỹ tới 2023 theo lộ trình Annex 2-A của family "
          f"(chuẩn hoá, 1 SD = {r['intensity_sd_pp']:.2f} điểm %). Event time theo **năm kết cục** (t + 1 − 2020), "
          "tham chiếu = năm kết cục 2019. FE importer, HS2, năm kết cục; dummy tuổi + lag R.", "",
          "| k | hệ số | SE 2 chiều | p 2 chiều | p wild (importer) | p wild (HS2) |", "|---|---:|---:|---:|---:|---:|"]
    for c in r["coefs"]:
        if c["term"].startswith("intensity_x_k"):
            L.append(f"| {c['term'][13:]} | {c['coef']:+.3f} | {c['se_2way']:.3f} | {c['p_2way']:.3f} | "
                     f"{c['boot_p']:.3f} | {c['boot_p_hs2']:.3f} |")
    L += ["", f"Pre-trend (k ≤ −2) Wald: p = {r['pretrend_wald_2way']['p']:.2f}. "
          f"Post (k = 1..4) Wald: p = {r['post_wald_2way']['p']:.2f}.", ""]
    for i in ("I13", "I14"):
        r = rs[i]
        L += [f"**{i}** — {r['spec']} ({r['sample']}):", "", "| hạng tử | hệ số | p 2 chiều | p wild HS2 |", "|---|---:|---:|---:|"]
        for c in r["coefs"]:
            if c["term"].startswith(("intensity", "entrant")) and "boot_p_hs2" in c:
                L.append(f"| {c['term']} | {c['coef']:+.3f} | {c['p_2way']:.3f} | {c['boot_p_hs2']:.3f} |")
        L.append("")
    L += ["**Đọc (thận trọng):** không có pre-trend và placebo 2017 bằng 0, nên thiết kế qua được hai kiểm tra "
          "cơ bản. Family có mức cắt thuế lớn hơn có hazard exit thấp hơn từ năm kết cục 2022 (k = +2..+4, "
          "khoảng −0,12 đến −0,17 log-HR trên 1 SD). Tuy nhiên kiểm định chung sau EVFTA với SE hai chiều "
          "không có ý nghĩa (p ≈ 0,27), và từng hệ số chỉ ở mức biên (p ≈ 0,05–0,15). Wild bootstrap một chiều cho p nhỏ hơn "
          "nhưng bỏ qua chiều cluster còn lại. Lộ trình cắt thuế cố định từ trước, nhưng các ngành cắt nhiều cũng có thể "
          "trùng với cú sốc hậu COVID riêng của ngành. Kết luận: **có dấu hiệu gợi ý, chưa đủ để khẳng định nhân quả**. "
          "Category A chiếm 93% kim ngạch, nên biến thiên nhận diện dựa trên phần đuôi (TU_DIEN §7b).", ""]
    with open(os.path.join(D, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L[:30]))


if __name__ == "__main__":
    main()
