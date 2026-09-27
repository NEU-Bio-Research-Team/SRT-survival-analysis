"""Collect finished cells into tables, paired contrasts and figures.

    python -m stage2_benchmark.runners.aggregate --plan batch1

Everything is computed from the saved per-row predictions (pred.parquet), so no
model is refit. Paired differences resample relations (importer x family) with
B = 1000 (tasks.yaml); cells are only compared when their scored cohort hashes
agree.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from stage2_benchmark.evaluation import bootstrap as BS  # noqa: E402
from stage2_benchmark.evaluation import metrics as M  # noqa: E402

GRID = [1, 2, 3, 4, 5]
NAMES = {k: v["name"] for k, v in paths.load_yaml("models.yaml")["models"].items()}
B = paths.load_yaml("tasks.yaml")["conventions"]["bootstrap"]["B"]


def load_cells(batch: str) -> pd.DataFrame:
    rows = []
    for d in sorted(glob.glob(os.path.join(paths.RUNS, batch, "*"))):
        sp = os.path.join(d, "status.json")
        if not os.path.exists(sp):
            continue
        st = json.load(open(sp))
        spec = st.get("spec", {})
        r = {"cell": os.path.basename(d), "dir": d, "state": st.get("state"),
             "model": spec.get("model"), "task": spec.get("task"),
             "fset": spec.get("fset") or "REF", "fold": spec.get("fold"),
             "stage": spec.get("stage"), "group": spec.get("group"),
             "variant": (spec.get("variant") or {}).get("name"),
             "reason": "; ".join(st.get("reasons", [])) or st.get("error", "")}
        if st.get("state") == "done":
            res = json.load(open(os.path.join(d, "result.json")))
            man = json.load(open(os.path.join(d, "manifest.json")))
            r.update({f"m_{k}": v for k, v in res["scores"].items()
                      if isinstance(v, (int, float))})
            r.update(n_trials=res.get("n_trials"), n_failed=res.get("n_failed"),
                     best_trial=res.get("best_trial"), best_params=json.dumps(res.get("best_params", res.get("params"))),
                     runtime_s=man.get("runtime_seconds"), peak_rss_mb=man.get("peak_rss_mb"),
                     eval_hash=man.get("eval_cohort_hash"), train_rows=man.get("train_rows"),
                     n_cols=len(man.get("preprocessor", {}).get("names", [])),
                     budget_curve=json.dumps(res.get("budget_curve")),
                     info=json.dumps(res.get("info", {})))
        rows.append(r)
    return pd.DataFrame(rows)


def not_converged(row) -> bool:
    """Best trial in the last 25% of an optuna budget (plan §2)."""
    try:
        curve = json.loads(row["budget_curve"])
    except (TypeError, ValueError):
        return False
    if not curve or row["n_trials"] is None or row["n_trials"] < 10:
        return False
    return row["best_trial"] >= int(np.ceil(0.75 * row["n_trials"]))


# ------------------------------------------------------ per-row losses
def row_losses(cell_dir: str, task: str) -> pd.DataFrame:
    """Per-row loss (Brier 1y for D; IBS 1-3 contribution for L), averaged
    over seed columns when a test cell has several seeds."""
    pf = pd.read_parquet(os.path.join(cell_dir, "pred.parquet"))
    keys = pf[["spell_id", "year", "relation"]].copy()
    if task == "D":
        pcols = [c for c in pf.columns if c.startswith("p")]
        losses = [M.D_rows(pf[c].to_numpy(), pf["y"].to_numpy()) for c in pcols]
    else:
        tags = sorted({c[2:] for c in pf.columns if c.startswith("S1")})
        d, e = pf["duration"].to_numpy(), pf["event"].to_numpy()
        G = M.CensoringKM(d, e)
        losses = []
        for t in tags:
            S = pf[[f"S{u}{t}" for u in GRID]].to_numpy("float64")
            losses.append(M.ibs_rows(S, GRID, d, e, [1, 2, 3], G))
    keys["loss"] = np.mean(losses, axis=0)
    return keys


def paired(cells: pd.DataFrame, a: str, b: str, seed=20260927) -> dict:
    """mean(loss_a) - mean(loss_b) with a relation bootstrap CI."""
    ra, rb = cells.loc[a], cells.loc[b]
    if ra["eval_hash"] != rb["eval_hash"]:
        return {"diff": np.nan, "lo": np.nan, "hi": np.nan, "note": "cohorts differ"}
    la = row_losses(ra["dir"], ra["task"])
    lb = row_losses(rb["dir"], rb["task"])
    m = la.merge(lb, on=["spell_id", "year", "relation"], suffixes=("_a", "_b"))
    out = BS.paired_diff(m["loss_a"], m["loss_b"], m["relation"], B=B, seed=seed)
    out["note"] = ""
    return out


def fmt_ci(r):
    if r is None or not np.isfinite(r.get("diff", np.nan)):
        return "—"
    star = "*" if (r["hi"] < 0 or r["lo"] > 0) else ""
    return f"{r['diff']:+.5f} [{r['lo']:+.5f}, {r['hi']:+.5f}]{star}"


# ------------------------------------------------------------- tables
def leaderboard(df: pd.DataFrame, task: str, fset: str, ref_cell: str | None,
                stage="valid") -> pd.DataFrame:
    metric = "m_brier_1y" if task == "D" else "m_ibs_1_3"
    sub = df[(df.task == task) & (df.state == "done") & (df.stage == stage)
             & ((df.fset == fset) | (df.fset == "REF"))].copy()
    sub = sub.set_index("cell")
    rows = []
    for cell, r in sub.iterrows():
        rr = {"model": r["model"], "name": NAMES.get(r["model"]), "fset": r["fset"],
              "primary": r[metric]}
        if ref_cell and cell != ref_cell and ref_cell in sub.index:
            ref_score = sub.loc[ref_cell, metric]
            rr["skill"] = 1 - r[metric] / ref_score
            rr["delta_ref"] = paired(sub, cell, ref_cell)
        rows.append(rr)
    out = pd.DataFrame(rows).sort_values("primary")
    return out


def write_md(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ------------------------------------------------------- batch1 report
C02_C03_PAIRS = [
    # (a, b, question, reading)
    ("D04", "D01", "C02/C03", "spline + X×age vs linear cloglog"),
    ("D05", "D01", "C02", "boosted vs linear (D)"),
    ("D06", "D01", "C02", "MLP vs linear (D)"),
    ("D02", "D01", "link", "logit vs cloglog (expect ≈ 0)"),
    ("D03", "D01", "link", "probit vs cloglog (expect ≈ 0)"),
    ("L05", "L02", "C02", "RSF vs CoxNet"),
    ("L06", "L02", "C02", "GB-Cox vs CoxNet (nonlinear, PH kept)"),
    ("L07", "L02", "C02", "DeepSurv vs CoxNet (nonlinear, PH kept)"),
    ("L08", "L07", "C03", "CoxTime vs DeepSurv (drop PH, same net)"),
    ("L05", "L06", "C03", "RSF vs GB-Cox (drop PH, trees)"),
    ("L03", "L02", "C03", "Weibull AFT vs CoxNet"),
    ("L04", "L02", "C03", "log-normal AFT vs CoxNet"),
    ("L01", "L02", "reg.", "CoxPH vs CoxNet (shrinkage)"),
]
SETS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
REPS = ["D01", "D05", "L02", "L05", "L07"]


def cell_key(df, model, fset, stage="valid"):
    m = df[(df.model == model) & (df.fset == fset) & (df.stage == stage) & (df.state == "done")]
    return m["cell"].iloc[0] if len(m) else None


def report_batch1(plan="batch1"):
    df = load_cells(plan)
    out = os.path.join(paths.REPORTS, plan)
    os.makedirs(out, exist_ok=True)
    df["not_converged"] = df.apply(lambda r: r["state"] == "done" and not_converged(r), axis=1)
    paths.atomic_write_csv(df.drop(columns=["dir"]), os.path.join(out, "cells.csv"))
    cells = df.set_index("cell")
    L = [f"# Đợt 1 — Sàng lọc F2 (chỉ validation)", "",
         f"Code `{paths.code_commit()}`, panel `{paths.panel_hash()[:12]}`. "
         f"Validation: D origin 2017 (đọc tới 2019), L origin 2015 (đọc tới 2019). "
         f"Test origin 2020 **chưa mở**. CI: paired bootstrap theo relation, B = {B}; "
         "`*` = CI không chứa 0. Âm = tốt hơn.", ""]
    status = df["state"].value_counts().to_dict()
    L += [f"Trạng thái ô: {status}", ""]

    # --- Track A leaderboards
    for task, ref, metric in (("D", "D00", "m_brier_1y"), ("L", "L00", "m_ibs_1_3")):
        refc = cell_key(df, ref, "REF")
        lb = leaderboard(df, task, "S4", refc)
        paths.atomic_write_csv(lb.assign(delta_ref=lb.get("delta_ref", pd.Series(dtype=object)).astype(str)),
                               os.path.join(out, f"trackA_{task}.csv"))
        mname = "Brier 1y" if task == "D" else "IBS 1–3"
        L += [f"## Track A — task {task} @S4 ({mname})", "",
              f"| model | {mname} | skill vs ref | Δ vs ref [95% CI] | extra |", "|---|---:|---:|---|---|"]
        for _, r in lb.iterrows():
            c = cell_key(df, r["model"], r["fset"])
            extra = []
            if task == "D" and c:
                extra.append(f"AUC {cells.loc[c].get('m_roc_auc', np.nan):.3f}, "
                             f"slope {cells.loc[c].get('m_calib_slope', np.nan):.2f}")
            if task == "L" and c:
                extra.append(f"C_td {cells.loc[c].get('m_antolini_ctd', np.nan):.3f}")
            if c and cells.loc[c, "not_converged"]:
                extra.append("⚠ chưa hội tụ")
            sk = "" if pd.isna(r.get("skill")) else f"{r['skill']:.3f}"
            L.append(f"| {r['model']} {r['name']} | {r['primary']:.5f} | {sk} | "
                     f"{fmt_ci(r.get('delta_ref') if isinstance(r.get('delta_ref'), dict) else None)} | "
                     f"{'; '.join(extra)} |")
        L.append("")

    # --- paired contrasts C02/C03
    L += ["## Cặp đối chiếu @S4 (C02 phi tuyến, C03 PH)", "",
          "| a − b | câu hỏi | đọc | Δ [95% CI] |", "|---|---|---|---|"]
    crows = []
    for a, b, q, txt in C02_C03_PAIRS:
        ca, cb = cell_key(df, a, "S4"), cell_key(df, b, "S4")
        r = paired(cells, ca, cb) if ca and cb else None
        crows.append({"a": a, "b": b, "question": q, **(r or {})})
        L.append(f"| {a} − {b} | {q} | {txt} | {fmt_ci(r)} |")
    paths.atomic_write_csv(pd.DataFrame(crows), os.path.join(out, "contrasts_C02_C03.csv"))
    L.append("")

    # --- Track B heatmap + increments
    metric = {"D": "m_brier_1y", "L": "m_ibs_1_3"}
    hm = []
    for m in REPS:
        for s in SETS:
            sub = df[(df.model == m) & (df.fset == s)]
            if not len(sub):
                hm.append({"model": m, "set": s, "value": np.nan, "state": "not run"})
                continue
            r = sub.iloc[0]
            hm.append({"model": m, "set": s, "state": r["state"], "reason": r["reason"],
                       "value": r.get(metric[m[0]], np.nan) if r["state"] == "done" else np.nan})
        fb = df[(df.model == m) & df.group.fillna("").str.endswith("_fallback") & (df.state == "done")]
        for _, r in fb.iterrows():
            hm.append({"model": m, "set": r["fset"], "state": "done (fallback)",
                       "value": r.get(metric[m[0]])})
    hm = pd.DataFrame(hm)
    paths.atomic_write_csv(hm, os.path.join(out, "trackB_heatmap.csv"))
    L += ["## Track B — 5 đại diện × 8 gói", "",
          "| model | " + " | ".join(SETS) + " |", "|---|" + "---:|" * len(SETS)]
    for m in REPS:
        cellsx = []
        for s in SETS:
            r = hm[(hm.model == m) & (hm.set == s)]
            if not len(r) or r.iloc[0]["state"] == "not run":
                cellsx.append("·")
            elif r.iloc[0]["state"] == "ineligible":
                cellsx.append("ineligible")
            elif r.iloc[0]["state"] != "done":
                cellsx.append(r.iloc[0]["state"])
            else:
                cellsx.append(f"{r.iloc[0]['value']:.5f}")
        L.append(f"| {m} {NAMES[m]} | " + " | ".join(cellsx) + " |")
    fbrows = hm[hm.state == "done (fallback)"]
    if len(fbrows):
        L += ["", "Gói thay thế khi S8 ineligible (S8 bỏ block không đạt): " +
              ", ".join(f"{r.model} {r.set} = {r.value:.5f}" for r in fbrows.itertuples())]
    inel = hm[hm.state == "ineligible"]
    if len(inel):
        L += ["", "Lý do ineligible: " + "; ".join(sorted(set(f"{r.model}×{r.set}: {r.reason}"
                                                               for r in inel.itertuples())))]
    L += ["", "### Increment feature (C01), Δ = gói sau − gói trước", "",
          "| model | bước | Δ [95% CI] |", "|---|---|---|"]
    inc_rows = []
    steps = [("S2", "S1"), ("S3", "S2"), ("S4", "S3"), ("S5", "S4"), ("S6", "S4"),
             ("S7", "S4"), ("S8", "S4")]
    for m in REPS:
        for a, b in steps:
            ca, cb = cell_key(df, m, a), cell_key(df, m, b)
            if not (ca and cb):
                continue
            r = paired(cells, ca, cb)
            inc_rows.append({"model": m, "step": f"{b}→{a}", **r})
            L.append(f"| {m} {NAMES[m]} | {b} → {a} | {fmt_ci(r)} |")
        for s in fbrows[fbrows.model == m]["set"]:
            ca, cb = cell_key(df, m, s), cell_key(df, m, "S4")
            if ca and cb:
                r = paired(cells, ca, cb)
                inc_rows.append({"model": m, "step": f"S4→{s}", **r})
                L.append(f"| {m} {NAMES[m]} | S4 → {s} | {fmt_ci(r)} |")
    paths.atomic_write_csv(pd.DataFrame(inc_rows), os.path.join(out, "increments_C01.csv"))

    # --- thin sweep
    thin = df[df.group.fillna("").str.startswith("b_thin") & (df.state == "done")]
    if len(thin):
        L += ["", "## Đợt 1b — thin sweep (hẹp – neo – rộng)", "",
              "| model | S1 | S4 | rộng (S8 hoặc thay thế) |", "|---|---:|---:|---:|"]
        for m in sorted(thin.model.unique()):
            v = lambda s: df[(df.model == m) & (df.fset == s) & (df.state == "done")]  # noqa: E731
            s1, s4 = v("S1"), v("S4")
            wide = df[(df.model == m) & df.fset.str.startswith("S8") & (df.state == "done")]
            g = lambda x: f"{x.iloc[0][metric[m[0]]]:.5f}" if len(x) else "—"  # noqa: E731
            L.append(f"| {m} {NAMES[m]} | {g(s1)} | {g(s4)} | "
                     f"{(g(wide) + ' (' + wide.iloc[0]['fset'] + ')') if len(wide) else '—'} |")

    # --- runtime / convergence
    done = df[df.state == "done"].sort_values(["task", "model", "fset"])
    L += ["", "## Runtime, RAM, hội tụ", "",
          "| ô | trials (lỗi) | best trial | runtime s | peak RSS MB | cờ |", "|---|---:|---:|---:|---:|---|"]
    for _, r in done.iterrows():
        L.append(f"| {r['cell']} | {r['n_trials']} ({r['n_failed']}) | {r['best_trial']} | "
                 f"{r['runtime_s']:.0f} | {r['peak_rss_mb']:.0f} | "
                 f"{'⚠ chưa hội tụ' if r['not_converged'] else ''} |")
    write_md(os.path.join(out, "REPORT.md"), L)
    plot_heatmap(hm, os.path.join(out, "trackB_heatmap.png"))
    plot_budget(df, os.path.join(out, "best_vs_budget.png"))
    return df


def plot_heatmap(hm, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2), gridspec_kw={"width_ratios": [2, 3]})
    for ax, task in zip(axes, "DL"):
        ms = [m for m in REPS if m[0] == task]
        M_ = np.full((len(ms), len(SETS)), np.nan)
        for i, m in enumerate(ms):
            for j, s in enumerate(SETS):
                r = hm[(hm.model == m) & (hm.set == s) & (hm.state == "done")]
                if len(r):
                    M_[i, j] = r.iloc[0]["value"]
        im = ax.imshow(M_, cmap="viridis_r", aspect="auto")
        ax.set_xticks(range(len(SETS)), SETS)
        ax.set_yticks(range(len(ms)), [f"{m} {NAMES[m]}" for m in ms])
        for i in range(len(ms)):
            for j in range(len(SETS)):
                txt = "inel." if np.isnan(M_[i, j]) else f"{M_[i, j]:.4f}"
                ax.text(j, i, txt, ha="center", va="center", fontsize=7,
                        color="white" if not np.isnan(M_[i, j]) else "black")
        ax.set_title("Brier 1y (D)" if task == "D" else "IBS 1–3 (L)", fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.03)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_budget(df, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sub = df[(df.state == "done") & (df.fset == "S4") & (df.n_trials.fillna(0) >= 10)]
    if not len(sub):
        return
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.5))
    for _, r in sub.iterrows():
        c = [x for x in json.loads(r["budget_curve"]) if x is not None]
        if not c:
            continue
        a = ax[0] if r["task"] == "D" else ax[1]
        a.plot(range(1, len(c) + 1), np.array(c) - c[-1], label=r["model"])
    for a, t in zip(ax, ("D: best Brier − final", "L: best IBS − final")):
        a.set_title(t, fontsize=9)
        a.set_xlabel("trial")
        a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    a = ap.parse_args()
    if a.plan == "batch1":
        report_batch1(a.plan)
        return
    df = load_cells(a.plan)
    out = os.path.join(paths.REPORTS, a.plan)
    os.makedirs(out, exist_ok=True)
    paths.atomic_write_csv(df.drop(columns=["dir"]), os.path.join(out, "cells.csv"))
    print(df[["cell", "state", "runtime_s", "peak_rss_mb"]].to_string())


if __name__ == "__main__":
    main()
