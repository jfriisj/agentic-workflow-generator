from __future__ import annotations

from pathlib import Path

import pytest

from agentic_workflow_generator.application import environment
from agentic_workflow_generator.infrastructure.errors import (
    ProcessExecutionError,
)
from agentic_workflow_generator.infrastructure.processes import (
    ProcessResult,
)
from agentic_workflow_generator.registry import ProjectPaths


def test_validate_environment_accepts_all_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        environment,
        "resolve_executable",
        lambda command, *, path: f"/bin/{command}",
    )
    monkeypatch.setattr(
        environment,
        "run_process",
        lambda executable, arguments, *, cwd, timeout_seconds: ProcessResult(
            executable=executable,
            arguments=arguments,
            exit_code=0,
            output="version 1.0\nextra",
        ),
    )

    result = environment.validate_environment(
        ProjectPaths(tmp_path.resolve()),
        path_value="/bin",
    )

    assert result.diagnostics == ()
    assert len(result.checks) == 6
    assert all(
        check.version == "version 1.0"
        for check in result.checks
    )


def test_validate_environment_applies_command_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_timeouts: list[float | None] = []

    monkeypatch.setattr(
        environment,
        "resolve_executable",
        lambda command, *, path: f"/bin/{command}",
    )

    def run(
        executable: str,
        arguments: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float | None,
    ) -> ProcessResult:
        del cwd
        observed_timeouts.append(timeout_seconds)
        return ProcessResult(
            executable=executable,
            arguments=arguments,
            exit_code=0,
            output="version 1.0",
        )

    monkeypatch.setattr(
        environment,
        "run_process",
        run,
    )

    result = environment.validate_environment(
        ProjectPaths(tmp_path.resolve()),
        path_value="/bin",
    )

    assert result.diagnostics == ()
    assert observed_timeouts == [
        environment.COMMAND_TIMEOUT_SECONDS
    ] * len(environment.REQUIRED_COMMANDS)


def test_validate_environment_reports_missing_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        environment,
        "resolve_executable",
        lambda command, *, path: (
            None
            if command == "node"
            else f"/bin/{command}"
        ),
    )
    monkeypatch.setattr(
        environment,
        "run_process",
        lambda executable, arguments, *, cwd, timeout_seconds: ProcessResult(
            executable=executable,
            arguments=arguments,
            exit_code=0,
            output="version 1.0",
        ),
    )

    result = environment.validate_environment(
        ProjectPaths(tmp_path.resolve()),
        path_value="/bin",
    )

    assert {
        diagnostic.code
        for diagnostic in result.diagnostics
    } == {
        environment.EXECUTABLE_MISSING_DIAGNOSTIC,
    }


def test_validate_environment_reports_rejected_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        environment,
        "resolve_executable",
        lambda command, *, path: f"/bin/{command}",
    )

    def run(
        executable: str,
        arguments: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float | None,
    ) -> ProcessResult:
        assert timeout_seconds == environment.COMMAND_TIMEOUT_SECONDS
        del cwd
        return ProcessResult(
            executable=executable,
            arguments=arguments,
            exit_code=9 if executable.endswith("node") else 0,
            output="node failed",
        )

    monkeypatch.setattr(
        environment,
        "run_process",
        run,
    )

    result = environment.validate_environment(
        ProjectPaths(tmp_path.resolve()),
        path_value="/bin",
    )

    assert {
        diagnostic.code
        for diagnostic in result.diagnostics
    } == {
        environment.COMMAND_REJECTED_DIAGNOSTIC,
    }
    assert "node is required but failed to run" in (
        result.diagnostics[0].message
    )


def test_validate_environment_reports_execution_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        environment,
        "resolve_executable",
        lambda command, *, path: f"/bin/{command}",
    )

    def run(
        executable: str,
        arguments: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float | None,
    ) -> ProcessResult:
        assert timeout_seconds == environment.COMMAND_TIMEOUT_SECONDS
        del arguments, cwd

        if executable.endswith("node"):
            raise ProcessExecutionError(
                executable,
                (),
                reason="cannot execute",
            )

        return ProcessResult(
            executable=executable,
            arguments=(),
            exit_code=0,
            output="version 1.0",
        )

    monkeypatch.setattr(
        environment,
        "run_process",
        run,
    )

    result = environment.validate_environment(
        ProjectPaths(tmp_path.resolve()),
        path_value="/bin",
    )

    assert {
        diagnostic.code
        for diagnostic in result.diagnostics
    } == {
        environment.EXECUTION_FAILURE_DIAGNOSTIC,
    }
