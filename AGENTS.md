# Project Conventions

## Git Workflow

- **Always work on a branch.** Never commit directly to `main`.
- **Always open a PR** for changes — even trivial ones. No direct pushes to
  `main`.
- **Always branch from `main`.** Before creating a new branch, run
  `git checkout main && git pull --ff-only` so the branch starts at the
  current tip. Never stack new work on top of another open PR — wait for
  the parent to merge, pull `main`, then branch.
- Use conventional-commit format for commit messages and PR titles
  (`feat:`, `fix:`, `docs:`, `chore:`, etc.).
- Keep each PR focused on one logical change.
- **Never add co-author trailers** to commits (no `Co-Authored-By:` lines —
  including for Claude). Commits should be authored solely by the user.

## Commit Message Format

- **Wrap commit body lines at ~72 characters.** `gitlint` enforces a
  100-char body line limit; aim for 72 to stay clear of it.
- **Never use `git commit -m "subject" -m "long body…"`.** Multiple `-m`
  flags concatenate as separate paragraphs but each one becomes a single
  unbroken line — long bodies always exceed the line-length cap. Use a
  heredoc with manual line wrapping instead:

    ```bash
    git commit -m "$(cat <<'EOF'
    type: short subject under 72 chars

    Body paragraph wrapped at about 72 columns so it stays clear of
    gitlint's 100-char body-line-length cap.

    Second paragraph also wrapped.
    EOF
    )"
    ```

- **Backtick uppercase identifiers in the subject** so
  `subject-case-allow-backticks` (in `.commitlintrc.cjs`) accepts them:
    - Wrong: `chore: add MIT license`
    - Right: ``chore: add `MIT` license``

## PR Bodies

- **Do not include unchecked test-plan checklists** (or any other unchecked
  to-do list) in PR descriptions. Checklist items represent verification work
  that should be **done before opening the PR**. If you've done the work,
  describe what you verified in prose; if you haven't, do it first. An empty
  checkbox is a reminder to yourself, not signal for a reviewer.

## Sprints (`prompt-*.md`)

- Every incremental piece of work is scoped by a `prompt-<slug>.md`
  file at the repo root. It captures: **Why now**, **Goal**, **Approach**,
  **Files** (add/edit/delete table), **Verification**, **Out of scope**,
  **Gotchas**.
- The prompt file is **local-only** — `prompt-*.md` is `.gitignore`d.
  It's the author's scoping notebook and the adversarial reviewer's
  brief; it is never committed.
- The durable historical record of a sprint is its **PR body + commit
  message**, not the prompt file. Write the PR body assuming nobody
  will ever see the prompt.
- One prompt = one PR. Follow-up work gets its own prompt with a fresh
  slug.
- New prompts must state their dependency on any open PR and wait for
  that PR to merge before branching (never stack).

### Sprint loop (every sprint runs this end-to-end)

1. **Write** `prompt-<slug>.md` locally at repo root (never committed).
2. **Branch** from `main` (`git checkout main && git pull --ff-only`,
   then `git checkout -b <type>/<slug>`).
3. **Implement**. One logical change, one commit.
4. **Local gates.** `uv run pre-commit run --all-files` and
   `uv run pytest tests/` both clean before pushing. The Stop hook
   enforces this at turn end, but running it explicitly avoids the
   surprise.
5. **Adversarial review.** Spawn (or self-run as) the
   `adversarial-reviewer` agent against the commit SHA, briefing it
   with the local `prompt-<slug>.md`. Address every MUST-FIX; address
   SHOULD-FIX unless there's a stated reason to defer; NITs are
   optional. Amend the commit rather than layering fixups.
6. **Push and open the PR** with `gh pr create`. PR body describes
   what you verified in prose, not as an unchecked checklist. The
   PR body IS the historical record — inline anything from the
   prompt that a future reader would want to know.
7. **Poll CI to green.** See "After Opening a PR" below. **This step is
   part of the sprint loop, not optional.** A PR that lands with a red
   check is not a merged sprint.
8. **Wait for merge.** Same `scripts/watch-pr.sh` invocation covers
   this phase.
9. **Next sprint** starts only after `main` has moved forward.
   Delete the local `prompt-<slug>.md` (or leave it — it's ignored).

### Parallel sprints via worktrees (optional)

For work that can proceed in parallel with an open PR, use sibling
worktrees rather than stashing/checkout-swapping in place:

```bash
scripts/worktree-new.sh <slug>          # -> ../<repo>-<slug>/ on feat/<slug>
# … work in that worktree, open its PR …
scripts/worktree-drop.sh <slug>         # after the PR merges
```

`worktree-new.sh` creates the sibling, branches from the current tip
of `main`, and runs `uv sync --group dev` so tests can run immediately.
`worktree-drop.sh` removes the sibling and force-deletes its branch
(squash-merge means `-d` would refuse). Neither script fetches or
pulls — do that in the main worktree first.

## After Opening a PR

- **CI polling is a required step of the sprint loop, not a nice-to-have.**
  Every PR must reach `CI_PASS` before its sprint counts as merged.
  If a check goes red: pull the failure detail, fix the root cause,
  push, and keep watching until every check is green.
- After `gh pr create`, watch the PR to green (and, unless `--ci-only`,
  to merge) with the standard poller:

    ```bash
    scripts/watch-pr.sh <pr-number>
    ```

    The script polls `gh pr checks` every 20s and `gh pr view` every 30s.
    It emits machine-readable markers — `CI_PASS`, `CI_FAIL`,
    `MERGED <iso-timestamp>`, `CLOSED` — that other agents grep for.

    Exit codes (the actual machine interface):

    - `0` — CI green and (unless `--ci-only`) PR merged.
    - `1` — PR closed without merging, or (with `--ci-only`) PR closed
      before CI turned green.
    - `2` — usage error, non-numeric PR number, or the PR does not exist.

- If any check fails, pull the failure detail (e.g. PR comments via
  `gh api repos/<owner>/<repo>/issues/<num>/comments`), fix the issue,
  push. The script picks up the re-run automatically; no restart needed.
- Prefer `ScheduleWakeup` over tight polling in agent turns so the
  conversation context isn't burned waiting on the runner.

## Linting

- Pre-commit is installed. Run `uv run pre-commit run --all-files` to
  reproduce CI locally.
- A Stop hook runs `pre-commit run --all-files` automatically — Claude
  cannot end a turn while linters are unhappy.
- A PostToolUse hook runs `ruff format` + `ruff check --fix` on any
  `.py` file just edited.
- **`typing.Any` is banned in this repo** — see
  `docs/policies/no-any.md`. Ruff rejects both `Any` in annotations
  (`ANN401`) and the import itself (`flake8-tidy-imports` banned-api),
  so the Stop hook will fail any turn that reintroduces it.

## Local/CI parity

The Stop hook also runs the same pytest invocations that CI runs in
`.github/workflows/test.yml`, so a turn cannot end in a state CI would
reject:

- `uv run pytest tests/` — the `Repository Standards` suite (asserts
  license, python version, presence of key config files).
- `bash scripts/local-ci/run-subproject-tests.sh` — iterates each
  member listed in the root pyproject's `[tool.uv.workspace].members`
  (currently none) and runs `uv run pytest` in each one that has a
  `tests/` directory. This mirrors the `Test Subprojects` CI matrix.

To run them manually before a push (the same commands the hook runs):

```bash
uv run pytest tests/
bash scripts/local-ci/run-subproject-tests.sh
```

Hook config is cached at session start, so edits to
`.claude/settings.json` only take effect in a new Claude Code session.
