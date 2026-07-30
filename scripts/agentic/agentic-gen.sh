#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-}"

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
  scripts/agentic/agentic-gen.sh lock
  scripts/agentic/agentic-gen.sh validate-lockfile
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
  scripts/agentic/agentic-gen.sh generate
  scripts/agentic/agentic-gen.sh validate-generated
  scripts/agentic/agentic-gen.sh validate-target-runtime
  scripts/agentic/agentic-gen.sh test-negative
  scripts/agentic/agentic-gen.sh check
  scripts/agentic/agentic-gen.sh all
  scripts/agentic/agentic-gen.sh verify
  scripts/agentic/agentic-gen.sh verify-quiet
  scripts/agentic/agentic-gen.sh status
  scripts/agentic/agentic-gen.sh doctor
  scripts/agentic/agentic-gen.sh doctor-strict

Commands:
  validate-environment
             Validate required local command-line tools fail-fast.
  init      Initialize .agentic/agentic.json from a registered bundle or guided setup.
  validate   Validate .agentic/agentic.json against its JSON Schema and semantic contract.
             Validate Milestone-specific agentic config semantics.
  lock       Generate deterministic .agentic/agentic-lock.json.
  validate-lockfile
             Validate generated lockfile structure.
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
  generate   Materialize all enabled targets transactionally.
  validate-generated
             Validate committed output against canonical rendering.
  validate-target-runtime
             Require OpenCode to parse generated config, agents, and skills.
  validate-init-idempotency
             Validate init determinism for .agentic/agentic.json and guided setup profiles.
  test-negative
             Run negative gate tests against an isolated temporary repo copy.
  check      Run syntax checks for scripts and JSON files.
  all        Run checks, validations, coverage, lock, artifacts, and materialization.
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
  require_file "scripts/agentic/test-negative-gates.py"
  require_file "src/agentic_workflow_generator/application/target_materialization.py"
  require_file "src/agentic_workflow_generator/application/target_output_validation.py"
  require_file "src/agentic_workflow_generator/application/target_runtime_validation.py"
  require_file "src/agentic_workflow_generator/cli/target_materialization.py"
  require_file "src/agentic_workflow_generator/cli/target_output.py"
  require_file "src/agentic_workflow_generator/cli/target_runtime.py"

  bash -n "scripts/agentic/agentic-gen.sh"

  uv run python -m py_compile     "src/agentic_workflow_generator/application/environment.py" "src/agentic_workflow_generator/cli/environment.py" "src/agentic_workflow_generator/infrastructure/processes.py"     "src/agentic_workflow_generator/application/registry_references.py" "src/agentic_workflow_generator/validation/registry_schemas.py" "src/agentic_workflow_generator/cli/registry_references.py" "src/agentic_workflow_generator/cli/registry_schemas.py"     "src/agentic_workflow_generator/validation/capability_coverage.py" "src/agentic_workflow_generator/application/capability_coverage.py" "src/agentic_workflow_generator/cli/capability_coverage.py"     "scripts/agentic/test-negative-gates.py" "src/agentic_workflow_generator/application/lockfile.py" "src/agentic_workflow_generator/cli/lockfile_generation.py" "src/agentic_workflow_generator/cli/lockfile_validation.py"     "src/agentic_workflow_generator/application/target_materialization.py"     "src/agentic_workflow_generator/application/target_output_validation.py"     "src/agentic_workflow_generator/application/target_runtime_validation.py"     "src/agentic_workflow_generator/cli/target_materialization.py"     "src/agentic_workflow_generator/cli/target_output.py"     "src/agentic_workflow_generator/cli/target_runtime.py"

  echo "PASS: Script syntax checks passed."
}

