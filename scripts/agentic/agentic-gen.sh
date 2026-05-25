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
  scripts/agentic/agentic-gen.sh validate-lockfile
  scripts/agentic/agentic-gen.sh validate-artifacts
  scripts/agentic/agentic-gen.sh validate-agents
  scripts/agentic/agentic-gen.sh validate-agent-artifacts
  scripts/agentic/agentic-gen.sh validate-targets
  scripts/agentic/agentic-gen.sh validate-skills
  scripts/agentic/agentic-gen.sh validate-workflows
  scripts/agentic/agentic-gen.sh validate-profiles
  scripts/agentic/agentic-gen.sh validate-references
  scripts/agentic/agentic-gen.sh validate-registry-schemas
  scripts/agentic/agentic-gen.sh coverage
  scripts/agentic/agentic-gen.sh generate [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh validate-generated
  scripts/agentic/agentic-gen.sh test-negative
  scripts/agentic/agentic-gen.sh check
  scripts/agentic/agentic-gen.sh all [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh verify [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh verify-quiet [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh status
  scripts/agentic/agentic-gen.sh doctor
  scripts/agentic/agentic-gen.sh doctor-strict

Commands:
  validate   Validate .agentic/agentic.json against its JSON Schema.
  resolve    Resolve agents, targets, capabilities, skills, and produced artifacts.
  validate-resolution
             Validate generated resolver output.
  lock       Generate deterministic .agentic/agentic-lock.json.
  validate-lockfile
             Validate generated lockfile structure.
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
  validate-registry-schemas
             Validate registry files against JSON Schemas.
  coverage   Report agent capability to skill capability coverage.
  generate   Generate target-specific output.
  validate-generated
             Validate generated target output files.
  test-negative
             Run negative gate tests against an isolated temporary repo copy.
  check      Run syntax checks for scripts and JSON files.
  all        Run checks, validations, coverage, resolve, lock, artifacts, and generate.
  verify     Run all and fail if generated output drifts from git.
  verify-quiet
             Run verify with full output written to a log file.
  status     Show generated files and git status.
  doctor     Run verify-quiet, negative gate tests, and git status.
  doctor-strict
             Run doctor and fail if the working tree is not clean.
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
  require_file "scripts/agentic/validate-lockfile.py"
  require_file "scripts/agentic/validate-generated-output.py"
  require_file "scripts/agentic/validate-artifacts.py"
  require_file "scripts/agentic/validate-agent-registry.py"
  require_file "scripts/agentic/validate-agent-artifact-bindings.py"
  require_file "scripts/agentic/validate-target-adapters.py"
  require_file "scripts/agentic/validate-skill-registry.py"
  require_file "scripts/agentic/validate-workflow-registry.py"
  require_file "scripts/agentic/validate-profile-registry.py"
  require_file "scripts/agentic/validate-registry-references.py"
  require_file "scripts/agentic/validate-registry-schemas.py"
  require_file "scripts/agentic/report-capability-coverage.py"

  bash -n "scripts/agentic/validate-agentic-config.sh"
  bash -n "scripts/agentic/agentic-gen.sh"

  python -m py_compile "scripts/agentic/resolve-agentic-config.py"
  python -m py_compile "scripts/agentic/validate-resolution-output.py"
  python -m py_compile "scripts/agentic/generate-vscode-copilot.py"
  python -m py_compile "scripts/agentic/generate-opencode.py"
  python -m py_compile "scripts/agentic/generate-lockfile.py"
  python -m py_compile "scripts/agentic/validate-lockfile.py"
  python -m py_compile "scripts/agentic/validate-generated-output.py"
  python -m py_compile "scripts/agentic/validate-artifacts.py"
  python -m py_compile "scripts/agentic/validate-agent-registry.py"
  python -m py_compile "scripts/agentic/validate-agent-artifact-bindings.py"
  python -m py_compile "scripts/agentic/validate-target-adapters.py"
  python -m py_compile "scripts/agentic/validate-skill-registry.py"
  python -m py_compile "scripts/agentic/validate-workflow-registry.py"
  python -m py_compile "scripts/agentic/validate-profile-registry.py"
  python -m py_compile "scripts/agentic/validate-registry-references.py"
  python -m py_compile "scripts/agentic/validate-registry-schemas.py"
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

  check_scripts || return 1
  validate_json_files || return 1
  scripts/agentic/validate-agentic-config.sh || return 1
  python scripts/agentic/validate-target-adapters.py || return 1
  python scripts/agentic/validate-skill-registry.py || return 1
  python scripts/agentic/validate-workflow-registry.py || return 1
  python scripts/agentic/validate-profile-registry.py || return 1
  python scripts/agentic/validate-registry-references.py || return 1
  python scripts/agentic/validate-registry-schemas.py || return 1
  python scripts/agentic/report-capability-coverage.py || return 1
  python scripts/agentic/resolve-agentic-config.py || return 1
  python scripts/agentic/validate-resolution-output.py || return 1
  python scripts/agentic/generate-lockfile.py || return 1
  python scripts/agentic/validate-lockfile.py || return 1
  python scripts/agentic/validate-artifacts.py || return 1
  python scripts/agentic/validate-agent-registry.py || return 1
  python scripts/agentic/validate-agent-artifact-bindings.py || return 1
  generate_target "$target" || return 1
  python scripts/agentic/validate-generated-output.py || return 1
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


run_doctor() {
  echo "== Agentic doctor =="
  echo ""

  echo "== Happy path verification =="
  run_quiet_verify "all" || return 1
  echo ""

  echo "== Negative gate tests =="
  scripts/agentic/test-negative-gates.py || return 1
  echo ""

  echo "== Git status =="
  local status_output
  status_output="$(git status --short)"

  if [[ -n "$status_output" ]]; then
    echo "$status_output"
    echo ""
    echo "WARN: Working tree has uncommitted changes."
  else
    echo "PASS: Working tree is clean."
  fi
}

run_doctor_strict() {
  run_doctor || return 1

  local status_output
  status_output="$(git status --short)"

  if [[ -n "$status_output" ]]; then
    echo ""
    echo "ERROR: Working tree is not clean."
    return 1
  fi

  return 0
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
  validate-lockfile)
    python scripts/agentic/validate-lockfile.py
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
  validate-registry-schemas)
    python scripts/agentic/validate-registry-schemas.py
    ;;
  coverage)
    python scripts/agentic/report-capability-coverage.py
    ;;
  generate)
    python scripts/agentic/resolve-agentic-config.py
    python scripts/agentic/generate-lockfile.py
    generate_target "$TARGET"
    ;;
  validate-generated)
    python scripts/agentic/validate-generated-output.py
    ;;
  test-negative)
    scripts/agentic/test-negative-gates.py
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
  doctor)
    run_doctor
    ;;
  doctor-strict)
    run_doctor_strict
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
