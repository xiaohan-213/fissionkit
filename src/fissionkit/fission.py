"""Data fission (Leiner, Duan, Wasserman & Ramdas, JASA 2023).

Fission splits a single observation X into two parts f(X) and g(X) such that
either the two parts are independent (Gaussian case, with externally generated
noise) or the conditional law of X given f(X) is known exactly (Bernoulli
case), so that selection may be performed on f(X) and valid inference carried
out with g(X) (or with X | f(X)).

Gaussian fission
----------------
For X ~ N(mu, sigma2) and external Z ~ N(0, sigma2):

    f(X) = X + tau * Z          ~ N(mu, (1 + tau^2)     sigma2)
    g(X) = X - Z / tau          ~ N(mu, (1 + 1/tau^2)   sigma2)

f(X) and g(X) are independent *provided sigma2 is the true noise scale*.
If sigma2 is misspecified, the two copies are correlated (conditionally on
the mean structure, Cov(f, g) = sigma2_true - sigma2_supplied) and downstream
inference is silently invalid.  Model-based workflows in this package
therefore run a residual cross-covariance diagnostic and warn on
inconsistency (see fission_lasso_inference); for raw sequences,
estimate_sigma2_diff provides a difference-based estimate of the noise scale
under a slowly varying mean.

Bernoulli fission
-----------------
For X ~ Bern(p) and external Z ~ Bern(q):

    f(X) = X (1 - Z) + (1 - X) Z      (X flipped with probability q)

X | f(X) remains Bernoulli with a known odds adjustment, enabling exact
conditional inference after selection on f(X).  The external randomization Z
is deliberately withheld from the public return value: conditional validity
requires that inference not use Z.
"""

from __future__ import annotations

from typing import Any, Union, cast

import numpy as np
from numpy.typing import ArrayLike, NDArray

Seed = Union[int, np.random.Generator, np.random.SeedSequence, None]

__all__ = [
    "bernoulli_fission",
    "estimate_sigma2_diff",
    "gaussian_fission",
    "poisson_fission",
]

def _rng(random_state):
    if isinstance(random_state, np.random.Generator):
        return random_state
    return np.random.default_rng(random_state)

def _validate(X):
    from .thinning import _validate_input

    _validate_input(X)

def gaussian_fission(
    X: ArrayLike,
    sigma2: ArrayLike,
    tau: float = 1.0,
    random_state: Seed = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Split Gaussian observations into independent selection / inference parts.

    Parameters
    ----------
    X : array_like
    sigma2 : float or array_like
        The noise variance of X.  Validity of the split requires this to be
        correct; see the module docstring for the failure mode and available
        diagnostics.
    tau : float
        Information trade-off: ``Var(f) = (1 + tau^2) sigma2`` (selection
        copy), ``Var(g) = (1 + tau^{-2}) sigma2`` (inference copy).

    Returns
    -------
    f, g : ndarrays with the shape of ``X``, independent when sigma2 is true.
    """
    if tau <= 0:
        raise ValueError("tau must be positive")
    _validate(X)
    s2 = np.asarray(sigma2, dtype=float)
    if s2.size == 0 or not np.all(np.isfinite(s2)) or np.any(s2 <= 0):
        raise ValueError("gaussian_fission requires sigma2 to be finite and strictly positive")
    rng = _rng(random_state)
    Xf = np.asarray(X, dtype=float)
    sig = np.sqrt(s2)
    Z = rng.standard_normal(Xf.shape) * sig
    return Xf + tau * Z, Xf - Z / tau

def estimate_sigma2_diff(x: ArrayLike) -> float:
    """Difference-based estimate of the noise variance of a 1-D sequence.

    Assumes the mean varies slowly relative to the sampling rate; then
    ``mean(diff(x)**2) / 2`` is a consistent estimate of the noise variance.
    Useful for supplying ``sigma2`` to gaussian_fission for signals and
    time series.
    """
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 3:
        raise ValueError("need at least three observations")
    return float(np.mean(np.diff(x) ** 2) / 2.0)

def poisson_fission(
    X: ArrayLike,
    epsilon: float = 0.5,
    random_state: Seed = None,
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Poisson fission coincides with binomial (multinomial) thinning."""
    from .thinning import thin

    # thin() is typed for all families at once (float or integer folds); the
    # Poisson recipe always returns int64, which the cast records for mypy.
    folds = cast(NDArray[np.int64], thin(X, "poisson", epsilon=[epsilon, 1.0 - epsilon], random_state=random_state))
    return folds[..., 0], folds[..., 1]

def bernoulli_fission(
    X: ArrayLike,
    q: float = 0.2,
    random_state: Seed = None,
) -> tuple[NDArray[np.int64], dict[str, Any]]:
    """Flip-channel fission for binary data.

    Parameters
    ----------
    X : array_like of {0, 1}
    q : float in (0, 0.5)
        Flip probability of the external Bernoulli noise.

    Returns
    -------
    f : ndarray
        The garbled copy used for selection: ``P(f = 1) = p(1-q) + (1-p)q``.
    info : dict
        ``info['q']`` echoes the flip probability and
        ``info['conditional_pmf_x1'](p)`` evaluates, elementwise, the exact
        conditional probability ``P(X = 1 | f)`` at success probability
        ``p`` - the building block of valid post-selection conditional
        likelihoods.  The external randomization is not returned.
    """
    if not (0 < q < 0.5):
        raise ValueError("q must lie in (0, 0.5)")
    _validate(X)
    rng = _rng(random_state)
    Xi = np.asarray(X)
    if not np.isin(Xi, (0, 1)).all():
        raise ValueError("bernoulli_fission requires binary data")
    Z = rng.binomial(1, q, size=Xi.shape)
    f = np.where(Z == 1, 1 - Xi, Xi)

    def conditional_pmf(p: ArrayLike) -> NDArray[np.float64]:
        """P(X = 1 | f) as a function of the success probability p."""
        p = np.asarray(p, dtype=float)
        num = np.where(f == 1, p * (1 - q), p * q)
        den = np.where(f == 1, p * (1 - q) + (1 - p) * q, p * q + (1 - p) * (1 - q))
        return num / den

    info: dict[str, Any] = {"q": q, "conditional_pmf_x1": conditional_pmf}
    return f, info
