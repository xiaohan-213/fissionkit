"""Contracts of the public API itself, as opposed to its numerical behaviour.

These checks exist because each of them corresponds to a defect that shipped
at least once and that the numerical test suite could not have caught:

* Type annotations that referenced names never imported into the module.  With
  ``from __future__ import annotations`` in force the annotations are stored as
  strings and never evaluated, so the package imported cleanly, every test
  passed, and the annotations were nevertheless useless to a type checker.
  Only ``typing.get_type_hints`` forces evaluation.
* A distribution whose recorded version disagreed with ``__version__``.
* A ``py.typed`` marker that was declared in the packaging configuration but
  did not reach the built wheel, so type checkers ignored the annotations.
"""

from __future__ import annotations

import importlib
import inspect
import pathlib
import typing

import pytest

import fissionkit


def _public_callables():
    for name in fissionkit.__all__:
        obj = getattr(fissionkit, name)
        if callable(obj):
            yield name, obj


@pytest.mark.parametrize("name", fissionkit.__all__)
def test_public_name_is_exported(name):
    """Every name promised by __all__ must actually be reachable."""
    assert hasattr(fissionkit, name), f"{name} is in __all__ but not importable"


@pytest.mark.parametrize("name,func", list(_public_callables()), ids=lambda x: x)
def test_annotations_resolve(name, func):
    """Annotations must evaluate, not merely parse.

    A NameError here means the signature references a type that the defining
    module never imported: the annotation is dead weight that no type checker
    can use.
    """
    try:
        hints = typing.get_type_hints(func)
    except NameError as exc:  # pragma: no cover - the failure we are guarding
        pytest.fail(
            f"{name}: annotation references an undefined name ({exc}). "
            "The module is missing an import; because PEP 563 defers "
            "evaluation this cannot fail at import time."
        )
    except TypeError as exc:  # pragma: no cover - the other failure we are guarding
        pytest.fail(
            f"{name}: annotation cannot be evaluated on this interpreter ({exc}). "
            "PEP 604 unions such as 'X | None' evaluate only on Python >= 3.10; "
            "with Python 3.9 supported, signatures must use Optional[...] / "
            "Union[...] (the package shipped 'X | None' from 0.1.7 to 0.1.11)."
        )
    params = [
        p
        for p in inspect.signature(func).parameters
        if p not in ("self", "args", "kwargs")
    ]
    missing = [p for p in params if p not in hints]
    assert not missing, f"{name}: parameters without annotations: {missing}"
    assert "return" in hints, f"{name}: no return annotation"


def test_version_is_single_sourced():
    """__version__ and the installed distribution metadata must agree.

    They diverged once, when pyproject.toml carried its own hardcoded version.
    Skipped when the package is not installed (e.g. a bare PYTHONPATH run).
    """
    import importlib.metadata as md

    try:
        recorded = md.version("fissionkit")
    except md.PackageNotFoundError:
        pytest.skip("fissionkit is not installed; nothing to compare against")
    assert recorded == fissionkit.__version__, (
        f"distribution metadata says {recorded} but "
        f"fissionkit.__version__ says {fissionkit.__version__}"
    )


def test_py_typed_marker_present():
    """PEP 561 marker must ship beside the package, or annotations are ignored."""
    root = pathlib.Path(fissionkit.__file__).parent
    assert (root / "py.typed").is_file(), (
        f"py.typed missing from {root}; type checkers will not read the "
        "annotations even though they are present in the source"
    )


def test_submodules_import_cleanly():
    """Importing a submodule directly must not depend on the package __init__."""
    for mod in (
        "fissionkit.thinning",
        "fissionkit.fission",
        "fissionkit.recipes.cluster_validation",
        "fissionkit.recipes.model_selection",
    ):
        importlib.import_module(mod)


def test_docstrings_on_public_api():
    """Every exported callable carries a docstring."""
    undocumented = [n for n, f in _public_callables() if not (f.__doc__ or "").strip()]
    assert not undocumented, f"undocumented public callables: {undocumented}"
