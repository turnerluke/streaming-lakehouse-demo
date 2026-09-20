# Prompt: Sprint 01 — Align repo standards with `cms-open-data`

## Why now

This repo was born from a green scaffold. Before any real feature work
(producer/consumer wiring, dbt models, cloud provisioning) lands, the
tooling, lint config, CI, and agent-facing docs need to match the
`cms-open-data` conventions so future PRs don't get bogged down in
tab-vs-space arguments or reviewers rediscovering the same rules.

Nothing in this sprint changes runtime behavior. It's pure repo hygiene.

## Goal

A fresh clone of `streaming-lakehouse-demo` should feel indistinguishable
from `cms-open-data` in terms of:

- Lint stack (pre-commit + ruff + gitlint + commitlint + yamllint +
  markdownlint + prettier + shellcheck).
- CI (`lint.yml` per-linter parallel jobs, `test.yml` matrix, PR-title
  validation, Dependabot, CODEOWNERS).
- Agent contract (`AGENTS.md`, `CLAUDE.md`, `REVIEW.md`,
  `docs/policies/no-any.md`, `.claude/settings.json` with a Stop hook that
  enforces pre-commit + pytest before turn end).
- Sprint pattern: every future increment lands as one focused PR driven
  by a `prompt-NN-<slug>.md` at the repo root, following this file's
  structure (Why now / Goal / Approach / Files / Verification / Out of
  scope / Gotchas).

## Approach

Single `chore:` PR. Branch from `main`:

```bash
git checkout main && git pull --ff-only
git checkout -b chore/repo-standards-alignment
```

1. Port `cms-open-data`'s lint configs verbatim where they're
   repo-agnostic (`.gitlint.yaml`, `.markdownlint.yml`, `.yamllint.yml`,
   `.prettierrc.cjs`, `.hadolint.yaml`, `.commitlintrc.cjs`), tweaking
   only the `known-first-party` in `ruff.toml`.
2. Adopt the same pyproject shape: `requires-python = ">=3.13"`,
   `[dependency-groups]` (not the deprecated `[project.optional-dependencies]`),
   MIT license, project URLs, `[tool.pytest.ini_options]` with strict
   markers. Add `.python-version`.
3. `.pre-commit-config.yaml` matches the cms hook list. The dbt sources
   generator hook is dropped (no registry to regenerate yet); the sqlfluff
   local hook is retained but scoped to `dbt/models/**/*.sql`.
4. GitHub Actions: replace the placeholder `ci.yml` with
   `.github/workflows/lint.yml` (per-linter jobs, PR title validation,
   artifact upload on failure) and `.github/workflows/test.yml`
   (repo-standards + subproject matrix). Consolidated PR-comment reporter
   is **out of scope** — see below.
5. Agent docs: `AGENTS.md` is a lightly-edited copy of the cms one
   (Ralph and registry-driven paragraphs replaced with content that
   applies here). `CLAUDE.md` is a one-line `@AGENTS.md`. `REVIEW.md`
   ports the review posture. `docs/policies/no-any.md` documents the
   `typing.Any` ban and is referenced from `ruff.toml`.
6. `.claude/settings.json` gets the PostToolUse ruff hook and the Stop
   hook that runs `pre-commit run --all-files` and `pytest tests/`.
   The `run-subproject-tests.sh` script is included as a stub for when
   workspace members are added.
7. `tests/test_repo_standards.py` asserts the invariants: LICENSE
   present, MIT declared, `requires-python == ">=3.13"`, `AGENTS.md` +
   `CLAUDE.md` + `ruff.toml` + `.pre-commit-config.yaml` present.
   This is the load-bearing backstop against future drift.
8. `.github/CODEOWNERS` + `.github/dependabot.yml` copied and re-scoped.

## Files

