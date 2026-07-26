"""Permission profile parsing and semantic validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.domain.permission_profiles import (
    BashPermission,
    PermissionProfile,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
)
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.identity_support import (
    duplicate_name_diagnostics,
    folder_name_mismatch_diagnostics,
)
from agentic_workflow_generator.validation.schema_support import (
    registry_schema_diagnostics,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_location as shared_schema_error_location,
)

SCHEMA_DIAGNOSTIC = "AWG-PERMISSION-001"
NAME_DIAGNOSTIC = "AWG-PERMISSION-002"
VERSION_DIAGNOSTIC = "AWG-PERMISSION-003"
DESCRIPTION_DIAGNOSTIC = "AWG-PERMISSION-004"
FOLDER_NAME_DIAGNOSTIC = "AWG-PERMISSION-005"
WRITE_REQUIRES_READ_DIAGNOSTIC = "AWG-PERMISSION-006"
EDIT_REQUIRES_WRITE_DIAGNOSTIC = "AWG-PERMISSION-007"
BASH_REQUIRES_READ_DIAGNOSTIC = "AWG-PERMISSION-008"
DUPLICATE_NAME_DIAGNOSTIC = "AWG-PERMISSION-009"


@dataclass(frozen=True, slots=True)
class PermissionProfileValidationResult:
    """Validated profiles and deterministic diagnostics."""

    profiles: tuple[PermissionProfile, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedProfile:
    profile: PermissionProfile
    source_path: Path


def validate_permission_profile_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
) -> PermissionProfileValidationResult:
    """Validate permission-profile sources without side effects."""

    parsed_profiles: list[_ParsedProfile] = []
    diagnostics: list[Diagnostic] = []

    validator = Draft202012Validator(cast(Mapping[str, Any], schema))

    for source in sources:
        schema_diagnostics = _validate_schema(
            source,
            validator,
        )
        diagnostics.extend(schema_diagnostics)

        if schema_diagnostics:
            continue

        parsed, parse_diagnostics = _parse_profile(source)
        diagnostics.extend(parse_diagnostics)

        if parsed is None:
            continue

        parsed_profiles.append(parsed)
        diagnostics.extend(_validate_semantics(parsed))

    diagnostics.extend(_validate_unique_names(parsed_profiles))

    return PermissionProfileValidationResult(
        profiles=tuple(parsed.profile for parsed in parsed_profiles),
        diagnostics=tuple(diagnostics),
    )


def _validate_schema(
    source: RegistrySource,
    validator: Draft202012Validator,
) -> tuple[Diagnostic, ...]:
    return registry_schema_diagnostics(
        source,
        validator,
        SCHEMA_DIAGNOSTIC,
    )


def _parse_profile(
    source: RegistrySource,
) -> tuple[
    _ParsedProfile | None,
    tuple[Diagnostic, ...],
]:
    diagnostics: list[Diagnostic] = []

    name = cast(str, source.data["name"])
    version = cast(str, source.data["version"])
    description = cast(
        str,
        source.data["description"],
    )

    if not name.strip():
        diagnostics.append(
            _field_diagnostic(
                source,
                NAME_DIAGNOSTIC,
                "name",
                "name must be a non-empty string",
            )
        )

    if not version.strip():
        diagnostics.append(
            _field_diagnostic(
                source,
                VERSION_DIAGNOSTIC,
                "version",
                "version must be a non-empty string",
            )
        )

    if not description.strip():
        diagnostics.append(
            _field_diagnostic(
                source,
                DESCRIPTION_DIAGNOSTIC,
                "description",
                ("description must be a non-empty string"),
            )
        )

    if diagnostics:
        return None, tuple(diagnostics)

    return (
        _ParsedProfile(
            profile=PermissionProfile(
                name=name,
                version=version,
                description=description,
                read=cast(bool, source.data["read"]),
                write=cast(bool, source.data["write"]),
                edit=cast(bool, source.data["edit"]),
                bash=BashPermission(cast(str, source.data["bash"])),
            ),
            source_path=source.source_path,
        ),
        (),
    )


def _validate_semantics(
    parsed: _ParsedProfile,
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

    if profile.write and not profile.read:
        diagnostics.append(
            Diagnostic(
                code=WRITE_REQUIRES_READ_DIAGNOSTIC,
                message="write=true requires read=true",
                source_path=source_path.as_posix(),
                location="write",
                related_identities=(profile.name,),
            )
        )

    if profile.edit and not profile.write:
        diagnostics.append(
            Diagnostic(
                code=EDIT_REQUIRES_WRITE_DIAGNOSTIC,
                message="edit=true requires write=true",
                source_path=source_path.as_posix(),
                location="edit",
                related_identities=(profile.name,),
            )
        )

    if (
        profile.bash
        in {
            BashPermission.LIMITED,
            BashPermission.ALLOW,
        }
        and not profile.read
    ):
        diagnostics.append(
            Diagnostic(
                code=BASH_REQUIRES_READ_DIAGNOSTIC,
                message=(f"bash={profile.bash.value} requires read=true"),
                source_path=source_path.as_posix(),
                location="bash",
                related_identities=(profile.name,),
            )
        )

    return tuple(diagnostics)


def _validate_unique_names(
    profiles: list[_ParsedProfile],
) -> tuple[Diagnostic, ...]:
    return duplicate_name_diagnostics(
        (
            (
                parsed.profile.name,
                parsed.source_path,
            )
            for parsed in profiles
        ),
        DUPLICATE_NAME_DIAGNOSTIC,
        'permission profile',
    )


def _field_diagnostic(
    source: RegistrySource,
    code: str,
    field_name: str,
    message: str,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        source_path=source.source_path.as_posix(),
        location=field_name,
    )


def _schema_error_location(
    error: ValidationError,
) -> str:
    return shared_schema_error_location(error)
