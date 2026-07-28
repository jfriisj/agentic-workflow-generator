from pathlib import Path

import pytest

import agentic_workflow_generator.application.registry_snapshot as registry_snapshot_module
from agentic_workflow_generator.application.registry_snapshot import (
    RegistrySnapshotLoadError,
    RegistrySnapshotLookupError,
    RegistrySnapshotValidationError,
    load_validated_registry_snapshot,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryKind,
    RegistrySource,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_real_registry_loads_one_complete_validated_snapshot() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )

    assert len(snapshot.agents) == 8
    assert len(snapshot.artifacts) == 7
    assert len(snapshot.bundles) == 4
    assert len(snapshot.permission_profiles) == 3
    assert len(snapshot.profiles) == 4
    assert len(snapshot.skills) == 10
    assert len(snapshot.targets) == 2
    assert len(snapshot.workflows) == 4
    assert tuple(
        target.name
        for target in snapshot.targets
    ) == (
        "opencode",
        "vscode-copilot",
    )
    assert snapshot.target_by_name("opencode").owned_paths == (
        ".opencode/agents",
        ".opencode/skills",
        "AGENTS.md",
        "opencode.json",
    )

    bundle = snapshot.bundle_by_name(
        "orchestrated-delivery"
    )
    workflow = snapshot.workflow_by_name(bundle.workflow)
    profile = snapshot.profile_by_name(bundle.profile)

    assert workflow.name == "orchestrated-delivery"
    assert profile.name == "microservice-platform"
    assert len(bundle.agent_instances) == 7
    assert len(bundle.role_bindings) == 7


def test_snapshot_lookup_fails_closed_for_unknown_identity() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )

    with pytest.raises(
        RegistrySnapshotLookupError,
        match="unknown bundle 'missing'",
    ):
        snapshot.bundle_by_name("missing")


def test_snapshot_loading_fails_closed_for_missing_repository(
    tmp_path: Path,
) -> None:
    with pytest.raises(RegistrySnapshotLoadError):
        load_validated_registry_snapshot(
            ProjectPaths(tmp_path)
        )


def test_snapshot_validation_error_preserves_diagnostics() -> None:
    diagnostic = Diagnostic(
        code="AWG-TEST-001",
        message="Injected registry failure.",
    )

    with pytest.raises(
        RegistrySnapshotValidationError,
        match="skill registry validation failed",
    ) as captured:
        registry_snapshot_module._require_valid(
            "skill registry",
            (diagnostic,),
        )

    assert captured.value.boundary == "skill registry"
    assert captured.value.diagnostics == (diagnostic,)


def test_skill_content_projection_ignores_invalid_and_missing_paths(
    tmp_path: Path,
) -> None:
    invalid = RegistrySource(
        kind=RegistryKind.SKILL,
        source_path=Path(
            "registry/skills/invalid/skill.json"
        ),
        data={
            "contentPath": 42,
        },
    )
    missing = RegistrySource(
        kind=RegistryKind.SKILL,
        source_path=Path(
            "registry/skills/missing/skill.json"
        ),
        data={
            "contentPath": "SKILL.md",
        },
    )

    assert (
        registry_snapshot_module._existing_skill_content_paths(
            (
                invalid,
                missing,
            )
        )
        == frozenset()
    )


def test_snapshot_lookup_rejects_non_callable_projection() -> None:
    with pytest.raises(
        TypeError,
        match="identity projection must be callable",
    ):
        registry_snapshot_module._lookup_identity(
            (),
            "missing",
            "item",
            object(),
        )
