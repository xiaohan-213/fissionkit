"""Data thinning for convolution-closed distributions.

Implements the thinning recipes of Neufeld, Dharamshi, Gao & Witten (JMLR 2024):
an observation X is split into K parts (Y_1, ..., Y_K) that are mutually
independent, sum (or otherwise recombine) to X, and each follow the same family
as X with a known parameter scaling.  All functions are vectorised over arrays
of arbitrary shape; the folds are returned stacked along a new trailing axis.

Supported families
------------------
poisson            X ~ Poi(mu)              -> Y_k ~ Poi(eps_k * mu)
gaussian           X ~ N(mu, sigma2)        -> Y_k ~ N(eps_k * mu, eps_k * sigma2)
mvgaussian         X ~ N_p(mu, Sigma)       -> Y_k ~ N_p(eps_k mu, eps_k Sigma)
negative_binomial  X ~ NB(size b, mean mu)  -> Y_k ~ NB(eps_k b, eps_k mu)
binomial           X ~ Bin(n, p)            -> Y_k ~ Bin(round(eps_k n), p)
gamma              X ~ Gamma(shape a, rate) -> Y_k ~ Gamma(eps_k a, rate)
exponential        X ~ Exp(rate)            -> folds Gamma(eps_k, rate)
chi_squared        X ~ chi2(df)             -> folds Gamma(eps_k df/2, 1/2)

The Gaussian and multivariate-Gaussian recipes require the noise scale
(``sigma2`` / ``Sigma``) to be known or well estimated; the negative binomial
requires the overdispersion ``size``; the binomial requires ``n``; the gamma
requires the ``shape``; the chi-squared family takes its degrees of freedom
through ``shape``.  This mirrors the assumptions of the original papers.  Each
nuisance parameter is validated at call time both for presence and for value
(finite and strictly positive; ``Sigma`` symmetric positive semidefinite;
binomial counts not exceeding ``n_trials``).
"""

from __future__ import annotations

from typing import Optional, Union

import numpy as np
from numpy.typing import ArrayLike, NDArray

Seed = Union[int, np.random.Generator, np.random.SeedSequence, None]

__all__ = ["SUPPORTED_FAMILIES", "thin"]

SUPPORTED_FAMILIES = (
    "poisson",
    "gaussian",
    "mvgaussian",
    "negative_binomial",
    "binomial",
    "gamma",
    "exponential",
    "chi_squared",
)

def _validate_input(X):
    try:
        import scipy.sparse as _sp
        if _sp.issparse(X):
            raise TypeError(
                "sparse matrices are not supported yet; densify with X.toarray() "
                "(sparse and AnnData support are on the roadmap)")
    except ImportError:  # pragma: no cover
        pass
    arr = np.asarray(X)
    if arr.dtype.kind == "f" and np.isnan(arr).any():
        raise ValueError("input contains NaN values")

def _integer_valued(a):
    """True when every entry is an integer up to float noise.

    Absolute tolerance: whether a count is an integer does not depend on its
    magnitude.  ``np.allclose`` with its default ``rtol = 1e-5`` accepted
    123456.7 as a count (and rounded it silently) while rejecting 3.4.
    """
    a = np.asarray(a, dtype=float)
    return bool(np.allclose(a, np.round(a), rtol=0.0, atol=1e-8))

def _check_eps(epsilon, K):
    if epsilon is None:
        epsilon = np.full(K, 1.0 / K)
    epsilon = np.asarray(epsilon, dtype=float).ravel()
    if epsilon.size < 2:
        raise ValueError("epsilon must contain at least two allocation weights")
    if np.any(epsilon <= 0):
        raise ValueError("all epsilon entries must be positive")
    if not np.isclose(epsilon.sum(), 1.0):
        raise ValueError("epsilon must sum to one")
    return epsilon

def _rng(random_state):
    if isinstance(random_state, np.random.Generator):
        return random_state
    return np.random.default_rng(random_state)

def _require_positive(value, name, family):
    """Nuisance parameters are validated for value, not only for presence.

    A negative ``sigma2`` used to propagate silently: ``np.sqrt`` returned NaN
    with only a RuntimeWarning and every fold came back NaN.  A non-positive
    ``size`` or ``shape`` surfaced as a bare NumPy/SciPy message ("shape < 0")
    that named neither the parameter nor the family.
    """
    arr = np.asarray(value, dtype=float)
    if arr.size == 0 or not np.all(np.isfinite(arr)) or np.any(arr <= 0):
        raise ValueError(f"{family} thinning requires {name} to be finite and strictly positive")
    return arr

