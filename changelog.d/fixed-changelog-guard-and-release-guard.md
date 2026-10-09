- The Changelog guard no longer rejects adoption: a line that only points the
  reader at `changelog.d/` is not an entry. The convention's pytest no longer
  fails every PR between releases (fragments present while `pyproject.toml`
  still names the last release is the normal state); the shared release
  workflow instead names a tag cut with fragments still unfolded.
