"""Step 3 — initial results: every model on every test fold, and its curves.

Metrics are read from reports/batch2/cells.csv (the Đợt 2 confirmation run;
nothing is recomputed). Curves are drawn from the saved test predictions in
artifacts/runs/batch2/<cell>/pred.parquet, seed-averaged for the stochastic
models (the same 3 refit seeds the metrics use).

Curves
  * Task L models output S(u | x) on u = 1..5. The cohort curve is the mean of
    S(u | x) over the test origins; its hazard is the discrete conditional
    h(u) = 1 - S(u) / S(u - 1). The observed counterpart is the Kaplan–Meier
    estimate on the same test cohort.
  * Task D models output one number, P(exit next year | x). Their "hazard
    curve" is that probability averaged by spell age, set against the observed
    one-year exit rate at each age.

Run from notebook/:
    $PY -m stage2_benchmark.presentation.step3_results
"""

from __future__ import annotations

import os

from stage2_benchmark.presentation.common import (
    COLOR, D_MODELS, EVENT, EXAMPLE_RELATION, FOLDS, INK, INK2, L_MODELS, MARKER,
    MUTED, NAMES, SEQ, TAB, TEST_ORIGIN, plt, save, write_csv)
from stage2_benchmark import paths
from stage2_benchmark.presentation.step2_problem import km

import numpy as np
import pandas as pd

RUNS = os.path.join(paths.RUNS, "batch2")
CELLS = os.path.join(paths.REPORTS, "batch2", "cells.csv")
SETS = ["S1", "S4", "S6"]
SET_MARK = {"S1": dict(mfc="white"), "S4": dict(mfc="white", alpha=0.75), "S6": dict()}
FSET = "S6"          # the locked S* for both tasks
U = np.arange(0, 6)


# ------------------------------------------------------------------ tables
def cells() -> pd.DataFrame:
    c = pd.read_csv(CELLS)
    c = c[c["stage"] == "test"].copy()
    c["name"] = c["model"].map(NAMES)
    return c


