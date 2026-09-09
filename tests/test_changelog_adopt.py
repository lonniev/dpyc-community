"""Adopting the fragment convention must not lose anybody's changelog.

`adopt.py` rewrites CHANGELOG.md in twelve repositories at once. The failure
that matters is not a crash — it is a quiet one: a `## [Unreleased]` section
lifted out and only partly written back, in a file nobody re-reads because the
PR title says "chore". Every test here is about content surviving the move.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "adopt", ROOT / "scripts" / "changelog-fragments" / "adopt.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


adopt = _module()

SAMPLE = """# Changelog

Some preamble.

## [Unreleased]

### Added

- A new tool.

### Fixed

- An old bug.

## [1.2.0] - 2026-01-01

### Added

- The thing that shipped.
"""


def test_every_entry_survives_the_move() -> None:
    remaining, groups = adopt.split_unreleased(SAMPLE)
    assert groups["added"].strip() == "- A new tool."
    assert groups["fixed"].strip() == "- An old bug."
    # And the released history is untouched.
    assert "## [1.2.0] - 2026-01-01" in remaining
    assert "- The thing that shipped." in remaining
    assert "Some preamble." in remaining


def test_the_conflict_anchor_is_actually_gone() -> None:
    """Installing the machinery and LEAVING the section is the null change:
    the next two PRs collide on `[Unreleased]` exactly as before."""
    remaining, _ = adopt.split_unreleased(SAMPLE)
    assert "Unreleased" not in remaining


def test_a_repo_with_no_unreleased_section_is_left_alone() -> None:
    text = "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- Shipped.\n"
    remaining, groups = adopt.split_unreleased(text)
    assert remaining == text and groups == {}


def test_running_it_twice_changes_nothing_the_second_time() -> None:
    once, groups = adopt.split_unreleased(SAMPLE)
    assert groups
    twice, again = adopt.split_unreleased(once)
    assert twice == once and again == {}


def test_prose_with_no_heading_is_kept_rather_than_dropped() -> None:
    text = "# Changelog\n\n## [Unreleased]\n\nA note nobody filed under a heading.\n\n## [1.0.0] - 2026-01-01\n"
    _remaining, groups = adopt.split_unreleased(text)
    assert "A note nobody filed under a heading." in groups["notes"]


def test_an_invented_heading_lands_in_notes_rather_than_nowhere() -> None:
    text = "# Changelog\n\n## [Unreleased]\n\n### Housekeeping\n\n- Tidied.\n"
    _remaining, groups = adopt.split_unreleased(text)
    assert "- Tidied." in groups["notes"]
    assert "housekeeping" not in groups


def test_the_last_section_in_the_file_is_still_bounded_correctly() -> None:
    """`[Unreleased]` with nothing after it: the bound is end-of-file, and the
    old released sections above it must not be swept along."""
    text = "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n- Shipped.\n\n## [Unreleased]\n\n### Fixed\n\n- Pending.\n"
    remaining, groups = adopt.split_unreleased(text)
    assert "- Shipped." in remaining and "## [1.0.0]" in remaining
    assert groups["fixed"].strip() == "- Pending."


def test_an_EMPTY_unreleased_section_is_removed_too(tmp_path) -> None:
    """It holds nothing, so nothing migrates — but it is still the anchor. The
    next PR writes `### Added` under it and the one after that collides on the
    same three lines. Leaving it because it looked harmless leaves the problem.
    """
    (tmp_path / "tests").mkdir()
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n\n- Shipped.\n"
    )
    assert adopt.adopt(tmp_path) == 0
    after = (tmp_path / "CHANGELOG.md").read_text()
    assert "Unreleased" not in after
    assert "- Shipped." in after


def test_a_repo_with_no_test_suite_is_refused_rather_than_half_adopted(tmp_path) -> None:
    """A repo with no pytest carries the release guard inert — it would look
    installed and hold nothing. Say so; do not write files."""
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    assert adopt.adopt(tmp_path) == 3
    assert not (tmp_path / "changelog.d").exists()


def test_a_repo_versioned_only_by_git_tag_still_adopts(tmp_path) -> None:
    """dpyc-community has no pyproject.toml and is where the most concurrent
    PRs land. Only the version guard needs a version file; the fold and the
    order-independence do not, so it adopts and that one guard skips."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "CHANGELOG.md").write_text(SAMPLE)
    assert adopt.adopt(tmp_path) == 0
    assert (tmp_path / "scripts" / "changelog.py").is_file()
    assert (tmp_path / "changelog.d" / "added-0001-unreleased.md").is_file()


@pytest.mark.parametrize("heading", ["## [Unreleased]", "## Unreleased", "## [UNRELEASED]"])
def test_the_section_is_found_however_it_is_spelled(heading: str) -> None:
    text = f"# Changelog\n\n{heading}\n\n### Fixed\n\n- A fix.\n\n## [1.0.0] - 2026-01-01\n"
    _remaining, groups = adopt.split_unreleased(text)
    assert groups["fixed"].strip() == "- A fix."


def test_a_real_adoption_writes_the_three_files(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    (tmp_path / "tests").mkdir()
    (tmp_path / "CHANGELOG.md").write_text(SAMPLE)

    assert adopt.adopt(tmp_path) == 0

    assert (tmp_path / "scripts" / "changelog.py").is_file()
    assert (tmp_path / "changelog.d" / "README.md").is_file()
    assert (tmp_path / "tests" / "test_changelog.py").is_file()
    fragments = sorted(p.name for p in (tmp_path / "changelog.d").glob("*.md"))
    assert fragments == ["README.md", "added-0001-unreleased.md", "fixed-0001-unreleased.md"]
    assert "Unreleased" not in (tmp_path / "CHANGELOG.md").read_text()
