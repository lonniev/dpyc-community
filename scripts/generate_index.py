#!/usr/bin/env python3
"""Generate members/read-only-lookup-cache.json from individual member files in members/.

Usage:
  python scripts/generate_index.py           # Write members/read-only-lookup-cache.json
  python scripts/generate_index.py --check   # Verify members/read-only-lookup-cache.json is up-to-date
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ROLE_DIRS = {
    "prime_authority": "prime",
    "authority": "authorities",
    "operator": "operators",
    "citizen": "citizens",
}

# Banned members keep their original role but live in this directory
BANNED_DIR = "persona-non-grata"

# Sort order: prime → authority → operator → citizen, then by npub
ROLE_ORDER = {"prime_authority": 0, "authority": 1, "operator": 2, "citizen": 3}

MEMBERS_DIR = REPO_ROOT / "members"
INDEX_PATH = REPO_ROOT / "members" / "read-only-lookup-cache.json"
MEMBER_SCHEMA_PATH = REPO_ROOT / "schemas" / "member.schema.json"


def load_member_files() -> list[dict]:
    """Load and validate all individual member JSON files."""
    members: list[dict] = []
    errors: list[str] = []

    # Try schema validation if jsonschema is available
    validator = None
    try:
        import jsonschema

        if MEMBER_SCHEMA_PATH.exists():
            schema = json.loads(MEMBER_SCHEMA_PATH.read_text())
            validator = jsonschema.Draft202012Validator(schema)
    except ImportError:
        pass

    # Scan role directories + persona-non-grata
    all_dirs = [(dirname, True) for dirname in ROLE_DIRS.values()]
    all_dirs.append((BANNED_DIR, False))  # skip role↔dir check for banned

    for dirname, check_role_dir in all_dirs:
        role_dir = MEMBERS_DIR / dirname
        if not role_dir.exists():
            continue

        for filepath in sorted(role_dir.glob("*.json")):
            try:
                member = json.loads(filepath.read_text())
            except json.JSONDecodeError as exc:
                errors.append(f"{filepath.relative_to(REPO_ROOT)}: invalid JSON: {exc}")
                continue

            # Validate against member schema
            if validator:
                for error in validator.iter_errors(member):
                    path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
                    errors.append(
                        f"{filepath.relative_to(REPO_ROOT)}: schema: {path}: {error.message}"
                    )

            # Validate filename matches npub
            expected_filename = f"{member.get('npub', '')}.json"
            if filepath.name != expected_filename:
                errors.append(
                    f"{filepath.relative_to(REPO_ROOT)}: filename must match npub "
                    f"(expected {expected_filename})"
                )

            # Validate directory matches role (skip for persona-non-grata)
            if check_role_dir:
                member_role = member.get("role", "")
                expected_dir = ROLE_DIRS.get(member_role)
                if expected_dir and dirname != expected_dir:
                    errors.append(
                        f"{filepath.relative_to(REPO_ROOT)}: role '{member_role}' "
                        f"belongs in members/{expected_dir}/, not members/{dirname}/"
                    )

            members.append(member)

    if errors:
        print(f"FAILED: {len(errors)} error(s) in member files:\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    return members


def sort_members(members: list[dict]) -> list[dict]:
    """Sort: prime → authority → operator → citizen, then by npub."""
    return sorted(
        members,
        key=lambda m: (ROLE_ORDER.get(m.get("role", ""), 99), m.get("npub", "")),
    )


def build_index(members: list[dict]) -> dict:
    """Assemble the full members/read-only-lookup-cache.json structure."""
    return {
        "$schema": "../schemas/members.schema.json",
        "version": "1.0.0",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "members": members,
    }


def main() -> int:
    check_mode = "--check" in sys.argv

    members = load_member_files()
    if not members:
        print("ERROR: No member files found in members/", file=sys.stderr)
        return 1

    members = sort_members(members)
    index = build_index(members)
    generated = json.dumps(index, indent=2, ensure_ascii=False) + "\n"

    if check_mode:
        # Compare member arrays only (ignore updated_at timestamp)
        if not INDEX_PATH.exists():
            print("FAILED: members/read-only-lookup-cache.json does not exist", file=sys.stderr)
            return 1

        existing = json.loads(INDEX_PATH.read_text())
        if existing.get("members") != index["members"]:
            print(
                "FAILED: members/read-only-lookup-cache.json is out of date. "
                "Run 'python scripts/generate_index.py' to regenerate.",
                file=sys.stderr,
            )
            return 1

        print(f"OK: members/read-only-lookup-cache.json is up-to-date ({len(members)} members).")
        return 0

    # Write mode
    INDEX_PATH.write_text(generated)
    print(f"Generated members/read-only-lookup-cache.json with {len(members)} members.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
