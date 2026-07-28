import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.profiles import (
    DUPLICATE_NAME_DIAGNOSTIC,
    FILE_NAME_DIAGNOSTIC,
    OBSOLETE_FIELD_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    UNKNOWN_AGENT_DIAGNOSTIC,
    UNKNOWN_CAPABILITY_DIAGNOSTIC,
    UNKNOWN_WORKFLOW_DIAGNOSTIC,
    ProfileDependencyProjectionError,
    ProfileReferenceData,
    project_agent_profile_names,
    project_skill_capabilities,
    project_workflow_names,
    validate_profile_registry,
)


def profile_schema() -> JsonObject:
    return cast(
        JsonObject,
        json.loads(
            Path(".agentic/schemas/registry/profile.schema.json").read_text(
                encoding="utf-8"
            )
        ),
    )


def source(
    path: str = ("registry/profiles/lean-delivery.profile.json"),
    *,
    values: JsonObject | None = None,
    **overrides: JsonValue,
) -> RegistrySource:
    data: JsonObject = {
        "name": "lean-delivery",
        "version": "0.2.0",
        "description": "Advisory delivery defaults.",
        "recommendedWorkflow": "lean-delivery",
        "recommendedAgents": [
            "Orchestrator",
            "Implementer",
        ],
        "recommendedCapabilities": [
            "workflow.route",
            "implementation.code",
        ],
        "recommendedLanguageProfiles": [
            "language-agnostic",
        ],
        "recommendedRuntimeProfiles": [
            "local",
            "ci",
        ],
    }
    if values is not None:
        data.update(values)

    data.update(overrides)

    return RegistrySource(
        kind=RegistryKind.PROFILE,
        source_path=Path(path),
        data=data,
    )


def references() -> ProfileReferenceData:
    return ProfileReferenceData(
        workflows=frozenset(
            {
                "lean-delivery",
            }
        ),
        agent_profiles=frozenset(
            {
                "Orchestrator",
                "Implementer",
            }
        ),
        skill_capabilities=frozenset(
            {
                "workflow.route",
                "implementation.code",
            }
        ),
    )


def identity_source(
    kind: RegistryKind,
    path: str,
    name: JsonValue,
) -> RegistrySource:
    return RegistrySource(
        kind=kind,
        source_path=Path(path),
        data={
            "name": name,
        },
    )


def skill_source(
    provides: JsonValue,
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.SKILL,
        source_path=Path("registry/skills/example/skill.json"),
        data={
            "name": "example",
            "provides": provides,
        },
    )


def test_valid_profile_is_parsed() -> None:
    result = validate_profile_registry(
        (source(),),
        profile_schema(),
        references(),
    )

    assert result.is_valid
    assert not result.diagnostics
    assert result.profiles[0].recommended_workflow == ("lean-delivery")
    assert result.profiles[0].recommended_agents == (
        "Orchestrator",
        "Implementer",
    )


def test_obsolete_workflow_field_is_rejected_before_schema() -> None:
    result = validate_profile_registry(
        (
            source(
                workflow="lean-delivery",
            ),
        ),
        profile_schema(),
        references(),
    )

    assert not result.is_valid
    assert result.profiles == ()
    assert result.diagnostics[0].code == (OBSOLETE_FIELD_DIAGNOSTIC)
    assert result.diagnostics[0].location == "workflow"


def test_obsolete_agents_field_is_rejected_before_schema() -> None:
    result = validate_profile_registry(
        (
            source(
                agents=[
                    "Requirements",
                ],
            ),
        ),
        profile_schema(),
        references(),
    )

    assert not result.is_valid
    assert result.profiles == ()
    assert result.diagnostics[0].code == (OBSOLETE_FIELD_DIAGNOSTIC)
    assert result.diagnostics[0].location == "agents"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {
                "recommendedAgents": [],
            },
            "recommendedAgents must be a non-empty list",
        ),
        (
            {
                "recommendedRuntimeProfiles": "local",
            },
            "recommendedRuntimeProfiles must be a non-empty list",
        ),
        (
            {
                "version": "",
            },
            "version must be a non-empty string",
        ),
        (
            {
                "recommendedCapabilities": [
                    "workflow.route",
                    "workflow.route",
                ],
            },
            ("recommendedCapabilities entry 'workflow.route' is duplicated"),
        ),
    ],
)
def test_schema_failures_are_structured(
    overrides: dict[str, JsonValue],
    message: str,
) -> None:
    result = validate_profile_registry(
        (
            source(
                values=overrides,
            ),
        ),
        profile_schema(),
        references(),
    )

    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC
    assert result.diagnostics[0].message == message


