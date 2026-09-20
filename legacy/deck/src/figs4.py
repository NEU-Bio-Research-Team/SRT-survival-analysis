# -*- coding: utf-8 -*-
"""Two figures: what is inside the final df, and which raw groups built it."""
import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import polars as pl

OUT = "legacy/deck/fig4"
BG, INK, BODY, MUTED = "#F0F4F8", "#16324F", "#33556E", "#8CA0B3"
BLUE, BLUE_D, BLUE_M, BLUE_L = "#2E6E9E", "#143D63", "#6FA3C7", "#BBD3E5"
ORANGE, GRID = "#E8763A", "#DCE5ED"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Carlito", "Open Sans", "DejaVu Sans"],
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "text.color": BODY, "axes.labelcolor": BODY,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#C3D2DE", "axes.linewidth": .9,
    "grid.color": GRID, "grid.linewidth": .9,
    "savefig.bbox": "tight", "savefig.pad_inches": .18, "figure.dpi": 200,
})

# column position ranges (1-based, per the data dictionary) -> block
BLOCKS = [
    ("keys",     [(1, 13), (205, 205)]),
    ("trade",    [(14, 25)]),
    ("feat",     [(172, 204)]),
    ("tariff",   [(26, 29), (137, 146)]),
    ("ntm",      [(101, 104), (147, 171)]),
    ("wdi",      [(30, 45)]),
    ("lpi",      [(46, 57)]),
    ("shocks",   [(105, 122)]),
    ("gravity",  [(73, 93)]),
    ("fta",      [(58, 64)]),
    ("ttb",      [(65, 72)]),
    ("cplx",     [(123, 129)]),
    ("ustar",    [(94, 100), (130, 131)]),
    ("cbam",     [(132, 136)]),
]

LAB = {}
LAB["vi"] = dict(
    blocks={"keys": "Khóa và nhãn sống/chết", "trade": "Thương mại (Comtrade)",
            "feat": "Biến tự tính (lag, cấu trúc)", "tariff": "Thuế nhập khẩu và EVFTA",
            "ntm": "Rào cản phi thuế", "wdi": "Vĩ mô nước nhập",
            "lpi": "Logistics và môi trường", "shocks": "Sốc chung và giá hàng hóa",
            "gravity": "Khoảng cách và thể chế", "fta": "Hiệp định thương mại",
            "ttb": "Phòng vệ thương mại", "cplx": "Độ phức tạp sản phẩm",
            "ustar": "Thuế Mỹ 2025", "cbam": "CBAM"},
    b_title="205 cột, chia theo khối",
    b_unit="cột",
    b_leg=["Từ nguồn ngoài", "Tự tính trong dự án"],
    s_src=[("UN Comtrade", "kim ngạch VN → nước nhập và ← thế giới", "6.656 file"),
           ("WITS TRAINS + EVFTA Annex", "thuế MFN, GSP, lộ trình EVFTA", "3.362 file"),
           ("WITS / UNCTAD NTM", "rào cản phi thuế, HS6 và theo ngành", "8 file"),
           ("World Bank", "WDI, LPI, Pink Sheet", "19 file"),
           ("CEPII Gravity", "khoảng cách, ngôn ngữ, thể chế", "1 file"),
           ("DESTA, TTBD, Atlas", "hiệp định, phòng vệ, độ phức tạp", "5 file")],
    s_mid=["Gom mã HS qua các kỳ sửa đổi\nthành product_family",
           "Ngưỡng 10.000 USD/năm,\nnối lại nếu đứt 1 năm"],
    s_df="stage1_panel.parquet\n\n949.537 dòng × 205 cột",
    s_key="Khóa chung: importer × product_family × year",
    s_grp=["có mã sản phẩm HS", "theo nước × năm"],
    s_foot="Spell dựng từ ngưỡng 10.000 USD/năm, nối lại nếu đứt đúng 1 năm",
    l_row1="Quan hệ sống 5 năm rồi chấm dứt",
    l_row2="Quan hệ vẫn còn sống khi dữ liệu dừng",
    l_ev="event",
    l_out1="event = 1 ở năm cuối",
    l_out2="right_censored = 1",
    l_cont="dữ liệu dừng",
)
LAB["en"] = dict(
    blocks={"keys": "Keys and the alive/dead label", "trade": "Trade (Comtrade)",
            "feat": "Computed features (lags, structure)", "tariff": "Import tariffs and EVFTA",
            "ntm": "Non-tariff measures", "wdi": "Importer macro",
            "lpi": "Logistics and environment", "shocks": "Common shocks and prices",
            "gravity": "Distance and institutions", "fta": "Trade agreements",
            "ttb": "Trade remedies", "cplx": "Product complexity",
            "ustar": "US 2025 tariffs", "cbam": "CBAM"},
    b_title="205 columns, by block",
    b_unit="columns",
    b_leg=["From an outside source", "Computed in the project"],
    s_src=[("UN Comtrade", "VN → importer and importer ← world", "6,656 files"),
           ("WITS TRAINS + EVFTA Annex", "MFN, GSP, the EVFTA schedule", "3,362 files"),
           ("WITS / UNCTAD NTM", "non-tariff measures, HS6 and sector", "8 files"),
           ("World Bank", "WDI, LPI, Pink Sheet", "19 files"),
           ("CEPII Gravity", "distance, language, institutions", "1 file"),
           ("DESTA, TTBD, Atlas", "agreements, remedies, complexity", "5 files")],
    s_mid=["Tie HS codes across revisions\ninto one product_family",
           "USD 10,000 a year,\nrejoin if the break is 1 year"],
    s_df="stage1_panel.parquet\n\n949,537 rows × 205 columns",
    s_key="Shared key: importer × product_family × year",
    s_grp=["carries an HS product code", "importer × year"],
    s_foot="Spells come from the USD 10,000 a year threshold, rejoined if the break is one year",
    l_row1="A relationship that lives 5 years, then ends",
    l_row2="A relationship still alive when the data stops",
    l_ev="event",
    l_out1="event = 1 in the final year",
    l_out2="right_censored = 1",
    l_cont="data stops",
)

