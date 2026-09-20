# Review instructions

These instructions apply when reviewing pull requests. They take precedence
over CLAUDE.md when they conflict. CLAUDE.md still applies as project
context.

## What to flag as Important

- Correctness bugs that would break behavior in production
- Mutable default arguments
- Race conditions, off-by-ones, unhandled edge cases
- Misuse of stdlib or third-party APIs
- Any `# noqa`, `# type: ignore`, `# pragma: no cover`, or similar
  suppression. Always flag these. Demand justification in a comment on the
  same line, and verify the suppression is the narrowest possible scope
  (specific rule code, not blanket).
- Out-of-scope changes to repo standards, linting config, formatter config,
  pre-commit hooks, CI/CD workflows, or dependency pinning when the PR is
  not specifically about that change. Flag with a request to split into a
  separate PR.

## What to flag as Nit

- Non-Pythonic patterns where a comprehension or builtin fits better
- Unclear variable names in non-trivial functions
- Deep nesting where early returns would help
- Functions doing too much; opportunities to extract a helper
- Repeated logic that should be DRY'd
- Magic numbers or strings that should be named constants
- Tests that assert on implementation details rather than behavior

## Test coverage

- New public functions or methods must have tests. Flag as Important if missing.
- New branches in existing functions should have a test exercising the new
  branch. Flag as Important if missing.
- Bug fixes should include a regression test that fails without the fix.
  Flag as Important if missing.
- Tests that don't actually assert anything meaningful (just that code runs)
  should be flagged.

## Types

- Flag `Any` outside of explicitly justified cases (`docs/policies/no-any.md`).
- Flag overly broad types (`dict`, `list` without parameters; `object`
  instead of a `Protocol`).
- Flag `cast()` usage without a comment explaining why the type system
  can't see it.

## Data-pipeline-specific

- dbt models: flag missing `not_null` / `unique` tests on grain columns.
- dbt models: flag `select *` in downstream models (except thin passthroughs).
- SQL: flag implicit CROSS JOINs, `SELECT DISTINCT` used to paper over a
  missing join key, and window functions without an explicit `PARTITION BY`.
- Streaming code: flag missing consumer offset commits, unbounded in-memory
  state, and blocking calls inside a poll loop.
- Terraform: flag any resource without an explicit `location`/`region`, or
  IAM bindings broader than the pipeline needs.

## What to skip

- Anything ruff or the type checker would catch — assume those run separately
- Missing docstrings on private or internal helpers
- Style preferences already covered by CLAUDE.md
- Generated files, lockfiles, anything under `.venv/` or `__pycache__/`

## Volume

- This is a high-quality-bar repo. Flag every issue you find at the
  appropriate severity. Do not cap or summarize away nits.

## Verification

- Don't flag based on inference from naming alone — read the relevant code
  to confirm the issue actually exists.
- For claims about behavior, cite the specific file:line you're reasoning
  from.
- For suppressions and out-of-scope changes, quote the exact line.