def thin(
    X: ArrayLike,
    family: str,
    epsilon: Optional[ArrayLike] = None,
    K: Optional[int] = None,
    *,
    sigma2: Optional[ArrayLike] = None,
    Sigma: Optional[ArrayLike] = None,
    size: Optional[ArrayLike] = None,
    n_trials: Optional[ArrayLike] = None,
    shape: Optional[ArrayLike] = None,
    random_state: Seed = None,
) -> Union[NDArray[np.floating], NDArray[np.integer]]:
    """Split ``X`` into independent folds by data thinning.

    Parameters
    ----------
    X : array_like
        Observations.  Any shape; for ``mvgaussian`` the last axis is the
        coordinate axis.
    family : str
        One of :data:`SUPPORTED_FAMILIES`.
    epsilon : sequence of float, optional
        Allocation weights, positive, summing to one.  Defaults to K equal
        folds.
    K : int, optional
        Number of equal folds when ``epsilon`` is not given (default 2).
    sigma2, Sigma, size, n_trials, shape :
        Known nuisance parameters required by the respective families
        (see module docstring).
    random_state : int, Generator, optional

    Returns
    -------
    ndarray with shape ``X.shape + (len(epsilon),)`` — fold k is ``[..., k]``.
    """
    _validate_input(X)
    if family not in SUPPORTED_FAMILIES:
        raise ValueError(f"unknown family '{family}'; choose from {SUPPORTED_FAMILIES}")
    if epsilon is not None and K is not None and len(np.ravel(epsilon)) != K:
        raise ValueError(
            f"conflicting fold specifications: epsilon has {len(np.ravel(epsilon))} "
            f"entries but K={K}; give either epsilon or K")
    epsilon = _check_eps(epsilon, 2 if K is None else K)
    rng = _rng(random_state)
    X = np.asarray(X)

    if family == "poisson":
        return _thin_poisson(X, epsilon, rng)
    if family == "gaussian":
        if sigma2 is None:
            raise ValueError("gaussian thinning requires the known variance sigma2")
        return _thin_gaussian(X, epsilon, _require_positive(sigma2, "sigma2", family), rng)
    if family == "mvgaussian":
        if Sigma is None:
            raise ValueError("mvgaussian thinning requires the known covariance Sigma")
        return _thin_mvgaussian(X, epsilon, _check_covariance(Sigma), rng)
    if family == "negative_binomial":
        if size is None:
            raise ValueError("negative_binomial thinning requires the known size b")
        return _thin_negative_binomial(X, epsilon, _require_positive(size, "size", family), rng)
    if family == "binomial":
        if n_trials is None:
            raise ValueError("binomial thinning requires the known number of trials")
        return _thin_binomial(X, epsilon, n_trials, rng)
    if family == "gamma":
        if shape is None:
            raise ValueError("gamma thinning requires the known shape parameter")
        return _thin_gamma(X, epsilon, _require_positive(shape, "shape", family), rng)
    if family == "exponential":
        return _thin_gamma(X, epsilon, 1.0, rng)
    if family == "chi_squared":
        if shape is None:
            raise ValueError("chi_squared thinning requires the degrees of freedom via shape")
        df = _require_positive(shape, "the degrees of freedom (shape)", family)
        return _thin_gamma(X.astype(float), epsilon, df / 2.0, rng)
    raise AssertionError("unreachable")

