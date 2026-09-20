"""Regression tests for the awk helpers inside `scripts/watch-pr.sh`.

We invoke each helper by sourcing the script under a guarded top-level
(the script returns immediately when `WATCH_PR_LIB_ONLY=1`) so the
helpers are loadable without executing the poll loop, then exercise
them against synthetic `gh pr checks` fixtures.
"""

from __future__ import annotations

from pathlib import Path
import subprocess


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "watch-pr.sh"


def _call(helper: str, fixture: str) -> subprocess.CompletedProcess[str]:
    """Source the script in lib-only mode, run `helper` on `fixture`, return the process."""
    snippet = f'WATCH_PR_LIB_ONLY=1 source "{SCRIPT}"; {helper} "$1"'
    return subprocess.run(  # noqa: S603 (fixed bash cmd, fixture is inline literal)
        ["/bin/bash", "-c", snippet, "_", fixture],
        capture_output=True,
        text=True,
        check=False,
    )


# Fixtures use raw multi-line strings so `ruff` FLY002 doesn't push us
# toward f-strings for what is really tab-delimited data.
PASS_FIXTURE = "ruff\tpass\t1m\nmarkdownlint\tpass\t30s\ntest\tpass\t2m"

MIXED_IN_PROGRESS = "ruff\tpass\t1m\nmarkdownlint\tfail\t30s\ntest\tin_progress\t-"

MIXED_PENDING = "ruff\tpass\t1m\ntest\tpending\t-"

MIXED_QUEUED = "ruff\tpass\t1m\ntest\tqueued\t-"

FAILED_FIXTURE = "ruff\tpass\t1m\nmarkdownlint\tfail\t30s\ntest\tfail\t2m"

SKIPPING_FIXTURE = "ruff\tpass\t1m\nmarkdownlint\tskipping\t0s"


# ---------- all_settled ----------


def test_all_settled_true_when_no_running_check() -> None:
    """No pending/queued/in_progress rows -> success (exit 0)."""
    assert _call("all_settled", PASS_FIXTURE).returncode == 0
    assert _call("all_settled", FAILED_FIXTURE).returncode == 0
    assert _call("all_settled", SKIPPING_FIXTURE).returncode == 0


def test_all_settled_false_for_each_running_status() -> None:
    """`pending`, `queued`, and `in_progress` each individually block settlement."""
    assert _call("all_settled", MIXED_PENDING).returncode != 0
    assert _call("all_settled", MIXED_QUEUED).returncode != 0
    assert _call("all_settled", MIXED_IN_PROGRESS).returncode != 0


def test_all_settled_empty_input_is_settled() -> None:
    """Empty input has no running rows and returns 0 (the caller distinguishes empty from settled)."""
    assert _call("all_settled", "").returncode == 0


# ---------- all_ok ----------


def test_all_ok_true_only_when_every_check_pass_or_skipping() -> None:
    """`pass` + `skipping` count as OK; anything else flips it."""
    assert _call("all_ok", PASS_FIXTURE).returncode == 0
    assert _call("all_ok", SKIPPING_FIXTURE).returncode == 0
    assert _call("all_ok", FAILED_FIXTURE).returncode != 0


def test_all_ok_treats_pending_as_not_ok() -> None:
    """A still-running check must not slip past `all_ok`."""
    assert _call("all_ok", MIXED_PENDING).returncode != 0


def test_all_ok_empty_input_is_not_ok() -> None:
    """Empty input is treated as "not OK" (safer default).

    A here-string of `""` presents awk with one empty record whose
    second field is empty — neither `pass` nor `skipping` — so the
    awk sets `bad=1` and returns 1. The poll loop pre-filters empty
    input via `[[ -z "$raw" ]]` before ever calling `all_ok`, so
    callers never observe the "empty means ok" false-positive.
    """
    assert _call("all_ok", "").returncode != 0


# ---------- print_failing_checks ----------


def test_print_failing_checks_lists_only_the_failures() -> None:
    """Every non-pass/non-skipping line is echoed; passers are dropped."""
    result = _call("print_failing_checks", FAILED_FIXTURE)
    assert result.returncode == 0
    lines = [line for line in result.stdout.splitlines() if line]
    assert len(lines) == 2
    assert all("fail" in line for line in lines)
    assert not any(line.startswith("ruff") for line in lines)


def test_print_failing_checks_does_not_match_pass_substrings() -> None:
    """A check whose NAME starts with `pass` must still be printed if it failed.

    Guards against the substring-grep bug the awk column-match was
    written to avoid.
    """
    fixture = "passport-check\tfail\t1s\nruff\tpass\t2s"
    result = _call("print_failing_checks", fixture)
    lines = [line for line in result.stdout.splitlines() if line]
    assert len(lines) == 1
    assert lines[0].startswith("passport-check")


def test_print_failing_checks_empty_input_yields_no_output() -> None:
    """Nothing in, nothing out."""
    result = _call("print_failing_checks", "")
    assert result.stdout.strip() == ""


# ---------- failing_fingerprint ----------


def test_failing_fingerprint_is_stable_under_status_flips() -> None:
    """A check flipping fail->cancelled keeps the same fingerprint (name-based)."""
    a = "markdownlint\tfail\t30s"
    b = "markdownlint\tcancelled\t30s"
    fp_a = _call("failing_fingerprint", a).stdout
    fp_b = _call("failing_fingerprint", b).stdout
    assert fp_a == fp_b
    assert fp_a.strip("|") == "markdownlint"


def test_failing_fingerprint_changes_when_the_set_changes() -> None:
    """A new failing name produces a distinct fingerprint."""
    fp_one = _call("failing_fingerprint", "a\tfail\t1s").stdout
    fp_two = _call("failing_fingerprint", "a\tfail\t1s\nb\tfail\t1s").stdout
    assert fp_one != fp_two


def test_failing_fingerprint_sorts_check_names() -> None:
    """Order of failing checks in input must not change the fingerprint."""
    fp_ab = _call("failing_fingerprint", "a\tfail\t1s\nb\tfail\t2s").stdout
    fp_ba = _call("failing_fingerprint", "b\tfail\t2s\na\tfail\t1s").stdout
    assert fp_ab == fp_ba


def test_failing_fingerprint_empty_input_is_distinct_from_any_real_set() -> None:
    r"""Empty input yields a fingerprint that doesn't collide with a real one.

    The here-string of `""` produces one empty awk record whose empty
    `$1` is printed and joined via `tr '\n' '|'` -> literal `|`.
    Callers compare fingerprints for equality; they don't parse them.
    All that matters is empty-input's fingerprint differs from any set
    of real check names.
    """
    empty_fp = _call("failing_fingerprint", "").stdout
    real_fp = _call("failing_fingerprint", "a\tfail\t1s").stdout
    assert empty_fp != real_fp


# ---------- lib-only sourcing sanity ----------


def test_script_re_sourceable_in_same_shell() -> None:
    """Sourcing the lib twice must not blow up on `readonly` reassignment."""
    snippet = (
        f'WATCH_PR_LIB_ONLY=1 source "{SCRIPT}"; '
        f'WATCH_PR_LIB_ONLY=1 source "{SCRIPT}"; '
        f"echo ok"
    )
    result = subprocess.run(  # noqa: S603 (fixed bash cmd, no external input)
        ["/bin/bash", "-c", snippet],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
