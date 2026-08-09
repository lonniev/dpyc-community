"""Tests for the funding-outage signature detector and OpenRouter credit preflight.

Pins the load-bearing facts from issue #181:

1. A mid-run 402 (api_error_status == 402 after real turns/spend) IS an outage.
   OpenRouter reserves max_tokens up front; a nearly-dry account serves cheap early
   turns and refuses the first expensive one. Turns and cost are the wrong discriminator.
2. The classic hard-reject shape (is_error + num_turns<=1 + cost==0) still matches.
3. A real tool/agent error with no 402 must NOT be mislabeled as funding outage.
4. Credit balance math: remaining = total_credits - total_usage; overdrawn when <= 0
   (or below an operator floor).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINEL_DIR = REPO_ROOT / "factory" / "actions" / "funding-sentinel"
PREFLIGHT_DIR = REPO_ROOT / "factory" / "actions" / "credit-preflight"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


detect = _load("detect_signature", SENTINEL_DIR / "detect_signature.py")


# --- Defect 1: mid-run 402 must match regardless of turns/spend ----------------

def test_mid_run_402_is_outage():
    """The cypher-mcp#70 shape: 6 turns, real spend, api_error_status 402."""
    events = [
        {
            "type": "result",
            "is_error": True,
            "num_turns": 6,
            "total_cost_usd": 0.358058,
            "terminal_reason": "api_error",
            "api_error_status": 402,
            "permission_denials": [],
        }
    ]
    assert detect.is_outage(events) is True


def test_mid_run_402_string_status_is_outage():
    """Some serializers leave the status as a string."""
    events = [
        {
            "type": "result",
            "is_error": True,
            "num_turns": 3,
            "total_cost_usd": 0.12,
            "api_error_status": "402",
        }
    ]
    assert detect.is_outage(events) is True


def test_hard_reject_zero_turn_still_matches():
    """Existing arm: rejected before inference — 0/1 turn, $0."""
    events = [
        {
            "type": "result",
            "is_error": True,
            "num_turns": 1,
            "total_cost_usd": 0,
        }
    ]
    assert detect.is_outage(events) is True


def test_hard_reject_zero_turns_explicit():
    events = [
        {
            "type": "result",
            "is_error": True,
            "num_turns": 0,
            "total_cost_usd": 0.0,
        }
    ]
    assert detect.is_outage(events) is True


def test_real_tool_error_is_not_outage():
    """A genuine failure with spend and no 402 must not be tagged awaiting-funds."""
    events = [
        {
            "type": "result",
            "is_error": True,
            "num_turns": 12,
            "total_cost_usd": 1.2,
            "terminal_reason": "error",
        }
    ]
    assert detect.is_outage(events) is False


def test_success_is_not_outage():
    events = [
        {
            "type": "result",
            "is_error": False,
            "num_turns": 8,
            "total_cost_usd": 0.4,
        }
    ]
    assert detect.is_outage(events) is False


def test_empty_events_is_not_outage():
    assert detect.is_outage([]) is False


def test_result_picked_from_stream_tail():
    """Result is the last type==result event in a mixed stream."""
    events = [
        {"type": "assistant", "message": "working"},
        {
            "type": "result",
            "is_error": True,
            "num_turns": 4,
            "total_cost_usd": 0.2,
            "api_error_status": 402,
        },
    ]
    assert detect.is_outage(events) is True


def test_cli_yes_for_mid_run_402(tmp_path, capsys):
    path = tmp_path / "out.json"
    path.write_text(
        '[{"type":"result","is_error":true,"num_turns":6,'
        '"total_cost_usd":0.35,"api_error_status":402}]',
        encoding="utf-8",
    )
    old = sys.argv
    try:
        sys.argv = ["detect_signature.py", str(path)]
        detect.main()
    finally:
        sys.argv = old
    assert capsys.readouterr().out.strip() == "yes"


def test_cli_no_for_tool_error(tmp_path, capsys):
    path = tmp_path / "out.json"
    path.write_text(
        '[{"type":"result","is_error":true,"num_turns":10,"total_cost_usd":1.0}]',
        encoding="utf-8",
    )
    old = sys.argv
    try:
        sys.argv = ["detect_signature.py", str(path)]
        detect.main()
    finally:
        sys.argv = old
    assert capsys.readouterr().out.strip() == "no"


# --- Credit balance math (preflight + canary share this) -----------------------

# Loaded lazily so the signature tests still run if preflight lands later in the PR.
@pytest.fixture(scope="module")
def credits():
    path = PREFLIGHT_DIR / "check_credits.py"
    if not path.exists():
        pytest.skip("credit-preflight not present yet")
    return _load("check_credits", path)


def test_remaining_and_overdrawn(credits):
    assert credits.remaining(70.0, 60.09) == pytest.approx(9.91)
    assert credits.is_overdrawn(70.0, 60.09) is False
    assert credits.is_overdrawn(60.0, 60.085) is True
    assert credits.is_overdrawn(60.0, 60.0) is True


def test_below_floor(credits):
    # Floor is the operator dial: remaining 9.91 is healthy at floor 0, broke at 10.
    assert credits.below_floor(70.0, 60.09, floor=0.0) is False
    assert credits.below_floor(70.0, 60.09, floor=10.0) is True
    assert credits.below_floor(60.0, 60.085, floor=0.0) is True


def test_classify_states(credits):
    assert credits.classify(70.0, 60.09, floor=0.0) == "healthy"
    assert credits.classify(70.0, 60.09, floor=10.0) == "low"
    assert credits.classify(60.0, 60.085, floor=0.0) == "broke"
    assert credits.classify(60.0, 60.085, floor=5.0) == "broke"
