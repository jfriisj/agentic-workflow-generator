from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryKind,
    RegistryLoader,
)

REPOSITORY_ROOT = Path(__file__).parents[3]


def profile_schema() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        read_json_object(
            REPOSITORY_ROOT
            / ".agentic"
            / "schemas"
            / "registry"
            / "profile.schema.json"
        ),
    )


def test_profile_schema_is_valid() -> None:
    Draft202012Validator.check_schema(profile_schema())


def test_registered_profiles_match_schema() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    validator = Draft202012Validator(profile_schema())
    sources = RegistryLoader(paths).load(RegistryKind.PROFILE)

    errors = [
        (
            source.source_path,
            error.message,
        )
        for source in sources
        for error in validator.iter_errors(source.to_json_object())
    ]

    assert errors == []


def test_profile_schema_requires_recommended_workflow() -> None:
    schema = profile_schema()
    required = schema["required"]

    assert isinstance(required, list)
    assert "recommendedWorkflow" in required
    assert "workflow" not in required


def test_profile_schema_rejects_obsolete_workflow_field() -> None:
    schema = profile_schema()
    properties = schema["properties"]

    assert schema["additionalProperties"] is False
    assert isinstance(properties, dict)
    assert "recommendedWorkflow" in properties
    assert "workflow" not in properties
