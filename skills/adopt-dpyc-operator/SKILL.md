---
name: adopt-dpyc-operator
description: Bring a repo you own into the DPYC Software Factory — CODEOWNERS, the agentic workflows, the pipeline secrets, branch protection, auto-merge, and the MCP registry entry. Use after `bootstrap-dpyc-operator` has produced a working operator, or when an existing repo of yours is missing the factory apparatus. NOT for operators other people own.
license: Apache-2.0
---

# Adopt an operator into the Factory

`bootstrap-dpyc-operator` builds an operator **anyone** can run: it wraps an API, joins the
network, and takes sats. This skill does the other half, and it is **owner-only**.

Everything here binds the repo to one identity: `@lonniev` in CODEOWNERS, the factory App's
private key, the Porter and Journeyman nsecs, reusable workflows in `lonniev/dpyc-community`,
and an `io.github.lonniev/*` name in the MCP registry. Someone else running this would produce
a repo that answers to a person who is not them. That is why it lives here and not in the
public exemplar.

## The distinction worth holding

A repo can be a **working operator** and not be **adopted**. roastify-mcp was exactly that for
a day: live, credentialled, priced, serving real data — and merging its own commits straight
to `main` with no code-owner gate, no doctrine lint, no GitHub Release on a tag, and absent
from the registry. Nothing failed, because nothing was watching. Adoption is what makes the
repo's mistakes visible.

## Procedure

### 1. Confirm this is yours to adopt
The repo must be under your account and intended for the factory. If you are helping someone
build a DPYC operator they will own, stop — `bootstrap-dpyc-operator` is the whole job.

### 2. Copy the furniture from the live exemplar
Clone `tollbooth-sample` fresh; never copy from memory or from a sibling that may have drifted.

```bash
git clone --depth 1 https://github.com/lonniev/tollbooth-sample.git /tmp/exemplar
```

Take, verbatim unless noted:

| From the exemplar | Adapt? |
|---|---|
| `.github/CODEOWNERS` | **yes** — rewrite the propagation note (below) |
| `.github/workflows/agentic-*.yml` (all of them) | no — thin callers into `dpyc-community` |
| `.github/workflows/doctrine-lint.yml` | no |
| `.github/workflows/release.yml` | no |
| `.github/workflows/publish-mcp-registry.yml` | no |
| `server.json` | **yes** — name, description, repository URL, remote URL |
| `constraints/example_*.json` | no |

Diff rather than eyeball, so a newly added workflow is not silently skipped:

```bash
for f in $(cd /tmp/exemplar && find .github server.json constraints -type f | sort); do
  [ -f "$f" ] || echo "MISSING: $f"
done
```

**CODEOWNERS keeps its shape and changes its note.** The shape is default-deny: catch-all
first (`* @lonniev`), carve-outs after (`/tests/`, `*.md`), because CODEOWNERS is
last-match-wins — written the other way round, any file not yet imagined lands unreviewed.
The note at the foot must describe *this* operator's sensitive surface, not the exemplar's
weather service. Name the specific thing a plausible-looking edit could break. For a
bring-your-own-key operator that is the credential gate: a default key added to the resolver
would hand one patron's world to every caller.

### 3. Repo settings
```bash
gh api repos/<owner>/<repo> --method PATCH -f allow_auto_merge=true
```
Not optional. `agentic-auto-merge.yml` calls `gh pr merge --auto`, and GitHub refuses that
outright — `Auto merge is not allowed for this repository` — when the toggle is off. The
workflow then fails on **every approved PR**, and it reads as a broken check rather than a
missing setting.

### 4. Branch protection
CODEOWNERS is an inert text file until protection requires code-owner review. Match the
exemplar rather than inventing a policy:

```bash
gh api repos/lonniev/tollbooth-sample/branches/main/protection \
  --jq '{checks: .required_status_checks.contexts,
         codeowners: .required_pull_request_reviews.require_code_owner_reviews,
         approvals: .required_pull_request_reviews.required_approving_review_count}'
```

Required checks name the *job*, not the workflow (e.g. `test (3.12)`), so read the target
repo's own CI job name before setting it — a context that never reports leaves every PR
blocked forever.

### 5. Pipeline secrets — five of them
Two scripts in `dpyc-community/scripts/`, split by what they carry:

```bash
scripts/bootstrap-factory-secrets.sh <repo>   # PORTER_NSEC, JOURNEYMAN_NSEC
scripts/set_pipeline_secrets.sh <app-key.pem> <repo>   # DPYC_BOT_APP_ID, DPYC_BOT_PRIVATE_KEY, ANTHROPIC_API_KEY
```

Both pipe values through stdin rather than argv, print only secret *names*, and read
`dpyc-community/.env` (gitignored) so nothing need be retyped. With no repo argument they
discover the estate from the checkouts under the working directory — pass the repo explicitly
when adopting just one.

⚠️ **Run these from a real terminal, not from an agent harness.** `gh secret set` needs a TTY;
without one it sets an **empty** secret and says nothing. An empty `DPYC_BOT_PRIVATE_KEY` fails
exactly like a missing one, several steps later, in a workflow log.

The account is a user, not an org, so there is no org-level fallback: every repo carries its
own five. Fork PRs never receive them, which is deliberate — never reach for
`pull_request_target` to work around it.

### 6. Verify, then let it prove itself
```bash
gh secret list --repo <owner>/<repo>          # expect five NAMES
gh api repos/<owner>/<repo>/branches/main/protection --jq .required_status_checks.contexts
gh run list --repo <owner>/<repo> --limit 5   # agentic runs green, not red
```

The real proof is the next PR: opened by the factory App, checks woken by a human-credential
commit, approved by you, landed by auto-merge. If any of those four steps needs a hand, the
adoption is incomplete — see `factory/README.md` for the PR procedure itself.

## What goes wrong

- **Taking only `ci.yml`.** The commonest failure, because the repo looks fine: tests run,
  CI is green, and nothing announces the absent gate. Diff the exemplar's `.github/`.
- **CODEOWNERS without branch protection.** A file that reads like a policy and enforces
  nothing.
- **`server.json` left with the exemplar's identity.** Publishes the wrong name and endpoint
  to the MCP registry, under your account.
- **Setting secrets from a harness.** Silent empties. See step 5.
- **Reaching for `gh pr merge --admin` when a PR stalls.** That bypasses the code-owner gate
  instead of satisfying it, on repos that move money. If a PR is blocked, find out which
  required check or review is missing — the answer is usually a repo setting from step 3 or 4.

## What NOT to do

- Do not run this against a repo someone else owns.
- Do not copy the factory files from a sibling operator; clone the exemplar. Siblings drift.
- Do not hardcode the App id, nsecs, or key paths into the repo. They live in secrets and in
  the gitignored `.env`.
- Do not weaken CODEOWNERS to make an agent's PR land unattended. The gate is the product.
