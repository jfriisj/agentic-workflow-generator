"""Agent-profile parsing and semantic validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.domain.agents import AgentProfile
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.identity_support import (
    duplicate_name_diagnostics,
    folder_name_mismatch_diagnostics,
)
from agentic_workflow_generator.validation.pipeline_support import (
    validate_and_parse_sources,
)
from agentic_workflow_generator.validation.schema_support import (
    field_schema_error_message,
    first_duplicate_string,
    missing_required_field,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_location as shared_schema_error_location,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_sort_key as shared_schema_error_sort_key,
)

SCHEMA_DIAGNOSTIC = "AWG-AGENT-001"
LEGACY_FIELD_DIAGNOSTIC = "AWG-AGENT-002"
FOLDER_NAME_DIAGNOSTIC = "AWG-AGENT-003"
DUPLICATE_NAME_DIAGNOSTIC = "AWG-AGENT-004"
UNKNOWN_CAPABILITY_DIAGNOSTIC = "AWG-AGENT-005"
UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC = "AWG-AGENT-006"


LEGACY_AGENT_FIELDS = frozenset(
    {
        "agents",
        "capabilities",
        "handoffs",
        "model",
        "mustNot",
        "permissionProfile",
        "produces",
        "requiredArtifacts",
        "responsibilities",
        "skills",
        "target",
        "targets",
    }
)


_LIST_FIELDS = frozenset(
    {
        "recommendedResponsibilities",
        "defaultGuardrails",
        "recommendedCapabilities",
    }
)

@dataclass(frozen=True, slots=True)
class AgentReferenceData:
    """Validated external identities needed by agent profiles."""

    skill_capabilities: frozenset[str]
    permission_profiles: frozenset[str]


@dataclass(frozen=True, slots=True)
class AgentValidationResult:
    """Validated profiles and deterministic diagnostics."""

    profiles: tuple[AgentProfile, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedAgent:
    profile: AgentProfile
    source_path: Path


class AgentDependencyProjectionError(ValueError):
    """Raised when dependency registry data cannot be projected."""


def project_skill_capabilities(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project capability identities without validating skill semantics."""

    capabilities: set[str] = set()

    for source in sources:
        raw_provides = source.data.get("provides")

        if not isinstance(raw_provides, list) or not raw_provides:
            raise AgentDependencyProjectionError(
                f"{source.source_path}: provides must be a non-empty list"
            )

        for index, raw_capability in enumerate(raw_provides):
            if not isinstance(raw_capability, str) or not raw_capability.strip():
                raise AgentDependencyProjectionError(
                    f"{source.source_path}: provides[{index}] "
                    "must be a non-empty string"
                )

            capabilities.add(raw_capability)

    return frozenset(capabilities)