LANG, T = "vi", LAB["vi"]
COMPUTED = {"keys", "feat"}


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    p = f"{OUT}/{name}_{LANG}.png"
    fig.savefig(p, dpi=200); plt.close(fig); print("  ", p)


def num(x):
    s = f"{x:,.0f}"
    return s.replace(",", ".") if LANG == "vi" else s


def counts():
    n = len(pl.scan_parquet("data/final/stage1_panel.parquet").collect_schema().names())
    out, seen = [], set()
    for key, spans in BLOCKS:
        c = 0
        for a, b in spans:
            for i in range(a, b + 1):
                assert i not in seen, i
                seen.add(i); c += 1
        out.append((key, c))
    assert len(seen) == n == 205, (len(seen), n)
    return out


# ------------------------------------------------------------ what is inside
def f_blocks():
    data = sorted(counts(), key=lambda r: -r[1])
    fig, ax = plt.subplots(figsize=(11.4, 5.0))
    ys = np.arange(len(data))[::-1]
    for y, (k, c) in zip(ys, data):
        col = BLUE_M if k in COMPUTED else BLUE_D
        ax.barh(y, c, height=.62, color=col, zorder=3)
        ax.text(-0.8, y, T["blocks"][k], ha="right", va="center", fontsize=13, color=INK)
        ax.text(c + 0.7, y, str(c), ha="left", va="center", fontsize=12.5,
                color=col, weight="bold")
    hs = [Rectangle((0, 0), 1, 1, color=BLUE_D), Rectangle((0, 0), 1, 1, color=BLUE_M)]
    ax.legend(hs, T["b_leg"], frameon=False, loc="lower right", handlelength=1.2,
              fontsize=12.5, bbox_to_anchor=(1.0, .0))
    ax.set_xlim(0, 40); ax.set_ylim(-.8, len(data) - .3)
    ax.set_yticks([]); ax.set_xticks([])
    for s in ax.spines.values(): s.set_visible(False)
    save(fig, "blocks")


# --------------------------------------------------------------- raw sources
def chip(ax, x, y, w, h, lines, fc, ec, tc, sizes, lw=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.6",
                                facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3))


