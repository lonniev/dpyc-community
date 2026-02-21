#!/usr/bin/env python3
"""Publish a DPYP protocol spec as a NIP-78 event on Nostr relays.

Usage:
    PRIME_AUTHORITY_NSEC=nsec1... python scripts/publish_dpyp.py

Requires: pip install -r scripts/requirements.txt
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import time

from pynostr.event import Event
from pynostr.key import PrivateKey

try:
    from websocket import create_connection  # type: ignore[import-untyped]
except ImportError:
    create_connection = None

PROTOCOL_ID = "dpyp-01-base-certificate"
RELAYS = ["wss://relay.damus.io", "wss://nos.lol"]

CONTENT = """\
DPYP-01: Base Certificate — defines the base JWT certificate schema for \
Tollbooth purchase orders. Every Authority includes a dpyc_protocol claim \
in signed certificates; every Operator verifies the claim matches a protocol \
it understands. Required claims: sub, jti, iat, exp, dpyc_protocol, \
amount_sats, tax_paid_sats, net_sats. Signature: Ed25519 (EdDSA). \
Status: Active.\
"""


def _publish_to_relay(relay_url: str, message: str) -> str:
    """Send a NIP-01 EVENT message to a single relay and return the response."""
    sslopt = {"cert_reqs": ssl.CERT_NONE}
    ws = create_connection(relay_url, timeout=10, sslopt=sslopt)
    try:
        ws.send(message)
        resp = ws.recv()
        return resp
    finally:
        ws.close()


def main() -> None:
    if create_connection is None:
        print(
            "Error: websocket-client is required. Install with:\n"
            "  pip install websocket-client",
            file=sys.stderr,
        )
        sys.exit(1)

    nsec = os.environ.get("PRIME_AUTHORITY_NSEC", "").strip()
    if not nsec:
        print("Error: Set PRIME_AUTHORITY_NSEC environment variable.", file=sys.stderr)
        sys.exit(1)

    pk = PrivateKey.from_nsec(nsec)

    event = Event(
        kind=30078,
        content=CONTENT,
        tags=[
            ["d", PROTOCOL_ID],
            ["dpyp-version", "1"],
            ["status", "active"],
            ["repo", "https://github.com/lonniev/dpyc-community"],
            ["spec", f"https://github.com/lonniev/dpyc-community/blob/main/protocols/{PROTOCOL_ID}.md"],
        ],
        pubkey=pk.public_key.hex(),
        created_at=int(time.time()),
    )
    event.sign(pk.hex())

    print(f"Event ID: {event.id}")
    print(f"Author:   {pk.public_key.bech32()}")
    print(f"Kind:     {event.kind}")
    print(f"d-tag:    {PROTOCOL_ID}")
    print()

    message = event.to_message()
    for relay_url in RELAYS:
        try:
            resp = _publish_to_relay(relay_url, message)
            print(f"  {relay_url} -> {resp}")
        except Exception as e:
            print(f"  {relay_url} -> ERROR: {e}")

    print("\nDone. Verify with:")
    print(f'  {{"kinds": [30078], "#d": ["{PROTOCOL_ID}"]}}')


if __name__ == "__main__":
    main()
