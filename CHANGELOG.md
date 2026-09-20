# Changelog

All notable changes to fissionkit are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/1.1.0/);
this project uses [Semantic Versioning](https://semver.org/).

Entries describe user-visible behaviour: what changed, whether existing code
or seeded results are affected, and what to do about it.

## [0.2.0] — 2026-09-20

First public release. No changes to the package outside the version string;
`scripts/bytecode_diff.py` reports nothing that determines behaviour differs
from 0.1.29.

The 0.1.x entries below record the pre-release audit rounds, most of them
dated the same day. None of them was tagged in this repository or published
to PyPI; they are kept as a record of what was checked and fixed before
publication. 0.2.0 is the first version intended for users.

## [0.1.29] — 2026-09-11

Release-tooling fix. No changes to the package outside the version string;
`scripts/bytecode_diff.py` reports nothing that determines behaviour differs
from 0.1.28.

### Fixed
- **`scripts/release.sh` refused every released archive from the next UTC
  day on.** The date check added in 0.1.28 compared `CITATION.cff` and the
  top `CHANGELOG.md` entry to today in every run, so the script that
  verifies a release stopped accepting that release once its day had
  passed - anyone checking out a tag to verify it, as CONTRIBUTING says
  to, would have been refused with no legitimate way through. The script
  now has two modes. Cutting (HEAD not tagged `v<version>`): both files
  must carry today's UTC date. Verifying (HEAD tagged `v<version>`, or
  `--verify`): the two files must agree with each other and with the
  package version; their date is the release date. With a fake `date`
  returning tomorrow, an untagged tree is refused and a tagged one passes.

### Added
- `CONTRIBUTING.md`: the release script's two modes, and a rule in the
  verification discipline - a check that compares to "now" must be probed
  with a fake tomorrow against a released tree.

## [0.1.28] — 2026-09-11

Hand-off tooling polish. No changes to the package outside the version
string; `scripts/bytecode_diff.py` reports nothing that determines behaviour
differs from 0.1.27.

### Fixed
- The example-marker pattern in `scripts/fill_placeholders.py` had no leading
  word boundary, so any address at a domain *ending* in `example.com` /
  `.org` / `.net` (`ada@counterexample.net`) was refused as an example value.
  The pattern now requires the domain to start at `example.`; an address at
  `goodexample.com` is among the applied self-test submissions.

### Added
- `scripts/release.sh` refuses to release unless the top `CHANGELOG.md` entry
  names the package version and both that entry and `CITATION.cff`
  `date-released` carry today's **UTC** date. Dates in both files are UTC
  dates by convention from this entry on. The audit that asked for this
  check ran on 12 September local time while the build host stood at
  21:38 UTC on the 11th - the case that shows why the reference clock has
  to be named. The check therefore dates this entry 2026-09-11, like the
  seventeen before it, and refuses a 2026-09-12 entry until UTC midnight.

## [0.1.27] — 2026-09-11

Hand-off tooling fix. No changes to the package outside the version string;
`scripts/bytecode_diff.py` reports nothing that determines behaviour differs
from 0.1.26.

### Fixed
- **`scripts/fill_placeholders.py` accepted the example file as a real
  submission.** Running the documented command with
  `paper/submission.example.json` in place of `paper/submission.json` filled
  the manuscript, `pyproject.toml`, `CITATION.cff` and `LICENSE` with the
  fictitious example authors, repository and DOI, reported success, and
  passed every syntax and semantic check - the example is self-consistent.
  `--apply` now refuses a file with a `_comment` key and any value that
  still carries an example marker (`example.org` / `.com` / `.net`,
  `example-org`, the zero Zenodo DOI, the all-zero ORCID), naming the
  field. Neutralising the guard makes two self-test cases fail.
- A missing, unreadable or syntactically invalid submission file raised a
  traceback; each now exits 2 with the reason.
- Two spellings of one affiliation (case or spacing) were numbered
  separately; they are now one affiliation under the first spelling, with
  a note.

### Added
- `--self-test`: the example file verbatim and a single leftover example
  e-mail are among nine rejected submissions; an affiliation spelled two
  ways is among ten applied ones, asserting that the affiliation count
  matches the distinct affiliations. The self-test derives its applied
  submissions from the example with the markers replaced, so that it
  exercises the writers rather than the guard.

### Lesson recorded
- The input domain of a tool includes every command in its documentation
  run verbatim. The audit found this one by making the mistake itself.

## [0.1.26] — 2026-09-11

Hand-off tooling fix. No changes to the package outside the version string;
`scripts/bytecode_diff.py` reports nothing that determines behaviour differs
from 0.1.25.

### Fixed
- **`scripts/fill_placeholders.py` treated `"corresponding": "no"` as
  corresponding.** Fields were checked for presence, not type, and the flag
  was read for truth: any non-empty string counted. The author was marked
  with `*` and listed in the e-mail line, and the TOML, CFF and XML
  validators passed the result, as they must - the file was valid, the
  content was wrong. `_load` now checks types: `corresponding` must be a
  JSON boolean, `authors` a non-empty list of objects, every text field a
  string (optional ones may be absent), and it exits 2 naming the field.
  An ORCID given as a number, an e-mail given as a list and a null
  declaration, which raised `AttributeError`, are rejected the same way.
- String values are stripped on load. A value's own surrounding whitespace
  was written verbatim: kept mid-line (`¹   Example University  ;`) and, in
  a text run without `xml:space="preserve"`, dropped by Word at the run's
  edge - the same input rendered two ways.

### Added
- `--self-test` rejects seven malformed submissions (the three above plus
  the earlier ones) and applies nine, adding values with surrounding
  whitespace. The applied variants now include a *semantic* assertion -
  the corresponding-author line contains every author flagged `true` and
  no other author's e-mail - because that is the class of error syntax
  validation cannot see. Removing the boolean check or the strip makes the
  self-test fail.

