"""Neural adapters: D06 MLP hazard, L07 DeepSurv, L08 CoxTime, L09 DeepHitSingle,
L10 CBNN. Ported from legacy/benchmark/models/{deep,cbnn}.py with three changes:

* early stopping reads an inner holdout of TRAINING relations, not the scored
  validation cohort;
* one shared search space (depth, width, dropout, lr, weight decay, batch) for
  every neural model, plus DeepHit's (alpha, sigma) and CBNN's base ratio;
* CBNN's base series is 10-50x the case series (legacy used 2-5x, far below
  the paper's setting).

DeepSurv vs CoxTime share the network family, optimiser, early stopping and
budget, so their gap reads as the price of the PH assumption (C03).
"""

from __future__ import annotations

import os

import numpy as np
import torch
import torch.nn as nn

from stage2_benchmark import paths

from .base import FitData, Model, breslow_H0, inner_split, interp_survival, monotone, ph_survival

torch.set_num_threads(paths.N_THREADS)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MAX_EPOCHS = 100
PATIENCE = 8
PRED_CHUNK = 8192


def _free():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def nn_space(trial):
    n_layers = trial.suggest_int("n_layers", 1, 3)
    width = trial.suggest_categorical("width", [32, 64, 128, 256])
    return {"nodes": [width] * n_layers,
            "dropout": trial.suggest_float("dropout", 0.0, 0.5),
            "lr": trial.suggest_float("lr", 1e-4, 1e-2, log=True),
            "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-2, log=True),
            "batch_size": trial.suggest_categorical("batch_size", [256, 512, 1024])}


