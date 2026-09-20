"""Property tests: every thinning recipe must produce folds that
(1) reconstruct the original observation,
(2) have the correct marginal distribution, and
(3) be statistically independent of each other.
Marginals are checked with Kolmogorov-Smirnov / chi-square tests against the
theoretical target; independence with a Pearson-correlation z-test.  All tests
are seeded and use generous alpha to keep the false-alarm rate negligible.
"""
import numpy as np
import pytest
from scipy import stats

from fissionkit import gaussian_fission, thin

N = 40_000
SEED = 20260822
ALPHA = 1e-4  # per-test false alarm rate under correctness


def ks_ok(sample, dist):
    return stats.kstest(sample, dist.cdf).pvalue > ALPHA


def indep_ok(a, b):
    r = np.corrcoef(a, b)[0, 1]
    z = abs(r) * np.sqrt(len(a))
    return z < stats.norm.ppf(1 - ALPHA / 2)


def test_poisson():
    rng = np.random.default_rng(SEED)
    mu = 7.3
    X = rng.poisson(mu, N)
    Y = thin(X, "poisson", epsilon=[0.3, 0.7], random_state=rng)
    assert np.array_equal(Y.sum(axis=-1), X)
    for k, e in enumerate([0.3, 0.7]):
        pv = stats.chisquare(*_binned(Y[:, k], stats.poisson(e * mu))).pvalue
        assert pv > ALPHA
    assert indep_ok(Y[:, 0], Y[:, 1])


def test_gaussian():
    rng = np.random.default_rng(SEED)
    mu, s2 = 2.0, 4.0
    X = rng.normal(mu, np.sqrt(s2), N)
    Y = thin(X, "gaussian", epsilon=[0.4, 0.6], sigma2=s2, random_state=rng)
    assert np.allclose(Y.sum(axis=-1), X)
    assert ks_ok(Y[:, 0], stats.norm(0.4 * mu, np.sqrt(0.4 * s2)))
    assert ks_ok(Y[:, 1], stats.norm(0.6 * mu, np.sqrt(0.6 * s2)))
    assert indep_ok(Y[:, 0], Y[:, 1])


def test_gaussian_three_folds():
    rng = np.random.default_rng(SEED)
    X = rng.normal(0.0, 1.0, N)
    Y = thin(X, "gaussian", epsilon=[0.2, 0.3, 0.5], sigma2=1.0, random_state=rng)
    assert np.allclose(Y.sum(axis=-1), X)
    for k, e in enumerate([0.2, 0.3, 0.5]):
        assert ks_ok(Y[:, k], stats.norm(0, np.sqrt(e)))
    for a, b in [(0, 1), (0, 2), (1, 2)]:
        assert indep_ok(Y[:, a], Y[:, b])


def test_negative_binomial():
    rng = np.random.default_rng(SEED)
    b, mu = 5.0, 12.0
    p = b / (b + mu)
    X = rng.negative_binomial(b, p, N)
    Y = thin(X, "negative_binomial", epsilon=[0.5, 0.5], size=b, random_state=rng)
    assert np.array_equal(Y.sum(axis=-1), X)
    target = stats.nbinom(b * 0.5, p)
    pv = stats.chisquare(*_binned(Y[:, 0], target)).pvalue
    assert pv > ALPHA
    assert indep_ok(Y[:, 0], Y[:, 1])


def test_binomial():
    rng = np.random.default_rng(SEED)
    n, p = 20, 0.35
    X = rng.binomial(n, p, N)
    Y = thin(X, "binomial", epsilon=[0.5, 0.5], n_trials=n, random_state=rng)
    assert np.array_equal(Y.sum(axis=-1), X)
    pv = stats.chisquare(*_binned(Y[:, 0], stats.binom(10, p))).pvalue
    assert pv > ALPHA
    assert indep_ok(Y[:, 0], Y[:, 1])


def test_gamma():
    rng = np.random.default_rng(SEED)
    a, rate = 3.0, 1.7
    X = rng.gamma(a, 1 / rate, N)
    Y = thin(X, "gamma", epsilon=[0.25, 0.75], shape=a, random_state=rng)
    assert np.allclose(Y.sum(axis=-1), X)
    assert ks_ok(Y[:, 0], stats.gamma(a * 0.25, scale=1 / rate))
    assert ks_ok(Y[:, 1], stats.gamma(a * 0.75, scale=1 / rate))
    assert indep_ok(Y[:, 0], Y[:, 1])


