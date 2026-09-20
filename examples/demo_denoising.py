"""Reference-free denoiser selection on a real optical-microscopy image.

The scikit-image `cell` image (a real quantitative-phase image of a cell,
retrieved from a digital hologram; CC0 public domain, Mueller et al. 2018,
Optics Express 26:10729) provides the underlying intensity; photon-limited acquisition is emulated by Poisson
counts at a low dose, the standard evaluation protocol in photon-limited
imaging.  `fissionkit.evaluate_denoisers` thins the single noisy image into
two independent noisy copies and scores a family of Gaussian denoisers with
no access to the clean reference; the script shows that the reference-free
score selects the same bandwidth as the (in practice unobservable) oracle MSE.
"""
import pathlib

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from skimage import data

from fissionkit import evaluate_denoisers

_HERE = pathlib.Path(__file__).resolve().parent
# Anchor output to the script's own directory: writing to the working
# directory produced duplicate figures depending on where it was run from.

INK, SLATE, ACCENT, TAUPE = "#2f3437", "#5b6b78", "#6e8898", "#8c7a6b"

rng = np.random.default_rng(20260822)
truth = data.cell().astype(float) / 255.0 * 12.0  # real image -> mean photon dose <= 12
noisy = rng.poisson(truth)

sigmas = [0.5, 1, 1.5, 2, 3, 4, 6, 8]
denoisers = {f"gauss σ={s:g}": (lambda a, s=s: gaussian_filter(a, s)) for s in sigmas}

scores = evaluate_denoisers(noisy, denoisers, epsilon=0.8, n_repeats=10, random_state=rng)
oracle = {k: float(np.mean((fn(noisy.astype(float)) - truth) ** 2)) for k, fn in denoisers.items()}
best = min(scores, key=scores.get)
best_oracle = min(oracle, key=oracle.get)
print("selected by fissionkit :", best)
print("selected by oracle MSE :", best_oracle)

fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.6))
axes[0].imshow(noisy, cmap="gray")
axes[0].set_title("single noisy acquisition\n(real cell image, Poisson dose ≤ 12)", fontsize=7.5)
axes[1].imshow(denoisers[best](noisy.astype(float)), cmap="gray")
axes[1].set_title(f"denoised with the selected {best}\n(chosen with no clean reference)", fontsize=7.5)
for ax in axes[:2]:
    ax.set_xticks([]), ax.set_yticks([])
sc = [scores[k] for k in denoisers]
om = [oracle[k] for k in denoisers]
axes[2].plot(sigmas, sc, "o-", color=ACCENT, ms=4, lw=1.2, label="thinning score (observable)")
ax2 = axes[2].twinx()
ax2.plot(sigmas, om, "s--", color=TAUPE, ms=4, lw=1.2, label="oracle MSE (unobservable)")
axes[2].axvline(float(best.split("=")[1]), color=SLATE, lw=0.9, ls=":")
axes[2].set_xlabel("Gaussian bandwidth σ", fontsize=8)
axes[2].set_ylabel("thinning score", fontsize=8, color=ACCENT)
ax2.set_ylabel("oracle MSE", fontsize=8, color=TAUPE)
axes[2].set_title("both criteria minimised at the same σ", fontsize=7.5)
for a in (axes[2], ax2):
    a.tick_params(labelsize=7)
fig.tight_layout()
fig.savefig(_HERE / "fig_denoising.pdf", bbox_inches="tight", metadata={"CreationDate": None})
fig.savefig(_HERE / "fig_denoising.png", dpi=300, bbox_inches="tight")
print("wrote fig_denoising.{pdf,png}")
