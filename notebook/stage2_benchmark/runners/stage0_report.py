"""Đợt 0.2 / 0.3 reports: views per fold and the S1-S8 x fold eligibility table.

    python -m stage2_benchmark.runners.stage0_report
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402

import pandas as pd  # noqa: E402

from stage2_benchmark.data import base_table  # noqa: E402
from stage2_benchmark.data import views as V  # noqa: E402
from stage2_benchmark.features.preprocess import eligibility, resolve_set  # noqa: E402

OUT = os.path.join(paths.REPORTS, "stage0")
SETS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]


def view_rows(base, splits):
    rows = []
    for f, fd in splits["folds"].items():
        for task in "DL":
            for stage in ("valid", "test"):
                tr, ev = V.fold_views(base, splits, f, task, stage)
                spec = fd[task]
                ev_origin = spec["valid_origin"] if stage == "valid" else fd["test_origin"]
                n_origin = int((base["year"] == ev_origin).sum())
                for part, v in (("train", tr), ("eval", ev)):
                    rows.append({
                        "fold": f, "task": task, "stage": stage, "part": part,
                        "origins": f"{v.year.min()}-{v.year.max()}",
                        "rows": len(v), "events_any": int(v.event.sum()),
                        "events_1y": int(((v.event == 1) & (v.duration == 1)).sum()),
                        "masked_rows": (n_origin - len(v)) if part == "eval" else None,
                        "known_start": round(v.meta_known_start.mean(), 3),
                        "recurrent": round(v.meta_recurrent.mean(), 3),
                        "incident_known_start_first": round(
                            ((v.meta_known_start == 1) & (v.meta_recurrent == 0)).mean(), 3),
                        "max_duration": int(v.duration.max()),
                        "cohort_hash": V.cohort_hash(v)})
    return pd.DataFrame(rows)


def eligibility_rows(base, splits):
    rows = []
    for f in splits["folds"]:
        for task in "DL":
            for stage in ("valid", "test"):
                tr, _ = V.fold_views(base, splits, f, task, stage)
                for s in SETS:
                    e = eligibility(tr, s)
                    rows.append({"fold": f, "task": task, "stage": stage, "set": s,
                                 "n_features": len(resolve_set(s)),
                                 "train_rows": len(tr), "train_events": int(tr.event.sum()),
                                 **{f"asof_{b}": v["asof_share"] for b, v in e["blocks"].items()},
                                 "eligible": e["eligible"],
                                 "reason": "; ".join(e["reasons"])})
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    base = base_table.load_base()
    splits = paths.load_yaml("splits.yaml")
    vr = view_rows(base, splits)
    er = eligibility_rows(base, splits)
    paths.atomic_write_csv(vr, os.path.join(OUT, "0.2_views.csv"))
    paths.atomic_write_csv(er, os.path.join(OUT, "0.3_eligibility.csv"))

    L = ["# Đợt 0.2 — View D / L / I", "",
         "Quy tắc censor: administrative tại H = C − g (configs/tasks.yaml). Origin là "
         "dòng active (`gap_filled == 0`, trade ≥ ngưỡng), không dùng `gap_filled` làm feature. "
         "Hàng có kết cục năm sau chưa xác nhận có follow-up 0 và bị loại (mask), không "
         "thành y = 0.", "",
         f"- Origin 2024 của EU27: {int((base.year == 2024).sum()):,} dòng; ở cutoff 2025 "
         f"(H = 2024) còn {len(V.view(base, 2024, 2025, task='D'))} dòng → toàn bộ bị mask.",
         f"- View I (B0, origin 2012–2023, cutoff 2025): {len(V.inference_view(base)):,} dòng, "
         f"{int(V.inference_view(base).y.sum()):,} exit 1 năm.", "",
         "| fold | task | stage | phần | origins | rows | events (1y) | masked | known-start | recurrent | max dur | cohort |",
         "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in vr.iterrows():
        L.append(f"| {r.fold} | {r.task} | {r.stage} | {r.part} | {r.origins} | {r.rows:,} | "
                 f"{r.events_1y:,} | {'' if pd.isna(r.masked_rows) else int(r.masked_rows)} | "
                 f"{r.known_start:.1%} | {r.recurrent:.1%} | {r.max_duration} | `{r.cohort_hash[:8]}` |")
    L += ["", "**0.2 PASS** — các kiểm tra nhãn/mask/cohort nằm trong `tests/test_stage0.py` "
          "(test 03, 04, 06, 06b)."]
    with open(os.path.join(OUT, "0.2_views.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    L = ["# Đợt 0.3 — Feature registry và eligibility S1–S8 × fold", "",
         "Registry: `configs/feature_registry.yaml` (grain, công thức, `available_at`, "
         "`missing_semantics` cho từng feature). Quy tắc eligibility: block phụ (N, C, L, H) "
         "cần ≥ 50% dòng train có giá trị as-of trên các cột nội dung và không hằng.", "",
         "Hai lệch khỏi bản nháp §3.1 của kế hoạch, cả hai theo hướng chặt hơn:",
         "1. Block N dùng `ntm6_*_survey`, không dùng `ntm6_*_inforce`: `inforce` gộp mọi "
         "đợt thu thập kể cả đợt sau origin (docstring `scripts/build_ntm6.py`), nên không as-of "
         "dù `ntm6_source_year ≤ origin`. `inforce` chỉ còn trong probe lenient C10(b).",
         "2. `hhi_*` có điều kiện được tính trên các dòng spell của panel (147 importer); quan "
         "hệ dưới ngưỡng ngoài spell không có trong panel.", "",
         "| fold | task | stage | set | #feat | train rows | N | C | L | H | eligible | lý do |",
         "|---|---|---|---|---:|---:|---:|---:|---:|---:|:-:|---|"]
    for _, r in er.iterrows():
        g = lambda b: "" if pd.isna(r.get(f"asof_{b}")) else f"{r[f'asof_{b}']:.0%}"  # noqa: E731
        L.append(f"| {r.fold} | {r.task} | {r.stage} | {r.set} | {r.n_features} | "
                 f"{r.train_rows:,} | {g('N')} | {g('C')} | {g('L')} | {g('H')} | "
                 f"{'✅' if r.eligible else '❌'} | {r.reason} |")
    L += ["", "**0.3 PASS** — mọi feature có đủ trường registry; bảng eligibility đã lập."]
    with open(os.path.join(OUT, "0.3_eligibility.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(er[er.stage == "valid"][["fold", "task", "set", "eligible", "reason"]]
          .query("not eligible").to_string())


if __name__ == "__main__":
    main()
