"""Plan and run a batch of cells, sequentially, resumably.

    python -m stage2_benchmark.runners.batch --plan batch1            # run / resume
    python -m stage2_benchmark.runners.batch --plan batch1 --dry      # list cells
    python -m stage2_benchmark.runners.batch --plan batch1 --only L05 # filter
    python -m stage2_benchmark.runners.batch --plan batch1 --retry-failed

One process, one cell at a time: this machine has 8 GB of RAM shared with an
editor, so parallel cells would multiply the peak. Progress is visible in
artifacts/logs/<plan>.log and reports/<plan>/progress.csv.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402

import pandas as pd  # noqa: E402

from stage2_benchmark.runners import cell as C  # noqa: E402

LOGDIR = os.path.join(paths.ARTIFACTS, "logs")


def expand(plan_name: str, include_optional: bool = True) -> list[dict]:
    exp = paths.load_yaml("experiments.yaml")
    plan = exp[plan_name]
    specs = []
    for task, ref in exp["references"].items():
        specs.append({"batch": plan_name, "fold": plan["fold"], "task": task, "model": ref,
                      "fset": None, "stage": plan["stage"], "group": "reference"})
    for grp in plan["cells"]:
        if grp.get("optional") and not include_optional:
            continue
        for fs in grp["feature_sets"]:
            for m in grp["models"]:
                specs.append({"batch": plan_name, "fold": plan["fold"], "task": m[0],
                              "model": m, "fset": fs, "stage": plan["stage"],
                              "n_trials": plan.get("n_trials", 15),
                              "convergence_rule": plan.get("convergence_rule", True),
                              "grid_limit": plan.get("grid_limit"),
                              "seeds": plan.get("seeds", [1]), "group": grp["id"],
                              "fallback": grp.get("fallback_if_ineligible")})
    return specs


STOCHASTIC = {"D05", "D06", "L05", "L06", "L07", "L08", "L09", "L10"}


def expand_batch2() -> list[dict]:
    """Đợt 2 (plan §6.1): shortlist x {S1, S4, S*} x F1/F2/F3.

    valid : F1 and F3 are tuned independently (15 trials). F2 reuses the batch1
            tuning when that cell exists; otherwise it is tuned here.
    test  : refit at the refit cutoff with those params; stochastic models get
            seeds 1-3; F1 also scores horizon 5.
    """
    sl = paths.load_yaml("shortlist.yaml")
    specs = []
    for fold in ("F1", "F2", "F3"):
        for task, ref in (("D", "D00"), ("L", "L00")):
            for stage in ("valid", "test"):
                specs.append({"batch": "batch2", "fold": fold, "task": task, "model": ref,
                              "fset": None, "stage": stage, "group": "reference",
                              "params_batch": "batch2", "seeds": [1],
                              "horizons": [1, 2, 3, 4, 5] if (fold == "F1" and task == "L") else [1, 2, 3]})
        for task in ("D", "L"):
            for m in sl[f"{task}_models"]:
                for fs in sl[f"{task}_sets"]:
                    reuse = False
                    if fold == "F2":
                        from stage2_benchmark.runners import cell as C
                        b1 = {"batch": "batch1", "fold": "F2", "task": task, "model": m,
                              "fset": fs, "stage": "valid"}
                        reuse = C.read_status(b1).get("state") == "done"
                    common = {"fold": fold, "task": task, "model": m, "fset": fs,
                              "n_trials": 15, "group": "confirm"}
                    if not reuse:
                        specs.append(dict(common, batch="batch2", stage="valid", seeds=[1]))
                    specs.append(dict(common, batch="batch2", stage="test",
                                      params_batch="batch1" if reuse else "batch2",
                                      seeds=[1, 2, 3] if m in STOCHASTIC else [1],
                                      horizons=[1, 2, 3, 4, 5] if (fold == "F1" and task == "L") else [1, 2, 3]))
    return specs


def expand_lobo() -> list[dict]:
    """Đợt 2 LOBO (plan §6.2) on F2 validation: S8 minus one block, for L02,
    L* and D05. Where S8 is ineligible for the task (block N, see 0.3), the base
    is the widest eligible package S8-N and N is not dropped separately."""
    sl = paths.load_yaml("shortlist.yaml")
    elig = pd.read_csv(os.path.join(paths.REPORTS, "stage0", "0.3_eligibility.csv"))
    specs = []
    for task, models in (("L", ["L02", sl["L_star"]]), ("D", ["D05"])):
        ok = elig[(elig.fold == "F2") & (elig.task == task) & (elig.stage == "valid") & (elig.set == "S8")]
        base, blocks = ("S8", list("RMEPNCLH")) if ok["eligible"].all() else ("S8-N", list("RMEPCLH"))
        specs.append({"batch": "batch2_lobo", "fold": "F2", "task": task, "model": "L00" if task == "L" else "D00",
                      "fset": None, "stage": "valid", "group": "reference"})
        for m in dict.fromkeys(models):
            for fs in [base] + [f"{base}-{b}" for b in blocks]:
                specs.append({"batch": "batch2_lobo", "fold": "F2", "task": task, "model": m,
                              "fset": fs, "stage": "valid", "n_trials": 15, "seeds": [1],
                              "group": "lobo", "lobo_base": base})
    return specs


def _batch1_params(model, fsets):
    """Best params of the first finished batch1 F2 cell among `fsets`."""
    from stage2_benchmark.runners import cell as C
    for fs in fsets:
        sp = {"batch": "batch1", "fold": "F2", "task": model[0], "model": model,
              "fset": fs, "stage": "valid"}
        p = os.path.join(C.cell_dir(sp), "result.json")
        if C.read_status(sp).get("state") == "done" and os.path.exists(p):
            import json
            return json.load(open(p))["best_params"], fs
    return None, None


def expand_batch3() -> list[dict]:
    """Đợt 3 (plan §7) on F2 validation, R4 = {D01, D05, L02, L*}.

    Hyperparameters start from the matching batch1 cell: grid models rerun
    their (cheap) grid; stochastic models run that cell's best params as trial 0
    plus 6 new TPE trials."""
    sl = paths.load_yaml("shortlist.yaml")
    lstar = sl["L_star"]
    R4 = ["D01", "D05", "L02", lstar]
    elig = pd.read_csv(os.path.join(paths.REPORTS, "stage0", "0.3_eligibility.csv"))
    wide = {}
    for task in "DL":
        ok = elig[(elig.fold == "F2") & (elig.task == task) & (elig.stage == "valid") & (elig.set == "S8")]
        wide[task] = "S8" if ok["eligible"].all() else "S8-N"
    specs = []

    def add(model, fset, question, variant=None, warm_sets=None):
        warm, src = _batch1_params(model, warm_sets or [fset, "S4"])
        s = {"batch": "batch3", "fold": "F2", "task": model[0], "model": model, "fset": fset,
             "stage": "valid", "seeds": [1], "group": question, "n_trials": 7,
             "convergence_rule": False, "warm_params": warm, "warm_from": src}
        if variant:
            s["variant"] = variant
        specs.append(s)

    def ref(task, variant=None, question="reference"):
        s = {"batch": "batch3", "fold": "F2", "task": task, "model": task + "00", "fset": None,
             "stage": "valid", "group": question}
        if variant:
            s["variant"] = variant
        specs.append(s)

    ref("D")
    ref("L")
    # C05 selection
    for m in R4:
        for sel in ("enet_stability", "consensus"):
            add(m, wide[m[0]], "C05", {"name": sel, "selector": sel}, [wide[m[0]], "S4"])
    # C06 timing / history
    for m in R4:
        add(m, "S4@lagonly", "C06a", warm_sets=["S4"])
        add(m, "S4@hist5", "C06b", warm_sets=["S4"])
        add(m, "S4+H", "C06c", warm_sets=["S4"])
    # C09 survival definition (OFAT around 10k, gap 1)
    for name, gap in (("t5k_g1", 1), ("t50k_g1", 1), ("t10k_g0", 0), ("t10k_g2", 2)):
        v = {"name": name, "base": f"base_{name}", "gap": gap, "target_version": f"exit_{name}"}
        ref("D", v, "C09")
        ref("L", v, "C09")
        for m, sets in (("D01", ["S1", "S4"]), ("L02", ["S1", "S4"]), ("D05", ["S4"]), (lstar, ["S4"])):
            for fs in sets:
                add(m, fs, "C09", v)
    # C10 coverage / vintage
    for sub, sets in (("N", ["S4", "S5"]), ("L", ["S4", "S7"])):
        v = {"name": f"sub{sub}", "subset": sub}
        ref("L", v, "C10a")
        for m in ("L02", lstar):
            for fs in sets:
                add(m, fs, "C10a", v, [fs, "S4"])
    lenient = {"name": "lenientN", "skip_eligibility": True,
               "extra_cols": ["probe_log_ntm_sps_inforce", "probe_log_ntm_tbt_inforce",
                              "probe_ntm_ave_border_pct"]}
    for m in ("L02", lstar):
        add(m, "S4", "C10b", lenient)
    return specs


def widest_eligible(spec: dict, status: dict) -> str | None:
    """S8 minus every block that failed eligibility - the widest package that is
    eligible in this fold (plan §4.3 'gói rộng nhất còn eligible')."""
    reasons = status.get("reasons", [])
    bad = sorted({r.split()[1].rstrip(":") for r in reasons})
    if not bad:
        return None
    return spec["fset"] + "".join(f"-{b}" for b in bad)


class Logger:
    def __init__(self, name):
        os.makedirs(LOGDIR, exist_ok=True)
        self.f = open(os.path.join(LOGDIR, f"{name}.log"), "a", encoding="utf-8")

    def __call__(self, msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()


def progress_table(specs: list[dict]) -> pd.DataFrame:
    rows = []
    for s in specs:
        st = C.read_status(s)
        rows.append({"cell": C.cell_id(s), "group": s.get("group"), "model": s["model"],
                     "fset": s.get("fset") or "REF", "task": s["task"],
                     "state": st.get("state", "pending"), "primary": st.get("primary"),
                     "runtime_s": st.get("runtime_seconds"),
                     "note": "; ".join(st.get("reasons", [])) or st.get("error", "")})
    return pd.DataFrame(rows)


def run_plan(plan_name: str, only=None, retry_failed=False, dry=False,
             include_optional=True, specs=None):
    if specs is None:
        specs = {"batch2": expand_batch2, "batch2_lobo": expand_lobo,
                 "batch3": expand_batch3}.get(
            plan_name, lambda: expand(plan_name, include_optional))()
    if only:
        specs = [s for s in specs if any(o in C.cell_id(s) for o in only)]
    log = Logger(plan_name)
    if dry:
        for s in specs:
            print(C.cell_id(s), C.read_status(s).get("state", "pending"))
        return specs
    log(f"=== {plan_name}: {len(specs)} cells, commit {paths.code_commit()} ===")
    extra = []
    for i, s in enumerate(specs, 1):
        st = C.read_status(s)
        if st.get("state") == "failed" and retry_failed:
            s = dict(s, force=True)
        elif st.get("state") in ("done", "ineligible", "failed"):
            if st.get("state") == "ineligible" and s.get("fallback"):
                fb = widest_eligible(s, st)
                if fb:
                    extra.append(dict(s, fset=fb, fallback=None, group=s["group"] + "_fallback"))
            continue
        log(f"[{i}/{len(specs)}] {C.cell_id(s)}  (mem avail {paths.mem_available_mb():.0f} MB)")
        st = C.run_cell(s, log=log)
        if st.get("state") == "ineligible" and s.get("fallback"):
            fb = widest_eligible(s, st)
            if fb:
                log(f"  fallback -> {fb}")
                extra.append(dict(s, fset=fb, fallback=None, group=s["group"] + "_fallback"))
    for s in extra:
        if C.read_status(s).get("state") not in C.TERMINAL:
            log(f"[fallback] {C.cell_id(s)}")
            C.run_cell(s, log=log)
    allspecs = specs + extra
    prog = progress_table(allspecs)
    outdir = os.path.join(paths.REPORTS, plan_name)
    os.makedirs(outdir, exist_ok=True)
    paths.atomic_write_csv(prog, os.path.join(outdir, "progress.csv"))
    log(f"=== {plan_name}: " + ", ".join(f"{k}={v}" for k, v in
                                          prog["state"].value_counts().items()) + " ===")
    return allspecs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-optional", action="store_true")
    a = ap.parse_args()
    run_plan(a.plan, a.only, a.retry_failed, a.dry, not a.no_optional)


if __name__ == "__main__":
    main()
