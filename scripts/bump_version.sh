#!/usr/bin/env bash
set -euo pipefail

DEFAULT_BRANCH="main"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <poetry version args>  (e.g. patch, minor, major, 1.2.3)"
  exit 1
fi

# ensure required tools are available
command -v git &>/dev/null || { echo "❌ git is required."; exit 1; }
command -v poetry &>/dev/null || { echo "❌ poetry is required."; exit 1; }

# prevent bumping with uncommitted changes that would be lost
if [[ -n $(git status --porcelain) ]]; then
  echo "❌ Git repo is dirty. Commit or stash changes first."
  exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)

# fetch latest remote state so sync checks below are accurate
if ! git fetch origin "$BRANCH"; then
  echo "❌ Failed to fetch origin/$BRANCH"
  exit 1
fi

# Bump from main: require exact sync with upstream, then create a release branch.
bump_on_main() {
  local version=$1

  # main must match upstream exactly — no unpushed or missing commits
  if ! git diff --quiet HEAD "@{u}"; then
    echo "❌ Branch is not in sync with origin/$DEFAULT_BRANCH"
    exit 1
  fi

  # prevent overwriting an existing release branch for the same version
  if git show-ref --verify --quiet "refs/heads/release/v$version"; then
    echo "❌ Branch release/v$version already exists."
    exit 1
  fi

  RELEASE_BRANCH="release/v$version"
  git checkout -b "$RELEASE_BRANCH"
  git add pyproject.toml
  git commit -m "chore(release): bump to v$version

Bump version in pyproject.toml to v$version.
Release branch created from $DEFAULT_BRANCH."

  echo "✅ Bumped to v$version on $RELEASE_BRANCH."
  echo ""
  echo "Next steps:"
  echo "  git push -u origin $RELEASE_BRANCH"
  echo "  gh pr create --base $DEFAULT_BRANCH"
}

# Bump from a feature/release branch: allow unpushed commits, block if behind remote.
bump_on_branch() {
  local version=$1

  # allow being ahead (unpushed commits), but block if remote has commits we're missing
  BEHIND=$(git rev-list --count HEAD..origin/"$BRANCH")
  if [[ "$BEHIND" -gt 0 ]]; then
    echo "❌ Branch is not in sync with origin/$BRANCH (you are $BEHIND commit(s) behind)"
    exit 1
  fi

  git add pyproject.toml
  git commit -m "chore(release): bump to v$version

Bump version in pyproject.toml to v$version."

  echo "✅ Bumped to v$version on $BRANCH."
  echo ""
  echo "Next steps:"
  echo "  git push"
}

poetry version "$@"
VERSION=$(poetry version -s)

if [[ "$BRANCH" == "$DEFAULT_BRANCH" ]]; then
  bump_on_main "$VERSION"
else
  bump_on_branch "$VERSION"
fi
