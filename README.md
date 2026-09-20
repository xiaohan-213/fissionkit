# fissionkit

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22853159.svg)](https://doi.org/10.5281/zenodo.22853159)

**Data fission and data thinning for valid statistics after selection.**

`fissionkit` splits a *single* observation — a count, a Gaussian measurement, a
whole matrix, an image — into independent parts that can play the roles of
"training set" and "test set" even when there are no rows to split. It solves
a concrete and pervasive problem: **using the same data twice** (cluster then
test, select then infer, fit then evaluate) silently invalidates p-values,
confidence intervals and model-selection criteria. Thinning and fission
restore validity, at a user-controlled information price.

The package implements, under one API, the splitting recipes of:

- J. Leiner, B. Duan, L. Wasserman, A. Ramdas, *Data fission: splitting a
  single data point*, *Journal of the American Statistical Association* 120 (2025) 135–146.
- A. Neufeld, A. Dharamshi, L. L. Gao, D. Witten, *Data thinning for
  convolution-closed distributions*, *JMLR* 25(57) (2024).
- A. Dharamshi, A. Neufeld, K. Motwani, L. L. Gao, D. Witten, J. Bien,
  *Generalized data thinning using sufficient statistics*, *JASA* (2025).

All methodological credit belongs to those authors; `fissionkit` contributes
an independent, tested, `pip`-installable Python implementation together with
four ready-to-run applied workflows.

## Install

fissionkit is installed from this repository (pip needs `git` on the PATH):

```bash
pip install "fissionkit @ git+https://github.com/xiaohan-213/fissionkit"            # core: numpy + scipy only
pip install "fissionkit[recipes] @ git+https://github.com/xiaohan-213/fissionkit"   # + scikit-learn for the applied recipes
```

To pin a release, append its tag to the URL, e.g.
`git+https://github.com/xiaohan-213/fissionkit@v0.2.0`.

## Quickstart

```python
import numpy as np
from fissionkit import thin, gaussian_fission

X = np.random.default_rng(1).poisson(8.0, size=(500, 200))  # e.g. cells x genes
folds = thin(X, "poisson", epsilon=[0.5, 0.5], random_state=1)
train, test = folds[..., 0], folds[..., 1]     # independent, sum back to X

y = np.random.default_rng(2).normal(1.0, 1.0, 300)
f, g = gaussian_fission(y, sigma2=1.0, tau=1.0, random_state=2)
# select on f, infer on g - they are exactly independent
```

Eight families are supported: `poisson`, `gaussian`, `mvgaussian`,
`negative_binomial`, `binomial`, `gamma`, `exponential`, `chi_squared`,
with arbitrary numbers of folds and unequal allocations `epsilon`. Nuisance
parameters (`sigma2`, `Sigma`, `size`, `n_trials`, `shape`) are validated for
presence and value at call time. `poisson_fission` is provided for symmetry
with the fission paper; for Poisson data fission and thinning coincide.

## The four applied workflows

| problem | function | one-line story |
| --- | --- | --- |
| Differential expression after clustering (double dipping) | `count_split_de` | cluster on one thinned fold, test on the other (2 or more groups; NB size estimated automatically); Type-I error restored. `naive_de(family=...)` is the same-data baseline with the *same* test, for honest comparisons |
| How many principal components? | `select_rank` | out-of-fold reconstruction error on thinned folds replaces the double-dipping scree plot |
| Which denoiser, with no clean reference? | `evaluate_denoisers` | thin one photon-count image into two independent noisy copies; score denoisers Noise2Noise-style |
| Confidence intervals after lasso selection | `fission_lasso_inference` | select on the fission copy, infer on the reserved copy (known-scale z or estimated-scale t mode); nominal coverage, with a diagnostic for misspecified noise scales |

Inputs must be dense NumPy arrays (sparse/AnnData adapters are on the roadmap). Each workflow has a runnable script under `examples/` using real data where
it ships with the scientific Python stack (the scikit-image cell microscopy
image, the scikit-learn diabetes study) and calibrated simulations
elsewhere; `examples/audit_fission_diagnostic.py` regenerates the audit
numbers quoted for the misspecified-scale diagnostic and the small-sample
coverage of the estimated-scale mode. The example scripts need the `dev`
extra (scikit-learn, scikit-image, matplotlib, pytest); from a clone of the
repository, run `pip install -e ".[dev]"`.

## Why not just sample-split?

Because often you cannot: a single-cell matrix has no second cell population
to hold out for *these* cells; an image is one observation; a regression with
n comparable to p cannot afford to discard half its rows. Thinning splits
*within* each observation, spending information instead of observations.

## Testing

The test suite checks the *statistical* contracts, not just execution: for
every family it verifies by simulation that folds reconstruct the input, have
the correct marginal law (KS / chi-square tests) and are independent, and for
every recipe it verifies the scientific claim (error control, coverage, rank
recovery, oracle-consistent denoiser ranking).

```bash
python -m pytest tests/
```

## License

MIT. Method papers should be cited alongside the software (see above).
