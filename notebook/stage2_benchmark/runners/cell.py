"""Run one cell = (batch, fold, task, model, feature set, stage[, variant]).

Crash safety - the whole point of this file:
  * every cell owns artifacts/runs/<batch>/<cell_id>/ and a status.json that is
    written atomically; a cell whose status is terminal (done / ineligible) is
    skipped on rerun;
  * grid trials are appended to trials.jsonl one line per finished trial, and
    optuna trials live in an SQLite study (optuna.db); a rerun resumes after
    the last finished trial instead of starting over;
  * the best predictions so far are rewritten atomically after each improving
    trial, so no refit is needed to recover them.

stage = "valid": tune on the fold's validation origin (plan Đợt 1).
stage = "test":  refit with the best params of the matching valid cell at the
                 refit cutoff, predict the test origin; stochastic models get
                 3 seeds (plan Đợt 2).
"""

from __future__ import annotations

import json
import os
import time
import traceback

import numpy as np
import pandas as pd

from stage2_benchmark import paths
from stage2_benchmark.data import views as V
from stage2_benchmark.evaluation import metrics as M
from stage2_benchmark.features.preprocess import Preprocessor, eligibility, resolve_set
from stage2_benchmark.models import get_model
from stage2_benchmark.models.base import FitData

GRID = [1, 2, 3, 4, 5]
TERMINAL = ("done", "ineligible")
_BASES: dict = {}


# ------------------------------------------------------------------ io
def cell_id(spec: dict) -> str:
    parts = [spec["fold"], spec["model"], spec.get("fset") or "REF", spec["stage"]]
    if spec.get("variant"):
        parts.append(spec["variant"]["name"])
    return "__".join(parts)


def cell_dir(spec: dict) -> str:
    return os.path.join(paths.RUNS, spec["batch"], cell_id(spec))


