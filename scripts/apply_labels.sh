#!/usr/bin/env bash
# Apply the DPYC Agentic Desk label taxonomy to a repo (idempotent; --force updates).
#
# Usage:  scripts/apply_labels.sh <owner/repo>
# Example: scripts/apply_labels.sh lonniev/tollbooth-sample
#
# The taxonomy is the shared contract the Service Desk / Engineering / QA workflows rely
# on. Run this once per repo when onboarding it to the pipeline.
set -euo pipefail

REPO="${1:?usage: apply_labels.sh <owner/repo>}"

# name|color|description   (color is a 6-hex code, no leading #)
labels=(
  "type/bug|d73a4a|A defect in existing behavior"
  "type/feature|a2eeef|A new capability or enhancement"
  "type/docs|0075ca|Documentation only"
  "type/question|d876e3|A question, not a change request"
  "type/chore|c5def5|Maintenance, deps, tooling"

  "area/ledger|bfd4f2|Credits, balances, demurrage"
  "area/pricing|bfd4f2|Pricing model / constraints"
  "area/vault|bfd4f2|Vault, credentials, Secure Courier"
  "area/auth|bfd4f2|Identity proof, ACL, OAuth"
  "area/ci|bfd4f2|CI / build / release"
  "area/docs|bfd4f2|Docs / README / copy"
  "area/ui|bfd4f2|Frontend / UI"

  "sev/critical|b60205|Money, security, or data-loss impact"
  "sev/high|d93f0b|Broken core behavior"
  "sev/medium|fbca04|Degraded but usable"
  "sev/low|0e8a16|Minor / cosmetic"

  "agent/fix|5319e7|Handed to the Engineering agent"
  "agent/working|1d76db|An agent is actively working this issue right now"
  "blocked/upstream|e99695|Fix belongs in the SDK or a sibling repo"
  "rejected/upstream|e99695|Target repo declined an escalation; routes the reason back to the origin"
  "blocked/arbitration|b60205|Routing standoff — two repos disagree on ownership; a human must decide"

  "rejected/spam|cfd3d7|Advertising / junk; closed"
  "rejected/out-of-scope|cfd3d7|Out of this repo's scope; closed"
  "rejected/injection|cfd3d7|Prompt-injection attempt; closed"
  "rejected/wontfix|cfd3d7|Working as intended; closed"
  "rejected/duplicate|cfd3d7|Duplicates an existing issue; closed"
  "rejected/needs-info|fef2c0|Awaiting reproduction / details; open"

  "qa/pass|0e8a16|QA verified the PR"
  "qa/flag|d93f0b|QA raised a concern on the PR"

  "awaiting-funds|b60205|Deferred: factory out of LLM credits; canary re-runs on recovery"
  "agent/retriage|5319e7|Replay marker: re-fire Porter after a funding outage"
)

for entry in "${labels[@]}"; do
  IFS='|' read -r name color desc <<< "$entry"
  echo "  $name"
  gh label create "$name" --color "$color" --description "$desc" --repo "$REPO" --force >/dev/null
done

echo "Applied ${#labels[@]} labels to $REPO."
