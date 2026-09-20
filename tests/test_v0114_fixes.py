"""Regression tests for the defects fixed in v0.1.14 (fourth audit round).

Both defects are of one kind: a validator that mixed an absolute quantity
into what must be a relative judgement (or the reverse), so that its verdict
depended on the units or the magnitude of the data.
"""
import numpy as np
import pytest

from fissionkit import thin

SEED = 23
SCALES = (1e-9, 1.0, 1e6)


def _covariances(rng, p=40, n=15):
    """Accepted and refused covariance shapes, before scaling."""
    Z64 = rng.standard_normal((n, p))
    S64 = np.cov(Z64.T)                                        # float64, rank-deficient
    Sfull = np.cov(rng.standard_normal((20 * p, p)).T)         # float64, full rank
    Z32 = rng.standard_normal((n, p)).astype(np.float32)
    Z32 = Z32 - Z32.mean(axis=0)
    S32 = ((Z32.T @ Z32) / np.float32(n - 1)).astype(np.float64)  # float32 Gram, rank-deficient
    wmax = np.linalg.eigvalsh(S64).max()
    accepted = {
        "float64 full-rank": Sfull,
        "float64 rank-deficient": S64,
        "float32 rank-deficient": S32,
        "asymmetric float noise 1e-9": S64 + 1e-9 * np.abs(S64).max() * rng.standard_normal((p, p)),
    }
    refused = {
        "indefinite at 1e-4": (S64 - 1e-4 * wmax * np.eye(p), "positive semidefinite"),
        "grossly indefinite": (np.array([[1.0, 2.0], [2.0, 1.0]]), "positive semidefinite"),
        "grossly asymmetric": (np.array([[1.0, 0.8], [0.0, 1.0]]), "symmetric"),
        "zero": (np.zeros((2, 2)), "nonzero"),
    }
    return accepted, refused


@pytest.mark.parametrize("scale", SCALES)
def test_covariance_validator_is_scale_invariant(scale):
    """The verdict must not depend on the units of the data.  0.1.11-0.1.13
    used an absolute floor in both the symmetry and the definiteness test, so
    at scale 1e-9 a grossly indefinite or asymmetric Sigma was accepted and
    silently repaired by _psd_sqrt."""
    rng = np.random.default_rng(SEED)
    accepted, refused = _covariances(rng)
    for name, S in accepted.items():
        Y = thin(rng.standard_normal((3, S.shape[0])) * np.sqrt(scale), "mvgaussian",
                 Sigma=scale * S, random_state=0)
        assert np.isfinite(Y).all(), (name, scale)
    for name, (S, match) in refused.items():
        with pytest.raises(ValueError, match=match):
            thin(np.zeros((3, S.shape[0])), "mvgaussian", Sigma=scale * S, random_state=0)


@pytest.mark.parametrize(
    "family,kwargs",
    [("poisson", {}), ("negative_binomial", {"size": 2.0}), ("binomial", {"n_trials": 10**8})],
)
def test_integer_count_check_is_absolute(family, kwargs):
    """Whether a count is an integer does not depend on its magnitude.  The
    former check, np.allclose with rtol=1e-5, rejected 3.4 but accepted
    123456.7 and rounded it silently."""
    for bad in (3.4, 123456.7, 1e7 + 0.5):
        with pytest.raises(ValueError, match="integer"):
            thin(np.array([bad, 1.0]), family, random_state=0, **kwargs)
    # float noise on genuine integers is still tolerated at any magnitude
    Y = thin(np.array([3.0 + 1e-10, 123456.0 - 1e-10, 1e7]), family, random_state=0, **kwargs)
    assert Y.sum(axis=-1).tolist() == [3, 123456, 10**7]
