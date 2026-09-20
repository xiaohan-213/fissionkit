"""Coverage of fission-based post-lasso intervals vs naive reuse of the data.

Regenerates the coverage numbers quoted in the paper: 60 replications of a
n=200, p=10 Gaussian regression with three active coefficients.  Three
procedures are compared at nominal 90%:
  (1) fission with known noise scale (normal quantiles),
  (2) fission with estimated noise scale (Student-t quantiles),
  (3) naive: select with lasso and compute textbook intervals on the same y.
"""
import numpy as np
from scipy import stats
from sklearn.linear_model import LassoCV

from fissionkit import fission_lasso_inference

rng = np.random.default_rng(7)
n, p, s2 = 200, 10, 1.0
beta = np.zeros(p); beta[:3] = [1.5, -1.0, 0.8]
cov_k = tot_k = cov_t = tot_t = cov_n = tot_n = 0
for rep in range(60):
    X = rng.standard_normal((n, p))
    y = X @ beta + rng.normal(0, np.sqrt(s2), n)
    r = fission_lasso_inference(X, y, sigma2=s2, level=0.9, random_state=rng)
    for j, idx in enumerate(r["support"]):
        lo, hi = r["ci"][j]; cov_k += int(lo <= beta[idx] <= hi); tot_k += 1
    r = fission_lasso_inference(X, y, sigma2=None, level=0.9, random_state=rng)
    for j, idx in enumerate(r["support"]):
        lo, hi = r["ci"][j]; cov_t += int(lo <= beta[idx] <= hi); tot_t += 1
    m = LassoCV(cv=5, random_state=0).fit(X, y)
    supp = np.flatnonzero(m.coef_ != 0)
    if supp.size:
        Xs = X[:, supp]; inv = np.linalg.pinv(Xs.T @ Xs); bh = inv @ Xs.T @ y
        se = np.sqrt(np.diag(inv) * s2); z = stats.norm.ppf(0.95)
        for j, idx in enumerate(supp):
            cov_n += int(bh[j] - z * se[j] <= beta[idx] <= bh[j] + z * se[j]); tot_n += 1
print(f"fission, known sigma2 (z):     {cov_k/tot_k:.3f}  ({tot_k} intervals)")
print(f"fission, estimated sigma2 (t): {cov_t/tot_t:.3f}  ({tot_t} intervals)")
print(f"naive same-data intervals:     {cov_n/tot_n:.3f}  ({tot_n} intervals)")
