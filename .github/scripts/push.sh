#!/usr/bin/env bash
# Commits what a run changed in the entries, the catalog, the README list, the state and the orders, and pushes it.
# Only the action's own paths are added; a run that changed nothing makes no commit.
set -euo pipefail
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
for path in entries catalog.json README.md state.json orders; do
  if [ -e "$path" ] || git ls-files --error-unmatch "$path" >/dev/null 2>&1; then
    git add -A "$path"
  fi
done
if git diff --cached --quiet; then
  echo "Nothing to commit."
  exit 0
fi
git commit -q -m "${1:-Update the workshop}"
# The runs of the write actions go one after the other, so the push normally just works; a person pushing in between is the one case.
git push || { git pull --rebase -q && git push; }