### Lesson recorded
- A configuration file's input domain has three axes - content, form and
  type - and a syntax validator on the output is blind to the third. Each
  self-test needs at least one semantic assertion about what the output
  *says*, not only that it parses.

## [0.1.25] — 2026-09-11

Hand-off tooling fix. No changes to the package outside the version string;
`scripts/bytecode_diff.py` reports nothing that determines behaviour differs
from 0.1.24.

### Fixed
- **`scripts/fill_placeholders.py` corrupted values containing backslashes.**
  The escaped TOML string, the quoted YAML block and the copyright line were
  passed to `re.sub` as replacement *strings*, which re-interpret `\\` and
  `\1`; a family name `O\Neil` reached `pyproject.toml` as `"O\Neil"` (invalid
  TOML - caught by the 0.1.24 validation, so not shipped, but not handled
  either) and the copyright line would have been silently mangled (LICENSE
  has no validator). All three substitutions now use callable replacements,
  which insert text verbatim.
- A corresponding author without an e-mail raised `KeyError` (exit 1);
  `--apply` now rejects it at load (exit 2, naming the author).
- ORCID given as the full `https://orcid.org/…` URL was written with the
  prefix doubled and accepted (the CFF schema does not check ORCID format);
  a DOI given as `https://doi.org/…` produced an invalid CFF. Both prefixes
  (and `doi:`) are stripped on load.
- Control characters in any value are rejected at load (exit 2); a newline
  in a name would otherwise have produced an invalid TOML basic string.

### Added
- `--self-test` now starts with three malformed submissions that must be
  rejected before anything is written, and adds two applied variants: a
  name, an affiliation and a copyright line containing backslashes and
  `\1` / `\g<0>` (values that cross the TOML, YAML, XML-text and - until
  0.1.24 - `re.sub` boundaries), and ORCID/DOI given as URLs. Each applied
  variant also checks that the copyright holder reached LICENSE verbatim and
  that no identifier prefix was doubled. Reverting the three substitutions
  to 0.1.24's replacement strings makes the backslash variant fail.
- `CONTRIBUTING.md`: "Tools that write user data into another syntax" - one
  test case with metacharacters per syntax boundary, `re.sub` replacement
  strings named as the fourth.
  *Note added in 0.1.26:* this version checked presence but not type;
  `"corresponding": "no"` marked an author as corresponding. See 0.1.26.

## [0.1.24] — 2026-09-11

Hand-off tooling fix. No changes to the package outside the version string;
`scripts/bytecode_diff.py` reports nothing that determines behaviour differs
from 0.1.23.

### Fixed
- **`scripts/fill_placeholders.py` wrote an invalid `CITATION.cff` for an
  affiliation containing ": " and reported success.** YAML scalars were
  written unquoted; "Institute of Physics: Theory & Computation" became a
  nested mapping and `cffconvert --validate` rejected the file, while the
  script's own `--check` - which only looks for placeholders - printed "no
  placeholder remains" and exited 0. Every value written to the CFF file is
  now a double-quoted scalar (JSON string syntax, valid YAML for any
  content), and `--apply` validates every file it wrote before reporting:
  `pyproject.toml` is parsed as TOML, `CITATION.cff` is checked with
  `cffconvert` or PyYAML when available and otherwise by a structural scan
  that requires every author field to be quoted, and `word/document.xml`
  must be well-formed. An invalid file exits 1. Both the `cffconvert` path
  and the structural-scan path were shown to reject the 0.1.23 output.
- With two corresponding authors the manuscript marked both with `*` but
  listed only the first e-mail; all corresponding e-mails are now listed.
- A repository URL with a trailing slash produced `…/fissionkit//tree/v…`
  in Table 1 C2; the URL is normalised on load.
- A second `--apply` on an already filled tree printed ten "placeholder not
  found" warnings; it now reports once that the manuscript is already filled
  and leaves it unchanged.

### Added
- `fill_placeholders.py --self-test`: six submissions applied to a scratch
  copy - single author without DOI or ORCID, three authors sharing an
  affiliation, names and affiliations with `: & < > " '` and non-ASCII
  letters, two corresponding authors, a trailing-slash repository URL, and a
  second apply - checking exit status, every corresponding e-mail, the
  absence of a double slash, no leaked XML escapes and every author and
  affiliation in the manuscript. The CI lint job runs it (stdlib only).
  *Note added in 0.1.25:* this version passed user values as `re.sub`
  replacement strings, which re-interpret backslashes; see 0.1.25.

### Lesson recorded
- A tool that writes files must validate each file it wrote; "the
  placeholder is gone" is not "the file is valid". And its self-test must
  sample the input domain it claims to accept - here, arbitrary names and
  affiliations - not the author's own example values (the same lesson as
  0.1.19, in a second tool).

## [0.1.23] — 2026-09-11

Hand-off tooling. No changes to the package outside the version string;
`scripts/bytecode_diff.py` reports nothing that determines behaviour differs
from 0.1.22. This is the last tooling release before the author-owned steps.

### Added
- `scripts/fill_placeholders.py` and `paper/submission.example.json`: the
  facts every submission needs - authors, affiliations, e-mails, repository,
  support address, PyPI link, DOI, CRediT roles, the three declarations -
  are entered once in a JSON file and written to `pyproject.toml`,
  `LICENSE`, `CITATION.cff`, `README.md` and the manuscript in one pass; the
  manuscript is edited at the level of whole text runs so its formatting is
  untouched. `--check` lists every remaining placeholder in the five files
  (20 at present) and is run again after `--apply`. A missing field, a
  missing corresponding author or a usage error exits 2; remaining
  placeholders exit 1. Dry-run on a scratch copy with the example values
  leaves no placeholder and a manuscript that still validates. While
  writing it the `LICENSE` placeholder turned out to be lower-case and was
  missed by a case-sensitive check on the first attempt - the reason the
  script re-checks after applying rather than trusting its own edits.
  *Note added in 0.1.24:* this version wrote YAML scalars unquoted and did
  not validate the files it wrote; see 0.1.24.
