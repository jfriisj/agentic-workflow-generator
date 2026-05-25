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

if command -v npx >/dev/null 2>&1; then
  npx --yes ajv-cli@5 validate \
    --spec=draft2020 \
    -s "$SCHEMA_FILE" \
    -d "$CONFIG_FILE"
  echo "PASS: Agentic config is valid."
  exit 0
fi

if command -v python >/dev/null 2>&1; then
  python - <<PY
import json
import sys

config_file = "$CONFIG_FILE"
schema_file = "$SCHEMA_FILE"

with open(config_file, "r", encoding="utf-8") as f:
    json.load(f)

with open(schema_file, "r", encoding="utf-8") as f:
    json.load(f)

print("PASS: JSON files are syntactically valid.")
print("WARN: JSON Schema validation was skipped because ajv-cli is not available.")
PY
  exit 0
fi

echo "ERROR: Neither npx nor python is available for validation." >&2
exit 1
