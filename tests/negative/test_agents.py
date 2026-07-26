from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure import (
    JsonObject,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.agents import (
    LEGACY_FIELD_DIAGNOSTIC,
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
    skill_capabilities=frozenset({"implementation.code"}),
    permission_profiles=frozenset({"implementation"}),
)

BASE: JsonObject = {
    "name": "Implementer",
    "version": "0.2.0",
    "role": "implementation",
    "description": "Implements approved work.",
    "recommendedResponsibilities": [
        "Modify product code",
    ],
    "defaultGuardrails": [
        "Do not self-approve",
    ],
    "recommendedCapabilities": [
        "implementation.code",
    ],
    "defaultPermissionProfile": "implementation",
}


def unknown_capability(data: JsonObject) -> None:
    data["recommendedCapabilities"] = ["does.not.exist"]


def duplicate_capability(data: JsonObject) -> None:
    data["recommendedCapabilities"] = [
        "implementation.code",
        "implementation.code",
    ]


def empty_responsibilities(data: JsonObject) -> None:
    data["recommendedResponsibilities"] = []


def empty_guardrails(data: JsonObject) -> None:
    data["defaultGuardrails"] = []


def empty_version(data: JsonObject) -> None:
    data["version"] = ""


def missing_permission_profile(data: JsonObject) -> None:
    data.pop("defaultPermissionProfile")


def unknown_permission_profile(data: JsonObject) -> None:
    data["defaultPermissionProfile"] = "does-not-exist"


def legacy_produces(data: JsonObject) -> None:
    data["produces"] = ["LegacyArtifact"]


@pytest.mark.parametrize(
    ("mutation", "expected_code", "message"),
    [
        (
            unknown_capability,
            UNKNOWN_CAPABILITY_DIAGNOSTIC,
            "must be provided by a registered skill",
        ),
        (
            duplicate_capability,
            SCHEMA_DIAGNOSTIC,
            "recommendedCapabilities entry",
        ),
        (
            empty_responsibilities,
            SCHEMA_DIAGNOSTIC,
            ("recommendedResponsibilities must be a non-empty list"),
        ),
        (
            empty_guardrails,
            SCHEMA_DIAGNOSTIC,
            ("defaultGuardrails must be a non-empty list"),
        ),
        (
            empty_version,
            SCHEMA_DIAGNOSTIC,
            "version must be a non-empty string",
        ),
        (
            missing_permission_profile,
            SCHEMA_DIAGNOSTIC,
            ("defaultPermissionProfile must be a non-empty string"),
        ),
        (
            unknown_permission_profile,
            UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC,
            ("must reference an existing permission profile"),
        ),
        (
            legacy_produces,
            LEGACY_FIELD_DIAGNOSTIC,
            ("legacy agent field 'produces' is not allowed"),
        ),
    ],
)
def test_invalid_agent_profile_fails_closed(
    mutation: object,
    expected_code: str,
    message: str,
) -> None:
    data = dict(BASE)
    typed_mutation = mutation
    assert callable(typed_mutation)
    typed_mutation(data)

    source = RegistrySource(
        kind=RegistryKind.AGENT,
        source_path=Path("registry/agents/Implementer/agent.json"),
        data=data,
    )

    result = validate_agent_registry(
        (source,),
        SCHEMA,
        REFERENCES,
    )

    assert not result.is_valid
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        expected_code,
    )
    assert message in result.diagnostics[0].message
