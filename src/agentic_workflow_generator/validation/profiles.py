"""Advisory project-profile parsing and semantic validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.domain.profiles import Profile
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.identity_support import (
    duplicate_name_diagnostics,
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

SCHEMA_DIAGNOSTIC = "AWG-PROFILE-001"
OBSOLETE_FIELD_DIAGNOSTIC = "AWG-PROFILE-002"
FILE_NAME_DIAGNOSTIC = "AWG-PROFILE-003"
DUPLICATE_NAME_DIAGNOSTIC = "AWG-PROFILE-004"
UNKNOWN_WORKFLOW_DIAGNOSTIC = "AWG-PROFILE-005"
UNKNOWN_AGENT_DIAGNOSTIC = "AWG-PROFILE-006"
UNKNOWN_CAPABILITY_DIAGNOSTIC = "AWG-PROFILE-007"

OBSOLETE_PROFILE_FIELDS = frozenset(
    {
        "agents",
        "artifacts",
        "capabilities",
        "constraints",
        "defaults",
        "recommendedSkills",
        "recommendedTargets",
        "recommendedWorkflows",
        "skills",
        "targets",
        "workflow",
        "workflows",
    }
)

_LIST_FIELDS = frozenset(
    {
        "recommendedAgents",
        "recommendedCapabilities",
        "recommendedLanguageProfiles",
        "recommendedRuntimeProfiles",
    }
)


@dataclass(frozen=True, slots=True)
class ProfileReferenceData:
    """Validated external identities needed by advisory profiles."""

    workflows: frozenset[str]
    agent_profiles: frozenset[str]
    skill_capabilities: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProfileValidationResult:
    """Validated profiles and deterministic diagnostics."""

    profiles: tuple[Profile, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedProfile:
    profile: Profile
    source_path: Path


class ProfileDependencyProjectionError(ValueError):
    """Raised when dependency registry data cannot be projected."""


def project_workflow_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project workflow identities without validating workflow semantics."""

    return _project_identity_names(sources)


def project_agent_profile_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project agent-profile identities without treating them as authority."""

    return _project_identity_names(sources)


def project_skill_capabilities(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project capability identities without validating skill semantics."""

    capabilities: set[str] = set()

    for source in sources:
        raw_provides = source.data.get("provides")

        if not isinstance(raw_provides, list) or not raw_provides:
            raise ProfileDependencyProjectionError(
                f"{source.source_path}: provides must be a non-empty list"
            )

        for index, raw_capability in enumerate(raw_provides):
            if not isinstance(raw_capability, str) or not raw_capability.strip():
                raise ProfileDependencyProjectionError(
                    f"{source.source_path}: provides[{index}] "
                    "must be a non-empty string"
                )

            capabilities.add(raw_capability)

    return frozenset(capabilities)


def validate_profile_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
    references: ProfileReferenceData,
) -> ProfileValidationResult:
    """Validate advisory project profiles without side effects."""

    validator = Draft202012Validator(
        cast(Mapping[str, Any], schema)
    )
    parsed_profiles, diagnostics = validate_and_parse_sources(
        sources,
        validator,
        _validate_obsolete_fields,
        _validate_schema,
        _parse_profile,
        lambda parsed: _validate_profile_semantics(parsed, references),
    )

    diagnostics.extend(_validate_unique_names(parsed_profiles))

    return ProfileValidationResult(
        profiles=tuple(parsed.profile for parsed in parsed_profiles),
        diagnostics=tuple(diagnostics),
    )


def _project_identity_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    names: set[str] = set()

    for source in sources:
        raw_name = source.data.get("name")

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ProfileDependencyProjectionError(
                f"{source.source_path}: name must be a non-empty string"
            )

        if raw_name in names:
            raise ProfileDependencyProjectionError(
                f"{source.source_path}: identity {raw_name!r} is duplicated"
            )

        names.add(raw_name)

    return frozenset(names)


