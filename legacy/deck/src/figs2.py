# -*- coding: utf-8 -*-
"""Slide figures, light editorial style. One accent colour, no chart junk."""
import json, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
from matplotlib.patches import Rectangle, FancyArrowPatch

A = "analysis/"
CORE = json.load(open("legacy/deck/src/data_core.json"))
QUAL = json.load(open("legacy/deck/src/data_quality.json"))
EDA  = json.load(open("legacy/deck/src/data_eda.json"))

BG     = "#F0F4F8"
INK    = "#16324F"
BODY   = "#33556E"
MUTED  = "#8CA0B3"
BLUE   = "#2E6E9E"
BLUE_D = "#143D63"
BLUE_M = "#6FA3C7"
BLUE_L = "#BBD3E5"
ORANGE = "#E8763A"
ORANGE_L = "#F6C3A6"
GRID   = "#DCE5ED"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Carlito", "Open Sans", "DejaVu Sans"],
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "text.color": BODY, "axes.labelcolor": BODY,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#C3D2DE", "axes.linewidth": .9,
    "grid.color": GRID, "grid.linewidth": .9,
    "axes.labelsize": 13, "xtick.labelsize": 12, "ytick.labelsize": 12,
    "legend.fontsize": 12, "xtick.major.size": 0, "ytick.major.size": 0,
    "savefig.bbox": "tight", "savefig.pad_inches": .18, "figure.dpi": 200,
})

L, LANG = {}, "vi"
def save(fig, name):
    p = f"legacy/deck/fig2/{name}_{LANG}.png"
    fig.savefig(p, dpi=200); plt.close(fig); print("  ", p)

def clean(ax, grid="y", left=True):
    ax.spines[["top", "right"]].set_visible(False)
    if not left: ax.spines["left"].set_visible(False)
    if grid: ax.grid(axis=grid, alpha=.9, zorder=0)
    ax.set_axisbelow(True)

def num(x, _=None):
    s = f"{x:,.0f}"
    return s.replace(",", ".") if LANG == "vi" else s

def dec(v, n=1):
    s = f"{v:.{n}f}"
    return s.replace(".", ",") if LANG == "vi" else s

# ---------------------------------------------------------------- 1
def f_story():
    d = CORE["motiv"]; yr = d["year"]; v = np.array(d["value"]) / 1e6
    fig, ax = plt.subplots(figsize=(11.2, 4.3))
    ax.fill_between(yr, 0, v, color=BLUE_L, alpha=.55, zorder=1)
    ax.plot(yr, v, color=BLUE, lw=2.8, zorder=3)
    pk = int(np.argmax(v))
    ax.scatter([yr[pk]], [v[pk]], s=60, color=BLUE, zorder=5)
    ax.annotate(L["s_peak"], (yr[pk], v[pk]), textcoords="offset points", xytext=(10, 12),
                fontsize=13, color=BLUE_D, weight="bold")
    ax.annotate(L["s_first"], (yr[0], v[0]), textcoords="offset points", xytext=(6, 58),
                fontsize=12, color=MUTED,
                arrowprops=dict(arrowstyle="-", color="#B9CBDA", lw=.9, shrinkB=3))
    ax.scatter([yr[-1]], [v[-1]], s=110, color=ORANGE, zorder=5)
    ax.annotate(L["s_end"], (yr[-1], v[-1]), textcoords="offset points", xytext=(-4, 40),
                ha="right", fontsize=13, color=ORANGE, weight="bold")
    ax.axvspan(2021.6, 2025.4, color=ORANGE, alpha=.055, zorder=0)
    ax.text(2023.5, max(v) * .48, L["s_gone"], ha="center", fontsize=12.5, color=ORANGE)
    ax.set_xlim(2004.4, 2025.4); ax.set_ylim(0, max(v) * 1.30)
    ax.set_ylabel(L["s_y"]); ax.set_xticks(range(2005, 2026, 3))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: dec(x, 1)))
    clean(ax)
    save(fig, "story")

