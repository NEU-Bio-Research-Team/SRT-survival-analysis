"""Add optuna trials to finished cells still flagged "not converged" (plan §5:
flagged models get more budget before ranking). Resumes the cell's own study.

    python -m stage2_benchmark.runners.extend_budget --batch batch1 --cells F2__D05__S7__valid ... --to 45
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from stage2_benchmark import paths  # noqa: E402,F401
from stage2_benchmark.runners import cell as C  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--batch", required=True)
ap.add_argument("--cells", nargs="+", required=True)
ap.add_argument("--to", type=int, default=45)
a = ap.parse_args()
for cid in a.cells:
    st = json.load(open(os.path.join(paths.RUNS, a.batch, cid, "status.json")))
    spec = dict(st["spec"], n_trials=a.to, convergence_rule=False, force=True)
    prev = st.get("primary")
    new = C.run_cell(spec)
    C.write_status(spec, budget_extended_to=a.to, primary_before_extension=prev)
    print(cid, "before", prev, "after", new.get("primary"), flush=True)