def _validate_obsolete_fields(
    source: RegistrySource,
) -> tuple[Diagnostic, ...]:
    fields = sorted(OBSOLETE_PROFILE_FIELDS.intersection(source.data))

    return tuple(
        Diagnostic(
            code=OBSOLETE_FIELD_DIAGNOSTIC,
            message=f"obsolete profile field {field!r} is not allowed",
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
    return Diagnostic(
        code=SCHEMA_DIAGNOSTIC,
        message=_schema_error_message(error),
        source_path=source.source_path.as_posix(),
        location=_schema_error_location(error),
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


def _parse_profile(source: RegistrySource) -> _ParsedProfile:
    return _ParsedProfile(
        profile=Profile(
            name=cast(str, source.data["name"]),
            version=cast(str, source.data["version"]),
            description=cast(str, source.data["description"]),
            recommended_workflow=cast(
                str,
                source.data["recommendedWorkflow"],
            ),
            recommended_agents=_string_tuple(source.data["recommendedAgents"]),
            recommended_capabilities=_string_tuple(
                source.data["recommendedCapabilities"]
            ),
            recommended_language_profiles=_string_tuple(
                source.data["recommendedLanguageProfiles"]
            ),
            recommended_runtime_profiles=_string_tuple(
                source.data["recommendedRuntimeProfiles"]
            ),
        ),
        source_path=source.source_path,
    )


def _string_tuple(value: JsonValue) -> tuple[str, ...]:
    return tuple(cast(list[str], value))


def _validate_profile_semantics(
    parsed: _ParsedProfile,
    references: ProfileReferenceData,
) -> tuple[Diagnostic, ...]:
    profile = parsed.profile
    path = parsed.source_path
    diagnostics: list[Diagnostic] = []
    expected_name = path.name.removesuffix(".profile.json")

    if profile.name != expected_name:
        diagnostics.append(
            Diagnostic(
                code=FILE_NAME_DIAGNOSTIC,
                message=(
                    f"profile name {profile.name!r} does not match "
                    f"file name {expected_name!r}"
                ),
                source_path=path.as_posix(),
                location="name",
                related_identities=(
                    profile.name,
                    expected_name,
                ),
            )
        )

    if profile.recommended_workflow not in references.workflows:
        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_WORKFLOW_DIAGNOSTIC,
                message=(
                    "recommendedWorkflow "
                    f"{profile.recommended_workflow!r} must reference "
                    "an existing workflow"
                ),
                source_path=path.as_posix(),
                location="recommendedWorkflow",
                related_identities=(
                    profile.name,
                    profile.recommended_workflow,
                ),
            )
        )

    for agent_name in profile.recommended_agents:
        if agent_name in references.agent_profiles:
            continue

        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_AGENT_DIAGNOSTIC,
                message=(
                    "recommendedAgents entry "
                    f"{agent_name!r} must reference an existing "
                    "agent profile"
                ),
                source_path=path.as_posix(),
                location="recommendedAgents",
                related_identities=(
                    profile.name,
                    agent_name,
                ),
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
                    f"{capability!r} must be provided by a "
                    "registered skill"
                ),
                source_path=path.as_posix(),
                location="recommendedCapabilities",
                related_identities=(
                    profile.name,
                    capability,
                ),
            )
        )

    return tuple(diagnostics)


def _validate_unique_names(
    parsed_profiles: list[_ParsedProfile],
) -> tuple[Diagnostic, ...]:
    return duplicate_name_diagnostics(
        (
            (
                parsed.profile.name,
                parsed.source_path,
            )
            for parsed in parsed_profiles
        ),
        DUPLICATE_NAME_DIAGNOSTIC,
        'profile',
    )


def _schema_error_sort_key(
    error: ValidationError,
) -> tuple[tuple[str, ...], str]:
    return shared_schema_error_sort_key(error)


def _schema_error_location(
    error: ValidationError,
) -> str:
    return shared_schema_error_location(error)
