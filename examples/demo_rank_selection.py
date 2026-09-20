"""Choosing the number of components of a count matrix without double dipping.

A rank-4 Poisson matrix (n=300 x p=80) is thinned; ranks are scored by
out-of-fold reconstruction error.  The in-sample scree curve decreases
monotonically and therefore always selects the largest rank allowed; the
thinned curve turns near the planted rank.  Because the weakest planted
component is close to the Poisson noise floor at this signal level, the
out-of-fold criterion typically selects rank 3 (2-4 across seeds): it chooses
the rank that is predictable from independent data, which is the honest
answer, whereas the scree plot chooses the maximum regardless of the truth.
"""
import numpy as np

from fissionkit import select_rank


def planted_matrix(rng, n=300, p=80, r=4):
    Lam = rng.gamma(2.0, 1.0, (n, r)) @ rng.gamma(2.0, 1.0, (r, p)) / r + 0.5
    return rng.poisson(Lam)


def in_sample_scree(X, max_rank):
    """Reconstruction error of the rank-r truncated SVD of X on X itself."""
    U, s, Vt = np.linalg.svd(X.astype(float), full_matrices=False)
    return np.array([np.mean((X - (U[:, :k] * s[:k]) @ Vt[:k]) ** 2) for k in range(1, max_rank + 1)])


rng = np.random.default_rng(3)
r, max_rank = 4, 15
X = planted_matrix(rng, r=r)
res = select_rank(X, family="poisson", max_rank=max_rank, random_state=rng)
scree = in_sample_scree(X, max_rank)
print("planted rank:", r, "| selected by thinning:", res["best_rank"],
      "| selected by in-sample scree:", int(np.argmin(scree) + 1), "(= max_rank; curve monotone:", bool(np.all(np.diff(scree) < 0)), ")")
print("out-of-fold errors:", np.round(res["errors"], 3))
print("in-sample errors:  ", np.round(scree, 3))

chosen = []
for seed in range(20):
    rs = np.random.default_rng(seed)
    chosen.append(select_rank(planted_matrix(rs, r=r), family="poisson", max_rank=max_rank, random_state=rs)["best_rank"])
vals, counts = np.unique(chosen, return_counts=True)
print("selected rank over 20 seeds:", dict(zip(vals.tolist(), counts.tolist())),
      "| in-sample scree selects", max_rank, "in every seed")
