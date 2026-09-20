"""Valid differential-expression testing after clustering (count splitting).

The double-dipping problem: clustering a count matrix and then testing, on the
same matrix, which features differ between the discovered clusters produces
p-values that are grossly anti-conservative — the clusters were built to
differ.  Count splitting (Neufeld et al. 2024) thins the matrix into
independent folds, clusters on one fold and tests on the other, restoring
Type-I error control.

Per-feature tests, chosen by the count family and the number of groups
(``_test_by_family``, shared by the thinned workflow and the same-data
baseline): for ``poisson`` the exact conditional test - under H0 (equal
per-sample rates) the group-1 sum of a feature, given its total, is
Binomial(total, n1/(n1+n2)) - for two groups and a Poisson likelihood-ratio
test for more; for ``negative_binomial`` the dispersion-robust Welch t-test
for two groups and Kruskal-Wallis for more.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional, Union

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats

from ..thinning import thin

Seed = Union[int, np.random.Generator, np.random.SeedSequence, None]

__all__ = [
    "count_split_de",
    "estimate_nb_size",
    "kruskal_test",
    "naive_de",
    "poisson_lr_test",
    "poisson_two_group_test",
    "welch_two_group_test",
]

def poisson_lr_test(counts: ArrayLike, labels: ArrayLike) -> NDArray[np.float64]:
    """Per-feature Poisson likelihood-ratio test for G >= 2 groups.

    Under H0 (equal per-sample rates across groups), the statistic
    2 * sum_g S_g log((S_g/n_g)/(S/n)) is asymptotically chi-squared with
    G - 1 degrees of freedom.
    """
    counts = np.asarray(counts, dtype=float)
    labels = np.asarray(labels)
    groups = np.unique(labels)
    n_g = np.array([(labels == g).sum() for g in groups], dtype=float)
    S_g = np.stack([counts[labels == g].sum(axis=0) for g in groups])  # (G, p)
    S = S_g.sum(axis=0)
    n = n_g.sum()
    rate_g = S_g / n_g[:, None]
    rate_0 = S / n
    with np.errstate(divide="ignore", invalid="ignore"):
        term = S_g * np.log(np.where(S_g > 0, rate_g / rate_0, 1.0))
    lr = 2.0 * np.nansum(term, axis=0)
    p = stats.chi2.sf(lr, df=len(groups) - 1)
    p[S == 0] = 1.0
    return p

def kruskal_test(counts: ArrayLike, labels: ArrayLike) -> NDArray[np.float64]:
    """Per-feature Kruskal-Wallis test; dispersion-robust, G >= 2 groups."""
    counts = np.asarray(counts)
    labels = np.asarray(labels)
    groups = np.unique(labels)
    samples = [counts[labels == g] for g in groups]
    p = np.empty(counts.shape[1])
    for j in range(counts.shape[1]):
        cols = [s[:, j] for s in samples]
        if all(np.all(c == cols[0][0]) for c in cols):
            p[j] = 1.0
            continue
        try:
            p[j] = stats.kruskal(*cols).pvalue
        except ValueError:
            p[j] = 1.0
    return p

def estimate_nb_size(
    counts: ArrayLike,
    min_size: float = 1e-8,
    max_size: float = 1e8,
) -> NDArray[np.float64]:
    """Per-feature moment estimate of the negative-binomial size parameter.

    b_j = mu_j^2 / (s_j^2 - mu_j); features with no evidence of
    overdispersion (s^2 <= mu) receive max_size, which makes negative-binomial
    thinning numerically indistinguishable from Poisson thinning for them.

    Caveat: a truly overdispersed feature misclassified into the fallback by
    sampling noise leaves a residual positive dependence between the thinned
    folds, of magnitude proportional to mu^2 / b.  In our stress tests
    (mild and strong overdispersion, n as small as 60) this did not inflate
    the Type-I error of :func:`count_split_de`, whose dispersion-robust tests
    absorb the residual; the mechanism is documented here because extreme
    overdispersion combined with aggressive clustering has not been ruled out.
    """
    counts = np.asarray(counts, dtype=float)
    mu = counts.mean(axis=0)
    s2 = counts.var(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        b = mu**2 / (s2 - mu)
    b = np.where((s2 > mu) & np.isfinite(b) & (b > 0), b, max_size)
    return np.asarray(np.clip(b, min_size, max_size), dtype=float)

def welch_two_group_test(counts: ArrayLike, labels: ArrayLike) -> NDArray[np.float64]:
    """Welch two-sample t-test per feature; robust to overdispersion."""
    counts = np.asarray(counts, dtype=float)
    labels = np.asarray(labels)
    groups = np.unique(labels)
    if groups.size != 2:
        raise ValueError("exactly two groups are required")
    a, b = counts[labels == groups[0]], counts[labels == groups[1]]
    res = stats.ttest_ind(a, b, axis=0, equal_var=False)
    return np.nan_to_num(res.pvalue, nan=1.0)

def poisson_two_group_test(counts: ArrayLike, labels: ArrayLike) -> NDArray[np.float64]:
    """Exact conditional two-group Poisson test, vectorised over features.

    Parameters
    ----------
    counts : (n_samples, n_features) integer array
    labels : (n_samples,) array with exactly two distinct values

    Returns
    -------
    pvalues : (n_features,) ndarray of two-sided mid-less p-values
    """
    counts = np.asarray(counts)
    labels = np.asarray(labels)
    groups = np.unique(labels)
    if groups.size != 2:
        raise ValueError("exactly two groups are required")
    m1 = labels == groups[0]
    n1, n2 = int(m1.sum()), int((~m1).sum())
    s1 = counts[m1].sum(axis=0)
    tot = counts.sum(axis=0)
    p0 = n1 / (n1 + n2)
    # two-sided exact binomial p-value: P(|S1 - E| >= |s1 - E|)
    lo = stats.binom.cdf(s1, tot, p0)
    hi = stats.binom.sf(s1 - 1, tot, p0)
    pvals = np.minimum(1.0, 2.0 * np.minimum(lo, hi))
    pvals[tot == 0] = 1.0
    return pvals

_COUNT_FAMILIES = ("poisson", "negative_binomial")

def _check_family(family, caller):
    if not isinstance(family, str):
        raise TypeError(
            f"{caller}: family must be a string, got {type(family).__name__}. Since 0.1.16 every "
            "option of the recipes is keyword-only: pass e.g. cluster=..., random_state=...")
    if family not in _COUNT_FAMILIES:
        raise ValueError(f"{caller} supports families {_COUNT_FAMILIES}, got '{family}'")

def _test_by_family(counts, labels, family):
    """Per-feature test matching the count family: exact Poisson / Poisson LR
    for ``poisson``; dispersion-robust Welch / Kruskal-Wallis for
    ``negative_binomial``.  Shared by :func:`count_split_de` and
    :func:`naive_de` so that the double-dipping baseline and the count-splitting
    workflow are compared with the same test."""
    n_groups = np.unique(labels).size
    if n_groups < 2:
        raise ValueError("clustering produced fewer than two groups")
    if family == "poisson":
        return poisson_two_group_test(counts, labels) if n_groups == 2 else poisson_lr_test(counts, labels)
    return welch_two_group_test(counts, labels) if n_groups == 2 else kruskal_test(counts, labels)

def count_split_de(
    counts: ArrayLike,
    *,
    family: str = "poisson",
    epsilon: float = 0.5,
    cluster: Optional[Callable[[NDArray], NDArray]] = None,
    size: Optional[ArrayLike] = None,
    random_state: Seed = None,
) -> dict[str, Any]:
    """Cluster on one thinned fold, test differential features on the other.

    All options are keyword-only (since 0.1.16).

    Parameters
    ----------
    counts : (n_samples, n_features) integer array
        e.g. a cells x genes expression matrix.
    family : 'poisson' or 'negative_binomial'
    epsilon : float in (0, 1)
        Fraction of information allocated to the clustering fold.
    cluster : callable, optional
        ``cluster(train_matrix) -> labels``.  Defaults to 2-means on
        log1p-transformed, library-size-normalised counts; any number of
        groups >= 2 is supported (two-group data use exact / Welch tests,
        multi-group data use Poisson likelihood-ratio / Kruskal-Wallis).
    size : array_like, optional
        Negative-binomial size parameter(s).  If omitted for that family, a
        per-feature moment estimate is computed automatically
        (see :func:`estimate_nb_size`) and returned under key 'size'.
    random_state : int or Generator

    Returns
    -------
    dict with 'labels', 'pvalues', 'train', 'test'.
    """
    _check_family(family, "count_split_de")
    if not (0.0 < float(epsilon) < 1.0):
        raise ValueError("epsilon must lie strictly between 0 and 1")
    rng = np.random.default_rng(random_state)
    counts = np.asarray(counts)
    size_estimated = False
    if family == "negative_binomial" and size is None:
        size = estimate_nb_size(counts)[None, :]  # per-feature, broadcast over samples
        size_estimated = True
    folds = thin(
        counts,
        family,
        epsilon=[epsilon, 1.0 - epsilon],
        size=size,
        random_state=rng,
    )
    train, test = folds[..., 0], folds[..., 1]
    if cluster is None:
        cluster = _default_two_means(rng)
    labels = np.asarray(cluster(train))
    pvalues = _test_by_family(test, labels, family)
    out = {"labels": labels, "pvalues": pvalues, "train": train, "test": test}
    if size_estimated:
        out["size"] = np.asarray(size).ravel()
    return out

def naive_de(
    counts: ArrayLike,
    *,
    family: str = "poisson",
    cluster: Optional[Callable[[NDArray], NDArray]] = None,
    random_state: Seed = None,
) -> dict[str, Any]:
    """The double-dipping baseline: cluster and test on the same matrix.

    All options are keyword-only (since 0.1.16).

    ``family`` selects the same per-feature test that :func:`count_split_de`
    uses for that family (exact Poisson / Poisson likelihood ratio, or the
    dispersion-robust Welch / Kruskal-Wallis tests for ``negative_binomial``),
    so that the baseline differs from the thinned workflow *only* in reusing
    the data.  Before 0.1.11 the baseline always used the exact Poisson test;
    on overdispersed data that conflated the double-dipping inflation with
    the anti-conservativeness of a Poisson test applied to negative-binomial
    counts (on the null matrix of ``examples/demo_cluster_validation.py``,
    51% rejections with the mismatched test against 37% with the matched
    one).  The default ``family="poisson"`` reproduces the old behaviour.
    """
    _check_family(family, "naive_de")
    rng = np.random.default_rng(random_state)
    counts = np.asarray(counts)
    if cluster is None:
        cluster = _default_two_means(rng)
    labels = np.asarray(cluster(counts))
    return {"labels": labels, "pvalues": _test_by_family(counts, labels, family)}

def _default_two_means(rng):
    from sklearn.cluster import KMeans

    def _cluster(M):
        depth = M.sum(axis=1, keepdims=True).astype(float)
        depth[depth == 0] = 1.0
        Z = np.log1p(M / depth * np.median(depth))
        km = KMeans(n_clusters=2, n_init=10, random_state=int(rng.integers(2**31)))
        return km.fit_predict(Z)

    return _cluster
