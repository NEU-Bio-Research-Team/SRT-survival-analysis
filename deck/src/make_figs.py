# -*- coding: utf-8 -*-
"""Generate all slide figures from the real WITS panel, in Vietnamese and English."""
import json, os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
from matplotlib.patches import Rectangle, Patch

A = "analysis/"
CORE = json.load(open("deck/src/data_core.json"))
QUAL = json.load(open("deck/src/data_quality.json"))

# ---- template palette (from Slides_template.pptx theme) -------------------
NAVY, TEAL, ORANGE, LBLUE = "#0E2841", "#156082", "#E97132", "#0F9ED5"
GREEN, PURPLE, TEXT = "#196B24", "#A02B93", "#002060"
GRID, MUTED, PAPER = "#DCE2E8", "#5A6B7A", "#FFFFFF"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["FreeSerif", "DejaVu Serif"],
    "figure.facecolor": PAPER, "axes.facecolor": PAPER,
    "text.color": TEXT, "axes.labelcolor": TEXT,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#B9C3CC", "axes.linewidth": .8,
    "grid.color": GRID, "grid.linewidth": .8,
    "axes.titlesize": 15, "axes.labelsize": 12,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "legend.fontsize": 11,
    "savefig.bbox": "tight", "savefig.pad_inches": .12, "figure.dpi": 200,
})

L = {}   # active language dict
LANG = "vi"
SHOW_TITLE = False   # slide carries the message instead

def save(fig, name):
    p = f"deck/fig/{name}_{LANG}.png"
    fig.savefig(p, dpi=200, facecolor=PAPER)
    plt.close(fig)
    print("  ", p)

def clean(ax, grid="y"):
    ax.spines[["top", "right"]].set_visible(False)
    if grid: ax.grid(axis=grid, alpha=.7, zorder=0)
    ax.set_axisbelow(True)

def thousands(x, _):
    return f"{x:,.0f}".replace(",", ".") if LANG == "vi" else f"{x:,.0f}"

# =========================================================================
def f1_motivation():
    """Value trajectory of one real relationship that grew, then died."""
    d = CORE["motiv"]; yr = d["year"]; v = np.array(d["value"]) / 1e6
    fig, ax = plt.subplots(figsize=(11.4, 4.5))
    ax.fill_between(yr, 0, v, color=TEAL, alpha=.13, zorder=1)
    ax.plot(yr, v, color=TEAL, lw=2.6, marker="o", ms=5.5, mfc=PAPER, mew=1.8, zorder=3)
    pk = int(np.argmax(v))
    ax.annotate(L["peak"].format(v=f"{v[pk]:.2f}"), (yr[pk], v[pk]),
                textcoords="offset points", xytext=(-14, 16), ha="center",
                fontsize=12, color=TEAL, weight="bold")
    ax.annotate(L["start"], (yr[0], v[0]), textcoords="offset points", xytext=(6, 26),
                fontsize=11, color=MUTED)
    # death marker
    ax.scatter([yr[-1]], [v[-1]], s=140, marker="X", color=ORANGE, zorder=5)
    ax.annotate(L["death"], (yr[-1], v[-1]), textcoords="offset points", xytext=(-6, 34),
                ha="right", fontsize=12, color=ORANGE, weight="bold")
    ax.axvspan(2021.5, 2025.4, color=ORANGE, alpha=.05, zorder=0)
    ax.text(2023.5, max(v) * .55, L["gone"], ha="center", fontsize=11.5, color=ORANGE, style="italic")
    ax.set_xlim(2004.2, 2025.4); ax.set_ylim(0, max(v) * 1.28)
    ax.set_ylabel(L["musd"]); ax.set_xlabel(L["year"])
    ax.set_xticks(range(2005, 2026, 2))
    clean(ax)
    (ax.set_title(L["f1_title"], loc="left", weight="bold", pad=12) if SHOW_TITLE else None)
    save(fig, "f1_motivation")