def project_permission_profile_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project permission-profile identities only."""

    names: set[str] = set()

    for source in sources:
        raw_name = source.data.get("name")

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise AgentDependencyProjectionError(
                f"{source.source_path}: name must be a non-empty string"
            )

        names.add(raw_name)

    return frozenset(names)


def validate_agent_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
    references: AgentReferenceData,
) -> AgentValidationResult:
    """Validate advisory agent profiles without side effects."""

    validator = Draft202012Validator(
        cast(Mapping[str, Any], schema)
    )
    parsed_agents, diagnostics = validate_and_parse_sources(
        sources,
        validator,
        _validate_legacy_fields,
        _validate_schema,
        _parse_agent,
        lambda parsed: _validate_agent_semantics(parsed, references),
    )

    diagnostics.extend(_validate_unique_names(parsed_agents))

    return AgentValidationResult(
        profiles=tuple(parsed.profile for parsed in parsed_agents),
        diagnostics=tuple(diagnostics),
    )


def _validate_legacy_fields(
    source: RegistrySource,
) -> tuple[Diagnostic, ...]:
    fields = sorted(LEGACY_AGENT_FIELDS.intersection(source.data))

    return tuple(
        Diagnostic(
            code=LEGACY_FIELD_DIAGNOSTIC,
            message=(f"legacy agent field {field!r} is not allowed"),
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
    errors = sorted(
        validator.iter_errors(source.to_json_object()),
        key=_schema_error_sort_key,
    )

    return tuple(_schema_diagnostic(source, error) for error in errors)


def _schema_diagnostic(
    source: RegistrySource,
    error: ValidationError,
) -> Diagnostic:
    location = _schema_error_location(error)
    message = _schema_error_message(error)

    return Diagnostic(
        code=SCHEMA_DIAGNOSTIC,
        message=message,
        source_path=source.source_path.as_posix(),
        location=location,
    )


def _schema_error_message(
    error: ValidationError,
) -> str:
    return field_schema_error_message(
        error,
        _LIST_FIELDS,
    )


def _missing_required_field(
    error: ValidationError,
) -> str | None:
    return missing_required_field(error)


def _first_duplicate(
    instance: object,
) -> str | None:
    return first_duplicate_string(instance)


def _parse_agent(source: RegistrySource) -> _ParsedAgent:
    return _ParsedAgent(
        profile=AgentProfile(
            name=cast(str, source.data["name"]),
            version=cast(str, source.data["version"]),
            role=cast(str, source.data["role"]),
            description=cast(
                str,
                source.data["description"],
            ),
            recommended_responsibilities=_string_tuple(
                source.data["recommendedResponsibilities"]
            ),
            default_guardrails=_string_tuple(source.data["defaultGuardrails"]),
            recommended_capabilities=_string_tuple(
                source.data["recommendedCapabilities"]
            ),
            default_permission_profile=cast(
                str,
                source.data["defaultPermissionProfile"],
            ),
        ),
        source_path=source.source_path,
    )


def _string_tuple(value: JsonValue) -> tuple[str, ...]:
    return tuple(cast(list[str], value))


def _validate_agent_semantics(
    parsed: _ParsedAgent,
    references: AgentReferenceData,
) -> tuple[Diagnostic, ...]:
    profile = parsed.profile
    source_path = parsed.source_path
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(
        folder_name_mismatch_diagnostics(
            profile.name,
            source_path,
            FOLDER_NAME_DIAGNOSTIC,
        )
    )

    for capability in profile.recommended_capabilities:
        if capability in references.skill_capabilities:
            continue

        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_CAPABILITY_DIAGNOSTIC,
                message=(
                    "recommendedCapabilities entry "
                    f"{capability!r} must be provided "
                    "by a registered skill"
                ),
                source_path=source_path.as_posix(),
                location="recommendedCapabilities",
                related_identities=(
                    profile.name,
                    capability,
                ),
            )
        )

    permission_profile = profile.default_permission_profile

    if permission_profile not in references.permission_profiles:
        diagnostics.append(
            Diagnostic(
                code=(UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC),
                message=(
                    "defaultPermissionProfile "
                    f"{permission_profile!r} must "
                    "reference an existing permission "
                    "profile"
                ),
                source_path=source_path.as_posix(),
                location="defaultPermissionProfile",
                related_identities=(
                    profile.name,
                    permission_profile,
                ),
            )
        )

    return tuple(diagnostics)


def _validate_unique_names(
    parsed_agents: list[_ParsedAgent],
) -> tuple[Diagnostic, ...]:
    return duplicate_name_diagnostics(
        (
            (
                parsed.profile.name,
                parsed.source_path,
            )
            for parsed in parsed_agents
        ),
        DUPLICATE_NAME_DIAGNOSTIC,
        'agent',
    )


def _schema_error_sort_key(
    error: ValidationError,
) -> tuple[tuple[str, ...], str]:
    return shared_schema_error_sort_key(error)


def _schema_error_location(
    error: ValidationError,
) -> str:
    return shared_schema_error_location(error)