def mlp(n_in, nodes, dropout, n_out=1):
    layers, prev = [], n_in
    for h in nodes:
        layers += [nn.Linear(prev, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(dropout)]
        prev = h
    layers.append(nn.Linear(prev, n_out))
    return nn.Sequential(*layers)


def train_loop(net, loss_fn, tensors_tr, tensors_ho, params, seed):
    """Minibatch Adam with early stopping on the holdout loss; restores the best
    weights. `loss_fn(net, *batch)` returns a scalar."""
    torch.manual_seed(seed)
    net.to(DEVICE)
    opt = torch.optim.Adam(net.parameters(), lr=params["lr"],
                           weight_decay=params["weight_decay"])
    tr = [t.to(DEVICE) for t in tensors_tr]
    ho = [t.to(DEVICE) for t in tensors_ho]
    n, bs = len(tr[0]), params["batch_size"]
    best, bad, best_state, epochs = np.inf, 0, None, 0
    g = torch.Generator(device="cpu").manual_seed(seed)
    for ep in range(MAX_EPOCHS):
        net.train()
        perm = torch.randperm(n, generator=g).to(DEVICE)
        for s in range(0, n, bs):
            j = perm[s:s + bs]
            if len(j) < 2:
                continue
            opt.zero_grad()
            loss = loss_fn(net, *[t[j] for t in tr])
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            vl = float(loss_fn(net, *ho))
        epochs = ep + 1
        if vl < best - 1e-6:
            best, bad = vl, 0
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    if best_state is not None:
        net.load_state_dict(best_state)
    net.eval()
    return best, epochs


def _t(a, dtype=torch.float32):
    return torch.as_tensor(np.ascontiguousarray(a), dtype=dtype)


class _Neural(Model):
    family, nonlinear, stochastic, tuning = "neural", True, True, "optuna"
    uses_inner_holdout = True

    def suggest(self, trial):
        return nn_space(trial)

    def info(self):
        return {"holdout_loss": getattr(self, "best_", None),
                "epochs": getattr(self, "epochs_", None), "device": str(DEVICE)}


# ------------------------------------------------------------------ D06
class MLPHazard(_Neural):
    id, name, task, ph = "D06", "MLPHazard", "D", False

    def fit(self, data: FitData, params, seed=1):
        tr, ho = inner_split(data.relation, seed=11)
        self.net_ = mlp(data.Z.shape[1], params["nodes"], params["dropout"])
        bce = nn.BCEWithLogitsLoss()

        def loss(net, x, y):
            return bce(net(x).squeeze(-1), y)

        self.best_, self.epochs_ = train_loop(
            self.net_, loss, (_t(data.Z[tr]), _t(data.y[tr])),
            (_t(data.Z[ho]), _t(data.y[ho])), params, seed)
        return self

    def predict_proba(self, Z, age):
        out = []
        with torch.no_grad():
            for s in range(0, len(Z), PRED_CHUNK):
                out.append(torch.sigmoid(self.net_(_t(Z[s:s + PRED_CHUNK]).to(DEVICE))
                                         .squeeze(-1)).cpu().numpy())
        _free()
        return np.concatenate(out).astype("float64")


# ------------------------------------------------------------------ L07
def cox_ph_loss(log_h, d, e):
    """Breslow negative partial log-likelihood on a batch (pycox convention)."""
    order = torch.argsort(d, descending=True)
    lh, ev = log_h[order], e[order]
    gamma = lh.max()
    log_cumsum = torch.log(torch.cumsum(torch.exp(lh - gamma), 0)) + gamma
    return -((lh - log_cumsum) * ev).sum() / ev.sum().clamp(min=1)


class DeepSurv(_Neural):
    id, name, task, ph = "L07", "DeepSurv", "L", True

    def fit(self, data: FitData, params, seed=1):
        tr, ho = inner_split(data.relation, seed=11)
        self.net_ = mlp(data.Z.shape[1], params["nodes"], params["dropout"])

        def loss(net, x, d, e):
            return cox_ph_loss(net(x).squeeze(-1), d, e)

        # a random tie-break per row so ties in the annual clock are not
        # ordered by row position
        rng = np.random.default_rng(seed)
        dj = data.duration + rng.uniform(0, 1e-3, len(data.duration))
        self.best_, self.epochs_ = train_loop(
            self.net_, loss, (_t(data.Z[tr]), _t(dj[tr]), _t(data.event[tr])),
            (_t(data.Z[ho]), _t(dj[ho]), _t(data.event[ho])), params, seed)
        self.H0_ = breslow_H0(self._risk(data.Z), data.duration, data.event, 5)
        return self

    def _risk(self, Z):
        out = []
        with torch.no_grad():
            for s in range(0, len(Z), PRED_CHUNK):
                out.append(self.net_(_t(Z[s:s + PRED_CHUNK]).to(DEVICE)).squeeze(-1).cpu().numpy())
        _free()
        return np.concatenate(out).astype("float64")

    def predict_survival(self, Z, grid, age):
        return ph_survival(self._risk(Z), self.H0_, grid)


# ------------------------------------------------------------ L08, L09
def _pycox_ckpt():
    return [__import__("torchtuples").callbacks.EarlyStopping(
        patience=PATIENCE, file_path=os.path.join(paths.TMP, f"pycox_{os.getpid()}.pt"))]


class CoxTime(_Neural):
    id, name, task, ph = "L08", "CoxTime", "L", False

    def fit(self, data: FitData, params, seed=1):
        import torchtuples as tt
        from pycox.models import CoxTime as PC
        from pycox.models.cox_time import MLPVanillaCoxTime
        torch.manual_seed(seed)
        np.random.seed(seed)
        tr, ho = inner_split(data.relation, seed=11)
        d = data.duration.astype("float32")
        e = data.event.astype("float32")
        self.labtrans_ = PC.label_transform()
        y_tr = self.labtrans_.fit_transform(d[tr], e[tr])
        y_ho = self.labtrans_.transform(d[ho], e[ho])
        net = MLPVanillaCoxTime(data.Z.shape[1], params["nodes"], batch_norm=True,
                                dropout=params["dropout"])
        self.m_ = PC(net, tt.optim.Adam(lr=params["lr"], weight_decay=params["weight_decay"]),
                     labtrans=self.labtrans_, device=DEVICE)
        log = self.m_.fit(data.Z[tr], y_tr, params["batch_size"], MAX_EPOCHS, _pycox_ckpt(),
                          verbose=False, val_data=tt.tuplefy(data.Z[ho], y_ho),
                          val_batch_size=params["batch_size"])
        self.epochs_ = len(log.to_pandas())
        self.best_ = float(log.to_pandas()["val_loss"].min())
        order = np.argsort(y_tr[0], kind="mergesort")
        self.m_.compute_baseline_hazards(input=data.Z[tr][order],
                                         target=(y_tr[0][order], y_tr[1][order]),
                                         batch_size=PRED_CHUNK)
        _free()
        return self

    def predict_survival(self, Z, grid, age):
        parts = []
        for s in range(0, len(Z), PRED_CHUNK):
            df = self.m_.predict_surv_df(Z[s:s + PRED_CHUNK], batch_size=PRED_CHUNK)
            parts.append(interp_survival(df.index.to_numpy(), df.to_numpy(), grid))
            _free()
        return monotone(np.vstack(parts))


class DeepHitSingle(_Neural):
    id, name, task, ph = "L09", "DeepHitSingle", "L", False
    MAX_BATCH = 512   # ranking loss is O(batch^2 x cuts) in GPU memory

    def suggest(self, trial):
        p = nn_space(trial)
        p["alpha"] = trial.suggest_float("alpha", 0.0, 1.0)
        p["sigma"] = trial.suggest_categorical("sigma", [0.1, 0.25, 0.5, 1.0])
        return p

    def fit(self, data: FitData, params, seed=1):
        import torchtuples as tt
        from pycox.models import DeepHitSingle as PD
        torch.manual_seed(seed)
        np.random.seed(seed)
        tr, ho = inner_split(data.relation, seed=11)
        bs = min(params["batch_size"], self.MAX_BATCH)
        cuts = np.arange(0, int(data.duration.max()) + 1, dtype="float64")
        self.labtrans_ = PD.label_transform(cuts)
        d = data.duration.astype("float32")
        e = data.event.astype("float32")
        y_tr = self.labtrans_.fit_transform(d[tr], e[tr])
        y_ho = self.labtrans_.transform(d[ho], e[ho])
        net = tt.practical.MLPVanilla(data.Z.shape[1], params["nodes"],
                                      self.labtrans_.out_features, batch_norm=True,
                                      dropout=params["dropout"])
        self.m_ = PD(net, tt.optim.Adam(lr=params["lr"], weight_decay=params["weight_decay"]),
                     alpha=params["alpha"], sigma=params["sigma"],
                     duration_index=self.labtrans_.cuts, device=DEVICE)
        log = self.m_.fit(data.Z[tr], y_tr, bs, MAX_EPOCHS, _pycox_ckpt(), verbose=False,
                          val_data=(data.Z[ho], y_ho), val_batch_size=bs)
        self.epochs_ = len(log.to_pandas())
        self.best_ = float(log.to_pandas()["val_loss"].min())
        _free()
        return self

    def predict_survival(self, Z, grid, age):
        parts = []
        for s in range(0, len(Z), PRED_CHUNK):
            df = self.m_.predict_surv_df(Z[s:s + PRED_CHUNK], batch_size=PRED_CHUNK)
            parts.append(interp_survival(df.index.to_numpy(), df.to_numpy(), grid))
            _free()
        return monotone(np.vstack(parts))


# ------------------------------------------------------------------ L10
class _CBNet(nn.Module):
    def __init__(self, n_in, nodes, dropout):
        super().__init__()
        self.f = mlp(n_in + 1, nodes, dropout)

    def forward(self, x, t):
        return self.f(torch.cat([x, t], dim=1)).squeeze(-1)


class CBNN(_Neural):
    """Case-base neural network (Islam et al.): log h(t|x) = f(x, t), fitted as
    a logistic model on case moments vs uniformly sampled base moments with
    offset log(B/b). S(u) = exp(-sum_{k<=u} h(k|x)) on the year grid."""
    id, name, task, ph = "L10", "CBNN", "L", False

    def suggest(self, trial):
        p = nn_space(trial)
        p["base_ratio"] = trial.suggest_categorical("base_ratio", [10, 20, 50])
        return p

    @staticmethod
    def _sample(Z, d, e, ratio, rng):
        d = np.asarray(d, dtype="float64")
        case = np.flatnonzero(np.asarray(e) == 1)
        B = float(d.sum())
        b = int(min(ratio * max(case.size, 1), 20 * len(d)))
        subj = rng.choice(len(d), size=b, p=d / B)
        bt = np.clip(np.ceil(rng.random(b) * d[subj]), 1, None)
        idx = np.concatenate([case, subj])
        t = np.concatenate([d[case], bt]).astype("float32")
        y = np.concatenate([np.ones(case.size), np.zeros(b)]).astype("float32")
        return Z[idx], t, y, float(np.log(B / b))

    def fit(self, data: FitData, params, seed=1):
        rng = np.random.default_rng(seed)
        tr, ho = inner_split(data.relation, seed=11)
        Xt, tt_, yt, off_t = self._sample(data.Z[tr], data.duration[tr], data.event[tr],
                                          params["base_ratio"], rng)
        Xh, th, yh, off_h = self._sample(data.Z[ho], data.duration[ho], data.event[ho],
                                         params["base_ratio"], rng)
        self.t_scale_ = float(max(1.0, data.duration.max()))
        self.net_ = _CBNet(data.Z.shape[1], params["nodes"], params["dropout"])
        bce = nn.BCEWithLogitsLoss()

        def loss(net, x, t, y, off):
            return bce(net(x, t) + off, y)

        self.best_, self.epochs_ = train_loop(
            self.net_, loss,
            (_t(Xt), _t(tt_ / self.t_scale_).unsqueeze(1), _t(yt), torch.full((len(yt),), off_t)),
            (_t(Xh), _t(th / self.t_scale_).unsqueeze(1), _t(yh), torch.full((len(yh),), off_h)),
            params, seed)
        return self

    def predict_survival(self, Z, grid, age):
        umax = max(grid)
        out = np.empty((len(Z), len(grid)))
        with torch.no_grad():
            for s in range(0, len(Z), PRED_CHUNK):
                X = _t(Z[s:s + PRED_CHUNK]).to(DEVICE)
                H = torch.zeros(len(X), device=DEVICE)
                cur = {}
                for k in range(1, umax + 1):
                    tk = torch.full((len(X), 1), k / self.t_scale_, device=DEVICE)
                    H = H + torch.exp(torch.clamp(self.net_(X, tk), -30, 10))
                    cur[k] = torch.exp(-H).cpu().numpy()
                out[s:s + len(X)] = np.column_stack([cur[u] for u in grid])
        _free()
        return monotone(out)