@pytest.mark.parametrize(
    ("profile_source", "code", "location"),
    [
        (
            source(
                path=("registry/profiles/wrong.profile.json"),
            ),
            FILE_NAME_DIAGNOSTIC,
            "name",
        ),
        (
            source(
                recommendedWorkflow="missing",
            ),
            UNKNOWN_WORKFLOW_DIAGNOSTIC,
            "recommendedWorkflow",
        ),
        (
            source(
                recommendedAgents=[
                    "Orchestrator",
                    "Missing",
                ],
            ),
            UNKNOWN_AGENT_DIAGNOSTIC,
            "recommendedAgents",
        ),
        (
            source(
                recommendedCapabilities=[
                    "workflow.route",
                    "missing.capability",
                ],
            ),
            UNKNOWN_CAPABILITY_DIAGNOSTIC,
            "recommendedCapabilities",
        ),
    ],
)
def test_semantic_failures_are_structured(
    profile_source: RegistrySource,
    code: str,
    location: str,
) -> None:
    result = validate_profile_registry(
        (profile_source,),
        profile_schema(),
        references(),
    )

    assert result.diagnostics[0].code == code
    assert result.diagnostics[0].location == location


def test_duplicate_profile_name_is_rejected() -> None:
    result = validate_profile_registry(
        (
            source(),
            source(
                path=("registry/profiles/duplicate.profile.json"),
            ),
        ),
        profile_schema(),
        references(),
    )

    assert result.diagnostics[-1].code == (DUPLICATE_NAME_DIAGNOSTIC)


def test_identity_projections_return_registered_names() -> None:
    workflow = identity_source(
        RegistryKind.WORKFLOW,
        "registry/workflows/lean-delivery.workflow.json",
        "lean-delivery",
    )
    agent = identity_source(
        RegistryKind.AGENT,
        "registry/agents/Implementer/agent.json",
        "Implementer",
    )

    assert project_workflow_names((workflow,)) == frozenset(
        {
            "lean-delivery",
        }
    )
    assert project_agent_profile_names((agent,)) == frozenset(
        {
            "Implementer",
        }
    )


def test_skill_projection_returns_capabilities() -> None:
    assert project_skill_capabilities(
        (
            skill_source(
                [
                    "workflow.route",
                    "implementation.code",
                ]
            ),
        )
    ) == frozenset(
        {
            "workflow.route",
            "implementation.code",
        }
    )


@pytest.mark.parametrize(
    ("projection", "sources", "message"),
    [
        (
            project_workflow_names,
            (
                identity_source(
                    RegistryKind.WORKFLOW,
                    "registry/workflows/invalid.workflow.json",
                    "",
                ),
            ),
            "name must be a non-empty string",
        ),
        (
            project_agent_profile_names,
            (
                identity_source(
                    RegistryKind.AGENT,
                    "registry/agents/first/agent.json",
                    "Duplicate",
                ),
                identity_source(
                    RegistryKind.AGENT,
                    "registry/agents/second/agent.json",
                    "Duplicate",
                ),
            ),
            "identity 'Duplicate' is duplicated",
        ),
        (
            project_skill_capabilities,
            (
                skill_source(
                    [],
                ),
            ),
            "provides must be a non-empty list",
        ),
        (
            project_skill_capabilities,
            (
                skill_source(
                    [
                        "",
                    ],
                ),
            ),
            "provides\\[0\\] must be a non-empty string",
        ),
    ],
)
def test_dependency_projections_fail_fast(
    projection: Callable[
        [tuple[RegistrySource, ...]],
        object,
    ],
    sources: tuple[RegistrySource, ...],
    message: str,
) -> None:
    with pytest.raises(
        ProfileDependencyProjectionError,
        match=message,
    ):
        projection(sources)
