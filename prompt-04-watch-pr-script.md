# Prompt: Sprint 04 — Port `watch-pr.sh` from `cms-open-data`

## Why now

The repo is now on GitHub with a branch-protection rule that forces
every change through a PR. The orchestrator (human or agent) needs a
reliable way to wait for CI + merge without either burning conversation
context on tight polling or missing a re-triggered check.

`cms-open-data` already solved this with `scripts/watch-pr.sh` — a
polling script that emits machine-readable markers (`CI_PASS`,
`CI_FAIL`, `MERGED <ts>`, `CLOSED`). Port it so future sprints in this
repo have the same guarantee.

Depends on `ci/terraform-checks` (sprint 03) being merged.

## Goal

`scripts/watch-pr.sh <pr-number> [--ci-only]` runs in this repo,
watches a PR to CI-green then to merge, and exits with the same
contract as the source script. AGENTS.md documents its use in the
"After Opening a PR" section.

## Approach

Single `feat:` PR. Branch from `main`:

```bash
git checkout main && git pull --ff-only
git checkout -b feat/watch-pr-script
```

1. Copy `scripts/watch-pr.sh` verbatim from cms-open-data. The script
   is fully generic — no cms-specific paths, tools, or assumptions —
   so no adaptation beyond the header comment referring to "this repo".
2. Verify shellcheck is happy (`shellcheck -x scripts/watch-pr.sh`).
   Fix any findings the CI shellcheck job would flag.
3. Amend AGENTS.md's "After Opening a PR" section: point at
   `scripts/watch-pr.sh <n>` as the standard poller. Keep the
   `ScheduleWakeup` recommendation for agents that want to yield the
   conversation while the runner works.
4. Add `tests/test_watch_pr_helpers.py` — a small pytest suite that
   spawns a bash sub-shell to invoke each awk helper (`all_settled`,
   `all_ok`, `print_failing_checks`, `failing_fingerprint`) as
   standalone functions and asserts their outputs against synthetic
   `gh pr checks` fixtures. This gives the awk parsing a regression net
   without needing a live PR.

## Files

|      | Path                                     |
| ---- | ---------------------------------------- |
| ADD  | `scripts/watch-pr.sh` (executable)       |
| ADD  | `tests/test_watch_pr_helpers.py`         |
| EDIT | `AGENTS.md` (After Opening a PR section) |

## Verification

```bash
shellcheck -x scripts/watch-pr.sh
uv run pytest tests/
uv run pre-commit run --all-files
scripts/watch-pr.sh --help          # exits 0
scripts/watch-pr.sh 999999          # exits 2 with "cannot access PR"
```

Paste the `--help` output + the exit-2 output into the PR body.

## Out of scope

- `worktree-new.sh` / `worktree-drop.sh`. Those depend on a bare-repo
  container layout this repo doesn't have. Deferred until we decide on
  a worktree convention.
- Adapting the polling intervals — 20s / 30s are fine defaults from
  the source script.
- A `--merged-only` flag. Ripe for premature abstraction; add it when
  a real caller needs it.
- Machine-readable JSON output. The current `CI_PASS` / `CI_FAIL` /
  `MERGED <ts>` / `CLOSED` markers are what downstream callers grep
  for.

## Gotchas

- `gh pr checks` exits non-zero when any check is failing. The source
  script guards with `|| true` under `set -e`; preserve that.
- `gh pr view --json state` needs at least one _resolved_ field to
  actually round-trip a lookup — bare `--json number` echoes the arg
  back without a fetch. The source script requests `number,state`; keep
  it.
- Under bash 3.2 (macOS default) some `[[` idioms behave differently
  than bash 5. The source script uses only bash-3.2-safe constructs;
  verify it still runs under `/bin/bash` on macOS.
- `tests/test_watch_pr_helpers.py` will run `bash -c` under `subprocess.run`.
  Ruff's `S603` (subprocess call) and `S607` (partial path) will fire —
  add narrow `# noqa` with justification.
- Pre-commit's `shellcheck` hook (indirectly, via the CI workflow) will
  gate merge. Any `SC2086`-style unquoted-var warning must be fixed,
  not suppressed.