def tables(c):
    D = c[c["task"] == "D"][["model", "name", "fset", "fold", "m_n", "m_events",
                            "m_brier_1y", "m_logloss", "m_roc_auc", "m_pr_auc",
                            "m_calib_slope", "m_calib_intercept", "m_mean_pred",
                            "m_event_rate", "runtime_s"]].copy()
    ref = D[D["model"] == "D00"].set_index("fold")["m_brier_1y"]
    D["skill_vs_age_only"] = 1 - D["m_brier_1y"] / D["fold"].map(ref)
    L = c[c["task"] == "L"][["model", "name", "fset", "fold", "m_n", "m_events",
                            "m_ibs_1_3", "m_brier_1", "m_brier_2", "m_brier_3",
                            "m_antolini_ctd", "m_td_auc_1", "m_td_auc_3",
                            "m_km_S1", "m_mean_pred_S1", "m_km_S3", "m_mean_pred_S3",
                            "m_ibs_1_5", "runtime_s"]].copy()
    ref = L[L["model"] == "L00"].set_index("fold")["m_ibs_1_3"]
    L["skill_vs_km"] = 1 - L["m_ibs_1_3"] / L["fold"].map(ref)
    for T in (D, L):
        T.columns = [x[2:] if x.startswith("m_") else x for x in T.columns]
        T.sort_values(["model", "fset", "fold"], inplace=True)
    write_csv(D.round(5), TAB, "results_D_per_fold.csv")
    write_csv(L.round(5), TAB, "results_L_per_fold.csv")

    # compact wide tables (primary metric; one row per model x set, one column per fold)
    md = []
    for T, metric, skill, title in ((D, "brier_1y", "skill_vs_age_only", "Task D — Brier 1y (lower is better)"),
                                    (L, "ibs_1_3", "skill_vs_km", "Task L — IPCW IBS 1–3 (lower is better)")):
        w = T.pivot_table(index=["model", "name", "fset"], columns="fold", values=metric).reset_index()
        w["mean"] = w[FOLDS].mean(axis=1)
        # as in batch2/REPORT.md: skill of the 3-fold mean against the reference's mean
        w["skill_mean"] = 1 - w["mean"] / float(w.loc[w["fset"] == "REF", "mean"].iloc[0])
        w["rank_by_fold"] = w[FOLDS].rank().astype(int).astype(str).agg(" / ".join, axis=1)
        w = w.sort_values("mean")
        write_csv(w.round(5), TAB, f"results_{T['model'].iloc[0][0]}_wide.csv")
        md.append(f"### {title}\n\n| model | set | F1 (2019) | F2 (2020) | F3 (2021) | mean | skill |\n"
                  "|---|---|---:|---:|---:|---:|---:|")
        for r in w.itertuples():
            md.append(f"| {r.model} {r.name} | {r.fset} | {getattr(r, 'F1'):.5f} | "
                      f"{getattr(r, 'F2'):.5f} | {getattr(r, 'F3'):.5f} | {r.mean:.5f} | "
                      f"{r.skill_mean:.3f} |")
        md.append("")
    with open(os.path.join(TAB, "results_per_fold.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("  wrote out/tables/results_per_fold.md")
    return D, L


def fig_per_fold(T, task):
    metric = "brier_1y" if task == "D" else "ibs_1_3"
    ref_model = "D00" if task == "D" else "L00"
    models = D_MODELS if task == "D" else L_MODELS
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9), sharey=True, gridspec_kw={"wspace": 0.08})
    for ax, fold in zip(axes, FOLDS):
        t = T[T["fold"] == fold]
        ref = float(t[t["model"] == ref_model][metric].iloc[0])
        yy = np.arange(len(models))[::-1]
        for y_, m in zip(yy, models):
            v = t[t["model"] == m].set_index("fset")[metric]
            ax.plot(v.reindex(SETS).values, [y_] * 3, color=COLOR[m], lw=1, alpha=0.6)
            for st in SETS:
                ax.plot(v[st], y_, MARKER[m], color=COLOR[m], ms=8 if st == "S6" else 6.5,
                        mec=COLOR[m], mew=1.4, **SET_MARK[st])
            ax.text(v["S1"], y_ + 0.25, "S1", fontsize=7.5, color=MUTED, ha="center")
            ax.text(v["S6"], y_ + 0.25, "S6", fontsize=7.5, color=INK2, ha="center")
        lo = t[t["model"].isin(models)][metric].min()
        ax.set_xlim(lo - (ref - lo) * 0.08, ref + (ref - lo) * 0.1)
        ax.axvline(ref, color=INK, lw=1)
        ax.text(ref, len(models) - 0.45, f"{NAMES[ref_model]}\n{ref:.4f}", ha="right",
                fontsize=8, color=INK)
        ax.set_title(f"{fold} · test origin {TEST_ORIGIN[fold]}")
        ax.set_yticks(yy, [NAMES[m] for m in models])
        ax.set_ylim(-0.6, len(models) - 0.1)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Brier 1y" if task == "D" else "IPCW IBS 1–3")
    fig.suptitle(f"Task {task}: test score of every model on every fold "
                 "(hollow = S1, faint = S4, solid = S6; lower is better)",
                 x=0.06, ha="left", fontsize=12.5, fontweight="semibold", color=INK, y=1.04)
    save(fig, f"20_task{task}_per_fold_scores.png")


def fig_skill(D, L):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"wspace": 0.55})
    for ax, T, models, sk, lab in ((axes[0], D, D_MODELS, "skill_vs_age_only", "Task D: Brier skill vs age-only"),
                                   (axes[1], L, L_MODELS, "skill_vs_km", "Task L: IBS skill vs Kaplan–Meier")):
        t = T[T["fset"] == FSET]
        x = np.arange(3)
        for m in models:
            v = t[t["model"] == m].set_index("fold")[sk].reindex(FOLDS)
            ax.plot(x, v.values, color=COLOR[m], marker=MARKER[m], ms=7, label=NAMES[m])
        ax.set_xticks(x, [f"{f}\n({TEST_ORIGIN[f]})" for f in FOLDS])
        ax.set_xlim(-0.2, 2.2)
        ax.set_ylabel("skill = 1 − score / reference")
        ax.set_title(f"{lab} (set {FSET})")
        ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "21_skill_by_fold_S6.png")


