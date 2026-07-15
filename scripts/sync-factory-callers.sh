#!/usr/bin/env bash
# Sync the DPYC Software Factory thin callers into every repo, idempotently, in one batch.
#
# The callers are pure boilerplate — six identical files that only reference the reusable
# workflows in dpyc-community (@main). Their canonical source is scripts/factory-callers/;
# this script fans that set out so an already-onboarded repo picks up a NEW caller (e.g.
# agentic-pr-dialogue.yml) and a fresh peer gets the whole set at once.
#
# Usage:
#   scripts/sync-factory-callers.sh [repo ...]
#
# With no repo args it DISCOVERS the fleet from the checkouts under the working directory
# (each subdir that is a git repo with a github.com/$OWNER origin) — so it only ever touches
# repos you actually have here, never legacy cruft elsewhere. Override the scan root with
# ROOT=..., the owner with OWNER=..., or pass explicit repos as args.
#
# For each repo it works in a throwaway clone (your working checkouts are never touched):
# it drops in the canonical callers and, IF anything changed, pushes branch
# 'factory-callers-sync' and opens a PR. Nothing changed ⇒ reported as already in sync.
# Set MERGE=admin to also `gh pr merge --squash --admin` each PR (use once you trust it);
# default leaves the PRs open for review (workflow files run with secrets — worth a look).
#
# This propagates the CALLERS only. A fresh peer also needs, separately:
#   scripts/apply_labels.sh <repo>              # the 26-label taxonomy the Porter writes
#   .github/CODEOWNERS                          # the money-path human gate
#   scripts/set_pipeline_secrets.sh <pem> <repo>        # App id/key + Anthropic
#   scripts/bootstrap-factory-secrets.sh                # PORTER_NSEC / JOURNEYMAN_NSEC
#   branch protection (per-repo: its own CI check names) — deliberately NOT blanket-applied.
set -euo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)"
CALLERS_DIR="$SELF/factory-callers"
[ -d "$CALLERS_DIR" ] || { echo "canonical callers not found: $CALLERS_DIR" >&2; exit 1; }

ENV_FILE="${ENV_FILE:-$SELF/../.env}"
if [ -f "$ENV_FILE" ]; then set -a; . "$ENV_FILE"; set +a; fi
OWNER="${OWNER:-lonniev}"
ROOT="${ROOT:-$(cd "$SELF/../.." && pwd)}"
MERGE="${MERGE:-}"
BRANCH="factory-callers-sync"

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
  read -rp "Sync factory callers into all of these? [y/N] " ans
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
  # Shallow clone of just the default branch; gh uses your auth. Quiet on success.
  if ! gh repo clone "$full" "$work" -- --depth 1 --quiet >/dev/null 2>&1; then
    echo "-- $full: skip (clone failed)"; skipped=$((skipped+1)); continue
  fi

  mkdir -p "$work/.github/workflows"
  cp "$CALLERS_DIR"/*.yml "$work/.github/workflows/"
  # Add the money-path CODEOWNERS gate only if the repo doesn't already have one
  # (never clobber a repo's own ownership rules).
  [ -f "$work/.github/CODEOWNERS" ] || cp "$SELF/factory-CODEOWNERS" "$work/.github/CODEOWNERS"

  if [ -z "$(git -C "$work" status --porcelain -- .github/)" ]; then
    echo "-- $full: already in sync"; uptodate=$((uptodate+1)); continue
  fi

  default="$(git -C "$work" symbolic-ref --short HEAD)"
  git -C "$work" checkout -q -b "$BRANCH"
  git -C "$work" add .github/workflows/agentic-*.yml .github/CODEOWNERS
  git -C "$work" -c user.name="DPYC Factory" -c user.email="noreply@anthropic.com" \
    commit -q -m "ci: sync DPYC Software Factory callers

Fan out the canonical thin callers from dpyc-community/scripts/factory-callers/
so this repo runs the current factory set (incl. the @journeyman PR-dialogue
reviewer). Callers are pure boilerplate — all logic lives in the reusable
workflows they call (dpyc-community @main).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"

  if ! git -C "$work" push -q -u origin "$BRANCH" --force-with-lease 2>/dev/null; then
    echo "-- $full: skip (push denied)"; skipped=$((skipped+1)); continue
  fi

  url="$(gh pr create --repo "$full" --base "$default" --head "$BRANCH" \
    --title "ci: sync DPYC Software Factory callers" \
    --body "Fans out the canonical thin callers from \`dpyc-community/scripts/factory-callers/\`, so this repo runs the current factory set — including the \`@journeyman\` PR-dialogue reviewer. All logic lives in the reusable workflows these call (dpyc-community @main); the callers themselves are boilerplate.

🤖 Generated with [Claude Code](https://claude.com/claude-code)" 2>/dev/null || \
    gh pr view "$full" --json url --jq .url 2>/dev/null || echo "(PR exists)")"
  echo "-- $full: PR $url"
  PRS+=("$full $url")
  synced=$((synced+1))

  if [ "$MERGE" = "admin" ]; then
    if gh pr merge "$url" --repo "$full" --squash --admin >/dev/null 2>&1; then
      echo "     merged (admin)"
    else
      echo "     merge deferred (CI/gates pending — merge manually)"
    fi
  fi
done

echo
echo "Done. $synced PR(s) opened, $uptodate already in sync, $skipped skipped."
[ "${#PRS[@]}" -gt 0 ] && printf '  %s\n' "${PRS[@]}"
[ "$MERGE" = "admin" ] || echo "Review + merge the PRs (or re-run with MERGE=admin to auto-merge)."