# ---------------------------------------------------------------- 2
def f_timeline():
    fig, ax = plt.subplots(figsize=(11.2, 3.5))
    lo, hi = 2003, 2025
    rows = [(L["t_r1"], CORE["timeline_291"], 1.0), (L["t_r2"], CORE["timeline_429"], 0.0)]
    for lab, spells, y in rows:
        for s in spells:
            x0, x1, w = s["start_year"], s["end_year"], s["end_year"] - s["start_year"] + 1
            cens = bool(s["right_censored"])
            ax.add_patch(Rectangle((x0 - .42, y - .19), w - .16, .38,
                                   facecolor=BLUE_L if cens else BLUE,
                                   edgecolor=BLUE if cens else "none",
                                   lw=1.4, ls=(0, (3, 2)) if cens else "-", zorder=3))
            if not cens:
                ax.scatter([x1 + .58], [y], marker="o", s=46, color=ORANGE, zorder=5)
            else:
                ax.annotate("", (x1 + 1.05, y), (x1 + .45, y),
                            arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.6))
                ax.text(x1 + 1.28, y, L["t_cens"], va="center", fontsize=11.5, color=BLUE)
            if w >= 5:
                ax.text(x0 + w / 2 - .5, y, f"{x0}–{x1}", ha="center", va="center",
                        color="white", fontsize=12, zorder=6, weight="bold")
        ax.text(lo - 1.2, y, lab, ha="right", va="center", fontsize=12.5, color=INK)
    ax.text(2015.5, 1.40, L["t_n1"], fontsize=12, color=MUTED, ha="center")
    ax.text(2013.0, -.44, L["t_n2"], fontsize=12, color=MUTED, ha="center")
    for x in range(lo, hi + 1):
        ax.axvline(x - .5, color=GRID, lw=.8, zorder=0)
    ax.set_xlim(lo - 7.4, hi + 3.6); ax.set_ylim(-.72, 1.68)
    ax.set_yticks([]); ax.set_xticks(range(2004, 2026, 3))
    ax.spines[["top", "right", "left"]].set_visible(False)
    save(fig, "timeline")

# ---------------------------------------------------------------- 3
def f_flows():
    f = EDA["flows"]
    yr = np.array(f["year"]); m = yr <= 2023
    yr = yr[m]; live = np.array(f["live"])[m]
    nb = np.array(f["births"])[m]; nd = np.array(f["deaths"])[m]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11.2, 5.0), sharex=True,
                                 gridspec_kw={"height_ratios": [1.55, 1], "hspace": .18})
    a1.fill_between(yr, 0, live, color=BLUE_L, alpha=.7, zorder=2)
    a1.plot(yr, live, color=BLUE_D, lw=2.8, zorder=3)
    for x in (2003, 2023):
        i = list(yr).index(x)
        a1.scatter([x], [live[i]], s=55, color=BLUE_D, zorder=5)
        a1.annotate(num(live[i]), (x, live[i]), textcoords="offset points",
                    xytext=(8 if x == 2003 else -8, 10), ha="left" if x == 2003 else "right",
                    fontsize=13, weight="bold", color=BLUE_D)
    a1.set_ylabel(L["fl_y1"]); a1.set_ylim(0, max(live) * 1.24)
    a1.yaxis.set_major_formatter(FuncFormatter(num)); clean(a1)
    a2.bar(yr - .19, nb, width=.38, color=BLUE_M, zorder=3)
    a2.bar(yr + .19, nd, width=.38, color=ORANGE_L, zorder=3)
    for k, (txt, col) in enumerate([(L["fl_new"], BLUE_M), (L["fl_exit"], ORANGE_L)]):
        yy = max(nb) * (1.02 - k * .22)
        a2.add_patch(Rectangle((2003.0, yy - max(nb) * .045), .55, max(nb) * .09,
                               facecolor=col, edgecolor="none", clip_on=False, zorder=6))
        a2.text(2003.85, yy, txt, fontsize=12.5, va="center",
                color=BLUE if k == 0 else ORANGE, weight="bold")
    a2.set_ylim(0, max(nb) * 1.18)
    a2.set_ylabel(L["fl_y2"]); a2.set_xticks(range(2003, 2024, 2))
    a2.yaxis.set_major_formatter(FuncFormatter(num)); clean(a2)
    save(fig, "flows")