# ------------------------------------------------------------------ curves
def load_pred(fold, model, fset):
    tag = "REF" if model in ("D00", "L00") else fset
    return pd.read_parquet(os.path.join(RUNS, f"{fold}__{model}__{tag}__test", "pred.parquet"))


def surv_matrix(p) -> np.ndarray:
    """n x 5 matrix of S(u), u = 1..5, averaged over the seeds present."""
    seeds = sorted({c.split("_s")[1] for c in p.columns if c.startswith("S1_s")})
    return np.mean([p[[f"S{u}_s{s}" for u in range(1, 6)]].to_numpy() for s in seeds], axis=0)


def hazard(S: np.ndarray) -> np.ndarray:
    """h(u) = 1 - S(u)/S(u-1) along the last axis, S(0) = 1."""
    S0 = np.concatenate([np.ones(S.shape[:-1] + (1,)), S], axis=-1)
    return 1 - S0[..., 1:] / np.clip(S0[..., :-1], 1e-9, None)


def curves(fset=FSET):
    """Cohort-level S and h per fold, per model, plus the observed KM."""
    rows = []
    for fold in FOLDS:
        ref = load_pred(fold, "L00", fset)
        t, S_km, risk, ev = km(ref["duration"], ref["event"])
        umax = int(ref["duration"].max())
        for u in range(1, umax + 1):
            rows.append({"fold": fold, "model": "observed", "name": "Observed (KM on test cohort)",
                         "u": u, "S": S_km[u], "h": 1 - S_km[u] / S_km[u - 1],
                         "at_risk": int(risk[u]), "events": int(ev[u])})
        for m in ["L00"] + L_MODELS:
            S = surv_matrix(load_pred(fold, m, fset)).mean(axis=0)
            h = hazard(S[None, :])[0]
            for u in range(1, 6):
                rows.append({"fold": fold, "model": m, "name": NAMES[m], "u": u,
                             "S": S[u - 1], "h": h[u - 1], "observed_to": umax})
    out = pd.DataFrame(rows)
    write_csv(out.round(5), TAB, f"curves_L_cohort_{fset}.csv")
    return out


def fig_cohort_curves(cv, what):
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), sharey=True, gridspec_kw={"wspace": 0.08})
    for ax, fold in zip(axes, FOLDS):
        c = cv[cv["fold"] == fold]
        obs = c[c["model"] == "observed"]
        umax = int(obs["u"].max())
        if umax < 5:
            ax.axvspan(umax + 0.5 if what == "h" else umax, 5.4, color="#f0efec", zorder=0)
            ax.text(5.3, 0.47 if what == "S" else 0.005, "beyond test\nfollow-up", ha="right",
                    fontsize=8, color=MUTED)
        for m in ["L00"] + L_MODELS:
            d = c[c["model"] == m]
            if what == "S":
                x, y = np.r_[0, d["u"]], np.r_[1, d["S"]]
            else:
                x, y = d["u"].to_numpy(), d["h"].to_numpy()
            if m == "L00":
                ax.plot(x, y, color=MUTED, lw=1.4, marker="o", ms=4, mfc="white",
                        label="Kaplan–Meier fitted on train (reference)")
            else:
                ax.plot(x, y, color=COLOR[m], marker=MARKER[m], ms=6, lw=1.6, label=NAMES[m])
        if what == "S":
            ax.plot(np.r_[0, obs["u"]], np.r_[1, obs["S"]], color=INK, lw=2.6, marker="o",
                    ms=7, label="observed on the test cohort (KM)", zorder=5)
        else:
            ax.plot(obs["u"], obs["h"], color=INK, lw=0, marker="_", ms=26, mew=3,
                    label="observed on the test cohort (life table)", zorder=5)
        ax.set_title(f"{fold} · test origin {TEST_ORIGIN[fold]} (n = {int(obs['at_risk'].iloc[0]):,})")
        ax.set_xlabel("years after the origin, u")
        ax.set_xticks(range(0 if what == "S" else 1, 6))
        ax.set_xlim(-0.1 if what == "S" else 0.6, 5.4)
    if what == "S":
        axes[0].set_ylabel("mean predicted S(u | x) over test origins")
        axes[0].set_ylim(0.45, 1.01)
        title = "Survival curves: every Task-L model vs the observed test cohort (set S6)"
        name = "22_survival_curves_by_fold.png"
    else:
        axes[0].set_ylabel("h(u) = 1 − S(u) / S(u − 1)")
        axes[0].set_ylim(0, None)
        title = "Hazard curves: annual conditional exit probability implied by each model (set S6)"
        name = "23_hazard_curves_by_fold.png"
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=4, fontsize=8.8, bbox_to_anchor=(0.5, -0.12))
    fig.suptitle(title, x=0.06, ha="left", fontsize=12.5, fontweight="semibold", color=INK, y=1.03)
    save(fig, name)