def _check_covariance(Sigma):
    """Sigma must be a finite, symmetric, positive-semidefinite (p, p) matrix.

    Every test here is *relative to the scale of Sigma*, so the verdict does
    not depend on the units of the data: symmetry is judged against
    ``max|Sigma|`` and definiteness against the largest eigenvalue, with the
    zero matrix refused outright (no noise means the folds cannot be
    independent, as for ``sigma2 = 0``).  0.1.11-0.1.13 mixed absolute
    floors into both tests (``np.allclose`` with its default ``atol`` and a
    ``max(1.0, ...)`` on the eigenvalue scale), so a covariance whose entries
    were below about 1e-5 in the data's units - kilometre-scale coordinates
    with millimetre noise, say - passed even when grossly indefinite, and
    ``_psd_sqrt`` then silently clipped it to a covariance the caller never
    specified.

    The definiteness tolerance, 1e-5 relative, is set by the inputs the
    sampler must accept rather than by float64 arithmetic: a rank-deficient
    covariance (p > n) computed in single precision carries negative
    eigenvalues of -5e-8 (p = 80) to -1.5e-7 (p = 2000) relative, growing
    slowly with p, and ``_psd_sqrt`` clips those harmlessly.  A matrix that
    is indefinite at the 1e-4 level or worse - any genuinely mis-specified
    covariance - is refused at every scale.
    """
    S = np.asarray(Sigma, dtype=float)
    if S.ndim != 2 or S.shape[0] != S.shape[1]:
        raise ValueError("mvgaussian thinning requires Sigma to be a square (p, p) matrix")
    if not np.all(np.isfinite(S)):
        raise ValueError("mvgaussian thinning requires Sigma to be finite")
    scale = float(np.abs(S).max())
    if scale == 0.0:
        raise ValueError("mvgaussian thinning requires a nonzero Sigma: with no noise the folds cannot be independent")
    if np.abs(S - S.T).max() > 1e-6 * scale:
        raise ValueError("mvgaussian thinning requires Sigma to be symmetric")
    w = np.linalg.eigvalsh((S + S.T) / 2.0)
    if w.min() < -1e-5 * np.abs(w).max():
        raise ValueError("mvgaussian thinning requires Sigma to be positive semidefinite")
    return S

# ----------------------------------------------------------------- families
def _thin_poisson(X, eps, rng):
    """Multinomial thinning: (Y_1..Y_K) | X ~ Multinomial(X, eps)."""
    Xi = np.asarray(X)
    if np.any(Xi < 0) or not _integer_valued(Xi):
        raise ValueError("poisson thinning requires nonnegative integer counts")
    flat = np.round(Xi).astype(np.int64).ravel()
    out = rng.multinomial(flat, eps)  # (N, K)
    return out.reshape(Xi.shape + (eps.size,))

def _thin_gaussian(X, eps, sigma2, rng):
    """Linear Gaussian thinning.

    Y = eps * X + N(0, sigma2 * (diag(eps) - eps eps^T)); then
    Y_k ~ N(eps_k mu, eps_k sigma2), mutually independent, sum(Y) = X.
    """
    K = eps.size
    Xf = np.asarray(X, dtype=float)
    cov = np.diag(eps) - np.outer(eps, eps)  # rank K-1, PSD
    L = _psd_sqrt(cov)
    z = rng.standard_normal(Xf.shape + (K,))
    noise = z @ L.T
    sig = np.sqrt(np.asarray(sigma2, dtype=float))
    noise = noise * sig[..., None] if np.ndim(sigma2) else noise * sig
    return Xf[..., None] * eps + noise

def _thin_mvgaussian(X, eps, Sigma, rng):
    """Multivariate version: coordinates on the last axis of X.

    The noise covariance kron(A, Sigma) is sampled through the separable
    square root L_A (x) L_Sigma, so the cost is O(K^3 + p^3) for the two
    eigendecompositions plus matrix products — not the O((Kp)^3)
    eigendecomposition of the Kronecker product itself, which was measured
    at 3.6 s already for p = 1200 in v0.1.4.  Because the rows
    of L_A are orthogonal to the all-ones vector, the folds still sum to X
    exactly.
    """
    K = eps.size
    Xf = np.asarray(X, dtype=float)
    p = Xf.shape[-1]
    if Sigma.shape != (p, p):
        raise ValueError("Sigma must be (p, p) matching the last axis of X")
    A = np.diag(eps) - np.outer(eps, eps)
    L_A = _psd_sqrt(A)          # (K, K)
    L_S = _psd_sqrt(Sigma)      # (p, p)
    z = rng.standard_normal(Xf.shape[:-1] + (K, p))
    noise = np.einsum("ab,...bp,qp->...aq", L_A, z, L_S)
    folds = Xf[..., None, :] * eps[:, None] + noise  # (..., K, p)
    return np.moveaxis(folds, -2, -1)  # (..., p, K)

