#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-.agentic/agentic.json}"
SCHEMA_FILE="${2:-.agentic/schemas/agentic.schema.json}"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

if [ ! -f "$SCHEMA_FILE" ]; then
  echo "ERROR: Schema file not found: $SCHEMA_FILE" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node is required for JSON Schema validation, but node was not found in PATH." >&2
  exit 1
fi

if ! NODE_VERSION="$(node --version 2>&1)"; then
  echo "ERROR: node is required for JSON Schema validation, but node failed to run." >&2
  echo "Node command: $(command -v node)" >&2
  echo "Node output:" >&2
  echo "$NODE_VERSION" >&2
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "ERROR: npx is required for JSON Schema validation, but npx was not found in PATH." >&2
  echo "Node command: $(command -v node)" >&2
  echo "Node version: $NODE_VERSION" >&2
  exit 1
fi

if ! NPX_VERSION="$(npx --version 2>&1)"; then
  echo "ERROR: npx is required for JSON Schema validation, but npx failed to run." >&2
  echo "Node command: $(command -v node)" >&2
  echo "Node version: $NODE_VERSION" >&2
  echo "npx command: $(command -v npx)" >&2
  echo "npx output:" >&2
  echo "$NPX_VERSION" >&2
  exit 1
fi

npx --yes ajv-cli@5 validate \
  --spec=draft2020 \
  -s "$SCHEMA_FILE" \
  -d "$CONFIG_FILE"

echo "PASS: Agentic config is valid."
