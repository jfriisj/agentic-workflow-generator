"""Tests for the typed capability-coverage CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

import agentic_workflow_generator.cli.capability_coverage as command
from agentic_workflow_generator.application.registry_snapshot import (
    RegistrySnapshotValidationError,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.validation.capability_coverage import (
    CapabilityConsumers,
    CapabilityCoverageResult,
    CapabilityProviders,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_capability_coverage_cli_preserves_success_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPOSITORY_ROOT)

    result = command.main()

    assert result == 0
    assert capsys.readouterr().out == (
        "Required runtime capabilities: 21\n"
        "Skill capabilities: 21\n"
        "\n"
        "Missing skill coverage:\n"
        "  none\n"
        "\n"
        "Unused skill capabilities:\n"
        "  none\n"
        "\n"
        "Duplicate skill capabilities:\n"
        "  none\n"
        "\n"
        "PASS: Runtime capability coverage is complete. "
        "Checked 21 required capability/capabilities.\n"
    )


def test_capability_coverage_cli_renders_incomplete_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = CapabilityConsumers(
        capability="missing.capability",
        role_bindings=("delivery:owner",),
    )
    unused = CapabilityProviders(
        capability="unused.capability",
        skills=("unused-skill",),
    )
    duplicate = CapabilityProviders(
        capability="duplicate.capability",
        skills=("duplicate-a", "duplicate-b"),
    )
    diagnostics = (
        Diagnostic(
            code="AWG-CAPABILITY-COVERAGE-001",
            message=(
                "capability 'missing.capability' has no "
                "registered skill provider"
            ),
        ),
        Diagnostic(
            code="AWG-CAPABILITY-COVERAGE-002",
            message=(
                "capability 'unused.capability' is unused"
            ),
        ),
        Diagnostic(
            code="AWG-CAPABILITY-COVERAGE-003",
            message=(
                "capability 'duplicate.capability' has "
                "multiple providers"
            ),
        ),
    )

    monkeypatch.setattr(
        command,
        "analyze_capability_coverage",
        lambda _paths: CapabilityCoverageResult(
            required=(missing,),
            provided=(unused, duplicate),
            missing=(missing,),
            unused=(unused,),
            duplicates=(duplicate,),
            diagnostics=diagnostics,
        ),
    )

    result = command.main()

    assert result == 1
    output = capsys.readouterr().out
    assert "Required runtime capabilities: 1" in output
    assert "Skill capabilities: 2" in output
    assert "AWG-CAPABILITY-COVERAGE-001" in output
    assert "AWG-CAPABILITY-COVERAGE-002" in output
    assert "AWG-CAPABILITY-COVERAGE-003" in output
    assert "PASS:" not in output


def test_capability_coverage_cli_renders_snapshot_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="AWG-SKILL-006",
        message="Injected duplicate provider.",
        source_path="registry/skills/duplicate/skill.json",
        location="provides",
    )

    def fail_analysis(
        _paths: object,
    ) -> None:
        raise RegistrySnapshotValidationError(
            "skill registry",
            (diagnostic,),
        )

    monkeypatch.setattr(
        command,
        "analyze_capability_coverage",
        fail_analysis,
    )

    result = command.main()

    assert result == 1
    output = capsys.readouterr().out
    assert (
        "FAIL: Capability coverage could not be analyzed."
        in output
    )
    assert "AWG-SKILL-006" in output
    assert "Injected duplicate provider." in output


def test_capability_coverage_cli_reports_command_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_analysis(
        _paths: object,
    ) -> None:
        raise ValueError("Injected command failure.")

    monkeypatch.setattr(
        command,
        "analyze_capability_coverage",
        fail_analysis,
    )

    result = command.main()

    assert result == 1
    output = capsys.readouterr().out
    assert "AWG-CAPABILITY-COVERAGE-900" in output
    assert "Injected command failure." in output
