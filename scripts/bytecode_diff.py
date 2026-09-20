"""Compare everything that determines behaviour in two source trees.

For a release that claims to change only documentation, this is the check
that the claim is true.  Every ``.py`` file under each tree is parsed,
stripped of docstrings (module, class, function and nested-function
docstrings alike), compiled, and the whole resulting code-object tree is
fingerprinted - ``co_code``, constants (recursively, so every nested
function, closure, lambda and comprehension is included), names, variable,
free and cell variables, argument counts - without line numbers.  Starting
from the whole module and subtracting only docstrings, comments, blank lines
and line numbers is what makes the claim "nothing that determines behaviour
differs" checkable: module-level statements (``warnings.simplefilter``,
``np.seterr``), keyword defaults, module constants, ``__all__``, error
strings, annotations and closures are all inside the module's code object,
so none of them can be missed by omission.  The 0.1.18 and 0.1.19 versions
of this script fingerprinted functions and then constants by enumeration,
and each missed the next kind of change.

The one thing masked on purpose is the value assigned to ``__version__``,
which changes in every release by definition.  Nothing is imported, so the
script needs neither NumPy nor the package's dependencies, and both trees are
compiled by the interpreter that runs it.

    python scripts/bytecode_diff.py /path/to/old/src /path/to/new/src
    python scripts/bytecode_diff.py --self-test src

Exit status: 0 when nothing differs, 1 when something does (or the
self-test fails), 2 on a usage or parse error from either entry point (a
missing or unparsable tree, a missing ``fissionkit/`` package under the
``--self-test`` argument; a tree that cannot be parsed
is not "different", it is unusable, and a CI step must be able to tell the
two apart).  Note that the order of statements is part of the fingerprint:
swapping two independent statements is reported as a change even when it
cannot alter behaviour - for a documentation-only claim that is the safe
direction of error.  ``--self-test`` applies
fourteen mutations to a scratch copy of the tree - nine that must be detected
(module-level statement, closure body, error string, module constant, module
tuple, keyword default, ``__all__`` entry, comparison operator, annotation)
and five that must not (module, function and closure docstrings, a comment,
blank lines) - and checks each verdict.
"""
import ast
import hashlib
import pathlib
import shutil
import sys
import tempfile
import types

_DEF_NODES = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
USAGE_ERROR = 2   # usage or parse error; 1 is reserved for "something differs"


def _normalise(tree: ast.AST) -> ast.AST:
    """Remove docstrings everywhere and mask the ``__version__`` string."""
    for node in ast.walk(tree):
        if isinstance(node, _DEF_NODES) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "__version__"
                and isinstance(node.value, ast.Constant)):
            node.value = ast.Constant("<masked>")
    return ast.fix_missing_locations(tree)


def _code_fp(c: types.CodeType) -> str:
    consts = tuple(_code_fp(k) if isinstance(k, types.CodeType) else repr(k) for k in c.co_consts)
    return repr((c.co_code, consts, c.co_names, c.co_varnames, c.co_freevars, c.co_cellvars,
                 c.co_argcount, c.co_kwonlyargcount, c.co_posonlyargcount))