def test_exponential_and_chi2():
    rng = np.random.default_rng(SEED)
    X = rng.exponential(2.0, N)
    Y = thin(X, "exponential", epsilon=[0.5, 0.5], random_state=rng)
    assert ks_ok(Y[:, 0], stats.gamma(0.5, scale=2.0))
    assert indep_ok(Y[:, 0], Y[:, 1])
    df = 6
    Xc = rng.chisquare(df, N)
    Yc = thin(Xc, "chi_squared", epsilon=[0.5, 0.5], shape=df, random_state=rng)
    assert ks_ok(Yc[:, 0], stats.gamma(df / 4, scale=2.0))
    assert indep_ok(Yc[:, 0], Yc[:, 1])


def test_mvgaussian():
    rng = np.random.default_rng(SEED)
    Sigma = np.array([[2.0, 0.8], [0.8, 1.0]])
    X = rng.multivariate_normal([1.0, -1.0], Sigma, size=N)
    Y = thin(X, "mvgaussian", epsilon=[0.5, 0.5], Sigma=Sigma, random_state=rng)
    assert np.allclose(Y.sum(axis=-1), X)
    # marginal of fold 0, coordinate 0: N(0.5, 0.5*2)
    assert ks_ok(Y[:, 0, 0], stats.norm(0.5, np.sqrt(1.0)))
    assert ks_ok(Y[:, 1, 1], stats.norm(-0.5, np.sqrt(0.5)))
    # cross-fold independence for each coordinate pair
    for i in range(2):
        for j in range(2):
            assert indep_ok(Y[:, i, 0], Y[:, j, 1])


def test_gaussian_fission_independence_and_marginals():
    rng = np.random.default_rng(SEED)
    mu, s2, tau = 1.5, 2.0, 0.8
    X = rng.normal(mu, np.sqrt(s2), N)
    f, g = gaussian_fission(X, sigma2=s2, tau=tau, random_state=rng)
    assert ks_ok(f, stats.norm(mu, np.sqrt((1 + tau**2) * s2)))
    assert ks_ok(g, stats.norm(mu, np.sqrt((1 + tau**-2) * s2)))
    assert indep_ok(f, g)


def test_matrix_shapes():
    rng = np.random.default_rng(SEED)
    X = rng.poisson(5.0, size=(30, 17))
    Y = thin(X, "poisson", K=3, random_state=rng)
    assert Y.shape == (30, 17, 3)
    assert np.array_equal(Y.sum(axis=-1), X)


def _binned(sample, dist, min_expected=8):
    """Bin an integer sample against a discrete distribution for chi-square."""
    sample = np.asarray(sample)
    lo, hi = int(sample.min()), int(sample.max())
    ks = np.arange(lo, hi + 1)
    expected = dist.pmf(ks) * sample.size
    counts = np.array([(sample == k).sum() for k in ks], dtype=float)
    # merge tail bins with tiny expectation
    keep = expected >= min_expected
    obs = list(counts[keep])
    exp = list(expected[keep])
    obs.append(counts[~keep].sum() + 0.0)
    exp.append(expected[~keep].sum() + dist.sf(hi) * sample.size + dist.cdf(lo - 1) * sample.size)
    obs, exp = np.array(obs), np.array(exp)
    exp = exp * obs.sum() / exp.sum()
    return obs, exp


# ------------------------------------------------------------------ v0.1.5
def test_nb_thinning_stable_for_tiny_size():
    """Gamma-representation underflow rows must be rescued exactly, not
    silently dumped into the last fold (regression for v0.1.5).

    With ``size * epsilon`` around 5e-4 nearly every row is split
    all-or-nothing, and a handful of rows carry most of the mass, so the fold
    *means* of a single thinning differ by tens of percent by chance (the
    0.1.5-0.1.11 version of this test compared them to 5% and passed on the
    reference environment by coincidence: 4 of 40 seeds).  The contract that
    actually holds is exchangeability of the folds: over independent
    thinnings of the same data, the share of each nonzero row's mass that
    lands in fold 0 has mean 1/2.  That is tested with a z-test on the pooled
    shares at ALPHA.  Emulating the 0.1.4 defect (no rescue: underflow rows
    dumped into the last fold) gives a mean share of 0.26 and z = -56 against
    a critical value of 3.9; the shipped path gives z = 1.5."""
    import warnings

    rng = np.random.default_rng(11)
    X = rng.negative_binomial(0.001, 0.001 / 50.001, 20_000)
    nz = X > 0
    shares = []
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any RuntimeWarning fails the test
        for r in range(60):
            Y = thin(X, "negative_binomial", epsilon=[0.5, 0.5], size=1e-3,
                     random_state=rng)
            assert np.array_equal(Y.sum(axis=-1), X)
            shares.append(Y[nz, 0] / X[nz])
    S = np.concatenate(shares)
    z = (S.mean() - 0.5) / (0.5 / np.sqrt(S.size))   # Bernoulli-like shares
    assert abs(z) < stats.norm.ppf(1 - ALPHA / 2), (S.mean(), z)