def fig_D_hazard_by_age(fset=FSET):
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), sharey=True, gridspec_kw={"wspace": 0.08})
    rows = []
    for ax, fold in zip(axes, FOLDS):
        base = load_pred(fold, "D00", fset)
        age = base["age_obs"].clip(upper=10).astype(int)
        obs = base.groupby(age)["y"].agg(["mean", "size"])
        for m in ["D00"] + D_MODELS:
            p = load_pred(fold, m, fset)
            prob = p[[c for c in p.columns if c.startswith("p_s")]].mean(axis=1)
            g = prob.groupby(p["age_obs"].clip(upper=10).astype(int)).mean()
            if m == "D00":
                ax.plot(g.index, g.values, color=MUTED, lw=1.4, marker="o", ms=4, mfc="white",
                        label="Age-only hazard (reference)")
            else:
                ax.plot(g.index, g.values, color=COLOR[m], marker=MARKER[m], ms=6, lw=1.6,
                        label=NAMES[m])
            rows += [{"fold": fold, "model": m, "age": int(a), "mean_pred": v} for a, v in g.items()]
        ax.plot(obs.index, obs["mean"], color=INK, lw=0, marker="_", ms=22, mew=3,
                label="observed one-year exit rate", zorder=5)
        rows += [{"fold": fold, "model": "observed", "age": int(a), "mean_pred": r["mean"],
                  "n": int(r["size"])} for a, r in obs.iterrows()]
        ax.set_title(f"{fold} · test origin {TEST_ORIGIN[fold]}")
        ax.set_xticks(range(1, 11), [str(i) for i in range(1, 10)] + ["10+"])
        ax.set_xlabel("spell age at origin")
    axes[0].set_ylabel("P(exit next year): mean prediction")
    axes[0].set_ylim(0, None)
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=6, fontsize=8.8, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle("Task D hazard curves: predicted vs observed one-year exit rate by spell age (set S6)",
                 x=0.06, ha="left", fontsize=12.5, fontweight="semibold", color=INK, y=1.03)
    save(fig, "24_taskD_hazard_by_age.png")
    write_csv(pd.DataFrame(rows).round(5), TAB, "curves_D_hazard_by_age_S6.csv")


def pick_examples(fold="F1", fset=FSET):
    """The worked relation plus a low-, median- and high-risk test origin
    (by the model-average S(3)), so the curves can be compared per model."""
    preds = {m: load_pred(fold, m, fset) for m in L_MODELS}
    key = preds[L_MODELS[0]][["relation", "spell_id", "year", "duration", "event", "age_obs"]]
    S3 = np.mean([surv_matrix(p)[:, 2] for p in preds.values()], axis=0)
    order = np.argsort(S3)
    picks = {"high risk (10th pct of S(3))": order[int(0.10 * len(order))],
             "median risk": order[int(0.50 * len(order))],
             "low risk (90th pct of S(3))": order[int(0.90 * len(order))]}
    ex = np.flatnonzero(key["relation"].to_numpy() == EXAMPLE_RELATION)
    if len(ex):
        picks = {"worked example (step 1)": ex[0], **picks}
    return preds, key, picks


