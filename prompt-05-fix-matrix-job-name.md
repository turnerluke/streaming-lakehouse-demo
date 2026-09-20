# Prompt: Sprint 05 — Fix empty-matrix job name in `test.yml`

## Why now

Every PR since sprint 01 has been showing a check named literally
``Test ${{ matrix.subproject }}`` — the raw workflow-expression string.
This happens because `.github/workflows/test.yml` sets

```yaml
name: Test ${{ matrix.subproject }}
```

on the matrix job, but the matrix is currently empty (there are no
workspace members with `tests/` yet). GitHub resolves check names at
plan time; with an empty matrix there's no `subproject` to interpolate,
so the template is emitted verbatim.

Small, visible UX bug. Trivial fix.

Depends on `feat/watch-pr-script` (sprint 04) being merged — done.

## Goal

Every PR shows a legible check name for the subproject-matrix job,
whether the matrix is empty (skipping) or populated. When a workspace
member is eventually added, the check should render as
`Test subproject (dbt/xyz)` via GitHub's automatic matrix suffix.

## Approach

Single `fix:` PR. Branch from `main`:

```bash
git checkout main && git pull --ff-only
git checkout -b fix/matrix-job-name
```

1. In `.github/workflows/test.yml`, change

    ```yaml
    name: Test ${{ matrix.subproject }}
    ```

    to

    ```yaml
    name: Test subproject
    ```

    GitHub's Actions UI auto-appends matrix values in parens
    (`Test subproject (foo)`, `Test subproject (bar)`) when a matrix
    is populated. Static base name means the empty-matrix "skipping"
    entry also renders sensibly.
2. Nothing else. This is a one-line diff.

## Files

| | Path |
|---|---|
| EDIT | `.github/workflows/test.yml` (matrix-job `name:` field) |

## Verification

Local:

```bash
uv run pre-commit run --all-files
uv run pytest tests/
```

Both clean.

CI verification: after opening the PR, the "Test subproject" check
shows `skipping` (until a workspace member exists). Compared with the
tail of PR #7's checks, the literal template is gone.

## Out of scope

- Adding an actual workspace member so the matrix populates. That's a
  future sprint's job.
- Changing how `discover_subprojects` emits the matrix. It works.
- Renaming the job identifier (`test_subprojects`) — that's referenced
  in `if:` guards nowhere else, but renaming just to rename is churn.

## Gotchas

- GitHub Actions expression parsing is strict about YAML types; the
  new `name` must remain a plain string, not accidentally a mapping.
- The `if: needs.discover_subprojects.outputs.any_found == 'true'`
  guard already prevents the matrix job from *running* on an empty
  matrix, but does **not** prevent GitHub from emitting a
  "skipping" check row. The name fix is what makes that row legible.
- No CI job depends on the *display name*, so this cannot break
  downstream tooling.
