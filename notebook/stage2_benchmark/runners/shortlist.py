"""Freeze the shortlist by the rules of plan §5, applied mechanically.

    python -m stage2_benchmark.runners.shortlist

Reads only batch1 VALIDATION results (F2). Writes configs/shortlist.yaml and
reports/shortlist/SHORTLIST.md; both are committed on their own before any
test origin is opened.

Rules (plan §5, fixed before batch1 was read):
  D  : D01, D04, D05 + the best Brier@S4 of {D02, D03, D06}            -> 4
  L  : L02, L07, L08 + the two best IBS@S4 of
       {L01, L03, L04, L05, L06, L09, L10}                              -> 5
  sets: {S1, S4, S*}; S* = best mean validation rank over the task's
       representatives (D: D01, D05; L: L02, L05, L07) among the sets of
       {S2, S3, S5, S6, S7, S8} that are eligible in the task's F1, F2 and
       F3 training blocks (Đợt 2 runs all three folds)
  L* : the nonlinear L model of the shortlist with the best IBS@S4; if its
       paired CI against L05 contains 0 (and L05 is shortlisted), L05
A candidate still flagged "not converged" after the automatic +15 trials is
reported; the ranking is not adjusted by hand.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from stage2_benchmark.runners.aggregate import NAMES, cell_key, load_cells, not_converged, paired  # noqa: E402

REPS = {"D": ["D01", "D05"], "L": ["L02", "L05", "L07"]}
CANDIDATE_SETS = ["S2", "S3", "S5", "S6", "S7", "S8"]
NONLINEAR_L = {"L05", "L06", "L07", "L08", "L09", "L10"}


def score(df, model, fset="S4"):
    m = df[(df.model == model) & (df.fset == fset) & (df.state == "done") & (df.stage == "valid")]
    if not len(m):
        return float("nan")
    return float(m.iloc[0]["m_brier_1y" if model[0] == "D" else "m_ibs_1_3"])


def main():
    df = load_cells("batch1")
    df["not_converged"] = df.apply(lambda r: r["state"] == "done" and not_converged(r), axis=1)
    elig = pd.read_csv(os.path.join(paths.REPORTS, "stage0", "0.3_eligibility.csv"))
    L = ["# Shortlist (quy tắc §5, áp dụng máy móc)", "",
         f"Nguồn: batch1, F2 validation. Code `{paths.code_commit()}`.", ""]
    out = {"source": "batch1 F2 validation", "code_commit": paths.code_commit()}

    # ---- models
    d_opt = {m: score(df, m) for m in ("D02", "D03", "D06")}
    d_pick = min(d_opt, key=d_opt.get)
    l_opt = {m: score(df, m) for m in ("L01", "L03", "L04", "L05", "L06", "L09", "L10")}
    l_pick = sorted(l_opt, key=l_opt.get)[:2]
    shortD = ["D01", "D04", "D05", d_pick]
    shortL = ["L02", "L07", "L08"] + l_pick
    L += ["## Model", "",
          f"- D: cố định D01, D04, D05; tốt nhất trong {{D02, D03, D06}} theo Brier @S4: "
          + ", ".join(f"{m} {v:.5f}" for m, v in sorted(d_opt.items(), key=lambda x: x[1]))
          + f" → **{d_pick}**",
          f"- L: cố định L02, L07, L08; hai tốt nhất trong {{L01, L03, L04, L05, L06, L09, L10}} theo IBS @S4: "
          + ", ".join(f"{m} {v:.5f}" for m, v in sorted(l_opt.items(), key=lambda x: x[1]))
          + f" → **{', '.join(l_pick)}**", ""]
    flagged = df[df.not_converged & df.model.isin(shortD + shortL + list(d_opt) + list(l_opt))
                 & (df.fset == "S4")]["cell"].tolist()
    L += [f"- Cờ 'chưa hội tụ' còn lại sau +15 trial: {flagged or 'không có'}", ""]

    # ---- feature sets
    sets = {}
    for task, reps in REPS.items():
        ok = elig[(elig.task == task)]
        eligible = [s for s in CANDIDATE_SETS if ok[ok.set == s]["eligible"].all()]
        ranks = {}
        for m in reps:
            vals = {s: score(df, m, s) for s in eligible}
            r = pd.Series(vals).rank()
            for s in eligible:
                ranks.setdefault(s, []).append(r[s])
        mean_rank = {s: sum(v) / len(v) for s, v in ranks.items()}
        star = min(mean_rank, key=lambda s: (mean_rank[s], CANDIDATE_SETS.index(s)))
        sets[task] = ["S1", "S4", star]
        L += [f"## Gói feature — task {task}", "",
              f"Gói eligible ở cả F1–F3: {eligible}. Hạng trung bình trên {reps}: "
              + ", ".join(f"{s} {v:.2f}" for s, v in sorted(mean_rank.items(), key=lambda x: x[1]))
              + f" → **S★ = {star}**", ""]

    # ---- L*
    nl = [m for m in shortL if m in NONLINEAR_L]
    best = min(nl, key=lambda m: score(df, m))
    lstar, why = best, "IBS @S4 tốt nhất trong các model phi tuyến của shortlist L"
    if best != "L05" and "L05" in shortL:
        r = paired(df.set_index("cell"), cell_key(df, best, "S4"), cell_key(df, "L05", "S4"))
        if r["lo"] <= 0 <= r["hi"]:
            lstar = "L05"
            why = (f"{best} tốt nhất nhưng CI paired so với L05 chứa 0 "
                   f"({r['diff']:+.5f} [{r['lo']:+.5f}, {r['hi']:+.5f}]) → L05")
        else:
            why += f"; CI so với L05: {r['diff']:+.5f} [{r['lo']:+.5f}, {r['hi']:+.5f}]"
    L += ["## L★ (đại diện phi tuyến cho Đợt 3)", "",
          f"Ứng viên phi tuyến: " + ", ".join(f"{m} {score(df, m):.5f}" for m in nl),
          f"→ **L★ = {lstar}** ({why})", ""]

    out.update(D_models=shortD, L_models=shortL, D_sets=sets["D"], L_sets=sets["L"],
               L_star=lstar, R4=["D01", "D05", "L02", lstar],
               names={m: NAMES[m] for m in shortD + shortL}, not_converged=flagged)
    with open(os.path.join(paths.CONFIGS, "shortlist.yaml"), "w", encoding="utf-8") as f:
        f.write("# Frozen by runners/shortlist.py from batch1 validation only. Do not edit.\n")
        yaml.safe_dump(out, f, sort_keys=False, allow_unicode=True)
    L += ["## Kết quả", "",
          f"- D: {shortD} × {sets['D']}",
          f"- L: {shortL} × {sets['L']}",
          f"- R4 cho Đợt 3: {out['R4']}", "",
          "Đã ghi `configs/shortlist.yaml`. Commit riêng trước khi mở test origin."]
    od = os.path.join(paths.REPORTS, "shortlist")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "SHORTLIST.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
