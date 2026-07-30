from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest

from agentic_workflow_generator.application.registry_references import (
    validate_registry_references,
)
from agentic_workflow_generator.application.target_materialization import (
    TargetMaterializationDriftError,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
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
    shutil.copy2(
        REPOSITORY_ROOT / ".agentic" / "agentic.json",
        tmp_path / ".agentic" / "agentic.json",
    )
    return ProjectPaths(tmp_path)


def test_real_registry_references_validate_canonical_composition() -> None:
    result = validate_registry_references(
        ProjectPaths(REPOSITORY_ROOT)
    )

    assert result.summary.agent_count == 8
    assert result.summary.target_count == 2
    assert result.summary.workflow_count == 4
    assert result.summary.profile_count == 4
    assert result.summary.artifact_count == 7
    assert result.summary.skill_capability_count == 21


def test_registry_references_reject_active_composition_drift(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    config = _read_json(paths.active_config)
    selection = cast(dict[str, Any], config["selection"])
    bundle = cast(dict[str, Any], selection["bundle"])
    bundle["version"] = "9.9.9"
    _write_json(paths.active_config, config)

    with pytest.raises(
        TargetMaterializationDriftError,
        match="does not match the canonical compiled composition",
    ):
        validate_registry_references(paths)


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
