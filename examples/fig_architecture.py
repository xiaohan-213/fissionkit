"""Regenerates the architecture figure (manuscript Fig. 1).

Three layers: splitting engines, applied recipes, test harness.  The thinning
engine returns the folds stacked on a trailing axis; the fission engine returns
a pair ``(f, g)`` (and ``bernoulli_fission`` a copy plus a conditional-law
callable), so the two engines are drawn with their own output boxes.
"""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

_HERE = pathlib.Path(__file__).resolve().parent

INK, SLATE, ACCENT, TAUPE = "#2f3437", "#5b6b78", "#6e8898", "#8c7a6b"
FILL, FILL_DARK, FILL_WARM = "#eef1f3", "#dde3e8", "#efe9e3"

fig, ax = plt.subplots(figsize=(7.4, 3.6))
ax.set_xlim(0, 100)
ax.set_ylim(0, 50)
ax.axis("off")


def box(x, y, w, h, text, fill="white", edge=SLATE, size=6.6, weight="normal", color=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                linewidth=0.9, edgecolor=edge, facecolor=fill))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            color=color, weight=weight, linespacing=1.35)


def arrow(p, q, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, linewidth=0.9,
                                 color=SLATE, connectionstyle=f"arc3,rad={rad}"))


# -- inputs and engines ------------------------------------------------------
# Fission sits above thinning so that every engine -> output -> recipe arrow is
# straight: the thinning folds feed three recipes from below, the fission pair
# feeds the fourth along the right-hand side.
box(1, 29, 21, 13, "Input array\nany shape: counts,\nintensities,\nGaussian data", size=6.4)
ax.text(38.5, 48.2, "SPLITTING ENGINES", ha="center", fontsize=6.8, weight="bold", color=ACCENT)
box(25, 37, 27, 9, "fission.gaussian_fission( )\nfission.bernoulli_fission( )", fill=FILL)
box(25, 25, 27, 9, "thinning.thin( )\n8 families, arbitrary folds\nand allocations $\\varepsilon$", fill=FILL)
arrow((22.5, 38), (24.5, 41.5))
arrow((22.5, 33), (24.5, 29.5))

# -- engine outputs ----------------------------------------------------------
box(57, 37, 20, 9, "independent pair (f, g)\nor copy + exact\nconditional law of X | f", fill=FILL_DARK)
box(57, 25, 20, 9, "independent folds\nstacked on a trailing axis\nX.shape + (K,)", fill=FILL_DARK)
arrow((52.5, 41.5), (56.5, 41.5))
arrow((52.5, 29.5), (56.5, 29.5))

# -- test harness ------------------------------------------------------------
box(83, 29, 15.5, 17, "TEST HARNESS\nreconstruction\nmarginal laws\nindependence\nerror control\ncoverage", fill=FILL_WARM, edge=TAUPE)
arrow((77.5, 41.5), (82.5, 40))
arrow((77.5, 29.5), (82.5, 33))

# -- recipes -----------------------------------------------------------------
ax.text(2.5, 7.0, "APPLIED RECIPES", ha="left", fontsize=6.8, weight="bold", color=ACCENT)
recipes = [
    (3, "count_split_de\nDE testing after clustering"),
    (27, "select_rank\nout-of-fold PCA rank"),
    (51, "evaluate_denoisers\nreference-free scoring"),
    (75, "fission_lasso_inference\npost-selection CIs"),
]
for x, text in recipes:
    box(x, 9, 22, 8, text)
for x in (14, 38, 62):          # thinning folds -> three recipes
    arrow((67, 24.5), (x, 17.6))
arrow((77.5, 38.5), (86, 17.6))  # fission pair -> post-selection CIs

# -- outcome -----------------------------------------------------------------
box(15, 0.6, 70, 5.2, "valid p-values \u00b7 nominal-coverage intervals \u00b7 honestly selected ranks and denoisers",
    fill=FILL_DARK, size=6.4)
for x in (14, 38, 62, 86):
    arrow((x, 8.6), (50, 6.3))

fig.savefig(_HERE / "fig_architecture.pdf", bbox_inches="tight", metadata={"CreationDate": None})
fig.savefig(_HERE / "fig_architecture.png", dpi=300, bbox_inches="tight")
print("wrote fig_architecture.{pdf,png}")