# ---------------------------------------------------------------- 4
def f_km():
    km = pd.read_csv(A + "km_survival.csv")
    fig, ax = plt.subplots(figsize=(10.8, 4.4))
    for g, c, lw, lab in [("all", BLUE_D, 3.2, L["km_all"]),
                          ("fta_in_force", BLUE_M, 2.2, L["km_fta"]),
                          ("no_fta", ORANGE, 2.2, L["km_no"])]:
        d = km[km.group == g].sort_values("duration")
        x = np.r_[0, d.duration.values]; y = np.r_[1, d.survival.values] * 100
        ax.step(x, y, where="post", color=c, lw=lw, zorder=3)
        i = min(len(x) - 1, 16)
        ax.text(x[i] + .45, y[i] + (3.0 if g == "fta_in_force" else (-3.6 if g == "no_fta" else -0.4)),
                lab, color=c, fontsize=12.5, weight="bold", va="center")
    d = km[km.group == "all"].set_index("duration").survival
    for t in (1, 2, 5, 10):
        ax.scatter([t], [d[t] * 100], s=46, color=BLUE_D, zorder=5)
        ax.annotate(dec(d[t] * 100, 1) + "%", (t, d[t] * 100), textcoords="offset points",
                    xytext=(8, 10), fontsize=13, color=BLUE_D, weight="bold")
    ax.set_xlim(0, 20.5); ax.set_ylim(0, 100)
    ax.set_xlabel(L["km_x"]); ax.set_ylabel(L["km_y"])
    ax.yaxis.set_major_formatter(PercentFormatter())
    clean(ax, grid="both")
    save(fig, "km")

# ---------------------------------------------------------------- 5
def f_size():
    ks = EDA["km_size"]; cut = EDA["km_size_cut"]
    fig, ax = plt.subplots(figsize=(10.8, 4.4))
    cols = [ORANGE, BLUE_M, BLUE, BLUE_D]
    labs = [L["sz_q1"], L["sz_q2"], L["sz_q3"], L["sz_q4"]]
    ends = []
    for (q, c, lab) in zip(["q1", "q2", "q3", "q4"], cols, labs):
        y = np.r_[100, np.array(ks[q]) * 100]
        x = np.arange(0, len(y))
        ax.step(x, y, where="post", color=c, lw=2.8, zorder=3)
        ends.append((y[-1], c, lab))
    ends.sort()
    prev = -99
    for v, c, lab in ends:                      # push labels apart vertically
        v = max(v, prev + 6.2); prev = v
        ax.plot([12.05, 12.55], [ends[[e[2] for e in ends].index(lab)][0], v],
                color=c, lw=.9, zorder=2)
        ax.text(12.7, v, lab, color=c, fontsize=12.5, weight="bold", va="center")
    for q, c in zip(["q1", "q4"], [ORANGE, BLUE_D]):
        v = ks[q][4] * 100
        ax.scatter([5], [v], s=52, color=c, zorder=5)
        ax.annotate(dec(v, 1) + "%", (5, v), textcoords="offset points", xytext=(6, 11),
                    fontsize=13, weight="bold", color=c)
    ax.axvline(5, color=MUTED, lw=1, ls=(0, (4, 4)), zorder=1)
    ax.set_xlim(0, 16.6); ax.set_ylim(0, 100)
    ax.set_xticks(range(0, 13, 2))
    ax.set_xlabel(L["km_x"]); ax.set_ylabel(L["km_y"])
    ax.yaxis.set_major_formatter(PercentFormatter())
    clean(ax, grid="both")
    save(fig, "size")

