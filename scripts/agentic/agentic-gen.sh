#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-}"
TARGET="${2:-all}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/agentic/agentic-gen.sh validate
  scripts/agentic/agentic-gen.sh resolve
  scripts/agentic/agentic-gen.sh validate-resolution
  scripts/agentic/agentic-gen.sh lock
  scripts/agentic/agentic-gen.sh validate-artifacts
  scripts/agentic/agentic-gen.sh validate-agents
  scripts/agentic/agentic-gen.sh validate-agent-artifacts
  scripts/agentic/agentic-gen.sh validate-targets
  scripts/agentic/agentic-gen.sh validate-skills
  scripts/agentic/agentic-gen.sh validate-workflows
  scripts/agentic/agentic-gen.sh validate-profiles
  scripts/agentic/agentic-gen.sh validate-references
  scripts/agentic/agentic-gen.sh coverage
  scripts/agentic/agentic-gen.sh generate [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh check
  scripts/agentic/agentic-gen.sh all [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh verify [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh verify-quiet [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh status

Commands:
  validate   Validate .agentic/agentic.json against its JSON Schema.
  resolve    Resolve agents, targets, capabilities, skills, and produced artifacts.
  validate-resolution
             Validate generated resolver output.
  lock       Generate deterministic .agentic/agentic-lock.json.
  validate-artifacts
             Validate registered artifact contracts and existing artifact files.
  validate-agents
             Validate registered agent definitions.
  validate-agent-artifacts
             Validate that agent produces bindings point to registered artifact contracts.
  validate-targets
             Validate registered target adapters.
  validate-skills
             Validate registered skill definitions.
  validate-workflows
             Validate registered workflow definitions.
  validate-profiles
             Validate registered profile definitions.
  validate-references
             Validate cross-references between config and registry files.
  coverage   Report agent capability to skill capability coverage.
  generate   Generate target-specific output.
  check      Run syntax checks for scripts and JSON files.
  all        Run checks, validations, coverage, resolve, lock, artifacts, and generate.
  verify     Run all and fail if generated output drifts from git.
  verify-quiet
             Run verify with full output written to a log file.
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

  if [[ -f opencode.json ]]; then
    python -m json.tool opencode.json >/dev/null
  fi

  echo "PASS: JSON files are syntactically valid."
}

check_scripts() {
  require_file "scripts/agentic/validate-agentic-config.sh"
  require_file "scripts/agentic/resolve-agentic-config.py"
  require_file "scripts/agentic/validate-resolution-output.py"
  require_file "scripts/agentic/generate-vscode-copilot.py"
  require_file "scripts/agentic/generate-opencode.py"
  require_file "scripts/agentic/generate-lockfile.py"
  require_file "scripts/agentic/validate-artifacts.py"
  require_file "scripts/agentic/validate-agent-registry.py"
  require_file "scripts/agentic/validate-agent-artifact-bindings.py"
  require_file "scripts/agentic/validate-target-adapters.py"
  require_file "scripts/agentic/validate-skill-registry.py"
  require_file "scripts/agentic/validate-workflow-registry.py"
  require_file "scripts/agentic/validate-profile-registry.py"
  require_file "scripts/agentic/validate-registry-references.py"
  require_file "scripts/agentic/report-capability-coverage.py"

  bash -n "scripts/agentic/validate-agentic-config.sh"
  bash -n "scripts/agentic/agentic-gen.sh"

  python -m py_compile "scripts/agentic/resolve-agentic-config.py"
  python -m py_compile "scripts/agentic/validate-resolution-output.py"
  python -m py_compile "scripts/agentic/generate-vscode-copilot.py"
  python -m py_compile "scripts/agentic/generate-opencode.py"
  python -m py_compile "scripts/agentic/generate-lockfile.py"
  python -m py_compile "scripts/agentic/validate-artifacts.py"
  python -m py_compile "scripts/agentic/validate-agent-registry.py"
  python -m py_compile "scripts/agentic/validate-agent-artifact-bindings.py"
  python -m py_compile "scripts/agentic/validate-target-adapters.py"
  python -m py_compile "scripts/agentic/validate-skill-registry.py"
  python -m py_compile "scripts/agentic/validate-workflow-registry.py"
  python -m py_compile "scripts/agentic/validate-profile-registry.py"
  python -m py_compile "scripts/agentic/validate-registry-references.py"
  python -m py_compile "scripts/agentic/report-capability-coverage.py"

  echo "PASS: Script syntax checks passed."
}

generate_target() {
  local target="$1"

  case "$target" in
    vscode-copilot)
      python scripts/agentic/generate-vscode-copilot.py
      ;;
    opencode)
      python scripts/agentic/generate-opencode.py
      ;;
    all|all-targets)
      python scripts/agentic/generate-vscode-copilot.py
      python scripts/agentic/generate-opencode.py
      ;;
    *)
      echo "ERROR: Unsupported target: $target" >&2
      echo "Supported targets: vscode-copilot, opencode, all" >&2
      exit 1
      ;;
  esac
}

