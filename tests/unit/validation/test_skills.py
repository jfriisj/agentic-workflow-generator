from collections.abc import Callable
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

import agentic_workflow_generator.validation.skills as skills_module
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    read_json_object,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.skills import (
    CONTENT_FILE_DIAGNOSTIC,
    DUPLICATE_CAPABILITY_PROVIDER_DIAGNOSTIC,
    DUPLICATE_NAME_DIAGNOSTIC,
    FOLDER_NAME_DIAGNOSTIC,
    LEGACY_FIELD_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    SELF_REQUIRED_CAPABILITY_DIAGNOSTIC,
    UNKNOWN_AGENT_DIAGNOSTIC,
    UNKNOWN_REQUIRED_CAPABILITY_DIAGNOSTIC,
    SkillDependencyProjectionError,
    SkillReferenceData,
    SkillValidationResult,
    project_agent_names,
    validate_skill_registry,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA = read_json_object(
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "skill.schema.json"
)
REFERENCES = SkillReferenceData(
    agent_names=frozenset({"Implementer", "Reviewer"}),
    existing_content_paths=frozenset(
        {
            "registry/skills/implementation/SKILL.md",
            "registry/skills/review/SKILL.md",
            "registry/skills/duplicate/SKILL.md",
        }
    ),
)


def source(
    *,
    name: str = "implementation",
    folder: str = "implementation",
    version: JsonValue = "1.0.0",
    description: JsonValue = "Implements approved work.",
    provides: JsonValue = None,
    content_path: JsonValue = "SKILL.md",
    context_budget: JsonValue = None,
    requires_capabilities: JsonValue = None,
    recommended_agents: JsonValue = None,
    extra: tuple[str, JsonValue] | None = None,
) -> RegistrySource:
    data: JsonObject = {
        "name": name,
        "version": version,
        "description": description,
        "provides": (["implementation.code"] if provides is None else provides),
        "contentPath": content_path,
        "contextBudget": (
            {"maxTokens": 4000} if context_budget is None else context_budget
        ),
        "requiresCapabilities": (
            [] if requires_capabilities is None else requires_capabilities
        ),
        "recommendedAgents": (
            ["Implementer"] if recommended_agents is None else recommended_agents
        ),
    }

    if extra is not None:
        data[extra[0]] = extra[1]

    return RegistrySource(
        kind=RegistryKind.SKILL,
        source_path=Path(f"registry/skills/{folder}/skill.json"),
        data=data,
    )


def agent_source(
    *,
    name: JsonValue = "Implementer",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.AGENT,
        source_path=Path("registry/agents/Implementer/agent.json"),
        data={"name": name},
    )


def validate(
    *sources: RegistrySource,
    references: SkillReferenceData = REFERENCES,
) -> SkillValidationResult:
    return validate_skill_registry(
        sources,
        SCHEMA,
        references,
    )


def test_valid_skill_is_parsed_and_provider_is_projected() -> None:
    result = validate(source())

    assert result.is_valid
    assert result.diagnostics == ()
    assert len(result.skills) == 1

    skill = result.skills[0]
    assert skill.name == "implementation"
    assert skill.version == "1.0.0"
    assert skill.description == "Implements approved work."
    assert skill.provides == ("implementation.code",)
    assert skill.content_path == "SKILL.md"
    assert skill.context_budget.max_tokens == 4000
    assert skill.requires_capabilities == ()
    assert skill.recommended_agents == ("Implementer",)

    assert len(result.capability_providers) == 1
    provider = result.capability_providers[0]
    assert provider.capability == "implementation.code"
    assert provider.skill_name == "implementation"
    assert provider.source_path == "registry/skills/implementation/skill.json"


def test_agent_names_are_projected() -> None:
    assert project_agent_names(
        (
            agent_source(),
            agent_source(name="Reviewer"),
        )
    ) == frozenset({"Implementer", "Reviewer"})


@pytest.mark.parametrize(
    "invalid_name",
    [
        None,
        42,
        "",
        " ",
    ],
)
def test_agent_name_projection_rejects_invalid_identity(
    invalid_name: JsonValue,
) -> None:
    with pytest.raises(
        SkillDependencyProjectionError,
        match="name must be a non-empty string",
    ):
        project_agent_names((agent_source(name=invalid_name),))


@pytest.mark.parametrize(
    ("mutator", "expected_message"),
    [
        (
            lambda data: data.pop("name"),
            "name must be a non-empty string",
        ),
        (
            lambda data: data.__setitem__("name", 42),
            "name must be a non-empty string",
        ),
        (
            lambda data: data.pop("version"),
            "version must be a non-empty string when present",
        ),
        (
            lambda data: data.pop("recommendedAgents"),
            "recommendedAgents must be a list when present",
        ),
        (
            lambda data: data.pop("requiresCapabilities"),
            "requiresCapabilities must be a list when present",
        ),
        (
            lambda data: data.pop("provides"),
            "provides must be a non-empty list",
        ),
        (
            lambda data: data.__setitem__(
                "provides",
                "invalid",
            ),
            "provides must be a non-empty list",
        ),
        (
            lambda data: data.__setitem__("provides", []),
            "provides must be a non-empty list",
        ),
        (
            lambda data: data.__setitem__(
                "provides",
                [""],
            ),
            "provides[0] must be a non-empty string",
        ),
        (
            lambda data: data.__setitem__(
                "provides",
                ["implementation.code", "implementation.code"],
            ),
            "provides[1] is duplicated",
        ),
        (
            lambda data: data.__setitem__(
                "description",
                42,
            ),
            "description must be a string when present",
        ),
        (
            lambda data: data.__setitem__("version", ""),
            "version must be a non-empty string when present",
        ),
        (
            lambda data: data.__setitem__("version", 42),
            "version must be a non-empty string when present",
        ),
        (
            lambda data: data.__setitem__(
                "recommendedAgents",
                "invalid",
            ),
            "recommendedAgents must be a list when present",
        ),
        (
            lambda data: data.__setitem__(
                "recommendedAgents",
                ["Implementer", "Implementer"],
            ),
            "recommendedAgents[1] is duplicated",
        ),
        (
            lambda data: data.__setitem__(
                "requiresCapabilities",
                "invalid",
            ),
            "requiresCapabilities must be a list when present",
        ),
        (
            lambda data: data.__setitem__(
                "requiresCapabilities",
                ["review.code", "review.code"],
            ),
            "requiresCapabilities[1] is duplicated",
        ),
    ],
)
def test_schema_errors_preserve_public_messages(
    mutator: Callable[[JsonObject], object],
    expected_message: str,
) -> None:
    invalid = source()
    data = invalid.to_json_object()
    mutator(data)

    result = validate(
        RegistrySource(
            kind=RegistryKind.SKILL,
            source_path=invalid.source_path,
            data=data,
        )
    )

    assert result.skills == ()
    assert result.capability_providers == ()
    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC
    assert result.diagnostics[0].message == expected_message


def test_schema_diagnostics_are_deterministic() -> None:
    result = validate(
        source(
            description="",
            provides=[""],
        )
    )

    assert tuple(diagnostic.location for diagnostic in result.diagnostics) == (
        "$.description",
        "$.provides[0]",
    )


@pytest.mark.parametrize(
    "context_budget",
    [
        {"maxTokens": 0},
        "invalid",
    ],
)
def test_generic_schema_violation_is_reported(
    context_budget: JsonValue,
) -> None:
    result = validate(
        source(
            context_budget=context_budget,
        )
    )

    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC
    assert result.diagnostics[0].message.startswith("schema violation:")


def test_all_legacy_fields_are_reported_in_order() -> None:
    invalid = source()
    data = invalid.to_json_object()

    for field in (
        "capability",
        "capabilities",
        "capabilityGroups",
        "documents",
        "inputs",
        "outputs",
        "providedCapabilities",
        "provided_capabilities",
    ):
        data[field] = []

    result = validate(
        RegistrySource(
            kind=RegistryKind.SKILL,
            source_path=invalid.source_path,
            data=data,
        )
    )

    assert result.skills == ()
    assert tuple(diagnostic.location for diagnostic in result.diagnostics) == (
        "capabilities",
        "capability",
        "capabilityGroups",
        "documents",
        "inputs",
        "outputs",
        "providedCapabilities",
        "provided_capabilities",
    )
    assert all(
        diagnostic.code == LEGACY_FIELD_DIAGNOSTIC for diagnostic in result.diagnostics
    )


def test_name_must_match_folder() -> None:
    result = validate(source(name="wrong"))

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        FOLDER_NAME_DIAGNOSTIC,
    )