- `paper/submission.json` is git-ignored; the example file is not.

## [0.1.22] — 2026-09-11

Hand-off polish. No changes to the package outside the version string;
`scripts/bytecode_diff.py` reports nothing that determines behaviour differs
from 0.1.21.

### Fixed
- `scripts/bytecode_diff.py --self-test` on a path that is not a source tree
  raised an uncaught `FileNotFoundError` (exit 1) instead of the documented
  usage error (exit 2); it now checks for a `fissionkit/` package under the
  argument first. The exit-code table in the docstring covers both entry
  points.
- The 0.1.21 changelog entry and the hand-off checklist counted the
  same-day patch releases ("ten") in the very release that made it eleven.
  Both now say "the same-day patch releases since 0.1.11" and leave the
  counting to the reader.

## [0.1.21] — 2026-09-11

Release-tooling polish and hand-off. No changes to the package outside the
version string; `scripts/bytecode_diff.py` reports nothing that determines
behaviour differs from 0.1.20.

### Changed
- `scripts/bytecode_diff.py` exits with status 2 on a usage or parse error
  and reserves 1 for "something differs", so a CI step can tell an unusable
  tree from a changed one (both were 1; an unterminated string in a scratch
  copy read as "detected" until stderr was consulted). The docstring states
  the three exit codes and that statement order is part of the fingerprint.

### Added
- `CONTRIBUTING.md`: "Before the first public tag" - the items only the
  authors can complete: placeholders, whether to squash the same-day patch
  releases since 0.1.11 into a `0.2.0` tag, reading the first macOS and
  Windows CI results, PyPI and Zenodo.

## [0.1.20] — 2026-09-11

Release-tooling rewrite. No changes to the package outside the version
string; the new tool reports nothing that determines behaviour differs from
0.1.19 (39 items).

### Changed
- **`scripts/bytecode_diff.py` fingerprints whole modules instead of
  enumerating parts.** Each `.py` file is parsed, stripped of every docstring
  (module, class, function, nested function), compiled, and the entire
  code-object tree is fingerprinted without line numbers, with the
  `__version__` string masked. Two consecutive versions of the tool had
  built the fingerprint by enumeration - first functions only (0.1.18), then
  functions, defaults and constants (0.1.19) - and each missed the next kind
  of change; the 0.1.19 version was silent on a module-level
  `warnings.simplefilter("ignore")`, which would disable the misspecified-
  scale diagnostic of `fission_lasso_inference`. Subtracting docstrings,
  comments and line numbers from the whole module leaves nothing to
  enumerate. The tool no longer imports the package and therefore needs no
  dependencies; the CI self-test step no longer installs any. Output names
  the file and the top-level function, class or module body that changed.
- The self-test now applies fourteen mutations: nine that must be detected
  (module-level statement, closure body, error string, module constant,
  module tuple, keyword default, `__all__` entry, comparison operator,
  annotation) and five that must not (module, function and closure
  docstrings, a comment, blank lines). Annotations count as behaviour: under
  `from __future__ import annotations` they are the strings the package
  exports to type checkers.

### Lesson recorded
- For a claim of the form "nothing that determines behaviour changed", build
  the check by subtraction from the whole (module code minus documentation),
  not by addition of parts - addition always has a next omission.

## [0.1.19] — 2026-09-11

Release-tooling fix. No changes to the package outside the version string;
`scripts/bytecode_diff.py` (this version) reports 42 fingerprinted items
identical to 0.1.18.

### Fixed
- **`scripts/bytecode_diff.py` missed keyword defaults and module constants.**
  The 0.1.18 version fingerprinted function code objects only; defaults
  live in `__defaults__` / `__kwdefaults__` and constants in the module
  namespace, so `MIN_DOF_ESTIMATED = 20 -> 30`, `_COUNT_FAMILIES` losing an
  entry, or `evaluate_denoisers(epsilon=0.8 -> 0.7)` all passed as "no
  function differs". The fingerprint now also covers function defaults,
  methods and literal class attributes, every literal module-level constant
  and `__all__` (`__version__` excluded by design). `--self-test src`
  applies six mutations to a scratch copy - the three above, a comparison
  operator, an `__all__` entry, and a docstring-only edit that must *not*
  be reported - and checks each verdict; the CI lint job runs it. Import
  failures in either tree are reported with the tree's path instead of a
  traceback. *Note added in 0.1.20:* this version still enumerated what to
  fingerprint (functions, then constants) and missed module-level statements
  such as `warnings.simplefilter("ignore")`; see 0.1.20.
- `scripts/check_wheel.py` documents that a file under `src/fissionkit`
  absent from the wheel fails the check on purpose.
- `CONTRIBUTING.md` describes what the tool actually checks.

### Lesson recorded
- A new tool's negative controls must cover what the tool is *claimed* to
  detect, not what it was written to detect; 0.1.18's two controls both
  exercised the implemented part.

## [0.1.18] — 2026-09-11

Release-tooling release. No changes to the package outside the version
string; signatures, function bytecode, random streams and seeded results are
identical to 0.1.17.

