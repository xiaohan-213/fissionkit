"""Snapshot of the public calling convention.

Bit-identity tests pin what the functions *return*; this pins what they
*accept*: the name, kind (positional / keyword-only) and default of every
parameter of every public callable. `naive_de` gained a positional `family`
in 0.1.11 and broke positional callers for four releases without any test
noticing, because nothing compared signatures. A change here must be made
deliberately: update the snapshot in the same commit and describe the change
in CHANGELOG.md as affecting existing calls.

Since 0.1.16 the four applied recipes take their data positionally and every
option keyword-only, so that adding an option can never shift an existing
call.
"""
import inspect

import pytest

import fissionkit

SNAPSHOT = {
    'bernoulli_fission': [
        ('X', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('q', 'POSITIONAL_OR_KEYWORD', '0.2'),
        ('random_state', 'POSITIONAL_OR_KEYWORD', 'None'),
    ],
    'count_split_de': [
        ('counts', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('family', 'KEYWORD_ONLY', "'poisson'"),
        ('epsilon', 'KEYWORD_ONLY', '0.5'),
        ('cluster', 'KEYWORD_ONLY', 'None'),
        ('size', 'KEYWORD_ONLY', 'None'),
        ('random_state', 'KEYWORD_ONLY', 'None'),
    ],
    'estimate_nb_size': [
        ('counts', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('min_size', 'POSITIONAL_OR_KEYWORD', '1e-08'),
        ('max_size', 'POSITIONAL_OR_KEYWORD', '100000000.0'),
    ],
    'estimate_sigma2_diff': [
        ('x', 'POSITIONAL_OR_KEYWORD', '<required>'),
    ],
    'evaluate_denoisers': [
        ('image_counts', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('denoisers', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('epsilon', 'KEYWORD_ONLY', '0.8'),
        ('n_repeats', 'KEYWORD_ONLY', '1'),
        ('random_state', 'KEYWORD_ONLY', 'None'),
    ],
    'fission_lasso_inference': [
        ('X', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('y', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('sigma2', 'KEYWORD_ONLY', 'None'),
        ('tau', 'KEYWORD_ONLY', '1.0'),
        ('alpha_lasso', 'KEYWORD_ONLY', 'None'),
        ('level', 'KEYWORD_ONLY', '0.9'),
        ('random_state', 'KEYWORD_ONLY', 'None'),
    ],
    'gaussian_fission': [
        ('X', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('sigma2', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('tau', 'POSITIONAL_OR_KEYWORD', '1.0'),
        ('random_state', 'POSITIONAL_OR_KEYWORD', 'None'),
    ],
    'kruskal_test': [
        ('counts', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('labels', 'POSITIONAL_OR_KEYWORD', '<required>'),
    ],
    'naive_de': [
        ('counts', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('family', 'KEYWORD_ONLY', "'poisson'"),
        ('cluster', 'KEYWORD_ONLY', 'None'),
        ('random_state', 'KEYWORD_ONLY', 'None'),
    ],
    'poisson_fission': [
        ('X', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('epsilon', 'POSITIONAL_OR_KEYWORD', '0.5'),
        ('random_state', 'POSITIONAL_OR_KEYWORD', 'None'),
    ],
    'poisson_lr_test': [
        ('counts', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('labels', 'POSITIONAL_OR_KEYWORD', '<required>'),
    ],
    'poisson_two_group_test': [
        ('counts', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('labels', 'POSITIONAL_OR_KEYWORD', '<required>'),
    ],
    'select_rank': [
        ('X', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('family', 'KEYWORD_ONLY', "'poisson'"),
        ('max_rank', 'KEYWORD_ONLY', '20'),
        ('epsilon', 'KEYWORD_ONLY', '0.5'),
        ('center', 'KEYWORD_ONLY', 'False'),
        ('sigma2', 'KEYWORD_ONLY', 'None'),
        ('size', 'KEYWORD_ONLY', 'None'),
        ('random_state', 'KEYWORD_ONLY', 'None'),
    ],
    'thin': [
        ('X', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('family', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('epsilon', 'POSITIONAL_OR_KEYWORD', 'None'),
        ('K', 'POSITIONAL_OR_KEYWORD', 'None'),
        ('sigma2', 'KEYWORD_ONLY', 'None'),
        ('Sigma', 'KEYWORD_ONLY', 'None'),
        ('size', 'KEYWORD_ONLY', 'None'),
        ('n_trials', 'KEYWORD_ONLY', 'None'),
        ('shape', 'KEYWORD_ONLY', 'None'),
        ('random_state', 'KEYWORD_ONLY', 'None'),
    ],
    'welch_two_group_test': [
        ('counts', 'POSITIONAL_OR_KEYWORD', '<required>'),
        ('labels', 'POSITIONAL_OR_KEYWORD', '<required>'),
    ],
}


def _current(name):
    sig = inspect.signature(getattr(fissionkit, name))
    return [(p.name, p.kind.name, "<required>" if p.default is inspect._empty else repr(p.default))
            for p in sig.parameters.values()]


def test_snapshot_covers_every_public_callable():
    public = {n for n in fissionkit.__all__ if callable(getattr(fissionkit, n))}
    assert public == set(SNAPSHOT), (public ^ set(SNAPSHOT))


@pytest.mark.parametrize("name", sorted(SNAPSHOT))
def test_public_signature_unchanged(name):
    assert _current(name) == SNAPSHOT[name], (
        f"{name}: public signature changed; if intended, update SNAPSHOT and record the "
        f"change in CHANGELOG.md.\n  now:      {_current(name)}\n  snapshot: {SNAPSHOT[name]}")


@pytest.mark.parametrize("name", ["count_split_de", "naive_de", "select_rank", "evaluate_denoisers", "fission_lasso_inference"])
def test_recipe_options_are_keyword_only(name):
    params = list(inspect.signature(getattr(fissionkit, name)).parameters.values())
    data = [p for p in params if p.default is inspect._empty]
    options = [p for p in params if p.default is not inspect._empty]
    assert all(p.kind is p.POSITIONAL_OR_KEYWORD for p in data), name
    assert all(p.kind is p.KEYWORD_ONLY for p in options), name
