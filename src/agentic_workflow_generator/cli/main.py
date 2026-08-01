"""Public typed command boundary for the workflow generator."""

from __future__ import annotations

import ast
import os
import sys
from collections.abc import Callable, Sequence
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from agentic_workflow_generator.cli import (
    active_config,
    agents,
    artifacts,
    bundles,
    capability_coverage,
    environment,
    generation_idempotency,
    init,
    init_idempotency,
    lockfile_generation,
    lockfile_validation,
    permission_profiles,
    profiles,
    registry_references,
    registry_schemas,
    setup_profiles,
    setups,
    skills,
    target_materialization,
    target_output,
    target_runtime,
    targets,
    workflows,
)
from agentic_workflow_generator.infrastructure import (
    ProcessResult,
    read_json,
    resolve_executable,
    run_process,
)
from agentic_workflow_generator.infrastructure.errors import InfrastructureError

Command = Callable[[Sequence[str]], int]
PipelineStep = tuple[str, Command]

USAGE = """Usage:
  agentic-workflow-generator validate-environment
  agentic-workflow-generator init --bundle <bundle-name>
  agentic-workflow-generator init --guided
  agentic-workflow-generator init --guided --setup <setup-name>
  agentic-workflow-generator init --guided --setup <setup-name> --dry-run
  agentic-workflow-generator validate
  agentic-workflow-generator lock
  agentic-workflow-generator validate-lockfile
  agentic-workflow-generator validate-artifacts
  agentic-workflow-generator validate-permission-profiles
  agentic-workflow-generator validate-agents
  agentic-workflow-generator validate-targets
  agentic-workflow-generator validate-skills
  agentic-workflow-generator validate-workflows
  agentic-workflow-generator validate-profiles
  agentic-workflow-generator validate-bundles
  agentic-workflow-generator validate-setups
  agentic-workflow-generator validate-setup-profile
  agentic-workflow-generator validate-references
  agentic-workflow-generator validate-registry-schemas
  agentic-workflow-generator coverage
  agentic-workflow-generator generate
  agentic-workflow-generator validate-generated
  agentic-workflow-generator validate-target-runtime
  agentic-workflow-generator validate-idempotency
  agentic-workflow-generator validate-init-idempotency --bundle <bundle-name>
  agentic-workflow-generator check
  agentic-workflow-generator all
  agentic-workflow-generator verify
  agentic-workflow-generator verify-quiet
  agentic-workflow-generator status
  agentic-workflow-generator doctor
  agentic-workflow-generator doctor-strict
"""


def _without_arguments(
    name: str,
    command: Callable[[], int],
) -> Command:
    def run(argv: Sequence[str]) -> int:
        if argv:
            print(
                f"ERROR: Command '{name}' does not accept arguments: "
                + " ".join(argv),
                file=sys.stderr,
            )
            return 2

        return command()

    return run


def _without_forwarded_arguments(
    name: str,
    command: Callable[[Sequence[str] | None], int],
) -> Command:
    def run(argv: Sequence[str]) -> int:
        if argv:
            print(
                f"ERROR: Command '{name}' does not accept arguments: "
                + " ".join(argv),
                file=sys.stderr,
            )
            return 2

        return command(())

    return run


def _with_arguments(
    command: Callable[[Sequence[str] | None], int],
) -> Command:
    def run(argv: Sequence[str]) -> int:
        return command(argv)

    return run


def _run_external(
    command: str,
    arguments: tuple[str, ...],
) -> ProcessResult:
    executable = resolve_executable(
        command,
        path=os.environ.get("PATH", ""),
    )
    if executable is None:
        raise ValueError(
            f"Required command not found in PATH: {command}"
        )

    return run_process(
        executable,
        arguments,
        cwd=Path.cwd().resolve(),
    )


def _git_status() -> str:
    result = _run_external(
        "git",
        ("status", "--short"),
    )
    if result.exit_code != 0:
        raise ValueError(
            f"git status failed with exit code {result.exit_code}: "
            f"{result.output}"
        )
    return result.output


def _check_python_syntax() -> int:
    root = Path.cwd().resolve()
    python_files = tuple(
        sorted(
            (root / "src" / "agentic_workflow_generator").rglob("*.py")
        )
    )

    if not python_files:
        print(
            "ERROR: No Python package files found under "
            "src/agentic_workflow_generator.",
            file=sys.stderr,
        )
        return 1

    for path in python_files:
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            print(
                f"ERROR: Python syntax validation failed for {path}: {exc}",
                file=sys.stderr,
            )
            return 1

    print(
        "PASS: Python files are syntactically valid. "
        f"Checked {len(python_files)} file(s)."
    )
    return 0


