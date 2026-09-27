"""Task views cut at an information cutoff (plan Đợt 0.2; tasks.yaml).

A view is the base table restricted to some origin years, with the outcome
re-read as it was knowable at calendar year C (`cutoff`). The rule, with gap g
and H = C - g (tasks.yaml `censoring_rule`):

    E >= H            censored at H - t   (alive, or bridging, through H)
    E <  H and died   event at    E - t + 1
    E <  H otherwise  censored at E - t   (importer stopped filing / HS revision)
    duration <= 0     dropped

`E` is the spell's last active year in the full panel. The first branch is
what keeps censoring independent of the outcome: a death at E >= H is not yet
confirmable, and so is every survivor, and both are censored at the same H.

D view  = origins whose one-year outcome is known: duration >= 1, and
          y = 1{event and duration == 1}. An unconfirmed next year never
          becomes y = 0 - it has duration 0 and is dropped (masked).
L view  = the same rows with (duration, event).
Both views of one cutoff therefore contain exactly the same cohort.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

GAP = 1


def recensor(df: pd.DataFrame, cutoff: int, gap: int = GAP) -> pd.DataFrame:
    """Add `duration`, `event` as knowable at `cutoff`; drop zero follow-up."""
    H = cutoff - gap
    t = df["year"].to_numpy(dtype="int32")
    E = df["_y_E"].to_numpy(dtype="int32")
    died = df["_y_died"].to_numpy(dtype="int8") == 1
    alive_H = E >= H
    ev = (~alive_H) & died
    dur = np.where(alive_H, H - t, np.where(ev, E - t + 1, E - t))
    out = df.assign(duration=dur.astype("int16"), event=ev.astype("int8"))
    return out[out["duration"] >= 1].reset_index(drop=True)


def view(base: pd.DataFrame, origins: tuple[int, int] | int, cutoff: int,
         gap: int = GAP, task: str = "L") -> pd.DataFrame:
    """Origins in [lo, hi] (inclusive) read at `cutoff`."""
    lo, hi = (origins, origins) if isinstance(origins, int) else origins
    b = base[(base["year"] >= lo) & (base["year"] <= hi)]
    v = recensor(b, cutoff, gap)
    if task == "D":
        v = v.assign(y=((v["event"] == 1) & (v["duration"] == 1)).astype("int8"))
    return v


def training_view(base, first_origin: int, cutoff: int, task: str, gap: int = GAP):
    """Every origin that has any follow-up at `cutoff` (t <= cutoff - gap - 1)."""
    return view(base, (first_origin, cutoff - gap - 1), cutoff, gap, task)


def cohort_hash(v: pd.DataFrame) -> str:
    """Identity of a scored cohort: keys and outcomes, order-independent."""
    cols = ["spell_id", "year", "duration", "event"]
    k = v[cols].sort_values(["spell_id", "year"])
    h = hashlib.sha1()
    for c in cols:
        h.update(pd.util.hash_pandas_object(k[c], index=False).to_numpy().tobytes())
    return h.hexdigest()[:16]


def fold_views(base: pd.DataFrame, splits: dict, fold: str, task: str,
               stage: str, first_origin: int | None = None,
               test_read_to: int | None = None, gap: int = GAP):
    """(train, eval) for a fold.

    stage = "valid": train at inner_cutoff, score the validation origin read
            to refit_cutoff.
    stage = "test":  train at refit_cutoff, score the test origin read to the
            end of the data.
    """
    f = splits["folds"][fold]
    spec = f[task]
    first = first_origin or splits["first_training_origin"]
    if stage == "valid":
        train = training_view(base, first, spec["inner_cutoff"], task, gap)
        ev = view(base, spec["valid_origin"], spec["refit_cutoff"], gap, task)
    elif stage == "test":
        train = training_view(base, first, spec["refit_cutoff"], task, gap)
        ev = view(base, f["test_origin"], test_read_to or splits["test_read_to"],
                  gap, task)
    else:
        raise ValueError(stage)
    return train, ev


def inference_view(base: pd.DataFrame, lo: int = 2012, hi: int = 2023,
                   cutoff: int = 2025, gap: int = GAP) -> pd.DataFrame:
    """Person-period rows of B0 with confirmed one-year outcomes (branch I)."""
    return view(base, (lo, hi), cutoff, gap, task="D")
