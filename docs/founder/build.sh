#!/usr/bin/env bash
# Regenerate LonnieVanZandt_2026.{html,pdf} from the markdown source.
#
# The .md is the ONLY source of truth; the .html and .pdf are generated artifacts.
# Run this after editing the markdown, or let the Generate Founder Resume workflow
# (.github/workflows/founder-docs.yml) do it on push to main.
#
# Requires: pandoc + a xelatex TeX install (texlive-xetex).
set -euo pipefail
cd "$(dirname "$0")"

SRC="LonnieVanZandt_2026.md"
TITLE="Lonnie VanZandt — CV April 2026"

# --- HTML ---------------------------------------------------------------
# Reuse the committed shell + CSS via template.html. Reproduce the original's
# conventions exactly: no header ids (-auto_identifiers), straight quotes
# (-smart), and unwrapped source lines (--wrap=preserve).
tmp="$(mktemp -t resume.XXXXXX).html"
pandoc "$SRC" \
  -f markdown-auto_identifiers-smart \
  -t html \
  --wrap=preserve \
  --template template.html \
  --metadata title="$TITLE" \
  -o "$tmp"
# pandoc 3.x emits <colgroup> width blocks the hand-authored original never had.
perl -0pe 's{<colgroup>.*?</colgroup>\n}{}gs' "$tmp" > LonnieVanZandt_2026.html
rm -f "$tmp"

# --- PDF ----------------------------------------------------------------
pandoc "$SRC" \
  --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V geometry:letterpaper \
  -V fontsize=11pt \
  -V colorlinks=true \
  -V urlcolor=RoyalBlue \
  -V linkcolor=RoyalBlue \
  -o LonnieVanZandt_2026.pdf

echo "Regenerated LonnieVanZandt_2026.html and LonnieVanZandt_2026.pdf"
