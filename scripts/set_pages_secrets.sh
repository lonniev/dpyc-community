#!/usr/bin/env bash
# set_pages_secrets.sh — provision the Cloudflare Pages deploy secrets on repos
# that ship a frontend. Interactive and idempotent; safe to re-run on rotation.
#
# Secrets it sets:
#   CLOUDFLARE_API_TOKEN   Pages-scoped deploy token   [required]
#   CLOUDFLARE_ACCOUNT_ID  the account the project lives in  [required]
#
# Only these two. The token deploys a Pages project and can do nothing else —
# notably it cannot create the DNS record a custom domain needs, which is why
# `deploy-frontend.yml` attaches the domain but someone still adds the CNAME by
# hand in the dashboard.
#
# Usage:
#   scripts/set_pages_secrets.sh [repo ...]
#     repo ...   explicit repos (owner/name or bare name). With none, it offers
#                the repos under the working directory that actually have a
#                frontend/ — a deploy secret on a repo with nothing to deploy is
#                just another secret to rotate.
#
# ── Handling rules (same as the sibling scripts) ────────────────────────────
#   • Values are piped to `gh` on STDIN, never as an argv --body — keeps them out
#     of the process table and shell history.
#   • Only secret NAMES are printed. No value is echoed, logged, or written out.
#   • Run this from a REAL TERMINAL. `gh secret set` needs a TTY; from an agent
#     harness it stores an EMPTY secret and says nothing, and an empty token
#     fails exactly like a missing one, later, in a workflow log.
set -euo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)"
OWNER="${OWNER:-lonniev}"

# Convenience: load dpyc-community/.env if present (gitignored). It may set
# CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID so you don't retype them.
# Values already in the environment win over the file.
ENV_FILE="${ENV_FILE:-$SELF/../.env}"
if [ -f "$ENV_FILE" ]; then
  echo "Loading $ENV_FILE"
  set -a; . "$ENV_FILE"; set +a
fi

# The account id is not a secret in the usual sense, but GitHub has one drawer
# and the workflow reads both from it, so both go in the same way.
if [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  read -rp "Cloudflare account id: " CLOUDFLARE_ACCOUNT_ID; echo
fi
[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ] || { echo "no account id provided" >&2; exit 1; }

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  read -rsp "Cloudflare API token (Pages:Edit): " CLOUDFLARE_API_TOKEN; echo
fi
[ -n "${CLOUDFLARE_API_TOKEN:-}" ] || { echo "no API token provided" >&2; exit 1; }

# Discover repos under the working directory that actually ship a frontend.
ROOT="${ROOT:-$(cd "$SELF/../.." && pwd)}"

discover_frontends() {
  local d url slug
  for d in "$ROOT"/*/; do
    [ -e "$d/.git" ] || continue
    [ -d "$d/frontend" ] || continue
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
  mapfile -t repos < <(discover_frontends)
  [ "${#repos[@]}" -gt 0 ] || { echo "no repos with a frontend/ found under $ROOT" >&2; exit 1; }
  echo "Found ${#repos[@]} repo(s) with a frontend under $ROOT:"
  printf '  %s\n' "${repos[@]}"
  read -rp "Set Cloudflare Pages secrets in all of these? [y/N] " ans
  [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "aborted."; exit 0; }
fi

ok=0; skipped=0
for r in "${repos[@]}"; do
  case "$r" in */*) full="$r";; *) full="$OWNER/$r";; esac
  if ! gh repo view "$full" >/dev/null 2>&1; then
    echo "-- $full: skip (no access / not found)"; skipped=$((skipped+1)); continue
  fi
  printf '%s' "$CLOUDFLARE_API_TOKEN"  | gh secret set CLOUDFLARE_API_TOKEN  --repo "$full" >/dev/null
  printf '%s' "$CLOUDFLARE_ACCOUNT_ID" | gh secret set CLOUDFLARE_ACCOUNT_ID --repo "$full" >/dev/null
  echo "-- $full: set CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID"
  ok=$((ok+1))
done

echo "Done. $ok repo(s) updated, $skipped skipped."
echo
echo "Verify with:   gh secret list --repo $OWNER/<repo>"
echo "A name listed is not proof of a value — the deploy is. Push to frontend/**"
echo "or run the Deploy Frontend workflow and watch it land."