def test_content_file_must_exist() -> None:
    result = validate(
        source(),
        references=SkillReferenceData(
            agent_names=REFERENCES.agent_names,
            existing_content_paths=frozenset(),
        ),
    )

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        CONTENT_FILE_DIAGNOSTIC,
    )


def test_recommended_agent_must_exist() -> None:
    result = validate(
        source(
            recommended_agents=["DoesNotExist"],
        )
    )

    assert result.diagnostics[0].code == UNKNOWN_AGENT_DIAGNOSTIC
    assert (
        result.diagnostics[0].message == "recommendedAgents entry 'DoesNotExist' "
        "must reference an existing agent"
    )


def test_required_capability_must_exist() -> None:
    result = validate(
        source(
            requires_capabilities=["capability.does.not.exist"],
        )
    )

    assert result.diagnostics[0].code == UNKNOWN_REQUIRED_CAPABILITY_DIAGNOSTIC
    assert (
        result.diagnostics[0].message == "requiresCapabilities entry "
        "'capability.does.not.exist' must reference "
        "an existing capability"
    )


def test_skill_cannot_require_own_capability() -> None:
    result = validate(
        source(
            requires_capabilities=["implementation.code"],
        )
    )

    assert result.diagnostics[0].code == SELF_REQUIRED_CAPABILITY_DIAGNOSTIC
    assert "is provided by the same skill" in (result.diagnostics[0].message)


