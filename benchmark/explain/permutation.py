"""Plan section 18 - explainability, with the explained quantity named.

The rule the plan insists on is the one most SHAP tables in this literature
break: a survival model has no single output, so "feature importance" is
meaningless until a horizon is fixed. Everything here is importance FOR A STATED
QUANTITY,

    P(T > 3 | X)  -  the three-year survival probability,

measured as the deterioration in that probability's Brier score when one column
is shuffled. Shuffling breaks the column's relationship with the outcome while
leaving its marginal distribution intact, so the number is "how much worse the
predictions get without this information", not "how big is the coefficient".

Two caveats travel with the output rather than being left to the reader:

*   Correlated columns share credit. `log_value` and `log_value_lag` are nearly
    the same fact, so shuffling either one alone understates the pair. Read
    blocks, not individual rows, where the registry says two columns encode one
    concept.
*   Importance is not a causal effect. A high score means the model leans on the
    column for prediction, which is a statement about the model and the sample,
    not about what a policymaker changing that variable would cause.

Usage:  python benchmark/explain/permutation.py --model RSF --fold 4
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from benchmark.evaluation import brier_at
from benchmark.features.preprocess import Preprocessor
from benchmark.models import FitContext, build_registry
from benchmark.splits.rolling_origin import load_yaml, make_folds

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "benchmark", "reports")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="CoxPH")
    ap.add_argument("--feature-set", default="F0F1F2F3F4")
    ap.add_argument("--fold", type=int, default=4)
    ap.add_argument("--horizon", type=int, default=3)
    ap.add_argument("--n-eval", type=int, default=8000)
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()

    cfg, hz = load_yaml("benchmark.yaml"), load_yaml("horizons.yaml")
    grid = hz["grid"]
    fold = next((f for f in make_folds() if f[0] == args.fold), None)
    if fold is None:
        print(f"fold {args.fold} not found")
        return 1
    _, tr, va, te = fold

    prep = Preprocessor(args.feature_set).fit(tr)
    Ztr, Zva = prep.transform(tr), prep.transform(va)
    reg = build_registry(cfg)
    model = reg[args.model]
    cap = getattr(model, "max_train_rows", None)
    rng = np.random.default_rng(cfg["sampling"]["seed"])
    if cap and len(Ztr) > cap:
        keep = rng.choice(len(Ztr), cap, replace=False)
        Ztr, tr = Ztr[keep], tr.iloc[keep]

    ctx = FitContext(Ztr, tr["duration"].to_numpy(), tr["event"].to_numpy(),
                     Zva, va["duration"].to_numpy(), va["event"].to_numpy(),
                     age_train=tr["t_stop"].to_numpy(),
                     age_valid=va["t_stop"].to_numpy(),
                     names=prep.names, seed=1)
    fitted = model.fit(ctx, model.param_space(rng, 1)[0])

    if len(te) > args.n_eval:
        te = te.sample(args.n_eval, random_state=0)
    Zte = prep.transform(te)
    dur, ev, age = (te["duration"].to_numpy(), te["event"].to_numpy(),
                    te["t_stop"].to_numpy())

    base = brier_at(fitted.predict_survival(Zte, grid, age=age), dur, ev,
                    args.horizon, grid)
    rows = []
    for j, name in enumerate(prep.names):
        losses = []
        for r in range(args.repeats):
            Zp = Zte.copy()
            Zp[:, j] = Zp[rng.permutation(len(Zp)), j]
            losses.append(brier_at(fitted.predict_survival(Zp, grid, age=age),
                                   dur, ev, args.horizon, grid))
        rows.append({"feature": name, "brier_base": base,
                     "brier_permuted": float(np.mean(losses)),
                     "importance": float(np.mean(losses) - base)})
    out = (pd.DataFrame(rows).sort_values("importance", ascending=False)
           .assign(model=args.model, feature_set=args.feature_set,
                   fold=args.fold,
                   explained_quantity=f"P(T > {args.horizon} | X)"))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT,
                        f"permutation_importance_{args.model}_h{args.horizon}.csv")
    out.to_csv(path, index=False)
    print(out.head(20)[["feature", "importance"]].to_string(index=False))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
