#!/usr/bin/env bash
# Adopt the changelog-fragment convention across the fleet, idempotently, in one batch.
#
# CHANGELOG.md is the fleet's most conflict-prone file and the reason is structural: every
# PR appends to the same `### Added` / `### Fixed` anchors of the same `## [Unreleased]`
# section, so two PRs sharing no source file still collide there. Six did in beesknees-mcp
# in one day. `changelog.d/` gives each change its own file, and files nobody else touches
# never conflict.
#
# Canonical set: scripts/changelog-fragments/ — changelog.py (the fold), the changelog.d
# README, the tests, and adopt.py which installs them into one repo and MIGRATES that
# repo's existing [Unreleased] section into fragments. Installing without migrating leaves
# the anchor in place and changes nothing, which is why adopt.py does both.
#
# Usage:
#   scripts/sync-changelog-fragments.sh [repo ...]
#
# With no repo args it DISCOVERS the fleet from the checkouts under the working directory
# (each subdir that is a git repo with a github.com/$OWNER origin), exactly as
# sync-factory-callers.sh does. Override the scan root with ROOT=..., the owner with
# OWNER=..., or pass explicit repos as args.
#
# Each repo is done in a throwaway clone; your working checkouts are never touched. A repo
# with no tests/ is reported "not applicable" and skipped — the guard that stops a release
# shipping with its fragments unfolded is a pytest, and would be inert there. A repo with no
# pyproject.toml still adopts; that one guard skips itself and says why. No pyproject.toml is fine; that one guard skips.
#
# Set MERGE=admin to also squash-merge each PR. Default leaves them open: this rewrites
# CHANGELOG.md, and a changelog is somebody's account of what they did to the money.
set -euo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)"
ADOPT="$SELF/changelog-fragments/adopt.py"
[ -f "$ADOPT" ] || { echo "canonical set not found: $ADOPT" >&2; exit 1; }

ENV_FILE="${ENV_FILE:-$SELF/../.env}"
if [ -f "$ENV_FILE" ]; then set -a; . "$ENV_FILE"; set +a; fi
OWNER="${OWNER:-lonniev}"
ROOT="${ROOT:-$(cd "$SELF/../.." && pwd)}"
MERGE="${MERGE:-}"
BRANCH="changelog-fragments"

discover_fleet() {
  local d url slug
  for d in "$ROOT"/*/; do
    [ -e "$d/.git" ] || continue
    url="$(git -C "$d" remote get-url origin 2>/dev/null)" || continue
    case "$url" in
      *github.com[:/]*) slug="$(printf '%s' "$url" | sed -E 's#.*github\.com[:/]([^/]+/[^/]+)#\1#; s#\.git$##')" ;;
      *) continue ;;
    esac
    case "$slug" in "$OWNER"/*) printf '%s\n' "$slug" ;; esac
  done | sort -u
}

if [ "$#" -gt 0 ]; then
  repos=("$@")
else
  mapfile -t repos < <(discover_fleet)
  echo "Discovered ${#repos[@]} $OWNER repo(s) under $ROOT:"
  printf '  %s\n' "${repos[@]}"
  read -rp "Adopt the changelog-fragment convention in all of these? [y/N] " ans
  [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "aborted."; exit 0; }
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

synced=0; uptodate=0; skipped=0
declare -a PRS=()

for r in "${repos[@]}"; do
  case "$r" in */*) full="$r";; *) full="$OWNER/$r";; esac
  if ! gh repo view "$full" >/dev/null 2>&1; then
    echo "-- $full: skip (no access / not found)"; skipped=$((skipped+1)); continue
  fi

  work="$TMP/${full##*/}"
  if ! gh repo clone "$full" "$work" -- --depth 1 --quiet >/dev/null 2>&1; then
    echo "-- $full: skip (clone failed)"; skipped=$((skipped+1)); continue
  fi

  # Push via the ACTIVE gh token — a fresh clone's credential helper can resolve a broken
  # secondary account. Same reasoning as sync-factory-callers.sh.
  git -C "$work" remote set-url origin \
    "https://x-access-token:$(gh auth token)@github.com/$full.git"

  out="$(python3 "$ADOPT" "$work")" || {
    case "$?" in
      3) echo "-- $full: skip (not applicable — no tests/)";;
      *) echo "-- $full: skip (adopt.py failed)";;
    esac
    skipped=$((skipped+1)); continue
  }
  echo "-- $out"

  if [ -z "$(git -C "$work" status --porcelain)" ]; then
    echo "   already in sync"; uptodate=$((uptodate+1)); continue
  fi

  default="$(git -C "$work" symbolic-ref --short HEAD)"
  git -C "$work" checkout -q -b "$BRANCH"
  git -C "$work" add -A
  git -C "$work" -c user.name="DPYC Factory" -c user.email="noreply@anthropic.com" \
    commit -q -m "chore: one changelog file per change, so independent PRs stop conflicting

Every PR appended to the same anchors of the same [Unreleased] section, so two
PRs sharing no source file still collided there. Fragments in changelog.d/ give
each change its own file; scripts/changelog.py folds them at release time and a
pytest refuses a release that left its fragments behind.

The existing [Unreleased] section is migrated into fragments, not dropped —
leaving it in place would leave the conflict anchor in place.

Canonical source: dpyc-community/scripts/changelog-fragments/.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"

  git -C "$work" push -q origin --delete "$BRANCH" >/dev/null 2>&1 || true
  if ! err=$(git -C "$work" push -u origin "$BRANCH" 2>&1); then
    echo "   skip (push failed: $(printf '%s' "$err" | tail -1))"; skipped=$((skipped+1)); continue
  fi

  url="$(gh pr create --repo "$full" --base "$default" --head "$BRANCH" \
    --title "chore: one changelog file per change" \
    --body "\`CHANGELOG.md\` was the most conflict-prone file in this repo for a structural reason: every PR appended to the same \`### Added\` / \`### Fixed\` anchors of the same \`## [Unreleased]\` section, so two PRs that shared no source file still collided there.

- \`changelog.d/\` — one file per change, named \`<kind>-<slug>.md\`. Two PRs never touch the same file.
- \`scripts/changelog.py fold X.Y.Z\` — gathers them into one Keep a Changelog section at release time, in filename order, so merge order never reaches the output.
- \`tests/test_changelog.py\` — holds the order-independence as a property, and refuses a release whose fragments were never folded.

**Check the CHANGELOG.md diff.** The existing \`[Unreleased]\` section is migrated into fragments rather than dropped; leaving it would leave the conflict anchor.

Canonical source: \`dpyc-community/scripts/changelog-fragments/\`. Fix it there.

🤖 Generated with [Claude Code](https://claude.com/claude-code)" 2>/dev/null || \
    gh pr view "$full" --json url --jq .url 2>/dev/null || echo "(PR exists)")"
  echo "   PR $url"
  PRS+=("$full $url")
  synced=$((synced+1))

  if [ "$MERGE" = "admin" ]; then
    if gh pr merge "$url" --repo "$full" --squash --admin >/dev/null 2>&1; then
      echo "   merged (admin)"
    else
      echo "   merge deferred (CI/gates pending — merge manually)"
    fi
  fi
done

echo
echo "Done. $synced PR(s) opened, $uptodate already in sync, $skipped skipped."
[ "${#PRS[@]}" -gt 0 ] && printf '  %s\n' "${PRS[@]}"
[ "$MERGE" = "admin" ] || echo "Review the CHANGELOG.md diffs before merging."
