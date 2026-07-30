from __future__ import annotations

from pathlib import Path

import pytest

from agentic_workflow_generator.application.lockfile import (
    generate_lockfile,
)
from agentic_workflow_generator.cli.lockfile_validation import (
    main,
)
from tests.support.lockfile_repository import (
    build_lockfile_repository,
)


def test_cli_accepts_canonical_lockfile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 0
    assert "PASS: Lockfile is valid." in captured.out


def test_cli_reports_input_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    changed = (
        tmp_path
        / "registry"
        / "bundles"
        / "example.bundle.json"
    )
    changed.write_text("[]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 1
    assert "AWG-LOCKFILE-007" in captured.out
    assert "AWG-LOCKFILE-004" in captured.out


def test_cli_reports_missing_lockfile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_lockfile_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "AWG-LOCKFILE-VALIDATION-900"
        in captured.out
    )
    assert "required JSON file not found" in captured.out
