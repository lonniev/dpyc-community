- **The changelog convention, hoisted to the shared home.**
  `scripts/changelog-fragments/` is now the canonical set — `changelog.py` (the
  fold), the `changelog.d/README.md` that states the convention, the tests that
  hold it as a property, and `adopt.py` which installs all three into one repo.
  `scripts/sync-changelog-fragments.sh` fans it out the way
  `sync-factory-callers.sh` fans out the factory callers: throwaway clones, one
  PR per repo, discovery from the checkouts under the working directory.

  `CHANGELOG.md` was the fleet's most conflict-prone file for a structural
  reason rather than a careless one. Every PR appended to the same
  `### Added` / `### Fixed` anchors of the same `## [Unreleased]` section, so
  two PRs sharing no source file still collided there — six did in
  `beesknees-mcp` in one day. One file per change removes the anchor; files
  nobody else touches never conflict.

- **Adoption migrates the existing `[Unreleased]` section rather than leaving
  it.** Installing the machinery and keeping the section is the null change:
  the next two PRs collide on it exactly as before. `adopt.py` lifts every
  entry into a fragment, keeps prose that was under no heading (as `notes`),
  keeps an invented heading's content (also as `notes`) rather than dropping
  it, and removes the section **even when it was empty** — an empty
  `[Unreleased]` is still the anchor the next PR writes under.

- **This repo adopted it first.** Its own empty `[Unreleased]` is gone and this
  entry is a fragment. It has no `pyproject.toml` — it versions itself by git
  tag — so the guard that refuses a release with unfolded fragments skips
  itself here and says why; the fold and the order-independence do not need a
  version file.
