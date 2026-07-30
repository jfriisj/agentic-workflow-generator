from __future__ import annotations

from pathlib import Path

import pytest

import agentic_workflow_generator.cli.registry_references as command
from agentic_workflow_generator.application.target_materialization import (
    TargetMaterializationValidationError,
)
from agentic_workflow_generator.domain import Diagnostic

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_registry_reference_cli_preserves_success_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPOSITORY_ROOT)

    result = command.main()

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Registry references are valid.\n"
        "Agents: 8\n"
        "Targets: 2\n"
        "Workflows: 4\n"
        "Profiles: 4\n"
        "Artifacts: 7\n"
        "Skill capabilities: 21\n"
    )


def test_registry_reference_cli_renders_typed_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="AWG-TEST-001",
        message="Injected active composition failure.",
        source_path=".agentic/agentic.json",
        location="$.selection",
    )

    def fail_validation(
        _paths: object,
    ) -> None:
        raise TargetMaterializationValidationError(
            (diagnostic,)
        )

    monkeypatch.setattr(
        command,
        "validate_registry_references",
        fail_validation,
    )

    result = command.main()

    assert result == 1
    output = capsys.readouterr().out
    assert "AWG-TEST-001" in output
    assert ".agentic/agentic.json" in output
    assert "$.selection" in output
    assert "Injected active composition failure." in output


def test_registry_reference_cli_reports_command_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_validation(
        _paths: object,
    ) -> None:
        raise ValueError("Injected command failure.")

    monkeypatch.setattr(
        command,
        "validate_registry_references",
        fail_validation,
    )

    result = command.main()

    assert result == 1
    output = capsys.readouterr().out
    assert "AWG-REGISTRY-REFERENCE-900" in output
    assert "Injected command failure." in output