def test_skill_can_require_capability_from_other_skill() -> None:
    result = validate(
        source(
            requires_capabilities=["review.code"],
        ),
        source(
            name="review",
            folder="review",
            provides=["review.code"],
            recommended_agents=["Reviewer"],
        ),
    )

    assert result.is_valid


def test_duplicate_skill_name_is_rejected() -> None:
    result = validate(
        source(),
        source(
            folder="duplicate",
        ),
    )

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        FOLDER_NAME_DIAGNOSTIC,
        DUPLICATE_NAME_DIAGNOSTIC,
        DUPLICATE_CAPABILITY_PROVIDER_DIAGNOSTIC,
    )
    assert "first declared at" in result.diagnostics[1].message


def test_duplicate_global_capability_is_rejected() -> None:
    result = validate(
        source(),
        source(
            name="review",
            folder="review",
            provides=["implementation.code"],
            recommended_agents=["Reviewer"],
        ),
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == DUPLICATE_CAPABILITY_PROVIDER_DIAGNOSTIC
    assert "is already provided by" in diagnostic.message


def test_capability_providers_are_sorted() -> None:
    result = validate(
        source(
            provides=["z.capability"],
        ),
        source(
            name="review",
            folder="review",
            provides=["a.capability"],
            recommended_agents=["Reviewer"],
        ),
    )

    assert tuple(provider.capability for provider in result.capability_providers) == (
        "a.capability",
        "z.capability",
    )


def test_multiple_semantic_errors_are_deterministic() -> None:
    result = validate(
        source(
            recommended_agents=[
                "MissingOne",
                "MissingTwo",
            ],
            requires_capabilities=[
                "missing.one",
                "implementation.code",
                "missing.two",
            ],
        ),
        references=SkillReferenceData(
            agent_names=frozenset(),
            existing_content_paths=frozenset(),
        ),
    )

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        CONTENT_FILE_DIAGNOSTIC,
        UNKNOWN_AGENT_DIAGNOSTIC,
        UNKNOWN_AGENT_DIAGNOSTIC,
        UNKNOWN_REQUIRED_CAPABILITY_DIAGNOSTIC,
        SELF_REQUIRED_CAPABILITY_DIAGNOSTIC,
        UNKNOWN_REQUIRED_CAPABILITY_DIAGNOSTIC,
    )


def test_skill_schema_wrapper_helpers_delegate() -> None:
    error = ValidationError(
        "invalid capability",
        path=["provides", 0],
    )

    assert skills_module._schema_error_sort_key(
        error
    ) == (
        (
            "provides",
            "0",
        ),
        "invalid capability",
    )
    assert skills_module._schema_error_location(
        error
    ) == "$.provides[0]"
