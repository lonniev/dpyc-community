"""Tests for the Symbol anchor audit.

Every test here pins a mistake the audit actually made while being written against the live
graph, because each one produced a plausible-looking report that was wrong:

  * a leaf-only search passed `PrefectClosureExecutor.submit` on a different class's `submit`
  * requiring the capitalised parent then reported the LIVE `PatronFundingStatus` as deleted,
    because its parent is the file name, not a type
  * a malformed-name verdict short-circuited the anchor check, so before the migration —
    when nothing conforms — the audit checked no anchors at all
  * duplicate Service nodes double every row from `symbols_in_service`, inflating counts for
    exactly the repos that are doubled

Run: pytest tests/test_symbol_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from symbol_audit import (
    Finding,
    _parent_and_leaf,
    audit,
    audit_row,
    format_report,
    strip_repo_prefix,
    symbol_present,
)

PY = "python"
TS = "typescript"


# --- fqn decomposition -------------------------------------------------------

def test_strip_repo_prefix_only_strips_a_real_repo_slug():
    assert strip_repo_prefix("tollbooth-dpyc:tollbooth.runtime.f") == "tollbooth.runtime.f"
    # Rust's '::' is not a repo prefix, nor is a line-numbered path
    assert strip_repo_prefix("dpyc_crypto::schnorr::verify") == "dpyc_crypto::schnorr::verify"
    assert strip_repo_prefix("server.py:42") == "server.py:42"
    # pre-migration bare names pass through untouched
    assert strip_repo_prefix("tollbooth.runtime.f") == "tollbooth.runtime.f"


def test_parent_is_returned_only_when_it_looks_like_a_type():
    assert _parent_and_leaf("repo:mod.Klass.method") == ("Klass", "method")
    assert _parent_and_leaf("repo:mod.submodule.func") == (None, "func")
    # Swift labels are part of the name, not path structure
    assert _parent_and_leaf("repo:App.Svc.notify(npub:dm:)") == ("Svc", "notify")


# --- symbol presence ---------------------------------------------------------

def test_a_surviving_file_does_not_prove_a_surviving_symbol():
    """The half a path-existence check misses — and the reason this audit reads the file."""
    text = "class JobExecutor:\n    def submit(self): ...\n"
    ok, _ = symbol_present(text, "repo:mod.JobExecutor.submit", PY)
    assert ok
    # the class is gone; only a leaf search would wrongly pass on the other `submit`
    gone, missing = symbol_present(text, "repo:mod.PrefectClosureExecutor.submit", PY)
    assert not gone and missing == "type PrefectClosureExecutor"


def test_parent_matching_the_file_stem_is_a_path_segment_not_a_type():
    """`FundingStatusPanels.PatronFundingStatus` — the parent is the FILE. A live export
    must not be reported as deleted."""
    text = "export function PatronFundingStatus() {}\n"
    fqn = "repo:frontend.src.components.FundingStatusPanels.PatronFundingStatus"
    assert symbol_present(text, fqn, TS, file_stem="FundingStatusPanels") == (True, "")
    # without that hint the heuristic produces the false positive this guards against
    assert symbol_present(text, fqn, TS)[0] is False


def test_unknown_language_never_claims_a_deletion():
    assert symbol_present("", "repo:a.b", "cobol") == (True, "")
    assert symbol_present("", "repo:a.b", None) == (True, "")


def test_missing_leaf_is_reported(tmp_path):
    assert symbol_present("def other(): ...", "repo:mod.gone", PY) == (False, "gone")


# --- row verdicts ------------------------------------------------------------

def _row(fqn, file, repo="r", lang=PY):
    return {"fqn": fqn, "file": file, "repo": repo, "lang": lang}


def test_verdicts_over_a_real_tree(tmp_path):
    repo = tmp_path / "r"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "m.py").write_text("def alive(): ...\n")
    assert audit_row(_row("r:src.m.alive", "src/m.py"), tmp_path).verdict == "ok"
    assert audit_row(_row("r:src.m.dead", "src/m.py"), tmp_path).verdict == "symbol_gone"
    assert audit_row(_row("r:src.g.x", "src/gone.py"), tmp_path).verdict == "file_gone"
    assert audit_row(_row("r:src.m.alive", None), tmp_path).verdict == "unanchored"
    assert audit_row(_row("nope:a.b", "src/m.py", repo="nope"), tmp_path).verdict == "no_repo"


def test_naming_is_an_independent_axis_and_never_short_circuits_the_anchor(tmp_path):
    """Before the migration NOTHING conforms — an audit that answered 'malformed' and
    checked no anchors would be useless exactly when it is most needed."""
    repo = tmp_path / "r"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "m.py").write_text("def alive(): ...\n")
    bare = audit_row(_row("src.m.alive", "src/m.py"), tmp_path)   # no <repo>: prefix
    assert bare.conforms is False and bare.naming            # naming is reported
    assert bare.verdict == "ok"                              # ...and the anchor still judged
    stale = audit_row(_row("src.m.dead", "src/m.py"), tmp_path)
    assert stale.conforms is False and stale.verdict == "symbol_gone"


def test_naming_reason_is_a_class_so_the_report_can_count_it(tmp_path):
    a = audit_row(_row("one.two", None), tmp_path)
    b = audit_row(_row("three.four", None), tmp_path)
    # the quoted fqn is stripped, so two different bad names share one reason
    assert a.naming == b.naming and "'" not in a.naming


# --- aggregate ---------------------------------------------------------------

def test_duplicate_rows_are_collapsed(tmp_path):
    """Duplicate Service nodes make symbols_in_service return every row twice."""
    rows = [_row("r:a.b", None)] * 3 + [_row("r:c.d", None)]
    assert len(audit(rows, tmp_path)) == 2


def test_report_names_the_half_a_path_check_would_miss():
    findings = [
        Finding("r:a.gone", "r", "a.py", "symbol_gone", "missing: gone", True, ""),
        Finding("r:b.ok", "r", "b.py", "ok", "", True, ""),
    ]
    out = format_report(findings)
    assert "STALE 1/2" in out
    assert "path-only check would miss" in out


def test_report_is_never_a_gate():
    """A stale anchor is a fact to act on, not a build break."""
    import symbol_audit
    src = (REPO_ROOT / "scripts" / "symbol_audit.py").read_text()
    assert "return 0  # a report, never a gate" in src
    assert not hasattr(symbol_audit, "SystemExit_on_findings")