### Added
- `scripts/check_wheel.py`: compares every file under the wheel's
  `fissionkit/` directory with `src/fissionkit/` by content hash, in both
  directions. The suite always runs against `src/`, so until now nothing
  verified that the wheel ships what was tested (it did, 7/7 files, but by
  inspection rather than by check). The CI `package` job runs it after the
  build.
- `scripts/bytecode_diff.py`: fingerprints the compiled code of every
  function in two source trees (docstrings and line numbers excluded) and
  lists the functions that differ. *Note added in 0.1.19:* this version
  covered function bodies only; keyword defaults and module constants were
  invisible to it, so it was weaker than "the check behind documentation-only
  release notes" claimed. See 0.1.19.
- `mypy` in the `dev` extra, so that `pip install -e ".[dev]"` installs
  everything the local release checks need; the `uv` recipe in
  `CONTRIBUTING.md` no longer installs it separately.
- `CONTRIBUTING.md` lists the two scripts and "run the examples from the
  built archive" in the release checklist; the lint job also checks
  `scripts/`.

## [0.1.17] — 2026-09-11

Documentation release. No code changes outside docstrings; signatures,
random streams and seeded results are identical to 0.1.16.

### Fixed
- The keyword-only rule introduced in 0.1.16 was stated in the docstring of
  `count_split_de` and in the module docstring of `recipes/model_selection.py`
  but not in the docstrings of `naive_de`, `select_rank`, `evaluate_denoisers`
  and `fission_lasso_inference`; a reader of `help()` on those four would
  have missed it. All five recipe docstrings now carry the same sentence.
- `paper/versions.txt` records the commit and date of the datathin Python
  port (4ddfc5e, 2024-07-01) alongside those of the two R packages, with the
  sizes of the files each statement in Table 3 rests on.
- Manuscript §1 gives the date of the Python port's last commit next to
  "early-stage", so that the reader can judge its status without the
  adjective.

## [0.1.16] — 2026-09-11

Calling-convention release. No changes to any sampler or recipe result;
seeded results on valid inputs remain bit-for-bit identical to 0.1.10 (pinned
by test).

### Changed
- **Every option of the four applied recipes is keyword-only.**
  `count_split_de(counts, *, family, epsilon, cluster, size, random_state)`,
  `naive_de(counts, *, family, cluster, random_state)`,
  `select_rank(X, *, family, max_rank, epsilon, center, sigma2, size,
  random_state)`, `evaluate_denoisers(image_counts, denoisers, *, epsilon,
  n_repeats, random_state)` and `fission_lasso_inference(X, y, *, sigma2, tau,
  alpha_lasso, level, random_state)`. Data arguments stay positional. Reason:
  0.1.11 inserted `family` as the second positional parameter of `naive_de`
  and silently broke 0.1.10-style positional calls for four releases; with
  options keyword-only, adding one can never shift an existing call. The
  manuscript, examples, README and tests already used keywords throughout.
  *Impact:* a call that passed a recipe option positionally (e.g.
  `count_split_de(X, "poisson")`) now raises `TypeError`; passing a
  non-string `family` raises a `TypeError` that names the keyword-only rule.
  `thin()`, `gaussian_fission()`, `poisson_fission()` and
  `bernoulli_fission()` are unchanged.

### Fixed
- **Table 3 of the manuscript said countsplit (R) has no statistical property
  test suite.** It has one: `tests/testthat/test_basic.R` (421 lines, about
  a hundred expectations checking reconstruction, mean and correlation
  thresholds and error messages) in the repository at version 4.0.2. The
  0.1.15 audit had relied on the package's DESCRIPTION (no testthat in
  Suggests) and on the absence of `tests/testthat.R`; a shallow clone settles
  it. datathin (R) 1.0 has no tests directory. Table 3 now says
  "reconstruction, moment / correlation thresholds" for countsplit, and its
  caption records the versions and date checked.
- `paper/versions.txt` recorded the mypy version I had pinned locally
  (1.14.1) for the Python 3.9 type-check row rather than the version an
  unpinned install resolves (1.19.1, which also passes); the record now
  states the resolved version and says so.

### Added
- `tests/test_api_signature.py`: a snapshot of the name, kind and default
  of every parameter of every public callable, plus a check that recipe
  options are keyword-only. Bit-identity tests pin what functions return;
  this pins what they accept. It catches the 0.1.11 `naive_de` change when
  applied to that signature.
- `CONTRIBUTING.md`: the release audit checklist gains "compare public
  signatures with the previous release".

## [0.1.15] — 2026-09-11

Type-check and third-party-wording release. No changes to any sampler or
recipe; seeded results on valid inputs remain bit-for-bit identical to 0.1.10
(pinned by test).

### Fixed
- **The `typecheck` CI job added in 0.1.14 would have failed on its first
  run.** It installs the newest NumPy, and under NumPy 2.5 mypy rejects
  `select_rank`, whose `base` variable is assigned an array in one branch
  and a float in the other (NumPy 2.4 typed `ndarray.mean()` as `Any` and
  hid it). The variable is now declared `Union[float, NDArray]` up front;
  `mypy src/fissionkit` is clean under NumPy 1.22.4, 2.4.4 and 2.5.3. The
  job now runs at both the newest and the minimum declared NumPy, and the
  `uv` recipe in `CONTRIBUTING.md` runs mypy in every environment of the
  local matrix.
- **The manuscript understated the third-party datathin Python port.** §1
  said it ships "only mean-level tests" and Table 3 called its test suite
  "minimal". Its `datathin/test_helpers.py` holds 55 test functions that
  assert mean, variance and correlation thresholds; what it lacks is
  distributional tests, joint independence tests and error-control tests.
  Both passages now say that, and the access date of reference [16] is the
  date of this check. The port's family coverage, K-fold and unequal
  allocation support, and its lack of documentation and packaging were
  re-verified against `datathin/thinning.py` and its README.
