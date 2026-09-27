"""Random-effect binary panel models for the inference branch (Đợt 4).

1. Grouped-time cloglog with a SHARED gamma frailty per relation
   (importer x family), integrated in closed form - a true frailty likelihood,
   not a post-hoc correction (design doc §6.3):

       P(y_i = 1 | v) = 1 - exp(-v c_i),  c_i = exp(eta_i),  v ~ Gamma(1/theta, theta)

   For relation g with non-event rows R0 and event rows K (one per ended spell):

       L_g = E_v[ exp(-v A_g) prod_{j in K} (1 - exp(-v c_j)) ],  A_g = sum_{R0} c_i
           = sum_{S subset K} (-1)^{|S|} (1 + theta (A_g + c_S))^(-1/theta)

   by expanding the product (inclusion-exclusion) and using the gamma Laplace
   transform. K is small (<= a handful of spells per relation).

2. Random-intercept logit / probit per relation (Besedeš-Prusa, Lejour),
   integrated by adaptive-free Gauss-Hermite quadrature.

Both are fit by L-BFGS in float64 torch; the covariance is the inverse of the
observed information (autograd Hessian).
"""

from __future__ import annotations

import itertools

import numpy as np
import torch

torch.set_default_dtype(torch.float64)
MAX_EVENTS_EXACT = 10


def _groups(group):
    codes, inv = np.unique(group, return_inverse=True)
    return len(codes), inv


def _fit(nll, p0, max_iter=500):
    p = torch.tensor(p0, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.LBFGS([p], lr=1.0, max_iter=max_iter, tolerance_grad=1e-9,
                            tolerance_change=1e-12, history_size=50,
                            line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        v = nll(p)
        v.backward()
        return v

    for _ in range(5):
        opt.step(closure)
    with torch.no_grad():
        final = float(nll(p))
    H = torch.autograd.functional.hessian(nll, p.detach()).numpy()
    g = torch.autograd.grad(nll(p), p)[0].detach().numpy()
    try:
        cov = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(H)
    return p.detach().numpy(), cov, final, float(np.abs(g).max())


class GammaFrailtyCloglog:
    def fit(self, X, y, group, beta0=None, log_theta0=np.log(0.5)):
        X = np.asarray(X, dtype="float64")
        y = np.asarray(y, dtype="float64")
        G, inv = _groups(group)
        ev_rows = np.flatnonzero(y == 1)
        ne_rows = np.flatnonzero(y == 0)
        # events per group, padded, bucketed by count
        ev_g = inv[ev_rows]
        order = np.argsort(ev_g, kind="mergesort")
        ev_rows, ev_g = ev_rows[order], ev_g[order]
        k_of_g = np.bincount(ev_g, minlength=G)
        if k_of_g.max() > MAX_EVENTS_EXACT:
            raise ValueError(f"a relation has {k_of_g.max()} events; exact expansion capped")
        start = np.r_[0, np.cumsum(k_of_g)[:-1]]
        buckets = {}
        for k in range(0, k_of_g.max() + 1):
            gs = np.flatnonzero(k_of_g == k)
            if not len(gs):
                continue
            if k == 0:
                buckets[0] = (torch.as_tensor(gs), None, None)
                continue
            idx = start[gs][:, None] + np.arange(k)[None, :]
            rows = ev_rows[idx]                                   # (Gk, k)
            subsets = np.array(list(itertools.product([0, 1], repeat=k)), dtype="float64")
            sign = (-1.0) ** subsets.sum(1)
            buckets[k] = (torch.as_tensor(gs), torch.as_tensor(rows),
                          (torch.as_tensor(subsets), torch.as_tensor(sign)))
        Xt = torch.as_tensor(X)
        ne_t, ne_g = torch.as_tensor(ne_rows), torch.as_tensor(inv[ne_rows])
        kx = X.shape[1]

        def nll(p):
            beta, th = p[:kx], torch.exp(p[kx])
            c = torch.exp(torch.clamp(Xt @ beta, -30, 8))
            A = torch.zeros(G).index_add_(0, ne_g, c[ne_t])
            total = torch.zeros(())
            for k, (gs, rows, sub) in buckets.items():
                Ag = A[gs]
                if k == 0:
                    total = total - torch.log1p(th * Ag).sum() / th
                    continue
                subsets, sign = sub
                cs = c[rows] @ subsets.T                            # (Gk, 2^k)
                terms = torch.exp(-torch.log1p(th * (Ag[:, None] + cs)) / th)
                Lg = (terms * sign[None, :]).sum(1)
                total = total + torch.log(torch.clamp(Lg, min=1e-300)).sum()
            return -total

        p0 = np.r_[np.zeros(kx) if beta0 is None else beta0, log_theta0]
        p, cov, f, gmax = _fit(nll, p0)
        self.beta_, self.log_theta_ = p[:kx], p[kx]
        self.theta_ = float(np.exp(p[kx]))
        self.cov_ = cov
        self.loglik_ = -f
        self.grad_max_ = gmax
        self.n_groups_ = G
        self.max_events_per_group_ = int(k_of_g.max())
        return self


def gh_nodes(n=15):
    x, w = np.polynomial.hermite.hermgauss(n)
    return x * np.sqrt(2.0), w / np.sqrt(np.pi)       # for u ~ N(0, 1)


class RandomInterceptBinary:
    """P(y=1|u) = F(eta + sigma u), u ~ N(0,1) shared within a relation."""

    def __init__(self, link="logit", n_nodes=15):
        self.link, self.n_nodes = link, n_nodes

    def fit(self, X, y, group, beta0=None, log_sigma0=np.log(0.5)):
        X = torch.as_tensor(np.asarray(X, dtype="float64"))
        yt = torch.as_tensor(np.asarray(y, dtype="float64"))
        G, inv = _groups(group)
        gi = torch.as_tensor(inv)
        z, w = gh_nodes(self.n_nodes)
        zt, lw = torch.as_tensor(z), torch.log(torch.as_tensor(w))
        kx = X.shape[1]
        normal = torch.distributions.Normal(0.0, 1.0)

        def log_cdf_pair(eta):
            if self.link == "logit":
                return torch.nn.functional.logsigmoid(eta), torch.nn.functional.logsigmoid(-eta)
            return normal.cdf(eta).clamp(1e-300).log(), normal.cdf(-eta).clamp(1e-300).log()

        def nll(p):
            beta, s = p[:kx], torch.exp(p[kx])
            eta = (X @ beta)[:, None] + s * zt[None, :]              # (n, Q)
            l1, l0 = log_cdf_pair(eta)
            ll = yt[:, None] * l1 + (1 - yt[:, None]) * l0
            per_g = torch.zeros(G, len(z)).index_add_(0, gi, ll)     # (G, Q)
            return -torch.logsumexp(per_g + lw[None, :], dim=1).sum()

        p0 = np.r_[np.zeros(kx) if beta0 is None else beta0, log_sigma0]
        p, cov, f, gmax = _fit(nll, p0)
        self.beta_, self.sigma_ = p[:kx], float(np.exp(p[kx]))
        self.cov_ = cov
        self.loglik_ = -f
        self.grad_max_ = gmax
        # share of latent variance at the relation level
        resid = np.pi ** 2 / 3 if self.link == "logit" else 1.0
        self.rho_ = self.sigma_ ** 2 / (self.sigma_ ** 2 + resid)
        self.n_groups_ = G
        return self
