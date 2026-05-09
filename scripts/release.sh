#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <poetry version args>"
  exit 1
fi

# Detect default branch (no prerequisites) 
CURRENT_LOCAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
DEFAULT_BRANCH="main" # hardcoded default to avoid complexity of parsing git remote output
if [[ "$CURRENT_LOCAL_BRANCH" != "$DEFAULT_BRANCH" ]]; then
  echo "❌ Releases must be done from '$DEFAULT_BRANCH' (current: $CURRENT_LOCAL_BRANCH)"
  exit 1
fi

# Ensure clean repo
if [[ -n $(git status --porcelain) ]]; then
  echo "❌ Git repo is dirty. Commit or stash changes first."
  exit 1
fi

# Fetch latest changes to ensure we're up-to-date
if ! git fetch origin "$DEFAULT_BRANCH"; then
  echo "❌ Failed to fetch origin/$DEFAULT_BRANCH"
  exit 1
fi

# Ensure up to date with upstream
if ! git diff --quiet HEAD "@{u}"; then
  echo "❌ Branch is not in sync with origin/$DEFAULT_BRANCH"
  exit 1
fi

# Version bump (pass-through to Poetry)
poetry version "$@"
VERSION=$(poetry version -s)

trap 'echo "❌ Release failed. Check git log and tag list — manual cleanup may be required."' ERR

git add pyproject.toml
git commit -m "chore(release): v$VERSION"
git tag -a "v$VERSION" -m "Release v$VERSION"

# Confirm
read -r -p "🚀 Push release v$VERSION (CI will publish)? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || exit 0

git push --follow-tags

echo "✅ Released v$VERSION from $DEFAULT_BRANCH"
