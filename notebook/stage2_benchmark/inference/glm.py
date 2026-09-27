"""Binary GLM by IRLS with cloglog / logit / probit links.

Shared by the D-task adapters (D01-D04) and the inference branch (Đợt 4). X
may be a dense ndarray or a scipy.sparse matrix (fixed-effect dummies), so a
design with a few hundred dummy columns on 200k rows stays small.

Returns the coefficients, the inverse Fisher information, and a function for
per-row score factors, from which cluster-robust sandwich covariances follow:

    score_i = g_i * x_i,   g_i = (y_i - mu_i) * mu'_i / (mu_i (1 - mu_i))
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.special import expit, ndtr

LINKS = ("cloglog", "logit", "probit")


def mean_and_deriv(eta, link):
    if link == "cloglog":
        eta = np.clip(eta, -30, 5)
        ee = np.exp(eta)
        mu = -np.expm1(-ee)
        dmu = np.exp(eta - ee)
    elif link == "logit":
        eta = np.clip(eta, -30, 30)
        mu = expit(eta)
        dmu = mu * (1 - mu)
    elif link == "probit":
        eta = np.clip(eta, -8.0, 8.0)
        mu = ndtr(eta)
        dmu = np.exp(-0.5 * eta ** 2) / np.sqrt(2 * np.pi)
    else:
        raise ValueError(link)
    return np.clip(mu, 1e-12, 1 - 1e-12), np.maximum(dmu, 1e-300)


def _xtwx(X, w):
    if sparse.issparse(X):
        return np.asarray((X.T @ (sparse.diags(w) @ X)).todense())
    return (X.T * w) @ X


def _xtv(X, v):
    return np.asarray(X.T @ v).ravel()


def fit_glm(X, y, link="cloglog", penalty=None, offset=None, weights=None,
            max_iter=60, tol=1e-8, beta0=None):
    """Penalised IRLS. `penalty` is a vector (per coefficient) of quadratic
    penalties added to X'WX (already multiplied by whatever scale the caller
    wants)."""
    n, k = X.shape
    y = np.asarray(y, dtype="float64")
    off = np.zeros(n) if offset is None else np.asarray(offset, dtype="float64")
    wt = np.ones(n) if weights is None else np.asarray(weights, dtype="float64")
    P = np.zeros(k) if penalty is None else np.asarray(penalty, dtype="float64")
    beta = np.zeros(k) if beta0 is None else np.asarray(beta0, dtype="float64").copy()
    converged = False
    ll_old = -np.inf
    for it in range(max_iter):
        eta = np.asarray(X @ beta).ravel() + off
        mu, dmu = mean_and_deriv(eta, link)
        var = mu * (1 - mu)
        w = wt * dmu ** 2 / var
        g = wt * (y - mu) * dmu / var
        H = _xtwx(X, w) + np.diag(P)
        grad = _xtv(X, g) - P * beta
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, grad, rcond=None)[0]
        # step halving on the penalised log-likelihood
        ll = loglik(X, y, beta, link, off, wt) - 0.5 * (P * beta ** 2).sum()
        t = 1.0
        for _ in range(20):
            nb = beta + t * step
            ll_new = loglik(X, y, nb, link, off, wt) - 0.5 * (P * nb ** 2).sum()
            if ll_new >= ll - 1e-10:
                break
            t /= 2
        beta = nb
        if np.max(np.abs(t * step)) < tol or abs(ll_new - ll_old) < tol * (1 + abs(ll_new)):
            converged = True
            break
        ll_old = ll_new
    eta = np.asarray(X @ beta).ravel() + off
    mu, dmu = mean_and_deriv(eta, link)
    var = mu * (1 - mu)
    w = wt * dmu ** 2 / var
    H = _xtwx(X, w) + np.diag(P)
    try:
        cov = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(H)
    return {"beta": beta, "cov": cov, "converged": converged, "iter": it + 1,
            "loglik": loglik(X, y, beta, link, off, wt), "link": link,
            "score_factor": wt * (y - mu) * dmu / var, "hessian": H}


def loglik(X, y, beta, link, off=None, wt=None):
    eta = np.asarray(X @ beta).ravel() + (0 if off is None else off)
    mu, _ = mean_and_deriv(eta, link)
    w = 1.0 if wt is None else wt
    return float(np.sum(w * (y * np.log(mu) + (1 - y) * np.log1p(-mu))))


def predict(X, beta, link, offset=None):
    eta = np.asarray(X @ beta).ravel() + (0 if offset is None else offset)
    return mean_and_deriv(eta, link)[0]


# ------------------------------------------------------ cluster sandwich
def cluster_meat(X, g, clusters):
    """sum_c (sum_{i in c} g_i x_i)(...)'  for one clustering."""
    codes, inv = np.unique(clusters, return_inverse=True)
    G = sparse.csr_matrix((g, (inv, np.arange(len(g)))), shape=(len(codes), len(g)))
    S = G @ X
    S = np.asarray(S.todense()) if sparse.issparse(S) else np.asarray(S)
    return S.T @ S, len(codes)


def cluster_cov(fit, X, clusters_a, clusters_b=None):
    """One-way or two-way (Cameron-Gelbach-Miller) cluster-robust covariance,
    with the usual G/(G-1) small-sample factor per clustering."""
    Hinv = fit["cov"]
    g = fit["score_factor"]
    Ma, Ga = cluster_meat(X, g, clusters_a)
    V = Hinv @ (Ma * Ga / max(Ga - 1, 1)) @ Hinv
    info = {"G_a": Ga}
    if clusters_b is not None:
        Mb, Gb = cluster_meat(X, g, clusters_b)
        inter = np.char.add(np.char.add(np.asarray(clusters_a, dtype=str), "|"),
                            np.asarray(clusters_b, dtype=str))
        Mab, Gab = cluster_meat(X, g, inter)
        Gmin = min(Ga, Gb)
        c = Gmin / max(Gmin - 1, 1)
        V = Hinv @ ((Ma + Mb - Mab) * c) @ Hinv
        # CGM can be non-PSD; eigenvalue fix (Cameron, Gelbach & Miller 2011)
        w, U = np.linalg.eigh((V + V.T) / 2)
        V = (U * np.maximum(w, 0)) @ U.T
        info.update(G_b=Gb, G_ab=Gab)
    return V, info