# =========================================================================
def f2_timeline():
    """Two real relationships with Germany: spell structure, gaps, censoring."""
    fig, ax = plt.subplots(figsize=(11.4, 3.9))
    lo, hi = 2003, 2025
    rows = [(L["r_291"], CORE["timeline_291"], 1),
            (L["r_429"], CORE["timeline_429"], 0)]
    for y, (lab, spells, _) in zip([1.0, 0.0], rows):
        for s in spells:
            x0, x1 = s["start_year"], s["end_year"]
            w = x1 - x0 + 1
            cens = bool(s["right_censored"])
            if cens:
                ax.add_patch(Rectangle((x0 - .42, y - .21), w - .16, .42, facecolor=TEAL,
                                       alpha=.28, edgecolor=TEAL, lw=1.6, ls=(0, (3, 2)), zorder=3))
                ax.annotate("", (x1 + .95, y), (x1 + .42, y),
                            arrowprops=dict(arrowstyle="-|>", color=TEAL, lw=1.8))
                ax.text(x1 + 1.15, y, L["censored"], va="center", fontsize=10.5, color=TEAL)
            else:
                ax.add_patch(Rectangle((x0 - .42, y - .21), w - .16, .42,
                                       facecolor=TEAL, edgecolor="none", zorder=3))
                ax.scatter([x1 + .58], [y], marker="X", s=78, color=ORANGE, zorder=5)
            if w >= 4:
                ax.text(x0 + w / 2 - .5, y, f"{x0}–{x1}", ha="center", va="center",
                        color="white", fontsize=11, zorder=6)
        ax.text(lo - 1.1, y, lab, ha="right", va="center", fontsize=11.5, color=TEXT)
    ax.text(2016.5, 1.42, L["one_spell"], fontsize=10.5, color=MUTED, ha="center")
    ax.text(2013.5, -.46, L["five_spells"], fontsize=10.5, color=MUTED, ha="center")
    for x in range(lo, hi + 1):
        ax.axvline(x - .5, color=GRID, lw=.7, zorder=0)
    ax.set_xlim(lo - 6.6, hi + 3.4); ax.set_ylim(-.75, 1.75)
    ax.set_yticks([]); ax.set_xticks(range(2004, 2026, 2))
    ax.spines[["top", "right", "left"]].set_visible(False)
    leg = [Patch(facecolor=TEAL, label=L["alive"]),
           plt.Line2D([], [], marker="X", ls="", color=ORANGE, ms=9, label=L["event1"]),
           Patch(facecolor=TEAL, alpha=.28, ls="--", ec=TEAL, label=L["rcens"])]
    ax.legend(handles=leg, loc="upper right", frameon=False, ncol=3, bbox_to_anchor=(1.0, 1.24))
    (ax.set_title(L["f2_title"], loc="left", weight="bold", pad=20) if SHOW_TITLE else None)
    save(fig, "f2_timeline")

# =========================================================================
def f3_km():
    km = pd.read_csv(A + "km_survival.csv")
    fig, ax = plt.subplots(figsize=(11.0, 4.7))
    style = {"all": (NAVY, 3.0, "-", L["km_all"]),
             "fta_in_force": (TEAL, 2.2, "-", L["km_fta"]),
             "no_fta": (ORANGE, 2.2, (0, (5, 2)), L["km_nofta"])}
    for g, (c, lw, ls, lab) in style.items():
        d = km[km.group == g].sort_values("duration")
        if d.empty: continue
        x = np.r_[0, d.duration.values]; y = np.r_[1.0, d.survival.values]
        ax.step(x, y * 100, where="post", color=c, lw=lw, ls=ls, label=lab, zorder=3)
    d = km[km.group == "all"].set_index("duration").survival
    for t in (1, 2, 5, 10):
        if t in d.index:
            ax.scatter([t], [d[t] * 100], s=42, color=NAVY, zorder=5)
            ax.annotate(f"{d[t]*100:.1f}%", (t, d[t] * 100), textcoords="offset points",
                        xytext=(9, 9), fontsize=11.5, color=NAVY, weight="bold")
    ax.set_xlim(0, 20); ax.set_ylim(0, 100)
    ax.set_xlabel(L["dur_years"]); ax.set_ylabel(L["surv_pct"])
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.legend(frameon=False, loc="upper right")
    clean(ax, grid="both")
    (ax.set_title(L["f3_title"], loc="left", weight="bold", pad=12) if SHOW_TITLE else None)
    ax.text(0, -.20, L["f3_note"], fontsize=10.5, color=MUTED, transform=ax.transAxes, va="top")
    save(fig, "f3_km")

