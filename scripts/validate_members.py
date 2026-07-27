#!/usr/bin/env python3
"""Validate the DPYC membership registry.

Checks:
  1. Individual member files: schema, filename↔npub, directory↔role
  2. Generated index (read-only-lookup-cache.json): schema, business rules
  3. No duplicate npubs
  4. All non-prime members have a valid upstream_authority_npub
  5. prime_authority members have upstream_authority_npub = null
  6. Banned members have ban_reason

Exit code 0 = valid, 1 = errors found.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NPUB_PATTERN = re.compile(r"^npub1[a-z0-9]{58}$")
REPO_ROOT = Path(__file__).resolve().parent.parent

ROLE_DIRS = {
    "prime_authority": "prime",
    "authority": "authorities",
    "operator": "operators",
    "advocate": "advocates",
    "citizen": "citizens",
}

# Banned members keep their original role but live in this directory
BANNED_DIR = "persona-non-grata"


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def validate_schema(members_data: dict, schema: dict) -> list[str]:
    """Validate read-only-lookup-cache.json against the JSON schema using jsonschema if available."""
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


def validate_member_files() -> list[str]:
    """Validate individual member files: schema, filename, directory placement."""
    errors = []
    members_dir = REPO_ROOT / "members"

    if not members_dir.exists():
        return []  # No member files yet — skip

    # Load member schema if available
    validator = None
    try:
        import jsonschema

        member_schema_path = REPO_ROOT / "schemas" / "member.schema.json"
        if member_schema_path.exists():
            schema = json.loads(member_schema_path.read_text())
            validator = jsonschema.Draft202012Validator(schema)
    except ImportError:
        pass

    # Scan role directories + persona-non-grata
    all_dirs = [(dirname, True) for dirname in ROLE_DIRS.values()]
    all_dirs.append((BANNED_DIR, False))  # skip role↔dir check for banned

    for dirname, check_role_dir in all_dirs:
        role_dir = members_dir / dirname
        if not role_dir.exists():
            continue

        for filepath in sorted(role_dir.glob("*.json")):
            rel = filepath.relative_to(REPO_ROOT)

            try:
                member = json.loads(filepath.read_text())
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}: invalid JSON: {exc}")
                continue

            # Schema validation
            if validator:
                for error in validator.iter_errors(member):
                    path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
                    errors.append(f"{rel}: {path}: {error.message}")

            # Filename must match npub
            expected = f"{member.get('npub', '')}.json"
            if filepath.name != expected:
                errors.append(f"{rel}: filename must match npub (expected {expected})")

            # Directory must match role (skip for persona-non-grata)
            if check_role_dir:
                member_role = member.get("role", "")
                expected_dir = ROLE_DIRS.get(member_role)
                if expected_dir and dirname != expected_dir:
                    errors.append(
                        f"{rel}: role '{member_role}' belongs in "
                        f"members/{expected_dir}/, not members/{dirname}/"
                    )

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
        if role in ("authority", "operator", "advocate", "citizen"):
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
    members_path = REPO_ROOT / "members" / "read-only-lookup-cache.json"
    schema_path = REPO_ROOT / "schemas" / "members.schema.json"

    if not members_path.exists():
        print("ERROR: read-only-lookup-cache.json not found")
        return 1

    if not schema_path.exists():
        print("ERROR: schemas/members.schema.json not found")
        return 1

    errors: list[str] = []

    # Validate individual member files
    errors.extend(validate_member_files())

    # Validate the index (read-only-lookup-cache.json)
    members_data = load_json(members_path)
    schema = load_json(schema_path)
    errors.extend(validate_schema(members_data, schema))

    # Business rules on the index
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
