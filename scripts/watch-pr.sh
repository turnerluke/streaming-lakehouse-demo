#!/usr/bin/env bash
# watch-pr.sh — poll a PR's CI checks (re-run aware) then its merge state.
#
# Standard PR poller for this repo. Used by orchestrator agents and
# humans alike to babysit a PR from `gh pr create` to merge without
# either burning a session on tight polling or missing a re-triggered
# check when CI is fixed and re-run.
#
# Machine-readable final lines (the contract other agents grep for):
#
#     CI_PASS                 all checks green
#     CI_FAIL                 at least one check failing right now
#     MERGED <ISO-timestamp>  PR merged
#     CLOSED                  PR closed without merging
#
# `--ci-only` exits 0 on green CI, 1 if the PR closes/merges before CI
# is green.
#
# Setting `WATCH_PR_LIB_ONLY=1` before sourcing this file defines the
# helper functions and returns immediately, without parsing args or
# entering the poll loop. Used by the pytest suite.
set -euo pipefail

# Polling intervals (seconds). Assigned only if unset so a second
# `source` of this file in the same shell (a plausible test-suite or
# debug pattern) doesn't crash under `set -e` on a readonly conflict.
: "${CI_POLL_INTERVAL:=20}"
: "${MERGE_POLL_INTERVAL:=30}"

usage() {
    cat <<'EOF'
Usage: scripts/watch-pr.sh <pr-number> [--ci-only]

Polls PR <pr-number> until its CI is fully green (or the PR closes)
and, unless --ci-only is given, then polls until the PR is merged or
closed.

CI phase:
  - polls `gh pr checks <pr-number>` every 20s until no check is
    pending/queued/in_progress and at least one check is reported,
  - treats `pass` and `skipping` as OK,
  - on any failure, prints the failing check lines and `CI_FAIL`, then
    loops back into the pending-wait phase so a fix-push that
    re-triggers CI is picked up automatically,
  - exits the CI phase when either every check is OK (prints `CI_PASS`)
    or the PR is no longer OPEN.

Merge phase (skipped with --ci-only):
  - polls `gh pr view <pr-number> --json state` every 30s until state
    is no longer OPEN,
  - prints `MERGED <mergedAt>` or `CLOSED`.

Exit codes:
  0  CI green (and, without --ci-only, PR merged)
  1  PR closed without merging, or --ci-only and PR closed before green
  2  usage error / nonexistent PR / non-numeric argument

Examples:
  scripts/watch-pr.sh 123
  scripts/watch-pr.sh 123 --ci-only
EOF
}

# ---- helper functions (kept above the CLI so lib-only sourcing works) ----

# Print any check lines whose status column isn't `pass` or `skipping`.
# `gh pr checks` output is tab-separated: name<TAB>status<TAB>duration<TAB>url.
# Using awk on the status column avoids a substring-grep bug: a check
# named `bypass-something` would match a plain `grep -v pass`.
print_failing_checks() {
    local raw="$1"
    awk -F'\t' '$2 != "pass" && $2 != "skipping" { print }' <<<"$raw"
}

# A stable fingerprint of the failing-check set (sorted names only) so we
# can skip re-reporting an identical `CI_FAIL` while waiting on a human
# to push a fix. We ignore the status/duration/url columns so a check
# flipping from `fail` to `cancelled` still counts as the same failure
# report; a genuinely new failing name changes the fingerprint.
failing_fingerprint() {
    local raw="$1"
    awk -F'\t' '$2 != "pass" && $2 != "skipping" { print $1 }' <<<"$raw" |
        LC_ALL=C sort -u |
        tr '\n' '|'
}

# True (returns 0) if no check is still running.
all_settled() {
    local raw="$1"
    ! awk -F'\t' '$2 == "pending" || $2 == "queued" || $2 == "in_progress" { found=1 } END { exit !found }' <<<"$raw"
}

# True (returns 0) if every check line's status is `pass` or `skipping`.
all_ok() {
    local raw="$1"
    awk -F'\t' '$2 != "pass" && $2 != "skipping" { bad=1 } END { exit bad ? 1 : 0 }' <<<"$raw"
}

# ---- lib-only exit point (tests source this and stop here) ----
if [[ "${WATCH_PR_LIB_ONLY:-0}" == "1" ]]; then
    # The `return` succeeds when this file is sourced (the tests' path);
    # falls through to `exit` when someone runs it directly with the
    # var set. shellcheck can't tell they're mutually reachable.
    # shellcheck disable=SC2317
    return 0 2>/dev/null || exit 0
