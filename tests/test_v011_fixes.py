"""Regression tests for the defects fixed in v0.1.1 and v0.1.4."""
import warnings

import numpy as np
import pytest
from scipy import stats

from fissionkit import (
    bernoulli_fission,
    count_split_de,
    estimate_nb_size,
    estimate_sigma2_diff,
    fission_lasso_inference,
    thin,
)
from fissionkit.recipes.model_selection import select_rank

SEED = 11


# ---------------------------------------------------------------- A1
def test_misspecified_sigma2_triggers_warning():
    rng = np.random.default_rng(SEED)
    n, p = 400, 8
    X = rng.standard_normal((n, p))
    beta = np.zeros(p); beta[:2] = [2.0, -1.5]
    y = X @ beta + rng.normal(0, 2.0, n)          # true sigma2 = 4
    with pytest.warns(UserWarning, match="misspecified"):
        fission_lasso_inference(X, y, sigma2=1.0, random_state=rng)  # user says 1
    # correct sigma2: must NOT warn
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fission_lasso_inference(X, y, sigma2=4.0, random_state=rng)


def test_sigma2_diff_estimator():
    rng = np.random.default_rng(SEED)
    t = np.linspace(0, 1, 5000)
    x = np.sin(3 * t) + rng.normal(0, 0.7, t.size)   # slowly varying mean
    est = estimate_sigma2_diff(x)
    assert abs(est - 0.49) < 0.05


# ---------------------------------------------------------------- A2
def test_t_branch_coverage_with_estimated_sigma():
    rng = np.random.default_rng(SEED)
    n, p = 200, 10
    beta = np.zeros(p); beta[:3] = [1.5, -1.0, 0.8]
    covered = total = 0
    for _ in range(40):
        X = rng.standard_normal((n, p))
        y = X @ beta + rng.normal(0, 1.0, n)
        res = fission_lasso_inference(X, y, sigma2=None, level=0.9, random_state=rng)
        assert res["sigma2_mode"] == "estimated"
        for j, idx in enumerate(res["support"]):
            lo, hi = res["ci"][j]
            covered += int(lo <= beta[idx] <= hi)
            total += 1
    assert covered / total > 0.85


# ---------------------------------------------------------------- A3
def test_multigroup_null_error_control():
    rng = np.random.default_rng(SEED)
    X = rng.poisson(6.0, size=(600, 120))            # null: no clusters

    def three_means(M):
        from sklearn.cluster import KMeans
        Z = np.log1p(M.astype(float))
        return KMeans(n_clusters=3, n_init=10, random_state=1).fit_predict(Z)

    res = count_split_de(X, family="poisson", cluster=three_means, random_state=rng)
    assert np.unique(res["labels"]).size == 3
    frac = (res["pvalues"] < 0.05).mean()
    assert frac < 0.12
    assert stats.kstest(res["pvalues"], "uniform").pvalue > 1e-4


# ---------------------------------------------------------------- A4
def test_nb_size_estimation_and_error_control():
    rng = np.random.default_rng(SEED)
    p = 100
    b_true = rng.uniform(2.0, 20.0, p)
    mu = 8.0
    X = rng.negative_binomial(b_true[None, :], b_true[None, :] / (b_true[None, :] + mu), size=(800, p))
    b_hat = estimate_nb_size(X)
    # moment estimator is noisy per gene but unbiased in aggregate (log scale)
    assert abs(np.median(np.log(b_hat / b_true))) < 0.35
    res = count_split_de(X, family="negative_binomial", size=None, random_state=rng)
    assert "size" in res
    assert (res["pvalues"] < 0.05).mean() < 0.12


# ---------------------------------------------------------------- B2
def test_select_rank_center_option():
    rng = np.random.default_rng(SEED)
    n, p, r = 250, 60, 3
    M = rng.gamma(2, 1, (n, r)) @ rng.gamma(2, 1, (r, p)) / r + 0.5
    X = rng.poisson(M)
    res_c = select_rank(X, family="poisson", max_rank=10, center=True, random_state=rng)
    res_u = select_rank(X, family="poisson", max_rank=10, center=False, random_state=rng)
    assert abs(res_u["best_rank"] - r) <= 1
    # centring absorbs one mean component; selected rank may drop by about one
    assert abs(res_c["best_rank"] - (r - 1)) <= 1


# ---------------------------------------------------------------- B3
def test_bernoulli_fission_marginal_and_conditional():
    rng = np.random.default_rng(SEED)
    p_true, q = 0.3, 0.2
    X = rng.binomial(1, p_true, 60_000)
    f, info = bernoulli_fission(X, q=q, random_state=rng)
    assert "noise" not in info                       # randomization withheld
    p_f = p_true * (1 - q) + (1 - p_true) * q
    assert abs(f.mean() - p_f) < 0.01                # marginal law of the copy
    cond = info["conditional_pmf_x1"](p_true)
    # analytic check at both values of f
    c1 = p_true * (1 - q) / (p_true * (1 - q) + (1 - p_true) * q)
    c0 = p_true * q / (p_true * q + (1 - p_true) * (1 - q))
    assert np.allclose(np.unique(cond), sorted([c0, c1]))
    # conditional MLE over a grid recovers p
    grid = np.linspace(0.01, 0.99, 197)
    ll = [np.sum(np.log(np.where(X == 1, info["conditional_pmf_x1"](g), 1 - info["conditional_pmf_x1"](g)))) for g in grid]
    assert abs(grid[int(np.argmax(ll))] - p_true) < 0.03


