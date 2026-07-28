from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from agentic_workflow_generator.application import (
    load_validated_registry_snapshot,
)
from agentic_workflow_generator.compiler import (
    ProjectMetadata,
    compile_bundle_composition,
    composition_to_json_object,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / ".agentic"
    / "schemas"
    / "agentic.schema.json"
)


def active_config_schema() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        read_json_object(SCHEMA_PATH),
    )


def test_active_config_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        active_config_schema()
    )


def test_all_real_bundles_serialize_against_schema() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    validator = Draft202012Validator(
        active_config_schema()
    )
    project = ProjectMetadata(
        name="consumer-project",
        project_type="agentic-project",
        description="Generated test configuration.",
        language_profiles=("python",),
        runtime_profiles=("python",),
        architecture_profile="typed-composition",
    )

    errors = [
        (
            bundle.name,
            error.json_path,
            error.message,
        )
        for bundle in snapshot.bundles
        for error in validator.iter_errors(
            composition_to_json_object(
                compile_bundle_composition(
                    snapshot,
                    project,
                    bundle.name,
                )
            )
        )
    ]

    assert errors == []


def test_active_repository_config_matches_schema() -> None:
    validator = Draft202012Validator(
        active_config_schema()
    )
    config = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "agentic.json"
    )

    assert list(validator.iter_errors(config)) == []


def test_schema_rejects_obsolete_runtime_authority() -> None:
    config = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "agentic.json"
    )
    config["agents"] = []
    config["gates"] = []

    errors = list(
        Draft202012Validator(
            active_config_schema()
        ).iter_errors(config)
    )

    assert len(errors) == 1
    assert errors[0].validator == (
        "additionalProperties"
    )
    assert "agents" in errors[0].message
    assert "gates" in errors[0].message


def test_schema_rejects_duplicate_target_entries() -> None:
    config = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "agentic.json"
    )
    targets = cast(list[Any], config["targets"])
    targets.append(dict(cast(dict[str, Any], targets[0])))

    errors = list(
        Draft202012Validator(
            active_config_schema()
        ).iter_errors(config)
    )

    assert any(
        error.validator == "uniqueItems"
        and error.json_path == "$.targets"
        for error in errors
    )


def test_schema_requires_target_enabled_to_be_true() -> None:
    config = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "agentic.json"
    )
    targets = cast(list[Any], config["targets"])
    first_target = cast(dict[str, Any], targets[0])
    first_target["enabled"] = "true"

    errors = list(
        Draft202012Validator(
            active_config_schema()
        ).iter_errors(config)
    )

    assert any(
        error.validator == "const"
        and error.json_path == "$.targets[0].enabled"
        for error in errors
    )
