#!/usr/bin/env python3
"""Install the changelog-fragment convention into one repository.

`CHANGELOG.md` is the fleet's most conflict-prone file, and the reason is
structural rather than careless: every PR appends to the same
`### Added` / `### Fixed` anchors of the same `## [Unreleased]` section, so two
PRs whose code shares no file still collide there. `changelog.d/` replaces that
one shared anchor with one file per change, and files that nobody else touches
never conflict.

Installing the machinery is only half the job. A repo that keeps its
`## [Unreleased]` section keeps the anchor, and the next two PRs collide on it
exactly as before — so this MIGRATES that section into fragments and removes it.
Nothing is dropped: every line of it lands in a fragment, and the run reports
the count so the diff can be checked against it.

    usage: adopt.py <repo-root>

Exit codes: 0 adopted, 3 not applicable (no pyproject.toml / no tests/), 2 usage.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent

#: Keep a Changelog's headings, lowercased, plus `notes`. Anything under an
#: `###` heading outside this set is kept as `notes` rather than discarded — a
#: repo that invented a heading still wrote something real under it.
KINDS = ("added", "changed", "deprecated", "removed", "fixed", "security", "notes")


def split_unreleased(text: str) -> tuple[str, dict[str, str]]:
    """Lift the `## [Unreleased]` section out, grouped by `###` heading.

    Returns the changelog WITHOUT that section, and `{kind: body}` for what was
    in it. A section that is absent or empty yields no fragments and returns
    the text unchanged, so this is safe to run on a repo that has already
    adopted the convention.

    The section is bounded by the next `## ` heading, never by a line count:
    a preamble of any length, and a `[Unreleased]` of any length, both work.
    """
    m = re.search(r"^## \[?Unreleased\]?.*$", text, re.MULTILINE | re.IGNORECASE)
    if not m:
        return text, {}
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    body = rest[: nxt.start()] if nxt else rest
    remaining = text[: m.start()] + (rest[nxt.start():] if nxt else "")

    groups: dict[str, list[str]] = {}
    # Everything before the first `### ` had no heading of its own; it is prose
    # about the release rather than an entry, which is what `notes` is for.
    parts = re.split(r"^### +(.+)$", body, flags=re.MULTILINE)
    preamble = parts[0].strip()
    if preamble:
        groups.setdefault("notes", []).append(preamble)
    for heading, chunk in zip(parts[1::2], parts[2::2], strict=True):
        kind = heading.strip().lower().split()[0].strip(":")
        if kind not in KINDS:
            kind = "notes"
        chunk = chunk.strip()
        if chunk:
            groups.setdefault(kind, []).append(chunk)

    return remaining, {k: "\n\n".join(v) + "\n" for k, v in groups.items()}


def adopt(root: pathlib.Path) -> int:
    # `tests/` is the only hard requirement: the fold is a script anybody can run,
    # but the guard that stops a release shipping with its fragments unfolded is a
    # pytest, and a repo with no suite would carry it inert. A repo with no
    # pyproject.toml still adopts — that guard skips itself and says why.
    if not (root / "tests").is_dir():
        print(f"{root.name}: not applicable (no tests/ — the release guard is a pytest)")
        return 3

    (root / "scripts").mkdir(exist_ok=True)
    (root / "changelog.d").mkdir(exist_ok=True)

    shutil.copy2(HERE / "changelog.py", root / "scripts" / "changelog.py")
    (root / "scripts" / "changelog.py").chmod(0o755)
    shutil.copy2(HERE / "changelog.d-README.md", root / "changelog.d" / "README.md")
    shutil.copy2(HERE / "test_changelog.py", root / "tests" / "test_changelog.py")

    changelog = root / "CHANGELOG.md"
    migrated = 0
    if changelog.is_file():
        original = changelog.read_text()
        remaining, groups = split_unreleased(original)
        for kind, body in sorted(groups.items()):
            # `0001-unreleased` sorts first, so a migrated backlog stays above
            # the fragments written after it — which is the order it was in.
            (root / "changelog.d" / f"{kind}-0001-unreleased.md").write_text(body)
            migrated += 1
        # Write whenever the section was THERE, empty or not. An empty
        # `## [Unreleased]` is still the conflict anchor: the next PR writes a
        # `### Added` under it and the one after that collides on the same
        # three lines. Leaving it because it held nothing leaves the problem.
        if remaining != original:
            changelog.write_text(remaining.rstrip() + "\n")

    print(
        f"{root.name}: adopted"
        + (f", migrated [Unreleased] into {migrated} fragment(s)" if migrated
           else " (no [Unreleased] section to migrate)")
    )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: adopt.py <repo-root>", file=sys.stderr)
        return 2
    return adopt(pathlib.Path(argv[0]).resolve())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
