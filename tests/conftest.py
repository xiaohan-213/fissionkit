"""Pin the import path to this repository's source tree.

A stale editable install once redirected
``import fissionkit`` to an old copy of the package, so a development session
measured and documented the behaviour of code that was never the code under
test.  This conftest makes that failure mode structurally impossible for the
test suite: the local ``src/`` directory is placed at the front of
``sys.path`` before collection, and a hard assertion verifies that the
imported package actually resolves inside this repository.
"""

import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC))

import fissionkit

_resolved = pathlib.Path(fissionkit.__file__).resolve()
assert _resolved.is_relative_to(_SRC), (
    f"import-path contamination: fissionkit resolved to {_resolved}, "
    f"expected a module under {_SRC}. A stale editable install or PYTHONPATH "
    "entry is shadowing the tree under test."
)
