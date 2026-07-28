#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-}"
TARGET="${2:-all}"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required but was not found in PATH." >&2
  exit 1
fi

usage() {
  cat <<'USAGE'
Usage:
  scripts/agentic/agentic-gen.sh validate-environment
  scripts/agentic/agentic-gen.sh init --bundle <bundle-name>
  scripts/agentic/agentic-gen.sh init --guided
  scripts/agentic/agentic-gen.sh init --guided --setup <setup-name>
  scripts/agentic/agentic-gen.sh init --guided --setup <setup-name> --dry-run
  scripts/agentic/agentic-gen.sh validate
  scripts/agentic/agentic-gen.sh resolve
  scripts/agentic/agentic-gen.sh validate-resolution
  scripts/agentic/agentic-gen.sh lock
  scripts/agentic/agentic-gen.sh validate-lockfile
  scripts/agentic/agentic-gen.sh manifest
  scripts/agentic/agentic-gen.sh validate-manifest
  scripts/agentic/agentic-gen.sh validate-artifacts
  scripts/agentic/agentic-gen.sh validate-permission-profiles
  scripts/agentic/agentic-gen.sh validate-agents
  scripts/agentic/agentic-gen.sh validate-targets
  scripts/agentic/agentic-gen.sh validate-skills
  scripts/agentic/agentic-gen.sh validate-workflows
  scripts/agentic/agentic-gen.sh validate-profiles
  scripts/agentic/agentic-gen.sh validate-bundles
  scripts/agentic/agentic-gen.sh validate-setups
  scripts/agentic/agentic-gen.sh validate-setup-profile
  scripts/agentic/agentic-gen.sh validate-references
  scripts/agentic/agentic-gen.sh validate-registry-schemas
  scripts/agentic/agentic-gen.sh coverage
  scripts/agentic/agentic-gen.sh generate [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh validate-generated
  scripts/agentic/agentic-gen.sh validate-target-compatibility
  scripts/agentic/agentic-gen.sh validate-target-runtime
  scripts/agentic/agentic-gen.sh test-negative
  scripts/agentic/agentic-gen.sh check
  scripts/agentic/agentic-gen.sh all [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh verify [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh verify-quiet [vscode-copilot|opencode|all]
  scripts/agentic/agentic-gen.sh status
  scripts/agentic/agentic-gen.sh doctor
  scripts/agentic/agentic-gen.sh doctor-strict

Commands:
  validate-environment
             Validate required local command-line tools fail-fast.
  init      Initialize .agentic/agentic.json from a registered bundle or guided setup.
  validate   Validate .agentic/agentic.json against its JSON Schema and semantic contract.
             Validate Milestone-specific agentic config semantics.
  resolve    Resolve agents, targets, capabilities, skills, and produced artifacts.
  validate-resolution
             Validate generated resolver output.
  lock       Generate deterministic .agentic/agentic-lock.json.
  validate-lockfile
             Validate generated lockfile structure.
  manifest   Generate deterministic output manifest.
  validate-manifest
             Validate generated output manifest.
  validate-artifacts
             Validate registered artifact contracts and existing artifact files.
  validate-permission-profiles
             Validate registered permission profile definitions.
  validate-agents
             Validate registered agent definitions.
  validate-targets
             Validate registered target adapters.
  validate-skills
             Validate registered skill definitions.
  validate-workflows
             Validate registered workflow definitions.
  validate-profiles
             Validate registered profile definitions.
  validate-bundles
             Validate registered bundle definitions.
  validate-setups
             Validate registered guided setup recommendation definitions.
  validate-setup-profile
             Validate the guided setup profile decisions.
  validate-references
             Validate cross-references between config and registry files.
  validate-registry-schemas
             Validate registry files against JSON Schemas.
  coverage   Report agent capability to skill capability coverage.
  generate   Generate target-specific output.
  validate-generated
             Validate generated target output files.
  validate-target-compatibility
             Validate generated framework contracts, permissions, tools, and handoffs.
  validate-target-runtime
             Require OpenCode to parse generated config, agents, and skills.
  validate-init-idempotency
             Validate init determinism for .agentic/agentic.json and guided setup profiles.
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
  find registry .agentic -name "*.json" -print0 | xargs -0 -r -n1 uv run python -m json.tool >/dev/null

  if [[ -f opencode.json ]]; then
    uv run python -m json.tool opencode.json >/dev/null
  fi

  echo "PASS: JSON files are syntactically valid."
}

check_scripts() {
  require_file "scripts/agentic/validate-environment.py"
  require_file "scripts/agentic/validate-setup-registry.py"
  require_file "scripts/agentic/validate-setup-profile.py"
  require_file "scripts/agentic/validate-agentic-config.sh"
  require_file "scripts/agentic/resolve-agentic-config.py"
  require_file "scripts/agentic/validate-resolution-output.py"
  require_file "scripts/agentic/generate-vscode-copilot.py"
  require_file "scripts/agentic/generate-opencode.py"
  require_file "scripts/agentic/generate-lockfile.py"
  require_file "scripts/agentic/validate-lockfile.py"
  require_file "scripts/agentic/validate-generated-output.py"
  require_file "scripts/agentic/target_generation_support.py"
  require_file "scripts/agentic/validate-target-compatibility.py"
  require_file "scripts/agentic/validate-artifacts.py"
  require_file "scripts/agentic/validate-permission-profile-registry.py"
  require_file "scripts/agentic/validate-agent-registry.py"
  require_file "scripts/agentic/validate-target-adapters.py"
  require_file "scripts/agentic/validate-skill-registry.py"
  require_file "scripts/agentic/validate-workflow-registry.py"
  require_file "scripts/agentic/validate-profile-registry.py"
  require_file "scripts/agentic/init-from-bundle.py"
  require_file "scripts/agentic/validate-init-idempotency.py"
  require_file "scripts/agentic/validate-bundle-registry.py"
  require_file "scripts/agentic/validate-registry-references.py"
  require_file "scripts/agentic/validate-registry-schemas.py"
  require_file "scripts/agentic/report-capability-coverage.py"

  uv run python -m py_compile "scripts/agentic/validate-environment.py"
  uv run python -m py_compile "scripts/agentic/validate-setup-registry.py"
  uv run python -m py_compile "scripts/agentic/validate-setup-profile.py"
  bash -n "scripts/agentic/validate-agentic-config.sh"
  bash -n "scripts/agentic/agentic-gen.sh"

  uv run python -m py_compile "scripts/agentic/resolve-agentic-config.py"
  uv run python -m py_compile "scripts/agentic/validate-resolution-output.py"
  uv run python -m py_compile "scripts/agentic/generate-vscode-copilot.py"
  uv run python -m py_compile "scripts/agentic/generate-opencode.py"
  uv run python -m py_compile "scripts/agentic/generate-lockfile.py"
  uv run python -m py_compile "scripts/agentic/validate-lockfile.py"
  uv run python -m py_compile "scripts/agentic/validate-generated-output.py"
  uv run python -m py_compile "scripts/agentic/target_generation_support.py"
  uv run python -m py_compile "scripts/agentic/validate-target-compatibility.py"
  uv run python -m py_compile "scripts/agentic/validate-artifacts.py"
  uv run python -m py_compile "scripts/agentic/validate-permission-profile-registry.py"
  uv run python -m py_compile "scripts/agentic/validate-agent-registry.py"
  uv run python -m py_compile "scripts/agentic/validate-target-adapters.py"
  uv run python -m py_compile "scripts/agentic/validate-skill-registry.py"
  uv run python -m py_compile "scripts/agentic/validate-workflow-registry.py"
  uv run python -m py_compile "scripts/agentic/validate-profile-registry.py"
  uv run python -m py_compile "scripts/agentic/init-from-bundle.py"
  uv run python -m py_compile "scripts/agentic/validate-init-idempotency.py"
  uv run python -m py_compile "scripts/agentic/validate-bundle-registry.py"
  uv run python -m py_compile "scripts/agentic/validate-registry-references.py"
  uv run python -m py_compile "scripts/agentic/validate-registry-schemas.py"
  uv run python -m py_compile "scripts/agentic/report-capability-coverage.py"

  echo "PASS: Script syntax checks passed."
}

generate_target() {
  local target="$1"

  case "$target" in
    vscode-copilot)
      uv run python scripts/agentic/generate-vscode-copilot.py
      ;;
    opencode)
      uv run python scripts/agentic/generate-opencode.py
      ;;
    all|all-targets)
      uv run python scripts/agentic/generate-vscode-copilot.py
      uv run python scripts/agentic/generate-opencode.py
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
  uv run python scripts/agentic/validate-target-adapters.py || return 1
  uv run python scripts/agentic/validate-skill-registry.py || return 1
  uv run python scripts/agentic/validate-workflow-registry.py || return 1
  uv run python scripts/agentic/validate-profile-registry.py || return 1
  uv run python scripts/agentic/validate-bundle-registry.py || return 1
  uv run python scripts/agentic/validate-setup-registry.py || return 1
  uv run python scripts/agentic/validate-setup-profile.py || return 1
  uv run python scripts/agentic/validate-registry-references.py || return 1
  uv run python scripts/agentic/validate-registry-schemas.py || return 1
  uv run python scripts/agentic/validate-permission-profile-registry.py || return 1
  uv run python scripts/agentic/report-capability-coverage.py || return 1
  uv run python scripts/agentic/resolve-agentic-config.py || return 1
  uv run python scripts/agentic/validate-resolution-output.py || return 1
  uv run python scripts/agentic/generate-lockfile.py || return 1
  uv run python scripts/agentic/validate-lockfile.py || return 1
  uv run python scripts/agentic/validate-artifacts.py || return 1
  uv run python scripts/agentic/validate-agent-registry.py || return 1
  generate_target "$target" || return 1
  uv run python scripts/agentic/validate-generated-output.py || return 1
  uv run python scripts/agentic/validate-target-compatibility.py || return 1
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

  echo "== Isolated consumer end-to-end test =="
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
  validate-environment)
    uv run python scripts/agentic/validate-environment.py
    ;;

  init)
    uv run python scripts/agentic/init-from-bundle.py "${@:2}"
    ;;

  validate)
    scripts/agentic/validate-agentic-config.sh
    ;;
  resolve)
    uv run python scripts/agentic/resolve-agentic-config.py
    ;;
  validate-resolution)
    uv run python scripts/agentic/validate-resolution-output.py
    ;;
  lock)
    uv run python scripts/agentic/generate-lockfile.py
    ;;
  validate-lockfile)
    uv run python scripts/agentic/validate-lockfile.py
    ;;

  manifest)
    uv run python scripts/agentic/generate-output-manifest.py
    ;;

  validate-manifest)
    uv run python scripts/agentic/validate-output-manifest.py
    ;;

  cleanup-generated)
    uv run python scripts/agentic/cleanup-generated-output.py "${@:2}"
    ;;
  validate-artifacts)
    uv run python scripts/agentic/validate-artifacts.py
    ;;
  validate-permission-profiles)
    uv run python scripts/agentic/validate-permission-profile-registry.py
    ;;
  validate-agents)
    uv run python scripts/agentic/validate-agent-registry.py
    ;;
  validate-targets)
    uv run python scripts/agentic/validate-target-adapters.py
    ;;
  validate-skills)
    uv run python scripts/agentic/validate-skill-registry.py
    ;;
  validate-workflows)
    uv run python scripts/agentic/validate-workflow-registry.py
    ;;
  validate-profiles)
    uv run python scripts/agentic/validate-profile-registry.py
    ;;
  validate-bundles)
    uv run python scripts/agentic/validate-bundle-registry.py
    ;;
  validate-setups)
    uv run python scripts/agentic/validate-setup-registry.py
    ;;
  validate-setup-profile)
    uv run python scripts/agentic/validate-setup-profile.py
    ;;
  validate-references)
    uv run python scripts/agentic/validate-registry-references.py
    ;;
  validate-registry-schemas)
    uv run python scripts/agentic/validate-registry-schemas.py
    ;;
  coverage)
    uv run python scripts/agentic/report-capability-coverage.py
    ;;
  generate)
    uv run python scripts/agentic/resolve-agentic-config.py
    uv run python scripts/agentic/generate-lockfile.py
    generate_target "$TARGET"
    ;;
  validate-generated)
    uv run python scripts/agentic/validate-generated-output.py
    ;;
  validate-target-compatibility)
    uv run python scripts/agentic/validate-target-compatibility.py
    ;;
  validate-target-runtime)
    uv run python scripts/agentic/validate-target-compatibility.py --require-opencode-runtime
    ;;
  validate-idempotency)
    uv run python scripts/agentic/validate-generation-idempotency.py
    ;;
  validate-init-idempotency)
    uv run python scripts/agentic/validate-init-idempotency.py "${@:2}"
    ;;
  test-negative)
    scripts/agentic/test-negative-gates.py "${@:2}"
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
