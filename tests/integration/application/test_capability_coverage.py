"""Integration tests for the capability-coverage application service."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest

from agentic_workflow_generator.application.capability_coverage import (
    analyze_capability_coverage,
)
from agentic_workflow_generator.application.registry_snapshot import (
    RegistrySnapshotValidationError,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_registry(
    tmp_path: Path,
) -> ProjectPaths:
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        tmp_path / "registry",
    )
    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        tmp_path / ".agentic" / "schemas",
    )
    return ProjectPaths(tmp_path)


def test_real_registry_has_complete_global_capability_coverage() -> None:
    result = analyze_capability_coverage(
        ProjectPaths(REPOSITORY_ROOT)
    )

    assert result.is_complete
    assert result.required_count == 21
    assert result.provided_count == 21
    assert result.missing == ()
    assert result.unused == ()
    assert result.duplicates == ()
    assert result.diagnostics == ()


def test_removed_skill_capability_fails_closed_at_snapshot_boundary(
    tmp_path: Path,
) -> None:
    paths = copy_registry(tmp_path)
    skill_path = (
        paths.registry_root
        / "skills"
        / "workflow-routing"
        / "skill.json"
    )
    data = _read_json(skill_path)
    provides = cast(list[Any], data["provides"])
    provides.remove("workflow.route")
    _write_json(skill_path, data)

    with pytest.raises(
        RegistrySnapshotValidationError,
    ) as exc_info:
        analyze_capability_coverage(paths)

    assert exc_info.value.boundary == "agent registry"
    assert any(
        "workflow.route" in diagnostic.message
        for diagnostic in exc_info.value.diagnostics
    )


def _read_json(path: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
