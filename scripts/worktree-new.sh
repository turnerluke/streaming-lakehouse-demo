#!/usr/bin/env bash
# worktree-new.sh — create a sibling worktree for parallel sprint work.
#
# This repo is a regular git clone, not a bare-repo container. Sibling
# worktrees live one directory up, named `<repo>-<slug>/` so they don't
# collide with unrelated projects sharing the same parent directory:
#
#     /Users/you/projects/streaming-lakehouse-demo/          # main
#     /Users/you/projects/streaming-lakehouse-demo-foo/      # feat/foo
#     /Users/you/projects/streaming-lakehouse-demo-bar/      # feat/bar
#
# The script:
#   1. resolves the current repo root and derives the sibling path,
#   2. `git worktree add`s a new worktree branched from main,
#   3. runs `uv sync --group dev` inside it so tests can run immediately.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/worktree-new.sh <slug> [branch]

Creates a sibling worktree at `../<repo>-<slug>/`, branched from the
current tip of `main`. If <branch> is omitted it defaults to
`feat/<slug>`.

After the worktree is created the script also:
  - runs `uv sync --group dev` inside the new worktree.

Examples:
  scripts/worktree-new.sh watch-pr-script
      # -> ../streaming-lakehouse-demo-watch-pr-script/  (feat/watch-pr-script)

  scripts/worktree-new.sh matrix-name fix/matrix-job-name
      # -> ../streaming-lakehouse-demo-matrix-name/      (fix/matrix-job-name)
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
    usage >&2
    exit 2
fi

case "${1:-}" in
    -h | --help)
        usage
        exit 0
        ;;
esac

slug="$1"
branch="${2:-feat/$slug}"

if ! [[ "$slug" =~ ^[a-z0-9][a-z0-9._-]*$ ]]; then
    echo "worktree-new.sh: slug must be lowercase kebab/dot/underscore (got: $slug)" >&2
    exit 2
fi

# Resolve repo root and derive the sibling path. `--show-toplevel`
# returns the working-tree root regardless of which worktree the
# script was invoked from.
repo_root="$(git rev-parse --show-toplevel)"
parent="$(cd "$repo_root/.." && pwd)"
repo_name="$(basename "$repo_root")"
dest="$parent/${repo_name}-${slug}"

if [[ -e "$dest" ]]; then
    echo "worktree-new.sh: destination already exists: $dest" >&2
    exit 2
fi

echo "==> creating worktree $dest on branch $branch"
git -C "$repo_root" worktree add "$dest" -b "$branch" main

echo "==> uv sync --group dev in $dest"
(
    cd "$dest"
    uv sync --group dev
)

echo
echo "worktree ready:"
echo "  path:   $dest"
echo "  branch: $branch"
echo
echo "next:  cd $dest"