# ---------------------------------------------------------------- 6
def f_sectors():
    r = pd.DataFrame(EDA["sectors"])
    r["lab"] = r.sec.map(L["sec"])
    r = r.sort_values("pct5y")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.4, 4.6), sharey=True,
                                 gridspec_kw={"wspace": .06, "width_ratios": [1, 1]})
    top = r.pct5y.idxmax(); bot = r.pct5y.idxmin()
    cols = [ORANGE if i == bot else (BLUE_D if i == top else BLUE_M) for i in r.index]
    b = a1.barh(range(len(r)), r.pct5y, color=cols, height=.66, zorder=3)
    a1.bar_label(b, labels=[dec(v, 1) + "%" for v in r.pct5y], padding=5,
                 fontsize=12, color=BODY)
    a1.set_yticks(range(len(r))); a1.set_yticklabels(r.lab, fontsize=12.5, color=INK)
    a1.set_xlim(0, max(r.pct5y) * 1.30); a1.set_xticks([])
    a1.set_xlabel(L["se_x1"], color=BODY)
    a1.spines[["top", "right", "bottom"]].set_visible(False)
    cols2 = [ORANGE if i == bot else (BLUE_D if i == top else BLUE_L) for i in r.index]
    b2 = a2.barh(range(len(r)), r.value_bn, color=cols2, height=.66, zorder=3)
    a2.bar_label(b2, labels=[num(v) for v in r.value_bn], padding=5, fontsize=12, color=BODY)
    a2.set_xscale("log"); a2.set_xlim(1, r.value_bn.max() * 6)
    from matplotlib.ticker import NullLocator
    a2.xaxis.set_minor_locator(NullLocator()); a2.xaxis.set_major_locator(NullLocator())
    a2.tick_params(which="both", length=0)
    a2.set_xlabel(L["se_x2"], color=BODY)
    a2.spines[["top", "right", "bottom", "left"]].set_visible(False)
    save(fig, "sectors")

# ---------------------------------------------------------------- 7
def f_map():
    r = pd.DataFrame(EDA["sectors"]); r["lab"] = r.sec.map(L["sec"])
    fig, ax = plt.subplots(figsize=(10.8, 5.0))
    mx = np.sqrt(r.value_bn); sz = 60 + mx / mx.max() * 1500
    hi = r.pct5y.median(); vx = r.value_bn.median()
    ax.axvline(vx, color=MUTED, lw=1, ls=(0, (4, 4)), zorder=1)
    ax.axhline(hi, color=MUTED, lw=1, ls=(0, (4, 4)), zorder=1)
    col = [ORANGE if (v > vx and p < hi) else BLUE for v, p in zip(r.value_bn, r.pct5y)]
    ax.scatter(r.value_bn, r.pct5y, s=sz, c=col, alpha=.42, edgecolors=col,
               linewidths=1.6, zorder=3)
    # place labels on alternating sides, then spread them so none collide
    med = np.median(np.log10(r.value_bn))
    pts = sorted(zip(np.log10(r.value_bn), r.pct5y, r.lab, r.value_bn),
                 key=lambda t: t[1])
    yr_span = r.pct5y.max() - r.pct5y.min()
    gap = yr_span * .098
    for side in ("L", "R"):
        grp = [p for p in pts if (p[0] < med) == (side == "L")]
        placed = []
        for lx, ly, lab, val in grp:
            ny = ly
            for py in placed:
                if abs(ny - py) < gap:
                    ny = py + gap
            placed.append(ny); placed.sort()
            rad = (np.sqrt(val) / np.sqrt(r.value_bn).max()) * 0.9 + .35
            dx = -(14 + rad * 9) if side == "L" else (14 + rad * 9)
            ax.annotate(lab, (10 ** lx, ly), xytext=(10 ** lx, ny),
                        textcoords="data",
                        ha="right" if side == "L" else "left", va="center",
                        fontsize=11.5, color=INK, zorder=6,
                        arrowprops=dict(arrowstyle="-", color="#B9CBDA", lw=.9,
                                        shrinkA=2, shrinkB=6))
            ax.annotate("", (10 ** lx, ly), (10 ** lx, ny))
    ax.margins(x=.30)
    ax.set_xscale("log")
    ax.set_xlabel(L["mp_x"]); ax.set_ylabel(L["mp_y"])
    ax.set_xlim(r.value_bn.min() * .16, r.value_bn.max() * 9.0)
    ax.set_ylim(r.pct5y.min() - 3.6, r.pct5y.max() + 4.2)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v)))
    ax.text(0, -.155, L["mp_note"], transform=ax.transAxes, ha="left",
            fontsize=11.5, color=MUTED)
    clean(ax, grid="both")
    save(fig, "map")

