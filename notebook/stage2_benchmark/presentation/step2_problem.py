"""Step 2 — the characteristic shape of the problem (descriptive, no model).

Spell-level plots use data/interim/spells.csv restricted to EU27. Origin-level
(annual hazard) plots use the base table read at the end of the data (C = 2025),
i.e. exactly the D-view rows: an origin counts only if its next year is
confirmable, so an unconfirmed exit is never scored as survival.

Run from notebook/:
    $PY -m stage2_benchmark.presentation.step2_problem
"""

from __future__ import annotations

import json
import os

from stage2_benchmark.presentation.common import (
    EU27, EVENT, INK, INK2, MUTED, SEQ, SLOT, TAB, TEST_ORIGIN, fmt_int, plt,
    save, write_csv)
from stage2_benchmark import paths
from stage2_benchmark.data import views as V

import numpy as np
import pandas as pd

HS_SECTIONS = [  # (first HS2, last HS2, label)
    (1, 5, "Animal products"), (6, 14, "Vegetable products"), (15, 15, "Fats & oils"),
    (16, 24, "Prepared food"), (25, 27, "Mineral products"), (28, 38, "Chemicals"),
    (39, 40, "Plastics & rubber"), (41, 43, "Hides & leather"), (44, 46, "Wood"),
    (47, 49, "Paper"), (50, 63, "Textiles & apparel"), (64, 67, "Footwear & headgear"),
    (68, 70, "Stone & glass"), (71, 71, "Precious metals"), (72, 83, "Base metals"),
    (84, 85, "Machinery & electrical"), (86, 89, "Transport equipment"),
    (90, 92, "Instruments"), (93, 93, "Arms"), (94, 96, "Miscellaneous manuf."),
    (97, 99, "Art & other")]


def section_of(hs2) -> str:
    h = int(hs2)
    for lo, hi, lab in HS_SECTIONS:
        if lo <= h <= hi:
            return lab
    return "Other"


def km(duration, event):
    """Product-limit estimate on integer years; returns t, S, at-risk, events."""
    d = np.asarray(duration, dtype=int)
    e = np.asarray(event, dtype=int)
    ts = np.arange(1, d.max() + 1)
    S, s, risk, evs = [1.0], 1.0, [len(d)], [0]
    for t in ts:
        n = int((d >= t).sum())
        k = int(((d == t) & (e == 1)).sum())
        s *= 1 - k / n if n else 1
        S.append(s)
        risk.append(n)
        evs.append(k)
    return np.r_[0, ts], np.array(S), np.array(risk), np.array(evs)


def binom_ci(k, n):
    p = k / n
    se = np.sqrt(p * (1 - p) / n)
    return p, p - 1.96 * se, p + 1.96 * se


def load():
    s = pd.read_csv(os.path.join(paths.INTERIM, "spells.csv"))
    s = s[s["importer"].isin(EU27)].copy()
    s["known_start"] = (s["left_trunc"] == 0).astype(int)
    s["hs2"] = s["product_family"].str.split("_").str[1].str[:2]
    b = pd.read_parquet(os.path.join(paths.VIEWS, "base_eu27.parquet"))
    d = V.view(b, (2005, 2023), 2025, task="D")   # confirmed 1-year outcomes
    d["section"] = d["hs2"].astype(str).map(section_of)
    return s, b, d


# ------------------------------------------------------------------ figures
def entry_rows(b):
    """One row per spell at its first active year, re-censored at C = 2025 with
    the benchmark rule (H = C - g): the landmark-at-entry view. Using the raw
    spell length instead would count a spell that began in 2025 as a survivor
    of year 1 although its exit could not yet be confirmed."""
    L = V.view(b, (2003, 2023), 2025, task="L")
    return L[(L["age_obs"] == 1) & (L["known_start"] == 1)].copy()


