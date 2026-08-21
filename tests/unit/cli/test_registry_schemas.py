from __future__ import annotations

from pathlib import Path

import pytest

import agentic_workflow_generator.cli.registry_schemas as command
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.validation.registry_schemas import (
    RegistrySchemaValidationResult,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_registry_schema_cli_preserves_success_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPOSITORY_ROOT)

    result = command.main()

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Registry JSON schemas are valid. "
        "Checked 48 registry file(s).\n"
    )


def test_registry_schema_cli_preserves_failure_heading(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="AWG-REGISTRY-SCHEMA-004",
        message="schema violation: injected failure",
        source_path="registry/agents/example/agent.json",
        location="$.version",
    )

    monkeypatch.setattr(
        command,
        "validate_registry_schemas",
        lambda _paths: RegistrySchemaValidationResult(
            checked_document_count=1,
            diagnostics=(diagnostic,),
        ),
    )

    result = command.main()

    assert result == 1
    output = capsys.readouterr().out
    assert output.startswith(
        "ERROR: Registry schema validation failed.\n"
    )
    assert "AWG-REGISTRY-SCHEMA-004" in output
    assert "$.version" in output
    assert "injected failure" in output


def test_registry_schema_cli_reports_command_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_validation(
        _paths: object,
    ) -> None:
        raise ValueError("Injected command failure.")

    monkeypatch.setattr(
        command,
        "validate_registry_schemas",
        fail_validation,
    )

    result = command.main()

    assert result == 1
    output = capsys.readouterr().out
    assert "AWG-REGISTRY-SCHEMA-900" in output
    assert "Injected command failure." in output