fi

# ---- argument parsing ----
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

pr="$1"
ci_only=0
if [[ $# -eq 2 ]]; then
    if [[ "$2" != "--ci-only" ]]; then
        usage >&2
        exit 2
    fi
    ci_only=1
fi

if ! [[ "$pr" =~ ^[0-9]+$ ]]; then
    echo "watch-pr.sh: <pr-number> must be numeric (got: $pr)" >&2
    exit 2
fi

# Sanity-check that the PR exists before entering a polling loop.
# `gh pr view` needs at least one field that actually resolves the PR
# (bare `number` is echoed back without a lookup); asking for `state`
# forces the GraphQL fetch and surfaces a clear error for missing PRs.
probe_err="$(mktemp -t watch-pr.XXXXXX)"
trap 'rm -f "$probe_err"' EXIT
if ! gh pr view "$pr" --json number,state >/dev/null 2>"$probe_err"; then
    echo "watch-pr.sh: cannot access PR #$pr" >&2
    cat "$probe_err" >&2
    exit 2
fi

pr_state() {
    gh pr view "$pr" --json state -q .state 2>/dev/null || true
}

pr_merged_at() {
    gh pr view "$pr" --json mergedAt -q '.mergedAt // ""' 2>/dev/null || true
}

# Fetch check status. `gh pr checks` exits nonzero when any check has
# failed, so guard with `|| true` under `set -e`.
fetch_checks() {
    gh pr checks "$pr" 2>/dev/null || true
}

echo "==> watching PR #$pr CI (poll every ${CI_POLL_INTERVAL}s)" >&2

ci_result=""       # "pass" | "fail_closed"
last_failing_fp="" # fingerprint of the last CI_FAIL set we printed
while :; do
    raw="$(fetch_checks)"

    if [[ -z "$raw" ]] || ! all_settled "$raw"; then
        # A re-run has kicked off (something is pending again), so a
        # subsequent failure with the same check names is a fresh
        # result the orchestrator needs to see. Clear the dedup memory.
        last_failing_fp=""
        # Bail out if the PR closed while we were waiting on CI.
        state="$(pr_state)"
        if [[ -n "$state" && "$state" != "OPEN" ]]; then
            echo "==> PR #$pr is $state; leaving CI phase" >&2
            ci_result="fail_closed"
            break
        fi
        sleep "$CI_POLL_INTERVAL"
        continue
    fi

    if all_ok "$raw"; then
        echo "CI_PASS"
        ci_result="pass"
        break
    fi

    # At least one check failed. Report it once per distinct failing
    # set, then loop back so a fix-push that re-triggers CI is naturally
    # picked up.
    fp="$(failing_fingerprint "$raw")"
    if [[ "$fp" != "$last_failing_fp" ]]; then
        echo "==> PR #$pr CI failing:" >&2
        print_failing_checks "$raw"
        echo "CI_FAIL"
        last_failing_fp="$fp"
    fi

    state="$(pr_state)"
    if [[ -n "$state" && "$state" != "OPEN" ]]; then
        echo "==> PR #$pr is $state; leaving CI phase" >&2
        ci_result="fail_closed"
        break
    fi

    echo "==> waiting for re-run (poll every ${CI_POLL_INTERVAL}s)" >&2
    sleep "$CI_POLL_INTERVAL"
done

if [[ "$ci_only" -eq 1 ]]; then
    if [[ "$ci_result" == "pass" ]]; then
        exit 0
    fi
    exit 1
fi

if [[ "$ci_result" != "pass" ]]; then
    # PR already closed. Report which flavour and exit.
    state="$(pr_state)"
    if [[ "$state" == "MERGED" ]]; then
        merged_at="$(pr_merged_at)"
        echo "MERGED ${merged_at:-unknown}"
        exit 0
    fi
    echo "CLOSED"
    exit 1
fi

echo "==> watching PR #$pr merge state (poll every ${MERGE_POLL_INTERVAL}s)" >&2
while :; do
    state="$(pr_state)"
    if [[ -z "$state" ]]; then
        sleep "$MERGE_POLL_INTERVAL"
        continue
    fi
    if [[ "$state" == "OPEN" ]]; then
        sleep "$MERGE_POLL_INTERVAL"
        continue
    fi
    if [[ "$state" == "MERGED" ]]; then
        merged_at="$(pr_merged_at)"
        echo "MERGED ${merged_at:-unknown}"
        exit 0
    fi
    echo "CLOSED"
    exit 1
done