def test_thin_rejects_conflicting_K_and_epsilon():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="conflicting"):
        thin(rng.poisson(3.0, 10), "poisson", epsilon=[0.5, 0.5], K=3)


def test_mvgaussian_separable_noise_contract():
    """The separable square-root sampler must preserve additivity and the
    exact block-covariance contract of the Kronecker construction."""
    rng = np.random.default_rng(5)
    S = np.array([[2.0, 0.8, 0.1], [0.8, 1.0, -0.3], [0.1, -0.3, 1.5]])
    X = rng.multivariate_normal([1.0, -1.0, 0.5], S, size=60_000)
    Y = thin(X, "mvgaussian", epsilon=[0.4, 0.6], Sigma=S, random_state=rng)
    assert np.allclose(Y.sum(axis=-1), X)
    C = np.cov(np.hstack([Y[:, :, 0], Y[:, :, 1]]).T)
    assert np.allclose(C[:3, :3], 0.4 * S, atol=0.04)
    assert np.allclose(C[3:, 3:], 0.6 * S, atol=0.04)
    assert np.abs(C[:3, 3:]).max() < 0.025


# ------------------------------------------------------- input-validation guards
# These behaviours were verified correct by an independent check against the
# published recipes, but were not covered by any test.  Correct-but-unguarded
# behaviour is what silently regresses during a later refactor.


# The `match=` patterns matter: without them these tests pass even when the
# package's own validation is removed, because a malformed epsilon eventually
# makes NumPy raise further downstream.  Matching the message verifies that
# fissionkit rejected the input itself, with a diagnosis the user can act on.


def test_rejects_epsilon_not_summing_to_one():
    with pytest.raises(ValueError, match="sum to one"):
        thin(np.array([5, 6]), "poisson", epsilon=[0.3, 0.3], random_state=0)


def test_rejects_negative_epsilon():
    with pytest.raises(ValueError, match="positive"):
        thin(np.array([5, 6]), "poisson", epsilon=[-0.5, 1.5], random_state=0)


def test_rejects_single_fold():
    """Thinning into one fold is meaningless and must not silently pass."""
    with pytest.raises(ValueError, match="at least two"):
        thin(np.array([3, 4, 5]), "poisson", epsilon=[1.0], random_state=0)


def test_all_zero_input_yields_all_zero_folds():
    Y = thin(np.zeros(200, dtype=int), "poisson", epsilon=[0.5, 0.5], random_state=0)
    assert np.all(Y == 0)


def test_thin_is_reproducible_from_a_seed():
    """The same integer seed must reproduce the folds exactly.

    The suite already pins this for fission_lasso_inference; thin() itself,
    which every recipe builds on, was unguarded.
    """
    X = np.random.default_rng(0).poisson(5.0, 2000)
    a = thin(X, "poisson", epsilon=[0.5, 0.5], random_state=12345)
    b = thin(X, "poisson", epsilon=[0.5, 0.5], random_state=12345)
    c = thin(X, "poisson", epsilon=[0.5, 0.5], random_state=54321)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_folds_are_independent_not_merely_uncorrelated():
    """Zero correlation is weaker than independence; test the joint table."""
    rng = np.random.default_rng(7)
    X = rng.poisson(7.5, 40000)
    Y = thin(X, "poisson", epsilon=[0.3, 0.7], random_state=rng)
    a = np.clip(Y[:, 0], 0, 6)
    b = np.clip(Y[:, 1], 0, 9)
    tab = np.histogram2d(a, b, bins=[np.arange(8), np.arange(11)])[0]
    tab = tab[tab.sum(1) > 30][:, tab.sum(0) > 30]
    # index, not attribute: chi2_contingency returned a plain tuple before SciPy 1.11,
    # and scipy >= 1.8 is the declared minimum
    assert stats.chi2_contingency(tab)[1] > ALPHA
