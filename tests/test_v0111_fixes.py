"""Regression tests for the defects fixed in v0.1.11.

Every test here corresponds to a finding of the pre-submission audit:
nuisance parameters were validated for presence but not for value; the
double-dipping baseline used a different test from the thinned workflow; and
two public return annotations disagreed with the objects actually returned.
"""
import inspect
import types
import typing

import numpy as np
import pytest

import fissionkit
from fissionkit import (
    bernoulli_fission,
    count_split_de,
    estimate_nb_size,
    evaluate_denoisers,
    fission_lasso_inference,
    gaussian_fission,
    naive_de,
    poisson_two_group_test,
    select_rank,
    thin,
    welch_two_group_test,
)

SEED = 13


# ------------------------------------------------- nuisance-parameter values
@pytest.mark.parametrize(
    "family,kwargs,match",
    [
        ("gaussian", {"sigma2": -1.0}, "sigma2"),
        ("gaussian", {"sigma2": 0.0}, "sigma2"),
        ("gaussian", {"sigma2": np.nan}, "sigma2"),
        ("negative_binomial", {"size": 0.0}, "size"),
        ("negative_binomial", {"size": -2.0}, "size"),
        ("gamma", {"shape": -1.0}, "shape"),
        ("chi_squared", {"shape": 0.0}, "degrees of freedom"),
    ],
)
def test_thin_rejects_nonpositive_nuisance_values(family, kwargs, match):
    """A negative sigma2 used to return all-NaN folds with only a RuntimeWarning."""
    X = np.array([1.0, 2.0, 3.0]) if family in ("gaussian", "gamma", "chi_squared") else np.array([1, 2, 3])
    with pytest.raises(ValueError, match=match):
        thin(X, family, random_state=0, **kwargs)


def test_thin_binomial_rejects_counts_above_n_trials():
    with pytest.raises(ValueError, match="at most"):
        thin(np.array([3, 5]), "binomial", n_trials=4, random_state=0)
    with pytest.raises(ValueError, match="positive integers"):
        thin(np.array([1, 2]), "binomial", n_trials=0, random_state=0)


def test_thin_mvgaussian_rejects_bad_covariance():
    X = np.random.default_rng(SEED).standard_normal((20, 2))
    with pytest.raises(ValueError, match="positive semidefinite"):
        thin(X, "mvgaussian", Sigma=np.array([[1.0, 2.0], [2.0, 1.0]]), random_state=0)
    with pytest.raises(ValueError, match="symmetric"):
        thin(X, "mvgaussian", Sigma=np.array([[1.0, 0.5], [0.0, 1.0]]), random_state=0)
    with pytest.raises(ValueError, match="square"):
        thin(X, "mvgaussian", Sigma=np.ones((2, 3)), random_state=0)
    with pytest.raises(ValueError, match="matching the last axis"):
        thin(X, "mvgaussian", Sigma=np.eye(3), random_state=0)


def test_gaussian_fission_rejects_nonpositive_sigma2():
    with pytest.raises(ValueError, match="sigma2"):
        gaussian_fission(np.array([1.0, 2.0]), sigma2=-1.0, random_state=0)


def test_recipe_argument_validation():
    rng = np.random.default_rng(SEED)
    X = rng.poisson(5.0, (40, 6))
    G = rng.standard_normal((60, 4))
    with pytest.raises(ValueError, match="supports families"):
        count_split_de(X, family="gaussian", random_state=0)
    with pytest.raises(ValueError, match="between 0 and 1"):
        count_split_de(X, epsilon=1.0, random_state=0)
    with pytest.raises(ValueError, match="between 0 and 1"):
        select_rank(X, epsilon=0.0, random_state=0)
    with pytest.raises(ValueError, match="n_repeats"):
        evaluate_denoisers(X, {"id": lambda a: a}, n_repeats=0, random_state=0)
    with pytest.raises(ValueError, match="level"):
        fission_lasso_inference(G[:, :3], G[:, 3], sigma2=1.0, level=1.5, random_state=0)
    with pytest.raises(ValueError, match="sigma2"):
        fission_lasso_inference(G[:, :3], G[:, 3], sigma2=-1.0, random_state=0)
    with pytest.raises(ValueError, match="tau"):
        fission_lasso_inference(G[:, :3], G[:, 3], sigma2=1.0, tau=0.0, random_state=0)


def test_valid_inputs_unchanged_by_validation():
    """Validation must not alter the random stream on valid inputs.

    The folds below were computed with 0.1.10 (no value validation) and
    0.1.11 and agree bit for bit; this pins them so that a later change to
    the validators, or to the order in which nuisance parameters are coerced,
    cannot silently move seeded results."""
    Y = thin(np.array([4, 9, 2, 7]), "poisson", epsilon=[0.3, 0.7], random_state=20260822)
    assert Y.tolist() == [[1, 3], [2, 7], [1, 1], [1, 6]]
    G = thin(np.array([1.0, -2.0, 0.5]), "gaussian", sigma2=2.0, random_state=20260822)
    assert np.allclose(G, [[0.985292, 0.014708], [-1.951622, -0.048378], [-0.585804, 1.085804]], atol=1e-6)
    N = thin(np.array([12, 0, 30]), "negative_binomial", size=3.0, random_state=20260822)
    assert N.tolist() == [[8, 4], [0, 0], [17, 13]]


