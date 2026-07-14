#!/usr/bin/env bash
# Set the three Agentic Desk pipeline secrets across DPYC repos, idempotently.
#
#   DPYC_BOT_APP_ID       the GitHub App id           (default 4292331; override via env APP_ID)
#   DPYC_BOT_PRIVATE_KEY  the App's .pem contents     (from the file arg)
#   ANTHROPIC_API_KEY     the Anthropic API key       (env ANTHROPIC_API_KEY, else prompted hidden)
#
# Usage:
#   scripts/set_pipeline_secrets.sh <path-to-app-private-key.pem> [repo ...]
#
# With no repo args it DISCOVERS the fleet from the checkouts under the working
# directory (each subdir that is a git repo with a github.com/$OWNER origin) — so it
# only ever touches repos you actually have here, never legacy cruft elsewhere in the
# account. Override the scan root with ROOT=..., or pass explicit repos as args.
# Every secret value is passed via stdin — never argv — so it won't appear in `ps`
# or shell history.
set -euo pipefail

OWNER="${OWNER:-lonniev}"
APP_ID="${APP_ID:-4292331}"

PEM="${1:?usage: set_pipeline_secrets.sh <private-key.pem> [repo ...]}"
shift || true
[ -f "$PEM" ] || { echo "private key file not found: $PEM" >&2; exit 1; }

# Anthropic key: from env if set, else prompt without echo (keeps it out of history).
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  read -rsp "Anthropic API key (sk-ant-...): " ANTHROPIC_API_KEY; echo
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "no Anthropic key provided" >&2; exit 1; }

# Discover the fleet from checkouts under the working directory. The script lives in
# dpyc-community/scripts/, so the DPYC working dir is two levels up by default.
SELF="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-$(cd "$SELF/../.." && pwd)}"

discover_fleet() {
  local d url slug
  for d in "$ROOT"/*/; do
    [ -e "$d/.git" ] || continue
    url="$(git -C "$d" remote get-url origin 2>/dev/null)" || continue
    case "$url" in
      *github.com[:/]*) slug="$(printf '%s' "$url" | sed -E 's#.*github\.com[:/]([^/]+/[^/]+)#\1#; s#\.git$##')" ;;
      *) continue ;;
    esac
    # Only repos owned by $OWNER (skip forks of other people's repos).
    case "$slug" in "$OWNER"/*) printf '%s\n' "$slug" ;; esac
  done | sort -u
}

if [ "$#" -gt 0 ]; then
  repos=("$@")
else
  mapfile -t repos < <(discover_fleet)
  echo "Discovered ${#repos[@]} $OWNER repo(s) under $ROOT:"
  printf '  %s\n' "${repos[@]}"
  read -rp "Set pipeline secrets in all of these? [y/N] " ans
  [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "aborted."; exit 0; }
fi

ok=0; skipped=0
for r in "${repos[@]}"; do
  case "$r" in */*) full="$r";; *) full="$OWNER/$r";; esac
  if ! gh repo view "$full" >/dev/null 2>&1; then
    echo "-- $full: skip (no access / not found)"; skipped=$((skipped+1)); continue
  fi
  printf '%s' "$APP_ID"            | gh secret set DPYC_BOT_APP_ID      --repo "$full" >/dev/null
  gh secret set DPYC_BOT_PRIVATE_KEY --repo "$full" < "$PEM"                            >/dev/null
  printf '%s' "$ANTHROPIC_API_KEY" | gh secret set ANTHROPIC_API_KEY    --repo "$full" >/dev/null
  echo "-- $full: set DPYC_BOT_APP_ID, DPYC_BOT_PRIVATE_KEY, ANTHROPIC_API_KEY"
  ok=$((ok+1))
done

echo "Done. $ok repo(s) updated, $skipped skipped."
