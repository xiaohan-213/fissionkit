"""fissionkit: data fission and data thinning for valid statistics after selection.

Implements the splitting recipes of Leiner et al. (JASA 2023, data fission),
Neufeld et al. (JMLR 2024, data thinning) and Dharamshi et al. (JASA 2025,
generalized data thinning), together with applied workflows for cluster
validation, rank selection, reference-free denoiser evaluation and
post-selection regression inference.
"""
from .fission import (
    bernoulli_fission,
    estimate_sigma2_diff,
    gaussian_fission,
    poisson_fission,
)
from .recipes.cluster_validation import (
    count_split_de,
    estimate_nb_size,
    kruskal_test,
    naive_de,
    poisson_lr_test,
    poisson_two_group_test,
    welch_two_group_test,
)
from .recipes.model_selection import (
    evaluate_denoisers,
    fission_lasso_inference,
    select_rank,
)
from .thinning import SUPPORTED_FAMILIES, thin

__version__ = "0.2.0"
__all__ = [
    "SUPPORTED_FAMILIES",
    "bernoulli_fission",
    "count_split_de",
    "estimate_nb_size",
    "estimate_sigma2_diff",
    "evaluate_denoisers",
    "fission_lasso_inference",
    "gaussian_fission",
    "kruskal_test",
    "naive_de",
    "poisson_fission",
    "poisson_lr_test",
    "poisson_two_group_test",
    "select_rank",
    "thin",
    "welch_two_group_test",
]
