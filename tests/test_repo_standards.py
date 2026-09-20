"""Repository-standards invariants.

These tests are the load-bearing backstop against config drift. Whenever the
repo grows, the invariants asserted here — MIT license, py3.13 pin, presence
of AGENTS.md / CLAUDE.md / ruff.toml / pre-commit config — should hold.
"""

from __future__ import annotations

from pathlib import Path
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject(path: Path) -> dict[str, object]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def test_license_file_is_present() -> None:
    """A `LICENSE` file must exist at the repo root."""
    assert (REPO_ROOT / "LICENSE").is_file(), "LICENSE file missing at repo root"


def test_pyproject_declares_mit() -> None:
    """`pyproject.toml` declares the MIT license and points at `LICENSE`."""
    data = _load_pyproject(REPO_ROOT / "pyproject.toml")
    project = data["project"]
    assert isinstance(project, dict)
    assert project.get("license") == "MIT", "project.license must be MIT"
    assert project.get("license-files") == ["LICENSE"], "project.license-files must be [LICENSE]"


def test_pyproject_pins_python_313() -> None:
    """The whole repo runs on Python 3.13; enforce the pin here."""
    data = _load_pyproject(REPO_ROOT / "pyproject.toml")
    project = data["project"]
    assert isinstance(project, dict)
    assert project.get("requires-python") == ">=3.13"


def test_pyproject_has_authors_and_urls() -> None:
    """Portfolio metadata must not silently drop off."""
    data = _load_pyproject(REPO_ROOT / "pyproject.toml")
    project = data["project"]
    assert isinstance(project, dict)
    authors = project.get("authors") or []
    assert authors, "project.authors must not be empty"
    urls = project.get("urls") or {}
    assert isinstance(urls, dict)
    assert "Repository" in urls, "project.urls.Repository must be set"


def test_python_version_file_matches_pyproject() -> None:
    """`.python-version` must match the pyproject pin."""
    pin = (REPO_ROOT / ".python-version").read_text().strip()
    assert pin.startswith("3.13"), f".python-version drift: {pin!r}"


def test_convention_files_present() -> None:
    """The agent contract and lint configs must exist."""
    required = [
        "AGENTS.md",
        "CLAUDE.md",
        "REVIEW.md",
        "ruff.toml",
        ".pre-commit-config.yaml",
        ".commitlintrc.cjs",
        ".gitlint.yaml",
        ".markdownlint.yml",
        ".yamllint.yml",
        ".prettierrc.cjs",
        ".github/CODEOWNERS",
        ".github/dependabot.yml",
        ".github/workflows/lint.yml",
        ".github/workflows/test.yml",
        "docs/policies/no-any.md",
    ]
    missing = [p for p in required if not (REPO_ROOT / p).exists()]
    assert not missing, f"missing convention files: {missing}"


def test_no_ci_workflow_leftover() -> None:
    """The old `ci.yml` was superseded by lint.yml + test.yml."""
    assert not (REPO_ROOT / ".github" / "workflows" / "ci.yml").exists()


def test_ruff_bans_typing_any() -> None:
    """`ruff.toml` must ban `typing.Any` via flake8-tidy-imports.banned-api."""
    ruff = (REPO_ROOT / "ruff.toml").read_text()
    assert "[lint.flake8-tidy-imports.banned-api]" in ruff
    assert '"typing.Any"' in ruff


def test_ruff_selects_all() -> None:
    """`ruff.toml` must opt into the full ruleset."""
    data = tomllib.loads((REPO_ROOT / "ruff.toml").read_text())
    lint = data.get("lint", {})
    assert isinstance(lint, dict)
    assert lint.get("select") == ["ALL"]
