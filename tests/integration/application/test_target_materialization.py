from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

import pytest

from agentic_workflow_generator.application.target_materialization import (
    TargetMaterializationDriftError,
    TargetMaterializationError,
    TargetMaterializationValidationError,
    build_target_materialization_plan,
    commit_target_materialization,
    load_active_composition,
)
from agentic_workflow_generator.compiler import (
    composition_to_json_object,
)
from agentic_workflow_generator.infrastructure import (
    AtomicWriteError,
    JsonObject,
    read_json_object,
    write_json,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository_boundary(
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


def test_real_active_config_recompiles_exactly() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)

    assert (
        composition_to_json_object(active.composition)
        == active.serialized
        == read_json_object(paths.active_config)
    )


def test_active_config_drift_fails_closed(
    tmp_path: Path,
) -> None:
    paths = copy_repository_boundary(tmp_path)
    config = read_json_object(paths.active_config)

    instances = config["agentInstances"]
    assert isinstance(instances, list)
    first_instance = cast(JsonObject, instances[0])
    first_instance["displayName"] = "Drifted Agent"

    write_json(paths.active_config, config)

    with pytest.raises(
        TargetMaterializationDriftError,
        match="does not match the canonical compiled composition",
    ):
        load_active_composition(paths)


def test_schema_invalid_active_config_fails_closed(
    tmp_path: Path,
) -> None:
    paths = copy_repository_boundary(tmp_path)
    config = read_json_object(paths.active_config)

    targets = config["targets"]
    assert isinstance(targets, list)
    first_target = cast(JsonObject, targets[0])
    first_target["enabled"] = False

    write_json(paths.active_config, config)

    with pytest.raises(
        TargetMaterializationValidationError,
    ) as captured:
        load_active_composition(paths)

    assert captured.value.diagnostics
    assert {
        diagnostic.code
        for diagnostic in captured.value.diagnostics
    } == {"AWG-TARGET-MATERIALIZATION-001"}


def test_unknown_selected_bundle_fails_closed(
    tmp_path: Path,
) -> None:
    paths = copy_repository_boundary(tmp_path)
    config = read_json_object(paths.active_config)

    selection = cast(JsonObject, config["selection"])
    bundle = cast(JsonObject, selection["bundle"])
    bundle["name"] = "missing-bundle"

    write_json(paths.active_config, config)

    with pytest.raises(
        TargetMaterializationError,
        match="cannot compile canonical active composition",
    ):
        load_active_composition(paths)


def test_commit_writes_manifest_and_removes_stale_output(
    tmp_path: Path,
) -> None:
    paths = copy_repository_boundary(tmp_path)
    stale = paths.repository_path(
        ".opencode/agents/orchestrator.md"
    )
    existing = paths.repository_path(
        ".opencode/agents/workflow-controller.md"
    )

    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")
    existing.write_bytes(b"old-controller")

    plan = build_target_materialization_plan(paths)

    assert Path(
        ".opencode/agents/orchestrator.md"
    ) in plan.stale_files

    result = commit_target_materialization(
        paths,
        plan,
    )

    expected_file_count = sum(
        len(target.files)
        for target in plan.rendered_targets
    )

    assert not stale.exists()
    assert existing.read_bytes() != b"old-controller"
    assert paths.manifest.read_bytes() == plan.manifest_bytes
    assert read_json_object(paths.manifest) == plan.manifest
    assert result.target_count == len(
        plan.rendered_targets
    )
    assert result.generated_file_count == expected_file_count
    assert result.removed_file_count == 1
    assert not (
        paths.generated_root / "resolution.json"
    ).exists()


def test_commit_rolls_back_writes_manifest_and_removals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = copy_repository_boundary(tmp_path)
    stale = paths.repository_path(
        ".opencode/agents/orchestrator.md"
    )
    existing = paths.repository_path(
        ".opencode/agents/workflow-controller.md"
    )
    newly_created = paths.repository_path(
        ".github/agents/requirements-worker.agent.md"
    )

    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")
    existing.write_bytes(b"old-controller")
    paths.generated_root.mkdir()
    paths.manifest.write_bytes(b"old-manifest")

    plan = build_target_materialization_plan(paths)
    original_unlink = Path.unlink

    def fail_stale_removal(
        self: Path,
        missing_ok: bool = False,
    ) -> None:
        if self == stale:
            raise OSError("injected stale removal failure")

        original_unlink(
            self,
            missing_ok=missing_ok,
        )

    monkeypatch.setattr(
        Path,
        "unlink",
        fail_stale_removal,
    )

    with pytest.raises(
        AtomicWriteError,
        match="could not remove file",
    ):
        commit_target_materialization(
            paths,
            plan,
        )

    assert stale.read_bytes() == b"stale"
    assert existing.read_bytes() == b"old-controller"
    assert paths.manifest.read_bytes() == b"old-manifest"
    assert not newly_created.exists()
    assert not (
        paths.generated_root / "resolution.json"
    ).exists()

def test_commit_removes_obsolete_resolution_output(
    tmp_path: Path,
) -> None:
    paths = copy_repository_boundary(tmp_path)
    resolution = (
        paths.generated_root / "resolution.json"
    )
    resolution.parent.mkdir(parents=True)
    resolution.write_bytes(b"{}")

    plan = build_target_materialization_plan(paths)

    assert Path(
        ".agentic/generated/resolution.json"
    ) in plan.stale_files

    result = commit_target_materialization(
        paths,
        plan,
    )

    assert not resolution.exists()
    assert result.removed_file_count == 1