- The 0.1.14 changelog dated the integer-count defect to 0.1.0, a release
  never audited; it now says "every release audited, 0.1.10 onward". It also
  said three consecutive releases had each missed a validator dimension;
  0.1.14 was the release that probed all four, and the entry now says so.
- `tests/test_v0114_fixes.py`, the template for validator probes, lacked a
  full-rank covariance among its accepted inputs; one is added, so the
  structure dimension (full-rank / rank-deficient) is actually covered.

- `.mypy_cache/` (written by the new type-check step) is ignored and rejected
  by the CI artefact check, alongside `.ruff_cache/`.

### Added
- `CONTRIBUTING.md`: two rules - every CI step that installs a tool at
  "latest" must have been run locally at that version before release, and
  every statement about third-party software must point at a specific file
  in its repository - each with the release it would have prevented.
- `paper/versions.txt` records the tool versions (ruff, mypy) and the NumPy
  versions under which the type check was run.

## [0.1.14] — 2026-09-11

Validator-scale release. No changes to any sampler or recipe; seeded results
on valid inputs remain bit-for-bit identical to 0.1.10 (pinned by test).

### Fixed
- **The covariance validator was not scale-invariant (0.1.11-0.1.13).** Its
  definiteness test used `max(1.0, largest eigenvalue)` and its symmetry test
  `np.allclose` with the default absolute `atol`, so for a `Sigma` whose
  entries were below about 1e-5 in the data's units a grossly indefinite
  matrix (`[[1, 2], [2, 1]]`, relative eigenvalue -1/3) or a grossly
  asymmetric one was accepted, and `_psd_sqrt` then silently clipped it to a
  covariance the caller never specified - the folds carried the wrong
  covariance and the independence guarantee failed. Both tests are now
  purely relative (symmetry against `max|Sigma|`, definiteness against the
  largest eigenvalue, 1e-5 as before), the zero matrix is refused, and a test
  requires identical verdicts at scales 1e-9, 1 and 1e6 for float64 and
  float32, full-rank and rank-deficient, symmetric and perturbed inputs.
- **The integer-count check was magnitude-dependent (present in every release
  audited, 0.1.10 onward).**
  `np.allclose(X, round(X))` with its default `rtol = 1e-5` rejected 3.4 but
  accepted 123456.7 and 1e7 + 0.5 as counts and rounded them silently. Whether
  a count is an integer is an absolute property; the check now uses
  `atol = 1e-8, rtol = 0` in the Poisson, negative-binomial and binomial
  recipes. Valid (integer-valued) inputs are unaffected.
- `poisson_fission` was annotated as returning two `int64` arrays but built
  them from `thin()`, whose return type covers all families; mypy reported
  the mismatch. The recipe now records the narrowing with a `cast`, and
  `mypy src/fissionkit` is clean.

### Added
- CI job `typecheck` (`mypy src/fissionkit`, default strictness) so that the
  `py.typed` marker shipped since 0.1.7 is backed by a check; `[tool.mypy]`
  in `pyproject.toml`.
- `CONTRIBUTING.md` documents the four-dimension probe (precision, structure,
  scale, symmetry) that every validator change must pass; 0.1.12 and 0.1.13
  each fixed one dimension of the same validator and missed the next, and
  this release is the first to probe all four.
- `tests/test_v0114_fixes.py`.

## [0.1.13] — 2026-09-11

Validation-tolerance and wording release. No changes to any sampler or
recipe; seeded results on valid inputs remain bit-for-bit identical to
0.1.10 (pinned by test).

### Fixed
- **Covariance validator still too strict (0.1.12).** The 1e-8 relative
  tolerance introduced in 0.1.12 accepted float64 sample covariances but
  rejected every rank-deficient covariance computed in single precision: a
  float32 Gram matrix with p > n has relative eigenvalues of -5e-8 (p = 80)
  to -1.5e-7 (p = 2000). The tolerance is now 1e-5, about 70 times the worst
  measured single-precision artefact and still 10 times below the level at
  which the test suite requires a matrix to be refused (1e-4). The test now
  includes float32 inputs at p = 80, 200 and 500, and the docstring records
  the measurements the tolerance rests on.
- The 0.1.12 changelog and the tiny-size negative-binomial test said the
  emulated 0.1.4 defect fails the exchangeability test "by hundreds of
  standard errors"; the measured value is z = -56 (critical 3.9), and both
  now say so.
- The 0.1.12 changelog, `CONTRIBUTING.md` and `paper/versions.txt` asserted
  that releases 0.1.7-0.1.11 had "only been run" on the reference
  environment. What is verifiable is narrower - no earlier release records a
  run elsewhere, and the annotation tests (added in 0.1.8) could not have
  passed on Python 3.9 - and the three texts now say exactly that.
- The PEP 604 guard test inspected a slice of the function source up to the
  first closing parenthesis; it now inspects `str(inspect.signature(f))`,
  which renders parameter and return annotations as their source strings,
  and flags any `X | Y`, not only `X | None`.
- Figure PDFs written by the example scripts carried a `CreationDate` and so
  differed between otherwise identical runs; `savefig` now omits it and the
  PDFs are byte-reproducible like the PNGs.
- The `uv` recipe in `CONTRIBUTING.md` removes the `src/*.egg-info` that an
  editable install leaves behind, which otherwise makes the installed-metadata
  test run (and pass) under `PYTHONPATH=src` and the pass/skip count vary.

## [0.1.12] — 2026-09-11

