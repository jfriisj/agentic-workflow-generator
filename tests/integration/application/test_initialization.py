from dataclasses import replace
from pathlib import Path

import pytest

from agentic_workflow_generator.application import (
    InitializationError,
    InitializationValidationError,
    load_initialization_service,
    load_project_metadata,
)
from agentic_workflow_generator.domain import Profile
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    serialize_json,
    write_json,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def advisory_profile() -> Profile:
    return Profile(
        name="lean-delivery",
        version="0.2.0",
        description="Lean delivery profile.",
        recommended_workflow="lean-delivery",
        recommended_agents=("Requirements",),
        recommended_capabilities=(
            "requirements.elicit",
        ),
        recommended_language_profiles=("python",),
        recommended_runtime_profiles=("python",),
    )


def test_direct_bundle_plan_preserves_project_metadata() -> None:
    service = load_initialization_service(
        ProjectPaths(REPOSITORY_ROOT)
    )

    plan = service.plan_bundle(
        "orchestrated-delivery"
    )

    assert plan.setup_profile is None
    assert plan.setup_profile_json is None
    assert plan.bundle == "orchestrated-delivery"
    assert plan.targets == (
        "opencode",
        "vscode-copilot",
    )
    assert plan.composition.project.name == (
        "agentic-workflow-generator"
    )
    assert plan.active_config["selection"] == {
        "bundle": {
            "name": "orchestrated-delivery",
            "version": "0.3.0",
        },
        "profile": {
            "name": "microservice-platform",
            "version": "0.2.0",
        },
        "workflow": {
            "name": "orchestrated-delivery",
            "version": "0.3.0",
        },
    }
    assert "agents" not in plan.active_config
    assert "gates" not in plan.active_config


def test_guided_setup_plan_compiles_selected_targets() -> None:
    service = load_initialization_service(
        ProjectPaths(REPOSITORY_ROOT)
    )

    plan = service.plan_setup(
        "orchestrated-delivery-greenfield",
        {
            "target-platforms": "opencode-only",
        },
    )

    assert plan.bundle == "orchestrated-delivery"
    assert plan.targets == ("opencode",)
    assert plan.setup_profile is not None
    assert plan.setup_profile_json is not None
    assert plan.setup_profile_json["selected"] == {
        "bundle": "orchestrated-delivery",
        "targets": ["opencode"],
    }
    assert plan.active_config["targets"] == [
        {
            "name": "opencode",
            "enabled": True,
            "priority": 1,
        }
    ]


def test_missing_active_config_uses_explicit_profile_defaults(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths(tmp_path)

    metadata = load_project_metadata(
        paths,
        advisory_profile(),
    )

    assert metadata.name == tmp_path.name
    assert metadata.project_type == "agentic-project"
    assert metadata.language_profiles == ("python",)
    assert metadata.runtime_profiles == ("python",)
    assert metadata.architecture_profile == "lean-delivery"


def test_invalid_existing_project_metadata_fails_closed(
    tmp_path: Path,
) -> None:
    agentic_root = tmp_path / ".agentic"
    agentic_root.mkdir()
    write_json(
        agentic_root / "agentic.json",
        {
            "project": {
                "name": "",
            },
        },
    )

    with pytest.raises(
        InitializationError,
        match=r"project\.name",
    ):
        load_project_metadata(
            ProjectPaths(tmp_path),
            advisory_profile(),
        )


def copy_initialization_repository(
    tmp_path: Path,
) -> ProjectPaths:
    import shutil

    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        tmp_path / "registry",
    )
    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        tmp_path / ".agentic" / "schemas",
    )

    return ProjectPaths(tmp_path)


def test_guided_commit_writes_both_outputs_transactionally(
    tmp_path: Path,
) -> None:
    paths = copy_initialization_repository(tmp_path)
    service = load_initialization_service(paths)
    plan = service.plan_setup(
        "orchestrated-delivery-greenfield",
        {
            "target-platforms": "opencode-only",
        },
    )

    result = service.commit(plan)

    assert result.changed is True
    assert result.written_paths == (
        paths.active_config,
        paths.setup_profile,
    )
    assert paths.active_config.is_file()
    assert paths.setup_profile.is_file()
    assert (
        paths.active_config.read_text(encoding="utf-8")
        == serialize_json(plan.active_config)
    )
    assert (
        paths.setup_profile.read_text(encoding="utf-8")
        == serialize_json(plan.setup_profile_json)
    )


def test_repeated_commit_skips_byte_identical_outputs(
    tmp_path: Path,
) -> None:
    paths = copy_initialization_repository(tmp_path)
    service = load_initialization_service(paths)
    plan = service.plan_setup(
        "lean-delivery-greenfield"
    )
    first = service.commit(plan)
    config_mtime = paths.active_config.stat().st_mtime_ns
    profile_mtime = paths.setup_profile.stat().st_mtime_ns

    second = service.commit(plan)

    assert first.changed is True
    assert second.changed is False
    assert second.written_paths == ()
    assert paths.active_config.stat().st_mtime_ns == (
        config_mtime
    )
    assert paths.setup_profile.stat().st_mtime_ns == (
        profile_mtime
    )


