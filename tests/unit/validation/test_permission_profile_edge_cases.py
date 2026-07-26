from pathlib import Path

from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.infrastructure import (
    JsonObject,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.permission_profiles import (
    VERSION_DIAGNOSTIC,
    _schema_error_location,
    validate_permission_profile_registry,
)

SCHEMA: JsonObject = {
    "type": "object",
    "required": [
        "name",
        "version",
        "description",
        "read",
        "write",
        "edit",
        "bash",
    ],
    "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "description": {"type": "string"},
        "read": {"type": "boolean"},
        "write": {"type": "boolean"},
        "edit": {"type": "boolean"},
        "bash": {
            "enum": [
                "deny",
                "limited",
                "allow",
            ]
        },
    },
}


def test_empty_version_is_rejected() -> None:
    source = RegistrySource(
        kind=RegistryKind.PERMISSION_PROFILE,
        source_path=Path(
            "registry/permission-profiles/read-only/permission-profile.json"
        ),
        data={
            "name": "read-only",
            "version": " ",
            "description": "Read-only access.",
            "read": True,
            "write": False,
            "edit": False,
            "bash": "deny",
        },
    )

    result = validate_permission_profile_registry(
        (source,),
        SCHEMA,
    )

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        VERSION_DIAGNOSTIC,
    )


def test_schema_location_formats_array_index() -> None:
    error = ValidationError(
        "invalid item",
        path=("items", 0),
    )

    assert _schema_error_location(error) == "$.items[0]"
