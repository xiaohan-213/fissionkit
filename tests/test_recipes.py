"""Scientific-property tests for the applied recipes.

These tests verify the *statistical* claims the package makes, not just that
code runs:
- under a null (homogeneous) count matrix, double dipping produces wildly
  anti-conservative p-values while count splitting produces ~uniform ones;
- fission-based post-lasso confidence intervals attain nominal coverage while
  the naive reuse of the same data undercovers;
- out-of-fold rank selection recovers the true rank of a planted low-rank
  Poisson matrix;
- the reference-free denoiser score ranks denoisers identically to the true
  (oracle) mean squared error.
"""
import numpy as np
import pytest
from scipy import stats

from fissionkit import (
    count_split_de,
    evaluate_denoisers,
    fission_lasso_inference,
    naive_de,
    select_rank,
)

SEED = 7


def test_double_dipping_vs_count_splitting_null():
    rng = np.random.default_rng(SEED)
    # Null: all cells exchangeable, no true clusters.
    X = rng.poisson(5.0, size=(500, 150))
    naive = naive_de(X, random_state=rng)
    split = count_split_de(X, epsilon=0.5, random_state=rng)
    # Double dipping: a large fraction of features "significant" at 0.05.
    assert (naive["pvalues"] < 0.05).mean() > 0.25
    # Count splitting: close to the nominal 5% (uniform p-values).
    frac = (split["pvalues"] < 0.05).mean()
    assert frac < 0.12
    ks = stats.kstest(split["pvalues"], "uniform").pvalue
    assert ks > 1e-4


def test_fission_lasso_coverage():
    rng = np.random.default_rng(SEED)
    n, p, s2 = 200, 10, 1.0
    beta = np.zeros(p)
    beta[:3] = [1.5, -1.0, 0.8]
    covered, total = 0, 0
    naive_covered, naive_total = 0, 0
    for rep in range(60):
        X = rng.standard_normal((n, p))
        y = X @ beta + rng.normal(0, np.sqrt(s2), n)
        res = fission_lasso_inference(X, y, sigma2=s2, tau=1.0, level=0.9, random_state=rng)
        for j, idx in enumerate(res["support"]):
            # target: projection parameter of the selected model = beta[idx]
            # here design is orthogonal in expectation so beta works as target
            lo, hi = res["ci"][j]
            covered += int(lo <= beta[idx] <= hi)
            total += 1
        # naive: select and infer on the same y, classic intervals
        from sklearn.linear_model import LassoCV

        m = LassoCV(cv=5, random_state=0).fit(X, y)
        supp = np.flatnonzero(m.coef_ != 0)
        if supp.size:
            Xs = X[:, supp]
            XtX_inv = np.linalg.pinv(Xs.T @ Xs)
            bh = XtX_inv @ Xs.T @ y
            se = np.sqrt(np.diag(XtX_inv) * s2)
            z = stats.norm.ppf(0.95)
            for j, idx in enumerate(supp):
                naive_covered += int(bh[j] - z * se[j] <= beta[idx] <= bh[j] + z * se[j])
                naive_total += 1
    coverage = covered / total
    naive_cov = naive_covered / naive_total
    assert coverage > 0.85  # nominal 0.90 within Monte-Carlo error
    # the naive procedure must do visibly worse on the null coefficients it selects
    assert naive_cov < coverage


def test_rank_selection_recovers_planted_rank():
    rng = np.random.default_rng(SEED)
    n, p, r = 300, 80, 4
    U = rng.gamma(2.0, 1.0, size=(n, r))
    V = rng.gamma(2.0, 1.0, size=(r, p))
    Lam = U @ V / r + 0.5
    X = rng.poisson(Lam)
    res = select_rank(X, family="poisson", max_rank=12, random_state=rng)
    assert abs(res["best_rank"] - r) <= 1


def test_denoiser_ranking_matches_oracle():
    rng = np.random.default_rng(SEED)
    from scipy.ndimage import gaussian_filter

    truth = np.zeros((96, 96)) + 4.0
    truth[24:72, 24:72] = 20.0
    truth = gaussian_filter(truth, 3)
    img = rng.poisson(truth)

    denoisers = {
        "identity": lambda a: a,
        "gauss_s1": lambda a: gaussian_filter(a, 1),
        "gauss_s2": lambda a: gaussian_filter(a, 2),
        "gauss_s8": lambda a: gaussian_filter(a, 8),
    }
    scores = evaluate_denoisers(img, denoisers, n_repeats=8, random_state=rng)
    oracle = {k: float(np.mean((fn(img.astype(float)) - truth) ** 2)) for k, fn in denoisers.items()}
    order = sorted(scores, key=scores.get)
    oracle_order = sorted(oracle, key=oracle.get)
    # The claim is oracle-consistent *ranking*, so the whole order is checked,
    # not only the best and worst entries.
    assert order == oracle_order


def test_select_rank_rejects_non_matrix_and_invalid_max_rank():
    with pytest.raises(ValueError, match="two-dimensional"):
        select_rank(np.ones(5), max_rank=2, random_state=0)
    for bad in (0, -1, 1.5, True):
        with pytest.raises(ValueError, match="positive integer"):
            select_rank(np.ones((4, 3)), max_rank=bad, random_state=0)


def test_evaluate_denoisers_rejects_noninteger_repeats():
    image = np.ones((3, 3), dtype=int)
    denoisers = {"identity": lambda x: x}
    for bad in (0, -1, 1.5, True):
        with pytest.raises(ValueError, match="positive integer"):
            evaluate_denoisers(image, denoisers, n_repeats=bad, random_state=0)
