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

- Every incremental piece of work is scoped by a `prompt-NN-<slug>.md`
  file at the repo root. It captures: **Why now**, **Goal**, **Approach**,
  **Files** (add/edit/delete table), **Verification**, **Out of scope**,
  **Gotchas**.
- One prompt = one PR. When the PR merges, the prompt file stays in
  `main` as the historical record. Follow-up work gets a new prompt file
  with the next number.
- New prompts must state their dependency on any open PR and wait for
  that PR to merge before branching (never stack).

## After Opening a PR

- **Do not stop the turn until CI is green.** After `gh pr create`, poll
  `gh pr checks <num>` until every check has finished. If any check fails,
  pull the failure detail (e.g. PR comments via
  `gh api repos/<owner>/<repo>/issues/<num>/comments`), fix the issue, push,
  and re-poll. Only report the PR as done when all required checks pass.
- Prefer `ScheduleWakeup` over tight polling so the conversation context
  isn't burned waiting on the runner.

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