def _check_json_syntax() -> int:
    root = Path.cwd().resolve()
    json_files = {
        *(
            path
            for base in (
                root / "registry",
                root / ".agentic",
            )
            if base.is_dir()
            for path in base.rglob("*.json")
        ),
    }

    opencode_config = root / "opencode.json"
    if opencode_config.is_file():
        json_files.add(opencode_config)

    for path in sorted(json_files):
        try:
            read_json(path)
        except (
            InfrastructureError,
            OSError,
            ValueError,
        ) as exc:
            print(
                f"ERROR: JSON syntax validation failed for {path}: {exc}",
                file=sys.stderr,
            )
            return 1

    print(
        "PASS: JSON files are syntactically valid. "
        f"Checked {len(json_files)} file(s)."
    )
    return 0


def _run_check(argv: Sequence[str]) -> int:
    if argv:
        print(
            "ERROR: Command 'check' does not accept arguments: "
            + " ".join(argv),
            file=sys.stderr,
        )
        return 2

    result = _check_python_syntax()
    if result != 0:
        return result

    return _check_json_syntax()


GENERATION_STEPS: tuple[PipelineStep, ...] = (
    (
        "lock",
        _without_forwarded_arguments(
            "lock",
            lockfile_generation.main,
        ),
    ),
    (
        "validate-lockfile",
        _without_forwarded_arguments(
            "validate-lockfile",
            lockfile_validation.main,
        ),
    ),
    (
        "materialize-targets",
        _without_forwarded_arguments(
            "materialize-targets",
            target_materialization.main,
        ),
    ),
    (
        "validate-generated",
        _without_forwarded_arguments(
            "validate-generated",
            target_output.main,
        ),
    ),
)


PIPELINE_STEPS: tuple[PipelineStep, ...] = (
    ("check", _run_check),
    (
        "validate",
        _without_forwarded_arguments(
            "validate",
            active_config.main,
        ),
    ),
    (
        "validate-targets",
        _without_arguments(
            "validate-targets",
            targets.main,
        ),
    ),
    (
        "validate-skills",
        _without_arguments(
            "validate-skills",
            skills.main,
        ),
    ),
    (
        "validate-workflows",
        _without_arguments(
            "validate-workflows",
            workflows.main,
        ),
    ),
    (
        "validate-profiles",
        _without_arguments(
            "validate-profiles",
            profiles.main,
        ),
    ),
    (
        "validate-bundles",
        _without_arguments(
            "validate-bundles",
            bundles.main,
        ),
    ),
    (
        "validate-setups",
        _without_arguments(
            "validate-setups",
            setups.main,
        ),
    ),
    (
        "validate-setup-profile",
        _without_forwarded_arguments(
            "validate-setup-profile",
            setup_profiles.main,
        ),
    ),
    (
        "validate-references",
        _without_arguments(
            "validate-references",
            registry_references.main,
        ),
    ),
    (
        "validate-registry-schemas",
        _without_arguments(
            "validate-registry-schemas",
            registry_schemas.main,
        ),
    ),
    (
        "validate-permission-profiles",
        _without_arguments(
            "validate-permission-profiles",
            permission_profiles.main,
        ),
    ),
    (
        "coverage",
        _without_arguments(
            "coverage",
            capability_coverage.main,
        ),
    ),
    *GENERATION_STEPS[:2],
    (
        "validate-artifacts",
        _without_arguments(
            "validate-artifacts",
            artifacts.main,
        ),
    ),
    (
        "validate-agents",
        _without_arguments(
            "validate-agents",
            agents.main,
        ),
    ),
    *GENERATION_STEPS[2:],
)


def _run_steps(
    steps: tuple[PipelineStep, ...],
) -> int:
    for _name, command in steps:
        result = command(())
        if result != 0:
            return result
    return 0


def _run_generate(argv: Sequence[str]) -> int:
    if argv:
        print(
            "ERROR: Command 'generate' does not accept arguments: "
            + " ".join(argv),
            file=sys.stderr,
        )
        return 2

    return _run_steps(GENERATION_STEPS)


def _run_pipeline(argv: Sequence[str]) -> int:
    if argv:
        print(
            "ERROR: Command 'all' does not accept arguments: "
            + " ".join(argv),
            file=sys.stderr,
        )
        return 2

    return _run_steps(PIPELINE_STEPS)


