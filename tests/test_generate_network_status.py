"""Tests for the network-status.json generator (issue #112).

Pins the *pure* assembler: given the existing snapshot plus a set of canned
``*_service_status`` payloads, it refreshes only the machine-derivable versions
(``current`` per component, and the fleet ``tollbooth-dpyc`` SDK version) while
preserving the human-authored ``minimum``, ``changelog_url``, ``advisory``,
``architecture_notes`` and ``protocols``. No network is touched here — that is
the whole point of splitting the probe layer from the assembler.

Run: pytest tests/test_generate_network_status.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_network_status import (  # noqa: E402
    assemble_network_status,
    latest_version,
)


EXISTING = {
    "components": {
        "tollbooth-dpyc": {
            "current": "0.59.1",
            "minimum": "0.49.0",
            "changelog_url": "https://github.com/lonniev/tollbooth-dpyc/releases",
        },
        "tollbooth-sample": {
            "current": "0.4.0",
            "minimum": "0.3.1",
            "changelog_url": "https://github.com/lonniev/tollbooth-sample/releases",
        },
        "schwab-mcp": {
            "current": "0.12.0",
            "minimum": "0.11.1",
            "changelog_url": "https://github.com/lonniev/schwab-mcp/releases",
        },
        "dpyc-oracle": {
            "current": "0.2.14",
            "minimum": "0.2.10",
            "changelog_url": "https://github.com/lonniev/dpyc-oracle/releases",
        },
    },
    "protocols": ["dpyp-01-base-certificate"],
    "last_updated": "2026-07-03",
    "advisory": "Human-authored prose that must survive verbatim.",
    "architecture_notes": "Also human-authored; also survives verbatim.",
}

PROBES = [
    {"service": "tollbooth-sample", "version": "0.4.2", "tollbooth_dpyc_version": "0.64.1"},
    {"service": "schwab-mcp", "version": "0.12.2", "tollbooth_dpyc_version": "0.63.3"},
]


def test_latest_version_picks_highest_semver():
    assert latest_version(["0.63.3", "0.64.1", "0.9.0"]) == "0.64.1"
    assert latest_version(["1.10.0", "1.9.0"]) == "1.10.0"  # numeric, not lexical
    assert latest_version([]) is None


def test_probed_component_current_is_refreshed_but_floor_preserved():
    out = assemble_network_status(EXISTING, PROBES, last_updated="2026-07-18")
    sample = out["components"]["tollbooth-sample"]
    assert sample["current"] == "0.4.2"          # machine-derived, refreshed
    assert sample["minimum"] == "0.3.1"          # human floor, untouched
    assert sample["changelog_url"] == "https://github.com/lonniev/tollbooth-sample/releases"


def test_sdk_version_is_highest_reported_across_fleet():
    out = assemble_network_status(EXISTING, PROBES, last_updated="2026-07-18")
    assert out["components"]["tollbooth-dpyc"]["current"] == "0.64.1"


def test_unprobed_component_keeps_existing_current():
    out = assemble_network_status(EXISTING, PROBES, last_updated="2026-07-18")
    # dpyc-oracle was not in the probe set: skip, don't fail, don't blank it.
    assert out["components"]["dpyc-oracle"]["current"] == "0.2.14"


def test_human_sections_and_protocols_survive_verbatim():
    out = assemble_network_status(EXISTING, PROBES, last_updated="2026-07-18")
    assert out["advisory"] == EXISTING["advisory"]
    assert out["architecture_notes"] == EXISTING["architecture_notes"]
    assert out["protocols"] == ["dpyp-01-base-certificate"]


def test_last_updated_is_stamped():
    out = assemble_network_status(EXISTING, PROBES, last_updated="2026-07-18")
    assert out["last_updated"] == "2026-07-18"


def test_unknown_probe_service_does_not_add_a_component():
    # A probed service with no human-authored floor must NOT invent a component
    # (minimum is a security floor only a human may set).
    probes = PROBES + [{"service": "brand-new-mcp", "version": "9.9.9"}]
    out = assemble_network_status(EXISTING, probes, last_updated="2026-07-18")
    assert "brand-new-mcp" not in out["components"]


def test_malformed_probes_are_ignored():
    probes = PROBES + [{"version": "1.2.3"}, {"service": "schwab-mcp"}, {}]
    out = assemble_network_status(EXISTING, probes, last_updated="2026-07-18")
    assert out["components"]["schwab-mcp"]["current"] == "0.12.2"  # good probe still wins


def test_assembler_is_deterministic_and_pure():
    a = assemble_network_status(EXISTING, PROBES, last_updated="2026-07-18")
    b = assemble_network_status(EXISTING, PROBES, last_updated="2026-07-18")
    assert a == b
    # component key order is preserved from the existing snapshot (stable diffs)
    assert list(a["components"].keys()) == list(EXISTING["components"].keys())
    # input was not mutated
    assert EXISTING["components"]["tollbooth-sample"]["current"] == "0.4.0"
