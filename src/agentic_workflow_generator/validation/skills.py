"""Skill parsing, capability projection and semantic validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.domain.skills import (
    Skill,
    SkillContextBudget,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.identity_support import (
    duplicate_name_diagnostics,
)
from agentic_workflow_generator.validation.schema_support import (
    custom_registry_schema_diagnostics,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_location as shared_schema_error_location,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_sort_key as shared_schema_error_sort_key,
)

SCHEMA_DIAGNOSTIC = "AWG-SKILL-001"
LEGACY_FIELD_DIAGNOSTIC = "AWG-SKILL-002"
CONTENT_FILE_DIAGNOSTIC = "AWG-SKILL-003"
FOLDER_NAME_DIAGNOSTIC = "AWG-SKILL-004"
DUPLICATE_NAME_DIAGNOSTIC = "AWG-SKILL-005"
DUPLICATE_CAPABILITY_PROVIDER_DIAGNOSTIC = "AWG-SKILL-006"
UNKNOWN_AGENT_DIAGNOSTIC = "AWG-SKILL-007"
UNKNOWN_REQUIRED_CAPABILITY_DIAGNOSTIC = "AWG-SKILL-008"
SELF_REQUIRED_CAPABILITY_DIAGNOSTIC = "AWG-SKILL-009"

LEGACY_SKILL_FIELDS = frozenset(
    {
        "capability",
        "capabilities",
        "capabilityGroups",
        "documents",
        "inputs",
        "outputs",
        "providedCapabilities",
        "provided_capabilities",
    }
)


@dataclass(frozen=True, slots=True)
class SkillReferenceData:
    """Validated external identities and filesystem projection."""

    agent_names: frozenset[str]
    existing_content_paths: frozenset[str]


@dataclass(frozen=True, slots=True)
class SkillCapabilityProvider:
    """Deterministic capability-to-skill projection."""

    capability: str
    skill_name: str
    source_path: str


@dataclass(frozen=True, slots=True)
class SkillValidationResult:
    """Validated skills, providers and deterministic diagnostics."""

    skills: tuple[Skill, ...]
    capability_providers: tuple[SkillCapabilityProvider, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedSkill:
    skill: Skill
    source_path: Path


class SkillDependencyProjectionError(ValueError):
    """Raised when dependency registry data cannot be projected."""


def project_agent_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project agent-profile identities without validating agent semantics."""

    names: set[str] = set()

    for source in sources:
        raw_name = source.data.get("name")

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise SkillDependencyProjectionError(
                f"{source.source_path}: name must be a non-empty string"
            )

        names.add(raw_name)

    return frozenset(names)


def validate_skill_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
    references: SkillReferenceData,
) -> SkillValidationResult:
    """Validate reusable skill definitions without side effects."""

    validator = Draft202012Validator(cast(Mapping[str, Any], schema))
    parsed_skills: list[_ParsedSkill] = []
    diagnostics: list[Diagnostic] = []

    for source in sources:
        legacy_diagnostics = _validate_legacy_fields(source)
        diagnostics.extend(legacy_diagnostics)

        if legacy_diagnostics:
            continue

        schema_diagnostics = _validate_schema(
            source,
            validator,
        )
        diagnostics.extend(schema_diagnostics)

        if schema_diagnostics:
            continue

        parsed_skills.append(_parse_skill(source))

    providers, provider_diagnostics = _project_capability_providers(parsed_skills)
    capability_names = frozenset(provider.capability for provider in providers)

    for parsed in parsed_skills:
        diagnostics.extend(
            _validate_skill_semantics(
                parsed,
                references,
                capability_names,
            )
        )

    diagnostics.extend(_validate_unique_names(parsed_skills))
    diagnostics.extend(provider_diagnostics)

    return SkillValidationResult(
        skills=tuple(parsed.skill for parsed in parsed_skills),
        capability_providers=providers,
        diagnostics=tuple(diagnostics),
    )


