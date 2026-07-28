from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agentic_workflow_generator.application.target_materialization import (
    materialize_targets,
)
from agentic_workflow_generator.cli.target_output import main
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
    tmp_path: Path,
) -> ProjectPaths:
    agentic_root = tmp_path / ".agentic"
    agentic_root.mkdir()

    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        agentic_root / "schemas",
    )
    shutil.copy2(
        REPOSITORY_ROOT / ".agentic" / "agentic.json",
        agentic_root / "agentic.json",
    )
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        tmp_path / "registry",
    )

    return ProjectPaths(tmp_path.resolve())


def test_cli_accepts_canonical_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    materialize_targets(paths)
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 0
    assert (
        "PASS: Generated target output is canonical."
        in captured.out
    )


def test_cli_reports_output_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    materialize_targets(paths)
    generated = paths.repository_path(
        ".opencode/agents/workflow-controller.md"
    )
    generated.write_bytes(b"drift")
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 1
    assert "AWG-TARGET-OUTPUT-003" in captured.out
