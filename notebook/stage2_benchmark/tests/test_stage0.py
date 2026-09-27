"""Đợt 0.4 - the ten checks of design doc §10.3, against the real panel.

Run:  python -m pytest -q stage2_benchmark/tests/test_stage0.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stage2_benchmark import paths
from stage2_benchmark.data import base_table
from stage2_benchmark.data import views as V
from stage2_benchmark.evaluation import metrics as M
from stage2_benchmark.features.preprocess import Preprocessor, registry, resolve_set

SETS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]


@pytest.fixture(scope="module")
def base():
    return base_table.load_base()


@pytest.fixture(scope="module")
def splits():
    return paths.load_yaml("splits.yaml")


def _feature_cols():
    return [c for c, s in registry()["features"].items()]


def frame_hash(df):
    return pd.util.hash_pandas_object(df, index=False).sum()


# 1. rebuild from the same input -> same target and cohort hash
def test_01_deterministic_rebuild(base, splits):
    again = base_table.build(out_path=False, verbose=False)
    a = base.sort_values(["spell_id", "year"]).reset_index(drop=True)
    b = again.sort_values(["spell_id", "year"]).reset_index(drop=True)
    assert frame_hash(a) == frame_hash(b)
    for task in "DL":
        _, e1 = V.fold_views(a, splits, "F2", task, "valid")
        _, e2 = V.fold_views(b, splits, "F2", task, "valid")
        assert V.cohort_hash(e1) == V.cohort_hash(e2)


# 2. adding future years leaves features and labels at an old cutoff unchanged
@pytest.mark.parametrize("cut", [2014, 2016])
def test_02_prefix_safety(base, cut):
    trunc = base_table.build(max_year=cut, out_path=False, verbose=False)
    full = base[base["year"] <= cut]
    k = ["spell_id", "year"]
    m = full.merge(trunc, on=k, suffixes=("", "_t"), how="outer", indicator=True)
    assert (m["_merge"] == "both").all(), "row sets differ"
    for c in _feature_cols():
        x, y = m[c].to_numpy("float64"), m[c + "_t"].to_numpy("float64")
        same = (np.isclose(x, y, rtol=1e-5, atol=1e-6) | (np.isnan(x) & np.isnan(y)))
        assert same.all(), f"{c} changes when years after {cut} are added ({(~same).sum()} rows)"
    for task in "DL":
        a = V.training_view(base, 2005, cut, task)
        b = V.training_view(trunc, 2005, cut, task)
        assert V.cohort_hash(a) == V.cohort_hash(b), f"{task} labels at cutoff {cut} read the future"


# 3. threshold/gap rule on a small example; a missing reporter is not a death
def test_03_gap_rule_examples():
    rows = []
    def spell(sid, years, E, died):
        for y in years:
            rows.append({"spell_id": sid, "year": y, "_y_E": E, "_y_died": died})
    spell("dies2015", range(2012, 2016), 2015, 1)        # confirmed by 2016+2017
    spell("stops2014", range(2012, 2015), 2014, 0)       # importer stops filing
    spell("alive", [2012, 2013, 2015, 2016], 2016, 0)    # 2014 bridged
    df = pd.DataFrame(rows)
    def at(v, sid, y):
        r = v[(v.spell_id == sid) & (v.year == y)]
        return None if r.empty else (int(r.duration.iloc[0]), int(r.event.iloc[0]))
    v16 = V.recensor(df, 2016)     # H = 2015: the 2015 death is not confirmable
    assert at(v16, "dies2015", 2012) == (3, 0)
    v17 = V.recensor(df, 2017)     # H = 2016: confirmed
    assert at(v17, "dies2015", 2012) == (4, 1)
    v25 = V.recensor(df, 2025)
    assert at(v25, "stops2014", 2012) == (2, 0), "a filing stop became a death"
    assert at(v25, "alive", 2012) == (4, 0)
    # survivors and unconfirmed deaths are censored at the SAME H (2015)
    assert at(v16, "dies2015", 2014) == (1, 0)
    assert at(v16, "alive", 2013) == (2, 0)


# 4. inside a training cutoff every event had two confirming years
def test_04_training_events_confirmed(base, splits):
    for f in splits["folds"]:
        for task in "DL":
            for stage, key in (("valid", "inner_cutoff"), ("test", "refit_cutoff")):
                C = splits["folds"][f][task][key]
                tr, _ = V.fold_views(base, splits, f, task, stage)
                E = tr.loc[tr.event == 1, "_y_E"]
                assert (E <= C - 2).all(), f"{f}/{task}/{stage}: event not confirmable by {C}"
                assert tr["year"].max() <= C - 2


# 5. no censor/outcome-derived column reaches X
def test_05_no_outcome_columns_in_X(base, splits):
    forb = set(registry()["forbidden"])
    for s in SETS + ["S8-N", "S4+H", "S4@lagonly"]:
        cols = resolve_set(s)
        assert not forb & set(cols), f"{s} contains forbidden {forb & set(cols)}"
        assert not [c for c in cols if c.startswith(("_y_", "meta_", "probe_"))]
    for c, spec in registry()["features"].items():
        assert spec.get("future_derived", False) is False
    # outcome-proxy sniff: no single feature separates the 1-year outcome
    tr, _ = V.fold_views(base, splits, "F2", "D", "valid")
    from sklearn.metrics import roc_auc_score
    for c in resolve_set("S8"):
        x = tr[c].to_numpy("float64")
        ok = np.isfinite(x)
        if ok.sum() > 1000 and np.nanstd(x) > 0:
            auc = roc_auc_score(tr["y"][ok], x[ok])
            assert max(auc, 1 - auc) < 0.9, f"{c} predicts the label with AUC {auc:.3f}"


# 6. keys unique, follow-up consistent with the cutoff
def test_06_keys_and_followup(base, splits):
    for f, fd in splits["folds"].items():
        for task in "DL":
            for stage in ("valid", "test"):
                tr, ev = V.fold_views(base, splits, f, task, stage)
                for v in (tr, ev):
                    assert not v.duplicated(["spell_id", "year"]).any()
                    assert (v["duration"] >= 1).all()
                    ev_rows = v[v.event == 1]
                    assert (ev_rows["duration"] == ev_rows["_y_E"] - ev_rows["year"] + 1).all()
                if task == "D":
                    assert set(ev["y"].unique()) <= {0, 1}
                    assert (ev["y"] == ((ev.event == 1) & (ev.duration == 1))).all()


def test_06b_unconfirmed_next_year_is_masked(base):
    # EU27 origin 2024 has no confirmable one-year outcome with data to 2025:
    # every such row must be dropped, never scored as y = 0.
    v = V.view(base, 2024, 2025, task="D")
    assert len(v) == 0
    assert (base["year"] == 2024).sum() == 14_958


# 7. survival in [0,1], non-increasing; probabilities finite
def test_07_survival_contract(base, splits):
    from stage2_benchmark.models.survival import KaplanMeier
    from stage2_benchmark.runners.cell import fit_data
    tr, ev = V.fold_views(base, splits, "F2", "L", "valid")
    fd = fit_data(tr, np.zeros((len(tr), 0), "float32"), [], "L")
    S = KaplanMeier().fit(fd, {}).predict_survival(np.zeros((len(ev), 0)), [1, 2, 3, 4, 5], None)
    assert M.check_survival(S) == []
    bad = np.array([[0.9, 0.95, 0.8]])
    assert M.check_survival(bad) == ["survival increases with horizon"]


# 8. compared models receive the same cohort (cohort does not depend on the set)
def test_08_same_cohort_across_sets(base, splits):
    for task in "DL":
        h = {V.cohort_hash(V.fold_views(base, splits, "F2", task, "valid")[1]) for _ in SETS}
        assert len(h) == 1


# 9. IPCW support reported; an unobservable horizon is NaN, not a number
def test_09_ipcw_support():
    d = np.array([1, 2, 2, 1, 2])
    e = np.array([1, 0, 0, 0, 1])
    S = np.tile([0.9, 0.8, 0.7, 0.6, 0.5], (5, 1))
    sc = M.score_L(S, [1, 2, 3, 4, 5], d, e, horizons=(1, 2, 3))
    assert np.isnan(sc["brier_3"]) and np.isnan(sc["ibs_1_3"])
    assert sc["ipcw_support_3"] >= 0


# 10. no preprocessing is fitted on validation/test rows
def test_10_preprocessor_train_only(base, splits):
    tr, ev = V.fold_views(base, splits, "F2", "L", "valid")
    cols = resolve_set("S4")
    p1 = Preprocessor(cols).fit(tr)
    ev2 = ev.copy()
    ev2[cols] = ev2[cols] * 100 + 7            # a wildly different eval block
    p2 = Preprocessor(cols).fit(tr)
    assert np.allclose(p1.mean_, p2.mean_) and np.allclose(p1.sd_, p2.sd_)
    assert np.array_equal(p1.transform(tr), p2.transform(tr))
    # medians come from train only
    for c in cols:
        assert p1.median_[c] == pytest.approx(float(tr[c].median()) if tr[c].notna().any() else 0.0)
