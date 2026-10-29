#!/usr/bin/env bash
# Commits what a run changed in the entries, the catalog, the README list, the state and the orders, and pushes it.
# Only the action's own paths are added; a run that changed nothing makes no commit.
#
# The checkout of the run keeps no credentials (persist-credentials: false), so the code that reads the text of a stranger
# finds none in .git/config. The key (GITHUB_TOKEN) is given to git for this one command line only.
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
branch="${GITHUB_REF_NAME:-main}"
auth=()
if [ -n "${GITHUB_TOKEN:-}" ]; then
  auth=(-c "http.https://github.com/.extraheader=AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 | tr -d '\n')")
fi
# The run took the newest main when it started, but a person may have pushed since, and the job that records an order (which has
# a group of its own) can run beside the others. So the newest main is taken in again before the push, and once more if the push
# is refused because main moved in between. A conflict stops the run with the error; it is never resolved by guessing.
update() { git "${auth[@]}" pull --rebase -q origin "$branch"; }
update
git "${auth[@]}" push origin "HEAD:$branch" || { update && git "${auth[@]}" push origin "HEAD:$branch"; }
