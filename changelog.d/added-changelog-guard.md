- **A PR may not add a line to `CHANGELOG.md`.** The fragment convention removed
  the anchor that made any two open PRs conflict, and nothing enforced it; a PR
  that still wrote its bullet there put the anchor straight back. The reusable
  `changelog-guard.yml` fails such a PR (a release PR, title beginning
  "release", is exempt), and `adopt.py` installs the thin caller with the rest.
- `adopt.py` adopts a repo with no `tests/` too — the fragments and the fold are
  what stop the conflicts; only the unfolded-release pytest is skipped, and the
  run says so. `sync-changelog-fragments.sh` opens each PR as the factory App
  and wakes its CI, as every PR not written by the owner is opened.