def _validate_legacy_fields(
    source: RegistrySource,
) -> tuple[Diagnostic, ...]:
    fields = sorted(LEGACY_SKILL_FIELDS.intersection(source.data))

    return tuple(
        Diagnostic(
            code=LEGACY_FIELD_DIAGNOSTIC,
            message=f"legacy skill field {field!r} is not allowed",
            source_path=source.source_path.as_posix(),
            location=field,
            related_identities=(field,),
        )
        for field in fields
    )


def _validate_schema(
    source: RegistrySource,
    validator: Draft202012Validator,
) -> tuple[Diagnostic, ...]:
    return custom_registry_schema_diagnostics(
        source,
        validator,
        SCHEMA_DIAGNOSTIC,
        _schema_error_message,
    )


def _schema_error_message(
    error: ValidationError,
) -> str:
    path = tuple(error.absolute_path)
    field_name = str(path[0]) if path else _missing_required_field(error)

    if error.validator == "required" and field_name is not None:
        return _required_field_message(field_name)

    if error.validator == "minItems" and field_name == "provides":
        return "provides must be a non-empty list"

    if error.validator == "uniqueItems" and field_name is not None:
        entries = cast(list[object], error.instance)
        duplicate_index = next(
            index for index, entry in enumerate(entries) if entry in entries[:index]
        )
        return f"{field_name}[{duplicate_index}] is duplicated"

    if error.validator == "pattern" and field_name == "version":
        return "version must be a non-empty string when present"

    if error.validator == "minLength" and path:
        if len(path) == 2:
            return f"{field_name}[{path[1]}] must be a non-empty string"

        return f"{field_name} must be a non-empty string"

    if error.validator == "type" and field_name is not None:
        expected = error.validator_value

        if expected == "string":
            if field_name == "description":
                return "description must be a string when present"

            if field_name == "version":
                return "version must be a non-empty string when present"

            return f"{field_name} must be a non-empty string"

        if expected == "array":
            if field_name == "provides":
                return "provides must be a non-empty list"

            return f"{field_name} must be a list when present"

    return f"schema violation: {error.message}"


def _required_field_message(field_name: str) -> str:
    if field_name == "provides":
        return "provides must be a non-empty list"

    if field_name in {
        "recommendedAgents",
        "requiresCapabilities",
    }:
        return f"{field_name} must be a list when present"

    if field_name == "version":
        return "version must be a non-empty string when present"

    return f"{field_name} must be a non-empty string"


def _missing_required_field(
    error: ValidationError,
) -> str:
    instance = cast(dict[str, object], error.instance)
    required = cast(list[str], error.validator_value)

    return next(field for field in required if field not in instance)


def _parse_skill(source: RegistrySource) -> _ParsedSkill:
    context_budget = cast(
        JsonObject,
        source.data["contextBudget"],
    )

    return _ParsedSkill(
        skill=Skill(
            name=cast(str, source.data["name"]),
            version=cast(str, source.data["version"]),
            description=cast(
                str,
                source.data["description"],
            ),
            provides=_string_tuple(source.data["provides"]),
            content_path=cast(
                str,
                source.data["contentPath"],
            ),
            context_budget=SkillContextBudget(
                max_tokens=cast(
                    int,
                    context_budget["maxTokens"],
                )
            ),
            requires_capabilities=_string_tuple(source.data["requiresCapabilities"]),
            recommended_agents=_string_tuple(source.data["recommendedAgents"]),
        ),
        source_path=source.source_path,
    )


def _string_tuple(value: JsonValue) -> tuple[str, ...]:
    return tuple(cast(list[str], value))


