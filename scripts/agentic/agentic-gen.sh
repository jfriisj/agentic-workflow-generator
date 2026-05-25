#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-}"
TARGET="${2:-vscode-copilot}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/agentic/agentic-gen.sh validate
  scripts/agentic/agentic-gen.sh resolve
  scripts/agentic/agentic-gen.sh lock
  scripts/agentic/agentic-gen.sh generate [vscode-copilot]
  scripts/agentic/agentic-gen.sh check
  scripts/agentic/agentic-gen.sh all
  scripts/agentic/agentic-gen.sh status

Commands:
  validate   Validate .agentic/agentic.json against its JSON Schema.
  resolve    Resolve agents, targets, capabilities, and skills.
  lock       Generate .agentic/agentic-lock.json from config, registry, and scripts.
  generate   Generate target-specific output.
  check      Run syntax checks for scripts and JSON files.
  all        Run check, validate, resolve, lock, and generate.
  status     Show generated files and git status.
USAGE
}

require_file() {
  local file_path="$1"
  if [[ ! -f "$file_path" ]]; then
    echo "ERROR: Required file not found: $file_path" >&2
    exit 1
  fi
}

validate_json_files() {
  find registry .agentic -name "*.json" -print0 | xargs -0 -r -n1 python -m json.tool >/dev/null
  echo "PASS: JSON files are syntactically valid."
}

check_scripts() {
  require_file "scripts/agentic/validate-agentic-config.sh"
  require_file "scripts/agentic/resolve-agentic-config.py"
  require_file "scripts/agentic/generate-vscode-copilot.py"
  require_file "scripts/agentic/generate-lockfile.py"

  bash -n "scripts/agentic/validate-agentic-config.sh"
  bash -n "scripts/agentic/agentic-gen.sh"
  python -m py_compile "scripts/agentic/resolve-agentic-config.py"
  python -m py_compile "scripts/agentic/generate-vscode-copilot.py"
  python -m py_compile "scripts/agentic/generate-lockfile.py"

  echo "PASS: Script syntax checks passed."
}

generate_target() {
  local target="$1"

  case "$target" in
    vscode-copilot)
      python scripts/agentic/generate-vscode-copilot.py
      ;;
    *)
      echo "ERROR: Unsupported target: $target" >&2
      echo "Supported targets: vscode-copilot" >&2
      exit 1
      ;;
  esac
}

show_status() {
  echo "Generated agents:"
  find .github/agents -name "*.agent.md" -print 2>/dev/null | sort || true

  echo ""
  echo "Generated skills:"
  find .github/skills -name "SKILL.md" -print 2>/dev/null | sort || true

  echo ""
  echo "Generated metadata:"
  find .agentic/generated -type f -print 2>/dev/null | sort || true

  echo ""
  echo "Lockfile:"
  if [[ -f .agentic/agentic-lock.json ]]; then
    echo ".agentic/agentic-lock.json"
  else
    echo "missing"
  fi

  echo ""
  echo "Git status:"
  git status --short
}

case "$COMMAND" in
  validate)
    scripts/agentic/validate-agentic-config.sh
    ;;
  resolve)
    python scripts/agentic/resolve-agentic-config.py
    ;;
  lock)
    python scripts/agentic/generate-lockfile.py
    ;;
  generate)
    python scripts/agentic/resolve-agentic-config.py
    python scripts/agentic/generate-lockfile.py
    generate_target "$TARGET"
    ;;
  check)
    check_scripts
    validate_json_files
    ;;
  all)
    check_scripts
    validate_json_files
    scripts/agentic/validate-agentic-config.sh
    python scripts/agentic/resolve-agentic-config.py
    python scripts/agentic/generate-lockfile.py
    generate_target "$TARGET"
    ;;
  status)
    show_status
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "ERROR: Unknown command: $COMMAND" >&2
    usage
    exit 1
    ;;
esac