# ---------------------------------------------------------------- 8
def f_markets():
    r = pd.DataFrame(CORE["importer_survival"])
    fig, ax = plt.subplots(figsize=(10.8, 4.7))
    sz = 70 + np.sqrt(r.n_spells) / np.sqrt(r.n_spells).max() * 900
    mx, my = r.value_bn.median(), r.pct_5y_plus.median()
    ax.axvline(mx, color=MUTED, lw=1, ls=(0, (4, 4)), zorder=1)
    ax.axhline(my, color=MUTED, lw=1, ls=(0, (4, 4)), zorder=1)
    col = [ORANGE if (v > mx and p < my) else BLUE for v, p in zip(r.value_bn, r.pct_5y_plus)]
    ax.scatter(r.value_bn, r.pct_5y_plus, s=sz, c=col, alpha=.40,
               edgecolors=col, linewidths=1.6, zorder=3)
    for _, q in r.iterrows():
        ax.annotate(q.importer, (q.value_bn, q.pct_5y_plus), ha="center", va="center",
                    fontsize=11.5, color=INK, weight="bold", zorder=5)
    ax.set_xscale("log"); ax.set_xlabel(L["mk_x"]); ax.set_ylabel(L["mk_y"])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v)))
    ax.text(.985, .045, L["mk_note"], transform=ax.transAxes, ha="right",
            fontsize=11.5, color=MUTED)
    clean(ax, grid="both")
    save(fig, "markets")

# ---------------------------------------------------------------- 9
def f_conc():
    c = pd.DataFrame(EDA["conc"]); c = c[c.year <= 2023]
    fig, ax = plt.subplots(figsize=(11.0, 4.3))
    ax.plot(c.year, c.top5_market, color=BLUE_D, lw=3, zorder=4)
    ax.plot(c.year, c.top10_prod, color=ORANGE, lw=3, zorder=4)
    ax.fill_between(c.year, c.top10_prod, c.top5_market,
                    where=(c.top10_prod >= c.top5_market), color=ORANGE, alpha=.07)
    yi = list(c.year).index(2013)
    for ser, col, lab, dy in [(c.top5_market, BLUE_D, L["cc_m"], -16),
                              (c.top10_prod, ORANGE, L["cc_p"], 14)]:
        ax.annotate(lab, (2013, ser.iloc[yi]), textcoords="offset points", xytext=(0, dy),
                    ha="center", color=col, fontsize=12.5, weight="bold")
        for i, dy2 in ((0, 12), (len(ser) - 1, 12)):
            ax.scatter([c.year.iloc[i]], [ser.iloc[i]], s=48, color=col, zorder=5)
        ax.annotate(dec(ser.iloc[0], 0) + "%", (c.year.iloc[0], ser.iloc[0]),
                    textcoords="offset points", xytext=(-4, 10 if col == BLUE_D else -20),
                    ha="center", fontsize=12.5, weight="bold", color=col)
    ax.annotate(dec(c.top5_market.iloc[-1], 0) + "% / " + dec(c.top10_prod.iloc[-1], 0) + "%",
                (2023, 56.6), textcoords="offset points", xytext=(12, 0), ha="left",
                va="center", fontsize=12.5, weight="bold", color=BLUE_D)
    ax.set_xlim(2002.2, 2027.6); ax.set_ylim(0, 76)
    ax.set_xticks(range(2003, 2024, 2)); ax.set_ylabel(L["cc_y"])
    ax.yaxis.set_major_formatter(PercentFormatter())
    clean(ax, grid="y")
    save(fig, "conc")