Support-matrix release. No changes to any sampler or recipe; random streams
and seeded results on valid inputs are bit-for-bit identical to 0.1.10 and
0.1.11 (now pinned by a test). Everything below came out of running the test
suite on the interpreters and dependency versions the package *claims* to
support. No earlier release records a run outside the reference environment
(CPython 3.12, NumPy 2.4), and the 3.9 and NumPy 2.5 failures below show that
at least the annotation tests had never been run there.

### Fixed
- **Python 3.9.** Public signatures used PEP 604 unions (`X | None`), which
  import fine under `from __future__ import annotations` but cannot be
  evaluated by `typing.get_type_hints` before Python 3.10; the annotation
  contract tests therefore failed on 3.9 (5 of them since 0.1.8, 5 more added
  in 0.1.11). All 15 occurrences now use `Optional[...]` / `Union[...]`. ruff
  is configured with `keep-runtime-typing = true` so that it stops rewriting
  them back, and a test asserts no PEP 604 union in any public signature.
- **NumPy 2.5.** The annotation-vs-runtime test added in 0.1.11 assumed that
  `typing.get_origin(NDArray[...])` is `numpy.ndarray`; from NumPy 2.5 it is
  the `NDArray` alias object and `isinstance` raised. The check is now
  name-based.
- **SciPy 1.8 (declared minimum).** One test used
  `chi2_contingency(...).pvalue`; the result was a plain tuple before SciPy
  1.11. Indexed access is used instead.
- **`test_nb_thinning_stable_for_tiny_size` was not a contract.** It compared
  the fold means of a single thinning to 5%, a criterion that an
  all-or-nothing split of data whose five largest rows hold 31% of the mass
  meets in about 4 of 40 seeds; it passed on the reference environment by
  coincidence and failed at the minimum SciPy version because the rescue
  path consumes randomness differently there. It now tests the property
  that holds - exchangeability: over 60 independent thinnings, the share of
  each nonzero row's mass landing in fold 0 has mean 1/2 (pooled z-test at
  1e-4). Emulating the 0.1.4 defect it guards against gives z = -56 against
  a critical value of 3.9; the shipped rescue path gives z = 1.5 and passes on
  every environment in the matrix.
- **Covariance validator too strict (0.1.11).** `_check_covariance` rejected a
  rank-deficient sample covariance (p > n) carrying 1e-9 float noise as "not
  positive semidefinite" (tolerance 1e-10), although `_psd_sqrt` clips such
  eigenvalues harmlessly. The eigenvalue test now runs on the symmetrised
  matrix with tolerance 1e-8 relative to the largest eigenvalue; materially
  indefinite matrices are still refused.
- The 0.1.11 test meant to pin seeded results asserted only reconstruction
  and shape; it now pins exact fold values for three families computed with
  0.1.10 and 0.1.11.
- Stale module docstring of `recipes/cluster_validation.py` (it still named
  the exact Poisson test as *the* per-feature test; there have been four since
  0.1.1).
- `scripts/release.sh` installs `setuptools>=68` into its throwaway
  environment before the non-isolated build instead of assuming it.
- The 0.1.11 changelog entry said `.ruff_cache/` "was tracked"; only its
  presence in the shipped archive was verified, and the entry now says so.

### Added
- CI job `min-versions`: Python 3.9 with `numpy==1.22.4`, `scipy==1.8.1`,
  `scikit-learn==1.1.3`, the lower bounds declared in `pyproject.toml`. The
  ruff version used by the lint job is pinned to a minor range, since the
  default rule set changes between ruff minors.
- `paper/versions.txt` records the support matrix actually run before this
  release (six interpreter/dependency combinations, all passing).
- `examples/demo_cluster_validation.py --seeds N` controls the Monte-Carlo
  loop (default 20; 0 skips it).
- `tests/test_v0112_fixes.py`.

## [0.1.11] — 2026-09-11

Pre-submission audit release. Random streams and every seeded result on
*valid* inputs are bit-for-bit identical to 0.1.10; the only numerical change
is in the double-dipping *baseline* reported by the cluster-validation
example, whose test now matches the thinned workflow.

### Changed
- **`naive_de` gains a `family` argument** and uses the same per-feature test
  as `count_split_de` for that family (exact Poisson / Poisson LR, or Welch /
  Kruskal-Wallis for `negative_binomial`). The baseline previously always used
  the exact Poisson test, so on overdispersed counts the reported inflation
  mixed double dipping with the anti-conservativeness of a Poisson test on
  negative-binomial data. On the null matrix of
  `examples/demo_cluster_validation.py` the same double-dipped labels give 51%
  rejections with the mismatched test and **37% with the matched one**; count
  splitting gives 3% (5.5% averaged over 20 seeds, i.e. the nominal level).
  The default `family="poisson"` reproduces the old behaviour exactly.
  *Impact:* Fig. 2 and the headline numbers in the manuscript, README and
  docstrings now read 37% → 3%. *Note added in 0.1.16:* `family` was inserted
  as the second positional parameter, so 0.1.10-style positional calls
  `naive_de(X, my_cluster)` fail with a `ValueError` about the family; this
  entry should have said so. Recipe options are keyword-only from 0.1.16.
- The audit numbers quoted for `fission_lasso_inference` (diagnostic flag
  rates, n = 30 coverage) are restated from the new shipped script
  `examples/audit_fission_diagnostic.py` with its design spelled out
  (n = 30, p ∈ {5, 8, 10}, 300 replications each, pooled 0.896).

