"""Model-selection recipes built on thinning and fission.

The data arguments of every recipe are positional; every option is
keyword-only (since 0.1.16), so that adding an option can never change the
meaning of an existing call.

``select_rank``     - choose the number of SVD/PCA components of a count or
                      Gaussian matrix by out-of-fold reconstruction error,
                      avoiding the double dipping that biases scree plots.
``evaluate_denoisers`` - rank denoisers on a single photon-count image with no
                      clean reference, Noise2Noise-style, by thinning the image
                      into two independent noisy copies.
``fission_lasso_inference`` - lasso selection on the fission copy, Gaussian
                      inference on the reserved copy, with a built-in
                      diagnostic for a misspecified noise scale.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from typing import Any, Optional, Union

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..fission import gaussian_fission
from ..thinning import thin

Seed = Union[int, np.random.Generator, np.random.SeedSequence, None]

__all__ = ["evaluate_denoisers", "fission_lasso_inference", "select_rank"]

MIN_DOF_ESTIMATED = 20  # A5: refuse the estimated-scale mode when n - p is below this

def select_rank(
    X: ArrayLike,
    *,
    family: str = "poisson",
    max_rank: int = 20,
    epsilon: float = 0.5,
    center: bool = False,
    sigma2: Optional[ArrayLike] = None,
    size: Optional[ArrayLike] = None,
    random_state: Seed = None,
) -> dict[str, Any]:
    """Choose an SVD/PCA rank by out-of-fold sum-of-squares error.

    All options are keyword-only (since 0.1.16).

    The matrix is thinned into train/test folds; rank-r truncated SVDs of the
    train fold predict the test fold after rescaling by (1-eps)/eps.  With
    ``center=True`` the train fold is column-centred before the SVD (the PCA
    convention) and the centring is carried into the prediction; the default
    ``center=False`` fits the uncentred low-rank model that is standard for
    nonnegative count matrices.  ``errors[r-1]`` is the test error of rank r;
    ``best_rank`` minimises it.
    """
    X = np.asarray(X)
    if X.ndim != 2:
        raise ValueError("X must be a two-dimensional matrix")
    if not isinstance(max_rank, (int, np.integer)) or isinstance(max_rank, (bool, np.bool_)) or max_rank < 1:
        raise ValueError("max_rank must be a positive integer")
    if not (0.0 < float(epsilon) < 1.0):
        raise ValueError("epsilon must lie strictly between 0 and 1")
    folds = thin(
        X,
        family,
        epsilon=[epsilon, 1.0 - epsilon],
        sigma2=sigma2,
        size=size,
        random_state=random_state,
    )
    train, test = folds[..., 0].astype(float), folds[..., 1].astype(float)
    scale = (1.0 - epsilon) / epsilon
    # Declared up front: the two branches assign an array and a float, and
    # from NumPy 2.5 the array type is precise enough for mypy to reject the
    # second assignment when the type is inferred from the first.
    base: Union[float, NDArray[np.float64]]
    if center:
        m = train.mean(axis=0, keepdims=True)
        U, s, Vt = np.linalg.svd(train - m, full_matrices=False)
        base = m
    else:
        U, s, Vt = np.linalg.svd(train, full_matrices=False)
        base = 0.0
    max_rank = int(min(max_rank, s.size))
    errors = np.empty(max_rank)
    approx = np.zeros_like(train)
    for r in range(1, max_rank + 1):
        approx = approx + s[r - 1] * np.outer(U[:, r - 1], Vt[r - 1])
        errors[r - 1] = np.mean((test - scale * (base + approx)) ** 2)
    return {"errors": errors, "best_rank": int(np.argmin(errors) + 1)}

def evaluate_denoisers(
    image_counts: ArrayLike,
    denoisers: Mapping[Any, Callable[[NDArray], ArrayLike]],
    *,
    epsilon: float = 0.8,
    n_repeats: int = 1,
    random_state: Seed = None,
) -> dict[Any, float]:
    """Rank denoisers on one Poisson-noise image without a clean reference.

    All options are keyword-only (since 0.1.16).

    Thins the count image into independent folds A and B; applies each
    denoiser to A (rescaled to the original intensity level) and scores it by
    mean squared error against B (rescaled).  Because B is an independent
    unbiased noisy view of the same underlying intensity, the *ranking* of
    denoisers by this score matches the ranking by true (unobservable) MSE up
    to a denoiser-independent constant.

    Choose ``epsilon`` close to 1 (default 0.8) so that the fold the
    denoisers see is near the full acquisition dose: the selected parameter
    then targets the full-dose image, while the small reserved fold serves
    only as an independent, unbiased judge.

    Each denoiser must return a finite array with the shape of its input;
    violations raise immediately with the offending denoiser named.

    Returns dict name -> mean score (lower is better).
    """
    if not (0.0 < float(epsilon) < 1.0):
        raise ValueError("epsilon must lie strictly between 0 and 1")
    if (not isinstance(n_repeats, (int, np.integer))
            or isinstance(n_repeats, (bool, np.bool_)) or n_repeats < 1):
        raise ValueError("n_repeats must be a positive integer")
    rng = np.random.default_rng(random_state)
    img = np.asarray(image_counts)
    scores = {name: 0.0 for name in denoisers}
    for _ in range(n_repeats):
        folds = thin(img, "poisson", epsilon=[epsilon, 1.0 - epsilon], random_state=rng)
        A = folds[..., 0].astype(float) / epsilon
        B = folds[..., 1].astype(float) / (1.0 - epsilon)
        for name, fn in denoisers.items():
            out = np.asarray(fn(A))
            if out.shape != A.shape:
                raise ValueError(f"denoiser '{name}' returned shape {out.shape}, expected {A.shape}")
            if not np.isfinite(out).all():
                raise ValueError(f"denoiser '{name}' returned non-finite values")
            scores[name] += float(np.mean((out - B) ** 2)) / n_repeats
    return scores

def fission_lasso_inference(
    X: ArrayLike,
    y: ArrayLike,
    *,
    sigma2: Optional[float] = None,
    tau: float = 1.0,
    alpha_lasso: Optional[float] = None,
    level: float = 0.9,
    random_state: Seed = None,
) -> dict[str, Any]:
    """Post-selection confidence intervals for lasso-selected coefficients.

    All options are keyword-only (since 0.1.16).

    The response is fissioned: ``f = y + tau z`` drives lasso selection,
    ``g = y - z / tau`` (independent of f when the noise scale is correct)
    supports Gaussian inference on the selected design.

    Two inference modes:

    * ``sigma2`` given - the noise variance is treated as known; intervals
      use normal quantiles and error variance (1 + tau^{-2}) sigma2, and a
      residual cross-covariance diagnostic warns if the supplied sigma2 is
      inconsistent with the data (a misspecified scale silently breaks the
      independence of the two copies).  The decision statistic is the
      empirically studentized mean of the residual cross-products, whose
      nonzero mean is the signature of a scale mismatch.  It detects a
      genuinely misspecified scale (variance 4 supplied as 1) with full power
      and never flags under normal errors with the correct scale, while
      flagging a small fraction of heavy-tailed (t3) samples whose marginal
      scale is correct: 0.5% in the 200-replication audit shipped as
      ``examples/audit_fission_diagnostic.py`` and 1.0-2.5% in earlier
      audits with other seeds (small-rate Monte-Carlo variability).  Those
      residual flags concentrate on samples whose realized noise variance has
      drifted from the supplied value, so a warning in a heavy-tailed setting
      is a signal to switch to sigma2=None, whose pilot estimate tracks the
      realized scale.
    * ``sigma2=None`` (default) - a pilot ordinary-least-squares fit of y on
      the full design estimates the noise variance for generating the fission
      noise; final intervals estimate the error variance from the residuals
      of the inference copy on the selected design and use Student-t
      quantiles with n - |S| degrees of freedom.  This mode requires
      n - p >= 20 and is asymptotically exact rather than exact: the pilot
      scale is estimated from the same response, and coverage at very small
      samples sits at the low edge of nominal (0.896 pooled over 900
      replications at n = 30, p in {5, 8, 10}, against a nominal 0.90;
      ``examples/audit_fission_diagnostic.py`` regenerates this number).

    All internal randomness (fission noise and the lasso cross-validation
    folds) derives from the single ``random_state``.

    Returns dict with 'support', 'coef', 'ci' ((k, 2) array), 'level',
    'sigma2_mode', and 'diagnostic' (the standardized residual
    cross-covariance; large absolute values indicate a misspecified scale).
    """
    from scipy import stats as st
    from sklearn.linear_model import Lasso, LassoCV

    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.ndim != 2 or y.shape != (X.shape[0],):
        raise ValueError("X must be (n, p) and y must be (n,)")
    n, p = X.shape
    if not (0.0 < level < 1.0):
        raise ValueError("level must lie strictly between 0 and 1")
    if tau <= 0:
        raise ValueError("tau must be positive")
    if sigma2 is not None and not (np.isfinite(sigma2) and sigma2 > 0):
        raise ValueError("sigma2 must be finite and strictly positive, or None to estimate it")
    rng = np.random.default_rng(random_state) if not isinstance(random_state, np.random.Generator) else random_state
    known_sigma = sigma2 is not None
    if not known_sigma:
        if n - p < MIN_DOF_ESTIMATED:
            raise ValueError(
                f"sigma2=None requires n - p >= {MIN_DOF_ESTIMATED} (got n - p = {n - p}): "
                "with p close to n the pilot least-squares fit interpolates, the estimated "
                "noise scale collapses toward zero, and the fission split silently degenerates "
                "into selecting and inferring on the same data. Supply sigma2 explicitly, or "
                "use a high-dimensional scale estimator (planned for a future release).")
        # pilot estimate for the fission noise scale
        beta_full = np.linalg.lstsq(X, y, rcond=None)[0]
        dof = n - p
        sigma2_gen = float(np.sum((y - X @ beta_full) ** 2) / dof)
    else:
        sigma2_gen = float(np.asarray(sigma2))
    f, g = gaussian_fission(y, sigma2=sigma2_gen, tau=tau, random_state=rng)
    cv_seed = int(rng.integers(2**31))
    if alpha_lasso is None:
        model = LassoCV(cv=5, random_state=cv_seed).fit(X, f)
    else:
        model = Lasso(alpha=alpha_lasso).fit(X, f)
    support = np.flatnonzero(model.coef_ != 0)
    if support.size == 0:
        return {"support": support, "coef": np.array([]), "ci": np.empty((0, 2)),
                "level": level, "sigma2_mode": "known" if known_sigma else "estimated",
                "diagnostic": np.nan}
    Xs = X[:, support]
    XtX_inv = np.linalg.pinv(Xs.T @ Xs)
    H = Xs @ XtX_inv @ Xs.T
    beta = XtX_inv @ Xs.T @ g
    df = max(n - support.size, 1)
    # residual cross-covariance diagnostic: E[e_f'e_g]/df = sigma2_true - sigma2_supplied
    e_f = f - H @ f
    e_g = g - H @ g
    cross = float(e_f @ e_g) / df
    # Decision statistic: a misspecified scale shifts the MEAN of the residual
    # cross-products w_i = e_f,i * e_g,i away from zero (by sigma2_true -
    # sigma2_supplied); the mean is studentized by the empirical sd of w.
    # Under heavy-tailed errors the realized noise variance of a given sample
    # drifts from its expectation, so a marginally correct sigma2 can still be
    # wrong for the sample at hand; the statistic flags exactly those samples
    # (drift in either direction).  examples/audit_fission_diagnostic.py
    # measures the flag rate under t3 errors with a correct marginal sigma2
    # (0.5% in the shipped seed; 1.0-2.5% in earlier seeds), 0% under normal
    # errors, and 100% detection of a genuinely misspecified scale (4 vs 1).
    w = e_f * e_g
    sd_w = float(np.std(w, ddof=1))
    zstat = float(np.mean(w)) / (sd_w / np.sqrt(w.size)) if sd_w > 0 else 0.0
    if known_sigma and abs(zstat) > 4.0:
        warnings.warn(
            "the fission copies show residual association (studentized z = "
            f"{zstat:.1f}; residual cross-covariance {cross:.3g}); the "
            "supplied sigma2 appears misspecified and the reported intervals "
            "may be invalid. Consider sigma2=None to estimate the scale from "
            "the data.",
            UserWarning,
        )
    if known_sigma:
        var = (1.0 + 1.0 / tau**2) * sigma2_gen
        se = np.sqrt(np.diag(XtX_inv) * var)
        q = st.norm.ppf(0.5 + level / 2.0)
    else:
        var_g = float(e_g @ e_g) / df  # estimates (1 + tau^-2) sigma2_true
        se = np.sqrt(np.diag(XtX_inv) * var_g)
        q = st.t.ppf(0.5 + level / 2.0, df)
    ci = np.column_stack([beta - q * se, beta + q * se])
    out = {"support": support, "coef": beta, "ci": ci, "level": level,
           "sigma2_mode": "known" if known_sigma else "estimated", "diagnostic": zstat}
    if not known_sigma and n - p < 40:
        out["note"] = ("small sample for the estimated-scale mode: intervals may "
                       "mildly undercover (see documentation)")
    return out