# =========================================================================
def f4_duration():
    d = CORE["dur_dist"]; tot = CORE["dur_total"]
    dd = np.array(d["d"]); nn = np.array(d["n"])
    cap = 15
    x = list(range(1, cap + 1)); y = [int(nn[dd == i].sum()) for i in x]
    y[-1] = int(nn[dd >= cap].sum())
    fig, ax = plt.subplots(figsize=(11.0, 4.4))
    cols = [ORANGE] + [TEAL] * (cap - 1)
    b = ax.bar(x, y, color=cols, width=.74, zorder=3)
    ax.bar_label(b, labels=[f"{v/tot*100:.1f}%" if v / tot > .02 else "" for v in y],
                 padding=3, fontsize=10.5, color=TEXT)
    ax.set_xticks(x); ax.set_xticklabels([str(i) for i in x[:-1]] + [f"{cap}+"])
    ax.set_xlabel(L["dur_years"]); ax.set_ylabel(L["n_spells"])
    ax.yaxis.set_major_formatter(FuncFormatter(thousands))
    clean(ax)
    (ax.set_title(L["f4_title"], loc="left", weight="bold", pad=12) if SHOW_TITLE else None)
    ax.annotate(L["f4_note"], (1, y[0]), textcoords="offset points", xytext=(30, -34),
                fontsize=11.5, color=ORANGE,
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.4))
    save(fig, "f4_duration")

