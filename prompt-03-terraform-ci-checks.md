# Prompt: Sprint 03 — Terraform CI checks

## Why now

Sprint 01 landed a `terraform/` module (BigQuery datasets, IAM,
service-account key). Nothing in CI touches it, so a broken `.tf` file
would silently ship and only get caught the next time someone ran
`terraform apply` — the worst possible place to find out. Two mechanical
checks (`terraform fmt -check` and `terraform validate`) catch >90% of
those failures in seconds.

Depends on `test/pipeline-unit-tests` (sprint 02) being merged.

## Goal

Every PR that touches `terraform/**` fails CI when the HCL is
unformatted or fails `validate`. Zero-cost — neither check hits a real
GCP project.

## Approach

Single `ci:` PR. Branch from `main`:

```bash
git checkout main && git pull --ff-only
git checkout -b ci/terraform-checks
```

1. Add `.github/workflows/pipeline-checks.yml` — one workflow, two jobs
   scoped to `terraform/**`: `terraform-fmt` and `terraform-validate`.
   Both use `hashicorp/setup-terraform@v3`. Skip both when the PR
   doesn't touch `terraform/**` (via `tj-actions/changed-files`).
2. Fix the two latent issues in `terraform/main.tf` while here — they
   *are* the "would break validate" cases and dropping them lets the
   new job pass on first run:
    - `local_file` used without `hashicorp/local` in
      `required_providers` — `validate` catches this.
    - `outputs.tf` had a mix of inline-block and multi-line `output`
      declarations — `fmt` normalizes to multi-line. Reformat.
3. No pre-commit hook for terraform in this sprint. The `hashicorp/terraform`
   pre-commit repo works, but running the terraform CLI from every
   pre-commit invocation is slow enough to noticeably annoy contributors
   who never touch `.tf`. Reconsider once we have >1 module.

## Files

| | Path |
|---|---|
| ADD | `.github/workflows/pipeline-checks.yml` |
| EDIT | `terraform/main.tf` (add `hashicorp/local` provider) |
| EDIT | `terraform/outputs.tf` (canonical `terraform fmt` layout) |

## Verification

Local:

```bash
uv run pre-commit run --all-files
uv run pytest tests/
```

If terraform is installed locally:

```bash
cd terraform && terraform init -backend=false && terraform validate && terraform fmt -check
```

CI verification: after opening the PR, the `terraform-fmt` and
`terraform-validate` jobs report green.

## Out of scope

- Running `tflint` / `tfsec` / `checkov` — nice to have, adds two more
  jobs and a config file each. Separate sprint once we start caring
  about IAM-scope regressions.
- Adding a pre-commit hook for terraform (see approach note above).
- Splitting the workflow into a matrix over multiple modules — we have
  one.
- Any change to what the terraform actually provisions.

## Gotchas

- `terraform validate` on a Google-provider config does NOT require GCP
  credentials, but it DOES require `terraform init -backend=false`
  first to fetch the provider plugins. The workflow must do that init
  step before `validate`.
- `hashicorp/setup-terraform@v3` sets a wrapper that intercepts
  `terraform` calls and can mangle multi-line outputs. Use
  `terraform_wrapper: false` so `validate` output is readable in the
  Actions log.
- `terraform fmt -check` returns non-zero on any drift, which is the
  point — no `continue-on-error`.
