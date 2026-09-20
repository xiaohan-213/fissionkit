"""Regression tests for the defects fixed in v0.1.12 (second audit round)."""
import numpy as np
import pytest

from fissionkit import thin

SEED = 17


def test_covariance_validator_accepts_float_level_indefiniteness():
    """A rank-deficient sample covariance (p > n) perturbed at the 1e-9 level
    is symmetric to ``allclose`` but has eigenvalues near -1e-9; the 0.1.11
    validator (tolerance 1e-10) rejected it although ``_psd_sqrt`` handles it.
    Materially indefinite matrices must still be refused."""
    rng = np.random.default_rng(SEED)
    Z = rng.standard_normal((30, 80))
    S = np.cov(Z.T)                                  # ~50 zero eigenvalues
    X = rng.standard_normal((10, 80))
    thin(X, "mvgaussian", Sigma=S, random_state=0)
    noise = 1e-9 * rng.standard_normal(S.shape)
    thin(X, "mvgaussian", Sigma=S + (noise + noise.T) / 2, random_state=0)   # accepted
    thin(X, "mvgaussian", Sigma=S + noise, random_state=0)                    # accepted
    with pytest.raises(ValueError, match="positive semidefinite"):
        thin(X, "mvgaussian", Sigma=S - 1e-3 * np.eye(80), random_state=0)     # refused
    # Single precision (0.1.12 rejected every one of these): a rank-deficient
    # covariance computed entirely in float32 has relative eigenvalues down to
    # about -8e-8 at p = 500; the validator must accept it, and must still
    # refuse a matrix that is indefinite at the 1e-4 level.
    for n, p in [(30, 80), (60, 200), (100, 500)]:
        Zs = rng.standard_normal((n, p)).astype(np.float32)
        Zs = Zs - Zs.mean(axis=0)
        S32 = (Zs.T @ Zs) / np.float32(n - 1)
        w = np.linalg.eigvalsh(S32.astype(np.float64))
        assert w.min() < 0, "test input is not indefinite at float32 precision"
        thin(rng.standard_normal((3, p)), "mvgaussian", Sigma=S32, random_state=0)
        with pytest.raises(ValueError, match="positive semidefinite"):
            thin(rng.standard_normal((3, p)), "mvgaussian",
                 Sigma=S32.astype(np.float64) - 1e-4 * abs(w).max() * np.eye(p), random_state=0)


def test_public_signatures_evaluate_without_pep604():
    """The package supports Python 3.9, where 'X | None' (or any 'X | Y') in
    an annotation cannot be evaluated; every public signature must use
    Optional/Union.  ``inspect.signature`` renders the annotations as the
    source strings under PEP 563, parameters and return alike, so the whole
    signature is inspected without slicing source text."""
    import inspect
    import re

    import fissionkit

    for name in fissionkit.__all__:
        obj = getattr(fissionkit, name)
        if not callable(obj):
            continue
        sig = str(inspect.signature(obj))
        assert not re.search(r"[\w\]\)] *\| *[\w\[]", sig), f"{name}: PEP 604 union in {sig}"
