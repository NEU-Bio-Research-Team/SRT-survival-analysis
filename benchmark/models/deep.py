"""B6, B7, B8 - the three pycox comparators, and why the benchmark needs all three.

They are not three attempts at the same thing. Each one drops a different
assumption, and the design of the leaderboard is that the gaps BETWEEN them are
readable:

    DeepSurv   nonlinear, still proportional hazards
    Cox-Time   nonlinear, and the risk score is a function of time as well
    DeepHit    nonlinear, no hazard structure at all - a discrete distribution
               over event times, learned directly

So DeepSurv minus CoxPH prices the neural representation while holding
proportionality fixed; Cox-Time minus DeepSurv prices dropping proportionality
while holding the network fixed. Running only one of them would confound the two,
and "a deep model beat Cox" would say nothing about which assumption was the
binding one - which is the actual research question (plan section 26).

All three share one architecture family, one optimiser, one early-stopping rule
and one tuning budget, because a comparison in which one model was tuned harder
than another measures the tuning.
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import torch
import torchtuples as tt
from pycox.models import CoxPH as _PycoxCoxPH
from pycox.models import CoxTime as _PycoxCoxTime
from pycox.models import DeepHitSingle as _PycoxDeepHit
from pycox.models.cox_time import MLPVanillaCoxTime

from .base import FitContext, SurvivalModel, interp_survival

torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))

# This machine has a 6 GB laptop GPU. It is a large speed-up and a small memory
# budget, so predictions are chunked and an out-of-memory failure demotes the
# model to CPU rather than losing the cell. Which device a cell actually used is
# not recorded as a result: the fitted parameters are the same either way.
_PRED_CHUNK = 8192


def _free():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _surv_df_chunked(model, Z):
    """predict_surv_df over slices, so a 60k test block never lands at once."""
    import pandas as pd
    parts = []
    for s in range(0, len(Z), _PRED_CHUNK):
        parts.append(model.predict_surv_df(Z[s:s + _PRED_CHUNK]))
        _free()
    return pd.concat(parts, axis=1)


def _shared_space(rng, n):
    space = []
    for nodes in ([64, 64], [128, 128], [256, 128], [64, 64, 64]):
        for drop in (0.1, 0.3):
            for lr in (0.01, 0.001):
                space.append({"nodes": nodes, "dropout": drop, "lr": lr})
    idx = rng.choice(len(space), size=min(n, len(space)), replace=False)
    return [space[i] for i in idx]


_CKPT_DIR = os.environ.get("SRT_BENCHMARK_TMP", tempfile.gettempdir())


def _callbacks(patience):
    """Early stopping, with its weight checkpoint kept out of the repository.

    torchtuples writes the restored-best weights to a file in the CURRENT working
    directory by default, which litters the project root with one .pt per fit.
    """
    path = os.path.join(_CKPT_DIR, f"pycox_ckpt_{os.getpid()}.pt")
    return [tt.callbacks.EarlyStopping(patience=patience, file_path=path)]


class _DeepBase(SurvivalModel):
    family = "deep"
    nonlinear = True
    budget = "deep"

    def __init__(self, max_epochs=40, patience=5, batch_size=1024):
        self.max_epochs, self.patience, self.batch_size = max_epochs, patience, batch_size

    def param_space(self, rng, n):
        return _shared_space(rng, n)

    @staticmethod
    def _y(dur, ev):
        return (np.asarray(dur, dtype="float32"), np.asarray(ev, dtype="float32"))

    # Validation is scored at the SAME batch size the model trains at.
    #
    # torchtuples defaults to scoring the whole validation block in batches of
    # 8224, which is where this benchmark's only out-of-memory failures came
    # from: DeepHit's ranking loss materialises a (batch x batch x n_cuts)
    # tensor, so an 8224-row scoring batch asks for tens of gigabytes at the end
    # of every epoch while training at 256 had been comfortable. Matching the two
    # is also the more defensible rule on its own terms - for a Cox partial
    # likelihood the loss VALUE depends on how the block is cut into batches, so
    # a validation score computed at a different batch size than the training
    # loss is not the same quantity, and early stopping is reading it.
    def _val_batch(self, batch: int) -> int:
        return batch


class DeepSurv(_DeepBase):
    """Cox's partial likelihood with a neural network in place of x'beta."""
    name = "DeepSurv"
    ph = True

    def fit(self, ctx: FitContext, params: dict) -> "DeepSurv":
        torch.manual_seed(ctx.seed)
        net = tt.practical.MLPVanilla(
            ctx.Z_train.shape[1], params["nodes"], 1, batch_norm=True,
            dropout=params["dropout"], output_bias=False)
        self.model_ = _PycoxCoxPH(net, tt.optim.Adam(params["lr"]))
        _free()
        self.model_.fit(
            ctx.Z_train, self._y(ctx.dur_train, ctx.ev_train),
            self.batch_size, self.max_epochs, _callbacks(self.patience),
            verbose=False,
            val_data=(ctx.Z_valid, self._y(ctx.dur_valid, ctx.ev_valid)),
            val_batch_size=self._val_batch(self.batch_size))
        self.model_.compute_baseline_hazards(
            input=ctx.Z_train, target=self._y(ctx.dur_train, ctx.ev_train))
        return self

    def predict_survival(self, Z, grid, age=None):
        df = _surv_df_chunked(self.model_, Z)
        return interp_survival(df.index.to_numpy(), df.to_numpy(), grid)


class CoxTime(_DeepBase):
    """Kvamme et al.: the risk score is f(x, t), so the ordering may cross."""
    name = "CoxTime"
    ph = False

    def fit(self, ctx: FitContext, params: dict) -> "CoxTime":
        torch.manual_seed(ctx.seed)
        self.labtrans_ = _PycoxCoxTime.label_transform()
        y_tr = self.labtrans_.fit_transform(*self._y(ctx.dur_train, ctx.ev_train))
        y_va = self.labtrans_.transform(*self._y(ctx.dur_valid, ctx.ev_valid))
        net = MLPVanillaCoxTime(ctx.Z_train.shape[1], params["nodes"],
                                batch_norm=True, dropout=params["dropout"])
        self.model_ = _PycoxCoxTime(net, tt.optim.Adam(params["lr"]),
                                    labtrans=self.labtrans_)
        _free()
        self.model_.fit(
            ctx.Z_train, y_tr, self.batch_size, self.max_epochs,
            _callbacks(self.patience), verbose=False,
            val_data=tt.tuplefy(ctx.Z_valid, y_va),
            val_batch_size=self._val_batch(self.batch_size))
        # pycox's Cox-Time baseline estimator walks the risk sets in order and
        # refuses an unsorted target, so hand it the training block sorted by
        # duration. Sorting changes nothing about the fitted network.
        order = np.argsort(y_tr[0], kind="mergesort")
        self.model_.compute_baseline_hazards(
            input=ctx.Z_train[order],
            target=(y_tr[0][order], y_tr[1][order]))
        return self

    def predict_survival(self, Z, grid, age=None):
        df = _surv_df_chunked(self.model_, Z)
        return interp_survival(df.index.to_numpy(), df.to_numpy(), grid)


class DeepHit(_DeepBase):
    """A discrete distribution over event times, with a ranking penalty.

    Discretisation is not a nuisance here, but it has to be done deliberately.
    The panel's time really is discrete - a customs year - so the grid is set to
    the years themselves, `[0, 1, 2, ..., max]`, rather than to pycox's default
    equidistant split of the duration range.

    That default is not a cosmetic difference. With twelve equidistant cuts over
    sixteen years the grid points land at 0, 1.455, 2.909, ... and there is no
    column at one year at all: a one-year survival probability then has to be
    read off the cut at zero, where every relationship sits at 0.987 with a
    standard deviation of 0.007. Scoring that column ranks pure noise, and it
    does so with enough consistency to produce a time-dependent AUC of 0.29 -
    an inverted ordering that looks like a broken model rather than a misread
    grid. Integer cuts put a column exactly where the metric asks for one.
    """
    name = "DeepHit"
    ph = False

    def param_space(self, rng, n):
        base = _shared_space(rng, n)
        for p, a in zip(base, rng.choice([0.0, 0.2, 0.5], size=len(base))):
            p["alpha"] = float(a)
        return base

    # DeepHit's ranking loss materialises a (batch x batch x n_cuts) tensor, so
    # its memory grows with the SQUARE of the batch. At 1024 with a per-year grid
    # that is a 260 MB allocation per step, which a 6 GB laptop GPU shared with a
    # desktop session will not reliably give. 256 costs a quarter of the compute
    # per step and a sixteenth of the memory. It is a deviation from the shared
    # batch size and it is only applied to the model that needs it.
    max_batch = 256

    def fit(self, ctx: FitContext, params: dict) -> "DeepHit":
        torch.manual_seed(ctx.seed)
        batch = min(self.batch_size, self.max_batch)
        # one grid point per year, so that S(u) is read at u and not interpolated
        cuts = np.arange(0, int(np.max(ctx.dur_train)) + 1, dtype="float64")
        self.labtrans_ = _PycoxDeepHit.label_transform(cuts)
        y_tr = self.labtrans_.fit_transform(*self._y(ctx.dur_train, ctx.ev_train))
        y_va = self.labtrans_.transform(*self._y(ctx.dur_valid, ctx.ev_valid))
        net = tt.practical.MLPVanilla(ctx.Z_train.shape[1], params["nodes"],
                                      self.labtrans_.out_features, batch_norm=True,
                                      dropout=params["dropout"])
        self.model_ = _PycoxDeepHit(net, tt.optim.Adam(params["lr"]),
                                    alpha=params.get("alpha", 0.2), sigma=0.1,
                                    duration_index=self.labtrans_.cuts)
        _free()
        self.model_.fit(
            ctx.Z_train, y_tr, batch, self.max_epochs,
            _callbacks(self.patience), verbose=False,
            val_data=(ctx.Z_valid, y_va),
            val_batch_size=self._val_batch(batch))
        return self

    def predict_survival(self, Z, grid, age=None):
        df = _surv_df_chunked(self.model_, Z)
        return interp_survival(df.index.to_numpy(), df.to_numpy(), grid)
