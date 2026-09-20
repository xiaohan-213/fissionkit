# fissionkit User Manual

**Version 0.2.0** · Data fission and data thinning for valid statistics after selection

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22853159.svg)](https://doi.org/10.5281/zenodo.22853159)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation](#3-installation)
4. [Functional Modules](#4-functional-modules)
5. [API Reference](#5-api-reference)
6. [Operation Guide](#6-operation-guide)
7. [Validation and Accuracy](#7-validation-and-accuracy)
8. [Scope and Limitations](#8-scope-and-limitations)
9. [Troubleshooting](#9-troubleshooting)
10. [Support and Version Information](#10-support-and-version-information)
11. [Appendix](#11-appendix)

---

## 1. Introduction

### 1.1 Overview

Many analyses use the same data twice: cluster the cells, then test which genes differ between the clusters; select predictors with the lasso, then compute confidence intervals for them; fit a model, then evaluate it on the data it was fitted to. Each second use is conditioned on a choice made from the same data, so its p-values, intervals and error estimates are invalid, usually in the optimistic direction, and nothing in the output shows it.

The classical remedy is to split the sample: select on one half of the rows, infer on the other. That is often impossible. A single-cell matrix has no second population of *these* cells, an image is one observation, and a regression with *n* close to *p* cannot afford to lose half its rows.

fissionkit splits **within** each observation instead. A count, a Gaussian measurement, a whole matrix or an image is divided into parts that are statistically independent (or whose conditional law is known exactly), so that one part can drive selection and another can support inference. The price is paid in information rather than in observations, and the user chooses how much of each part receives.

fissionkit implements, under one API, the splitting recipes of:

- J. Leiner, B. Duan, L. Wasserman, A. Ramdas. *Data fission: splitting a single data point.* Journal of the American Statistical Association 120 (2025) 135–146.
- A. Neufeld, A. Dharamshi, L. L. Gao, D. Witten. *Data thinning for convolution-closed distributions.* Journal of Machine Learning Research 25(57) (2024).
- A. Dharamshi, A. Neufeld, K. Motwani, L. L. Gao, D. Witten, J. Bien. *Generalized data thinning using sufficient statistics.* Journal of the American Statistical Association (2025).

All methodological credit belongs to those authors. fissionkit contributes an independent, tested Python implementation together with four ready-to-run applied workflows.

### 1.2 Key Features

- **Data thinning for eight families** — `poisson`, `gaussian`, `mvgaussian`, `negative_binomial`, `binomial`, `gamma`, `exponential` and `chi_squared`, with any number of folds and unequal allocations
- **Data fission** — Gaussian fission with a tunable information trade-off, Bernoulli fission with an exact conditional law, and Poisson fission
- **Validated nuisance parameters** — every known parameter a family needs (`sigma2`, `Sigma`, `size`, `n_trials`, `shape`) is checked at call time for presence and for value, with an error that names the parameter and the family
- **Differential expression after clustering** — count splitting with exact, likelihood-ratio, Welch and Kruskal–Wallis tests matched to the count family and the number of groups, plus a same-data baseline that uses the same test
- **Rank selection** — the number of principal components from out-of-fold reconstruction error instead of a scree plot
- **Reference-free denoiser evaluation** — score denoisers on a single photon-count image with no clean reference
- **Post-selection inference for the lasso** — known-scale and estimated-scale modes, with a built-in diagnostic for a misspecified noise scale
- **Reproducibility** — every random operation is driven by one `random_state`

### 1.3 Thinning or Fission?

| Your data | Use | What you get |
|---|---|---|
| Counts (Poisson, negative binomial, binomial) | `thin` | *K* independent folds of the same family that sum to the data |
| Positive continuous data (gamma, exponential, chi-squared) | `thin` | *K* independent gamma folds that sum to the data |
| Gaussian data with a known noise variance | `thin(..., "gaussian")` or `gaussian_fission` | Thinning gives folds that sum to the data, each with mean scaled by its allocation; fission gives two copies that both keep the original mean |
| Multivariate Gaussian data with a known covariance | `thin(..., "mvgaussian")` | Independent vector-valued folds |
| Binary data | `bernoulli_fission` | A garbled copy for selection and the exact conditional law of the original given that copy |

Thinning divides the signal: a Poisson count with mean μ split with allocations (ε₁, ε₂) gives folds with means ε₁μ and ε₂μ. Fission keeps the mean and divides the precision instead. Both let you decide, before looking at the data, how much information goes to selection and how much to inference.

### 1.4 Technical Architecture

| Layer | Technology |
|---|---|
| Language | Python ≥ 3.9 |
| Numerical core | NumPy, SciPy |
| Applied recipes | scikit-learn (k-means clustering, lasso), optional |
| Typing | Fully annotated, ships `py.typed`, checked with mypy |
| Packaging | setuptools / PEP 621 (`pyproject.toml`), version single-sourced from `fissionkit.__version__` |
| Continuous integration | GitHub Actions — Ubuntu, macOS, Windows × Python 3.9–3.13, plus a run at the minimum supported dependency versions, type checking, linting and packaging checks |
| Distribution | This GitHub repository; each release is archived on Zenodo with a DOI |
| License | MIT |

---

## 2. System Requirements

### 2.1 Software

| Item | Requirement |
|---|---|
| Python | 3.9, 3.10, 3.11, 3.12 or 3.13 |
| Operating system | Linux, macOS or Windows (all three are tested in CI) |
| git | Needed only for the `pip install "... @ git+https://..."` form of installation (see [3.2](#32-without-git)) |

**Required dependencies** (installed automatically):

| Package | Minimum version |
|---|---|
| numpy | 1.22 |
| scipy | 1.8 |

**Optional dependency groups:**

| Group | Packages | Needed for |
|---|---|---|
| `recipes` | scikit-learn ≥ 1.1 | `fission_lasso_inference`, and the default clustering of `count_split_de` and `naive_de` |
| `dev` | pytest ≥ 7, scikit-learn ≥ 1.1, scikit-image, matplotlib, mypy | the test suite and the example scripts |

`thin`, the fission functions, `select_rank` and `evaluate_denoisers` need only NumPy and SciPy.

### 2.2 Memory

`thin` returns all folds at once, stacked along a new last axis, so its output occupies *K* times the memory of the input at 8 bytes per entry (int64 for count families, float64 otherwise). Thinning a 2,000 × 5,000 matrix into two folds, for example, produces 2 × 10⁷ entries, about 160 MB. Inputs must be dense arrays; see [8](#8-scope-and-limitations).

---

## 3. Installation

fissionkit is distributed from its GitHub repository and is not published on PyPI.

### 3.1 With pip

```bash
pip install "fissionkit @ git+https://github.com/xiaohan-213/fissionkit"            # core: numpy + scipy only
pip install "fissionkit[recipes] @ git+https://github.com/xiaohan-213/fissionkit"   # + scikit-learn for the applied recipes
```

This installs the latest state of the main branch. To install a specific release, which is recommended for published analyses, append its tag:

```bash
pip install "fissionkit[recipes] @ git+https://github.com/xiaohan-213/fissionkit@v0.2.0"
```

### 3.2 Without git

pip can install a release directly from its source archive, which does not require git:

```bash
pip install "fissionkit[recipes] @ https://github.com/xiaohan-213/fissionkit/archive/refs/tags/v0.2.0.zip"
```

### 3.3 From Source (for development)

```bash
git clone https://github.com/xiaohan-213/fissionkit
cd fissionkit
pip install -e ".[dev]"
```

### 3.4 Verify the Installation

```bash
python -c "import fissionkit; print(fissionkit.__version__)"
# 0.2.0
```

From a source checkout with the `dev` extra installed, the full test suite should pass:

```bash
python -m pytest tests/ -q
# 132 passed
```

The suite takes about ten seconds. It reports `131 passed, 1 skipped` when fissionkit is imported from `src/` without being installed; the skipped test compares `__version__` with the installed package metadata and needs an installation to compare against.

---
## 4. Functional Modules

| Module | Purpose |
|---|---|
| `fissionkit.thinning` | Data thinning for eight families (`thin`, `SUPPORTED_FAMILIES`) |
| `fissionkit.fission` | Gaussian, Bernoulli and Poisson fission; difference-based noise-variance estimate |
| `fissionkit.recipes.cluster_validation` | Differential expression after clustering by count splitting, the same-data baseline, and the per-feature tests they use |
| `fissionkit.recipes.model_selection` | Rank selection, reference-free denoiser evaluation, post-lasso inference |

Every public name is also importable directly from `fissionkit` (see [Appendix A](#a-complete-public-api)).

### 4.1 `fissionkit.thinning` — Data Thinning

`thin` splits an observation *X* into *K* folds *Y₁, …, Y_K* that are mutually independent, sum to *X*, and follow the same family as *X* with a known change of parameter. The allocation weights ε₁, …, ε_K are positive and sum to one; fold *k* carries the fraction ε_k of the information.

| Family | Model for *X* | Fold *k* | Known parameter |
|---|---|---|---|
| `poisson` | Poi(μ) | Poi(ε_k μ) | — |
| `gaussian` | N(μ, σ²) | N(ε_k μ, ε_k σ²) | `sigma2` = σ² |
| `mvgaussian` | N_p(μ, Σ) | N_p(ε_k μ, ε_k Σ) | `Sigma` = Σ |
| `negative_binomial` | NB(size *b*, mean μ) | NB(ε_k *b*, ε_k μ) | `size` = *b* |
| `binomial` | Bin(*n*, *p*) | Bin(round(ε_k *n*), *p*) | `n_trials` = *n* |
| `gamma` | Gamma(shape *a*, rate λ) | Gamma(ε_k *a*, λ) | `shape` = *a* |
| `exponential` | Exp(λ) | Gamma(ε_k, λ) | — |
| `chi_squared` | χ²(ν) | Gamma(ε_k ν/2, 1/2) | `shape` = ν |

The rate parameters λ of the gamma, exponential and chi-squared families never need to be known. The mechanics are multinomial (Poisson), Dirichlet-multinomial (negative binomial), multivariate hypergeometric (binomial), Dirichlet (gamma family) and additive Gaussian noise with a degenerate covariance (Gaussian families).

### 4.2 `fissionkit.fission` — Data Fission

- **`gaussian_fission`** — for X ~ N(μ, σ²) and external noise Z ~ N(0, σ²), returns f = X + τZ and g = X − Z/τ. Both have mean μ; Var(f) = (1 + τ²)σ² and Var(g) = (1 + τ⁻²)σ². They are independent **provided σ² is the true noise variance**; with a wrong σ² they are correlated and downstream inference is silently invalid.
- **`bernoulli_fission`** — flips each binary observation with probability *q* to produce a selection copy *f*, and returns the exact conditional probability P(X = 1 | f) as a function of the success probability. The external randomisation is deliberately not returned: conditional validity requires that inference not use it.
- **`poisson_fission`** — provided for symmetry with the fission paper; for Poisson data fission and two-fold thinning coincide.
- **`estimate_sigma2_diff`** — estimates the noise variance of a one-dimensional sequence from successive differences, for use as `sigma2` when the mean varies slowly (signals, time series).

### 4.3 `fissionkit.recipes.cluster_validation` — Differential Expression After Clustering

- **`count_split_de`** — thins a count matrix into two folds, clusters on the first and tests every feature for a difference between clusters on the second. The normal entry point.
- **`naive_de`** — the double-dipping baseline: clusters and tests on the same matrix, with exactly the same test, so that a comparison with `count_split_de` isolates the effect of reusing the data.
- **`estimate_nb_size`** — per-feature moment estimate of the negative binomial size parameter; `count_split_de` calls it automatically when `size` is not given.
- **Per-feature tests** — `poisson_two_group_test`, `poisson_lr_test`, `welch_two_group_test`, `kruskal_test`. The recipes choose among them automatically:

| Count family | Two groups | Three or more groups |
|---|---|---|
| `poisson` | Exact conditional test (`poisson_two_group_test`): given a feature's total, the group-1 sum is Binomial(total, n₁/(n₁+n₂)) under H₀ | Poisson likelihood-ratio test (`poisson_lr_test`), χ² with G − 1 degrees of freedom |
| `negative_binomial` | Welch t-test (`welch_two_group_test`), robust to overdispersion | Kruskal–Wallis test (`kruskal_test`) |

### 4.4 `fissionkit.recipes.model_selection` — Model Selection

- **`select_rank`** — thins a matrix into a training and a test fold, fits truncated SVDs of increasing rank on the training fold, and scores each rank by its error in predicting the test fold. The in-sample scree curve always decreases with rank; the out-of-fold curve turns where additional components stop being reproducible.
- **`evaluate_denoisers`** — thins one photon-count image into two independent noisy copies, applies each candidate denoiser to the first and scores it against the second. The ranking of denoisers by this score matches their ranking by the true, unobservable error.
- **`fission_lasso_inference`** — fissions the response, selects predictors with the lasso on the selection copy, and computes confidence intervals for the selected coefficients on the independent inference copy.

---

## 5. API Reference

Arrays may be anything NumPy accepts (`list`, `numpy.ndarray`, and so on). `random_state` accepts an `int`, a `numpy.random.Generator`, a `numpy.random.SeedSequence` or `None` (fresh randomness on every call). In the recipes the data arguments are positional and **every option is keyword-only**.

### 5.1 Thinning

```python
thin(X, family, epsilon=None, K=None, *, sigma2=None, Sigma=None, size=None,
     n_trials=None, shape=None, random_state=None)
```

| Parameter | Type | Description |
|---|---|---|
| `X` | array, any shape | Observations. For `mvgaussian` the last axis holds the *p* coordinates of each vector. Must not contain NaN; sparse matrices are refused |
| `family` | str | One of `SUPPORTED_FAMILIES` |
| `epsilon` | sequence of float, optional | Allocation weights: at least two, all positive, summing to one. Defaults to *K* equal folds |
| `K` | int, optional | Number of equal folds when `epsilon` is not given (default 2). Giving both with different lengths is an error |
| `sigma2` | float or array | `gaussian`: noise variance, scalar or broadcastable to `X` |
| `Sigma` | (p, p) array | `mvgaussian`: covariance; must be finite, symmetric, positive semidefinite and non-zero |
| `size` | float or array | `negative_binomial`: size (overdispersion) parameter, scalar or broadcastable to `X`, e.g. one value per column |
| `n_trials` | int or array | `binomial`: number of trials. The values ε_k·n are rounded to integers, which must sum to *n*; no count may exceed *n* |
| `shape` | float or array | `gamma`: shape parameter; `chi_squared`: degrees of freedom |
| `random_state` | seed | Source of randomness |

Scalar known parameters must be finite and strictly positive. Count families (`poisson`, `negative_binomial`, `binomial`) require non-negative integer counts (floats are accepted when every value is an integer); the gamma family requires non-negative observations.

**Returns** an array of shape `X.shape + (K,)`; fold *k* is `result[..., k]`, and the folds sum to `X`. The dtype is int64 for the count families and float64 otherwise. For `mvgaussian` with `X` of shape `(n, p)` the result has shape `(n, p, K)`.

`SUPPORTED_FAMILIES` is the tuple of accepted family names.

### 5.2 Fission

```python
gaussian_fission(X, sigma2, tau=1.0, random_state=None)      # -> (f, g)
```

| Parameter | Type | Description |
|---|---|---|
| `X` | array | Gaussian observations |
| `sigma2` | float or array | Noise variance of `X`; must be correct for f and g to be independent |
| `tau` | float > 0 | Information trade-off. Var(f) = (1 + τ²)σ² (selection copy), Var(g) = (1 + τ⁻²)σ² (inference copy). τ = 1 splits evenly; a larger τ keeps more precision for inference |

Returns two float64 arrays with the shape of `X`.

```python
bernoulli_fission(X, q=0.2, random_state=None)                # -> (f, info)
```

| Parameter | Type | Description |
|---|---|---|
| `X` | array of 0/1 | Binary observations |
| `q` | float in (0, 0.5) | Flip probability of the external noise. A larger `q` leaves less information in `f` |

Returns `f`, an int64 array with P(f = 1) = p(1 − q) + (1 − p)q, and a dictionary `info` with `info["q"]` and `info["conditional_pmf_x1"]`, a function that maps a success probability *p* (scalar or array) to the element-wise conditional probability P(X = 1 | f).

```python
poisson_fission(X, epsilon=0.5, random_state=None)            # -> (f, g)
estimate_sigma2_diff(x)                                       # -> float
```

`poisson_fission` returns two int64 arrays with means εμ and (1 − ε)μ that sum to `X`. `estimate_sigma2_diff` returns mean(diff(x)²)/2 for a sequence of at least three values; it is consistent when the mean changes slowly relative to the sampling rate.

### 5.3 Differential Expression After Clustering

```python
count_split_de(counts, *, family="poisson", epsilon=0.5, cluster=None,
               size=None, random_state=None)
```

| Parameter | Type | Description |
|---|---|---|
| `counts` | (n_samples, n_features) integer array | e.g. a cells × genes matrix of **raw** counts |
| `family` | `"poisson"` or `"negative_binomial"` | Count model; also selects the per-feature test ([4.3](#43-fissionkitrecipescluster_validation--differential-expression-after-clustering)) |
| `epsilon` | float in (0, 1) | Fraction of information allocated to the clustering fold |
| `cluster` | callable, optional | `cluster(train_matrix) -> labels`, one label per sample. Defaults to 2-means on log1p-transformed, library-size-normalised counts. Any number of groups ≥ 2 is supported |
| `size` | float or array, optional | Negative binomial size. If omitted with `family="negative_binomial"`, it is estimated per feature with `estimate_nb_size` |
| `random_state` | seed | Drives the thinning and the default clustering |

Returns a dictionary:

| Key | Content |
|---|---|
| `labels` | Cluster label of every sample, computed on the training fold |
| `pvalues` | One p-value per feature, computed on the test fold |
| `train`, `test` | The two folds |
| `size` | The estimated per-feature size; present only when it was estimated |

```python
naive_de(counts, *, family="poisson", cluster=None, random_state=None)
```

Returns `{"labels", "pvalues"}` computed by clustering and testing the same matrix. Use it only as a baseline.

```python
estimate_nb_size(counts, min_size=1e-8, max_size=1e8)             # -> (n_features,)
poisson_two_group_test(counts, labels)                           # -> (n_features,) p-values
poisson_lr_test(counts, labels)
welch_two_group_test(counts, labels)
kruskal_test(counts, labels)
```

`estimate_nb_size` returns μ²/(s² − μ) per column; columns without evidence of overdispersion (s² ≤ μ) receive `max_size`, which makes negative binomial thinning numerically equivalent to Poisson thinning for them. The two-group tests require exactly two distinct labels.

### 5.4 Model Selection

```python
select_rank(X, *, family="poisson", max_rank=20, epsilon=0.5, center=False,
            sigma2=None, size=None, random_state=None)
```

| Parameter | Type | Description |
|---|---|---|
| `X` | 2-D array | Matrix to decompose |
| `family` | str | Thinning family of `X`; supply `sigma2` for `gaussian` and `size` for `negative_binomial` |
| `max_rank` | int ≥ 1 | Largest rank scored; capped at min(n, p) |
| `epsilon` | float in (0, 1) | Fraction of information in the training fold |
| `center` | bool | `True` centres the columns of the training fold before the SVD (the PCA convention); the default `False` fits the uncentred low-rank model usual for non-negative counts |

Returns `{"errors": array, "best_rank": int}`, where `errors[r-1]` is the out-of-fold mean squared error of rank *r* and `best_rank` minimises it.

```python
evaluate_denoisers(image_counts, denoisers, *, epsilon=0.8, n_repeats=1,
                   random_state=None)
```

| Parameter | Type | Description |
|---|---|---|
| `image_counts` | integer array | One photon-count (Poisson) image, any shape |
| `denoisers` | mapping | `{name: function}`; each function takes a float image and returns a finite array of the same shape |
| `epsilon` | float in (0, 1) | Fraction of the dose the denoisers see. Keep it close to 1 so that the selected setting suits the full-dose image; the reserved fold only serves as an independent judge |
| `n_repeats` | int ≥ 1 | Number of independent thinnings averaged |

Returns `{name: score}`, lower is better. The absolute score includes the noise of the judging fold and is not an estimate of the error itself; compare scores only with each other.

```python
fission_lasso_inference(X, y, *, sigma2=None, tau=1.0, alpha_lasso=None,
                        level=0.9, random_state=None)
```

| Parameter | Type | Description |
|---|---|---|
| `X` | (n, p) array | Design matrix. **Centre its columns** (see [6.9](#69-confidence-intervals-after-lasso-selection)) |
| `y` | (n,) array | Response. **Centre it** |
| `sigma2` | float or `None` | Known noise variance (normal quantiles), or `None` to estimate it (Student-t quantiles; requires n − p ≥ 20) |
| `tau` | float > 0 | Fission trade-off, as in `gaussian_fission` |
| `alpha_lasso` | float or `None` | Lasso penalty; `None` chooses it by 5-fold cross-validation on the selection copy |
| `level` | float in (0, 1) | Confidence level |

Returns a dictionary:

| Key | Content |
|---|---|
| `support` | Indices of the selected columns of `X` |
| `coef` | Least-squares coefficients of the inference copy on the selected columns, in the order of `support` |
| `ci` | Array of shape `(len(support), 2)`: lower and upper limits, row *j* for `support[j]` |
| `level` | The confidence level used |
| `sigma2_mode` | `"known"` or `"estimated"` |
| `diagnostic` | Studentised mean of the residual cross-products of the two copies. Values far from zero indicate that the copies are not independent; in known-scale mode a warning is issued when its absolute value exceeds 4 |
| `note` | Present only in estimated-scale mode when n − p < 40: a reminder that intervals may mildly undercover at such sample sizes |

If the lasso selects nothing, `support` and `coef` are empty, `ci` has shape `(0, 2)` and `diagnostic` is NaN.

---
## 6. Operation Guide

Every example below runs as shown. Each one draws its data and its split from a single random generator `rng`, passed on with `random_state=rng`; see [6.10](#610-reproducibility) for why the split must never reuse the seed that generated the data.

### 6.1 Splitting a Count Matrix

```python
import numpy as np
from fissionkit import thin

rng = np.random.default_rng(1)
X = rng.poisson(8.0, size=(500, 200))          # e.g. 500 cells x 200 genes

folds = thin(X, "poisson", epsilon=[0.5, 0.5], random_state=rng)
train, test = folds[..., 0], folds[..., 1]

print(folds.shape)                              # (500, 200, 2)
print((train + test == X).all())                # True: the folds sum back to X
print(train.mean().round(2), test.mean().round(2))                   # 4.0 4.0
print(np.corrcoef(train.ravel(), test.ravel())[0, 1].round(3))       # -0.004
```

Each fold is a Poisson matrix with half the original mean, and the two folds are independent. Anything decided on `train` — a clustering, a set of selected genes, a fitted model — can be evaluated on `test` as if on new data.

### 6.2 Unequal and Multiple Folds

Continuing the example above:

```python
folds = thin(X, "poisson", epsilon=[0.2, 0.3, 0.5], random_state=rng)   # three unequal folds
folds = thin(X, "poisson", K=5, random_state=rng)                        # five equal folds
```

A fold with allocation ε carries the fraction ε of the information, and in every family its mean is ε times the original mean. Divide by ε to put a fold back on the scale of the data. Give the larger share to the step that needs more precision: a clustering that must find weak structure, or an inference that must detect small effects.

### 6.3 Families With Known Parameters

```python
import numpy as np
from fissionkit import thin, estimate_nb_size

rng = np.random.default_rng(2)

# Gaussian: the noise variance must be known
Y = rng.normal(3.0, 2.0, size=1000)
g = thin(Y, "gaussian", sigma2=4.0, random_state=rng)

# Negative binomial: supply the size, or estimate it per column
C = rng.negative_binomial(10, 10 / 15, size=(400, 50))      # size 10, mean 5
nb = thin(C, "negative_binomial", size=estimate_nb_size(C), random_state=rng)

# Binomial: epsilon * n_trials must round to integers summing to n_trials
B = rng.binomial(10, 0.3, size=300)
bi = thin(B, "binomial", epsilon=[0.4, 0.6], n_trials=10, random_state=rng)

# Gamma: the shape must be known; the rate need not be
G = rng.gamma(shape=3.0, scale=2.0, size=500)
ga = thin(G, "gamma", shape=3.0, random_state=rng)

# Multivariate Gaussian: the last axis holds the coordinates
Sigma = np.array([[1.0, 0.5], [0.5, 2.0]])
V = rng.multivariate_normal([0.0, 1.0], Sigma, size=200)    # (200, 2)
mv = thin(V, "mvgaussian", Sigma=Sigma, random_state=rng)   # (200, 2, 2)
```

The validity of thinning rests on the known parameter being right. For Gaussian data with an unknown variance, use an estimate from a source independent of the data where one exists (replicate measurements, a calibration run), or `estimate_sigma2_diff` for a sequence with a slowly varying mean. For negative binomial counts, `estimate_nb_size` gives a per-column moment estimate.

### 6.4 Gaussian Fission: Select on One Copy, Infer on the Other

```python
import numpy as np
from fissionkit import gaussian_fission, estimate_sigma2_diff

rng = np.random.default_rng(3)
t = np.linspace(0, 1, 2000)
signal = np.sin(2 * np.pi * t)
x = signal + rng.normal(0, 0.5, t.size)          # noise variance 0.25, not known to us

sigma2 = estimate_sigma2_diff(x)                 # 0.241
f, g = gaussian_fission(x, sigma2=sigma2, tau=1.0, random_state=rng)

# Decide anything using f: a threshold, a change point, a model ...
# ... then estimate or test on g, which is independent of f.
print(np.corrcoef(f - signal, g - signal)[0, 1].round(3))    # 0.001
```

Both copies keep the mean of `x`. With `tau=1.0` they have equal variance, 2σ². Increasing `tau` makes the selection copy noisier and the inference copy more precise, since Var(f) = (1 + τ²)σ² and Var(g) = (1 + τ⁻²)σ².

### 6.5 Bernoulli Fission

For binary data there is no independent split. Instead, `bernoulli_fission` produces a garbled copy `f` for selection and the exact conditional law of the original data given `f`, which is what inference after selecting on `f` must use.

```python
import numpy as np
from scipy.optimize import minimize_scalar
from fissionkit import bernoulli_fission

rng = np.random.default_rng(4)
x = rng.binomial(1, 0.3, size=5000)
f, info = bernoulli_fission(x, q=0.2, random_state=rng)

# Inference uses the conditional law of x given f, never f alone.
# Here: the conditional maximum-likelihood estimate of the success probability.
def neg_loglik(p):
    pi = info["conditional_pmf_x1"](p)           # P(x_i = 1 | f_i) at this p
    return -np.sum(x * np.log(pi) + (1 - x) * np.log1p(-pi))

p_hat = minimize_scalar(neg_loglik, bounds=(1e-6, 1 - 1e-6), method="bounded").x
print(round(p_hat, 3))                           # 0.309
```

In a real analysis, the selection made with `f` determines which observations or which model enter the likelihood, and `conditional_pmf_x1` supplies each observation's term. A larger `q` leaves less information in `f` and more for inference.

### 6.6 Differential Expression After Clustering

The script below simulates one homogeneous population with no true clusters, so every gene called "differentially expressed" is a false discovery.

```python
import numpy as np
from fissionkit import count_split_de, naive_de

rng = np.random.default_rng(20260822)
b, mu = 10.0, 5.0
X = rng.negative_binomial(b, b / (b + mu), size=(500, 150))   # no true clusters

naive = naive_de(X, family="negative_binomial", random_state=rng)
split = count_split_de(X, family="negative_binomial", size=b, random_state=rng)

print((naive["pvalues"] < 0.05).mean().round(2))   # 0.37: double dipping
print((split["pvalues"] < 0.05).mean().round(2))   # 0.03: count splitting
```

Clustering and testing the same matrix declares 37% of the genes significant at the 5% level; count splitting brings the rate back to the nominal level.

**On your own data:**

- Pass **raw counts**, samples in rows and features in columns. Do not normalise, log-transform or scale before splitting; the default clustering normalises internally.
- For single-cell RNA-seq and other overdispersed counts use `family="negative_binomial"`. If you omit `size`, it is estimated per gene and returned under `res["size"]`.
- Supply your own clustering through `cluster`. It receives the training fold and must return one label per row; any number of groups of two or more is accepted:

```python
import numpy as np
from sklearn.cluster import KMeans
from fissionkit import count_split_de

rng = np.random.default_rng(20260822)
X = rng.negative_binomial(10, 10 / 15, size=(500, 150))

def three_means(M):
    depth = np.maximum(M.sum(axis=1, keepdims=True), 1)
    Z = np.log1p(M / depth * np.median(depth))
    return KMeans(n_clusters=3, n_init=10, random_state=0).fit_predict(Z)

res = count_split_de(X, family="negative_binomial", cluster=three_means, random_state=rng)
# three groups: one Kruskal-Wallis p-value per gene in res["pvalues"]
```

- `epsilon` is the share of information given to clustering. The default 0.5 is a reasonable start; raising it helps a clustering that must find weak structure, at the cost of power in the tests.

### 6.7 Choosing the Number of Components

```python
import numpy as np
from fissionkit import select_rank

rng = np.random.default_rng(3)
n, p, r = 300, 80, 4
Lam = rng.gamma(2.0, 1.0, (n, r)) @ rng.gamma(2.0, 1.0, (r, p)) / r + 0.5
X = rng.poisson(Lam)                              # a planted rank-4 Poisson matrix

res = select_rank(X, family="poisson", max_rank=15, random_state=rng)
print(res["best_rank"])                           # 3
print(res["errors"][:6].round(3))                 # [2.653 2.603 2.582 2.618 2.689 2.763]
```

The out-of-fold error falls, reaches its minimum and rises again, whereas the in-sample reconstruction error of the same matrix decreases monotonically and would always select the largest rank allowed. Here the weakest planted component lies close to the Poisson noise floor, and the criterion selects rank 3: the number of components that can be reproduced on independent data. Across 20 seeds it selects 2, 3 or 4 (see [7.4](#74-rank-selection)).

For Gaussian data pass the noise variance, and use `center=True` for the PCA convention. Continuing the example above:

```python
Y = rng.normal(size=(200, 30))          # your matrix here; noise variance 1
res = select_rank(Y, family="gaussian", sigma2=1.0, center=True, max_rank=10, random_state=rng)
```

### 6.8 Choosing a Denoiser Without a Clean Reference

```python
import numpy as np
from scipy.ndimage import gaussian_filter
from fissionkit import evaluate_denoisers

rng = np.random.default_rng(5)
yy, xx = np.mgrid[0:256, 0:256]
truth = 6 + 5 * np.sin(xx / 12.0) * np.cos(yy / 17.0)       # unknown in practice
image = rng.poisson(truth)                                   # the only thing observed

denoisers = {f"gauss sigma={s}": (lambda a, s=s: gaussian_filter(a, s))
             for s in [0.5, 1, 2, 3, 4, 6]}
scores = evaluate_denoisers(image, denoisers, epsilon=0.8, n_repeats=10, random_state=rng)
print(min(scores, key=scores.get))               # gauss sigma=3

# Check against the clean image, which a real analysis does not have:
oracle = {k: np.mean((fn(image.astype(float)) - truth) ** 2) for k, fn in denoisers.items()}
print(min(oracle, key=oracle.get))               # gauss sigma=3
```

Any function from image to image of the same shape can serve as a denoiser, including a deep network wrapped in a function. Averaging several thinnings with `n_repeats` stabilises the ranking. The scores are meaningful only relative to each other.

### 6.9 Confidence Intervals After Lasso Selection

```python
from sklearn.datasets import load_diabetes
from fissionkit import fission_lasso_inference

d = load_diabetes()                                   # n = 442, 10 clinical covariates
X = (d.data - d.data.mean(0)) / d.data.std(0)         # centre (and scale) the columns
y = d.target.astype(float)
y = (y - y.mean()) / y.std()                          # centre the response

res = fission_lasso_inference(X, y, sigma2=None, tau=1.0, level=0.9, random_state=0)
for j, k in enumerate(res["support"]):
    lo, hi = res["ci"][j]
    print(f"{d.feature_names[k]:>4s}  coef {res['coef'][j]: .3f}   90% CI [{lo: .3f}, {hi: .3f}]")
```

```
 age  coef  0.077   90% CI [-0.010,  0.163]
 sex  coef -0.194   90% CI [-0.283, -0.106]
 bmi  coef  0.249   90% CI [ 0.153,  0.345]
  bp  coef  0.236   90% CI [ 0.141,  0.331]
  s1  coef -0.068   90% CI [-0.233,  0.097]
  s3  coef -0.152   90% CI [-0.353,  0.050]
  s4  coef  0.038   90% CI [-0.194,  0.270]
  s5  coef  0.351   90% CI [ 0.237,  0.464]
  s6  coef  0.043   90% CI [-0.052,  0.139]
```

**Centre `y` and the columns of `X` before calling.** The lasso step fits an intercept, but the inference step regresses the inference copy on the selected columns without one. If the response has a non-zero mean, the intervals are shifted: in known-scale mode the diagnostic then warns that `sigma2` "appears misspecified" even when it is correct, and in estimated-scale mode coverage falls below nominal without any warning.

**Choosing a mode.**

- `sigma2=<value>` (known scale): use it when the noise variance is genuinely known, for example from the measurement process. Intervals use normal quantiles, and the diagnostic checks the supplied value against the data.
- `sigma2=None` (estimated scale, the default): the scale of the fission noise comes from a least-squares fit on the full design, and the intervals estimate the error variance from the inference copy and use Student-t quantiles. It requires n − p ≥ 20 and is asymptotically exact; at very small samples coverage sits at the low edge of nominal (see [7.2](#72-post-lasso-inference)).

**What the intervals cover.** Each interval is for the coefficient of a selected predictor in the regression on the selected predictors only. It equals the coefficient in the true model whenever the selected set contains every predictor with a non-zero effect.

**Choosing `tau`.** A smaller `tau` gives the lasso a cleaner copy and so a better selection, at the price of wider intervals; a larger `tau` does the opposite. `tau=1.0` splits the information evenly.

### 6.10 Reproducibility

Every function that draws random numbers takes `random_state`. With the same seed and the same versions of NumPy and fissionkit, results are identical. Two practices matter:

- **Never split data with the seed that generated it.** In a simulation, the split's "external" noise must be independent of the data. If the data are drawn as `np.random.default_rng(2).normal(1.0, 1.0, 300)` and then fissioned with `gaussian_fission(y, sigma2=1.0, tau=1.0, random_state=2)`, the fission noise reproduces the data's own noise draw for draw, and the inference copy comes out as the constant 1.0: the true mean, with no noise at all. Every result built on such a split is meaningless. Draw the data and the split from one generator, as all examples in this manual do, or use different seeds.
- **Pass one generator through a whole analysis.** A `numpy.random.Generator` passed as `random_state` continues its stream from call to call, so a single seed at the top of a script reproduces every split below it.

### 6.11 Example Scripts

The `examples/` directory of the repository contains runnable scripts. Running them requires the `dev` extra.

| Script | What it shows | Run time |
|---|---|---|
| `demo_cluster_validation.py` | Double dipping versus count splitting on a null single-cell-like matrix, for one seed and averaged over 20; writes `fig_cluster_validation.pdf/png` | seconds |
| `demo_rank_selection.py` | Out-of-fold versus in-sample scree on a planted rank-4 matrix, over 20 seeds | under a second |
| `demo_denoising.py` | Reference-free denoiser selection on the scikit-image `cell` image; writes `fig_denoising.pdf/png` | seconds |
| `demo_fission_inference.py` | Post-lasso intervals on the scikit-learn diabetes data (the example in [6.9](#69-confidence-intervals-after-lasso-selection)) | seconds |
| `demo_coverage.py` | Coverage of fission intervals versus naive same-data intervals, 60 replications | seconds |
| `audit_fission_diagnostic.py` | Flag rates of the misspecified-scale diagnostic and small-sample coverage of the estimated-scale mode | about a minute |
| `benchmark.py` | Timings of `thin` and `count_split_de` on fixed workloads | seconds |
| `fig_architecture.py` | Draws the package architecture figure | seconds |

---
## 7. Validation and Accuracy

Every number in this section is printed by a script in `examples/` and can be regenerated with it.

### 7.1 The Test Suite

The test suite checks statistical contracts, not only that the code runs.

- **Every thinning family** is checked by seeded simulation with 40,000 draws: the folds must sum exactly to the input, each fold must follow its theoretical distribution (Kolmogorov–Smirnov or chi-square test against the target law), and the folds must be independent (a correlation test, and for the Poisson family a chi-square test of the joint table, since zero correlation alone does not imply independence). The per-test false-alarm rate is 10⁻⁴.
- **Every recipe** is checked for its scientific claim: Type I error control of count splitting on null data, coverage of the fission intervals, recovery of a planted rank, and agreement of the reference-free denoiser ranking with the oracle ranking.
- **The public interface** is pinned: a snapshot records the name, kind and default of every parameter of every public function, other tests pin the values that seeded calls return, and the type annotations of every public function are resolved to catch broken annotations.

CI runs the suite on Ubuntu, macOS and Windows with Python 3.9–3.13, and again at the minimum supported versions of NumPy, SciPy and scikit-learn.

### 7.2 Post-Lasso Inference

`examples/demo_coverage.py` — 60 replications of a Gaussian regression with n = 200, p = 10 and three non-zero coefficients, at nominal 90% coverage:

| Procedure | Coverage | Intervals |
|---|---|---|
| Fission, known scale (normal quantiles) | 0.897 | 389 |
| Fission, estimated scale (Student-t quantiles) | 0.913 | 390 |
| Naive: lasso selection and textbook intervals on the same data | 0.851 | 382 |

`examples/audit_fission_diagnostic.py`, part 1 — how often the misspecified-scale diagnostic of the known-scale mode warns (n = 300, p = 8, 200 replications per row):

| Errors | Supplied `sigma2` | Warning rate |
|---|---|---|
| Normal, variance 1 | 1 (correct) | 0.000 |
| Student t₃ scaled to variance 1 | 1 (correct on average) | 0.005 |
| Normal, variance 4 | 1 (wrong) | 1.000 |

The rare warnings under heavy tails fall on samples whose realised noise variance has drifted from its expected value; in a heavy-tailed setting a warning is a signal to switch to `sigma2=None`.

Part 2 — coverage of the estimated-scale mode at the smallest sample it accepts (n = 30, 300 replications per row, nominal 0.90):

| p | Coverage | Intervals |
|---|---|---|
| 5 | 0.895 | 1,119 |
| 8 | 0.906 | 1,346 |
| 10 | 0.890 | 1,587 |
| pooled | 0.896 | 4,052 |

### 7.3 Differential Expression After Clustering

`examples/demo_cluster_validation.py` — a null matrix of 500 cells × 150 genes with negative binomial counts (mean 5, size 10) and no true clusters, both arms using the same Welch test. Fraction of genes with p < 0.05:

| | Double dipping (`naive_de`) | Count splitting (`count_split_de`) |
|---|---|---|
| Single seed | 0.37 | 0.03 |
| Mean over 20 seeds (range) | 0.374 (0.32–0.43) | 0.055 (0.01–0.09) |

With 150 genes, the Monte-Carlo standard error of a rejection rate near 5% is about 1.8 percentage points. The same double-dipped clustering tested with the exact Poisson test, which does not fit these overdispersed counts, rejects 51% of the genes.

### 7.4 Rank Selection

`examples/demo_rank_selection.py` — a planted rank-4 Poisson matrix (300 × 80), ranks 1–15:

| Criterion | Selected rank |
|---|---|
| Out-of-fold error (`select_rank`), seed 3 | 3 |
| Out-of-fold error, 20 further seeds | 2 (3 seeds), 3 (14 seeds), 4 (3 seeds) |
| In-sample scree | 15, the maximum allowed, in every seed |

The weakest planted component lies close to the Poisson noise floor at this signal level, so the out-of-fold criterion usually selects the rank that is reproducible on independent data rather than the planted rank.

### 7.5 Denoiser Selection

`examples/demo_denoising.py` — the scikit-image `cell` image (a real quantitative-phase microscopy image) as the underlying intensity, a Poisson acquisition at a mean dose of at most 12 photons, and Gaussian filters of eight bandwidths. The reference-free score and the oracle error computed against the clean image both select σ = 4.

### 7.6 Performance

`examples/benchmark.py` on an Intel Xeon at 2.10 GHz (the machine used to prepare this manual):

| Workload | Time |
|---|---|
| `thin`, Poisson, 2,000 × 5,000 (10⁷ entries), two folds | 0.91 s |
| `thin`, Gaussian, 2,000 × 5,000, two folds | 0.56 s |
| `count_split_de`, 500 × 150, negative binomial with estimated size | 0.34 s |

Timings vary with hardware; the workloads and seeds are fixed.

---

## 8. Scope and Limitations

- **Dense arrays only.** Sparse matrices are refused; convert them with `.toarray()`. Sparse and AnnData input are on the roadmap.
- **Known parameters must be right.** Thinning and fission are exact only when the known parameter (`sigma2`, `Sigma`, `size`, `n_trials`, `shape`) is correct. A wrong value leaves the parts dependent, and except for the diagnostic in `fission_lasso_inference`, nothing in the output shows it.
- **Estimated negative binomial sizes.** When `count_split_de` estimates `size`, a truly overdispersed gene that sampling noise places in the "no overdispersion" fallback leaves a small residual dependence between the folds. In stress tests (mild and strong overdispersion, n as small as 60) this did not inflate the Type I error, whose dispersion-robust tests absorb it; extreme overdispersion combined with aggressive clustering has not been ruled out.
- **`fission_lasso_inference`** requires centred data ([6.9](#69-confidence-intervals-after-lasso-selection)); its estimated-scale mode requires n − p ≥ 20 and is asymptotically rather than exactly valid; for p close to or above n, `sigma2` must be supplied. The intervals target the coefficients of the selected submodel.
- **`count_split_de` and `naive_de`** support the `poisson` and `negative_binomial` families.
- **Bernoulli fission** provides the conditional law P(X = 1 | f); building the conditional likelihood for a particular model is left to the user ([6.5](#65-bernoulli-fission)).
- **Splitting spends information.** Each part is less precise than the full data. The allocation should be fixed before the data are examined; choosing it by trying several allocations and keeping the most favourable result reintroduces the double dipping that splitting removes.

---

## 9. Troubleshooting

### 9.1 `poisson thinning requires nonnegative integer counts`

**Cause:** the matrix is not raw counts: it has been normalised, log-transformed, scaled or imputed. The negative binomial and binomial families report the same problem.

**Fix:** thin the raw counts, and normalise afterwards if an analysis needs it. `count_split_de` normalises internally for its default clustering.

### 9.2 `sparse matrices are not supported yet`

**Fix:** `thin(X.toarray(), ...)`. Check the memory first ([2.2](#22-memory)): the output holds *K* dense copies.

### 9.3 `gaussian thinning requires the known variance sigma2`

**Cause:** a family was called without its known parameter. The equivalent messages name `size` (negative binomial), `n_trials` (binomial), `shape` (gamma, chi-squared) and `Sigma` (multivariate Gaussian). `select_rank` passes `sigma2` and `size` through to `thin`, so it reports the same error.

**Fix:** supply the parameter ([6.3](#63-families-with-known-parameters)). A message ending in "to be finite and strictly positive" means the value given was zero, negative, infinite or NaN.

### 9.4 `epsilon must sum to one` or `conflicting fold specifications`

**Fix:** give either `epsilon` (at least two positive weights summing to one) or `K` (equal folds), not both with different lengths.

### 9.5 `epsilon * n_trials must round to integers summing to n_trials`

**Cause:** binomial thinning splits the *n* trials themselves, so each fold must receive a whole number of them. With `n_trials=5`, equal halves would need 2.5 trials each.

**Fix:** choose `epsilon` so that the rounded values of ε_k·n add up to *n*, for example `epsilon=[0.4, 0.6]` for *n* = 5.

### 9.6 `count_split_de() takes 1 positional argument but 2 were given`

**Cause:** an option was passed by position, e.g. `count_split_de(X, "negative_binomial")`. In all four recipes the data are positional and every option is keyword-only. A related message, `family must be a string`, appears when a value meant for another option lands in `family`.

**Fix:** `count_split_de(X, family="negative_binomial")`.

### 9.7 `clustering produced fewer than two groups`

**Cause:** the function passed as `cluster` returned the same label for every sample.

**Fix:** call your function yourself on a thinned fold, e.g. `labels = my_cluster(thin(X, "poisson", random_state=0)[..., 0])`, and inspect `np.unique(labels)`.

### 9.8 `sigma2=None requires n - p >= 20`

**Cause:** with fewer than 20 residual degrees of freedom the pilot least-squares fit comes too close to interpolating the response; the estimated noise scale collapses, and the split would silently degenerate into selecting and inferring on the same data.

**Fix:** supply `sigma2` if the noise variance is known, or reduce the number of candidate predictors.

### 9.9 Warning: `the supplied sigma2 appears misspecified`

**Cause (a):** the response or the columns of `X` are not centred. This is the most common cause; see [6.9](#69-confidence-intervals-after-lasso-selection).

**Cause (b):** `sigma2` does not match the noise variance of the data.

**Cause (c):** heavy-tailed errors, where a correct average variance can still be wrong for the sample at hand (about 0.5% of samples in the audit of [7.2](#72-post-lasso-inference)).

**Fix:** centre `y` and `X`; if the warning remains, use `sigma2=None`.

### 9.10 The Lasso Selected Nothing

**Symptom:** `res["support"]` is empty, `res["ci"]` has shape `(0, 2)` and `res["diagnostic"]` is NaN.

**Fix:** use a smaller `tau`, which gives the selection copy more information, or set `alpha_lasso` explicitly. Decide on either before seeing the intervals.

### 9.11 In a Simulation, One Copy Is Constant or the Parts Are Perfectly Correlated

**Cause:** the same seed generated the data and the split ([6.10](#610-reproducibility)).

**Fix:** draw both from one generator (`rng = np.random.default_rng(seed)`, generate the data with `rng`, pass `random_state=rng`), or use different seeds.

### 9.12 Results Change Every Time

**Cause:** `random_state` was left at `None`.

**Fix:** pass an integer seed or a `numpy.random.Generator`.

### 9.13 `denoiser '...' returned shape ..., expected ...`

**Cause:** a denoiser cropped, padded or resized the image, or (with the message `returned non-finite values`) produced NaN or infinity.

**Fix:** make every denoiser return a finite array of the same shape as its input.

### 9.14 `mvgaussian thinning requires Sigma to be ...`

**Cause:** `Sigma` is not square, not finite, zero, not symmetric, or not positive semidefinite. The checks are relative to the scale of `Sigma`, so they do not depend on the units of the data.

**Fix:** pass the covariance of one observation vector, of size (p, p) where p is the length of the last axis of `X`.

### 9.15 pip Cannot Find `git`

**Fix:** install git, or install from the source archive instead ([3.2](#32-without-git)).

---

## 10. Support and Version Information

### 10.1 Contact

- **Repository:** https://github.com/xiaohan-213/fissionkit
- **Issue tracker:** https://github.com/xiaohan-213/fissionkit/issues

### 10.2 Version

- **Current version:** 0.2.0
- **Released:** 2026-09-20
- **Development status:** Beta
- **DOI:** [10.5281/zenodo.22853159](https://doi.org/10.5281/zenodo.22853159)
- **License:** MIT
- **Change history:** `CHANGELOG.md`

### 10.3 Author

| Name | Affiliation | ORCID |
|---|---|---|
| Xiangnan Han (maintainer, contact: xiaohan-213@163.com) | Yantai Engineering & Technology College | [0009-0003-5987-0908](https://orcid.org/0009-0003-5987-0908) |

### 10.4 Citation

If you use fissionkit in published work, please cite the software together with the method papers listed in [1.1](#11-overview). Machine-readable metadata is in `CITATION.cff`, and the repository page offers it through "Cite this repository".

```bibtex
@misc{han2026fissionkit,
  author  = {Han, Xiangnan},
  title   = {fissionkit: data fission and data thinning in Python},
  version = {0.2.0},
  year    = {2026},
  doi     = {10.5281/zenodo.22853159},
  url     = {https://github.com/xiaohan-213/fissionkit}
}
```

### 10.5 Testing

```bash
python -m pytest tests/ -q
```

See [3.4](#34-verify-the-installation) for the expected result and [7.1](#71-the-test-suite) for what the suite checks. `CONTRIBUTING.md` describes the release checks.

---

## 11. Appendix

### A. Complete Public API

**Thinning:** `thin`, `SUPPORTED_FAMILIES`

**Fission:** `gaussian_fission`, `bernoulli_fission`, `poisson_fission`, `estimate_sigma2_diff`

**Differential expression after clustering:** `count_split_de`, `naive_de`, `estimate_nb_size`, `poisson_two_group_test`, `poisson_lr_test`, `welch_two_group_test`, `kruskal_test`

**Model selection:** `select_rank`, `evaluate_denoisers`, `fission_lasso_inference`

### B. Default Information Allocations

| Function | Parameter | Default | Meaning |
|---|---|---|---|
| `thin` | `epsilon` / `K` | two equal folds | Allocation of information between folds |
| `gaussian_fission` | `tau` | 1.0 | Equal variance in the selection and inference copies |
| `bernoulli_fission` | `q` | 0.2 | Flip probability of the selection copy |
| `poisson_fission` | `epsilon` | 0.5 | Share of the first copy |
| `count_split_de` | `epsilon` | 0.5 | Share given to clustering |
| `select_rank` | `epsilon` | 0.5 | Share of the training fold |
| `evaluate_denoisers` | `epsilon` | 0.8 | Share of the dose seen by the denoisers |
| `fission_lasso_inference` | `tau` | 1.0 | As in `gaussian_fission` |

### C. Return Values

| Function | Returns |
|---|---|
| `thin` | Array of shape `X.shape + (K,)`; int64 for count families, float64 otherwise |
| `gaussian_fission`, `poisson_fission` | Tuple `(f, g)` of arrays with the shape of `X` |
| `bernoulli_fission` | Tuple `(f, info)`; `info` has `"q"` and `"conditional_pmf_x1"` |
| `estimate_sigma2_diff` | `float` |
| `estimate_nb_size` | Array with one size per column |
| `poisson_two_group_test`, `poisson_lr_test`, `welch_two_group_test`, `kruskal_test` | Array with one p-value per column |
| `count_split_de` | `dict`: `labels`, `pvalues`, `train`, `test`, and `size` when estimated |
| `naive_de` | `dict`: `labels`, `pvalues` |
| `select_rank` | `dict`: `errors`, `best_rank` |
| `evaluate_denoisers` | `dict`: denoiser name → score (lower is better) |
| `fission_lasso_inference` | `dict`: `support`, `coef`, `ci`, `level`, `sigma2_mode`, `diagnostic`, and `note` in small estimated-scale samples |

### D. Repository Layout

```
fissionkit/
├── src/fissionkit/
│   ├── __init__.py                  # public API and __version__
│   ├── thinning.py                  # thin, SUPPORTED_FAMILIES
│   ├── fission.py                   # Gaussian, Bernoulli and Poisson fission
│   ├── py.typed                     # marks the package as typed
│   └── recipes/
│       ├── cluster_validation.py    # count splitting and per-feature tests
│       └── model_selection.py       # rank selection, denoisers, post-lasso inference
├── examples/                        # runnable demonstrations, audits and figures
├── tests/                           # pytest suite
├── scripts/                         # release tooling
├── .github/workflows/ci.yml         # CI matrix
├── pyproject.toml
├── CITATION.cff
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                          # MIT
├── README.md
└── USER_MANUAL.md                   # this manual
```

---

*fissionkit 0.2.0 · MIT License · Copyright © 2026 Xiangnan Han*