run_pipeline() {
  check_scripts || return 1
  validate_json_files || return 1
  uv run python -m agentic_workflow_generator.cli.active_config || return 1
  uv run python -m agentic_workflow_generator.cli.targets || return 1
  uv run python -m agentic_workflow_generator.cli.skills || return 1
  uv run python -m agentic_workflow_generator.cli.workflows || return 1
  uv run python -m agentic_workflow_generator.cli.profiles || return 1
  uv run python -m agentic_workflow_generator.cli.bundles || return 1
  uv run python -m agentic_workflow_generator.cli.setups || return 1
  uv run python -m agentic_workflow_generator.cli.setup_profiles || return 1
  uv run python -m agentic_workflow_generator.cli.registry_references || return 1
  uv run python -m agentic_workflow_generator.cli.registry_schemas || return 1
  uv run python -m agentic_workflow_generator.cli.permission_profiles || return 1
  uv run python -m agentic_workflow_generator.cli.capability_coverage || return 1
  uv run python -m agentic_workflow_generator.cli.lockfile_generation || return 1
  uv run python -m agentic_workflow_generator.cli.lockfile_validation || return 1
  uv run python -m agentic_workflow_generator.cli.artifacts || return 1
  uv run python -m agentic_workflow_generator.cli.agents || return 1
  uv run python -m agentic_workflow_generator.cli.target_materialization || return 1
  uv run python -m agentic_workflow_generator.cli.target_output || return 1
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
  local log_path="${AGENTIC_VERIFY_LOG:-/tmp/agentic-verify.log}"

  rm -f "$log_path"

  if ! run_pipeline >"$log_path" 2>&1; then
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
  run_quiet_verify || return 1
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
    uv run python -m agentic_workflow_generator.cli.environment
    ;;

  init)
    uv run python -m agentic_workflow_generator.cli.init "${@:2}"
    ;;

  validate)
    uv run python -m agentic_workflow_generator.cli.active_config
    ;;

  lock)
    uv run python -m agentic_workflow_generator.cli.lockfile_generation
    ;;

  validate-lockfile)
    uv run python -m agentic_workflow_generator.cli.lockfile_validation
    ;;
  validate-artifacts)
    uv run python -m agentic_workflow_generator.cli.artifacts
    ;;
  validate-permission-profiles)
    uv run python -m agentic_workflow_generator.cli.permission_profiles
    ;;
  validate-agents)
    uv run python -m agentic_workflow_generator.cli.agents
    ;;
  validate-targets)
    uv run python -m agentic_workflow_generator.cli.targets
    ;;
  validate-skills)
    uv run python -m agentic_workflow_generator.cli.skills
    ;;
  validate-workflows)
    uv run python -m agentic_workflow_generator.cli.workflows
    ;;
  validate-profiles)
    uv run python -m agentic_workflow_generator.cli.profiles
    ;;
  validate-bundles)
    uv run python -m agentic_workflow_generator.cli.bundles
    ;;
  validate-setups)
    uv run python -m agentic_workflow_generator.cli.setups
    ;;
  validate-setup-profile)
    uv run python -m agentic_workflow_generator.cli.setup_profiles
    ;;
  validate-references)
    uv run python -m agentic_workflow_generator.cli.registry_references
    ;;
  validate-registry-schemas)
    uv run python -m agentic_workflow_generator.cli.registry_schemas
    ;;
  coverage)
    uv run python -m agentic_workflow_generator.cli.capability_coverage
    ;;
  generate)
    uv run python -m agentic_workflow_generator.cli.lockfile_generation
    uv run python -m agentic_workflow_generator.cli.lockfile_validation
    uv run python -m agentic_workflow_generator.cli.target_materialization
    uv run python -m agentic_workflow_generator.cli.target_output
    ;;
  validate-generated)
    uv run python -m agentic_workflow_generator.cli.target_output
    ;;
  validate-target-runtime)
    uv run python -m agentic_workflow_generator.cli.target_runtime
    ;;
  validate-idempotency)
    uv run python scripts/agentic/validate-generation-idempotency.py
    ;;
  validate-init-idempotency)
    uv run python -m agentic_workflow_generator.cli.init_idempotency "${@:2}"
    ;;
  test-negative)
    scripts/agentic/test-negative-gates.py "${@:2}"
    ;;
  check)
    check_scripts
    validate_json_files
    ;;
  all)
    run_pipeline
    ;;
  verify)
    run_pipeline
    verify_no_drift
    ;;
  verify-quiet)
    run_quiet_verify
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