| | Path |
|---|---|
| ADD | `AGENTS.md` |
| ADD | `CLAUDE.md` |
| ADD | `REVIEW.md` |
| ADD | `LICENSE` |
| ADD | `ruff.toml` |
| ADD | `.commitlintrc.cjs` |
| ADD | `.gitlint.yaml` |
| ADD | `.markdownlint.yml` |
| ADD | `.markdownlintignore` |
| ADD | `.yamllint.yml` |
| ADD | `.prettierrc.cjs` |
| ADD | `.prettierignore` |
| ADD | `.hadolint.yaml` |
| ADD | `.python-version` |
| ADD | `package.json` |
| ADD | `docs/policies/no-any.md` |
| ADD | `.github/CODEOWNERS` |
| ADD | `.github/dependabot.yml` |
| ADD | `.github/workflows/lint.yml` |
| ADD | `.github/workflows/test.yml` |
| ADD | `.claude/settings.json` |
| ADD | `.claude/agents/adversarial-reviewer.md` |
| ADD | `.claude/agents/implementer.md` |
| ADD | `scripts/local-ci/run-subproject-tests.sh` |
| ADD | `tests/__init__.py` |
| ADD | `tests/test_repo_standards.py` |
| EDIT | `pyproject.toml` (py3.13, dep-groups, MIT, pytest config) |
| EDIT | `.pre-commit-config.yaml` (full cms-style hook list) |
| EDIT | `.gitignore` (broaden coverage) |
| EDIT | `README.md` (link `AGENTS.md`, drop the "scaffold" caveat once green) |
| DELETE | `.github/workflows/ci.yml` (superseded by `lint.yml` + `test.yml`) |
| DELETE | `.sqlfluff` (moved into `dbt/` scope; sqlfluff-templater-dbt takes over) |

## Verification

```bash
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest tests/
```

- All hooks pass.
- Repo-standards test passes (proves the invariants hold).
- `gh workflow list` shows exactly `Code Quality Check` and `Test`;
  no dangling `ci` workflow.
- The PR title itself passes `commitlint` (starts with lowercase
  `chore:`).

## Out of scope

- The consolidated `lint_report` PR-comment job from cms-open-data
  (`.github/workflows/lint.yml` lines ~500-707). Complex, low-value at
  this repo's current scale. Follow-up sprint if the raw-artifact UX
  becomes annoying.
- `warehouse.yml` — the CMS pipeline runner has no analog here yet.
  A `pipeline.yml` will land in a later sprint when the producer +
  consumer are wired end-to-end.
- Splitting into a `uv workspace` (like `dbt/cms_analytics`,
  `dagster/cms_pipelines`, `libs/cms_api`). Deferred until there's a
  second Python subproject that warrants it.
- `claude-review.yml` — the automated Claude PR reviewer workflow is
  personal preference; leave it to a later sprint if wanted.
- Ralph loop tooling — no autonomous work planned for this repo yet.

## Gotchas

- `commitlint` will reject **this** sprint's own PR title unless it's
  lowercase after the type. Use `chore: align repo standards with
  cms-open-data`, not `Chore: …`.
- `interrogate` (docstring coverage) will fail loudly on the current
  `producer/` and `consumer/` modules if their module docstrings are
  missing. They already have them; keep them.
- The `.claude/settings.json` Stop hook cache is baked at session start.
  After adding it, **start a new Claude Code session** or subsequent
  turns will still end without the hook enforcement.
- `ruff.toml`'s `select = ["ALL"]` will surface a wave of findings on
  the existing producer/consumer code. Auto-fix what auto-fixes; for
  the rest, either address in this same PR or add narrow `# noqa: <RULE>`
  with a one-line justification. Do **not** disable rules globally to
  make the initial run green — that defeats the point.
- `sqlfluff` under `dbt-templater` needs a `dbt/profiles.yml` present
  even for offline linting. Point the pre-commit hook at a stub profile
  (env vars unset → dbt-bigquery will still parse), or scope sqlfluff to
  templater `jinja` for the pre-CI hook and let `dbt` templating validate
  in the future `pipeline.yml`.