def _project_capability_providers(
    parsed_skills: list[_ParsedSkill],
) -> tuple[
    tuple[SkillCapabilityProvider, ...],
    tuple[Diagnostic, ...],
]:
    first_providers: dict[str, _ParsedSkill] = {}
    diagnostics: list[Diagnostic] = []

    for parsed in parsed_skills:
        for capability in parsed.skill.provides:
            first_provider = first_providers.get(capability)

            if first_provider is None:
                first_providers[capability] = parsed
                continue

            diagnostics.append(
                Diagnostic(
                    code=(DUPLICATE_CAPABILITY_PROVIDER_DIAGNOSTIC),
                    message=(
                        f"capability {capability!r} is already "
                        "provided by "
                        f"{first_provider.source_path.as_posix()}"
                    ),
                    source_path=parsed.source_path.as_posix(),
                    location="provides",
                    related_identities=(
                        capability,
                        first_provider.source_path.as_posix(),
                        parsed.source_path.as_posix(),
                    ),
                )
            )

    providers = tuple(
        SkillCapabilityProvider(
            capability=capability,
            skill_name=parsed.skill.name,
            source_path=parsed.source_path.as_posix(),
        )
        for capability, parsed in sorted(first_providers.items())
    )

    return providers, tuple(diagnostics)


def _validate_skill_semantics(
    parsed: _ParsedSkill,
    references: SkillReferenceData,
    capability_names: frozenset[str],
) -> tuple[Diagnostic, ...]:
    skill = parsed.skill
    source_path = parsed.source_path
    diagnostics: list[Diagnostic] = []
    folder_name = source_path.parent.name

    if skill.name != folder_name:
        diagnostics.append(
            Diagnostic(
                code=FOLDER_NAME_DIAGNOSTIC,
                message=(f"name {skill.name!r} does not match folder {folder_name!r}"),
                source_path=source_path.as_posix(),
                location="name",
                related_identities=(
                    skill.name,
                    folder_name,
                ),
            )
        )

    content_path = (source_path.parent / skill.content_path).as_posix()

    if content_path not in references.existing_content_paths:
        diagnostics.append(
            Diagnostic(
                code=CONTENT_FILE_DIAGNOSTIC,
                message=(
                    f"contentPath {skill.content_path!r} "
                    "must reference an existing file"
                ),
                source_path=source_path.as_posix(),
                location="contentPath",
                related_identities=(
                    skill.name,
                    skill.content_path,
                ),
            )
        )

    for agent_name in skill.recommended_agents:
        if agent_name in references.agent_names:
            continue

        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_AGENT_DIAGNOSTIC,
                message=(
                    "recommendedAgents entry "
                    f"{agent_name!r} must reference "
                    "an existing agent"
                ),
                source_path=source_path.as_posix(),
                location="recommendedAgents",
                related_identities=(
                    skill.name,
                    agent_name,
                ),
            )
        )

    own_capabilities = frozenset(skill.provides)

    for capability in skill.requires_capabilities:
        if capability in own_capabilities:
            diagnostics.append(
                Diagnostic(
                    code=SELF_REQUIRED_CAPABILITY_DIAGNOSTIC,
                    message=(
                        "requiresCapabilities entry "
                        f"{capability!r} is provided "
                        "by the same skill"
                    ),
                    source_path=source_path.as_posix(),
                    location="requiresCapabilities",
                    related_identities=(
                        skill.name,
                        capability,
                    ),
                )
            )
            continue

        if capability in capability_names:
            continue

        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_REQUIRED_CAPABILITY_DIAGNOSTIC,
                message=(
                    "requiresCapabilities entry "
                    f"{capability!r} must reference "
                    "an existing capability"
                ),
                source_path=source_path.as_posix(),
                location="requiresCapabilities",
                related_identities=(
                    skill.name,
                    capability,
                ),
            )
        )

    return tuple(diagnostics)


def _validate_unique_names(
    parsed_skills: list[_ParsedSkill],
) -> tuple[Diagnostic, ...]:
    return duplicate_name_diagnostics(
        (
            (
                parsed.skill.name,
                parsed.source_path,
            )
            for parsed in parsed_skills
        ),
        DUPLICATE_NAME_DIAGNOSTIC,
        'skill',
    )


def _schema_error_sort_key(
    error: ValidationError,
) -> tuple[tuple[str, ...], str]:
    return shared_schema_error_sort_key(error)


def _schema_error_location(
    error: ValidationError,
) -> str:
    return shared_schema_error_location(error)