def fig_individual(fold="F1", fset=FSET):
    preds, key, picks = pick_examples(fold, fset)
    n = len(picks)
    fig, ax = plt.subplots(2, n, figsize=(3.6 * n, 6.6), sharey="row",
                           gridspec_kw={"hspace": 0.45, "wspace": 0.08})
    rows = []
    for j, (lab, i) in enumerate(picks.items()):
        k = key.iloc[i]
        for m in L_MODELS:
            S = surv_matrix(preds[m])[i]
            h = hazard(S[None, :])[0]
            ax[0, j].plot(np.r_[0, np.arange(1, 6)], np.r_[1, S], color=COLOR[m], marker=MARKER[m],
                          ms=5.5, lw=1.5, label=NAMES[m])
            ax[1, j].plot(np.arange(1, 6), h, color=COLOR[m], marker=MARKER[m], ms=5.5, lw=1.5)
            rows += [{"case": lab, "relation": k["relation"], "origin": int(k["year"]),
                      "model": m, "u": u, "S": S[u - 1], "h": h[u - 1]} for u in range(1, 6)]
        out = (f"exit observed at u = {int(k['duration'])}" if k["event"] == 1 else
               f"alive, censored at u = {int(k['duration'])}")
        for a in ax[:, j]:
            a.axvline(k["duration"], color=EVENT if k["event"] == 1 else MUTED, lw=1)
        ax[0, j].set_title(f"{lab}\n{k['relation']} · age {int(k['age_obs'])}\n{out}", fontsize=9.5)
        ax[1, j].set_xlabel("years after origin 2019, u")
        ax[0, j].set_xticks(range(0, 6))
        ax[1, j].set_xticks(range(1, 6))
    ax[0, 0].set_ylabel("S(u | x)")
    ax[1, 0].set_ylabel("h(u | x)")
    ax[0, 0].set_ylim(0, 1.02)
    ax[1, 0].set_ylim(0, None)
    h_, l_ = ax[0, 0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="lower center", ncol=5, fontsize=9, bbox_to_anchor=(0.5, -0.05))
    fig.suptitle(f"Individual survival (top) and hazard (bottom) curves, {fold} test origins, set {fset}"
                 " — vertical line = observed outcome", x=0.06, ha="left", fontsize=12,
                 fontweight="semibold", color=INK, y=1.02)
    save(fig, "25_individual_curves_F1.png")
    write_csv(pd.DataFrame(rows).round(5), TAB, "curves_L_individual_F1.csv")


def fig_calibration_L(cv):
    """Predicted vs observed S(u) per fold: the time-profile gap behind the IBS ranking."""
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharey=True, gridspec_kw={"wspace": 0.08})
    for ax, fold in zip(axes, FOLDS):
        c = cv[cv["fold"] == fold]
        obs = c[c["model"] == "observed"].set_index("u")["S"]
        for j, m in enumerate(["L00"] + L_MODELS):
            d = c[c["model"] == m].set_index("u")["S"].reindex(obs.index)
            diff = (d - obs) * 100
            ax.plot(obs.index + (j - 2.5) * 0.06, diff.values,
                    color=MUTED if m == "L00" else COLOR[m], marker="o" if m == "L00" else MARKER[m],
                    ms=6, lw=1.2, label="Kaplan–Meier (train)" if m == "L00" else NAMES[m])
        ax.axhline(0, color=INK, lw=1)
        ax.set_title(f"{fold} · test origin {TEST_ORIGIN[fold]}")
        ax.set_xticks(obs.index)
        ax.set_xlabel("years after the origin, u")
    axes[0].set_ylabel("mean predicted S(u) − observed KM S(u)\n(percentage points)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=6, fontsize=8.8, bbox_to_anchor=(0.5, -0.12))
    fig.suptitle("Calibration-in-the-large of the survival curves (0 = on the observed curve)",
                 x=0.06, ha="left", fontsize=12.5, fontweight="semibold", color=INK, y=1.04)
    save(fig, "26_survival_calibration_gap.png")


def main():
    c = cells()
    D, L = tables(c)
    fig_per_fold(D, "D")
    fig_per_fold(L, "L")
    fig_skill(D, L)
    cv = curves()
    fig_cohort_curves(cv, "S")
    fig_cohort_curves(cv, "h")
    fig_calibration_L(cv)
    fig_D_hazard_by_age()
    fig_individual()


if __name__ == "__main__":
    main()