def _verify_no_drift() -> int:
    try:
        unstaged = _run_external(
            "git",
            ("diff", "--quiet"),
        )
        staged = _run_external(
            "git",
            ("diff", "--cached", "--quiet"),
        )
    except (
        InfrastructureError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"ERROR: Could not verify generated output drift: {exc}",
            file=sys.stderr,
        )
        return 1

    if unstaged.exit_code not in {0, 1}:
        print(
            "ERROR: git diff failed while checking generated output.",
            file=sys.stderr,
        )
        return 1

    if staged.exit_code not in {0, 1}:
        print(
            "ERROR: git diff --cached failed while checking generated output.",
            file=sys.stderr,
        )
        return 1

    if unstaged.exit_code == 1:
        print(
            "ERROR: Generated output drift detected.",
            file=sys.stderr,
        )
        print(
            "Run 'uv run agentic-workflow-generator all' and commit "
            "the resulting changes.",
            file=sys.stderr,
        )
        try:
            status = _git_status()
        except (
            InfrastructureError,
            OSError,
            ValueError,
        ):
            status = ""
        if status:
            print("", file=sys.stderr)
            print(status, file=sys.stderr)
        return 1

    if staged.exit_code == 1:
        print(
            "ERROR: Staged changes exist after generation.",
            file=sys.stderr,
        )
        try:
            status = _git_status()
        except (
            InfrastructureError,
            OSError,
            ValueError,
        ):
            status = ""
        if status:
            print(status, file=sys.stderr)
        return 1

    print(
        "PASS: Generated output is up-to-date with committed sources."
    )
    return 0


def _run_verify(argv: Sequence[str]) -> int:
    if argv:
        print(
            "ERROR: Command 'verify' does not accept arguments: "
            + " ".join(argv),
            file=sys.stderr,
        )
        return 2

    result = _run_pipeline(())
    if result != 0:
        return result

    return _verify_no_drift()


def _print_log_tail(
    log_path: Path,
) -> None:
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(
            f"ERROR: Could not read verify log {log_path}: {exc}",
            file=sys.stderr,
        )
        return

    for line in lines[-120:]:
        print(line, file=sys.stderr)