def fig_km(s, e):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"wspace": 0.25})
    rows = []
    groups = (("all new spells", e, SLOT[0], "o"),
              ("first spell of the relation", e[e["meta_recurrent"] == 0], SLOT[1], "s"),
              ("re-entry spell", e[e["meta_recurrent"] == 1], SLOT[2], "^"))
    for lab, sub, c, m in groups:
        t, S, risk, ev = km(sub["duration"], sub["event"])
        ax[0].step(t, S, where="post", color=c)
        ax[0].plot(t[1:], S[1:], m, color=c, ms=5, label=f"{lab} (n = {fmt_int(len(sub))})")
        rows += [{"group": lab, "t": int(a), "S": round(float(b_), 4), "at_risk": int(r),
                  "events": int(k)} for a, b_, r, k in zip(t, S, risk, ev)]
        if lab == "all new spells":
            S_all, t_all = S, t
    for u in (1, 2, 5, 10):
        ax[0].annotate(f"S({u}) = {S_all[u]:.2f}", (u, S_all[u]), (u + 0.8, S_all[u] + 0.1),
                       fontsize=8.5, color=INK2,
                       arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
    med = t_all[np.argmax(S_all <= 0.5)]
    ax[0].text(9.5, 0.5, f"median lifetime of a new spell: {med} years", fontsize=9, color=INK)
    ax[0].set_xticks(range(0, 21, 2))
    ax[0].set_ylim(0, 1.02)
    ax[0].set_xlim(0, 21)
    ax[0].set_xlabel("years since the relationship (re)started")
    ax[0].set_ylabel("S(t): share still alive")
    ax[0].set_title("Kaplan–Meier survival of new VN → EU27 spells")
    ax[0].legend(loc="upper right", fontsize=8.5)
    ax[0].text(0.3, 0.04, "entries 2003–2023, known start; outcomes read at 2025\n"
               "with the benchmark's censoring rule (H = C − 1)", fontsize=8, color=INK2)
    # observed spell lengths, exit vs still alive / censored
    k = s[s["known_start"] == 1]
    cnt = k.groupby(["duration", "event"]).size().unstack(fill_value=0).reindex(
        range(1, 25), fill_value=0)
    ax[1].bar(cnt.index, cnt[1], color=EVENT, width=0.78, label="ended by a confirmed exit",
              zorder=3)
    ax[1].bar(cnt.index, cnt[0], bottom=cnt[1], color=MUTED, width=0.78,
              label="still alive / censored", zorder=3)
    ax[1].text(3, cnt.sum(axis=1).max() * 0.78,
               f"{1 - S_all[1]:.0%} of new spells exit after their first year\n"
               f"(1 − S(1), left panel)", fontsize=9.5, color=INK)
    ax[1].set_xlabel("observed spell length (active years, gap years included)")
    ax[1].set_ylabel("number of spells (known start)")
    ax[1].set_title("Most relationships are short-lived")
    ax[1].legend(loc="upper right", fontsize=8.5)
    save(fig, "10_km_and_spell_lengths.png")
    write_csv(pd.DataFrame(rows), TAB, "km_new_spells.csv")


def fig_hazard_age(d):
    k = d[d["known_start"] == 1].copy()
    k["age"] = k["age_obs"].clip(upper=15).astype(int)
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    rows = []
    for lab, sub, c, m in (("first spell of the relation", k[k["meta_recurrent"] == 0], SLOT[0], "o"),
                           ("re-entry spell (relation died before)", k[k["meta_recurrent"] == 1], SLOT[1], "s")):
        g = sub.groupby("age")["y"].agg(["sum", "count"])
        g = g[g["count"] >= 100]
        p, lo, hi = binom_ci(g["sum"], g["count"])
        ax.fill_between(g.index, lo, hi, color=c, alpha=0.15, lw=0)
        ax.plot(g.index, p, color=c, marker=m, ms=6, label=lab)
        rows += [{"group": lab, "age": int(a), "exits": int(r["sum"]), "at_risk": int(r["count"]),
                  "hazard": round(float(r["sum"] / r["count"]), 4)} for a, r in g.iterrows()]
    ax.set_xticks(range(1, 16), [str(i) for i in range(1, 15)] + ["15+"])
    ax.set_ylim(0, None)
    ax.set_xlabel("spell age at origin (years active so far)")
    ax.set_ylabel("P(exit next year | alive now)")
    ax.set_title("Negative duration dependence: the annual exit hazard falls with age")
    ax.legend(fontsize=9)
    ax.text(15, ax.get_ylim()[1] * 0.93, "origins 2005–2023, known start, outcomes read at 2025\n"
            "band = 95% binomial CI; ages with < 100 origins hidden",
            ha="right", va="top", fontsize=8.3, color=INK2)
    save(fig, "11_hazard_by_age.png")
    write_csv(pd.DataFrame(rows), TAB, "hazard_by_age.csv")


def fig_km_initial(e):
    k = e.copy()
    k["q"] = pd.qcut(k["import_value_usd"], 4, labels=False)
    edges = k.groupby("q")["import_value_usd"].agg(["min", "max"])
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    rows = []
    for q in range(4):
        sub = k[k["q"] == q]
        t, S, risk, ev = km(sub["duration"], sub["event"])
        lab = (f"Q{q + 1}: first-year value {edges.loc[q, 'min'] / 1e3:,.0f}k–"
               f"{edges.loc[q, 'max'] / 1e3:,.0f}k USD")
        if q == 3:
            lab = f"Q4: first-year value > {edges.loc[q, 'min'] / 1e3:,.0f}k USD"
        ax.step(t, S, where="post", color=SEQ[q + 1], label=f"{lab} (n = {fmt_int(len(sub))})")
        rows += [{"quartile": f"Q{q + 1}", "t": int(a), "S": round(float(b_), 4),
                  "at_risk": int(r)} for a, b_, r in zip(t, S, risk)]
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("years since the relationship (re)started")
    ax.set_ylabel("S(t)")
    ax.set_title("Relationships that start bigger survive longer (initial-size gradient)")
    ax.legend(fontsize=8.5, loc="upper right")
    save(fig, "12_km_by_initial_value.png")
    write_csv(pd.DataFrame(rows), TAB, "km_by_initial_value.csv")


def fig_calendar(b, d):
    act = b[b["year"] >= 2005].groupby("year").size()
    g = d.groupby("year")["y"].agg(["sum", "count"])
    p, lo, hi = binom_ci(g["sum"], g["count"])
    fig, ax = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True, gridspec_kw={"hspace": 0.3})
    ax[0].bar(act.index, act.values, color=SLOT[0], width=0.7, zorder=3)
    ax[0].set_ylabel("active relations")
    ax[0].set_title("Active VN → EU27 importer × family relations per year")
    ax[1].fill_between(g.index, lo, hi, color=SLOT[0], alpha=0.15, lw=0)
    ax[1].plot(g.index, p, color=SLOT[0], marker="o", ms=5)
    for f, t in TEST_ORIGIN.items():
        ax[1].axvspan(t - 0.4, t + 0.4, color=SEQ[0], zorder=0)
    ax[1].text(2020, p.max() * 1.07, "test origins F1 · F2 · F3", ha="center", fontsize=8.3,
               color=INK2)
    ax[1].axvline(2020.6, color=INK, lw=0.8)
    ax[1].text(2020.7, 0.02, "EVFTA in force (Aug 2020)", fontsize=8.3, color=INK)
    ax[1].set_ylabel("one-year exit rate")
    ax[1].set_ylim(0, p.max() * 1.15)
    ax[1].set_title("Annual exit rate by origin year (confirmed outcomes; 2024–25 not yet confirmable)")
    ax[1].set_xticks(range(2005, 2026, 2))
    save(fig, "13_calendar_activity_and_exit_rate.png")
    out = pd.DataFrame({"year": act.index, "active_relations": act.values}).merge(
        pd.DataFrame({"year": g.index, "exits_next_year": g["sum"].values,
                      "origins_confirmed": g["count"].values,
                      "exit_rate": np.round(p.values, 4)}), how="left")
    write_csv(out, TAB, "calendar_exit_rate.csv")