def read_status(spec: dict) -> dict:
    p = os.path.join(cell_dir(spec), "status.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {}


def write_status(spec: dict, **kw) -> None:
    st = read_status(spec)
    st.update(kw, updated=time.strftime("%Y-%m-%d %H:%M:%S"))
    paths.atomic_write_json(os.path.join(cell_dir(spec), "status.json"), st)


def load_base(variant: dict | None = None) -> pd.DataFrame:
    """The EU27 base table; a C09 target variant has its own base file."""
    key = (variant or {}).get("base", "base_eu27")
    if key not in _BASES:
        path = os.path.join(paths.VIEWS, f"{key}.parquet")
        if key == "base_eu27" and not os.path.exists(path):
            from stage2_benchmark.data import base_table
            base_table.build()
        _BASES.clear()
        _BASES[key] = pd.read_parquet(path)
    return _BASES[key]


# ------------------------------------------------------------ data
def make_views(spec: dict):
    splits = paths.load_yaml("splits.yaml")
    variant = spec.get("variant") or {}
    base = load_base(variant)
    gap = variant.get("gap", V.GAP)
    task = spec["task"]
    train, ev = V.fold_views(base, splits, spec["fold"], task, spec["stage"],
                             first_origin=variant.get("first_origin"), gap=gap)
    if variant.get("subset"):
        train, ev = apply_subset(train, ev, variant["subset"])
    return train, ev


def apply_subset(train, ev, subset: str):
    """C10(a): restrict both cohorts to rows where a block has an as-of value."""
    from stage2_benchmark.features.preprocess import set_config
    keys = set_config()["eligibility"]["key_columns"][subset]
    f = lambda d: d[d[keys].notna().any(axis=1)].reset_index(drop=True)  # noqa: E731
    return f(train), f(ev)


def fit_data(df: pd.DataFrame, Z: np.ndarray, names, task: str) -> FitData:
    fd = FitData(Z=Z, age=df["age_obs"].to_numpy().astype("int64"),
                 relation=df["relation"].to_numpy(), names=list(names), raw=df)
    fd.duration = df["duration"].to_numpy().astype("int64")
    fd.event = df["event"].to_numpy().astype("int64")
    if task == "D":
        fd.y = df["y"].to_numpy().astype("float64")
    return fd


def feature_columns(spec: dict) -> list[str]:
    if not spec.get("fset"):
        return []
    cols = resolve_set(spec["fset"])
    extra = (spec.get("variant") or {}).get("extra_cols", [])
    return cols + [c for c in extra if c not in cols]


# --------------------------------------------------------- predict/score
def predict(model, task, Z, age):
    if task == "D":
        p = np.asarray(model.predict_proba(Z, age), dtype="float64")
        bad = [] if np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all() \
            else ["probability outside [0,1] or non-finite"]
        return p, bad
    S = np.asarray(model.predict_survival(Z, GRID, age), dtype="float64")
    return S, M.check_survival(S)


def score(task, pred, ev: FitData, horizons=(1, 2, 3)):
    if task == "D":
        return M.score_D(pred, ev.y)
    return M.score_L(pred, GRID, ev.duration, ev.event, horizons=tuple(horizons))


def primary(task):
    return "brier_1y" if task == "D" else "ibs_1_3"


def pred_frame(ev_df: pd.DataFrame, task: str, preds: dict) -> pd.DataFrame:
    keep = ["spell_id", "year", "relation", "importer", "hs2", "duration", "event",
            "age_obs", "meta_known_start", "meta_recurrent"]
    out = ev_df[keep].copy()
    if task == "D":
        out["y"] = ev_df["y"].to_numpy()
    for tag, p in preds.items():
        if task == "D":
            out[f"p{tag}"] = p.astype("float32")
        else:
            for k, u in enumerate(GRID):
                out[f"S{u}{tag}"] = p[:, k].astype("float32")
    return out


# ------------------------------------------------------------- tuning
class TrialLog:
    def __init__(self, d):
        self.path = os.path.join(d, "trials.jsonl")

    def read(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(x) for x in f if x.strip()]

    def append(self, rec):
        with open(self.path, "a") as f:
            f.write(json.dumps(rec, default=paths._json_default) + "\n")
            f.flush()
            os.fsync(f.fileno())


def run_trial(model_id, params, tr: FitData, ev: FitData, task, seed):
    t0 = time.time()
    m = get_model(model_id)
    m.fit(tr, params, seed=seed)
    fit_s = time.time() - t0
    pred, bad = predict(m, task, ev.Z, ev.age)
    if bad:
        raise ValueError("; ".join(bad))
    sc = score(task, pred, ev)
    return m, pred, sc, {"fit_seconds": round(fit_s, 2),
                         "total_seconds": round(time.time() - t0, 2),
                         "rss_mb": round(paths.rss_mb()), "info": m.info()}


def tune(spec, tr, ev, d, log):
    """Returns (best_params, best_pred, best_score, trials)."""
    task, mid = spec["task"], spec["model"]
    model = get_model(mid)
    tl = TrialLog(d)
    done = tl.read()
    best = {"value": np.inf}
    best_pred_path = os.path.join(d, "best_pred.npy")
    for r in done:
        if r.get("state") == "ok" and r["value"] < best["value"]:
            best = r
    key = primary(task)

    def consider(i, params, seed=1):
        nonlocal best
        try:
            m, pred, sc, meta = run_trial(mid, params, tr, ev, task, seed)
            val = float(sc[key])
            if not np.isfinite(val):
                raise ValueError(f"{key} is not finite")
            rec = {"trial": i, "params": params, "value": val, "state": "ok",
                   "scores": sc, **meta}
            if val < best["value"]:
                best = rec
                tmp = best_pred_path + ".tmp.npy"
                np.save(tmp, pred)
                os.replace(tmp, best_pred_path)
        except Exception as ex:  # a failed trial is recorded, not fatal
            rec = {"trial": i, "params": params, "value": None, "state": "failed",
                   "error": f"{type(ex).__name__}: {ex}"[:500]}
            log(f"    trial {i} failed: {rec['error']}")
        tl.append(rec)
        log(f"    trial {i}: {key}={rec['value']}  "
            f"({rec.get('total_seconds', '?')}s, rss {paths.rss_mb():.0f}MB)")
        return rec

    if model.tuning in ("none", "grid"):
        grid = model.grid()
        for i, params in enumerate(grid):
            if i < len(done):
                continue
            consider(i, params)
    else:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        n_target = spec.get("n_trials", 15)
        storage = f"sqlite:///{os.path.join(d, 'optuna.db')}"
        study = optuna.create_study(study_name="s", storage=storage, direction="minimize",
                                    load_if_exists=True,
                                    sampler=optuna.samplers.TPESampler(seed=spec.get("tune_seed", 1)))
        # trials left RUNNING by a crash are closed as FAIL and not counted
        for t in study.get_trials(deepcopy=False):
            if t.state == optuna.trial.TrialState.RUNNING:
                study._storage.set_trial_state_values(t._trial_id, optuna.trial.TrialState.FAIL)

        def n_finished():
            return len([t for t in study.get_trials(deepcopy=False)
                        if t.state in (optuna.trial.TrialState.COMPLETE,
                                       optuna.trial.TrialState.FAIL)])

        def objective(trial):
            params = model.suggest(trial)
            rec = consider(trial.number, params)
            if rec["state"] != "ok":
                raise optuna.TrialPruned()
            return rec["value"]

        def run_until(n):
            while n_finished() < n:
                study.optimize(objective, n_trials=1, catch=(Exception,))

        run_until(n_target)
        # convergence rule (plan §2): best trial in the last 25% -> +15 trials, once
        recs = [r for r in tl.read() if r["state"] == "ok"]
        if recs and spec.get("convergence_rule", True):
            order = [r["trial"] for r in recs]
            bi = min(recs, key=lambda r: r["value"])["trial"]
            late = bi >= int(np.ceil(max(order) + 1 - 0.25 * (max(order) + 1)))
            if late and n_target <= spec.get("n_trials", 15):
                log(f"    best trial {bi} is in the last 25% -> +15 trials")
                write_status(spec, extended=True)
                run_until(n_target + 15)
    trials = tl.read()
    ok = [r for r in trials if r["state"] == "ok"]
    if not ok:
        raise RuntimeError("every trial failed")
    best = min(ok, key=lambda r: r["value"])
    return best, np.load(best_pred_path), trials


# ----------------------------------------------------------------- cell
def run_cell(spec: dict, log=print) -> dict:
    d = cell_dir(spec)
    os.makedirs(d, exist_ok=True)
    st = read_status(spec)
    if st.get("state") in TERMINAL and not spec.get("force"):
        return st
    cid = cell_id(spec)
    task = spec["task"]
    t0 = time.time()
    write_status(spec, state="running", started=time.strftime("%Y-%m-%d %H:%M:%S"),
                 spec=spec)
    try:
        train, ev = make_views(spec)
        cols = feature_columns(spec)
        manifest = build_manifest(spec, train, ev, cols)
        if cols:
            el = eligibility(train, spec["fset"])
            manifest["eligibility"] = el
            if not el["eligible"]:
                paths.atomic_write_json(os.path.join(d, "manifest.json"), manifest)
                write_status(spec, state="ineligible", reasons=el["reasons"])
                log(f"  {cid}: INELIGIBLE - {'; '.join(el['reasons'])}")
                return read_status(spec)
        pre = Preprocessor(cols).fit(train)
        Ztr, Zev = pre.transform(train), pre.transform(ev)
        manifest["preprocessor"] = pre.state()
        tr = fit_data(train, Ztr, pre.names, task)
        evd = fit_data(ev, Zev, pre.names, task)
        del Ztr, Zev
        log(f"  {cid}: train {len(train):,} rows / {int(tr.event.sum()) if task == 'L' else int(tr.y.sum()):,} events, "
            f"eval {len(ev):,}, {len(pre.names)} cols")

        if spec["stage"] == "valid":
            best, pred, trials = tune(spec, tr, evd, d, log)
            preds = {"": pred}
            result = {"best_params": best["params"], "best_trial": best["trial"],
                      "scores": best["scores"], "n_trials": len(trials),
                      "n_failed": sum(r["state"] != "ok" for r in trials),
                      "budget_curve": budget_curve(trials, task),
                      "info": best.get("info", {})}
        else:
            params = test_params(spec)
            seeds = spec.get("seeds", [1])
            preds, per_seed = {}, {}
            for s in seeds:
                sp = os.path.join(d, f"pred_seed{s}.npy")
                if os.path.exists(sp):
                    p = np.load(sp)
                    sc = score(task, p, evd, spec.get("horizons", (1, 2, 3)))
                else:
                    m, p, sc, meta = run_trial(spec["model"], params, tr, evd, task, s)
                    np.save(sp + ".tmp.npy", p)
                    os.replace(sp + ".tmp.npy", sp)
                    log(f"    seed {s}: {primary(task)}={sc[primary(task)]:.5f}")
                preds[f"_s{s}"] = p
                per_seed[s] = sc
                if task == "L" and 5 in spec.get("horizons", ()):
                    per_seed[s].update({k: v for k, v in score(task, p, evd, (1, 2, 3, 4, 5)).items()
                                        if k == "ibs_1_5"})
            keys = per_seed[seeds[0]].keys()
            mean_sc = {k: float(np.mean([per_seed[s][k] for s in seeds]))
                       for k in keys if isinstance(per_seed[seeds[0]][k], (int, float))}
            result = {"params": params, "scores": mean_sc,
                      "per_seed": per_seed, "seeds": seeds}
        pf = pred_frame(ev, task, preds)
        paths.atomic_write_parquet(pf, os.path.join(d, "pred.parquet"))
        manifest.update(runtime_seconds=round(time.time() - t0, 1),
                        peak_rss_mb=round(paths.peak_rss_mb()))
        paths.atomic_write_json(os.path.join(d, "manifest.json"), manifest)
        paths.atomic_write_json(os.path.join(d, "result.json"), result)
        write_status(spec, state="done", primary=result["scores"].get(primary(task)),
                     runtime_seconds=round(time.time() - t0, 1))
        log(f"  {cid}: DONE {primary(task)}={result['scores'].get(primary(task)):.5f} "
            f"in {time.time() - t0:.0f}s")
    except Exception as ex:
        write_status(spec, state="failed", error=f"{type(ex).__name__}: {ex}",
                     traceback=traceback.format_exc()[-3000:])
        log(f"  {cid}: FAILED {type(ex).__name__}: {ex}")
    return read_status(spec)


def test_params(spec):
    """Best params of the matching validation cell (params_from overrides)."""
    src = dict(spec, stage="valid", batch=spec.get("params_batch", spec["batch"]))
    src.pop("seeds", None)
    p = os.path.join(cell_dir(src), "result.json")
    if not os.path.exists(p):
        raise FileNotFoundError(f"no tuned params at {p}")
    with open(p) as f:
        return json.load(f)["best_params"]


def budget_curve(trials, task):
    best, out = np.inf, []
    for r in sorted(trials, key=lambda r: r["trial"]):
        if r["state"] == "ok":
            best = min(best, r["value"])
        out.append(best if np.isfinite(best) else None)
    return out


def build_manifest(spec, train, ev, cols):
    splits = paths.load_yaml("splits.yaml")
    tasks = paths.load_yaml("tasks.yaml")
    f = splits["folds"][spec["fold"]]
    t = f[spec["task"]]
    variant = spec.get("variant") or {}
    return {
        "panel_version": tasks["panel_version"], "panel_hash": paths.panel_hash(),
        "code_commit": paths.code_commit(),
        "target_version": variant.get("target_version", tasks["target_version"]),
        "scope": tasks["scope"], "task": spec["task"], "feature_set": spec.get("fset"),
        "feature_columns": cols, "selector": variant.get("selector", "none"),
        "model": spec["model"], "fold": spec["fold"], "stage": spec["stage"],
        "valid_origin": t["valid_origin"], "inner_label_cutoff": t["inner_cutoff"],
        "validation_outcome_cutoff": t["refit_cutoff"], "refit_label_cutoff": t["refit_cutoff"],
        "test_origin": f["test_origin"], "test_outcome_cutoff": splits["test_read_to"],
        "first_training_origin": variant.get("first_origin", splits["first_training_origin"]),
        "horizons": [1, 2, 3] if spec["task"] == "L" else [1],
        "seeds": spec.get("seeds", [1]), "sample_budget": "full_eligible",
        "variant": variant or None,
        "train_rows": len(train), "train_events": int(train["event"].sum()),
        "train_origins": [int(train["year"].min()), int(train["year"].max())] if len(train) else None,
        "eval_rows": len(ev), "eval_events": int(ev["event"].sum()),
        "eval_one_year_events": int(((ev["duration"] == 1) & (ev["event"] == 1)).sum()),
        "train_cohort_hash": V.cohort_hash(train), "eval_cohort_hash": V.cohort_hash(ev),
    }
