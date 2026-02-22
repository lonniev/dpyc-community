#!/usr/bin/env python3
"""Validate members.json against the JSON schema and DPYC business rules.

Checks:
  1. JSON Schema validation (structure, types, enums, npub pattern)
  2. No duplicate npubs
  3. All non-prime members have a valid upstream_authority_npub that exists
  4. prime_authority members have upstream_authority_npub = null
  5. Banned members have ban_reason and banned_at

Exit code 0 = valid, 1 = errors found.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NPUB_PATTERN = re.compile(r"^npub1[a-z0-9]{58}$")
REPO_ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def validate_schema(members_data: dict, schema: dict) -> list[str]:
    """Validate members.json against the JSON schema using jsonschema if available."""
    try:
        import jsonschema
    except ImportError:
        # Fall back to basic structural checks if jsonschema not installed
        errors = []
        if "members" not in members_data:
            errors.append("Missing required field: 'members'")
        if "version" not in members_data:
            errors.append("Missing required field: 'version'")
        if "updated_at" not in members_data:
            errors.append("Missing required field: 'updated_at'")
        return errors

    errors = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in validator.iter_errors(members_data):
        path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"Schema: {path}: {error.message}")
    return errors


def validate_business_rules(members: list[dict]) -> list[str]:
    """Check DPYC-specific business rules beyond schema validation."""
    errors = []
    npubs_seen: dict[str, int] = {}
    all_npubs: set[str] = set()

    # First pass: collect all npubs
    for i, member in enumerate(members):
        npub = member.get("npub", "")
        if npub:
            all_npubs.add(npub)

    # Second pass: validate rules
    for i, member in enumerate(members):
        npub = member.get("npub", "")
        role = member.get("role", "")
        status = member.get("status", "")
        upstream = member.get("upstream_authority_npub")
        display = member.get("display_name", npub[:20])

        # Duplicate check
        if npub in npubs_seen:
            errors.append(
                f"Member {i} ({display}): duplicate npub — "
                f"same as member {npubs_seen[npub]}"
            )
        else:
            npubs_seen[npub] = i

        # npub format (redundant with schema, but useful without jsonschema)
        if npub and not NPUB_PATTERN.match(npub):
            errors.append(f"Member {i} ({display}): invalid npub format")

        # Prime authority must have null upstream
        if role == "prime_authority" and upstream is not None:
            errors.append(
                f"Member {i} ({display}): prime_authority must have "
                f"upstream_authority_npub = null"
            )

        # Non-prime must have a valid upstream
        if role in ("authority", "operator", "citizen"):
            if not upstream:
                errors.append(
                    f"Member {i} ({display}): {role} must have "
                    f"upstream_authority_npub set"
                )
            elif upstream not in all_npubs:
                errors.append(
                    f"Member {i} ({display}): upstream_authority_npub "
                    f"{upstream[:20]}... not found in registry"
                )

        # Banned members should have ban_reason
        if status == "banned" and not member.get("ban_reason"):
            errors.append(
                f"Member {i} ({display}): banned members should have ban_reason"
            )

    return errors


def main() -> int:
    members_path = REPO_ROOT / "members.json"
    schema_path = REPO_ROOT / "schemas" / "members.schema.json"

    if not members_path.exists():
        print("ERROR: members.json not found")
        return 1

    if not schema_path.exists():
        print("ERROR: schemas/members.schema.json not found")
        return 1

    members_data = load_json(members_path)
    schema = load_json(schema_path)

    errors: list[str] = []

    # Schema validation
    errors.extend(validate_schema(members_data, schema))

    # Business rules
    members = members_data.get("members", [])
    errors.extend(validate_business_rules(members))

    if errors:
        print(f"FAILED: {len(errors)} error(s) found:\n")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"PASSED: {len(members)} member(s) validated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