# ---------------------------------------------------------------- 10
def f_duration():
    d = EDA_dur = CORE["dur_dist"]; tot = CORE["dur_total"]
    dd = np.array(d["d"]); nn = np.array(d["n"])
    cap = 12; x = list(range(1, cap + 1))
    y = [int(nn[dd == i].sum()) for i in x]; y[-1] = int(nn[dd >= cap].sum())
    fig, ax = plt.subplots(figsize=(10.8, 4.1))
    cols = [ORANGE] + [BLUE_M] * (cap - 1)
    b = ax.bar(x, y, color=cols, width=.72, zorder=3)
    ax.bar_label(b, labels=[dec(v / tot * 100, 1) + "%" if v / tot > .022 else ""
                            for v in y], padding=4, fontsize=12, color=BODY)
    ax.set_xticks(x); ax.set_xticklabels([str(i) for i in x[:-1]] + [f"{cap}+"])
    ax.set_xlabel(L["km_x"]); ax.set_ylabel(L["du_y"])
    ax.yaxis.set_major_formatter(FuncFormatter(num))
    ax.annotate(L["du_note"], (1, y[0]), textcoords="offset points", xytext=(46, -30),
                fontsize=13, color=ORANGE, weight="bold",
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.6))
    clean(ax)
    save(fig, "duration")

# ---------------------------------------------------------------- 11
def f_scope():
    s = CORE["scope"]
    items = [(L["sc_eu"], s["eu27_2003_2023"]), (L["sc_uk"], s["uk_2003_2023"]),
             (L["sc_gl"], s["global_2003_2025"])]
    keys = [("episode_years", L["sc_k1"]), ("spells", L["sc_k2"]),
            ("events", L["sc_k3"]), ("families", L["sc_k4"])]
    fig, axes = plt.subplots(1, 4, figsize=(11.4, 3.0))
    for ax, (k, kl) in zip(axes, keys):
        vals = [it[1][k] for it in items][::-1]
        cols = [BLUE_L, BLUE_M, BLUE_D]
        b = ax.barh([0, 1, 2], vals, color=cols, height=.58, zorder=3)
        ax.bar_label(b, labels=[num(v) for v in vals], padding=5, fontsize=12, color=BODY)
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels([it[0] for it in items][::-1] if ax is axes[0] else [],
                           fontsize=12, color=INK)
        ax.set_xlim(0, max(vals) * 1.45); ax.set_xticks([])
        ax.set_title(kl, fontsize=12.5, color=INK, loc="left", pad=8)
        ax.spines[["top", "right", "bottom"]].set_visible(False)
        ax.spines["left"].set_visible(ax is axes[0])
    save(fig, "scope")

# ---------------------------------------------------------------- 12
def f_quality():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.4, 4.0),
                                 gridspec_kw={"width_ratios": [1.15, 1], "wspace": .30})
    cov = QUAL["coverage"]
    keep = [c for c in cov if c["label"] not in ("RCA",)]
    labs = [L["cov"][c["label"]] for c in keep][::-1]
    pct = [c["pct"] for c in keep][::-1]
    cols = [BLUE_M if p >= 94 else ORANGE for p in pct]
    b = a1.barh(range(len(pct)), pct, color=cols, height=.62, zorder=3)
    a1.bar_label(b, labels=[dec(p, 0) + "%" for p in pct], padding=5, fontsize=11.5, color=BODY)
    a1.set_yticks(range(len(labs))); a1.set_yticklabels(labs, fontsize=12, color=INK)
    a1.set_xlim(0, 122); a1.set_xticks([])
    a1.set_title(L["q_a"], fontsize=13, color=INK, loc="left", pad=10)
    a1.spines[["top", "right", "bottom"]].set_visible(False)
    names = [L["q_tar"], L["q_ntm"], L["q_grav"]]
    exact = [QUAL["tariff_exact_pct"], QUAL["ntm6_exact_pct"], 100 - QUAL["gravity_carry_pct"]]
    other = [100 - e for e in exact]
    y = np.arange(3)
    a2.barh(y, exact, color=BLUE_D, height=.5, zorder=3)
    a2.barh(y, other, left=exact, color=ORANGE_L, height=.5, zorder=3)
    for i in range(3):
        a2.text(exact[i] / 2, i, dec(exact[i], 0) + "%", ha="center", va="center",
                color="white", fontsize=12, weight="bold")
        a2.text(exact[i] + other[i] / 2, i, dec(other[i], 0) + "%", ha="center", va="center",
                color="#8A4A22", fontsize=12, weight="bold")
    a2.set_yticks(y); a2.set_yticklabels(names, fontsize=12, color=INK)
    a2.set_xlim(0, 100); a2.set_xticks([]); a2.invert_yaxis()
    for k, (txt, col, x0) in enumerate([(L["q_exact"], BLUE_D, 0), (L["q_other"], ORANGE_L, 46)]):
        a2.add_patch(Rectangle((x0, 2.72), 3.2, .16, facecolor=col, edgecolor="none",
                               clip_on=False, zorder=6))
        a2.text(x0 + 4.6, 2.80, txt, color=BLUE_D if k == 0 else ORANGE,
                fontsize=12, weight="bold", va="center")
    a2.set_title(L["q_b"], fontsize=13, color=INK, loc="left", pad=10)
    a2.spines[["top", "right", "bottom"]].set_visible(False)
    save(fig, "quality")