# =========================================================================
def f5_threshold():
    t = pd.read_csv(A + "threshold_sensitivity.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.4, 4.0))
    x = np.arange(len(t)); lab = [f"{v//1000}K" for v in t.threshold_usd]
    cur = list(t.threshold_usd).index(10000)
    c1 = [TEAL if i != cur else NAVY for i in range(len(t))]
    b = a1.bar(x, t.spells, color=c1, width=.66, zorder=3)
    a1.bar_label(b, labels=[f"{v:,.0f}".replace(",", ".") if LANG == "vi" else f"{v:,.0f}"
                            for v in t.spells], padding=3, fontsize=10, color=TEXT)
    a1.set_xticks(x); a1.set_xticklabels(lab); a1.set_ylabel(L["n_spells"])
    a1.set_xlabel(L["threshold"]); a1.set_title(L["f5_a"], fontsize=13, loc="left", color=TEXT)
    a1.yaxis.set_major_formatter(FuncFormatter(thousands)); clean(a1)

    a2.plot(x, t.pct_one_year, color=ORANGE, lw=2.6, marker="o", ms=7, mfc=PAPER, mew=1.8,
            label=L["pct1y"], zorder=4)
    a2.plot(x, t.value_above_floor_pct, color=TEAL, lw=2.6, marker="s", ms=6.5, mfc=PAPER,
            mew=1.8, label=L["pctval"], zorder=4)
    for i, v in enumerate(t.pct_one_year):
        a2.annotate(f"{v:.1f}", (i, v), textcoords="offset points", xytext=(0, -20),
                    ha="center", fontsize=10.5, color=ORANGE)
    a2.axvline(cur, color=NAVY, lw=1.2, ls=(0, (4, 3)), zorder=2)
    a2.text(cur + .08, 72, L["current"], fontsize=10.5, color=NAVY, rotation=90, va="bottom")
    a2.set_xticks(x); a2.set_xticklabels(lab); a2.set_ylim(30, 108)
    a2.set_xlabel(L["threshold"]); a2.set_ylabel("%")
    a2.legend(frameon=False, loc="center left"); clean(a2, grid="y")
    a2.set_title(L["f5_b"], fontsize=13, loc="left", color=TEXT)
    (fig.suptitle(L["f5_title"], x=.005, ha="left", weight="bold", fontsize=15, y=1.045) if SHOW_TITLE else None)
    save(fig, "f5_threshold")

# =========================================================================
def f6_blocks():
    blocks = [(L["b_id"], 11, TEAL), (L["b_trade"], 11, TEAL), (L["b_tar"], 4, ORANGE),
              (L["b_mx"], 6, MUTED), (L["b_mm"], 10, MUTED), (L["b_lpi"], 8, MUTED),
              (L["b_glpi"], 4, MUTED), (L["b_fta"], 7, ORANGE), (L["b_ttb"], 8, ORANGE),
              (L["b_grav"], 21, MUTED), (L["b_us"], 9, ORANGE), (L["b_ave"], 4, PURPLE),
              (L["b_shock"], 18, MUTED), (L["b_pci"], 7, TEAL), (L["b_cbam"], 5, ORANGE),
              (L["b_ntms"], 13, PURPLE), (L["b_ntm6"], 12, PURPLE)]
    fig, ax = plt.subplots(figsize=(11.6, 3.5))
    x = 0
    for lab, n, c in blocks:
        ax.add_patch(Rectangle((x, .55), n, .42, facecolor=c, edgecolor=PAPER, lw=1.4))
        ax.text(x + n / 2, .76, str(n), ha="center", va="center", color="white",
                fontsize=10.5 if n >= 6 else 9)
        if n >= 7:
            ax.text(x + n / 2, .50, lab, ha="right", va="top", fontsize=9.5, color=TEXT,
                    rotation=38, rotation_mode="anchor")
        x += n
    groups = [(L["g_core"], TEAL, 29), (L["g_pol"], ORANGE, 33),
              (L["g_ctx"], MUTED, 67), (L["g_ntm"], PURPLE, 29)]
    gx = 6
    for lab, c, n in groups:
        ax.add_patch(Rectangle((gx, 1.10), 5.2, .17, facecolor=c, edgecolor="none"))
        ax.text(gx + 7, 1.185, f"{lab} — {n} {L['cols']}", ha="left", va="center",
                fontsize=11.5, color=TEXT)
        gx += 38
    ax.set_xlim(-2, 160); ax.set_ylim(-.30, 1.45); ax.axis("off")
    (ax.set_title(L["f6_title"], loc="left", weight="bold", pad=6, x=.012) if SHOW_TITLE else None)
    save(fig, "f6_blocks")

# =========================================================================
def f7_scope():
    s = CORE["scope"]
    items = [(L["s_eu"], s["eu27_2003_2023"], NAVY),
             (L["s_uk"], s["uk_2003_2023"], TEAL),
             (L["s_gl"], s["global_2003_2025"], LBLUE)]
    keys = [("episode_years", L["k_ep"]), ("spells", L["k_sp"]),
            ("events", L["k_ev"]), ("families", L["k_fa"])]
    fig, axes = plt.subplots(1, 4, figsize=(11.6, 3.5))
    for ax, (k, kl) in zip(axes, keys):
        vals = [it[1][k] for it in items]
        b = ax.barh([0, 1, 2], vals[::-1], color=[c for _, _, c in items][::-1],
                    height=.62, zorder=3)
        ax.bar_label(b, labels=[thousands(v, 0) for v in vals[::-1]], padding=4,
                     fontsize=10.5, color=TEXT)
        ax.set_yticks([0, 1, 2]); ax.set_yticklabels([it[0] for it in items][::-1], fontsize=10.5)
        ax.set_xlim(0, max(vals) * 1.42); ax.set_xticks([])
        ax.set_title(kl, fontsize=12, color=TEXT, loc="left")
        ax.spines[["top", "right", "bottom"]].set_visible(False)
        if ax is not axes[0]: ax.set_yticklabels([])
    (fig.suptitle(L["f7_title"], x=.005, ha="left", weight="bold", fontsize=15, y=1.06) if SHOW_TITLE else None)
    save(fig, "f7_scope")

# =========================================================================
def f8_quality():
    cov = QUAL["coverage"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.6, 4.5),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    labs = [c["label"] for c in cov][::-1]; pct = [c["pct"] for c in cov][::-1]
    labs = [L["cov_map"].get(x, x) for x in labs]
    cols = [TEAL if p >= 94 else (ORANGE if p >= 20 else PURPLE) for p in pct]
    b = a1.barh(range(len(pct)), pct, color=cols, height=.66, zorder=3)
    a1.bar_label(b, labels=[f"{p:.1f}%" for p in pct], padding=4, fontsize=10, color=TEXT)
    a1.set_yticks(range(len(labs))); a1.set_yticklabels(labs, fontsize=10.5)
    a1.set_xlim(0, 118); a1.set_xticks([0, 25, 50, 75, 100])
    a1.xaxis.set_major_formatter(PercentFormatter())
    a1.set_title(L["f8_a"], fontsize=13, loc="left", color=TEXT)
    a1.spines[["top", "right"]].set_visible(False); a1.grid(axis="x", alpha=.6); a1.set_axisbelow(True)

    # timing quality
    names = [L["q_tar"], L["q_ntm"], L["q_grav"]]
    exact = [QUAL["tariff_exact_pct"], QUAL["ntm6_exact_pct"], 100 - QUAL["gravity_carry_pct"]]
    fut = [0, QUAL["ntm6_future_pct"], 0]
    past = [100 - QUAL["tariff_exact_pct"], QUAL["ntm6_past_pct"], QUAL["gravity_carry_pct"]]
    y = np.arange(3)
    a2.barh(y, exact, color=TEAL, height=.55, label=L["q_exact"], zorder=3)
    a2.barh(y, past, left=exact, color=ORANGE, height=.55, label=L["q_past"], zorder=3)
    a2.barh(y, fut, left=np.array(exact) + np.array(past), color=PURPLE, height=.55,
            label=L["q_future"], zorder=3)
    for i in range(3):
        a2.text(exact[i] / 2, i, f"{exact[i]:.0f}%", ha="center", va="center",
                color="white", fontsize=10.5)
        if past[i] > 8:
            a2.text(exact[i] + past[i] / 2, i, f"{past[i]:.0f}%", ha="center", va="center",
                    color="white", fontsize=10.5)
        if fut[i] > 8:
            a2.text(exact[i] + past[i] + fut[i] / 2, i, f"{fut[i]:.0f}%", ha="center",
                    va="center", color="white", fontsize=10.5)
    a2.set_yticks(y); a2.set_yticklabels(names, fontsize=10.5)
    a2.set_xlim(0, 100); a2.set_xticks([]); a2.invert_yaxis()
    a2.legend(frameon=False, loc="upper center", bbox_to_anchor=(.5, -.02), ncol=3, fontsize=10.5)
    a2.spines[["top", "right", "bottom"]].set_visible(False)
    a2.set_title(L["f8_b"], fontsize=13, loc="left", color=TEXT)
    (fig.suptitle(L["f8_title"], x=.005, ha="left", weight="bold", fontsize=15, y=1.04) if SHOW_TITLE else None)
    save(fig, "f8_quality")

# =========================================================================
def f9_importers():
    r = pd.DataFrame(CORE["importer_survival"])
    fig, ax = plt.subplots(figsize=(11.0, 4.8))
    sz = np.sqrt(r.n_spells) * 9
    sc = ax.scatter(r.value_bn, r.pct_5y_plus, s=sz, c=[TEAL] * len(r),
                    alpha=.72, edgecolors=NAVY, linewidths=1.1, zorder=3)
    for _, row in r.iterrows():
        ax.annotate(row.importer, (row.value_bn, row.pct_5y_plus),
                    textcoords="offset points", xytext=(0, -4), ha="center",
                    fontsize=10, color=TEXT, weight="bold", zorder=5)
    mx, my = r.value_bn.median(), r.pct_5y_plus.median()
    ax.axvline(mx, color=MUTED, lw=1, ls=(0, (4, 3))); ax.axhline(my, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.set_xscale("log")
    ax.set_xlabel(L["f9_x"]); ax.set_ylabel(L["f9_y"])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:.0f}"))
    clean(ax, grid="both")
    (ax.set_title(L["f9_title"], loc="left", weight="bold", pad=12) if SHOW_TITLE else None)
    ax.text(.99, .04, L["f9_note"], transform=ax.transAxes, ha="right", fontsize=10.5,
            color=MUTED, style="italic")
    save(fig, "f9_importers")

# =========================================================================
def f10_hazard():
    h = pd.read_csv(A + "hazard_baseline.csv")
    h = h[~h.term.str.startswith("duration")].copy()
    nm = L["haz_map"]
    h["lab"] = h.term.map(lambda t: nm.get(t, t))
    h = h.sort_values("hazard_ratio")
    fig, ax = plt.subplots(figsize=(10.6, 4.4))
    y = np.arange(len(h))
    lo = np.exp(h.coef - 1.96 * h.std_err); hi = np.exp(h.coef + 1.96 * h.std_err)
    cols = [TEAL if v < 1 else ORANGE for v in h.hazard_ratio]
    ax.hlines(y, lo, hi, color=cols, lw=2.4, zorder=3)
    ax.scatter(h.hazard_ratio, y, s=70, color=cols, zorder=4, edgecolors=PAPER, linewidths=1.2)
    for i, v in zip(y, h.hazard_ratio):
        ax.annotate(f"{v:.3f}", (v, i), textcoords="offset points", xytext=(0, 11),
                    ha="center", fontsize=10.5, color=TEXT)
    ax.axvline(1, color=NAVY, lw=1.3, zorder=2)
    ax.set_yticks(y); ax.set_yticklabels(h.lab, fontsize=11)
    ax.set_xlim(.4, 1.12); ax.set_xlabel(L["hr"])
    ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="x", alpha=.6); ax.set_axisbelow(True)
    ax.text(.995, 1.075, L["haz_hi"], transform=ax.transAxes, ha="right", fontsize=10.5, color=ORANGE)
    ax.text(.02, 1.075, L["haz_lo"], transform=ax.transAxes, fontsize=10.5, color=TEAL)
    ((ax.set_title(L["f10_title"], loc="left", weight="bold", pad=36) if SHOW_TITLE else None) if SHOW_TITLE else None)
    save(fig, "f10_hazard")

