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
                              "seeds": plan.get("seeds", [1]), "group": grp["id"],
                              "fallback": grp.get("fallback_if_ineligible")})
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
    specs = specs if specs is not None else expand(plan_name, include_optional)
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