def f_sources():
    """Six raw groups -> the df. Two arrows only, so nothing crosses."""
    fig, ax = plt.subplots(figsize=(12.2, 4.0))
    ax.set_xlim(0, 100); ax.set_ylim(25, 100); ax.axis("off")

    sx, sw, sh, gap = 0.5, 30.0, 9.4, 2.6
    top = 98.0
    ys = []
    for i, (name, what, n) in enumerate(T["s_src"]):
        y = top - i * (sh + gap) - sh
        ys.append(y + sh / 2)
        ax.add_patch(FancyBboxPatch((sx, y), sw, sh, boxstyle="round,pad=0.3,rounding_size=0.8",
                                    facecolor="#FFFFFF", edgecolor=BLUE_M, lw=1.2, zorder=3))
        ax.text(sx + 1.4, y + sh * .70, name, ha="left", va="center", fontsize=11.2,
                color=INK, weight="bold", zorder=4)
        ax.text(sx + 1.4, y + sh * .27, what, ha="left", va="center", fontsize=10,
                color=BODY, zorder=4)
        ax.text(sx + sw - 1.4, y + sh * .70, n, ha="right", va="center", fontsize=9.4,
                color=MUTED, zorder=4)

    # two brackets: the HS-coded sources, and the country-level ones
    bx = sx + sw + 1.6
    grp = [(ys[0], ys[2]), (ys[3], ys[5])]
    ctr = []
    for (hi, lo), lab in zip(grp, T["s_grp"]):
        c = (hi + lo) / 2
        ctr.append(c)
        ax.plot([bx, bx], [lo - 1.0, hi + 1.0], color=BLUE_M, lw=1.4, zorder=2)
        for e in (lo - 1.0, hi + 1.0):
            ax.plot([bx - 1.0, bx], [e, e], color=BLUE_M, lw=1.4, zorder=2)
        ax.text(bx + 1.6, hi + 4.2, lab, ha="left", va="center", fontsize=9.8,
                color=MUTED, style="italic", zorder=4)

    # the one shared preprocessing step, on the HS branch only
    mx, mw, mh = 41.0, 24.0, 12.0
    my = ctr[0] - mh / 2
    ax.add_patch(FancyBboxPatch((mx, my), mw, mh, boxstyle="round,pad=0.3,rounding_size=0.8",
                                facecolor=BLUE_L, edgecolor=BLUE_L, lw=1.2, zorder=3))
    ax.text(mx + mw / 2, my + mh / 2, T["s_mid"][0], ha="center", va="center", fontsize=10.6,
            color=BLUE_D, zorder=4, linespacing=1.5)

    dx, dw, dh = 72.0, 27.5, 18.0
    dy = (ctr[0] + ctr[1]) / 2 - dh / 2
    ax.add_patch(FancyBboxPatch((dx, dy), dw, dh, boxstyle="round,pad=0.3,rounding_size=0.8",
                                facecolor=BLUE_D, edgecolor=BLUE_D, lw=1.2, zorder=3))
    ax.text(dx + dw / 2, dy + dh / 2, T["s_df"], ha="center", va="center", fontsize=12,
            color="white", weight="bold", zorder=4, linespacing=1.6)

    A = dict(arrowstyle="-|>", mutation_scale=13, zorder=2)
    ax.add_patch(FancyArrowPatch((bx + 1.0, ctr[0]), (mx - 1.0, ctr[0]), color=BLUE, lw=1.6, **A))
    ax.add_patch(FancyArrowPatch((mx + mw + 1.0, ctr[0]), (dx - 1.0, dy + dh * .72),
                                 color=BLUE, lw=1.6, **A))
    ax.add_patch(FancyArrowPatch((bx + 1.0, ctr[1]), (dx - 1.0, dy + dh * .28),
                                 color=BLUE, lw=1.6, **A))

    ax.text(dx + dw / 2, dy - 4.2, T["s_key"], ha="center", va="center", fontsize=11,
            color=BLUE, weight="bold")
    ax.text(dx + dw / 2, dy - 9.0, T["s_foot"], ha="center", va="center", fontsize=9.8,
            color=MUTED)
    save(fig, "sources")


# ------------------------------------------------------------ target label
def f_labels():
    """What y looks like: one binary per year, and what censoring means."""
    fig, ax = plt.subplots(figsize=(11.4, 3.4))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    cw, cg, ch = 10.6, 1.5, 15.0

    def row(y, head, years, evs, censored, outcome):
        ax.text(0.5, y + ch + 9.5, head, ha="left", va="center", fontsize=12.5,
                color=INK, weight="bold")
        for i, (yr, e) in enumerate(zip(years, evs)):
            x = 0.5 + i * (cw + cg)
            hit = e == 1
            ax.add_patch(FancyBboxPatch((x, y), cw, ch, boxstyle="round,pad=0.2,rounding_size=0.6",
                                        facecolor=ORANGE if hit else "#FFFFFF",
                                        edgecolor=ORANGE if hit else BLUE_M, lw=1.3, zorder=3))
            ax.text(x + cw / 2, y + ch / 2, str(yr), ha="center", va="center", fontsize=11,
                    color="white" if hit else BODY, weight="bold" if hit else "normal", zorder=4)
            ax.text(x + cw / 2, y - 6.0, str(e), ha="center", va="center", fontsize=13,
                    color=ORANGE if hit else MUTED, weight="bold", zorder=4)
        xe = 0.5 + len(years) * (cw + cg)
        if censored:
            ax.plot([xe - 0.6, xe + 5.2], [y + ch / 2, y + ch / 2], color=BLUE_M, lw=1.6,
                    ls=(0, (3, 2.6)), zorder=2)
            ax.text(xe + 6.0, y + ch / 2, T["l_cont"], ha="left", va="center", fontsize=10,
                    color=MUTED, style="italic")
        ax.text(0.5 - 1.0, y - 6.0, T["l_ev"], ha="right", va="center", fontsize=10,
                color=MUTED, style="italic")
        ax.text(78.0, y + ch / 2, outcome, ha="left", va="center", fontsize=12,
                color=ORANGE if not censored else BLUE_D, weight="bold")

    row(58, T["l_row1"], [2018, 2019, 2020, 2021, 2022], [0, 0, 0, 0, 1], False, T["l_out1"])
    row(12, T["l_row2"], [2021, 2022, 2023, 2024], [0, 0, 0, 0], True, T["l_out2"])
    save(fig, "labels")


if __name__ == "__main__":
    for lg in ("vi", "en"):
        LANG = lg; T = LAB[lg]
        globals()["LANG"] = lg; globals()["T"] = LAB[lg]
        print(lg); f_blocks(); f_sources(); f_labels()