### Fixed
- **Nuisance parameters are validated for value, not only for presence.** A
  negative `sigma2` in `thin()` or `gaussian_fission()` returned all-NaN folds
  with nothing but a NumPy `RuntimeWarning`; a non-positive `size`, `shape` or
  degrees of freedom surfaced as a bare NumPy/SciPy message (`shape < 0`);
  binomial counts above `n_trials` gave `nbad < 0`; a non-symmetric or
  indefinite `Sigma` was accepted. All now raise a `ValueError` naming the
  family and parameter. `count_split_de` rejects families other than
  `poisson` / `negative_binomial`; `count_split_de`, `select_rank` and
  `evaluate_denoisers` reject `epsilon` outside (0, 1); `evaluate_denoisers`
  rejects `n_repeats < 1`; `fission_lasso_inference` rejects `level` outside
  (0, 1), non-positive `tau` or `sigma2`, and mismatched `X` / `y` shapes.
- Return annotations of `bernoulli_fission` (an array and a dict, not two
  arrays) and `estimate_nb_size` (an array, not a float) were wrong; a new
  test calls every public function and checks the annotated return type
  against the object actually returned, since resolvable annotations are not
  the same as correct ones.
- `.ruff_cache/` was shipped in the release archive; it is now ignored and
  the CI artefact check rejects it.
- `matplotlib` is required by the figure-producing examples but was not
  declared; it is now part of the `dev` extra.
- `scripts/release.sh` ran the suite only from `src/`, so the test comparing
  `__version__` with the installed distribution metadata was always skipped
  at release time; the script now also installs the archive into a throwaway
  environment and runs that check.
- `examples/demo_rank_selection.py` claimed that the thinned curve "turns at
  the planted rank"; it typically selects rank 3 for the planted rank 4 (2-4
  across seeds), as the manuscript says. The docstring now explains why, and
  the script prints the in-sample scree curve and the selected rank over 20
  seeds, which it previously only described.

### Added
- `examples/audit_fission_diagnostic.py` (see above).
- `examples/fig_architecture.py`, which regenerates Fig. 1; the figure now
  draws the fission output as the pair `(f, g)` rather than as stacked folds.
- `tests/test_v0111_fixes.py`: value validation, the matched baseline test,
  the return-annotation contract, and a guard that validation leaves the
  random stream on valid inputs unchanged. The denoiser test now checks the
  full ranking against the oracle, not only its best and worst entries.
- `paper/versions.txt` maps every number quoted in the manuscript to the
  script that regenerates it.

## [0.1.10] — 2026-09-04

Test coverage only. No source changes, no behaviour changes; all seeded
results are bit-for-bit identical to 0.1.9.