def _module_fingerprints(path: pathlib.Path) -> dict:
    """Fingerprint of the module body plus one per top-level function/class."""
    tree = _normalise(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    code = compile(tree, str(path.name), "exec")
    nested = {k.co_name: k for k in code.co_consts if isinstance(k, types.CodeType)}
    out = {name: hashlib.sha256(_code_fp(k).encode()).hexdigest() for name, k in nested.items()}
    # the module body with its nested code objects replaced by their names
    body = repr((code.co_code, tuple(f"<code:{k.co_name}>" if isinstance(k, types.CodeType)
                                    else repr(k) for k in code.co_consts), code.co_names))
    out["<module body>"] = hashlib.sha256(body.encode()).hexdigest()
    return out


def fingerprints(src: str) -> dict:
    root = pathlib.Path(src)
    if not root.is_dir():
        print(f"not a directory: {src}", file=sys.stderr)
        sys.exit(USAGE_ERROR)
    out = {}
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        try:
            mod = _module_fingerprints(p)
        except SyntaxError as exc:
            print(f"could not parse {p}: {exc}", file=sys.stderr)
            sys.exit(USAGE_ERROR)
        for k, v in mod.items():
            out[f"{p.relative_to(root).as_posix()}::{k}"] = v
    return out


def compare(old: str, new: str, quiet: bool = False) -> list:
    a, b = fingerprints(old), fingerprints(new)
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    changed = sorted(k for k in a if k in b and a[k] != b[k])
    if not quiet:
        print(f"items fingerprinted: {len(a)} in {old}, {len(b)} in {new}")
        for label, items in (("added", added), ("removed", removed), ("changed", changed)):
            if items:
                print(f"  {label}: {', '.join(items)}")
        if not (added or removed or changed):
            print("  nothing that determines behaviour differs (docstrings, comments and line numbers excluded)")
    return added + removed + changed


# (label, file under src/fissionkit, old text, new text, must be detected)
_MUTATIONS = [
    ("module-level statement", "thinning.py", "SUPPORTED_FAMILIES = (",
     'import warnings\nwarnings.simplefilter("ignore")\nSUPPORTED_FAMILIES = (', True),
    ("closure body", "recipes/cluster_validation.py", "n_init=10", "n_init=5", True),
    ("error string", "thinning.py", '"epsilon must sum to one"', '"epsilon must sum to 1"', True),
    ("module constant", "recipes/model_selection.py", "MIN_DOF_ESTIMATED = 20", "MIN_DOF_ESTIMATED = 30", True),
    ("module tuple", "recipes/cluster_validation.py",
     '_COUNT_FAMILIES = ("poisson", "negative_binomial")', '_COUNT_FAMILIES = ("poisson",)', True),
    ("keyword default", "recipes/model_selection.py", "epsilon: float = 0.8,", "epsilon: float = 0.7,", True),
    ("__all__ entry", "__init__.py", '    "kruskal_test",\n', "", True),
    ("comparison operator", "fission.py", "tau <= 0", "tau < 0", True),
    ("annotation", "thinning.py", "K: Optional[int] = None,", "K: int = None,", True),
    ("module docstring", "thinning.py", "Data thinning for convolution-closed distributions.",
     "Data thinning for convolution-closed distributions (edited).", False),
    ("function docstring", "thinning.py", "Split ``X`` into independent folds by data thinning.",
     "Split ``X`` into independent folds by data thinning (edited).", False),
    ("closure docstring added", "recipes/cluster_validation.py", "    def _cluster(M):\n",
     '    def _cluster(M):\n        """Cluster the training fold."""\n', False),
    ("comment", "thinning.py", "# ----------------------------------------------------------------- families",
     "# families", False),
    ("blank lines", "fission.py", "def _rng(random_state):\n", "\n\ndef _rng(random_state):\n", False),
]


def self_test(src: str) -> int:
    if not (pathlib.Path(src) / "fissionkit").is_dir():
        print(f"not a source tree (no fissionkit/ package inside): {src}", file=sys.stderr)
        sys.exit(USAGE_ERROR)
    failures = 0
    for label, rel, old, new, expect in _MUTATIONS:
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "src"
            shutil.copytree(src, copy, ignore=shutil.ignore_patterns("__pycache__"))
            target = copy / "fissionkit" / rel
            text = target.read_text(encoding="utf-8")
            if old not in text:
                print(f"  {label:<24s} SKIP (pattern not found in {rel}) - update _MUTATIONS")
                failures += 1
                continue
            target.write_text(text.replace(old, new, 1), encoding="utf-8")
            detected = bool(compare(src, str(copy), quiet=True))
            ok = detected == expect
            failures += not ok
            print(f"  {label:<24s} {'detected' if detected else 'not detected':<13s} "
                  f"{'as expected' if ok else 'WRONG (expected ' + ('detection' if expect else 'silence') + ')'}")
    print("self-test passed" if not failures else f"self-test FAILED ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        sys.exit(self_test(sys.argv[2]))
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(USAGE_ERROR)
    sys.exit(1 if compare(sys.argv[1], sys.argv[2]) else 0)
