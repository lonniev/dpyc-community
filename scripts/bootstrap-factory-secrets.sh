#!/usr/bin/env bash
# bootstrap-factory-secrets.sh — provision the DPYC Software Factory agent secrets
# across the working-directory repo estate. Interactive and idempotent; safe to re-run
# when a key rotates.
#
# Secrets it will set (only those actually present in the env file / environment):
#   PORTER_NSEC          Service Desk (Porter) Nostr secret key      [required]
#   JOURNEYMAN_NSEC      Engineering (Journeyman) Nostr secret key   [required]
#   ANTHROPIC_API_KEY    meters every agent run                      [optional here]
#   DPYC_BOT_APP_ID      GitHub App id for the chaining token        [optional here]
#
# The App private key (multiline .pem) is provisioned by set_pipeline_secrets.sh, not here.
#
# Usage:
#   scripts/bootstrap-factory-secrets.sh [--env FILE] [repo ...]
#     --env FILE   env file to source (default: dpyc-community/.env). MUST be gitignored.
#     repo ...     explicit repos (owner/name or bare name); default = discovered estate.
#
# ── Handling rules (enforced below) ─────────────────────────────────────────────
#   • Every value is piped to `gh` on STDIN, never as an argv --body — keeps it out of
#     the process table and shell history.
#   • Only secret NAMES are ever printed. No value is echoed, logged, or written to a file.
#   • The env file must be gitignored. Per doctrine, prefer not persisting an nsec on disk:
#     if you use an env file, treat it as sensitive and shred it afterward. If an nsec ever
#     appears in a file, a log, a commit, or a chat, consider it BURNED — rotate it and
#     republish the NIP-05.
#   • The fork-secrets property is load-bearing: GitHub does not pass repo secrets to
#     workflows triggered by pull_request from a fork. Never use pull_request_target.
set -euo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)"
OWNER="${OWNER:-lonniev}"
ENV_FILE="$SELF/../.env"

# --- parse args: --env FILE, --yes, then repos ---
repos=()
ASSUME_YES=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --env) ENV_FILE="$2"; shift 2 ;;
    --env=*) ENV_FILE="${1#--env=}"; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    *) repos+=("$1"); shift ;;
  esac
done

# --- preconditions (per Task 1 runbook) ---
# Test the ACTIVE token functionally: `gh auth status` exits non-zero if ANY configured
# account is broken, even when the active one is fine, so probe the API instead.
if ! gh api user >/dev/null 2>&1; then
  echo "gh's active token can't reach the API. Run: gh auth login (or gh auth switch)" >&2; exit 1
fi
if ! gh auth status --active 2>&1 | grep -q "'repo'"; then
  echo "⚠️  gh token may lack the 'repo' scope that 'gh secret set' requires." >&2
  echo "   If setting secrets fails, run: gh auth refresh -s repo" >&2
fi

# --- load the env file WITHOUT echoing anything ---
if [ -f "$ENV_FILE" ]; then
  echo "Loading secrets from $ENV_FILE (values not shown)"
  set -a; . "$ENV_FILE"; set +a
else
  echo "No env file at $ENV_FILE — will prompt for any missing required secret."
fi

# Interactive hidden fallback for the two required nsecs if the env file didn't supply them.
if [ -z "${PORTER_NSEC:-}" ]; then read -rsp "PORTER_NSEC (hidden): " PORTER_NSEC; echo; fi
if [ -z "${JOURNEYMAN_NSEC:-}" ]; then read -rsp "JOURNEYMAN_NSEC (hidden): " JOURNEYMAN_NSEC; echo; fi
[ -n "${PORTER_NSEC:-}" ] && [ -n "${JOURNEYMAN_NSEC:-}" ] || { echo "both nsecs are required" >&2; exit 1; }

# --- discover the repo estate from working-dir checkouts (never the whole account) ---
discover_fleet() {
  local root d url slug
  root="$(cd "$SELF/../.." && pwd)"
  for d in "$root"/*/; do
    [ -e "$d/.git" ] || continue
    url="$(git -C "$d" remote get-url origin 2>/dev/null)" || continue
    case "$url" in *github.com[:/]*) : ;; *) continue ;; esac
    slug="$(printf '%s' "$url" | sed -E 's#.*github\.com[:/]([^/]+/[^/]+)#\1#; s#\.git$##')"
    case "$slug" in "$OWNER"/*) printf '%s\n' "$slug" ;; esac
  done | sort -u
}

if [ "${#repos[@]}" -eq 0 ]; then
  # bash 3.2 (macOS default) has no mapfile — read the discovered repos line by line.
  while IFS= read -r line; do [ -n "$line" ] && repos+=("$line"); done < <(discover_fleet)
  echo "Discovered ${#repos[@]} $OWNER repo(s) under the working directory:"
  printf '  %s\n' "${repos[@]}"
  if [ "$ASSUME_YES" -ne 1 ]; then
    read -rp "Set the factory secrets in all of these? [y/N] " ans
    [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "aborted."; exit 0; }
  fi
fi

# --- set the secrets that are present; print NAMES only ---
set_secret() {  # $1=name $2=value $3=repo
  [ -n "$2" ] || return 0
  printf '%s' "$2" | gh secret set "$1" --repo "$3" --app actions >/dev/null
  printf '     %s\n' "$1"
}

failures=0
for r in "${repos[@]}"; do
  case "$r" in */*) full="$r";; *) full="$OWNER/$r";; esac
  echo "-- $full"
  if ! gh repo view "$full" >/dev/null 2>&1; then
    echo "   skip (no access / not found)"; continue
  fi
  set_secret PORTER_NSEC        "${PORTER_NSEC:-}"        "$full"
  set_secret JOURNEYMAN_NSEC    "${JOURNEYMAN_NSEC:-}"    "$full"
  set_secret ANTHROPIC_API_KEY  "${ANTHROPIC_API_KEY:-}" "$full"
  set_secret DPYC_BOT_APP_ID    "${DPYC_BOT_APP_ID:-}"   "$full"
  # verify the two required nsecs landed (names only)
  have=$(gh secret list --repo "$full" --app actions 2>/dev/null | awk '{print $1}')
  for req in PORTER_NSEC JOURNEYMAN_NSEC; do
    printf '%s\n' "$have" | grep -qx "$req" || { echo "   ✗ MISSING $req"; failures=$((failures+1)); }
  done
done

if [ "$failures" -gt 0 ]; then
  echo "Done with $failures missing-secret failure(s)." >&2; exit 1
fi
echo "Done. Factory nsecs provisioned across ${#repos[@]} repo(s)."
