#!/bin/sh
# Release verification: build the archive from HEAD and re-run the full test
# suite from that archive in an isolated environment.  Two rules it enforces:
# never trust a deliverable that has not been cold-started, and never let
# archive creation hide behind a fallible command chain.
set -eu
cd "$(git rev-parse --show-toplevel)"

if [ -n "$(git status --porcelain)" ]; then
    echo "release.sh: working tree not clean - commit first" >&2
    exit 1
fi

# Version comes from the single source of truth (fissionkit.__version__),
# not from a regex over pyproject.toml -- the project uses a dynamic version.
VERSION=$(PYTHONPATH="$PWD/src" python3 -c "import fissionkit; print(fissionkit.__version__)")
# Two uses, one script.  Cutting a release: the top CHANGELOG entry and
# CITATION.cff must carry today's UTC date (both files use UTC dates), so
# that a release never goes out with a stale date.  Verifying a release
# that already exists - HEAD carries the tag v$VERSION, or "--verify" is
# given - its date is its release date, not today's; only the consistency
# between the two files is checked.  0.1.28 checked "today" in both cases,
# so every released archive was refused by its own script from the next
# UTC day on.
MODE=cut
if [ "${1:-}" = "--verify" ] || git tag --points-at HEAD 2>/dev/null | grep -qx "v$VERSION"; then
    MODE=verify
fi
TODAY=$(date -u +%F)
CFF_DATE=$(sed -n 's/^date-released: "\(.*\)"/\1/p' CITATION.cff)
LOG_LINE=$(grep -m1 '^## \[' CHANGELOG.md)
LOG_VERSION=$(printf '%s' "$LOG_LINE" | sed 's/^## \[\([^]]*\)\].*/\1/')
LOG_DATE=$(printf '%s' "$LOG_LINE" | sed 's/.*— //')
[ "$LOG_VERSION" = "$VERSION" ] || { echo "top CHANGELOG entry is $LOG_VERSION, package is $VERSION" >&2; exit 1; }
[ "$CFF_DATE" = "$LOG_DATE" ] || { echo "CITATION.cff date-released is $CFF_DATE, top CHANGELOG entry is dated $LOG_DATE" >&2; exit 1; }
if [ "$MODE" = cut ]; then
    [ "$CFF_DATE" = "$TODAY" ] || { echo "cutting v$VERSION: CITATION.cff and CHANGELOG.md are dated $CFF_DATE, today (UTC) is $TODAY" >&2; exit 1; }
    echo "cutting v$VERSION dated $TODAY (UTC)"
else
    echo "verifying existing release v$VERSION dated $CFF_DATE (UTC)"
fi
[ -n "$VERSION" ] || { echo "release.sh: could not read version" >&2; exit 1; }
mkdir -p dist
ARCHIVE="dist/fissionkit-v${VERSION}.tar.gz"
git archive --format=tar.gz --prefix="fissionkit/" -o "$ARCHIVE" HEAD
echo "built  $ARCHIVE"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
tar xzf "$ARCHIVE" -C "$TMP"
cd "$TMP/fissionkit"
PYTHONPATH="$PWD/src" python3 -c "import fissionkit, inspect, sys; p=inspect.getfile(fissionkit); assert '$TMP' in p, p; print('isolated import:', p)"
PYTHONPATH="$PWD/src" python3 -m pytest tests/ -q -p no:cacheprovider

# The suite above imports from src/, so test_version_is_single_sourced (which
# compares __version__ with the *installed* distribution metadata) is skipped.
# Install the archive into a throwaway environment and run the suite again so
# that check is exercised before anything ships.
python3 -m venv --system-site-packages "$TMP/venv"
# The build backend (setuptools>=68) must be importable in the venv for a
# non-isolated build; install it there if the system copy is too old.
"$TMP/venv/bin/python" -m pip install --quiet "setuptools>=68"
"$TMP/venv/bin/python" -m pip install --quiet --no-deps --no-build-isolation "$TMP/fissionkit"
"$TMP/venv/bin/python" -m pytest tests/ -q -p no:cacheprovider -k "version_is_single_sourced or public_name"
echo "release verification passed for v${VERSION}"