# ---------------------------------------------------------------- B5
def test_input_validation():
    with pytest.raises(ValueError, match="NaN"):
        thin(np.array([1.0, np.nan]), "gaussian", sigma2=1.0)
    import scipy.sparse as sp
    with pytest.raises(TypeError, match="sparse"):
        thin(sp.csr_matrix(np.eye(3)), "poisson")
    from fissionkit.recipes.model_selection import evaluate_denoisers
    img = np.random.default_rng(0).poisson(5.0, (16, 16))
    with pytest.raises(ValueError, match="shape"):
        evaluate_denoisers(img, {"bad": lambda a: a[:2]}, random_state=0)


# ---------------------------------------------------------------- B4
def test_seed_chain_reproducible_and_responsive():
    rng = np.random.default_rng(SEED)
    X = rng.standard_normal((150, 6))
    y = X[:, 0] * 2 + rng.normal(0, 1, 150)
    r1 = fission_lasso_inference(X, y, sigma2=1.0, random_state=5)
    r2 = fission_lasso_inference(X, y, sigma2=1.0, random_state=5)
    r3 = fission_lasso_inference(X, y, sigma2=1.0, random_state=6)
    assert np.array_equal(r1["support"], r2["support"]) and np.allclose(r1["coef"], r2["coef"])
    assert (not np.array_equal(r1["support"], r3["support"])) or (not np.allclose(r1["coef"], r3["coef"]))


# ---------------------------------------------------------------- A5 (round 2)
def test_estimated_mode_refuses_high_dimensional_design():
    rng = np.random.default_rng(3)
    X = rng.standard_normal((50, 60))
    y = rng.standard_normal(50)
    with pytest.raises(ValueError, match="n - p"):
        fission_lasso_inference(X, y, sigma2=None)
    # known-sigma mode remains available in high dimension
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # LassoCV convergence chatter on pure noise
        res = fission_lasso_inference(X, y, sigma2=1.0, random_state=0)
    assert "ci" in res


def test_estimated_mode_threshold_boundary():
    rng = np.random.default_rng(4)
    X = rng.standard_normal((30, 11))  # n - p = 19 < 20
    y = rng.standard_normal(30)
    with pytest.raises(ValueError):
        fission_lasso_inference(X, y, sigma2=None)
    X = rng.standard_normal((31, 11))  # n - p = 20: runs, and flags small sample
    y = X[:, 0] + rng.standard_normal(31)
    res = fission_lasso_inference(X, y, sigma2=None, random_state=0)
    assert res["sigma2_mode"] == "estimated" and "note" in res


def test_estimated_mode_near_threshold_coverage():
    rng = np.random.default_rng(5)
    n, p = 60, 35  # dof = 25, just above the guard
    beta = np.zeros(p); beta[:2] = [2.0, -1.5]
    covered = total = 0
    for _ in range(60):
        X = rng.standard_normal((n, p))
        y = X @ beta + rng.normal(0, 1.0, n)
        r = fission_lasso_inference(X, y, sigma2=None, level=0.9, random_state=rng)
        for j, idx in enumerate(r["support"]):
            lo, hi = r["ci"][j]
            covered += int(lo <= beta[idx] <= hi)
            total += 1
    assert covered / total > 0.82


# ---------------------------------------------------------------- B9 (round 3/4)
def test_heavy_tail_flags_track_realized_scale():
    """Under t3 errors with a marginally correct sigma2, diagnostic flags must
    concentrate on samples whose realized error variance drifted away from the
    supplied value (in either direction) - the samples in which known-scale
    intervals conditionally undercover."""
    rng = np.random.default_rng(9)
    n, p = 300, 8
    beta = np.zeros(p); beta[:2] = [1.5, -1.0]
    flagged, clean = [], []
    for _ in range(45):
        X = rng.standard_normal((n, p))
        eps = rng.standard_t(3, n) / np.sqrt(3)
        y = X @ beta + eps
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            fission_lasso_inference(X, y, sigma2=1.0, random_state=rng)
            warned = any("misspecified" in str(x.message) for x in w)
        (flagged if warned else clean).append(abs(float(np.var(eps)) - 1.0))
    assert len(flagged) >= 2          # heavy tails must produce some flags
    assert np.mean(flagged) > np.mean(clean) + 0.10


# ---------------------------------------------------------------- v0.1.4
def test_import_path_is_local_tree():
    """The package under test must resolve inside this repository's src/ tree,
    never to a stale editable install elsewhere.  A stale install once caused
    measurements to be taken on code that was not the code under test."""
    import pathlib

    import fissionkit

    src = pathlib.Path(__file__).resolve().parent.parent / "src"
    assert pathlib.Path(fissionkit.__file__).resolve().is_relative_to(src)