# ------------------------------------------------- matched baseline test
def test_naive_de_uses_the_same_test_as_count_split_de():
    """On negative-binomial data the baseline must use the dispersion-robust
    test, so that the comparison with count splitting isolates double dipping
    from the Poisson-misfit inflation."""
    rng = np.random.default_rng(SEED)
    X = rng.negative_binomial(10, 10 / 15, size=(300, 60))
    nb = naive_de(X, family="negative_binomial", random_state=1)
    po = naive_de(X, random_state=1)  # default: Poisson, as before 0.1.11
    assert np.array_equal(nb["labels"], po["labels"])  # same clustering
    assert np.allclose(nb["pvalues"], welch_two_group_test(X, nb["labels"]))
    assert np.allclose(po["pvalues"], poisson_two_group_test(X, po["labels"]))
    with pytest.raises(ValueError, match="supports families"):
        naive_de(X, family="gaussian")


def test_matched_baseline_still_shows_double_dipping():
    """With the matched test the double-dipping inflation remains large: the
    contrast the package exists to demonstrate is not an artefact of the test."""
    rng = np.random.default_rng(SEED)
    X = rng.negative_binomial(10, 10 / 15, size=(500, 150))
    naive = naive_de(X, family="negative_binomial", random_state=rng)
    split = count_split_de(X, family="negative_binomial", size=10, random_state=rng)
    assert (naive["pvalues"] < 0.05).mean() > 0.20
    assert (split["pvalues"] < 0.05).mean() < 0.12


# ------------------------------------------------- return annotations
def _smoke_call(name):
    """A tiny valid call for every public callable, returning its result."""
    rng = np.random.default_rng(SEED)
    X = rng.poisson(5.0, (40, 6))
    G = rng.standard_normal((60, 3))
    y = G[:, 0] + rng.standard_normal(60)
    labels = np.repeat([0, 1], 20)
    img = rng.poisson(6.0, (16, 16))
    calls = {
        "thin": lambda: thin(X, "poisson", random_state=0),
        "gaussian_fission": lambda: gaussian_fission(y, sigma2=1.0, random_state=0),
        "poisson_fission": lambda: fissionkit.poisson_fission(X, random_state=0),
        "bernoulli_fission": lambda: bernoulli_fission(rng.binomial(1, 0.3, 50), random_state=0),
        "estimate_sigma2_diff": lambda: fissionkit.estimate_sigma2_diff(y),
        "count_split_de": lambda: count_split_de(X, random_state=0),
        "naive_de": lambda: naive_de(X, random_state=0),
        "estimate_nb_size": lambda: estimate_nb_size(X),
        "kruskal_test": lambda: fissionkit.kruskal_test(X, labels),
        "poisson_lr_test": lambda: fissionkit.poisson_lr_test(X, labels),
        "poisson_two_group_test": lambda: poisson_two_group_test(X, labels),
        "welch_two_group_test": lambda: welch_two_group_test(X, labels),
        "select_rank": lambda: select_rank(X, max_rank=3, random_state=0),
        "evaluate_denoisers": lambda: evaluate_denoisers(img, {"id": lambda a: a}, random_state=0),
        "fission_lasso_inference": lambda: fission_lasso_inference(G, y, sigma2=1.0, random_state=0),
    }
    return calls[name]()


_UNION_ORIGINS = {typing.Union, getattr(types, "UnionType", typing.Union)}


def _matches(value, hint):
    """Structural check of a runtime value against a resolved annotation.

    Deliberately name-based for arrays: ``typing.get_origin(NDArray[...])``
    was ``numpy.ndarray`` up to NumPy 2.4 and the ``NDArray`` alias object
    (not a type) from NumPy 2.5, and the 0.1.11 version of this helper, which
    passed the origin to ``isinstance``, failed on the newer NumPy."""
    origin = typing.get_origin(hint)
    if origin is tuple:
        args = typing.get_args(hint)
        return isinstance(value, tuple) and len(value) == len(args) and all(
            _matches(v, a) for v, a in zip(value, args))
    if origin in _UNION_ORIGINS:
        return any(_matches(value, a) for a in typing.get_args(hint))
    if origin is dict or hint is dict:
        return isinstance(value, dict)
    if hint is np.ndarray or "ndarray" in str(hint) or "NDArray" in str(hint):
        return isinstance(value, np.ndarray)
    if hint is float:
        return isinstance(value, float)
    target = origin if isinstance(origin, type) else hint
    if not isinstance(target, type):
        pytest.fail(f"unrecognised annotation {hint!r}; extend _matches")
    return isinstance(value, target)


@pytest.mark.parametrize("name", [n for n in fissionkit.__all__ if callable(getattr(fissionkit, n))])
def test_return_annotation_matches_runtime_type(name):
    """`bernoulli_fission` was annotated as returning two arrays but returns an
    array and a dict; `estimate_nb_size` was annotated `float` but returns an
    array.  Resolvable annotations are not the same as correct ones."""
    func = getattr(fissionkit, name)
    hint = typing.get_type_hints(func)["return"]
    value = _smoke_call(name)
    assert _matches(value, hint), f"{name}: returns {type(value).__name__}, annotated {hint}"
    assert inspect.isfunction(func)