def fig_heterogeneity(d):
    fig, ax = plt.subplots(1, 2, figsize=(13, 7.2), gridspec_kw={"wspace": 0.55})
    overall = d["y"].mean()
    out = []
    for a, key, title in ((ax[0], "importer", "by importer"),
                          (ax[1], "section", "by HS section of the product")):
        g = d.groupby(key)["y"].agg(["sum", "count"])
        g = g[g["count"] >= 200]
        g = g.assign(rate=g["sum"] / g["count"]).sort_values("rate")
        p, lo, hi = binom_ci(g["sum"], g["count"])
        yy = np.arange(len(g))
        a.hlines(yy, lo, hi, color=SEQ[1], lw=2)
        a.plot(p, yy, "o", color=SLOT[0], ms=6)
        a.axvline(overall, color=INK, lw=0.8)
        a.set_yticks(yy, [f"{i}  (n = {fmt_int(n)})" for i, n in zip(g.index, g["count"])],
                     fontsize=8.5)
        a.set_xlabel("one-year exit rate (95% CI)")
        a.set_title(f"Exit risk {title}")
        a.grid(axis="y", visible=False)
        out.append(pd.DataFrame({"dimension": key, "group": g.index, "exits": g["sum"].values,
                                 "origins": g["count"].values, "exit_rate": np.round(p.values, 4)}))
    ax[0].text(overall, -1.6, f"pooled {overall:.3f}", fontsize=8.3, color=INK, ha="center")
    save(fig, "14_exit_rate_heterogeneity.png")
    write_csv(pd.concat(out), TAB, "exit_rate_by_importer_and_section.csv")


