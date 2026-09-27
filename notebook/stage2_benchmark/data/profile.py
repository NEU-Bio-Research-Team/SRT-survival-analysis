"""Đợt 0.1 - profile the v2 panel and the EU27 base table.

Pass condition (plan §3): the audit numbers reproduce (932,204 rows, 189,830
spells, 112,885 events; B0 146,042 rows / 15,958 events) and there is a
count / missingness / variation table by origin x block.

Writes reports/stage0/0.1_profile.md and the tables as CSV.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from stage2_benchmark.data import base_table  # noqa: E402

OUTDIR = os.path.join(paths.REPORTS, "stage0")
AUDIT = {"rows": 932_204, "spells": 189_830, "events": 112_885,
         "b0_rows": 146_042, "b0_events": 15_958}


def panel_counts() -> dict:
    p = base_table.read_panel(["spell_id", "importer", "year", "gap_filled", "event"])
    members = base_table.eu27_members()
    b0 = p[p["importer"].astype(str).isin(members) & (p["gap_filled"] == 0)
           & p["year"].between(2012, 2024)]
    return {"rows": len(p), "spells": int(p["spell_id"].nunique()),
            "events": int(p["event"].sum()), "b0_rows": len(b0),
            "b0_events": int(b0["event"].sum())}


def block_table(base: pd.DataFrame, reg: dict) -> pd.DataFrame:
    feats = reg["features"]
    rows = []
    for year, g in base.groupby("year"):
        for blk in ["D", "R", "M", "E", "P", "N", "C", "L", "H"]:
            cols = [c for c, s in feats.items() if s["block"] == blk
                    and not s.get("optional")]
            X = g[cols]
            nonnull = X.notna().mean()
            sd = X.std()
            rows.append({"year": year, "block": blk, "rows": len(g),
                         "events_panel": int((g["_y_died"] == 1).sum() and
                                             ((g["_y_E"] == g["year"]) &
                                              (g["_y_died"] == 1)).sum()),
                         "share_any_value": float(X.notna().any(axis=1).mean()),
                         "share_all_values": float(X.notna().all(axis=1).mean()),
                         "mean_nonnull": float(nonnull.mean()),
                         "n_constant_cols": int((sd.fillna(0) < 1e-12).sum()),
                         "n_cols": len(cols)})
    return pd.DataFrame(rows)


def feature_table(base: pd.DataFrame, reg: dict) -> pd.DataFrame:
    rows = []
    for c, s in reg["features"].items():
        x = base[c]
        by = base.assign(nn=x.notna()).groupby("year")["nn"].mean()
        rows.append({"feature": c, "block": s["block"],
                     "null_share_2005_2025": float(x[base["year"] >= 2005].isna().mean()),
                     "null_share_b0": float(x[base["year"].between(2012, 2024)].isna().mean()),
                     "first_year_nonnull_50pct": (int(by[by >= 0.5].index.min())
                                                  if (by >= 0.5).any() else None),
                     "mean": float(x.mean()), "sd": float(x.std()),
                     "min": float(x.min()), "max": float(x.max()),
                     "n_unique": int(x.nunique())})
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    reg = paths.load_yaml("feature_registry.yaml")
    counts = panel_counts()
    base = base_table.load_base()
    bt = block_table(base, reg)
    ft = feature_table(base, reg)
    paths.atomic_write_csv(bt, os.path.join(OUTDIR, "0.1_block_by_origin.csv"))
    paths.atomic_write_csv(ft, os.path.join(OUTDIR, "0.1_features.csv"))

    per_year = (base.assign(ev=(base["_y_E"] == base["year"]) & (base["_y_died"] == 1))
                .groupby("year").agg(rows=("spell_id", "size"), events=("ev", "sum"),
                                     known_start=("meta_known_start", "mean"),
                                     recurrent=("meta_recurrent", "mean"))
                .reset_index())
    ok = {k: counts[k] == v for k, v in AUDIT.items()}
    lines = ["# Đợt 0.1 — Profile panel v2", "",
             f"Panel sha256: `{paths.panel_hash()}`  ",
             f"Code: `{paths.code_commit()}`", "",
             "## Tái lập số audit", "",
             "| Mục | Audit | Tái lập | Khớp |", "|---|---:|---:|:-:|"]
    for k, v in AUDIT.items():
        lines.append(f"| {k} | {v:,} | {counts[k]:,} | {'✅' if ok[k] else '❌'} |")
    lines += ["", f"**0.1 PASS: {all(ok.values())}**", "",
              "## Bảng gốc EU27 (dòng active, 27 nước cố định)", "",
              f"{len(base):,} dòng, năm {base.year.min()}–{base.year.max()}.", "",
              "| origin | rows | events (panel) | known-start | recurrent |",
              "|---|---:|---:|---:|---:|"]
    for _, r in per_year.iterrows():
        lines.append(f"| {r.year} | {r.rows:,} | {int(r.events):,} | "
                     f"{r.known_start:.1%} | {r.recurrent:.1%} |")
    piv = bt.pivot(index="year", columns="block", values="mean_nonnull")
    lines += ["", "## Tỷ lệ có giá trị as-of (trung bình các cột) theo origin × block", "",
              "| origin | " + " | ".join(piv.columns) + " |",
              "|---|" + "---:|" * len(piv.columns)]
    for y, r in piv.iterrows():
        lines.append(f"| {y} | " + " | ".join(f"{v:.0%}" for v in r) + " |")
    lines += ["", "## Từng feature", "",
              "| feature | block | null 2005+ | null B0 | năm đầu ≥50% | sd | unique |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for _, r in ft.iterrows():
        lines.append(f"| {r.feature} | {r.block} | {r.null_share_2005_2025:.1%} | "
                     f"{r.null_share_b0:.1%} | {r.first_year_nonnull_50pct} | "
                     f"{r.sd:.3g} | {r.n_unique:,} |")
    lines += ["", "CSV: `0.1_block_by_origin.csv`, `0.1_features.csv`."]
    with open(os.path.join(OUTDIR, "0.1_profile.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    paths.atomic_write_json(os.path.join(OUTDIR, "0.1_status.json"),
                            {"pass": all(ok.values()), "counts": counts})
    print("\n".join(lines[:16]))
    return all(ok.values())


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
