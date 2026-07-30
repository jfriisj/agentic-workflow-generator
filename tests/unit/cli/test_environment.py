from __future__ import annotations

from pathlib import Path

import pytest

from agentic_workflow_generator.application.environment import (
    COMMAND_REJECTED_DIAGNOSTIC,
    EnvironmentCheck,
    EnvironmentRequirement,
    EnvironmentValidationResult,
)
from agentic_workflow_generator.cli import environment
from agentic_workflow_generator.domain import Diagnostic


def test_cli_preserves_success_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirement = EnvironmentRequirement(
        name="node",
        command=("node", "--version"),
    )
    result = EnvironmentValidationResult(
        checks=(
            EnvironmentCheck(
                requirement=requirement,
                executable="/bin/node",
                version="v1.0.0",
                diagnostic=None,
            ),
        ),
        diagnostics=(),
    )
    monkeypatch.setattr(
        environment,
        "validate_environment",
        lambda paths, *, path_value: result,
    )
    monkeypatch.chdir(tmp_path)

    exit_code = environment.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "== Agentic environment validation ==" in captured.out
    assert (
        "PASS: node available at /bin/node (v1.0.0)"
        in captured.out
    )
    assert (
        "PASS: Environment validation passed. Checked "
        "1 required command(s)."
        in captured.out
    )


def test_cli_renders_stable_failure_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code=COMMAND_REJECTED_DIAGNOSTIC,
        message="node is required but failed to run.",
    )
    requirement = EnvironmentRequirement(
        name="node",
        command=("node", "--version"),
    )
    result = EnvironmentValidationResult(
        checks=(
            EnvironmentCheck(
                requirement=requirement,
                executable="/bin/node",
                version=None,
                diagnostic=diagnostic,
            ),
        ),
        diagnostics=(diagnostic,),
    )
    monkeypatch.setattr(
        environment,
        "validate_environment",
        lambda paths, *, path_value: result,
    )
    monkeypatch.chdir(tmp_path)

    exit_code = environment.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "AWG-ENVIRONMENT-003" in captured.out
    assert "node is required but failed to run" in captured.out