def fig_size_and_age(d):
    """Hazard surface: current trade value decile × age (the two strongest signals)."""
    k = d[d["known_start"] == 1].copy()
    k["age"] = k["age_obs"].clip(upper=8).astype(int)
    k["vq"] = pd.qcut(k["log_value"], 5, labels=[f"Q{i}" for i in range(1, 6)])
    t = k.pivot_table(index="vq", columns="age", values="y", aggfunc="mean", observed=True)
    n = k.pivot_table(index="vq", columns="age", values="y", aggfunc="size", observed=True)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", ["#f0efec"] + SEQ[1:])
    im = ax.imshow(t.values, cmap=cmap, aspect="auto", origin="lower")
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = t.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5,
                    color="white" if v > t.values.max() * 0.6 else INK)
    ax.set_xticks(range(t.shape[1]), [str(c) if c < 8 else "8+" for c in t.columns])
    ax.set_yticks(range(t.shape[0]), [f"{q} value" for q in t.index])
    ax.set_xlabel("spell age at origin")
    ax.set_title("Exit hazard falls with both current size (log_value quintile) and age")
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="P(exit next year)", shrink=0.85)
    save(fig, "15_hazard_value_x_age.png")
    long = t.stack().rename("hazard").reset_index().merge(
        n.stack().rename("origins").reset_index())
    write_csv(long, TAB, "hazard_value_x_age.csv")


def fig_target_definition():
    j = json.load(open(os.path.join(paths.REPORTS, "batch3", "target_variants_build.json")))
    r = pd.DataFrame([{"variant": k, "threshold_usd": v["threshold"], "gap": v["gap"],
                       "exit_rate_b0": v["exit_rate_b0"], "one_year_spell_share": v["one_year_spell_share"],
                       "spells": v["spells"], "rows_b0": v["rows_b0"]} for k, v in j.items()])
    r = r.sort_values(["gap", "threshold_usd"])
    write_csv(r, TAB, "target_definition_variants.csv")
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"wspace": 0.45})
    lab = [f"{int(t / 1e3)}k, gap {g}" for t, g in zip(r["threshold_usd"], r["gap"])]
    base = [(t == 10000 and g == 1) for t, g in zip(r["threshold_usd"], r["gap"])]
    cols = [SLOT[1] if b_ else SLOT[0] for b_ in base]
    for a, c, ttl in ((ax[0], "exit_rate_b0", "one-year exit rate (B0 origins)"),
                      (ax[1], "one_year_spell_share", "share of spells lasting 1 year")):
        yy = np.arange(len(r))
        a.barh(yy, r[c], color=cols, height=0.6, zorder=3)
        for y_, v in zip(yy, r[c]):
            a.text(v + 0.005, y_, f"{v:.1%}", va="center", fontsize=8.5, color=INK2)
        a.set_yticks(yy, lab)
        a.set_title(ttl)
        a.set_xlim(0, r[c].max() * 1.25)
        a.grid(axis="y", visible=False)
    fig.suptitle("The label depends on the definition: threshold and gap tolerance "
                 "(orange = the benchmark target)", x=0.06, ha="left", fontsize=12,
                 fontweight="semibold", color=INK, y=1.03)
    save(fig, "16_target_definition_sensitivity.png")


def summary(s, d):
    k = s[s["known_start"] == 1]
    rows = [
        ("EU27 spells", len(s)),
        ("… with known start", len(k)),
        ("… left-truncated (start not observed: importer's first filed year, or HS switch)", int((s["known_start"] == 0).sum())),
        ("spells ending in a confirmed exit", int(s["event"].sum())),
        ("share of spells censored", round(1 - s["event"].mean(), 4)),
        ("share of known-start spells observed for exactly 1 active year (incl. censored)", round((k["duration"] == 1).mean(), 4)),
        ("re-entry spells (relation died before)", int((s.sort_values("start_year").groupby(["importer", "product_family"]).cumcount() > 0).sum())),
        ("origins with confirmed 1-year outcome (2005–2023)", len(d)),
        ("pooled one-year exit rate", round(d["y"].mean(), 4)),
        ("importers", s["importer"].nunique()),
        ("product families", s["product_family"].nunique()),
    ]
    out = pd.DataFrame(rows, columns=["quantity", "value"], dtype=object)
    write_csv(out, TAB, "problem_summary.csv")


def main():
    s, b, d = load()
    e = entry_rows(b)
    summary(s, d)
    fig_km(s, e)
    fig_hazard_age(d)
    fig_km_initial(e)
    fig_calendar(b, d)
    fig_heterogeneity(d)
    fig_size_and_age(d)
    fig_target_definition()


if __name__ == "__main__":
    main()
