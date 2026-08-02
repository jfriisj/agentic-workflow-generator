"""Fail-fast validation of required development commands."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    ProcessExecutionError,
)
from agentic_workflow_generator.infrastructure.processes import (
    resolve_executable,
    run_process,
)
from agentic_workflow_generator.registry import ProjectPaths

EXECUTABLE_MISSING_DIAGNOSTIC = "AWG-ENVIRONMENT-001"
EXECUTION_FAILURE_DIAGNOSTIC = "AWG-ENVIRONMENT-002"
COMMAND_REJECTED_DIAGNOSTIC = "AWG-ENVIRONMENT-003"

COMMAND_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class EnvironmentRequirement:
    """One mandatory external command contract."""

    name: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EnvironmentCheck:
    """Result of validating one mandatory command."""

    requirement: EnvironmentRequirement
    executable: str | None
    version: str | None
    diagnostic: Diagnostic | None


@dataclass(frozen=True, slots=True)
class EnvironmentValidationResult:
    """Complete deterministic environment-validation result."""

    checks: tuple[EnvironmentCheck, ...]
    diagnostics: tuple[Diagnostic, ...]


REQUIRED_COMMANDS = (
    EnvironmentRequirement(
        name="bash",
        command=("bash", "--version"),
    ),
    EnvironmentRequirement(
        name="git",
        command=("git", "--version"),
    ),
    EnvironmentRequirement(
        name="uv",
        command=("uv", "--version"),
    ),
    EnvironmentRequirement(
        name="project Python",
        command=("uv", "run", "python", "--version"),
    ),
)


def validate_environment(
    paths: ProjectPaths,
    *,
    path_value: str,
) -> EnvironmentValidationResult:
    """Validate every required command without fallback."""

    checks = tuple(
        _validate_requirement(
            paths,
            requirement,
            path_value=path_value,
        )
        for requirement in REQUIRED_COMMANDS
    )
    diagnostics = tuple(
        check.diagnostic
        for check in checks
        if check.diagnostic is not None
    )

    return EnvironmentValidationResult(
        checks=checks,
        diagnostics=diagnostics,
    )


def _validate_requirement(
    paths: ProjectPaths,
    requirement: EnvironmentRequirement,
    *,
    path_value: str,
) -> EnvironmentCheck:
    command_name, *arguments = requirement.command
    executable = resolve_executable(
        command_name,
        path=path_value,
    )

    if executable is None:
        diagnostic = Diagnostic(
            code=EXECUTABLE_MISSING_DIAGNOSTIC,
            message=(
                f"{requirement.name} is required but was not "
                "found in PATH."
            ),
        )
        return EnvironmentCheck(
            requirement=requirement,
            executable=None,
            version=None,
            diagnostic=diagnostic,
        )

    try:
        result = run_process(
            executable,
            tuple(arguments),
            cwd=paths.root,
            timeout_seconds=COMMAND_TIMEOUT_SECONDS,
        )
    except ProcessExecutionError as exc:
        diagnostic = Diagnostic(
            code=EXECUTION_FAILURE_DIAGNOSTIC,
            message=(
                f"{requirement.name} is required but failed to run. "
                f"Command path: {executable}. "
                f"Command: {' '.join(requirement.command)}. "
                f"Error: {exc.detail}"
            ),
        )
        return EnvironmentCheck(
            requirement=requirement,
            executable=executable,
            version=None,
            diagnostic=diagnostic,
        )

    if result.exit_code != 0:
        message = (
            f"{requirement.name} is required but failed to run. "
            f"Command path: {executable}. "
            f"Command: {' '.join(requirement.command)}. "
            f"Exit code: {result.exit_code}."
        )

        if result.output:
            message = f"{message} Output: {result.output}"

        diagnostic = Diagnostic(
            code=COMMAND_REJECTED_DIAGNOSTIC,
            message=message,
        )
        return EnvironmentCheck(
            requirement=requirement,
            executable=executable,
            version=None,
            diagnostic=diagnostic,
        )

    version = (
        result.output.splitlines()[0]
        if result.output
        else "<no version output>"
    )
    return EnvironmentCheck(
        requirement=requirement,
        executable=executable,
        version=version,
        diagnostic=None,
    )