# =========================================================================
def f11_eventrate():
    e = QUAL["event_rate"]
    yr = np.array(e["year"]); rt = np.array(e["rate"]); ep = np.array(e["episodes"])
    fig, ax = plt.subplots(figsize=(11.2, 4.3))
    ax2 = ax.twinx()
    ax2.bar(yr, ep, color=LBLUE, alpha=.20, width=.72, zorder=1, label=L["k_ep"])
    ax2.set_ylabel(L["k_ep"], color=MUTED); ax2.set_ylim(0, max(ep) * 2.3)
    ax2.yaxis.set_major_formatter(FuncFormatter(thousands)); ax2.spines[["top"]].set_visible(False)
    ax.plot(yr, rt, color=NAVY, lw=2.8, marker="o", ms=5.5, mfc=PAPER, mew=1.8, zorder=4)
    for xx, yy, lab in [(2008, rt[yr == 2008][0], L["gfc"]), (2020, rt[yr == 2020][0], L["covid"])]:
        ax.scatter([xx], [yy], s=120, facecolors="none", edgecolors=ORANGE, lw=2, zorder=5)
        ax.annotate(lab, (xx, yy), textcoords="offset points", xytext=(0, 16), ha="center",
                    fontsize=11, color=ORANGE, weight="bold")
    ax.set_ylabel(L["ev_rate"]); ax.set_xlabel(L["year"]); ax.set_zorder(3); ax.patch.set_visible(False)
    ax.set_ylim(0, max(rt) * 1.3); ax.yaxis.set_major_formatter(PercentFormatter())
    ax.set_xticks(range(2003, 2026, 2)); clean(ax)
    (ax.set_title(L["f11_title"], loc="left", weight="bold", pad=12) if SHOW_TITLE else None)
    ax.text(0, -.30, L["f11_note"], transform=ax.transAxes, fontsize=10.5, color=MUTED, va="top")
    save(fig, "f11_eventrate")

