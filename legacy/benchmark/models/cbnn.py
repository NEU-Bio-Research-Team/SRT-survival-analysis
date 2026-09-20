"""B9 - Case-Base Neural Network (Islam et al. 2024), implemented here.

No library ships it, so this is the paper's construction written out.

The idea is a change of sampling frame. Instead of a partial likelihood over risk
sets, case-base sampling draws a *base series* of person-moments uniformly from
the total follow-up time and pairs it with the *case series* of the moments at
which failures actually occurred. Whether a given moment is a case then becomes
an ordinary binary outcome, and the hazard is recovered by correcting for the
sampling rate with a fixed offset:

    P(Y = 1 | X, t) = sigmoid( f(X, t) + log(B / b) ),   log h(t | X) = f(X, t)

where B is the total person-time in the block and b the number of base moments
drawn. The offset is not a tuning knob; it is what makes the fitted logit a
hazard rather than a sampling artefact.

Why it belongs in this benchmark rather than being one more neural comparator:
follow-up time is an INPUT to the network, so a term of the form x_j * g(t) can
be learned without anyone specifying g in advance. That is exactly the hypothesis
the trade side of this project cares about - that the effect of launch scale, or
of a tariff, is not constant over the life of a relationship but concentrated in
its first years. DeepHit and Cox-Time also drop proportional hazards, but neither
of them gives back a full hazard surface in t that can be read that way.

Time enters as time SINCE the prediction origin. The relationship's age at the
origin is already a covariate, so f(X, t) is free to represent an interaction
between how old a relationship is and how its risk evolves from here.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from .base import FitContext, SurvivalModel


class _Net(nn.Module):
    def __init__(self, n_in: int, nodes: list[int], dropout: float):
        super().__init__()
        layers, prev = [], n_in + 1        # +1 for follow-up time
        for h in nodes:
            layers += [nn.Linear(prev, h), nn.BatchNorm1d(h), nn.ReLU(),
                       nn.Dropout(dropout)]
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x, t):
        return self.net(torch.cat([x, t], dim=1)).squeeze(-1)


class CBNN(SurvivalModel):
    name = "CBNN"
    family = "deep"
    nonlinear = True
    ph = False
    budget = "deep"

    def __init__(self, max_epochs=40, patience=5, batch_size=1024):
        self.max_epochs, self.patience, self.batch_size = max_epochs, patience, batch_size

    def param_space(self, rng, n):
        space = []
        for nodes in ([64, 64], [128, 128], [256, 128]):
            for drop in (0.1, 0.3):
                for lr in (0.01, 0.001):
                    for ratio in (2, 5):
                        space.append({"nodes": nodes, "dropout": drop,
                                      "lr": lr, "base_ratio": ratio})
        idx = rng.choice(len(space), size=min(n, len(space)), replace=False)
        return [space[i] for i in idx]

    # ------------------------------------------------------- case-base sample
    @staticmethod
    def _sample(Z, dur, ev, ratio, rng):
        """Case series = every failure. Base series = person-moments drawn
        uniformly over follow-up time, which is what the offset then corrects for."""
        d = np.asarray(dur, dtype="float64")
        e = np.asarray(ev, dtype="int64")
        case_idx = np.flatnonzero(e == 1)
        if case_idx.size == 0:
            raise ValueError("no failures in the block; case-base is undefined")
        B = float(d.sum())
        b = int(min(len(d) * 4, max(1000, ratio * case_idx.size)))

        # a subject is drawn in proportion to how long it was under observation
        p = d / B
        base_subj = rng.choice(len(d), size=b, p=p)
        # and a moment uniformly inside that subject's follow-up, on the year grid
        base_t = np.ceil(rng.random(b) * d[base_subj])
        base_t = np.clip(base_t, 1.0, None)

        idx = np.concatenate([case_idx, base_subj])
        t = np.concatenate([d[case_idx], base_t]).astype("float32")
        y = np.concatenate([np.ones(case_idx.size), np.zeros(b)]).astype("float32")
        offset = float(np.log(B / b))
        return Z[idx], t, y, offset

    # ------------------------------------------------------------------- fit
    def fit(self, ctx: FitContext, params: dict) -> "CBNN":
        rng = np.random.default_rng(ctx.seed)
        torch.manual_seed(ctx.seed)
        Xtr, ttr, ytr, off_tr = self._sample(ctx.Z_train, ctx.dur_train,
                                             ctx.ev_train, params["base_ratio"], rng)
        Xva, tva, yva, off_va = self._sample(ctx.Z_valid, ctx.dur_valid,
                                             ctx.ev_valid, params["base_ratio"], rng)
        self.t_scale_ = float(max(1.0, np.max(ttr)))

        net = _Net(ctx.Z_train.shape[1], params["nodes"], params["dropout"])
        opt = torch.optim.Adam(net.parameters(), lr=params["lr"])
        lossf = nn.BCEWithLogitsLoss()

        Xtr_t = torch.from_numpy(np.ascontiguousarray(Xtr))
        ttr_t = torch.from_numpy(ttr / self.t_scale_).unsqueeze(1)
        ytr_t = torch.from_numpy(ytr)
        Xva_t = torch.from_numpy(np.ascontiguousarray(Xva))
        tva_t = torch.from_numpy(tva / self.t_scale_).unsqueeze(1)
        yva_t = torch.from_numpy(yva)

        best, bad, best_state = np.inf, 0, None
        n = len(ytr_t)
        for _ in range(self.max_epochs):
            net.train()
            perm = torch.randperm(n)
            for s in range(0, n, self.batch_size):
                j = perm[s:s + self.batch_size]
                if len(j) < 2:
                    continue
                opt.zero_grad()
                logit = net(Xtr_t[j], ttr_t[j]) + off_tr
                loss = lossf(logit, ytr_t[j])
                loss.backward()
                opt.step()
            net.eval()
            with torch.no_grad():
                vl = float(lossf(net(Xva_t, tva_t) + off_va, yva_t))
            if vl < best - 1e-6:
                best, bad = vl, 0
                best_state = {k: v.clone() for k, v in net.state_dict().items()}
            else:
                bad += 1
                if bad >= self.patience:
                    break
        if best_state is not None:
            net.load_state_dict(best_state)
        net.eval()
        self.net_ = net
        self.val_loss_ = best
        return self

    # --------------------------------------------------------------- predict
    def predict_survival(self, Z, grid, age=None):
        """S(u | X) = exp( - sum_{k=1..u} h(k | X) ), the hazard read off f(X, k).

        Unit-width rectangles rather than a finer quadrature: the panel's time is
        a customs year, so a hazard between two years is not a quantity the data
        has an opinion about.
        """
        X = torch.from_numpy(np.ascontiguousarray(Z))
        umax = max(grid)
        H = np.zeros(len(Z))
        curves = {}
        with torch.no_grad():
            for k in range(1, umax + 1):
                tk = torch.full((len(Z), 1), k / self.t_scale_, dtype=torch.float32)
                f = self.net_(X, tk).numpy().astype("float64")
                H = H + np.exp(np.clip(f, -30, 10))
                curves[k] = np.exp(-H)
        return np.clip(np.column_stack([curves[u] for u in grid]), 1e-12, 1.0)
