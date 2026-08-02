"""Artifact-contract parsing, projection and semantic validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.domain.artifacts import (
    ArtifactContract,
    ArtifactProvenanceContract,
    ArtifactStatus,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    serialize_json,
)
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.schema_support import (
    custom_registry_schema_diagnostics,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_location as shared_schema_error_location,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_sort_key as shared_schema_error_sort_key,
)

SCHEMA_DIAGNOSTIC = "AWG-ARTIFACT-001"
OBSOLETE_FIELD_DIAGNOSTIC = "AWG-ARTIFACT-002"
FOLDER_TYPE_DIAGNOSTIC = "AWG-ARTIFACT-003"
DUPLICATE_TYPE_DIAGNOSTIC = "AWG-ARTIFACT-004"
STATUS_HEADING_DIAGNOSTIC = "AWG-ARTIFACT-005"
INVALID_STATUS_PATTERN_DIAGNOSTIC = "AWG-ARTIFACT-006"
STATUS_PATTERN_MISMATCH_DIAGNOSTIC = "AWG-ARTIFACT-007"
MISSING_GENERATED_SCHEMA_DIAGNOSTIC = "AWG-ARTIFACT-008"
ORPHAN_GENERATED_SCHEMA_DIAGNOSTIC = "AWG-ARTIFACT-009"
GENERATED_SCHEMA_DRIFT_DIAGNOSTIC = "AWG-ARTIFACT-010"
PROVENANCE_HEADING_DIAGNOSTIC = "AWG-ARTIFACT-011"

OBSOLETE_ARTIFACT_FIELDS = frozenset(
    {
        "binding",
        "producedBy",
        "required",
    }
)


@dataclass(frozen=True, slots=True)
class ArtifactSchemaSnapshot:
    """Immutable canonical snapshot of one generated artifact schema."""

    source_path: str
    canonical_json: str


@dataclass(frozen=True, slots=True)
class ArtifactSchemaProjection:
    """Deterministic expected generated schema for one contract."""

    artifact_type: str
    contract_path: str
    schema_path: str
    canonical_json: str


@dataclass(frozen=True, slots=True)
class ArtifactValidationResult:
    """Validated contracts, schema projections and diagnostics."""

    contracts: tuple[ArtifactContract, ...]
    schema_projections: tuple[ArtifactSchemaProjection, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedArtifact:
    contract: ArtifactContract
    source_path: Path


def validate_artifact_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
    schema_snapshots: tuple[ArtifactSchemaSnapshot, ...],
) -> ArtifactValidationResult:
    """Validate reusable artifact contracts without side effects."""

    validator = Draft202012Validator(cast(Mapping[str, Any], schema))
    parsed_artifacts: list[_ParsedArtifact] = []
    diagnostics: list[Diagnostic] = []

    for source in sources:
        obsolete_diagnostics = _validate_obsolete_fields(source)
        diagnostics.extend(obsolete_diagnostics)

        if obsolete_diagnostics:
            continue

        schema_diagnostics = custom_registry_schema_diagnostics(
            source,
            validator,
            SCHEMA_DIAGNOSTIC,
            _schema_error_message,
        )
        diagnostics.extend(schema_diagnostics)

        if schema_diagnostics:
            continue

        parsed = _parse_artifact(source)
        parsed_artifacts.append(parsed)
        diagnostics.extend(_validate_artifact_semantics(parsed))

    diagnostics.extend(_validate_unique_types(parsed_artifacts))

    projections = tuple(
        _project_generated_schema(parsed) for parsed in parsed_artifacts
    )
    diagnostics.extend(
        _validate_generated_schema_parity(
            projections,
            schema_snapshots,
        )
    )

    return ArtifactValidationResult(
        contracts=tuple(parsed.contract for parsed in parsed_artifacts),
        schema_projections=projections,
        diagnostics=tuple(diagnostics),
    )


def _validate_obsolete_fields(
    source: RegistrySource,
) -> tuple[Diagnostic, ...]:
    fields = sorted(OBSOLETE_ARTIFACT_FIELDS.intersection(source.data))

    return tuple(
        Diagnostic(
            code=OBSOLETE_FIELD_DIAGNOSTIC,
            message=(f"obsolete artifact field {field!r} is not allowed"),
            source_path=source.source_path.as_posix(),
            location=field,
            related_identities=(field,),
        )
        for field in fields
    )


def _schema_error_message(
    error: ValidationError,
) -> str:
    path = tuple(error.absolute_path)
    field_name = _schema_field_name(error, path)

    if error.validator == "required":
        return _required_field_message(field_name)

    if error.validator == "minItems":
        return f"{field_name} must be a non-empty list"

    if error.validator == "uniqueItems":
        duplicate_index = _first_duplicate_index(error.instance)
        return f"{field_name}[{duplicate_index}] is duplicated"

    if error.validator == "minLength":
        return f"{field_name} must be a non-empty string"

    if error.validator == "type":
        if error.validator_value == "array":
            return f"{field_name} must be a non-empty list"

        if error.validator_value == "object":
            return f"{field_name} must be an object"

        return f"{field_name} must be a non-empty string"

    if error.validator == "pattern" and field_name == "version":
        return "version must be a semantic version"

    if error.validator == "pattern" and field_name == "pathPattern":
        return "pathPattern must be a safe relative path"

    if error.validator == "const" and field_name == "status.heading":
        return "status.heading must be exactly '## Status'"

    if error.validator == "const" and field_name == "provenance.heading":
        return "provenance.heading must be exactly '## Provenance'"

    if (
        error.validator == "const"
        and field_name == "provenance.requiredIdentities"
    ):
        return (
            "provenance.requiredIdentities must match the canonical "
            "identity set"
        )

    return f"schema violation: {error.message}"


def _schema_field_name(
    error: ValidationError,
    path: tuple[object, ...],
) -> str:
    if error.validator == "required":
        missing = _missing_required_field(error)

        if path:
            return ".".join(
                (
                    *(str(component) for component in path),
                    missing,
                )
            )

        return missing

    return ".".join(str(component) for component in path)


def _required_field_message(
    field_name: str,
) -> str:
    if field_name in {
        "allowedStatuses",
        "requiredHeadings",
        "provenance.requiredIdentities",
    }:
        return f"{field_name} must be a non-empty list"

    if field_name in {"status", "provenance"}:
        return f"{field_name} must be an object"

    return f"{field_name} must be a non-empty string"


def _missing_required_field(
    error: ValidationError,
) -> str:
    instance = cast(dict[str, object], error.instance)
    required = cast(list[str], error.validator_value)

    return next(field for field in required if field not in instance)


def _first_duplicate_index(
    instance: object,
) -> int:
    entries = cast(list[object], instance)

    return next(
        index for index, entry in enumerate(entries) if entry in entries[:index]
    )


def _parse_artifact(
    source: RegistrySource,
) -> _ParsedArtifact:
    status = cast(
        JsonObject,
        source.data["status"],
    )
    provenance = cast(
        JsonObject,
        source.data["provenance"],
    )

    return _ParsedArtifact(
        contract=ArtifactContract(
            type=cast(str, source.data["type"]),
            version=cast(str, source.data["version"]),
            description=cast(
                str,
                source.data["description"],
            ),
            path_pattern=cast(
                str,
                source.data["pathPattern"],
            ),
            status=ArtifactStatus(
                heading=cast(str, status["heading"]),
                pattern=cast(str, status["pattern"]),
            ),
            provenance=ArtifactProvenanceContract(
                heading=cast(str, provenance["heading"]),
                required_identities=_string_tuple(
                    provenance["requiredIdentities"]
                ),
            ),
            allowed_statuses=_string_tuple(source.data["allowedStatuses"]),
            required_headings=_string_tuple(source.data["requiredHeadings"]),
        ),
        source_path=source.source_path,
    )


def _string_tuple(
    value: JsonValue,
) -> tuple[str, ...]:
    return tuple(cast(list[str], value))


def _validate_artifact_semantics(
    parsed: _ParsedArtifact,
) -> tuple[Diagnostic, ...]:
    contract = parsed.contract
    source_path = parsed.source_path
    diagnostics: list[Diagnostic] = []
    folder_name = source_path.parent.name

    if contract.type != folder_name:
        diagnostics.append(
            Diagnostic(
                code=FOLDER_TYPE_DIAGNOSTIC,
                message=(
                    f"type {contract.type!r} does not match folder {folder_name!r}"
                ),
                source_path=source_path.as_posix(),
                location="type",
                related_identities=(
                    contract.type,
                    folder_name,
                ),
            )
        )

    if contract.status.heading not in contract.required_headings:
        diagnostics.append(
            Diagnostic(
                code=STATUS_HEADING_DIAGNOSTIC,
                message=("status.heading must be present in requiredHeadings"),
                source_path=source_path.as_posix(),
                location="status.heading",
                related_identities=(
                    contract.type,
                    contract.status.heading,
                ),
            )
        )

    if contract.provenance.heading not in contract.required_headings:
        diagnostics.append(
            Diagnostic(
                code=PROVENANCE_HEADING_DIAGNOSTIC,
                message=(
                    "provenance.heading must be present in requiredHeadings"
                ),
                source_path=source_path.as_posix(),
                location="provenance.heading",
                related_identities=(
                    contract.type,
                    contract.provenance.heading,
                ),
            )
        )

    try:
        status_pattern = re.compile(contract.status.pattern)
    except re.error as exc:
        diagnostics.append(
            Diagnostic(
                code=INVALID_STATUS_PATTERN_DIAGNOSTIC,
                message=(f"status.pattern must be a valid regular expression: {exc}"),
                source_path=source_path.as_posix(),
                location="status.pattern",
                related_identities=(contract.type,),
            )
        )
        return tuple(diagnostics)

    unmatched_statuses = tuple(
        status
        for status in contract.allowed_statuses
        if status_pattern.fullmatch(status) is None
    )

    if unmatched_statuses:
        diagnostics.append(
            Diagnostic(
                code=STATUS_PATTERN_MISMATCH_DIAGNOSTIC,
                message=("status.pattern must match every allowed status"),
                source_path=source_path.as_posix(),
                location="status.pattern",
                related_identities=(
                    contract.type,
                    *unmatched_statuses,
                ),
            )
        )

    return tuple(diagnostics)


def _validate_unique_types(
    parsed_artifacts: list[_ParsedArtifact],
) -> tuple[Diagnostic, ...]:
    seen: dict[str, Path] = {}
    diagnostics: list[Diagnostic] = []

    for parsed in parsed_artifacts:
        artifact_type = parsed.contract.type
        first_path = seen.get(artifact_type)

        if first_path is None:
            seen[artifact_type] = parsed.source_path
            continue

        diagnostics.append(
            Diagnostic(
                code=DUPLICATE_TYPE_DIAGNOSTIC,
                message=(
                    f"artifact type {artifact_type!r} "
                    "is duplicated; first declared at "
                    f"{first_path.as_posix()}"
                ),
                source_path=(parsed.source_path.as_posix()),
                location="type",
                related_identities=(artifact_type,),
            )
        )

    return tuple(diagnostics)


def _project_generated_schema(
    parsed: _ParsedArtifact,
) -> ArtifactSchemaProjection:
    contract = parsed.contract
    schema_path = parsed.source_path.parent / "artifact.schema.json"

    return ArtifactSchemaProjection(
        artifact_type=contract.type,
        contract_path=parsed.source_path.as_posix(),
        schema_path=schema_path.as_posix(),
        canonical_json=serialize_json(_expected_schema(contract)),
    )


def _expected_schema(
    contract: ArtifactContract,
) -> JsonObject:
    required_fields: list[JsonValue] = [
        "type",
        "version",
        "description",
        "pathPattern",
        "status",
        "provenance",
        "allowedStatuses",
        "requiredHeadings",
    ]

    properties: JsonObject = {
        "type": {
            "type": "string",
            "const": contract.type,
        },
        "version": {
            "type": "string",
            "const": contract.version,
        },
        "description": {
            "type": "string",
            "const": contract.description,
        },
        "pathPattern": {
            "type": "string",
            "const": contract.path_pattern,
        },
        "status": {
            "type": "object",
            "required": [
                "heading",
                "pattern",
            ],
            "additionalProperties": False,
            "properties": {
                "heading": {
                    "type": "string",
                    "const": contract.status.heading,
                },
                "pattern": {
                    "type": "string",
                    "const": contract.status.pattern,
                },
            },
        },
        "provenance": {
            "type": "object",
            "required": [
                "heading",
                "requiredIdentities",
            ],
            "additionalProperties": False,
            "properties": {
                "heading": {
                    "type": "string",
                    "const": contract.provenance.heading,
                },
                "requiredIdentities": _constant_string_array(
                    contract.provenance.required_identities
                ),
            },
        },
        "allowedStatuses": _constant_string_array(contract.allowed_statuses),
        "requiredHeadings": _constant_string_array(contract.required_headings),
    }

    return {
        "$schema": ("https://json-schema.org/draft/2020-12/schema"),
        "$id": (
            "https://example.local/agentic/artifacts/"
            f"{_slugify_artifact_type(contract.type)}"
            ".schema.json"
        ),
        "title": (f"{contract.type} Artifact Contract"),
        "type": "object",
        "required": required_fields,
        "additionalProperties": False,
        "properties": properties,
    }


def _constant_string_array(
    values: tuple[str, ...],
) -> JsonObject:
    return {
        "type": "array",
        "prefixItems": [
            {
                "type": "string",
                "const": value,
            }
            for value in values
        ],
        "items": False,
        "minItems": len(values),
        "maxItems": len(values),
        "uniqueItems": True,
    }


def _slugify_artifact_type(
    artifact_type: str,
) -> str:
    return re.sub(
        r"(?<!^)(?=[A-Z])",
        "-",
        artifact_type,
    ).lower()


def _validate_generated_schema_parity(
    projections: tuple[ArtifactSchemaProjection, ...],
    snapshots: tuple[ArtifactSchemaSnapshot, ...],
) -> tuple[Diagnostic, ...]:
    snapshots_by_path = {snapshot.source_path: snapshot for snapshot in snapshots}
    expected_paths = {projection.schema_path for projection in projections}
    diagnostics: list[Diagnostic] = []

    for projection in projections:
        snapshot = snapshots_by_path.get(projection.schema_path)

        if snapshot is None:
            diagnostics.append(
                Diagnostic(
                    code=(MISSING_GENERATED_SCHEMA_DIAGNOSTIC),
                    message="missing artifact.schema.json",
                    source_path=projection.contract_path,
                    location="artifact.schema.json",
                    related_identities=(projection.artifact_type,),
                )
            )
            continue

        if snapshot.canonical_json != projection.canonical_json:
            diagnostics.append(
                Diagnostic(
                    code=GENERATED_SCHEMA_DRIFT_DIAGNOSTIC,
                    message=(
                        "artifact.schema.json does not "
                        "match expected schema generated "
                        "from artifact.json"
                    ),
                    source_path=projection.schema_path,
                    location="$",
                    related_identities=(projection.artifact_type,),
                )
            )

    for snapshot in snapshots:
        if snapshot.source_path in expected_paths:
            continue

        diagnostics.append(
            Diagnostic(
                code=ORPHAN_GENERATED_SCHEMA_DIAGNOSTIC,
                message=("orphan artifact.schema.json without artifact.json"),
                source_path=snapshot.source_path,
                location="$",
            )
        )

    return tuple(diagnostics)


def _schema_error_sort_key(
    error: ValidationError,
) -> tuple[tuple[str, ...], str]:
    return shared_schema_error_sort_key(error)


def _schema_error_location(
    error: ValidationError,
) -> str:
    return shared_schema_error_location(error)
