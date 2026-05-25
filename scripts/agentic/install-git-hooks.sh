#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [[ ! -d ".git" ]]; then
  echo "ERROR: Not inside a Git repository."
  exit 1
fi

if [[ ! -x ".githooks/pre-push" ]]; then
  echo "ERROR: .githooks/pre-push is missing or not executable."
  exit 1
fi

git config core.hooksPath .githooks

echo "PASS: Git hooks installed."
echo "core.hooksPath=$(git config core.hooksPath)"
echo ""
echo "Pre-push hook:"
echo "  .githooks/pre-push"
echo ""
echo "The hook runs:"
echo "  scripts/agentic/agentic-gen.sh doctor-strict"
