"""Đợt 4 - inference branch I1-I16 (plan §8).

    python -m stage2_benchmark.inference.run_inference            # all, resumable
    python -m stage2_benchmark.inference.run_inference --only I12

Sample: B0 person-period view, origins 2012-2023, outcomes confirmed with data
to 2025 (views.inference_view). One row = one active relation-year at risk of
exiting in the following year. Main sample = known-start spells (spell age from
the 2002 history is real); I11, I15, I16 use every spell.

Specification choices (written before any fit):
  * duration dummies for observed spell age 1..10+ (the grouped-time baseline);
  * explanatory mode: LAGGED covariates only (the S-sets with @lagonly - the
    current-year trade value is dropped), standardised on the sample, missing
    -> median + indicator; indicators that duplicate a duration dummy dropped;
  * SE: two-way cluster by importer and HS2 (CGM), plus an unrestricted wild
    score bootstrap over the 27 importer clusters (Kline-Santos 2012, Webb
    weights, 999 draws) for the coefficients of interest;
  * event time is read on the OUTCOME year (t + 1): origin 2019's outcome is
    exit during 2020, the EVFTA entry year, so the reference period is outcome
    year 2019 (origin 2018), 2020 is the transition, 2021+ post.
Coefficients are associations unless an identification argument is stated
(design doc §9.2 C08); nothing here is read as a causal EVFTA effect by default.

Each spec is checkpointed to reports/batch4/specs/<id>.json and skipped when
present.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import sparse  # noqa: E402
from scipy.stats import norm  # noqa: E402

from stage2_benchmark.data import base_table  # noqa: E402
from stage2_benchmark.data import views as V  # noqa: E402
from stage2_benchmark.features.preprocess import Preprocessor, resolve_set  # noqa: E402
from stage2_benchmark.inference.frailty import GammaFrailtyCloglog, RandomInterceptBinary  # noqa: E402
from stage2_benchmark.inference.glm import cluster_cov, fit_glm  # noqa: E402

OUT = os.path.join(paths.REPORTS, "batch4")
SPECDIR = os.path.join(OUT, "specs")
D_COLS = {"age_obs", "log_age", "known_start"}
MAX_AGE = 10
EVFTA_YEAR = 2020


# ----------------------------------------------------------------- data
def sample(full: bool = False) -> pd.DataFrame:
    v = V.inference_view(base_table.load_base())
    if not full:
        v = v[v["meta_known_start"] == 1]
    v = v.reset_index(drop=True)
    v["outcome_year"] = v["year"] + 1
    v["k"] = v["outcome_year"] - EVFTA_YEAR
    return v


def intensity(base: pd.DataFrame) -> pd.Series:
    """EVFTA tariff-cut intensity per family: the cumulative scheduled cut (pp)
    by 2023, fixed by the 2019 schedule (Annex 2-A), not by outcomes."""
    b = base[base["year"] == 2024][["product_family", "evfta_cut_cum_pp_lag"]]
    s = b.groupby("product_family")["evfta_cut_cum_pp_lag"].max()
    return s


def design(df, fset, extra=None, fe=(), duration_dummies=True):
    """Sparse design: [age dummies | standardised lagged X (+ flags) | extra | FE]."""
    names, blocks = [], []
    if duration_dummies:
        a = np.clip(df["age_obs"].to_numpy().astype(int), 1, MAX_AGE)
        blocks.append(sparse.csr_matrix((np.ones(len(a)), (np.arange(len(a)), a - 1)),
                                        shape=(len(a), MAX_AGE)))
        names += [f"age_{k}" + ("+" if k == MAX_AGE else "") for k in range(1, MAX_AGE + 1)]
    pre = None
    if fset:
        cols = [c for c in resolve_set(fset + "@lagonly") if c not in D_COLS]
        pre = Preprocessor(cols).fit(df)
        Z = pre.transform(df).astype("float64")
        nm = list(pre.names)
        if duration_dummies:          # drop flags that duplicate an age dummy
            a1 = (df["age_obs"].to_numpy() == 1).astype(float)
            keep = [j for j, n in enumerate(nm)
                    if not (n.endswith("_isna") and abs(np.corrcoef(Z[:, j], a1)[0, 1]) > 0.995)]
            Z, nm = Z[:, keep], [nm[j] for j in keep]
        blocks.append(sparse.csr_matrix(Z))
        names += nm
    if extra is not None and extra.shape[1]:
        blocks.append(sparse.csr_matrix(extra.to_numpy(dtype="float64")))
        names += list(extra.columns)
    for f in fe:
        codes, inv = np.unique(df[f].astype(str).to_numpy(), return_inverse=True)
        m = sparse.csr_matrix((np.ones(len(inv)), (np.arange(len(inv)), inv)),
                              shape=(len(inv), len(codes)))[:, 1:]    # drop first level
        blocks.append(m)
        names += [f"FE_{f}_{c}" for c in codes[1:]]
    X = sparse.hstack(blocks).tocsr()
    return X, names, pre


def webb_weights(rng, size):
    v = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
    return rng.choice(v, size=size)


def wild_score_bootstrap(fit, X, clusters, idx, B=999, seed=20260927):
    """Unrestricted wild score bootstrap over clusters for coefficients `idx`."""
    g = fit["score_factor"]
    codes, inv = np.unique(clusters, return_inverse=True)
    Gm = sparse.csr_matrix((g, (inv, np.arange(len(g)))), shape=(len(codes), len(g)))
    S = Gm @ X
    S = np.asarray(S.todense()) if sparse.issparse(S) else S       # (G, k)
    Hinv = fit["cov"][idx, :]                                      # (m, k)
    rng = np.random.default_rng(seed)
    W = webb_weights(rng, (B, len(codes)))
    D = (W @ S) @ Hinv.T                                           # (B, m)
    b = fit["beta"][idx]
    out = []
    for j in range(len(idx)):
        d = D[:, j]
        out.append({"boot_se": float(d.std(ddof=1)),
                    "boot_ci_lo": float(b[j] - np.quantile(d, 0.975)),
                    "boot_ci_hi": float(b[j] - np.quantile(d, 0.025)),
                    "boot_p": float((np.abs(d) >= abs(b[j])).mean())})
    return out, len(codes)


def glm_result(df, X, names, link, key_prefixes, ridge=1e-8, cluster=True, wild=True):
    n = X.shape[0]
    fit = fit_glm(X, df["y"].to_numpy(), link, penalty=np.full(X.shape[1], ridge * n))
    res = {"n": int(n), "events": int(df["y"].sum()), "loglik": fit["loglik"],
           "converged": bool(fit["converged"]), "k": X.shape[1], "link": link}
    se_model = np.sqrt(np.diag(fit["cov"]))
    if cluster:
        V2, info = cluster_cov(fit, X, df["importer"].to_numpy(), df["hs2"].to_numpy())
        se2 = np.sqrt(np.maximum(np.diag(V2), 0))
        res["clusters"] = info
    else:
        se2 = se_model
    key = [i for i, nm in enumerate(names) if nm.startswith(tuple(key_prefixes))
           and not nm.startswith("FE_")]
    boot = None
    if wild and key:
        boot, G = wild_score_bootstrap(fit, X, df["importer"].to_numpy(), key)
        res["wild_clusters"] = G
    coefs = []
    for i, nm in enumerate(names):
        if nm.startswith("FE_"):
            continue
        r = {"term": nm, "coef": float(fit["beta"][i]), "se_model": float(se_model[i]),
             "se_2way": float(se2[i]), "z_2way": float(fit["beta"][i] / se2[i]) if se2[i] > 0 else np.nan,
             "p_2way": float(2 * norm.sf(abs(fit["beta"][i] / se2[i]))) if se2[i] > 0 else np.nan}
        if link == "cloglog":
            r["hazard_ratio"] = float(np.exp(fit["beta"][i]))
        if boot is not None and i in key:
            r.update(boot[key.index(i)])
        coefs.append(r)
    res["coefs"] = coefs
    return res, fit


def wald(fit, V_, idx):
    b = fit["beta"][idx]
    Vs = V_[np.ix_(idx, idx)]
    stat = float(b @ np.linalg.pinv(Vs) @ b)
    from scipy.stats import chi2
    return {"chi2": stat, "df": len(idx), "p": float(chi2.sf(stat, len(idx)))}


# ---------------------------------------------------------------- specs
LADDER = {"I1": None, "I2": "S1", "I3": "S2", "I4": "S3", "I5": "S4"}
KEY_S4 = ["log_value_lag", "log_initial_value", "vn_market_share", "volatility",
          "log_gdp", "log_n_", "hs2_share", "log_rca", "tariff_applied", "pref_margin",
          "evfta"]


def spec_ladder(sid, full=False):
    df = sample(full)
    X, names, _ = design(df, LADDER.get(sid, "S4"))
    res, _ = glm_result(df, X, names, "cloglog", KEY_S4)
    res.update(spec=f"pooled cloglog, duration dummies + {LADDER.get(sid, 'S4') or 'none'}",
               sample="all spells" if full else "known-start")
    return res


def spec_frailty(fset, full=False):
    df = sample(full)
    X, names, _ = design(df, fset)
    Xd = X.toarray()
    pooled = fit_glm(X, df["y"].to_numpy(), "cloglog", penalty=np.full(X.shape[1], 1e-8 * len(df)))
    t0 = time.time()
    m = GammaFrailtyCloglog().fit(Xd, df["y"].to_numpy(), df["relation"].to_numpy(),
                                  beta0=pooled["beta"])
    se = np.sqrt(np.maximum(np.diag(m.cov_)[:-1], 0))
    lr = 2 * (m.loglik_ - pooled["loglik"])
    from scipy.stats import chi2
    res = {"spec": f"cloglog + shared gamma frailty (relation) @{fset}",
           "sample": "all spells" if full else "known-start",
           "n": len(df), "events": int(df["y"].sum()), "groups": m.n_groups_,
           "max_events_per_group": m.max_events_per_group_,
           "theta": m.theta_, "theta_se_log": float(np.sqrt(m.cov_[-1, -1])),
           "loglik": m.loglik_, "loglik_pooled": pooled["loglik"],
           "LR_theta0": float(lr), "p_LR_theta0_boundary": float(0.5 * chi2.sf(max(lr, 0), 1)),
           "grad_max": m.grad_max_, "seconds": round(time.time() - t0, 1),
           "coefs": [{"term": nm, "coef": float(m.beta_[i]), "se_model": float(se[i]),
                      "hazard_ratio": float(np.exp(m.beta_[i])),
                      "coef_pooled": float(pooled["beta"][i])}
                     for i, nm in enumerate(names)]}
    return res


def spec_re(link):
    df = sample()
    X, names, _ = design(df, "S4")
    pooled = fit_glm(X, df["y"].to_numpy(), link, penalty=np.full(X.shape[1], 1e-8 * len(df)))
    t0 = time.time()
    m = RandomInterceptBinary(link).fit(X.toarray(), df["y"].to_numpy(),
                                        df["relation"].to_numpy(), beta0=pooled["beta"])
    se = np.sqrt(np.maximum(np.diag(m.cov_)[:-1], 0))
    return {"spec": f"random-intercept {link} (relation) @S4", "sample": "known-start",
            "n": len(df), "events": int(df["y"].sum()), "groups": m.n_groups_,
            "sigma_u": m.sigma_, "rho": m.rho_, "loglik": m.loglik_,
            "loglik_pooled": pooled["loglik"], "grad_max": m.grad_max_,
            "seconds": round(time.time() - t0, 1),
            "coefs": [{"term": nm, "coef": float(m.beta_[i]), "se_model": float(se[i]),
                       "coef_pooled": float(pooled["beta"][i])} for i, nm in enumerate(names)]}


INTERACT = ["log_value_lag", "vn_market_share_lag1", "tariff_applied_lag",
            "pref_margin_lag", "log_initial_value"]


def spec_age_interactions():
    df = sample()
    la = np.log(df["age_obs"].to_numpy().astype(float))
    la = la - la.mean()
    base_X, names, pre = design(df, "S4")
    Zdf = pd.DataFrame(pre.transform(df), columns=pre.names)
    extra = pd.DataFrame({f"{c}_x_logage": Zdf[c].to_numpy() * la for c in INTERACT if c in Zdf})
    X, names, _ = design(df, "S4", extra=extra)
    res, fit = glm_result(df, X, names, "cloglog", [c + "_x_logage" for c in INTERACT])
    V2, _ = cluster_cov(fit, X, df["importer"].to_numpy(), df["hs2"].to_numpy())
    idx = [i for i, n in enumerate(names) if n.endswith("_x_logage")]
    res["wald_all_interactions_2way"] = wald(fit, V2, idx)
    res["spec"] = "pooled cloglog S4 + X × log(age) (5 R/P variables): PH-in-age check"
    res["sample"] = "known-start"
    return res


def spec_recurrent():
    df = sample(full=True)
    _, _, pre = design(df, "S4")
    Zdf = pd.DataFrame(pre.transform(df), columns=pre.names)
    rec = df["meta_recurrent"].to_numpy().astype(float)
    unk = 1.0 - df["meta_known_start"].to_numpy().astype(float)
    extra = {"recurrent": rec, "unknown_start": unk}
    for c in ("log_value_lag", "log_initial_value", "vn_market_share_lag1"):
        if c in Zdf:
            extra[f"recurrent_x_{c}"] = rec * Zdf[c].to_numpy()
            extra[f"unknown_start_x_{c}"] = unk * Zdf[c].to_numpy()
    extra = pd.DataFrame(extra)
    X, names, _ = design(df, "S4", extra=extra)
    res, fit = glm_result(df, X, names, "cloglog", ["recurrent", "unknown_start"])
    V2, _ = cluster_cov(fit, X, df["importer"].to_numpy(), df["hs2"].to_numpy())
    for tag in ("recurrent_x_", "unknown_start_x_"):
        idx = [i for i, n in enumerate(names) if n.startswith(tag)]
        res[f"wald_{tag.rstrip('_')}_2way"] = wald(fit, V2, idx)
    res["spec"] = "pooled cloglog S4 + recurrent and unknown-start main effects and interactions"
    res["sample"] = "all spells"
    return res


def _policy_frame(df, inten):
    x = df["product_family"].map(inten)
    ok = x.notna().to_numpy()
    df = df[ok].reset_index(drop=True)
    x = x[ok].to_numpy()
    sd = float(np.std(x))
    return df, (x - x.mean()) / sd, sd


def spec_event_study():
    base = base_table.load_base()
    df, xi, sd = _policy_frame(sample(), intensity(base))
    ks = sorted(df["k"].unique())
    extra = {"intensity": xi}
    for k in ks:
        if k == -1:
            continue
        extra[f"intensity_x_k{k:+d}"] = xi * (df["k"].to_numpy() == k)
    X, names, _ = design(df, "S1", extra=pd.DataFrame(extra),
                         fe=("importer", "hs2", "outcome_year"))
    res, fit = glm_result(df, X, names, "cloglog", ["intensity_x_k"])
    V2, _ = cluster_cov(fit, X, df["importer"].to_numpy(), df["hs2"].to_numpy())
    pre = [i for i, n in enumerate(names) if n.startswith("intensity_x_k-")]
    post = [i for i, n in enumerate(names) if n.startswith("intensity_x_k+") and not n.endswith("k+0")]
    res.update(pretrend_wald_2way=wald(fit, V2, pre), post_wald_2way=wald(fit, V2, post),
               intensity_sd_pp=sd, reference="outcome year 2019 (k = -1)",
               spec="cloglog event study: intensity × 1[outcome year − 2020 = k]; FE importer, HS2, "
                    "outcome year; duration dummies + lagged R controls",
               sample="known-start")
    return res


def spec_incumbent_entrant():
    base = base_table.load_base()
    df, xi, sd = _policy_frame(sample(), intensity(base))
    oy = df["outcome_year"].to_numpy()
    trans = (oy == EVFTA_YEAR).astype(float)
    post = (oy >= EVFTA_YEAR + 1).astype(float)
    entrant = (df["spell_start_year"].to_numpy() >= EVFTA_YEAR).astype(float)
    extra = pd.DataFrame({"intensity": xi, "intensity_x_transition": xi * trans,
                          "intensity_x_post": xi * post,
                          "entrant_x_post": entrant * post,
                          "intensity_x_post_x_entrant": xi * post * entrant})
    X, names, _ = design(df, "S1", extra=extra, fe=("importer", "hs2", "outcome_year"))
    res, _ = glm_result(df, X, names, "cloglog", ["intensity_x", "entrant"])
    res.update(intensity_sd_pp=sd,
               spec="cloglog: intensity × {transition 2020, post 2021+} × (entrant: spell start ≥ 2020); "
                    "FE importer, HS2, outcome year", sample="known-start",
               n_entrant_rows=int(entrant.sum()))
    return res


def spec_placebo():
    base = base_table.load_base()
    df = sample()
    df = df[df["outcome_year"] <= 2019].reset_index(drop=True)
    df, xi, sd = _policy_frame(df, intensity(base))
    fake = (df["outcome_year"].to_numpy() >= 2017).astype(float)
    extra = pd.DataFrame({"intensity": xi, "intensity_x_fakepost2017": xi * fake})
    X, names, _ = design(df, "S1", extra=extra, fe=("importer", "hs2", "outcome_year"))
    res, _ = glm_result(df, X, names, "cloglog", ["intensity_x_fakepost"])
    res.update(intensity_sd_pp=sd, sample="known-start, outcome years ≤ 2019",
               spec="placebo: EVFTA dated 2017; intensity × 1[outcome year ≥ 2017]")
    return res


SPECS = {
    "I1": lambda: spec_ladder("I1"), "I2": lambda: spec_ladder("I2"),
    "I3": lambda: spec_ladder("I3"), "I4": lambda: spec_ladder("I4"),
    "I5": lambda: spec_ladder("I5"),
    "I6": lambda: spec_frailty("S1"), "I7": lambda: spec_frailty("S4"),
    "I8": lambda: spec_re("logit"), "I9": lambda: spec_re("probit"),
    "I10": spec_age_interactions, "I11": spec_recurrent,
    "I12": spec_event_study, "I13": spec_incumbent_entrant, "I14": spec_placebo,
    "I15": lambda: spec_ladder("I5", full=True),
    "I16": lambda: spec_frailty("S4", full=True),
}


def run(only=None, log=print):
    os.makedirs(SPECDIR, exist_ok=True)
    for sid, fn in SPECS.items():
        if only and sid not in only:
            continue
        path = os.path.join(SPECDIR, f"{sid}.json")
        if os.path.exists(path):
            log(f"{sid}: done (checkpoint)")
            continue
        t0 = time.time()
        log(f"{sid}: running ...")
        try:
            res = fn()
            res.update(id=sid, seconds_total=round(time.time() - t0, 1),
                       code_commit=paths.code_commit(), panel_hash=paths.panel_hash(),
                       peak_rss_mb=round(paths.peak_rss_mb()))
            paths.atomic_write_json(path, res)
            log(f"{sid}: ok in {time.time() - t0:.0f}s, rss {paths.rss_mb():.0f} MB")
        except Exception as ex:
            import traceback
            log(f"{sid}: FAILED {type(ex).__name__}: {ex}")
            traceback.print_exc()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    run(a.only)


if __name__ == "__main__":
    main()
