from __future__ import annotations

from pathlib import Path

import pytest

from agentic_workflow_generator.cli.lockfile_generation import (
    main,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from tests.support.lockfile_repository import (
    build_lockfile_repository,
)


def test_cli_generates_canonical_lockfile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_lockfile_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 0
    assert (
        "PASS: Generated deterministic lockfile."
        in captured.out
    )
    assert "Input files: 10" in captured.out
    lockfile = read_json_object(
        tmp_path / ".agentic" / "agentic-lock.json"
    )
    assert lockfile["lockfileVersion"] == 1


def test_cli_reports_missing_repository_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 1
    assert "AWG-LOCKFILE-GENERATION-900" in captured.out
    assert (
        "No files matched lockfile input patterns."
        in captured.out
    )
