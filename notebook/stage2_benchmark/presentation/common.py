"""Shared paths, names and plot style for the presentation material.

Everything under presentation/ only READS the benchmark's inputs and outputs
(panel, raw files, base table, per-cell predictions); nothing here refits a
model or rewrites a report.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from stage2_benchmark import paths  # noqa: E402,F401  (thread limits first)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = os.path.join(HERE, "out")
FIG = os.path.join(OUT, "figures")
CAP = os.path.join(OUT, "captures")
TAB = os.path.join(OUT, "tables")
for _d in (FIG, CAP, TAB):
    os.makedirs(_d, exist_ok=True)

EU27 = ["AUT", "BEL", "BGR", "CYP", "CZE", "DEU", "DNK", "ESP", "EST", "FIN",
        "FRA", "GRC", "HRV", "HUN", "IRL", "ITA", "LTU", "LUX", "LVA", "MLT",
        "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "SWE"]

# the worked example: one relation that shows every spell rule at once
EXAMPLE_IMPORTER = "AUT"
EXAMPLE_FAMILY = "H0_080110"
EXAMPLE_RELATION = f"{EXAMPLE_IMPORTER}|{EXAMPLE_FAMILY}"

FOLDS = ["F1", "F2", "F3"]
TEST_ORIGIN = {"F1": 2019, "F2": 2020, "F3": 2021}

NAMES = {"D00": "Age-only", "D01": "Cloglog", "D04": "Flexible cloglog",
         "D05": "Boosted hazard", "D06": "MLP hazard",
         "L00": "Kaplan–Meier", "L02": "CoxNet", "L05": "RSF",
         "L07": "DeepSurv", "L08": "CoxTime", "L09": "DeepHit"}
D_MODELS = ["D01", "D04", "D05", "D06"]
L_MODELS = ["L02", "L05", "L07", "L08", "L09"]

# Validated categorical palette (dataviz reference instance, light mode), in
# its fixed order. Colour follows the model, never its rank.
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300",
        "#4a3aa7", "#e34948"]
COLOR = {"D01": SLOT[0], "D04": SLOT[1], "D05": SLOT[2], "D06": SLOT[3],
         "L02": SLOT[0], "L05": SLOT[1], "L07": SLOT[2], "L08": SLOT[3],
         "L09": SLOT[4]}
MARKER = {"D01": "o", "D04": "s", "D05": "^", "D06": "D",
          "L02": "o", "L05": "s", "L07": "^", "L08": "D", "L09": "v"}
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
SEQ = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]   # blue ramp
EVENT = "#d03b3b"      # a confirmed exit (status: critical)
CENSOR = MUTED         # a censored end

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "figure.dpi": 110, "savefig.dpi": 160,
    "font.family": "DejaVu Sans", "font.size": 10.5,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2,
    "axes.titlesize": 12, "axes.titleweight": "semibold", "axes.titlecolor": INK,
    "axes.titlelocation": "left", "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "legend.frameon": False, "legend.fontsize": 9.5, "lines.linewidth": 2,
})


def save(fig, name: str) -> str:
    path = os.path.join(FIG, name)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("  wrote", os.path.relpath(path, HERE))
    return path


def write_csv(df, folder: str, name: str, **kw) -> str:
    path = os.path.join(folder, name)
    df.to_csv(path, index=kw.pop("index", False), **kw)
    print("  wrote", os.path.relpath(path, HERE))
    return path


def fmt_int(x) -> str:
    return f"{int(x):,}"