def _run_quiet_verify(argv: Sequence[str]) -> int:
    if argv:
        print(
            "ERROR: Command 'verify-quiet' does not accept arguments: "
            + " ".join(argv),
            file=sys.stderr,
        )
        return 2

    log_path = Path(
        os.environ.get(
            "AGENTIC_VERIFY_LOG",
            "/tmp/agentic-verify.log",
        )
    )

    try:
        with log_path.open(
            "w",
            encoding="utf-8",
        ) as log, redirect_stdout(log), redirect_stderr(log):
            result = _run_verify(())
    except OSError as exc:
        print(
            f"FAIL: Could not write verify log {log_path}: {exc}",
            file=sys.stderr,
        )
        return 1

    if result != 0:
        print(
            f"FAIL: verify pipeline failed. Full log: {log_path}",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        _print_log_tail(log_path)
        return result

    print("PASS: verify-quiet completed successfully.")
    print(f"Log: {log_path}")
    return 0


def _run_pytest() -> int:
    try:
        result = run_process(
            sys.executable,
            ("-m", "pytest", "-q"),
            cwd=Path.cwd().resolve(),
        )
    except InfrastructureError as exc:
        print(
            f"FAIL: Could not run pytest: {exc}",
            file=sys.stderr,
        )
        return 1

    if result.output:
        print(result.output)

    if result.exit_code != 0:
        return 1

    return 0


def _render_git_status(
    *,
    strict: bool,
) -> int:
    try:
        status = _git_status()
    except (
        InfrastructureError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"FAIL: Could not read git status: {exc}",
            file=sys.stderr,
        )
        return 1

    if status:
        print(status)
        print()
        if strict:
            print(
                "ERROR: Working tree is not clean.",
                file=sys.stderr,
            )
            return 1

        print("WARN: Working tree has uncommitted changes.")
        return 0

    print("PASS: Working tree is clean.")
    return 0


def _run_doctor(argv: Sequence[str]) -> int:
    if argv:
        print(
            "ERROR: Command 'doctor' does not accept arguments: "
            + " ".join(argv),
            file=sys.stderr,
        )
        return 2

    print("== Agentic doctor ==")
    print()
    print("== Happy path verification ==")

    result = _run_quiet_verify(())
    if result != 0:
        return result

    print()
    print("== Pytest suite ==")
    result = _run_pytest()
    if result != 0:
        return result

    print()
    print("== Git status ==")
    return _render_git_status(strict=False)


def _run_doctor_strict(argv: Sequence[str]) -> int:
    if argv:
        print(
            "ERROR: Command 'doctor-strict' does not accept arguments: "
            + " ".join(argv),
            file=sys.stderr,
        )
        return 2

    result = _run_doctor(())
    if result != 0:
        return result

    try:
        status = _git_status()
    except (
        InfrastructureError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"FAIL: Could not read git status: {exc}",
            file=sys.stderr,
        )
        return 1

    if status:
        print()
        print(
            "ERROR: Working tree is not clean.",
            file=sys.stderr,
        )
        return 1

    return 0


def _print_generated_files(
    label: str,
    root: Path,
    pattern: str,
) -> None:
    print(label)
    if root.is_dir():
        for path in sorted(root.rglob(pattern)):
            if path.is_file():
                print(path.relative_to(Path.cwd().resolve()))
    print()


def _show_status(argv: Sequence[str]) -> int:
    if argv:
        print(
            "ERROR: Command 'status' does not accept arguments: "
            + " ".join(argv),
            file=sys.stderr,
        )
        return 2

    root = Path.cwd().resolve()

    _print_generated_files(
        "Generated VS Code agents:",
        root / ".github" / "agents",
        "*.agent.md",
    )
    _print_generated_files(
        "Generated VS Code skills:",
        root / ".github" / "skills",
        "SKILL.md",
    )
    _print_generated_files(
        "Generated OpenCode agents:",
        root / ".opencode" / "agents",
        "*.md",
    )
    _print_generated_files(
        "Generated OpenCode skills:",
        root / ".opencode" / "skills",
        "SKILL.md",
    )
    _print_generated_files(
        "Generated metadata:",
        root / ".agentic" / "generated",
        "*",
    )

    print("Lockfile:")
    lockfile = root / ".agentic" / "agentic-lock.json"
    print(
        ".agentic/agentic-lock.json"
        if lockfile.is_file()
        else "missing"
    )
    print()

    print("Git status:")
    try:
        status = _git_status()
    except (
        InfrastructureError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"ERROR: Could not read git status: {exc}",
            file=sys.stderr,
        )
        return 1

    if status:
        print(status)

    return 0


COMMANDS: dict[str, Command] = {
    "validate-environment": _without_forwarded_arguments(
        "validate-environment",
        environment.main,
    ),
    "init": _with_arguments(init.main),
    "validate": _without_forwarded_arguments(
        "validate",
        active_config.main,
    ),
    "lock": _without_forwarded_arguments(
        "lock",
        lockfile_generation.main,
    ),
    "validate-lockfile": _without_forwarded_arguments(
        "validate-lockfile",
        lockfile_validation.main,
    ),
    "validate-artifacts": _without_arguments(
        "validate-artifacts",
        artifacts.main,
    ),
    "validate-permission-profiles": _without_arguments(
        "validate-permission-profiles",
        permission_profiles.main,
    ),
    "validate-agents": _without_arguments(
        "validate-agents",
        agents.main,
    ),
    "validate-targets": _without_arguments(
        "validate-targets",
        targets.main,
    ),
    "validate-skills": _without_arguments(
        "validate-skills",
        skills.main,
    ),
    "validate-workflows": _without_arguments(
        "validate-workflows",
        workflows.main,
    ),
    "validate-profiles": _without_arguments(
        "validate-profiles",
        profiles.main,
    ),
    "validate-bundles": _without_arguments(
        "validate-bundles",
        bundles.main,
    ),
    "validate-setups": _without_arguments(
        "validate-setups",
        setups.main,
    ),
    "validate-setup-profile": _without_forwarded_arguments(
        "validate-setup-profile",
        setup_profiles.main,
    ),
    "validate-references": _without_arguments(
        "validate-references",
        registry_references.main,
    ),
    "validate-registry-schemas": _without_arguments(
        "validate-registry-schemas",
        registry_schemas.main,
    ),
    "coverage": _without_arguments(
        "coverage",
        capability_coverage.main,
    ),
    "generate": _run_generate,
    "validate-generated": _without_forwarded_arguments(
        "validate-generated",
        target_output.main,
    ),
    "validate-target-runtime": _without_forwarded_arguments(
        "validate-target-runtime",
        target_runtime.main,
    ),
    "validate-idempotency": _without_forwarded_arguments(
        "validate-idempotency",
        generation_idempotency.main,
    ),
    "validate-init-idempotency": _with_arguments(
        init_idempotency.main
    ),
    "check": _run_check,
    "all": _run_pipeline,
    "verify": _run_verify,
    "verify-quiet": _run_quiet_verify,
    "status": _show_status,
    "doctor": _run_doctor,
    "doctor-strict": _run_doctor_strict,
}


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Route one public command through the typed CLI boundary."""

    arguments = tuple(
        sys.argv[1:]
        if argv is None
        else argv
    )

    if not arguments or arguments[0] in {
        "-h",
        "--help",
        "help",
    }:
        print(USAGE, end="")
        return 0

    command_name = arguments[0]
    command = COMMANDS.get(command_name)

    if command is None:
        print(
            f"ERROR: Unknown command: {command_name}",
            file=sys.stderr,
        )
        print(USAGE, end="")
        return 1

    return command(arguments[1:])


if __name__ == "__main__":
    raise SystemExit(main())
