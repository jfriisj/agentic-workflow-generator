from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

import pytest

from agentic_workflow_generator.cli.target_materialization import (
    main,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
    tmp_path: Path,
) -> None:
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


def test_cli_materializes_all_targets_transactionally(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    copy_repository(tmp_path)
    stale = (
        tmp_path
        / ".opencode"
        / "agents"
        / "orchestrator.md"
    )
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 0
    assert (
        "PASS: Materialized canonical target output."
        in captured.out
    )
    assert "Targets: 2" in captured.out
    assert "Removed stale files: 1" in captured.out
    assert not stale.exists()
    assert (
        tmp_path
        / ".opencode"
        / "agents"
        / "workflow-controller.md"
    ).is_file()
    assert (
        tmp_path
        / ".github"
        / "agents"
        / "workflow-controller.agent.md"
    ).is_file()

    manifest = read_json_object(
        tmp_path
        / ".agentic"
        / "generated"
        / "output-manifest.json"
    )
    assert manifest["schemaVersion"] == "0.3.0"
    assert "bundle" not in manifest


def test_cli_preserves_schema_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    copy_repository(tmp_path)
    config_path = (
        tmp_path / ".agentic" / "agentic.json"
    )
    config = read_json_object(config_path)
    targets = config["targets"]
    assert isinstance(targets, list)
    first_target = cast(JsonObject, targets[0])
    first_target["enabled"] = False
    write_json(config_path, config)
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "AWG-TARGET-MATERIALIZATION-001"
        in captured.out
    )
    assert not (
        tmp_path
        / ".agentic"
        / "generated"
        / "output-manifest.json"
    ).exists()


def test_cli_reports_missing_repository_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main([])

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "AWG-TARGET-MATERIALIZATION-900"
        in captured.out
    )
    assert ".agentic/agentic.json" in captured.out
