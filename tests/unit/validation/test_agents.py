from pathlib import Path

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.agents import (
    DUPLICATE_NAME_DIAGNOSTIC,
    FOLDER_NAME_DIAGNOSTIC,
    OBSOLETE_FIELD_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    UNKNOWN_CAPABILITY_DIAGNOSTIC,
    UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC,
    AgentReferenceData,
    validate_agent_registry,
)

SCHEMA: JsonObject = {
    "type": "object",
    "required": [
        "name",
        "version",
        "role",
        "description",
        "recommendedResponsibilities",
        "defaultGuardrails",
        "recommendedCapabilities",
        "defaultPermissionProfile",
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
        "role": {
            "type": "string",
            "minLength": 1,
        },
        "description": {
            "type": "string",
            "minLength": 1,
        },
        "recommendedResponsibilities": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "minLength": 1,
            },
        },
        "defaultGuardrails": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "minLength": 1,
            },
        },
        "recommendedCapabilities": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "minLength": 1,
            },
        },
        "defaultPermissionProfile": {
            "type": "string",
            "minLength": 1,
        },
    },
}

REFERENCES = AgentReferenceData(
    skill_capabilities=frozenset(
        {
            "implementation.code",
            "implementation.update-tests",
        }
    ),
    permission_profiles=frozenset(
        {
            "implementation",
            "read-only",
        }
    ),
)


def source(
    *,
    name: str = "Implementer",
    folder: str = "Implementer",
    version: str = "0.2.0",
    role: JsonValue = "implementation",
    description: str = "Implements approved work.",
    responsibilities: JsonValue = None,
    guardrails: JsonValue = None,
    capabilities: JsonValue = None,
    permission_profile: JsonValue = "implementation",
    obsolete_field: str | None = None,
) -> RegistrySource:
    data: JsonObject = {
        "name": name,
        "version": version,
        "role": role,
        "description": description,
        "recommendedResponsibilities": (
            ["Modify product code"] if responsibilities is None else responsibilities
        ),
        "defaultGuardrails": (
            ["Do not self-approve"] if guardrails is None else guardrails
        ),
        "recommendedCapabilities": (
            ["implementation.code"] if capabilities is None else capabilities
        ),
        "defaultPermissionProfile": permission_profile,
    }

    if obsolete_field is not None:
        data[obsolete_field] = ["ObsoleteArtifact"]

    return RegistrySource(
        kind=RegistryKind.AGENT,
        source_path=Path(f"registry/agents/{folder}/agent.json"),
        data=data,
    )


def codes(
    *sources: RegistrySource,
) -> tuple[str, ...]:
    result = validate_agent_registry(
        sources,
        SCHEMA,
        REFERENCES,
    )
    return tuple(diagnostic.code for diagnostic in result.diagnostics)


def test_valid_agent_profile_is_parsed() -> None:
    result = validate_agent_registry(
        (source(),),
        SCHEMA,
        REFERENCES,
    )

    assert result.is_valid
    assert result.diagnostics == ()
    assert len(result.profiles) == 1

    profile = result.profiles[0]
    assert profile.name == "Implementer"
    assert profile.version == "0.2.0"
    assert profile.role == "implementation"
    assert profile.description == ("Implements approved work.")
    assert profile.recommended_responsibilities == ("Modify product code",)
    assert profile.default_guardrails == ("Do not self-approve",)
    assert profile.recommended_capabilities == ("implementation.code",)
    assert profile.default_permission_profile == "implementation"


def test_schema_violation_prevents_parsing() -> None:
    result = validate_agent_registry(
        (source(role=42),),
        SCHEMA,
        REFERENCES,
    )

    assert not result.is_valid
    assert result.profiles == ()
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        SCHEMA_DIAGNOSTIC,
    )
    assert result.diagnostics[0].location == "$.role"


def test_schema_diagnostics_are_deterministic() -> None:
    result = validate_agent_registry(
        (
            source(
                description="",
                role="",
            ),
        ),
        SCHEMA,
        REFERENCES,
    )

    assert tuple(diagnostic.location for diagnostic in result.diagnostics) == (
        "$.description",
        "$.role",
    )


def test_obsolete_field_has_specific_diagnostic() -> None:
    result = validate_agent_registry(
        (
            source(
                obsolete_field="produces",
            ),
        ),
        SCHEMA,
        REFERENCES,
    )

    assert result.profiles == ()
    assert codes(source(obsolete_field="produces")) == (OBSOLETE_FIELD_DIAGNOSTIC,)
    assert (
        result.diagnostics[0].message == "obsolete agent field 'produces' is not allowed"
    )


def test_all_obsolete_fields_are_reported_in_order() -> None:
    invalid = source()
    data = invalid.to_json_object()
    data["skills"] = ["obsolete"]
    data["produces"] = ["ObsoleteArtifact"]

    result = validate_agent_registry(
        (
            RegistrySource(
                kind=RegistryKind.AGENT,
                source_path=invalid.source_path,
                data=data,
            ),
        ),
        SCHEMA,
        REFERENCES,
    )

    assert tuple(diagnostic.location for diagnostic in result.diagnostics) == (
        "produces",
        "skills",
    )


def test_name_must_match_folder() -> None:
    assert codes(source(name="Wrong")) == (FOLDER_NAME_DIAGNOSTIC,)


def test_unknown_capability_is_rejected() -> None:
    assert codes(
        source(
            capabilities=["does.not.exist"],
        )
    ) == (UNKNOWN_CAPABILITY_DIAGNOSTIC,)


def test_unknown_permission_profile_is_rejected() -> None:
    assert codes(
        source(
            permission_profile="does-not-exist",
        )
    ) == (UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC,)


def test_duplicate_agent_name_is_rejected() -> None:
    result = validate_agent_registry(
        (
            source(),
            source(folder="Duplicate"),
        ),
        SCHEMA,
        REFERENCES,
    )

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        FOLDER_NAME_DIAGNOSTIC,
        DUPLICATE_NAME_DIAGNOSTIC,
    )
    assert "first declared at" in result.diagnostics[1].message


def test_multiple_reference_errors_are_deterministic() -> None:
    result = validate_agent_registry(
        (
            source(
                capabilities=[
                    "missing.first",
                    "missing.second",
                ],
                permission_profile="missing-profile",
            ),
        ),
        SCHEMA,
        REFERENCES,
    )

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        UNKNOWN_CAPABILITY_DIAGNOSTIC,
        UNKNOWN_CAPABILITY_DIAGNOSTIC,
        UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC,
    )
