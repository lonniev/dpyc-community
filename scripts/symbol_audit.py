#!/usr/bin/env python3
"""Audit the factory graph's code Symbols against the code they claim to describe.

The graph records where a symbol lives (``anchor_symbol`` -> ``file_path`` +
``verified_at_sha``) but nothing ever reads it back, so an anchor rots silently: the code
moves or dies, the node keeps pointing at it, and the next agent greps a scope that no
longer contains what it was promised.

**File existence is only the cheap half.** Measured on tollbooth-dpyc 2026-08-07: of 36
anchored symbols, 6 were stale and only ONE was file-missing. A file survives the refactor
that guts it — ``PrefectClosureExecutor.submit`` and ``async_executor._harvest_artifacts``
were anchored to ``src/tollbooth/async_executor.py``, which still exists, while the class
they name had been deleted outright. So this audit reads the file and looks for the symbol
INSIDE it. A path-only check reports a clean bill of health on a graph a sixth stale.

Second trap, and the reason ``_parent_and_leaf`` exists: a leaf-only search gives FALSE
PASSES. ``PrefectClosureExecutor.submit`` matched a *different* class's ``def submit`` in the
same file. When the parent looks like a type, the type must be found too.

This is a REPORT, never a gate. It writes nothing — not to the graph, not to the repos —
and it exits 0 whatever it finds, because a stale anchor is a fact to act on, not a build
break. Verdicts:

    ok          the anchored file exists and the symbol is in it
    file_gone   the anchored path does not exist at HEAD
    symbol_gone the file is there; the symbol is not (the half a path check misses)
    in_flight   absent at HEAD, but its verified_at_sha is NOT an ancestor of HEAD — the
                anchor was recorded from an unmerged branch, so this is work in progress,
                not rot
    unanchored  the graph never recorded a file_path — nothing to check
    no_repo     the repo is not checked out locally, so this row was not judged

``in_flight`` exists because the first run of this audit called
``metrics_harvest.profile_click_rate`` and ``time_of_day_cohort`` DELETED. They were not:
they were new in excalibur-mcp#362, and the Journeyman had indexed them into the graph while
working the branch, before the code ever reached main. Reporting live work as rot is the
expensive direction. The distinction needs ``verified_at_sha`` — absent at HEAD *and* its sha
is an ancestor means genuinely deleted; absent at HEAD *and* its sha is not means unmerged.
That field has existed since Task 2 and this is the first thing to read it.

⚠️ ``symbols_in_service`` does NOT return ``verified_at_sha`` — only fqn/lang/file. So rows
sourced from it cannot make this distinction and will report ``symbol_gone`` for in-flight
work. ``symbol_provenance`` does return it, one symbol per call. The listing read omitting the
one field that dates an anchor is a gap in the read surface, not in this audit.

Naming conformance (``factory/README.md`` -> "Symbol names in the graph") is reported on a
SEPARATE axis, never as a verdict: before the migration nothing conforms, and an audit that
answered "malformed" for every row and checked no anchors would be useless exactly when the
staleness report is most needed.

Usage:
    # rows: [{"fqn": ..., "file": ..., "lang": ..., "repo": ...}, ...]
    python scripts/symbol_audit.py --input symbols.json --repos-root ~/Development/.../DPYC
    python scripts/symbol_audit.py --input symbols.json --repos-root .. --verdict symbol_gone
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intention_harvest import check_symbol_fqn  # the shared naming doctrine

# A Swift argument-label clause is part of the NAME (`foo(npub:dm:)`); strip it before
# splitting a dotted path, or the labels' colons get mistaken for path structure.
_SWIFT_LABELS = re.compile(r"\((?:(?:[A-Za-z_][A-Za-z0-9_]*|_):)*\)$")
# A parent that names a TYPE — the thing a leaf-only search would let you skip.
_TYPE_LIKE = re.compile(r"^[A-Z]")

#: Per language, how a definition of ``{name}`` is spelled. Deliberately generous: this
#: audit's job is to catch a symbol that is GONE, so a false "present" costs less than a
#: false "deleted" that sends someone chasing live code.
_DEFINITION_PATTERNS: dict[str, tuple[str, ...]] = {
    "python": (r"^\s*(?:async\s+)?def\s+{name}\b", r"^\s*class\s+{name}\b",
               r"^\s*{name}\s*(?::[^=]+)?=", r"^\s*{name}\s*:\s*\w"),
    "typescript": (r"\b(?:function|class|interface|type|enum)\s+{name}\b",
                   r"\b(?:const|let|var)\s+{name}\b", r"^\s*{name}\s*[:(]",
                   r"\b{name}\s*=\s*(?:function|\()"),
    "swift": (r"\bfunc\s+{name}\b", r"\b(?:class|struct|enum|protocol|actor)\s+{name}\b",
              r"\b(?:let|var)\s+{name}\b"),
    "rust": (r"\bfn\s+{name}\b", r"\b(?:struct|enum|trait|impl|type)\s+{name}\b",
             r"\b(?:const|static)\s+{name}\b"),
}
_DEFINITION_PATTERNS["javascript"] = _DEFINITION_PATTERNS["typescript"]


@dataclass(frozen=True)
class Finding:
    fqn: str
    repo: str
    file: str | None
    verdict: str
    detail: str = ""
    #: Naming conformance is an INDEPENDENT axis from anchor staleness, and must never
    #: short-circuit it. Before the migration nothing conforms, which is precisely when the
    #: staleness report is most needed — an audit that answered "malformed" 78 times and
    #: checked no anchors would be useless exactly when it matters.
    conforms: bool = True
    naming: str = ""


def strip_repo_prefix(fqn: str) -> str:
    """Return the import-path part of a `<repo>:<path>` fqn (pre-migration names pass through)."""
    repo, sep, rest = fqn.partition(":")
    # Only treat it as a prefix when it looks like a repo slug — Rust's `::` and a stray
    # `file.py:42` must not be mistaken for one.
    return rest if sep and re.fullmatch(r"[a-z0-9][a-z0-9-]*", repo) else fqn


def _parent_and_leaf(fqn: str) -> tuple[str | None, str]:
    """Split a symbol into (containing type, leaf name).

    The parent is returned ONLY when it looks like a type, because that is the case where a
    leaf-only search silently passes: `Foo.submit` finds some *other* class's `submit`.
    """
    path = _SWIFT_LABELS.sub("", strip_repo_prefix(fqn))
    parts = re.split(r"\.|::|#|/", path)
    parts = [p for p in parts if p]
    if not parts:
        return None, ""
    leaf = parts[-1]
    parent = parts[-2] if len(parts) > 1 else None
    return (parent if parent and _TYPE_LIKE.match(parent) else None), leaf


def symbol_present(text: str, fqn: str, lang: str | None,
                   file_stem: str | None = None) -> tuple[bool, str]:
    """Is ``fqn`` defined anywhere in ``text``? Returns (present, what_was_missing).

    ``file_stem`` suppresses a false positive that a capitalisation heuristic alone cannot
    avoid: in `frontend.src.components.FundingStatusPanels.PatronFundingStatus` the
    capitalised parent is the FILE, not a containing type, so demanding a
    `type FundingStatusPanels` inside FundingStatusPanels.tsx reports a live export as
    deleted. A parent that matches the file's own stem is a path segment — skip it.
    """
    patterns = _DEFINITION_PATTERNS.get((lang or "").lower())
    if not patterns:
        return True, ""  # unknown language: never claim a deletion we cannot see
    parent, leaf = _parent_and_leaf(fqn)
    if parent and file_stem and parent == file_stem:
        parent = None
    for name, label in ((parent, f"type {parent}"), (leaf, leaf)):
        if not name:
            continue
        found = any(re.search(p.format(name=re.escape(name)), text, re.MULTILINE)
                    for p in patterns)
        if not found:
            return False, label
    return True, ""


def sha_is_ancestor(repo_root: Path, sha: str) -> bool:
    """Is ``sha`` reachable from HEAD? False for an unmerged branch — or an unknown sha.

    Unknown counts as "not an ancestor" deliberately: a sha this clone has never fetched is
    far more likely to be un-merged work than a deletion we can prove, and calling live code
    deleted is the costlier mistake.
    """
    try:
        done = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", sha, "HEAD"],
            capture_output=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def _naming(fqn: str) -> tuple[bool, str]:
    try:
        check_symbol_fqn(fqn)
    except ValueError as exc:
        # First sentence only — but split on ". ", never ".", or a dotted fqn is mangled
        # ("symbol fqn 'tollbooth" instead of the actual complaint). Then drop the quoted
        # name itself, so the report can COUNT reasons instead of printing 78 rows that
        # each occur exactly once.
        reason = str(exc).split(". ")[0]
        return False, re.sub(r"'[^']*'", "", reason).replace("  ", " ").strip()
    return True, ""


def audit_row(row: dict, repos_root: Path) -> Finding:
    fqn, repo = row.get("fqn", ""), row.get("repo", "")
    file_path, lang = row.get("file"), row.get("lang")
    conforms, naming = _naming(fqn)

    def finding(verdict: str, detail: str = "") -> Finding:
        return Finding(fqn, repo, file_path, verdict, detail, conforms, naming)

    if not file_path:
        return finding("unanchored", "no file_path recorded")
    root = repos_root / repo
    if not root.is_dir():
        return finding("no_repo", f"{root} not checked out")
    target = root / file_path
    if not target.exists():
        return finding("file_gone", "path absent at HEAD")
    present, missing = symbol_present(target.read_text(errors="replace"), fqn, lang,
                                      file_stem=target.stem)
    if not present:
        sha = row.get("verified_at_sha")
        if sha and not sha_is_ancestor(root, sha):
            return finding("in_flight", f"anchored at {sha[:9]}, not an ancestor of HEAD")
        return finding("symbol_gone", f"missing: {missing}")
    return finding("ok")


def audit(rows: list[dict], repos_root: Path) -> list[Finding]:
    # The graph can hand back the same row twice (duplicate Service nodes double every row
    # from symbols_in_service — cypher-mcp fix/service-identity-one-key), so dedupe first or
    # every count is inflated for exactly the repos that are doubled.
    seen: set[tuple] = set()
    out: list[Finding] = []
    for row in rows:
        key = (row.get("fqn"), row.get("repo"), row.get("file"))
        if key in seen:
            continue
        seen.add(key)
        out.append(audit_row(row, repos_root))
    return out


def format_report(findings: list[Finding], only: str | None = None) -> str:
    counts = Counter(f.verdict for f in findings)
    lines = [f"{len(findings)} distinct symbols audited", "", "ANCHORS"]
    for verdict in ("ok", "symbol_gone", "file_gone", "in_flight", "unanchored", "no_repo"):
        if counts.get(verdict):
            lines.append(f"  {verdict:12s} {counts[verdict]}")
    stale = counts.get("symbol_gone", 0) + counts.get("file_gone", 0)
    checked = stale + counts.get("ok", 0)
    if checked:
        lines.append(f"  -> STALE {stale}/{checked} of the anchors that could be checked"
                     + (f"; {counts['symbol_gone']} of them have a file that still exists,"
                        " so a path-only check would miss them"
                        if counts.get("symbol_gone") else ""))
    nonconforming = [f for f in findings if not f.conforms]
    lines += ["", f"NAMING  {len(findings) - len(nonconforming)}/{len(findings)} conform"]
    for reason, n in Counter(f.naming for f in nonconforming).most_common():
        lines.append(f"  {n:>4}  {reason}")

    detail = [f for f in findings
              if f.verdict != "ok" and (not only or f.verdict == only)]
    if detail:
        lines.append("")
        for f in sorted(detail, key=lambda f: (f.verdict, f.repo, f.fqn)):
            flag = "" if f.conforms else "  [also malformed]"
            lines.append(f"  [{f.verdict}] {f.repo}: {f.fqn}"
                         + (f"  ({f.detail})" if f.detail else "") + flag)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path,
                    help="JSON list of {fqn, file, lang, repo} rows from the graph")
    ap.add_argument("--repos-root", required=True, type=Path,
                    help="directory holding the repo checkouts")
    ap.add_argument("--verdict", help="show only this verdict in the detail list")
    args = ap.parse_args()
    rows = json.loads(args.input.read_text())
    findings = audit(rows, args.repos_root.expanduser().resolve())
    print(format_report(findings, args.verdict))
    return 0  # a report, never a gate


if __name__ == "__main__":
    raise SystemExit(main())