run_pipeline() {
  local target="$1"

  check_scripts
  validate_json_files
  scripts/agentic/validate-agentic-config.sh
  python scripts/agentic/validate-target-adapters.py
  python scripts/agentic/validate-skill-registry.py
  python scripts/agentic/validate-workflow-registry.py
  python scripts/agentic/validate-profile-registry.py
  python scripts/agentic/validate-registry-references.py
  python scripts/agentic/report-capability-coverage.py
  python scripts/agentic/resolve-agentic-config.py
  python scripts/agentic/validate-resolution-output.py
  python scripts/agentic/generate-lockfile.py
  python scripts/agentic/validate-artifacts.py
  python scripts/agentic/validate-agent-registry.py
  python scripts/agentic/validate-agent-artifact-bindings.py
  generate_target "$target"
}

verify_no_drift() {
  if ! git diff --quiet; then
    echo "ERROR: Generated output drift detected." >&2
    echo "Run scripts/agentic/agentic-gen.sh all and commit the resulting changes." >&2
    echo "" >&2
    git status --short >&2
    return 1
  fi

  if ! git diff --cached --quiet; then
    echo "ERROR: Staged changes exist after generation." >&2
    git status --short >&2
    return 1
  fi

  echo "PASS: Generated output is up-to-date with committed sources."
}


run_quiet_verify() {
  local target="$1"
  local log_path="${AGENTIC_VERIFY_LOG:-/tmp/agentic-verify.log}"

  rm -f "$log_path"

  if ! run_pipeline "$target" >"$log_path" 2>&1; then
    echo "FAIL: verify pipeline failed. Full log: $log_path" >&2
    echo "" >&2
    tail -n 120 "$log_path" >&2 || true
    return 1
  fi

  if ! verify_no_drift >>"$log_path" 2>&1; then
    echo "FAIL: generated output drift detected. Full log: $log_path" >&2
    echo "" >&2
    tail -n 120 "$log_path" >&2 || true
    return 1
  fi

  echo "PASS: verify-quiet completed successfully."
  echo "Log: $log_path"
}

show_status() {
  echo "Generated VS Code agents:"
  find .github/agents -name "*.agent.md" -print 2>/dev/null | sort || true

  echo ""
  echo "Generated VS Code skills:"
  find .github/skills -name "SKILL.md" -print 2>/dev/null | sort || true

  echo ""
  echo "Generated OpenCode agents:"
  find .opencode/agents -name "*.md" -print 2>/dev/null | sort || true

  echo ""
  echo "Generated OpenCode skills:"
  find .opencode/skills -name "SKILL.md" -print 2>/dev/null | sort || true

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
  validate-resolution)
    python scripts/agentic/validate-resolution-output.py
    ;;
  lock)
    python scripts/agentic/generate-lockfile.py
    ;;
  validate-artifacts)
    python scripts/agentic/validate-artifacts.py
    ;;
  validate-agents)
    python scripts/agentic/validate-agent-registry.py
    ;;
  validate-agent-artifacts)
    python scripts/agentic/validate-agent-artifact-bindings.py
    ;;
  validate-targets)
    python scripts/agentic/validate-target-adapters.py
    ;;
  validate-skills)
    python scripts/agentic/validate-skill-registry.py
    ;;
  validate-workflows)
    python scripts/agentic/validate-workflow-registry.py
    ;;
  validate-profiles)
    python scripts/agentic/validate-profile-registry.py
    ;;
  validate-references)
    python scripts/agentic/validate-registry-references.py
    ;;
  coverage)
    python scripts/agentic/report-capability-coverage.py
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
    run_pipeline "$TARGET"
    ;;
  verify)
    run_pipeline "$TARGET"
    verify_no_drift
    ;;
  verify-quiet)
    run_quiet_verify "$TARGET"
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
