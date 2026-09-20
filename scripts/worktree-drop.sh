#!/usr/bin/env bash
# worktree-drop.sh — tear down a sibling worktree after its PR merges.
#
# Mirrors worktree-new.sh: resolves the sibling path from the current
# repo root, then:
#
#   1. detects the branch checked out in the target worktree (refuses
#      `main` or a detached HEAD);
#   2. refuses if tracked-file changes exist (unless --force);
#   3. `git worktree remove <path> --force`;
#   4. `git branch -D <branch>` — force-delete because squash-merges
#      leave feature branches looking unmerged even after they land.
#
# We deliberately do NOT `git pull` main here. The sprint loop already
# pulls before branching; pulling here would surprise anyone running
# this from a stale main.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/worktree-drop.sh <slug> [--force]

Removes the sibling worktree at `../<repo>-<slug>/` and force-deletes
its branch. Refuses to run if:
  - <slug> is `main`,
  - the worktree does not exist,
  - the worktree has uncommitted tracked changes (unless --force is
    passed; untracked build artifacts like `.venv/` are always ignored).

Force-delete (`branch -D`) is intentional: PRs are squash-merged in
this repo, so git never sees a feature branch as merged into main even
after it has landed. `-d` would refuse every real-world cleanup.

Example:
  scripts/worktree-drop.sh watch-pr-script
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
force=0
if [[ $# -eq 2 ]]; then
    if [[ "$2" != "--force" ]]; then
        usage >&2
        exit 2
    fi
    force=1
fi

if [[ "$slug" == "main" ]]; then
    echo "worktree-drop.sh: refusing to drop the main worktree" >&2
    exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
parent="$(cd "$repo_root/.." && pwd)"
repo_name="$(basename "$repo_root")"
target="$parent/${repo_name}-${slug}"

if [[ ! -d "$target" ]]; then
    echo "worktree-drop.sh: worktree does not exist: $target" >&2
    exit 2
fi

branch="$(git -C "$target" rev-parse --abbrev-ref HEAD)"
if [[ "$branch" == "main" ]] || [[ "$branch" == "HEAD" ]]; then
    echo "worktree-drop.sh: refusing to drop worktree on branch '$branch'" >&2
    exit 2
fi

# Only tracked-file changes count as "uncommitted work". `status --porcelain`
# without `-uall` still lists untracked entries, so filter them out — a
# freshly-built .venv/ is expected debris.
dirty="$(git -C "$target" status --porcelain | grep -Ev '^\?\?' || true)"
if [[ -n "$dirty" && "$force" -ne 1 ]]; then
    echo "worktree-drop.sh: $target has uncommitted tracked changes:" >&2
    echo "$dirty" >&2
    echo "re-run with --force to drop anyway" >&2
    exit 2
fi

echo "==> removing worktree $target"
git -C "$repo_root" worktree remove "$target" --force

echo "==> deleting branch $branch (force: squash-merge means -d would refuse)"
git -C "$repo_root" branch -D "$branch"

echo
echo "dropped:"
echo "  path:   $target"
echo "  branch: $branch"
