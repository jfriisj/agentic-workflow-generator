from pathlib import Path

from agentic_workflow_generator.infrastructure import (
    JsonObject,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.permission_profiles import (
    BASH_REQUIRES_READ_DIAGNOSTIC,
    DESCRIPTION_DIAGNOSTIC,
    DUPLICATE_NAME_DIAGNOSTIC,
    EDIT_REQUIRES_WRITE_DIAGNOSTIC,
    FOLDER_NAME_DIAGNOSTIC,
    NAME_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
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
        "name": {
            "type": "string",
            "minLength": 1,
        },
        "version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+$",
        },
        "description": {
            "type": "string",
            "minLength": 1,
        },
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


def source(
    *,
    name: str = "read-only",
    folder: str = "read-only",
    read: bool = True,
    write: bool = False,
    edit: bool = False,
    bash: str = "deny",
    description: str = "Read-only access.",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.PERMISSION_PROFILE,
        source_path=Path(
            f"registry/permission-profiles/{folder}/permission-profile.json"
        ),
        data={
            "name": name,
            "version": "0.1.0",
            "description": description,
            "read": read,
            "write": write,
            "edit": edit,
            "bash": bash,
        },
    )


def diagnostic_codes(
    *sources: RegistrySource,
) -> tuple[str, ...]:
    result = validate_permission_profile_registry(
        sources,
        SCHEMA,
    )
    return tuple(diagnostic.code for diagnostic in result.diagnostics)


def test_valid_profile_is_parsed() -> None:
    result = validate_permission_profile_registry(
        (source(),),
        SCHEMA,
    )

    assert result.is_valid
    assert len(result.profiles) == 1
    assert result.profiles[0].name == "read-only"
    assert result.diagnostics == ()


def test_schema_violation_prevents_parsing() -> None:
    invalid = RegistrySource(
        kind=RegistryKind.PERMISSION_PROFILE,
        source_path=Path(
            "registry/permission-profiles/read-only/permission-profile.json"
        ),
        data={
            "name": "read-only",
            "version": "0.1.0",
            "description": "Read-only access.",
            "read": "yes",
            "write": False,
            "edit": False,
            "bash": "deny",
        },
    )

    result = validate_permission_profile_registry(
        (invalid,),
        SCHEMA,
    )

    assert result.profiles == ()
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        SCHEMA_DIAGNOSTIC,
    )
    assert result.diagnostics[0].location == "$.read"


def test_schema_diagnostics_are_deterministic() -> None:
    invalid = RegistrySource(
        kind=RegistryKind.PERMISSION_PROFILE,
        source_path=Path(
            "registry/permission-profiles/read-only/permission-profile.json"
        ),
        data={
            "name": "read-only",
            "version": "wrong",
            "description": "Read-only access.",
            "read": True,
            "write": False,
            "edit": False,
            "bash": "root",
        },
    )

    result = validate_permission_profile_registry(
        (invalid,),
        SCHEMA,
    )

    assert tuple(diagnostic.location for diagnostic in result.diagnostics) == (
        "$.bash",
        "$.version",
    )


def test_empty_name_is_rejected() -> None:
    assert diagnostic_codes(source(name=" ", folder=" ")) == (NAME_DIAGNOSTIC,)


def test_empty_description_is_rejected() -> None:
    assert diagnostic_codes(source(description=" ")) == (DESCRIPTION_DIAGNOSTIC,)


def test_name_must_match_folder() -> None:
    assert diagnostic_codes(source(name="wrong-name")) == (FOLDER_NAME_DIAGNOSTIC,)


def test_write_requires_read() -> None:
    assert diagnostic_codes(source(read=False, write=True)) == (
        WRITE_REQUIRES_READ_DIAGNOSTIC,
    )


def test_edit_requires_write() -> None:
    assert diagnostic_codes(source(edit=True)) == (EDIT_REQUIRES_WRITE_DIAGNOSTIC,)


def test_limited_bash_requires_read() -> None:
    assert diagnostic_codes(
        source(
            name="limited",
            folder="limited",
            read=False,
            bash="limited",
        )
    ) == (BASH_REQUIRES_READ_DIAGNOSTIC,)


def test_allow_bash_requires_read() -> None:
    assert diagnostic_codes(
        source(
            name="allow",
            folder="allow",
            read=False,
            bash="allow",
        )
    ) == (BASH_REQUIRES_READ_DIAGNOSTIC,)


def test_deny_bash_does_not_require_read() -> None:
    assert (
        diagnostic_codes(
            source(
                name="deny",
                folder="deny",
                read=False,
                bash="deny",
            )
        )
        == ()
    )


def test_duplicate_name_is_rejected() -> None:
    result = validate_permission_profile_registry(
        (
            source(),
            source(folder="duplicate"),
        ),
        SCHEMA,
    )

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        FOLDER_NAME_DIAGNOSTIC,
        DUPLICATE_NAME_DIAGNOSTIC,
    )
    assert "first declared at" in result.diagnostics[1].message
