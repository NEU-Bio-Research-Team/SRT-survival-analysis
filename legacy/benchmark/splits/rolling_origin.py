"""Rolling-origin splits, and the censoring rule that makes them honest.

Disjoint origin years are not enough. Consider fold 1, trained on origins
2003-2013. A relationship with origin 2013 that finally dies in 2018 carries
`duration_u = 6, event_u = 1` in the frozen matrix - but in 2013 nobody could
know that. Train on it and the model has read the test period's outcomes through
the label, which is the same leak as a random split, wearing a different hat.

So every block is re-censored at its own information horizon:

    observed_through = the last year whose trade filing the block is allowed to
                       have seen.

An origin in year t whose spell is still alive at `observed_through` contributes
    duration = observed_through - t,  event = 0
because all that is known is that it did not fail in any of the years
t+1 .. observed_through. An origin whose spell was last alive in D, with
D <= observed_through - 1, contributes the real
    duration = D - t + 1,  event = 1.
(`D = observed_through` gives nothing: the death would fall in the first
unobserved year, so it is censored like any survivor.)

An origin in the final year of its own block has censoring time zero and carries
no information at all; it is dropped. That is why a train block written
[2003, 2013] yields effective origins 2003-2012.

Test blocks read outcomes forward to `window.outcome_observed_through` (2025),
which is what a retrospective evaluator genuinely has.

With the panel's gap rule (`target.gap_tolerance = g` in the benchmark config,
panel v2 onwards) a death is only a death once g+1 empty years have been seen:
a relationship absent for g years and then back is one spell. The rule above
then becomes censor_block_gap():
    event     only if the spell died with D <= observed_through - 1 - g;
    otherwise censored at A - t, where A is the last year <= observed_through
              in which the relationship was actually alive.
The plain rule reads a death confirmed by filings after the block's horizon
(D = observed_through - 1 needs observed_through + g), and credits a spell
whose importer stopped filing before the horizon with survival up to it.
Configs without `gap_tolerance` keep the plain rule, so earlier runs reproduce.

Sampling, when the caps in benchmark.yaml bite, is drawn over SPELLS rather than
rows, so a spell is wholly in or wholly out and the within-spell dependence is
not broken. The drawn rows are identical for every model in the cell.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MATRIX = os.path.join(ROOT, "data", "interim", "benchmark_matrix.parquet")


def load_yaml(name: str) -> dict:
    with open(os.path.join(ROOT, "legacy", "benchmark", "config", name),
              encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_matrix(path: str | None = None) -> pd.DataFrame:
    """The frozen matrix, with the feature columns held in single precision.

    889k origins x 60 float64 features is roughly half a gigabyte before a fold
    is even cut, and the copies made while censoring push the peak past what a
    7 GB laptop has spare - this benchmark has already been killed once by the
    out-of-memory reaper at that point. The preprocessor casts to float32 on the
    way into every model anyway, so carrying float64 through the split buys
    nothing but the peak.

    `path` overrides the default MATRIX (used for a rescoped run, e.g. the
    EU27-only matrix, without touching the default global one).
    """
    df = pd.read_parquet(path or MATRIX)
    f64 = [c for c in df.columns if df[c].dtype == "float64"]
    df[f64] = df[f64].astype("float32")
    return df


def censor_block(df: pd.DataFrame, lo: int, hi: int,
                 observed_through: int) -> pd.DataFrame:
    """Origins in [lo, hi], with outcomes truncated at `observed_through`."""
    b = df[(df["year"] >= lo) & (df["year"] <= hi)].copy()
    cens_time = observed_through - b["year"]           # years of follow-up known
    died_in_time = (b["event_u"] == 1) & (b["last_alive_year"] <= observed_through - 1)
    b["duration"] = np.where(died_in_time, b["duration_u"], cens_time)
    b["event"] = np.where(died_in_time, 1, 0).astype("int8")
    b = b[b["duration"] >= 1]          # zero follow-up carries no information
    return b.reset_index(drop=True)


def last_alive_by(df: pd.DataFrame, horizon: int) -> pd.Series:
    """spell_id -> the last origin year <= `horizon`. Origins are exactly the
    years a spell is alive (gap-filled padding rows are not origins), so this
    is the last year the relationship was seen alive by the horizon."""
    return df.loc[df["year"] <= horizon].groupby("spell_id")["year"].max()


def censor_block_gap(df: pd.DataFrame, lo: int, hi: int, observed_through: int,
                     gap: int, full: pd.DataFrame) -> pd.DataFrame:
    """censor_block() under the panel's gap rule (see the module docstring).
    `full` is the whole matrix, so A can reach years outside the scored window."""
    b = df[(df["year"] >= lo) & (df["year"] <= hi)].copy()
    A = b["spell_id"].map(last_alive_by(full, observed_through)).to_numpy()
    confirmed = (b["event_u"] == 1) & \
        (b["last_alive_year"] <= observed_through - 1 - gap)
    b["duration"] = np.where(confirmed, b["duration_u"], A - b["year"])
    b["event"] = np.where(confirmed, 1, 0).astype("int8")
    b = b[b["duration"] >= 1]          # zero follow-up carries no information
    return b.reset_index(drop=True)


def subsample(df: pd.DataFrame, max_rows: int, seed: int) -> pd.DataFrame:
    """Draw whole spells until the row cap is reached. Deterministic."""
    if max_rows is None or len(df) <= max_rows:
        return df
    rng = np.random.default_rng(seed)
    spells = df["spell_id"].unique()
    rng.shuffle(spells)
    sizes = df.groupby("spell_id", sort=False).size()
    take, total = [], 0
    for s in spells:
        n = int(sizes[s])
        if total + n > max_rows:
            continue
        take.append(s)
        total += n
        if total >= max_rows * 0.995:
            break
    return df[df["spell_id"].isin(set(take))].reset_index(drop=True)


def make_folds(df: pd.DataFrame | None = None, benchmark_config: str = "benchmark.yaml",
               splits_config: str = "splits.yaml", matrix_path: str | None = None):
    """Yield (fold_id, train, valid, test) frames, already censored and sampled.

    `benchmark_config`/`splits_config` name files inside benchmark/config/;
    `matrix_path` overrides the default frozen matrix. All three default to
    the original global-scope run, so existing callers are unaffected.
    """
    cfg = load_yaml(benchmark_config)
    spl = load_yaml(splits_config)
    if df is None:
        df = load_matrix(matrix_path)
    full = df
    df = df[df["in_leaderboard_window"] == 1]
    smp, seed = cfg["sampling"], cfg["sampling"]["seed"]
    final_obs = cfg["window"]["outcome_observed_through"]
    gap = cfg.get("target", {}).get("gap_tolerance")
    if gap is None:
        censor = censor_block
    else:
        def censor(d, lo, hi, obs):
            return censor_block_gap(d, lo, hi, obs, gap, full)

    for fold in spl["folds"]:
        tr_lo, tr_hi = fold["train"]
        va_lo, va_hi = fold["valid"]
        te_lo, te_hi = fold["test"]
        # A block may only see filings up to the end of its own window; the test
        # block is scored retrospectively and may read to the end of the data.
        train = censor(df, tr_lo, tr_hi, tr_hi)
        valid = censor(df, va_lo, va_hi, va_hi)
        test = censor(df, te_lo, te_hi, final_obs)

        train = subsample(train, smp["train_max_rows"], seed + fold["id"])
        valid = subsample(valid, smp["valid_max_rows"], seed + 100 + fold["id"])
        test = subsample(test, smp["test_max_rows"], seed + 200 + fold["id"])
        yield fold["id"], train, valid, test


if __name__ == "__main__":
    print(f"{'fold':>4} {'block':<6} {'years':<11} {'rows':>9} {'spells':>8} "
          f"{'events':>8} {'evt%':>6} {'med.fu':>7} {'maxfu':>6}")
    spl = load_yaml("splits.yaml")
    for (fid, tr, va, te) in make_folds():
        f = next(x for x in spl["folds"] if x["id"] == fid)
        for nm, b in (("train", tr), ("valid", va), ("test", te)):
            lo, hi = f[nm if nm != "valid" else "valid"]
            print(f"{fid:>4} {nm:<6} {f'{lo}-{hi}':<11} {len(b):>9,} "
                  f"{b.spell_id.nunique():>8,} {int(b.event.sum()):>8,} "
                  f"{b.event.mean():>5.1%} {b.duration.median():>7.0f} "
                  f"{b.duration.max():>6.0f}")
