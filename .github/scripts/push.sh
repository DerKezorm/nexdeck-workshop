#!/usr/bin/env bash
# Commits what a run changed in the entries, the catalog and the README list, and pushes it.
# Only the action's own paths are added; a run that changed nothing makes no commit.
set -euo pipefail
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A entries catalog.json README.md
if git diff --cached --quiet; then
  echo "Nothing to commit."
  exit 0
fi
git commit -q -m "${1:-Update the workshop}"
# The runs of the write actions go one after the other, so the push normally just works; a person pushing in between is the one case.
git push || { git pull --rebase -q && git push; }
