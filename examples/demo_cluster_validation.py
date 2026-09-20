"""Double dipping vs count splitting on a null single-cell-like matrix.

Simulates a homogeneous population of 500 cells x 150 genes with negative
binomial counts calibrated to typical droplet scRNA-seq scale (mean ~5,
size ~10), where NO true clusters exist.  Clustering then testing on the same
matrix declares a large fraction of genes 'differentially expressed'; count
splitting restores uniform p-values.  Reproduces the phenomenon documented by
Neufeld et al. (2024) / countsplit; the same script applied to a real 10X
matrix (user-downloadable) yields the same contrast.

Both arms use the same per-feature test (Welch, dispersion-robust) so that the
contrast isolates double dipping.  For reference the script also prints the
rejection rate of the baseline with the exact Poisson test, which on these
overdispersed counts adds a separate, test-misfit inflation; this was the
baseline reported before 0.1.11 (51% instead of 37%).  The single-seed figures
are followed by an average over 20 seeds, because with 150 features the
Monte-Carlo standard error of a rejection rate near 5% is about 1.8 points.
"""
import argparse
import pathlib

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fissionkit import count_split_de, naive_de

_HERE = pathlib.Path(__file__).resolve().parent
# Anchor output to the script's own directory: writing to the working
# directory produced duplicate figures depending on where it was run from.

INK, SLATE, ACCENT, TAUPE = "#2f3437", "#5b6b78", "#6e8898", "#8c7a6b"

parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("--seeds", type=int, default=20,
                    help="number of seeds for the Monte-Carlo average (default 20; 0 skips it)")
N_SEEDS = parser.parse_args().seeds

rng = np.random.default_rng(20260822)
b, mu = 10.0, 5.0
X = rng.negative_binomial(b, b / (b + mu), size=(500, 150))

naive = naive_de(X, family="negative_binomial", random_state=rng)
split = count_split_de(X, family="negative_binomial", size=b, epsilon=0.5, random_state=rng)
naive_poisson = naive_de(X, family="poisson", cluster=lambda M: naive["labels"])

frac_naive = (naive["pvalues"] < 0.05).mean()
frac_split = (split["pvalues"] < 0.05).mean()
frac_naive_poisson = (naive_poisson["pvalues"] < 0.05).mean()
print(f"fraction of 'significant' genes at 0.05  |  double dipping: {frac_naive:.2f}   count splitting: {frac_split:.2f}")
print(f"  (same double-dipped labels, mismatched exact Poisson test: {frac_naive_poisson:.2f} - the pre-0.1.11 baseline)")

# Monte-Carlo spread over seeds: the honest summary of a rejection rate that
# is expected to sit at the nominal 5% under count splitting.
nv, sp = [], []
for seed in range(N_SEEDS):
    r = np.random.default_rng(seed)
    Xs = r.negative_binomial(b, b / (b + mu), size=(500, 150))
    nv.append((naive_de(Xs, family="negative_binomial", random_state=r)["pvalues"] < 0.05).mean())
    sp.append((count_split_de(Xs, family="negative_binomial", size=b, random_state=r)["pvalues"] < 0.05).mean())
if N_SEEDS:
    print(f"over {N_SEEDS} seeds  |  double dipping: mean {np.mean(nv):.3f} (range {min(nv):.2f}-{max(nv):.2f})"
          f"   count splitting: mean {np.mean(sp):.3f} (range {min(sp):.2f}-{max(sp):.2f})")

fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
for ax, pv, title, frac in [
    (axes[0], naive["pvalues"], "Double dipping (cluster and test on X, same test)", frac_naive),
    (axes[1], split["pvalues"], "Count splitting (cluster on fold 1, test on fold 2)", frac_split),
]:
    ax.hist(pv, bins=20, range=(0, 1), color=ACCENT if ax is axes[1] else TAUPE,
            edgecolor="white", linewidth=0.6, density=True)
    ax.axhline(1.0, color=SLATE, lw=1.0, ls="--")
    ax.set_title(title, fontsize=8.5, color=INK)
    ax.set_xlabel("per-gene p-value (null data: no true clusters)", fontsize=8)
    ax.text(0.55, 0.9, f"{frac*100:.0f}% < 0.05", transform=ax.transAxes,
            fontsize=9, color=INK, weight="bold")
    ax.tick_params(labelsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
axes[0].set_ylabel("density", fontsize=8)
fig.tight_layout()
fig.savefig(_HERE / "fig_cluster_validation.pdf", bbox_inches="tight", metadata={"CreationDate": None})
fig.savefig(_HERE / "fig_cluster_validation.png", dpi=300, bbox_inches="tight")
print("wrote fig_cluster_validation.{pdf,png}")