def test_invalid_plan_is_rejected_before_any_write(
    tmp_path: Path,
) -> None:
    paths = copy_initialization_repository(tmp_path)
    service = load_initialization_service(paths)
    plan = service.plan_bundle("lean-delivery")
    plan.active_config["agents"] = []

    with pytest.raises(
        InitializationValidationError,
    ) as captured:
        service.commit(plan)

    assert captured.value.boundary == (
        "active configuration"
    )
    assert captured.value.diagnostics
    assert not paths.active_config.exists()
    assert not paths.setup_profile.exists()


def test_plan_rejects_setup_model_without_json(
    tmp_path: Path,
) -> None:
    paths = copy_initialization_repository(tmp_path)
    service = load_initialization_service(paths)
    guided = service.plan_setup(
        "lean-delivery-greenfield"
    )
    direct = service.plan_bundle("lean-delivery")
    invalid = replace(
        direct,
        setup_profile=guided.setup_profile,
    )

    with pytest.raises(
        InitializationError,
        match="model exists without JSON output",
    ):
        service.validate_plan(invalid)


def test_plan_rejects_setup_json_without_model(
    tmp_path: Path,
) -> None:
    paths = copy_initialization_repository(tmp_path)
    service = load_initialization_service(paths)
    guided = service.plan_setup(
        "lean-delivery-greenfield"
    )
    invalid = replace(
        guided,
        setup_profile=None,
    )

    with pytest.raises(
        InitializationError,
        match="JSON exists without typed model",
    ):
        service.validate_plan(invalid)


def test_invalid_setup_profile_is_rejected_at_commit_boundary(
    tmp_path: Path,
) -> None:
    paths = copy_initialization_repository(tmp_path)
    service = load_initialization_service(paths)
    plan = service.plan_setup(
        "lean-delivery-greenfield"
    )
    invalid_json = dict(plan.setup_profile_json or {})
    invalid_json["selected"] = {}
    invalid = replace(
        plan,
        setup_profile_json=invalid_json,
    )

    with pytest.raises(
        InitializationValidationError,
    ) as captured:
        service.validate_plan(invalid)

    assert captured.value.boundary == "setup profile"
    assert captured.value.diagnostics


def test_setup_profile_round_trip_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    paths = copy_initialization_repository(tmp_path)
    service = load_initialization_service(paths)
    lean = service.plan_setup(
        "lean-delivery-greenfield"
    )
    review = service.plan_setup(
        "review-heavy-delivery-greenfield"
    )
    mismatched = replace(
        lean,
        setup_profile_json=review.setup_profile_json,
    )

    with pytest.raises(
        InitializationError,
        match="does not match the planned typed profile",
    ):
        service.validate_plan(mismatched)


def test_existing_project_metadata_requires_project_object(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths(tmp_path)
    paths.active_config.parent.mkdir()
    write_json(
        paths.active_config,
        {
            "project": [],
        },
    )

    with pytest.raises(
        InitializationError,
        match="project must be an object",
    ):
        load_project_metadata(
            paths,
            advisory_profile(),
        )


@pytest.mark.parametrize(
    (
        "language_profiles",
        "runtime_profiles",
        "expected",
    ),
    [
        (
            (),
            ("python",),
            "no recommended language profiles",
        ),
        (
            ("python",),
            (),
            "no recommended runtime profiles",
        ),
    ],
)
def test_default_metadata_requires_profile_recommendations(
    tmp_path: Path,
    language_profiles: tuple[str, ...],
    runtime_profiles: tuple[str, ...],
    expected: str,
) -> None:
    profile = replace(
        advisory_profile(),
        recommended_language_profiles=language_profiles,
        recommended_runtime_profiles=runtime_profiles,
    )

    with pytest.raises(
        InitializationError,
        match=expected,
    ):
        load_project_metadata(
            ProjectPaths(tmp_path),
            profile,
        )


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "expected",
    ),
    [
        (
            "languageProfiles",
            [],
            "must be a non-empty list",
        ),
        (
            "runtimeProfiles",
            ["python", "python"],
            "must contain unique values",
        ),
    ],
)
def test_existing_project_metadata_rejects_invalid_profile_lists(
    tmp_path: Path,
    field: str,
    value: JsonValue,
    expected: str,
) -> None:
    paths = ProjectPaths(tmp_path)
    paths.active_config.parent.mkdir()
    project: JsonObject = {
        "name": "consumer",
        "type": "agentic-project",
        "description": "Consumer project.",
        "languageProfiles": ["python"],
        "runtimeProfiles": ["python"],
        "architectureProfile": "lean-delivery",
    }
    project[field] = value
    write_json(
        paths.active_config,
        {
            "project": project,
        },
    )

    with pytest.raises(
        InitializationError,
        match=expected,
    ):
        load_project_metadata(
            paths,
            advisory_profile(),
        )