### Added
- Regression guards for input validation and reproducibility in `thin()`.
  An independent check of the eight recipes against the distributions in the
  source papers (38 assertions, using SciPy's reference distributions rather
  than this package's own expectations) found no defects, but did find six
  behaviours that were correct and untested:
  rejection of an `epsilon` that does not sum to one, rejection of a negative
  `epsilon`, rejection of a single fold, all-zero input mapping to all-zero
  folds, exact reproducibility of `thin()` from an integer seed, and fold
  independence tested on the joint contingency table rather than only through
  zero correlation.
  Correct-but-unguarded behaviour is what regresses silently during a later
  refactor.

## [0.1.9] — 2026-09-04

Metadata and comment hygiene. No behaviour changes; all seeded results are
bit-for-bit identical to 0.1.8.

### Fixed
- `pyproject.toml` carried a placeholder author string that was copied verbatim
  into the built distribution metadata (`Author: PLACEHOLDER - to be filled by
  the submitting authors`) and would have appeared on the PyPI project page.
  It is now marked as a release blocker in a comment beside the field.
- Comments added in 0.1.7 and 0.1.8 were written in a language other than the
  one used throughout the rest of the project. All source comments are English
  again.
- `tests/test_v011_fixes.py` and `tests/conftest.py` referred to numbered items
  of an internal review document that is not distributed with the package. The
  technical content is unchanged; only the framing is now self-contained.

## [0.1.8] — 2026-09-04

Release-integrity fixes. No statistical behaviour changes; all seeded results
are bit-for-bit identical to 0.1.7.

### Fixed
- `scripts/release.sh` could not read the project version. It extracted the
  version with a regular expression over `pyproject.toml`, which stopped
  matching when 0.1.7 moved to a dynamic version; the script aborted before
  building anything. It now reads `fissionkit.__version__`, the same single
  source the build uses.
- Type annotations on the public API referenced names that the defining
  modules never imported. Because the modules use `from __future__ import
  annotations` the annotations are stored as strings and never evaluated, so
  the package imported cleanly and every test passed while type checkers saw
  nothing usable. All fifteen public callables now resolve under
  `typing.get_type_hints`.
- `README.md` listed a Nile hydrology series among the datasets used by the
  examples. No example uses it.
- The repository carried duplicate figures at its root: the example scripts
  wrote output to the working directory, so running them from the repository
  root and from `examples/` produced two sets. Scripts now write relative to
  their own location, and the stale root copies are removed.

### Added
- `tests/test_public_api.py`, covering contracts that the numerical suite
  cannot see: annotations must resolve rather than merely parse, `__all__`
  entries must be importable, distribution metadata must agree with
  `__version__`, and the `py.typed` marker must reach the installed package.
  Each check corresponds to a defect that shipped at least once.
- `MANIFEST.in`: the runnable examples are now part of the source
  distribution; the manuscript and figures stay in the repository only.
- `CITATION.cff` gains the `type` and `date-released` fields.

### Note on versioning
Two archives were circulated as 0.1.7 during review, differing in the defects
listed above. This release supersedes both. A version number that has been
handed to anyone is never reused for different content.

## [0.1.7] — 2026-09-04

Packaging and typing release. No statistical behaviour changes; all seeded
results are bit-for-bit identical to v0.1.6.

### Fixed
- The package version is now derived from a single source
  (`fissionkit.__version__`). Earlier releases could report a stale version in
  the installed distribution metadata while `import fissionkit` reported the
  current one.
- The source archive no longer contains build artefacts (`build/`,
  `*.egg-info/`, `__pycache__/`, `.pytest_cache/`). A stale copy of the
  package had previously been shipped alongside the sources.

### Added
- Type annotations on the full public API, and a `py.typed` marker so that
  type checkers use them.
- Python 3.13 in the tested matrix; lint and packaging checks in CI.

## [0.1.6] — 2026-08-29

Documentation release. No behaviour changes.

### Changed
- The feature comparison in the manuscript (Table 3) and the related
  discussion in Section 1 were corrected after re-checking the third-party
  Python port of datathin against its repository. That port covers the
  convolution-closed families **and** several generalized
  (sufficient-statistic) recipes — more families than fissionkit — and
  supports K folds with unequal allocations. fissionkit's differentiation is
  therefore stated in terms of data fission, the applied workflows, the
  statistical-property test suite and packaging, not the number of families.
- The additional random-number consumption on the negative-binomial rescue
  path (introduced in 0.1.5) is now documented in the source. Random streams
  remain identical to v0.1.4 on data that does not trigger the rescue path.

## [0.1.5] — 2026-08-29

Correctness and performance release.

### Fixed
- **Negative-binomial thinning with very small `size * epsilon`.** The float64
  gamma representation of the Dirichlet split underflows in this regime; at
  `size = 1e-3, mu = 50`, 78% of nonzero rows degenerated and dumped all mass
  into the last fold, warning only with a generic `RuntimeWarning`. Such rows
  are now detected and resampled through a numerically stable sequential
  beta-binomial representation. Fold means at those settings are 31.9 / 31.1
  where 0.1.4 gave 22 / 41.
  *Impact:* the fast path and its random stream are unchanged for normal
  parameter ranges, so previously seeded results are unaffected.
- `thin()` raises on conflicting `epsilon` and `K` arguments instead of
  silently ignoring `K`.
- `welch_two_group_test` is importable from the package top level;
  `naive_de` was missing from its module `__all__`.

### Changed
- **Multivariate-Gaussian splitting is substantially faster.** Noise is now
  drawn through the separable square root `L_A ⊗ L_Σ` rather than by
  eigendecomposing the `(Kp × Kp)` Kronecker matrix: `O(K³ + p³)`, measured
  3.6 s → 0.55 s at `p = 1200`. Additivity and the block-covariance contract
  are preserved.
  *Impact:* draws differ from 0.1.4 **for this family only**. Re-run any
  seeded `mvgaussian` results.
- Two docstring claims (the t₃ flag rate and small-`n` coverage) are restated
  with replication counts and observed ranges rather than point values.

## [0.1.4] — 2026-08-22

Release-process release. No statistical behaviour changes.

### Added
- `tests/conftest.py` pins the suite's import path to the local `src/` tree
  and fails loudly if an installed copy shadows it, with a regression test
  reproducing that failure mode.
- `scripts/release.sh` builds the archive from `HEAD` and re-runs the full
  suite from the built archive, in an isolated directory, before shipping.
- `CONTRIBUTING.md` documents the verification steps expected of a release.

## [0.1.3] — 2026-08-22

### Changed
- The misspecified-scale diagnostic in `fission_lasso_inference` now uses the
  empirically studentized mean of the residual cross-products. Measured on the
  shipped code: 100% detection of a misspecified scale, 0% flags under normal
  errors, 2.5% under t₃ errors with a correct marginal scale. Those residual
  flags mark samples whose realized noise variance drifted from the supplied
  `sigma2` in either direction. `sigma2=None` is recommended in heavy-tailed
  settings.

### Added
- Provenance for the cell image used in the denoising demo (quantitative
  phase imaging, CC0; Müller et al. 2018).
- `paper/versions.txt` records the library versions behind the numbers quoted
  in the manuscript.

## [0.1.2] — 2026-08-22

### Fixed
- `fission_lasso_inference(sigma2=None)` refuses designs with `n - p < 20`.
  Below that threshold the pilot fit interpolates and the fission split
  silently collapses into same-data selection and inference.

### Changed
- Small-sample behaviour of the estimated-scale mode is documented
  (asymptotically exact; ≈0.88 coverage at `n = 30` against a nominal 0.90).
  A `note` field flags runs with `n - p < 40`.
- The residual cross-fold dependence of the Poisson fallback in
  `estimate_nb_size` is documented (order `μ²/b`; no inflation observed in
  stress tests).

### Removed
- `statsmodels` from the dev extras; it was unused.

### Added
- `examples/benchmark.py` regenerates the timing figures.

## [0.1.1] — 2026-08-22

### Added
- `estimate_sigma2_diff` for estimating the noise scale from a sequence.
- Multi-group testing after clustering: `poisson_lr_test` (per-feature Poisson
  likelihood ratio) and `kruskal_test`.
- Automatic per-feature negative-binomial size estimation
  (`estimate_nb_size`) with a Poisson fallback.
- `select_rank(center=...)`: uncentred SVD by default, PCA convention optional.

### Changed
- `fission_lasso_inference` warns when a residual cross-covariance diagnostic
  indicates a misspecified noise scale.
- `fission_lasso_inference(sigma2=None)` estimates the noise scale from the
  inference copy and uses Student-t quantiles with `df = n - |S|`.
- All internal randomness, including `LassoCV` folds, derives from the single
  user-supplied seed.

### Fixed
- Dead code that consumed random state in negative-binomial thinning.
- `bernoulli_fission` no longer exposes the external randomization.
- NaN and sparse inputs are rejected; denoiser outputs are validated.

## [0.1.0] — 2026-08-22

Initial release: the thinning engine (8 convolution-closed families),
Gaussian and Bernoulli fission, four applied workflows, and the statistical
property test suite.