def _thin_negative_binomial(X, eps, size, rng):
    """Dirichlet-multinomial thinning: (Y|X) ~ DirMult(X, eps * b)."""
    Xi = np.asarray(X)
    if np.any(Xi < 0) or not _integer_valued(Xi):
        raise ValueError("negative_binomial thinning requires nonnegative integer counts")
    flat = np.round(Xi).astype(np.int64).ravel()
    b = np.broadcast_to(np.asarray(size, dtype=float), Xi.shape).ravel()
    alpha = b[:, None] * eps[None, :]
    # vectorised gamma representation of the Dirichlet with row-specific alpha
    G = rng.gamma(shape=alpha)
    tot = G.sum(axis=1, keepdims=True)
    good = np.isfinite(tot[:, 0]) & (tot[:, 0] > 0)
    P = np.divide(G, tot, out=np.zeros_like(G), where=tot > 0)
    out = np.empty_like(P, dtype=np.int64)
    for k in range(eps.size - 1):
        denom = P[:, k:].sum(axis=1)
        ratio = np.divide(P[:, k], denom, out=np.zeros_like(denom), where=denom > 0)
        out[:, k] = rng.binomial(flat - out[:, :k].sum(axis=1), np.clip(ratio, 0, 1))
    out[:, -1] = flat - out[:, :-1].sum(axis=1)
    if not good.all():
        # For very small alpha (size * eps below ~1e-3) the float64 gamma draws
        # underflow to zero for entire rows; the ratio path above would then
        # silently dump the whole count into the last fold, as v0.1.4 did.
        # Those rows are resampled exactly, by the sequential
        # beta-binomial representation of the Dirichlet-multinomial, which is
        # numerically stable for arbitrarily small shape parameters.  The
        # rescue consumes additional draws from the same generator, so on
        # datasets that contain underflow rows the downstream random stream
        # differs from a hypothetical no-underflow world; on normal parameter
        # ranges (no underflow) the stream is bitwise identical to v0.1.4.
        from scipy import stats as _st

        idx = np.flatnonzero(~good)
        rem_n = flat[idx].copy()
        for k in range(eps.size - 1):
            a_k = alpha[idx, k]
            b_k = alpha[idx, k + 1:].sum(axis=1)
            draw = np.asarray(_st.betabinom.rvs(rem_n, a_k, b_k, random_state=rng),
                              dtype=np.int64)
            out[idx, k] = draw
            rem_n = rem_n - draw
        out[idx, -1] = rem_n
    return out.reshape(Xi.shape + (eps.size,))

def _thin_binomial(X, eps, n_trials, rng):
    """Multivariate hypergeometric thinning; eps * n must be integers."""
    Xi = np.asarray(X)
    n_arr = np.asarray(n_trials)
    if np.any(n_arr <= 0) or not _integer_valued(n_arr):
        raise ValueError("binomial thinning requires n_trials to be positive integers")
    if np.any(Xi < 0) or not _integer_valued(Xi):
        raise ValueError("binomial thinning requires nonnegative integer counts")
    n = np.broadcast_to(np.round(n_arr), Xi.shape).ravel().astype(np.int64)
    if np.any(np.round(Xi).ravel() > n):
        raise ValueError("binomial thinning requires every count to be at most its n_trials")
    m = np.round(eps[None, :] * n[:, None]).astype(np.int64)
    if not np.all(m.sum(axis=1) == n):
        raise ValueError("epsilon * n_trials must round to integers summing to n_trials")
    flat = np.round(Xi).astype(np.int64).ravel()
    out = np.empty((flat.size, eps.size), dtype=np.int64)
    remaining_n = n.copy()
    remaining_x = flat.copy()
    for k in range(eps.size - 1):
        out[:, k] = rng.hypergeometric(remaining_x, remaining_n - remaining_x, m[:, k])
        remaining_x = remaining_x - out[:, k]
        remaining_n = remaining_n - m[:, k]
    out[:, -1] = remaining_x
    return out.reshape(Xi.shape + (eps.size,))

def _thin_gamma(X, eps, shape, rng):
    """Dirichlet thinning: Y = X * W, W ~ Dirichlet(shape * eps)."""
    Xf = np.asarray(X, dtype=float)
    if np.any(Xf < 0):
        raise ValueError("gamma thinning requires nonnegative observations")
    a = np.broadcast_to(np.asarray(shape, dtype=float), Xf.shape).ravel()
    alpha = a[:, None] * eps[None, :]
    G = rng.gamma(shape=alpha)
    W = G / G.sum(axis=1, keepdims=True)
    out = Xf.ravel()[:, None] * W
    return out.reshape(Xf.shape + (eps.size,))

def _psd_sqrt(M):
    w, V = np.linalg.eigh(M)
    tol = np.max(np.abs(w)) * 1e-10
    w = np.where(w < tol, 0.0, w)
    return V @ np.diag(np.sqrt(w)) @ V.T
