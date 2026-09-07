"""Step 11: does the panel actually support a hazard model? A validation run.

This is not the paper's estimation. It is the check that should happen before
anyone builds on the panel: that the counting-process columns are coherent, that
the covariates carry signal rather than noise, and that a duration model can be
fitted at all. A dataset that has never had a model run against it has not been
tested, only described.

Two things are estimated:

  1. **Kaplan-Meier**, overall and split by whether a trade agreement was in
     force. Non-parametric, assumption-free, and it exposes the shape the
     descriptive tables keep pointing at - the enormous first-year mortality.

  2. **A discrete-time hazard model** with a complementary log-log link. Cox is
     the reflex here and it is the wrong reflex for this panel: durations are
     whole years, so ties are not incidental but universal, and Cox's partial
     likelihood then leans entirely on a tie-breaking approximation. The
     grouped-data proportional hazards model (Prentice-Gloeckner; cloglog on
     annual episodes) is the same proportional-hazards assumption applied to
     data that is genuinely interval-censored, which is what annual trade
     filings are. Its coefficients read as log hazard ratios, exactly as Cox's
     do.

Duration enters as a set of dummies rather than a smooth term, so the baseline
hazard stays unrestricted - which matters when more than half the mass is at
one year and no smooth function would fit it.

Estimation is Newton-Raphson (IRLS) in numpy: no new dependency, and on this
panel it converges in a handful of iterations.

Output: data/interim/km_survival.csv, data/interim/hazard_baseline.csv
"""

import csv
import math
import os
import sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "interim")
OUT = os.path.join(HERE, "analysis")   # model results, not data
PANEL = os.path.join(DATA, "panel_final.csv")
MAX_DURATION_DUMMY = 10        # 10+ collapses into one category


def load():
    """Only the columns the model needs - the panel is 600 MB wide."""
    cols = ["spell_id", "importer", "year", "t_stop", "event",
            "tariff_rate", "fta_in_force", "dist", "importer_gdp_usd",
            "pci", "rca", "import_value_usd", "partner_share_pct"]
    rows = defaultdict(list)
    n = 0
    with open(PANEL, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            n += 1
            for c in cols:
                rows[c].append(r[c])
    print(f"  read {n:,} episodes")
    return rows, n


def to_float(values, fill=np.nan):
    out = np.empty(len(values))
    for i, v in enumerate(values):
        try:
            out[i] = float(v)
        except (TypeError, ValueError):
            out[i] = fill
    return out


def kaplan_meier(duration, event, label, writer):
    """S(t) by the product-limit estimator, on spells not episodes."""
    at_risk = len(duration)
    surv = 1.0
    order = sorted(set(duration))
    for t in order:
        d = int(((duration == t) & (event == 1)).sum())
        c = int(((duration == t) & (event == 0)).sum())
        if at_risk <= 0:
            break
        if d:
            surv *= (1 - d / at_risk)
        writer.writerow({"group": label, "duration": t, "at_risk": at_risk,
                         "deaths": d, "censored": c,
                         "survival": round(surv, 6)})
        at_risk -= (d + c)
    return surv


def cloglog_fit(X, y, names, max_iter=40, tol=1e-8):
    """Grouped-data proportional hazards by Newton-Raphson.

    h = 1 - exp(-exp(Xb)); the log-likelihood is Bernoulli in y. The Hessian is
    formed explicitly - with a few dozen columns that is cheap, and it gives the
    standard errors for free.
    """
    n, k = X.shape
    beta = np.zeros(k)
    for it in range(max_iter):
        eta = np.clip(X @ beta, -30, 10)
        exp_eta = np.exp(eta)
        h = -np.expm1(-exp_eta)                 # 1 - exp(-exp(eta)), stable
        h = np.clip(h, 1e-12, 1 - 1e-12)
        # d h / d eta = exp(eta) * exp(-exp(eta)) = exp(eta) * (1 - h)
        dh = exp_eta * (1 - h)
        w = dh ** 2 / (h * (1 - h))
        z = (y - h) * dh / (h * (1 - h))
        XtW = X.T * w
        H = XtW @ X
        g = X.T @ z
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, g, rcond=None)[0]
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    eta = np.clip(X @ beta, -30, 10)
    h = np.clip(-np.expm1(-np.exp(eta)), 1e-12, 1 - 1e-12)
    ll = float(np.sum(y * np.log(h) + (1 - y) * np.log(1 - h)))
    cov = np.linalg.pinv(H)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    return beta, se, ll, it + 1


