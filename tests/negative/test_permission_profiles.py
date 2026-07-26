from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure import (
    JsonObject,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.permission_profiles import (
    BASH_REQUIRES_READ_DIAGNOSTIC,
    EDIT_REQUIRES_WRITE_DIAGNOSTIC,
    FOLDER_NAME_DIAGNOSTIC,
    WRITE_REQUIRES_READ_DIAGNOSTIC,
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
    "additionalProperties": False,
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


@pytest.mark.parametrize(
    ("folder", "data", "expected_code"),
    [
        (
            "read-only",
            {
                "name": "wrong-name",
                "version": "0.1.0",
                "description": "Read-only.",
                "read": True,
                "write": False,
                "edit": False,
                "bash": "deny",
            },
            FOLDER_NAME_DIAGNOSTIC,
        ),
        (
            "implementation",
            {
                "name": "implementation",
                "version": "0.1.0",
                "description": "Implementation.",
                "read": False,
                "write": True,
                "edit": False,
                "bash": "deny",
            },
            WRITE_REQUIRES_READ_DIAGNOSTIC,
        ),
        (
            "implementation",
            {
                "name": "implementation",
                "version": "0.1.0",
                "description": "Implementation.",
                "read": True,
                "write": False,
                "edit": True,
                "bash": "deny",
            },
            EDIT_REQUIRES_WRITE_DIAGNOSTIC,
        ),
        (
            "test-runner",
            {
                "name": "test-runner",
                "version": "0.1.0",
                "description": "Test runner.",
                "read": False,
                "write": False,
                "edit": False,
                "bash": "limited",
            },
            BASH_REQUIRES_READ_DIAGNOSTIC,
        ),
    ],
)
def test_invalid_permission_profile_fails_closed(
    folder: str,
    data: JsonObject,
    expected_code: str,
) -> None:
    source = RegistrySource(
        kind=RegistryKind.PERMISSION_PROFILE,
        source_path=Path(
            f"registry/permission-profiles/{folder}/permission-profile.json"
        ),
        data=data,
    )

    result = validate_permission_profile_registry(
        (source,),
        SCHEMA,
    )

    assert not result.is_valid
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        expected_code,
    )
