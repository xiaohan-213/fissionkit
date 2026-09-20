"""Fill every submission placeholder from one JSON file, or list what is left.

The same facts - authors, affiliations, e-mail, repository URL, support
address, PyPI link, DOI, CRediT roles, declarations - are needed in five
places that are easy to leave inconsistent: ``pyproject.toml``, ``LICENSE``,
``CITATION.cff``, ``README.md`` and the manuscript ``.docx``.  This script
writes them all from one source of truth and then re-checks that nothing is
left.

    python scripts/fill_placeholders.py --check
    python scripts/fill_placeholders.py --apply paper/submission.json
    python scripts/fill_placeholders.py --self-test

``paper/submission.example.json`` documents every field.  The manuscript is
edited in place at the level of whole text runs, so its formatting is
untouched.  After writing, ``--apply`` validates every file it touched -
``pyproject.toml`` is parsed as TOML, ``CITATION.cff`` is checked with
``cffconvert`` or PyYAML when available and otherwise by a structural scan,
``word/document.xml`` must still be well-formed XML - and then re-runs
``--check``.  The 0.1.23 version wrote YAML scalars unquoted, so an
affiliation containing ": " produced an invalid CITATION.cff while the
script reported success; every value is now written as a double-quoted
scalar (JSON string syntax, valid YAML for any content).

The example file itself is refused: a ``_comment`` key, an ``example.org`` /
``example-org`` address, the placeholder Zenodo DOI or an all-zero ORCID
anywhere in the submission exits 2 - the example values are
self-consistent, so nothing downstream would notice them.

``--self-test`` first checks that nine malformed submissions are rejected
before anything is written (the example file verbatim, corresponding author
without e-mail, a control character in a value, no corresponding author,
``"corresponding": "no"``, an ORCID given as a number, a null declaration,
``authors`` not a list, one example e-mail left in), then applies eleven
submissions to a scratch copy of the repository - backslashes and ``\1`` in
a name, an affiliation and the copyright line (the values cross four
syntaxes: TOML string, YAML scalar, XML text and, until 0.1.24, a ``re.sub``
replacement string that re-interpreted them), ORCID and DOI given as URLs,
single author without DOI or ORCID, three authors sharing an affiliation,
names and affiliations with ``: & < > " '`` and non-ASCII letters, two
corresponding authors, a repository URL with a trailing slash, values with
surrounding whitespace, an affiliation spelled two ways (one number), an
address at ``goodexample.com`` (not a marker), and a second ``--apply`` on an
already filled tree -
and checks the outputs, including the semantic assertion that only authors
flagged ``true`` appear in the corresponding-author line.

Exit status: 0 when no placeholder remains and every written file
validates, 1 when placeholders remain or a written file is invalid (or the
self-test fails), 2 on a usage error - including a submission file that is
missing, unreadable, not valid JSON, malformed, or still the example.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCX = ROOT / "paper" / "fissionkit_SoftwareX_manuscript.docx"
REPO_PLACEHOLDER = "https://github.com/USER/fissionkit"
SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹"
USAGE_ERROR = 2


def _sup(n: int) -> str:
    return "".join(SUPERSCRIPT[int(d)] for d in str(n))


def _version() -> str:
    text = (ROOT / "src" / "fissionkit" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', text).group(1)


# ---------------------------------------------------------------- checking
_PATTERNS = {
    "pyproject.toml": [r"TO BE COMPLETED", r"to-be-completed@", re.escape(REPO_PLACEHOLDER)],
    "LICENSE": [r"(?i)to be completed"],
    "CITATION.cff": [r"to be completed", re.escape(REPO_PLACEHOLDER)],
    "README.md": [re.escape(REPO_PLACEHOLDER)],
}
_DOCX_MARK = "to be completed before submission"


def check(verbose: bool = True) -> int:
    left = 0
    for rel, pats in _PATTERNS.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for pat in pats:
            for m in re.finditer(pat, text):
                left += 1
                if verbose:
                    line = text[: m.start()].count("\n") + 1
                    print(f"  {rel}:{line}: {m.group(0)}")
    with zipfile.ZipFile(DOCX) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    for m in re.finditer(r"<w:t[^>]*>([^<]*" + re.escape(_DOCX_MARK) + r"[^<]*)</w:t>", xml):
        left += 1
        if verbose:
            print(f"  {DOCX.relative_to(ROOT)}: {m.group(1)[:90]}")
    if verbose:
        print("no placeholder remains" if not left else f"{left} placeholder(s) remain")
    return left


# ---------------------------------------------------------------- applying
def _load(path: str) -> dict:
    try:
        cfg = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"cannot read submission file: {exc}", file=sys.stderr)
        sys.exit(USAGE_ERROR)
    except json.JSONDecodeError as exc:
        print(f"submission file is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(USAGE_ERROR)
    if not isinstance(cfg, dict):
        print("submission file must contain a JSON object", file=sys.stderr)
        sys.exit(USAGE_ERROR)
    # A1: the example file, or values copied from it, must never reach the
    # manuscript, pyproject.toml or CITATION.cff.  Every check downstream
    # would pass - the example is self-consistent - and the fictitious
    # authors would only be noticed on PyPI or Zenodo.
    if "_comment" in cfg:
        print("this is the example file (it has a '_comment' key): copy it to paper/submission.json, "
              "remove the comment and fill in the real values", file=sys.stderr)
        sys.exit(USAGE_ERROR)
    example_markers = _find_example_markers(cfg)
    if example_markers:
        print("example values must be replaced before applying: " + "; ".join(example_markers), file=sys.stderr)
        sys.exit(USAGE_ERROR)

    def fail(msg):
        print(msg, file=sys.stderr)
        sys.exit(USAGE_ERROR)

    # Types are checked, not only presence: JSON "no" is a truthy string, and
    # 0.1.25 marked an author with "corresponding": "no" as corresponding.
    def text(obj, key, where, optional=False):
        if key not in obj:
            if optional:
                return None
            fail(f"{where} lacks '{key}'")
        v = obj[key]
        if not isinstance(v, str):
            fail(f"{where}.{key} must be a string, got {type(v).__name__}")
        v = v.strip()  # a value's own leading/trailing space would be dropped by Word at a run's edge and kept mid-line
        if not v and not optional:
            fail(f"{where}.{key} is empty")
        obj[key] = v
        return v

    for k in ("copyright_holder", "repository", "support_email", "pypi_url",
              "competing_interests", "funding", "ai_statement"):
        text(cfg, k, "submission")
    text(cfg, "zenodo_doi", "submission", optional=True)
    if not isinstance(cfg.get("authors"), list) or not cfg["authors"]:
        fail("submission.authors must be a non-empty list of author objects")
    for i, a in enumerate(cfg["authors"]):
        where = f"submission.authors[{i}]"
        if not isinstance(a, dict):
            fail(f"{where} must be an object, got {type(a).__name__}")
        for k in ("given", "family", "affiliation", "credit"):
            text(a, k, where)
        for k in ("email", "orcid"):
            text(a, k, where, optional=True)
        if "corresponding" in a and not isinstance(a["corresponding"], bool):
            fail(f"{where}.corresponding must be JSON true or false, got {a['corresponding']!r}")
    if not any(a.get("corresponding") for a in cfg["authors"]):
        print("no author is marked corresponding", file=sys.stderr)
        sys.exit(USAGE_ERROR)
    for a in cfg["authors"]:
        if a.get("corresponding") and not a.get("email"):
            print(f"corresponding author {a['given']} {a['family']} has no email", file=sys.stderr)
            sys.exit(USAGE_ERROR)
        if a.get("orcid"):  # accept the bare identifier or the full URL
            a["orcid"] = re.sub(r"^https?://orcid\.org/", "", a["orcid"].strip())
    if cfg.get("zenodo_doi"):
        cfg["zenodo_doi"] = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", cfg["zenodo_doi"].strip())
    cfg["repository"] = cfg["repository"].rstrip("/")
    # control characters cannot be carried into a TOML basic string, a Word
    # text run or an author line; reject them rather than write them
    def scan(value, where):
        if isinstance(value, str) and re.search(r"[\x00-\x1f\x7f]", value):
            print(f"control character in {where}: {value!r}", file=sys.stderr)
            sys.exit(USAGE_ERROR)
        if isinstance(value, dict):
            for k, v in value.items():
                scan(v, f"{where}.{k}")
        if isinstance(value, list):
            for i, v in enumerate(value):
                scan(v, f"{where}[{i}]")
    scan({k: v for k, v in cfg.items() if not k.startswith("_")}, "submission")
    return cfg


_EXAMPLE_PATTERNS = [
    (re.compile(r"(?<![\w-])example\.(org|com|net)\b|(?<![\w-])example-org\b", re.IGNORECASE), "example.org / example-org address"),
    (re.compile(r"zenodo\.0{6,}"), "placeholder Zenodo DOI"),
    (re.compile(r"\b0000-0000-0000-0000\b"), "all-zero ORCID"),
]


def _find_example_markers(obj, where="submission") -> list:
    found = []
    if isinstance(obj, str):
        for pat, label in _EXAMPLE_PATTERNS:
            if pat.search(obj):
                found.append(f"{where} ({label})")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            found += _find_example_markers(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += _find_example_markers(v, f"{where}[{i}]")
    return found


def _toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _apply_pyproject(cfg):
    p = ROOT / "pyproject.toml"
    s = p.read_text(encoding="utf-8")
    entries = []
    for a in cfg["authors"]:
        name = _toml_str(f"{a['given']} {a['family']}")
        entries.append(f"{{name = {name}, email = {_toml_str(a['email'])}}}" if a.get("email") else f"{{name = {name}}}")
    authors = ", ".join(entries)
    # A callable replacement: a replacement *string* would re-interpret the
    # backslashes _toml_str just escaped (0.1.24 wrote "O\Neil" from O\Neil).
    s = re.sub(r"^authors = \[.*?\]$", lambda m: f"authors = [{authors}]", s, count=1, flags=re.MULTILINE | re.DOTALL)
    s = s.replace(REPO_PLACEHOLDER, cfg["repository"])
    p.write_text(s, encoding="utf-8")


def _apply_license(cfg):
    p = ROOT / "LICENSE"
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"\[AUTHORS[^\]]*\]", lambda m: cfg["copyright_holder"], s, count=1)
    p.write_text(s, encoding="utf-8")


def _yaml_str(value: str) -> str:
    """A YAML double-quoted scalar: JSON string syntax is valid YAML for any content."""
    return json.dumps(value, ensure_ascii=False)


def _apply_citation(cfg):
    p = ROOT / "CITATION.cff"
    s = p.read_text(encoding="utf-8")
    block = "authors:\n" + "".join(
        f"  - family-names: {_yaml_str(a['family'])}\n    given-names: {_yaml_str(a['given'])}\n"
        + (f"    affiliation: {_yaml_str(a['affiliation'])}\n" if a.get("affiliation") else "")
        + (f"    orcid: {_yaml_str('https://orcid.org/' + a['orcid'])}\n" if a.get("orcid") else "")
        for a in cfg["authors"])
    s = re.sub(r"^authors:\n(?:  .*\n)+", lambda m: block, s, count=1, flags=re.MULTILINE)
    s = s.replace(REPO_PLACEHOLDER, cfg["repository"])
    if cfg.get("zenodo_doi") and "doi:" not in s:
        s = s.replace("repository-code:", f"doi: {_yaml_str(cfg['zenodo_doi'])}\nrepository-code:", 1)
    p.write_text(s, encoding="utf-8")


def _apply_readme(cfg):
    p = ROOT / "README.md"
    p.write_text(p.read_text(encoding="utf-8").replace(REPO_PLACEHOLDER, cfg["repository"]), encoding="utf-8")


def _docx_texts(cfg) -> dict:
    """Placeholder run text (prefix) -> replacement text."""
    def key(aff):  # spelling variants of one affiliation get one number
        return re.sub(r"\s+", " ", aff).casefold()

    affs, keys = [], []
    for a in cfg["authors"]:
        if key(a["affiliation"]) not in keys:
            affs.append(a["affiliation"])
            keys.append(key(a["affiliation"]))
        elif a["affiliation"] != affs[keys.index(key(a["affiliation"]))]:
            print(f"note: affiliation {a['affiliation']!r} treated as {affs[keys.index(key(a['affiliation']))]!r}")
    author_line = ", ".join(
        f"{a['given']} {a['family']}{_sup(keys.index(key(a['affiliation'])) + 1)}{'˙*' if a.get('corresponding') else ''}"
        for a in cfg["authors"])
    aff_line = "; ".join(f"{_sup(i + 1)} {aff}" for i, aff in enumerate(affs))
    corr = [a for a in cfg["authors"] if a.get("corresponding")]
    version = _version()
    c2 = f"{cfg['repository']}/tree/v{version}"
    if cfg.get("zenodo_doi"):
        c2 += f" (archived: https://doi.org/{cfg['zenodo_doi']})"
    credit = " ".join(f"{a['given']} {a['family']}: {a['credit']}." for a in cfg["authors"])
    return {
        "[Author A]¹˙*, [Author B]²": author_line,
        "¹ [Department], [University / Organization], [City], [Country];": aff_line,
        "* Corresponding author. E-mail: [email address]":
            f"* Corresponding author{'s' if len(corr) > 1 else ''}. E-mail: {', '.join(a['email'] for a in corr)}",
        "[https://github.com/USER/fissionkit/tree/v": c2,
        "[support email – to be provided]": cfg["support_email"],
        "[https://pypi.org/project/fissionkit/": cfg["pypi_url"],
        "[Author A]: Conceptualization": credit,
        "[Declare all financial and non-financial competing interests.": cfg["competing_interests"],
        "[No external funding was received for this work.": cfg["funding"],
        "[To be completed truthfully by the authors": cfg["ai_statement"],
    }


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _apply_docx(cfg):
    with zipfile.ZipFile(DOCX) as zf:
        entries = [(i, zf.read(i.filename)) for i in zf.infolist()]
    items = {i.filename: (i, data) for i, data in entries}
    xml = items["word/document.xml"][1].decode("utf-8")
    if _DOCX_MARK not in xml:
        print("manuscript: already filled (no placeholder runs), left unchanged")
        return 0
    replaced = 0
    for prefix, new in _docx_texts(cfg).items():
        pat = re.compile(r"(<w:t[^>]*>)" + re.escape(prefix) + r"[^<]*" + re.escape(_DOCX_MARK) + r"[^<]*(</w:t>)")
        escaped = _xml_escape(new)
        xml, n = pat.subn(lambda m, rep=escaped: m.group(1) + rep + m.group(2), xml)
        replaced += n
        if n == 0:
            print(f"  warning: manuscript placeholder not found: {prefix[:50]!r}", file=sys.stderr)
    tmp = DOCX.with_suffix(".docx.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for info, data in entries:  # keep the original entry order
            if info.filename == "word/document.xml":
                data = xml.encode("utf-8")
            out.writestr(info, data)
    tmp.replace(DOCX)
    return replaced


# ---------------------------------------------------------------- validation
def _validate_toml() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return "skipped (no TOML parser on this interpreter)"
    tomllib.loads(text)
    return "parsed"


def _validate_cff() -> str:
    path = ROOT / "CITATION.cff"
    if shutil.which("cffconvert"):
        r = subprocess.run(["cffconvert", "--validate", "-i", str(path)], capture_output=True, text=True, check=False)
        if r.returncode != 0:
            raise ValueError((r.stderr or r.stdout).strip().splitlines()[-1])
        return "cffconvert"
    try:
        import yaml  # type: ignore[import-untyped]
        yaml.safe_load(path.read_text(encoding="utf-8"))
        return "PyYAML"
    except ImportError:
        pass
    # structural scan: every author field must be a double-quoted scalar
    block = re.search(r"^authors:\n((?:  .*\n)+)", path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    if not block:
        raise ValueError("no authors block")
    for line in block.group(1).splitlines():
        m = re.match(r"^\s*(?:- )?([a-z-]+): (.*)$", line)
        if not m or not (m.group(2).startswith('"') and m.group(2).endswith('"')):
            raise ValueError(f"unquoted or malformed author field: {line.strip()}")
    return "structural scan"


def _validate_docx() -> str:
    with zipfile.ZipFile(DOCX) as zf:
        ET.fromstring(zf.read("word/document.xml"))  # well-formed XML
    return "well-formed"


def _validate_all() -> int:
    failures = 0
    for name, fn in (("pyproject.toml", _validate_toml), ("CITATION.cff", _validate_cff), ("manuscript", _validate_docx)):
        try:
            print(f"  {name}: {fn()}")
        except (ValueError, ET.ParseError, zipfile.BadZipFile, OSError) as exc:  # TOML parsers raise ValueError subclasses
            print(f"  {name}: INVALID - {exc}", file=sys.stderr)
            failures += 1
    return failures


def apply(path: str) -> int:
    cfg = _load(path)
    _apply_pyproject(cfg)
    _apply_license(cfg)
    _apply_citation(cfg)
    _apply_readme(cfg)
    n = _apply_docx(cfg)
    print(f"manuscript: {n} placeholder run(s) replaced; repository metadata rewritten")
    invalid = _validate_all()
    return check() + invalid


# ---------------------------------------------------------------- self-test
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx_paragraphs(docx: pathlib.Path) -> list:
    with zipfile.ZipFile(docx) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    return ["".join(t.text or "" for t in p.iter(f"{_W}t")) for p in root.iter(f"{_W}p")]


def _variants(example: dict) -> list:
    def v(name, mutate):
        cfg = json.loads(json.dumps(example))
        mutate(cfg)
        return name, cfg

    def special(c):
        c["authors"][0].update({"given": "Zoë", "family": "Müller-O'Brien",
                                "affiliation": "Institute of Physics: Theory & Computation, <Example> University, City, Country"})
        c["copyright_holder"] = 'Zoë Müller-O\'Brien & "Bob" Babbage'
        c["funding"] = "Grant <A&B> 42: *none*"

    def backslashes(c):  # every syntax boundary at once: TOML, YAML, XML text, re.sub replacement
        c["authors"][0]["family"] = "O\\Neil"
        c["authors"][0]["affiliation"] = "Dept \\1 of \\g<0> Sciences, Example University, City, Country"
        c["copyright_holder"] = "O\\Neil \\1 and Babbage"

    return [
        v("domain ending in 'example.com' (not an example marker)", lambda c: c["authors"][1].__setitem__("email", "bob@goodexample.com")),
        v("affiliation spelled two ways", lambda c: c["authors"].append(
            {"given": "Carla", "family": "Chen", "affiliation": c["authors"][0]["affiliation"].upper(),
             "email": "carla@stats.uni.invalid", "corresponding": False, "credit": "Data curation"})),
        v("surrounding whitespace in values", lambda c: (c["authors"][0].__setitem__("affiliation", "  " + c["authors"][0]["affiliation"] + "  "),
                                                        c.__setitem__("support_email", " " + c["support_email"] + " "))),
        v("backslashes and \\1 in name, affiliation, copyright", backslashes),
        v("ORCID and DOI given as URLs", lambda c: (c["authors"][0].__setitem__("orcid", "https://orcid.org/" + c["authors"][0]["orcid"]),
                                                   c.__setitem__("zenodo_doi", "https://doi.org/" + c["zenodo_doi"]))),
        v("single author, no DOI, no ORCID", lambda c: (c["authors"].__setitem__(slice(None), c["authors"][:1]),
                                                       c["authors"][0].pop("orcid"), c.pop("zenodo_doi"))),
        v("three authors, shared affiliation", lambda c: c["authors"].append(
            {"given": "Carla", "family": "Chen", "affiliation": c["authors"][0]["affiliation"],
             "email": "carla@stats.uni.invalid", "corresponding": False, "credit": "Data curation"})),
        v("special characters", special),
        v("two corresponding authors", lambda c: c["authors"][1].__setitem__("corresponding", True)),
        v("trailing slash in repository", lambda c: c.__setitem__("repository", c["repository"] + "/")),
    ]


_REJECTED = [  # (label, mutate) -> --apply must exit USAGE_ERROR without writing
    ("corresponding author without e-mail", lambda c: c["authors"][0].pop("email")),
    ("control character in an affiliation", lambda c: c["authors"][0].__setitem__("affiliation", "Dept,\nUniversity")),
    ("no corresponding author", lambda c: [a.__setitem__("corresponding", False) for a in c["authors"]]),
    ("corresponding given as the string 'no'", lambda c: c["authors"][1].__setitem__("corresponding", "no")),
    ("orcid given as a number", lambda c: c["authors"][0].__setitem__("orcid", 1234)),
    ("funding given as null", lambda c: c.__setitem__("funding", None)),
    ("authors given as an object", lambda c: c.__setitem__("authors", {"given": "A"})),
    ("one example e-mail left in", lambda c: c["authors"][1].__setitem__("email", "bob@example.org")),
]


def _realistic(example: dict) -> dict:
    """The example file with its example markers replaced, so that the
    self-test exercises the writers rather than the example guard."""
    text = json.dumps({k: v for k, v in example.items() if k != "_comment"})
    for old, new in (("example.org", "stats.uni.invalid"), ("example-org", "uni-stats"),
                     ("zenodo.0000000", "zenodo.1234567"), ("0000-0000-0000-0000", "0000-0002-1825-0097")):
        text = text.replace(old, new)
    return json.loads(text)


def self_test() -> int:
    raw = json.loads((ROOT / "paper" / "submission.example.json").read_text(encoding="utf-8"))
    example = _realistic(raw)
    failures = 0
    rejected = [("the example file, verbatim", None)] + _REJECTED
    for label, mutate in rejected:
        cfg = json.loads(json.dumps(raw if mutate is None else example))
        if mutate is not None:
            mutate(cfg)
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "dist", "build", "*.egg-info"))
            sub = copy / "paper" / "submission.json"
            sub.write_text(json.dumps(cfg), encoding="utf-8")
            r = subprocess.run([sys.executable, str(copy / "scripts" / "fill_placeholders.py"), "--apply", str(sub)],
                               capture_output=True, text=True, check=False)
            untouched = (copy / "LICENSE").read_text(encoding="utf-8") == (ROOT / "LICENSE").read_text(encoding="utf-8")
            ok = r.returncode == USAGE_ERROR and "Traceback" not in r.stderr and untouched
            failures += not ok
            print(f"  {label:<36s} {'rejected (exit 2, nothing written)' if ok else 'FAILED: exit ' + str(r.returncode)}")
    # Once a repository has been populated for release, the manuscript no longer
    # contains the original author/affiliation placeholder runs.  The writer
    # variants below intentionally exercise those template runs, so they are
    # meaningful only on an unfilled submission template.  Keep the rejection
    # tests above active in a populated release tree, but do not report false
    # failures merely because real author metadata is already present.
    current_text = "\n".join(_docx_paragraphs(ROOT / "paper" / "fissionkit_SoftwareX_manuscript.docx"))
    if "[Author A]" not in current_text:
        print("  writer variants skipped: manuscript author metadata is already populated")
        print("self-test " + ("FAILED" if failures else "ok") + (f" ({failures})" if failures else ""))
        return 1 if failures else 0

    for name, cfg in _variants(example) + [("second apply on a filled tree", None)]:
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "dist", "build", "*.egg-info"))
            sub = copy / "paper" / "submission.json"
            run = [sys.executable, str(copy / "scripts" / "fill_placeholders.py"), "--apply", str(sub)]
            if cfg is None:  # apply twice with the (de-exampled) example values
                sub.write_text(json.dumps(example), encoding="utf-8")
                subprocess.run(run, capture_output=True, text=True, check=False)
            else:
                sub.write_text(json.dumps(cfg), encoding="utf-8")
            r = subprocess.run(run, capture_output=True, text=True, check=False)
            problems = [] if r.returncode == 0 else [f"exit {r.returncode}: {(r.stderr or r.stdout).strip().splitlines()[-1][:80]}"]
            paras = _docx_paragraphs(copy / "paper" / "fissionkit_SoftwareX_manuscript.docx")
            text = "\n".join(paras)
            if cfg is not None:
                corr = [a for a in cfg["authors"] if a.get("corresponding") is True]
                corr_line = next((p for p in paras if p.startswith("* Corresponding author")), "")
                if not all(a["email"].strip() in corr_line for a in corr):
                    problems.append("a corresponding e-mail is missing from the manuscript")
                # semantic, not syntactic: a non-corresponding author's e-mail must not be listed
                if any(a.get("email") and a["email"].strip() in corr_line for a in cfg["authors"] if a not in corr):
                    problems.append("a non-corresponding author is listed as corresponding")
                if any(p.startswith("¹  ") or "  ;" in p for p in paras):
                    problems.append("surrounding whitespace leaked into the manuscript")
                distinct = {re.sub(r"\s+", " ", a["affiliation"]).casefold() for a in cfg["authors"]}
                aff_line = next((p for p in paras if p.startswith("¹ ")), "")
                if aff_line.count(";") + 1 != len(distinct):
                    problems.append("affiliation count does not match the distinct affiliations")
                if "//tree/" in text:
                    problems.append("double slash in the repository link")
                if "&amp;" in text or "&lt;" in text:
                    problems.append("XML escapes leaked into the text")
                norm = lambda x: re.sub(r"\s+", " ", x.strip()).casefold()  # load strips; spelling variants merge
                for a in cfg["authors"]:
                    if a["family"].strip() not in text or norm(a["affiliation"]) not in norm(text):
                        problems.append(f"author {a['family']} or affiliation missing from the manuscript")
                cff = (copy / "CITATION.cff").read_text(encoding="utf-8")
                if "orcid.org/https" in cff or "doi.org/https" in text:
                    problems.append("doubled ORCID or DOI prefix")
                lic = (copy / "LICENSE").read_text(encoding="utf-8")
                if cfg["copyright_holder"] not in lic:
                    problems.append("copyright holder not written verbatim to LICENSE")
            if "warning" in r.stderr:
                problems.append("warnings on stderr")
            failures += bool(problems)
            print(f"  {name:<36s} {'ok' if not problems else 'FAILED: ' + '; '.join(problems)}")
    print("self-test passed" if not failures else f"self-test FAILED ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        sys.exit(1 if check() else 0)
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    if len(sys.argv) == 3 and sys.argv[1] == "--apply":
        sys.exit(1 if apply(sys.argv[2]) else 0)
    print(__doc__, file=sys.stderr)
    sys.exit(USAGE_ERROR)