def main():
    print("Loading the panel")
    raw, n = load()

    dur = to_float(raw["t_stop"])
    ev = to_float(raw["event"])
    spell = raw["spell_id"]

    # --- Kaplan-Meier, on spells: the last episode of each spell carries its
    # total duration and whether it ended in death.
    print("\nKaplan-Meier")
    last = {}
    fta_last = {}
    fta = to_float(raw["fta_in_force"], 0.0)
    for i, sid in enumerate(spell):
        if sid not in last or dur[i] > last[sid][0]:
            last[sid] = (dur[i], ev[i])
            fta_last[sid] = fta[i]
    d_all = np.array([v[0] for v in last.values()])
    e_all = np.array([v[1] for v in last.values()])
    f_all = np.array([fta_last[s] for s in last])
    print(f"  {len(d_all):,} spells | {int(e_all.sum()):,} deaths | "
          f"{int((e_all == 0).sum()):,} censored")

    path = os.path.join(OUT, "km_survival.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["group", "duration", "at_risk",
                                          "deaths", "censored", "survival"])
        w.writeheader()
        kaplan_meier(d_all, e_all, "all", w)
        kaplan_meier(d_all[f_all == 1], e_all[f_all == 1], "fta_in_force", w)
        kaplan_meier(d_all[f_all == 0], e_all[f_all == 0], "no_fta", w)
    print(f"  wrote {path}")
    for t in (1, 2, 3, 5, 10):
        alive = (d_all >= t).sum()
        print(f"    share of spells reaching year {t:>2}: "
              f"{100*alive/len(d_all):5.1f}%")

    # --- discrete-time hazard
    print("\nDiscrete-time hazard (complementary log-log)")
    tariff = to_float(raw["tariff_rate"])
    gdp = to_float(raw["importer_gdp_usd"])
    dist = to_float(raw["dist"])
    pci = to_float(raw["pci"])
    rca = to_float(raw["rca"])
    val = to_float(raw["import_value_usd"])
    share = to_float(raw["partner_share_pct"])

    feats = {
        "log_tariff_1p": np.log1p(np.clip(tariff, 0, None)),
        "fta_in_force": fta,
        "log_gdp": np.log(np.clip(gdp, 1, None)),
        "log_dist": np.log(np.clip(dist, 1, None)),
        "pci": pci,
        "log_rca_1p": np.log1p(np.clip(rca, 0, None)),
        "log_value": np.log(np.clip(val, 1, None)),
        "partner_share_pct": share,
    }
    ok = np.ones(n, dtype=bool)
    for v in feats.values():
        ok &= np.isfinite(v)
    ok &= np.isfinite(dur) & np.isfinite(ev)
    print(f"  usable episodes: {int(ok.sum()):,} of {n:,} "
          f"({100*ok.sum()/n:.1f}%)")

    d = np.clip(dur[ok].astype(int), 1, MAX_DURATION_DUMMY)
    cols, names = [], []
    for t in range(1, MAX_DURATION_DUMMY + 1):
        cols.append((d == t).astype(float))
        names.append(f"duration_{t}" + ("plus" if t == MAX_DURATION_DUMMY else ""))
    for nm, v in feats.items():
        x = v[ok]
        # standardise the continuous ones so the Newton step is well scaled and
        # the coefficients are comparable in magnitude
        if nm not in ("fta_in_force",):
            s = x.std()
            x = (x - x.mean()) / (s if s > 0 else 1.0)
        cols.append(x)
        names.append(nm)
    X = np.column_stack(cols)
    y = ev[ok]

    beta, se, ll, iters = cloglog_fit(X, y, names)
    print(f"  converged in {iters} iterations, log-likelihood {ll:,.0f}")
    path = os.path.join(OUT, "hazard_baseline.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["term", "coef", "std_err", "z",
                                          "hazard_ratio"])
        w.writeheader()
        print("\n  term                       coef     s.e.       z    HR")
        for nm, b, s in zip(names, beta, se):
            z = b / s if s > 0 else float("nan")
            w.writerow({"term": nm, "coef": round(float(b), 6),
                        "std_err": round(float(s), 6), "z": round(float(z), 3),
                        "hazard_ratio": round(float(math.exp(b)), 4)})
            if not nm.startswith("duration_"):
                print(f"  {nm:<22} {b:>8.4f} {s:>8.4f} {z:>7.1f} "
                      f"{math.exp(b):>6.3f}")
    print(f"\n  wrote {path}")
    print("\n  These are a validation that the panel supports estimation, not "
          "the paper's specification:")
    print("  there are no fixed effects, no clustering, and the standard errors "
          "treat episodes as independent")
    print("  when they are repeated observations of the same relationship. Read "
          "the signs and magnitudes,")
    print("  not the significance stars.")


if __name__ == "__main__":
    sys.exit(main())
