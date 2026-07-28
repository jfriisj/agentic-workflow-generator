from __future__ import annotations

from pathlib import Path

import pytest

import agentic_workflow_generator.cli.target_runtime as cli_module
from agentic_workflow_generator.cli.target_runtime import main
from agentic_workflow_generator.domain import Diagnostic


def test_cli_reports_runtime_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli_module,
        "validate_opencode_runtime",
        lambda _paths: (),
    )

    result = main([])

    captured = capsys.readouterr()
    assert result == 0
    assert "PASS: OpenCode runtime parsed" in captured.out


def test_cli_preserves_runtime_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli_module,
        "validate_opencode_runtime",
        lambda _paths: (
            Diagnostic(
                code="AWG-TARGET-RUNTIME-005",
                message="runtime drift",
            ),
        ),
    )

    result = main([])

    captured = capsys.readouterr()
    assert result == 1
    assert "AWG-TARGET-RUNTIME-005" in captured.out
