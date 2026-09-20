#!/usr/bin/env bash
# ==============================================================================================================================
# Iterate each uv workspace member and run its pytest suite if one exists.
# ==============================================================================================================================
# Mirrors the `Test Subprojects` matrix in `.github/workflows/test.yml`
# so local pre-push runs cannot pass while CI would fail.
#
# No workspace members exist yet; the script is safely idempotent and
# no-ops until members are added to `[tool.uv.workspace].members`.
# ==============================================================================================================================
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

# Discover subproject directories: any dir (except the repo root) that has
# both a pyproject.toml and a tests/ directory. Uses a portable while-read
# loop instead of `mapfile` so it works on macOS's bundled bash 3.2.
subprojects=""
while IFS= read -r pj; do
    dir="$(dirname "$pj")"
    dir="${dir#./}"
    if [ "$dir" != "." ] && [ -d "$dir/tests" ]; then
        subprojects="$subprojects$dir"$'\n'
    fi
done < <(find . -maxdepth 4 -name pyproject.toml -type f 2>/dev/null)

if [ -z "$subprojects" ]; then
    echo "run-subproject-tests: no workspace members with tests/ found; skipping."
    exit 0
fi

failed=0
while IFS= read -r sp; do
    [ -z "$sp" ] && continue
    echo "==> pytest ($sp)"
    if ! (cd "$sp" && uv run pytest tests/); then
        failed=1
        echo "!! $sp tests failed"
    fi
done <<< "$subprojects"

exit "$failed"
