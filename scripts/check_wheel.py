"""Verify that a built wheel ships exactly the package source tree.

The test suite always runs against ``src/`` (``tests/conftest.py`` pins the
import path there), so nothing else guarantees that what is installed from
the wheel is what was tested.  This compares every file under the wheel's
``fissionkit/`` directory with ``src/fissionkit/`` by content hash, in both
directions, and exits non-zero on any difference.  A file present under
``src/fissionkit`` but absent from the wheel - typically a data file not
declared in ``[tool.setuptools.package-data]`` - is reported as "missing from
wheel" and fails the check on purpose: the tree that was tested would not be
the tree that ships.  Run by the CI ``package`` job after ``python -m build``.

    python scripts/check_wheel.py dist/fissionkit-*.whl src/fissionkit
"""
import hashlib
import pathlib
import sys
import zipfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(wheel: str, src: str) -> int:
    src_dir = pathlib.Path(src)
    pkg = src_dir.name
    expected = {
        p.relative_to(src_dir).as_posix(): digest(p.read_bytes())
        for p in src_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    with zipfile.ZipFile(wheel) as zf:
        shipped = {
            name[len(pkg) + 1:]: digest(zf.read(name))
            for name in zf.namelist()
            if name.startswith(pkg + "/") and not name.endswith("/")
        }
    missing = sorted(set(expected) - set(shipped))
    extra = sorted(set(shipped) - set(expected))
    changed = sorted(k for k in expected if k in shipped and expected[k] != shipped[k])
    print(f"{wheel}: {len(shipped)} files under {pkg}/, {len(expected)} in {src}")
    for label, items in (("missing from wheel", missing), ("not in src", extra), ("content differs", changed)):
        if items:
            print(f"  {label}: {', '.join(items)}")
    if missing or extra or changed:
        return 1
    print("  wheel matches src")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
