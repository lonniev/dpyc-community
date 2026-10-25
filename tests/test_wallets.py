"""wallets.json is read by the Oracle and shown to new guests, so it must hold
only what a page can render safely: https links, logos carried inline, one
wallet pinned at most."""

import json
import re
from pathlib import Path

DOC = json.loads((Path(__file__).parent.parent / "wallets.json").read_text())
LINKS = ("homepage", "app_store", "google_play")
CUSTODY = {"custodial", "self-custodial", "either"}


def test_top_level():
    assert isinstance(DOC["query"], str) and DOC["query"].strip()
    assert isinstance(DOC["show"], int) and 1 <= DOC["show"] <= len(DOC["wallets"])
    assert isinstance(DOC["credit"], str)


def test_ids_are_unique_slugs():
    ids = [w["id"] for w in DOC["wallets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z0-9-]+", i) for i in ids)


def test_links_are_https():
    for w in DOC["wallets"]:
        assert w.get("homepage"), w["id"]
        for k in LINKS:
            if w.get(k) is not None:
                assert w[k].startswith("https://"), f"{w['id']}.{k}"


def test_logos_are_inline_png():
    for w in DOC["wallets"]:
        assert w["logo"].startswith("data:image/png;base64,"), w["id"]
        assert len(w["logo"]) < 12_000, f"{w['id']} logo is too large"


def test_fields():
    for w in DOC["wallets"]:
        assert w["name"].strip() and w["line"].strip(), w["id"]
        assert w["custody"] in CUSTODY, w["id"]
        assert isinstance(w["buys_in_app"], bool), w["id"]
        assert isinstance(w.get("aliases", []), list), w["id"]


def test_at_most_one_pinned():
    assert sum(1 for w in DOC["wallets"] if w.get("pinned")) <= 1
