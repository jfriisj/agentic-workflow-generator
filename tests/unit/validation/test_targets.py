from pathlib import Path
from typing import cast

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.targets import (
    CROSS_TARGET_OWNERSHIP_DIAGNOSTIC,
    DUPLICATE_NAME_DIAGNOSTIC,
    DUPLICATE_OUTPUT_PATH_DIAGNOSTIC,
    FOLDER_NAME_DIAGNOSTIC,
    MISSING_PERMISSION_MAPPING_DIAGNOSTIC,
    OBSOLETE_FIELD_DIAGNOSTIC,
    OUTPUT_OUTSIDE_OWNERSHIP_DIAGNOSTIC,
    OWNED_PATH_OVERLAP_DIAGNOSTIC,
    UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC,
    UNSAFE_OUTPUT_PATH_DIAGNOSTIC,
    TargetReferenceData,
    TargetValidationResult,
    validate_target_registry,
)

SCHEMA: JsonObject = {
    "type": "object",
    "required": [
        "name",
        "version",
        "description",
        "outputPaths",
        "ownedPaths",
        "permissionMapping",
    ],
    "additionalProperties": False,
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
        },
        "version": {
            "type": "string",
            "minLength": 1,
        },
        "description": {
            "type": "string",
            "minLength": 1,
        },
        "outputPaths": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": {
                "type": "string",
                "minLength": 1,
            },
        },
        "ownedPaths": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "minLength": 1,
            },
        },
        "permissionMapping": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": {
                    "oneOf": [
                        {
                            "type": "string",
                            "minLength": 1,
                        },
                        {
                            "type": "array",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {
                                "type": "string",
                                "minLength": 1,
                            },
                        },
                    ]
                },
            },
        },
    },
}

REFERENCES = TargetReferenceData(
    permission_profiles=frozenset(
        {
            "implementation",
            "read-only",
            "test-runner",
        }
    )
)


def source(
    *,
    name: str = "opencode",
    folder: str = "opencode",
    output_paths: JsonObject | None = None,
    owned_paths: list[str] | None = None,
    permission_mapping: JsonObject | None = None,
    extra: JsonObject | None = None,
) -> RegistrySource:
    owned_path_values: list[JsonValue] = (
        list(owned_paths)
        if owned_paths is not None
        else [
            ".opencode/agents",
            "AGENTS.md",
        ]
    )

    data: JsonObject = {
        "name": name,
        "version": "0.1.0",
        "description": "Target adapter.",
        "outputPaths": (
            output_paths
            if output_paths is not None
            else {
                "agents": ".opencode/agents",
                "instructions": "AGENTS.md",
            }
        ),
        "ownedPaths": owned_path_values,
        "permissionMapping": (
            permission_mapping
            if permission_mapping is not None
            else {
                "implementation": {
                    "bash": "allow",
                },
                "read-only": {
                    "bash": "deny",
                },
                "test-runner": {
                    "bash": "allow",
                },
            }
        ),
    }

    if extra is not None:
        data.update(extra)

    return RegistrySource(
        kind=RegistryKind.TARGET,
        source_path=Path(
            f"registry/targets/{folder}/adapter.json"
        ),
        data=data,
    )


def result(
    *sources: RegistrySource,
) -> TargetValidationResult:
    return validate_target_registry(
        sources,
        SCHEMA,
        REFERENCES,
    )


def diagnostic_codes(
    *sources: RegistrySource,
) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in result(*sources).diagnostics
    )


def test_valid_target_is_parsed_to_immutable_values() -> None:
    validation = result(source())

    assert validation.is_valid
    assert validation.diagnostics == ()
    assert validation.adapters[0].name == "opencode"
    assert validation.adapters[0].output_paths[0].name == (
        "agents"
    )
    assert (
        validation.adapters[0]
        .permission_mappings[0]
        .settings[0]
        .value
        == "allow"
    )


def test_obsolete_field_is_rejected_before_schema() -> None:
    validation = result(
        source(
            extra={
                "supportedFeatures": cast(
                    JsonValue,
                    [],
                )
            }
        )
    )

    assert diagnostic_codes(
        source(
            extra={
                "supportedFeatures": cast(
                    JsonValue,
                    [],
                )
            }
        )
    ) == (OBSOLETE_FIELD_DIAGNOSTIC,)
    assert validation.adapters == ()


def test_name_must_match_folder() -> None:
    assert diagnostic_codes(
        source(name="different")
    ) == (FOLDER_NAME_DIAGNOSTIC,)


def test_duplicate_target_name_is_rejected() -> None:
    codes = diagnostic_codes(
        source(),
        source(folder="duplicate"),
    )

    assert FOLDER_NAME_DIAGNOSTIC in codes
    assert DUPLICATE_NAME_DIAGNOSTIC in codes


def test_output_paths_must_be_safe() -> None:
    assert diagnostic_codes(
        source(
            output_paths={
                "agents": "../outside",
            },
            owned_paths=["safe"],
        )
    ) == (UNSAFE_OUTPUT_PATH_DIAGNOSTIC,)


def test_duplicate_output_paths_are_rejected() -> None:
    assert diagnostic_codes(
        source(
            output_paths={
                "agents": ".opencode/agents",
                "skills": ".opencode/agents",
            },
            owned_paths=[".opencode/agents"],
        )
    ) == (DUPLICATE_OUTPUT_PATH_DIAGNOSTIC,)


def test_owned_paths_must_not_overlap() -> None:
    assert diagnostic_codes(
        source(
            output_paths={
                "agents": ".opencode/agents",
            },
            owned_paths=[
                ".opencode",
                ".opencode/agents",
            ],
        )
    ) == (OWNED_PATH_OVERLAP_DIAGNOSTIC,)


def test_output_path_must_be_owned() -> None:
    assert diagnostic_codes(
        source(
            output_paths={
                "agents": ".opencode/agents",
            },
            owned_paths=["different"],
        )
    ) == (OUTPUT_OUTSIDE_OWNERSHIP_DIAGNOSTIC,)


def test_cross_target_owned_paths_must_not_overlap() -> None:
    second = source(
        name="second",
        folder="second",
        output_paths={
            "agents": ".opencode/agents/nested",
        },
        owned_paths=[
            ".opencode/agents/nested",
        ],
    )

    codes = diagnostic_codes(
        source(),
        second,
    )

    assert CROSS_TARGET_OWNERSHIP_DIAGNOSTIC in codes


def test_unknown_permission_mapping_is_rejected() -> None:
    mapping: JsonObject = {
        "implementation": {
            "bash": "allow",
        },
        "read-only": {
            "bash": "deny",
        },
        "test-runner": {
            "bash": "allow",
        },
        "unknown": {
            "bash": "allow",
        },
    }

    assert diagnostic_codes(
        source(permission_mapping=mapping)
    ) == (UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC,)


def test_missing_permission_mapping_is_rejected() -> None:
    mapping: JsonObject = {
        "implementation": {
            "bash": "allow",
        },
        "read-only": {
            "bash": "deny",
        },
    }

    assert diagnostic_codes(
        source(permission_mapping=mapping)
    ) == (MISSING_PERMISSION_MAPPING_DIAGNOSTIC,)
