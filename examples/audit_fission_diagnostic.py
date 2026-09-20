"""Regenerates the audit numbers quoted for fission_lasso_inference.

Two claims in the documentation and the manuscript are numerical and were
previously not backed by a shipped script:

1. The misspecified-scale diagnostic (known-sigma mode) detects a genuinely
   wrong scale with full power, never flags under normal errors with the
   correct scale, and flags only a few percent of heavy-tailed (t3) samples
   whose *marginal* scale is correct.
2. The estimated-scale mode is asymptotically exact: at n = 30 its intervals
   sit at the low edge of nominal 90% coverage.

Design.  Part 1: n = 300, p = 8, beta = (1.5, -1, 0, ..., 0), 200 replications
each of (a) t3 errors scaled to unit variance with sigma2 = 1 supplied,
(b) N(0, 1) errors with sigma2 = 1 supplied, (c) N(0, 4) errors with sigma2 = 1
supplied.  Part 2: n = 30, p in {5, 8, 10} (all satisfying n - p >= 20),
beta = (1.5, -1, 0, ..., 0), N(0, 1) errors, 300 replications per p, nominal
level 0.90; coverage is pooled over the 900 replications and also reported
per p.  Runs in about a minute on one core.
"""
import time
import warnings

import numpy as np

from fissionkit import fission_lasso_inference

t0 = time.perf_counter()

# ---------------------------------------------------------------- part 1
rng = np.random.default_rng(2026)
n, p, reps = 300, 8, 200
beta = np.zeros(p)
beta[:2] = [1.5, -1.0]
flags = {"t3, correct marginal scale": 0, "normal, correct scale": 0, "normal, scale 4 supplied as 1": 0}
for _ in range(reps):
    X = rng.standard_normal((n, p))
    errors = {
        "t3, correct marginal scale": rng.standard_t(3, n) / np.sqrt(3),
        "normal, correct scale": rng.standard_normal(n),
        "normal, scale 4 supplied as 1": 2.0 * rng.standard_normal(n),
    }
    for key, e in errors.items():
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            fission_lasso_inference(X, X @ beta + e, sigma2=1.0, random_state=rng)
            flags[key] += any("misspecified" in str(x.message) for x in w)
print(f"diagnostic flag rates over {reps} replications (n={n}, p={p}):")
for key, count in flags.items():
    print(f"  {key:<32s} {count / reps:.3f}")

# ---------------------------------------------------------------- part 2
rng = np.random.default_rng(30)
n, reps = 30, 300
pooled_cov = pooled_tot = 0
print(f"estimated-scale mode, n={n}, nominal 0.90:")
for p in (5, 8, 10):
    beta = np.zeros(p)
    beta[:2] = [1.5, -1.0]
    cov = tot = 0
    for _ in range(reps):
        X = rng.standard_normal((n, p))
        y = X @ beta + rng.standard_normal(n)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = fission_lasso_inference(X, y, sigma2=None, level=0.9, random_state=rng)
        for j, idx in enumerate(r["support"]):
            lo, hi = r["ci"][j]
            cov += int(lo <= beta[idx] <= hi)
            tot += 1
    pooled_cov += cov
    pooled_tot += tot
    print(f"  p={p:<3d} coverage {cov / tot:.3f}  ({tot} intervals)")
print(f"  pooled over {3 * reps} replications: {pooled_cov / pooled_tot:.3f}  ({pooled_tot} intervals)")
print(f"elapsed {time.perf_counter() - t0:.0f} s")
