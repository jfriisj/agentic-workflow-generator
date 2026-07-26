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


def test_permission_profile_schema_is_valid() -> None:
    schema = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "schemas"
        / "registry"
        / "permission-profile.schema.json"
    )

    Draft202012Validator.check_schema(cast(dict[str, Any], schema))


def test_registered_permission_profiles_match_schema() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    schema = read_json_object(
        paths.schema_root / "registry" / "permission-profile.schema.json"
    )
    validator = Draft202012Validator(cast(dict[str, Any], schema))
    sources = RegistryLoader(paths).load(RegistryKind.PERMISSION_PROFILE)

    errors = [
        (
            source.source_path,
            error.message,
        )
        for source in sources
        for error in validator.iter_errors(source.to_json_object())
    ]

    assert errors == []
