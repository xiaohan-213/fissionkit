"""Post-lasso confidence intervals on the diabetes study via data fission.

Real data: the scikit-learn diabetes cohort (n=442, 10 clinical covariates,
Efron et al. 2004).  The response is fissioned; lasso selects predictors on
the selection copy; intervals are computed on the independent inference copy.  A simulation with the same design shows the coverage
contrast against naive reuse of the data (see tests/test_recipes.py).
"""
from sklearn.datasets import load_diabetes

from fissionkit import fission_lasso_inference

d = load_diabetes()
X = (d.data - d.data.mean(0)) / d.data.std(0)
y = d.target.astype(float)
y = (y - y.mean()) / y.std()

# sigma2=None: the noise scale is estimated from the data and the intervals
# use Student-t quantiles on the inference copy (v0.1.1 "estimated" mode).
res = fission_lasso_inference(X, y, sigma2=None, tau=1.0, level=0.9, random_state=0)
print("selected:", [d.feature_names[j] for j in res["support"]])
for j, name in enumerate(d.feature_names[k] for k in res["support"]):
    lo, hi = res["ci"][j]
    print(f"  {name:>4s}  beta = {res['coef'][j]: .3f}   90% CI [{lo: .3f}, {hi: .3f}]")