# =========================================================================
def f12_valdur():
    s = CORE["eu_scatter"]
    d = np.array(s["dur"], float); v = np.array(s["val"], float)
    m = v > 0
    d, v = d[m], np.log10(v[m])
    fig, ax = plt.subplots(figsize=(10.6, 4.6))
    hb = ax.hexbin(d, v, gridsize=(22, 20), bins="log", cmap="Blues", mincnt=1,
                   edgecolors="none", zorder=2)
    med = [np.median(v[d == k]) for k in range(1, 21)]
    ax.plot(range(1, 21), med, color=ORANGE, lw=2.6, marker="o", ms=4.5, mfc=PAPER,
            mew=1.6, zorder=4, label=L["median_val"])
    cb = fig.colorbar(hb, ax=ax, pad=.015); cb.set_label(L["n_spells"], color=MUTED, fontsize=11)
    cb.ax.tick_params(labelsize=10, colors=MUTED)
    ax.set_xlim(.4, 20.6); ax.set_xlabel(L["dur_years"]); ax.set_ylabel(L["log_val"])
    ax.set_yticks([4, 5, 6, 7, 8])
    ax.set_yticklabels(["10K", "100K", "1M", "10M", "100M"])
    ax.legend(frameon=False, loc="upper left")
    clean(ax, grid="both")
    (ax.set_title(L["f12_title"], loc="left", weight="bold", pad=12) if SHOW_TITLE else None)
    save(fig, "f12_valdur")

FIGS = [f1_motivation, f2_timeline, f3_km, f4_duration, f5_threshold, f6_blocks,
        f7_scope, f8_quality, f9_importers, f10_hazard, f11_eventrate, f12_valdur]

if __name__ == "__main__":
    from fig_labels import LABELS
    for lang in ("vi", "en"):
        LANG = lang
        globals()["LANG"] = lang
        L.clear(); L.update(LABELS[lang])
        print(f"--- {lang} ---")
        for f in FIGS:
            f()
    print("done")