# ---------------------------------------------------------------- 13
def f_hazard():
    h = pd.read_csv(A + "hazard_baseline.csv")
    h = h[~h.term.str.startswith("duration")].copy()
    h["lab"] = h.term.map(L["haz"])
    h = h.sort_values("hazard_ratio")
    fig, ax = plt.subplots(figsize=(10.4, 4.2))
    y = np.arange(len(h))
    chg = (h.hazard_ratio - 1) * 100
    cols = [BLUE_D if v < -12 else BLUE_M for v in chg]
    ax.barh(y, chg, color=cols, height=.60, zorder=3)
    for i, v in zip(y, chg):
        inside = v < -9
        ax.annotate(dec(v, 1) + "%", (v, i), textcoords="offset points",
                    xytext=(9 if inside else -9, 0), ha="left" if inside else "right",
                    va="center", fontsize=12, color="white" if inside else BODY,
                    weight="bold")
    ax.axvline(0, color=INK, lw=1.4, zorder=4)
    ax.set_yticks(y); ax.set_yticklabels(h.lab, fontsize=12.5, color=INK)
    ax.set_xlim(min(chg) * 1.10, 7)
    ax.set_xticks([]); ax.set_xlabel(L["hz_x"], color=BODY)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    save(fig, "hazard")

# ---------------------------------------------------------------- 14
def f_blocks():
    B = L["blocks"]
    groups = [(L["bg1"], BLUE_D, [B[0], B[1], B[12]]),
              (L["bg2"], ORANGE, [B[2], B[7], B[8], B[10], B[13]]),
              (L["bg3"], BLUE_M, [B[3], B[4], B[5], B[6], B[9]]),
              (L["bg4"], BLUE_L, [B[11], B[14], B[15]])]
    counts = {B[0]: 11, B[1]: 11, B[2]: 4, B[3]: 16, B[4]: 8, B[5]: 4, B[6]: 21,
              B[7]: 7, B[8]: 8, B[9]: 18, B[10]: 9, B[11]: 4, B[12]: 7,
              B[13]: 5, B[14]: 13, B[15]: 12}
    assert sum(counts.values()) == 158, sum(counts.values())
    fig, ax = plt.subplots(figsize=(11.4, 4.0))
    x = 0.0
    for gname, col, items in groups:
        tot = sum(counts[i] for i in items)
        ax.add_patch(Rectangle((x, 2.30), tot, .30, facecolor=col, edgecolor=BG, lw=2))
        ax.text(x + tot / 2, 2.78, f"{gname} · {tot}", ha="center", fontsize=13.5,
                color=col if col != BLUE_L else BLUE, weight="bold")
        xx = x
        for it in items:
            n = counts[it]
            ax.add_patch(Rectangle((xx, 1.10), n, .78, facecolor=col, alpha=.20,
                                   edgecolor=col, lw=1.1))
            ax.text(xx + n / 2, 1.49, str(n), ha="center", va="center", fontsize=12,
                    color=BLUE_D, weight="bold")
            ax.text(xx + n / 2, .92, it, ha="right", va="top", fontsize=11,
                    color=BODY, rotation=34, rotation_mode="anchor")
            xx += n
        x += tot
    ax.set_xlim(-3, 163); ax.set_ylim(-.55, 3.05); ax.axis("off")
    save(fig, "blocks")

FIGS = [f_story, f_timeline, f_flows, f_km, f_size, f_sectors, f_map, f_markets,
        f_conc, f_duration, f_scope, f_quality, f_hazard, f_blocks]
