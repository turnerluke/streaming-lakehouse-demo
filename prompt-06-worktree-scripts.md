# Prompt: Sprint 06 — Port `worktree-new.sh` and `worktree-drop.sh`

## Why now

Sprint 04 ported `scripts/watch-pr.sh`. The other two workflow helpers
from `cms-open-data` — `scripts/worktree-new.sh` and
`scripts/worktree-drop.sh` — round out the toolkit and let a future
orchestrator run sprints in parallel worktrees instead of stopping to
stash/checkout every branch switch.

`cms-open-data`'s scripts assume a bare-repo container layout
(`<container>/.bare/`, `<container>/main/`, `<container>/<name>/`).
This repo is a regular clone at
`/Users/turner/projects/streaming-lakehouse-demo/` — so the scripts
have to be adapted, not copied verbatim.

Depends on `fix/matrix-job-name` (sprint 05) being merged — done.

## Goal

- `scripts/worktree-new.sh <slug> [branch]` creates a sibling worktree
  at `../streaming-lakehouse-demo-<slug>/`, branched from the current
  tip of `main`, defaults branch name to `feat/<slug>`, runs
  `uv sync --group dev` inside it.
- `scripts/worktree-drop.sh <slug> [--force]` tears down the worktree
  and force-deletes its branch (squash-merges leave feature branches
  looking unmerged to `git`, so `-d` refuses).
- Both refuse dangerous no-ops: the main worktree, missing target,
  uncommitted tracked changes without `--force`.
- Shellcheck clean under `-x`. Documented in `AGENTS.md`.

## Approach

Single `feat:` PR. Branch from `main`:

```bash
git checkout main && git pull --ff-only
git checkout -b feat/worktree-scripts
```

1. **Locate the repo root.** cms resolves the "container" via
   `git rev-parse --git-common-dir` (which points at `.bare/` in the
   cms layout). Here we resolve the *worktree root* instead
   (`git rev-parse --show-toplevel`), take its `basename` as the repo
   name, and place sibling worktrees at
   `../${repo_name}-${slug}/`.
2. **`worktree-new.sh`:**
    - Validate `slug` matches `^[a-z0-9][a-z0-9._-]*$`.
    - Refuse if the destination already exists.
    - `git worktree add "$dest" -b "$branch" main`.
    - Skip cms's `rsync data/raw/` step (this repo has no CMS
      extracts; the block is dead weight until we actually have data
      to seed).
    - `uv sync --group dev` inside the new worktree.
    - Skip cms's `dbt deps` step — `dbt/packages.yml` exists but
      running `dbt deps` requires a `profiles.yml` this repo doesn't
      ship. Runbook step for later.
    - Print the ready-to-`cd` path at the end.
3. **`worktree-drop.sh`:**
    - Refuse dropping the main worktree or a worktree on `HEAD`
      (detached).
    - `git status --porcelain | grep -v '^??'` to detect tracked
      dirtiness; refuse unless `--force`.
    - `git -C <root>/main pull --ff-only` — n/a for us; instead
      `git -C <root> pull --ff-only` on the main worktree. But we
      might BE the main worktree. Safer: skip the pull entirely and
      leave it to the operator (the sprint loop already pulls before
      branching).
    - `git worktree remove <name> --force`.
    - `git branch -D <branch>` in the current repo (no bare
      indirection needed).
4. **Shellcheck.** Both scripts must pass `shellcheck -x` with no
   suppressions.
5. **AGENTS.md.** Add a short subsection under "Sprint loop" pointing
   at both scripts. Not required for the loop (branch-in-place works),
   but recommended for parallel work.

## Files

| | Path |
|---|---|
| ADD | `scripts/worktree-new.sh` (executable) |
| ADD | `scripts/worktree-drop.sh` (executable) |
| EDIT | `AGENTS.md` (add worktree note under Sprint loop) |

## Verification

Since these scripts mutate the working tree, verify by *running* them:

```bash
scripts/worktree-new.sh --help          # exit 0
scripts/worktree-drop.sh --help         # exit 0
scripts/worktree-new.sh Main            # exit 2 (invalid slug)
scripts/worktree-new.sh smoke-test
cd ../streaming-lakehouse-demo-smoke-test
git branch --show-current               # feat/smoke-test
ls .venv                                # uv sync worked
cd -
scripts/worktree-drop.sh smoke-test
ls -d ../streaming-lakehouse-demo-smoke-test 2>&1
                                        # No such file or directory
```

Local gates:

```bash
uv run pre-commit run --all-files
uv run pytest tests/
shellcheck -x scripts/worktree-new.sh scripts/worktree-drop.sh
```

## Out of scope

- Unit tests. cms doesn't have them for these scripts either; they're
  filesystem-mutating and hard to fixture without over-mocking. The
  adversarial reviewer runs them against a real worktree.
- Data seeding (`rsync data/raw/`). No data extracts to seed yet.
- `dbt deps` in `worktree-new.sh`. Needs a `profiles.yml`; separate
  sprint.
- Auto-registering worktrees with Dagster or any other tool.
- A `worktree-list.sh` helper. `git worktree list` already exists.

## Gotchas

- **Path convention:** siblings live at `../<repo>-<slug>/`, not
  `../<slug>/`. Bare `<slug>` would collide with other projects in
  `/Users/turner/projects/`.
- **`git worktree remove --force` still refuses** on a worktree that
  has staged (but not committed) changes. The `--force` in this
  script's contract is about the tracked-changes check, not about
  overriding git's own refusal — surface git's error message plainly
  if it happens.
- **Never `rm -rf`** the target as a fallback. `git worktree remove`
  is the only allowed teardown; unlinking manually leaves a stale
  entry in `.git/worktrees/` that `git worktree prune` has to clean
  up later.
- **`chmod +x`** must be committed with the file. Missing execute bit
  = a mysterious "command not found" for whoever cloned fresh.
- **Do not stack on this PR.** Sprint 07 (already queued) waits for
  this one to merge before branching.
