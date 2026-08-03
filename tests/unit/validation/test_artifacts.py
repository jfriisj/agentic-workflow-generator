import re
from collections.abc import Callable
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

import agentic_workflow_generator.validation.artifacts as artifacts_module
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    read_json_object,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.artifacts import (
    DUPLICATE_TYPE_DIAGNOSTIC,
    FOLDER_TYPE_DIAGNOSTIC,
    GENERATED_SCHEMA_DRIFT_DIAGNOSTIC,
    INVALID_STATUS_PATTERN_DIAGNOSTIC,
    MISSING_GENERATED_SCHEMA_DIAGNOSTIC,
    OBSOLETE_FIELD_DIAGNOSTIC,
    ORPHAN_GENERATED_SCHEMA_DIAGNOSTIC,
    PROVENANCE_HEADING_DIAGNOSTIC,
    REVISION_HEADING_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    STATUS_HEADING_DIAGNOSTIC,
    STATUS_PATTERN_MISMATCH_DIAGNOSTIC,
    ArtifactSchemaSnapshot,
    ArtifactValidationResult,
    validate_artifact_registry,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA = read_json_object(
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "artifact.schema.json"
)


def source(
    *,
    artifact_type: JsonValue = "Requirements",
    folder: str = "Requirements",
    version: JsonValue = "0.3.0",
    description: JsonValue = "Requirements contract.",
    path_pattern: JsonValue = ("agent-output/requirements/*.md"),
    status: JsonValue = None,
    status_invariants: JsonValue = None,
    allowed_statuses: JsonValue = None,
    required_headings: JsonValue = None,
    extra: tuple[str, JsonValue] | None = None,
) -> RegistrySource:
    data: JsonObject = {
        "type": artifact_type,
        "version": version,
        "description": description,
        "pathPattern": path_pattern,
        "status": (
            {
                "heading": "## Status",
                "pattern": "PASS|FAIL|BLOCKED",
            }
            if status is None
            else status
        ),
        "provenance": {
            "heading": "## Provenance",
            "requiredIdentities": [
                "artifactType",
                "artifactVersion",
                "workflow",
                "workflowVersion",
                "roleBinding",
                "agentInstance",
            ],
        },
        "revision": {
            "heading": "## Revision",
            "pattern": "^[1-9][0-9]*$",
        },
        "statusInvariants": (
            {
                "passRequiresCompleteEvidence": True,
                "passForbidsDemonstratedNonconformance": True,
                "failRequiresDemonstratedNonconformance": True,
                "blockedRequiresUnavailablePrerequisite": True,
            }
            if status_invariants is None
            else status_invariants
        ),
        "allowedStatuses": (
            ["PASS", "FAIL", "BLOCKED"]
            if allowed_statuses is None
            else allowed_statuses
        ),
        "requiredHeadings": (
            [
                "# Requirements",
                "## Status",
                "## Provenance",
                "## Revision",
                "## Summary",
            ]
            if required_headings is None
            else required_headings
        ),
    }

    if extra is not None:
        data[extra[0]] = extra[1]

    return RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=Path(f"registry/artifacts/{folder}/artifact.json"),
        data=data,
    )


def matching_snapshots(
    *sources: RegistrySource,
) -> tuple[ArtifactSchemaSnapshot, ...]:
    projected = validate_artifact_registry(
        tuple(sources),
        SCHEMA,
        (),
    )

    return tuple(
        ArtifactSchemaSnapshot(
            source_path=projection.schema_path,
            canonical_json=projection.canonical_json,
        )
        for projection in projected.schema_projections
    )


def validate(
    *sources: RegistrySource,
    snapshots: tuple[ArtifactSchemaSnapshot, ...] | None = None,
) -> ArtifactValidationResult:
    effective_snapshots = (
        matching_snapshots(*sources) if snapshots is None else snapshots
    )

    return validate_artifact_registry(
        tuple(sources),
        SCHEMA,
        effective_snapshots,
    )


def test_valid_artifact_is_parsed_and_schema_is_projected() -> None:
    artifact_source = source()
    result = validate(artifact_source)

    assert result.is_valid
    assert result.diagnostics == ()
    assert len(result.contracts) == 1
    assert len(result.schema_projections) == 1

    contract = result.contracts[0]
    assert contract.type == "Requirements"
    assert contract.version == "0.3.0"
    assert contract.description == "Requirements contract."
    assert contract.path_pattern == "agent-output/requirements/*.md"
    assert contract.status.heading == "## Status"
    assert contract.status.pattern == "PASS|FAIL|BLOCKED"
    assert contract.provenance.heading == "## Provenance"
    assert contract.provenance.required_identities == (
        "artifactType",
        "artifactVersion",
        "workflow",
        "workflowVersion",
        "roleBinding",
        "agentInstance",
    )
    assert contract.revision.heading == "## Revision"
    assert contract.revision.pattern == "^[1-9][0-9]*$"
    assert contract.status_invariants.pass_requires_complete_evidence is True
    assert (
        contract.status_invariants
        .pass_forbids_demonstrated_nonconformance
        is True
    )
    assert (
        contract.status_invariants
        .fail_requires_demonstrated_nonconformance
        is True
    )
    assert (
        contract.status_invariants
        .blocked_requires_unavailable_prerequisite
        is True
    )
    assert contract.allowed_statuses == (
        "PASS",
        "FAIL",
        "BLOCKED",
    )
    assert contract.required_headings == (
        "# Requirements",
        "## Status",
        "## Provenance",
        "## Revision",
        "## Summary",
    )

    projection = result.schema_projections[0]
    assert projection.artifact_type == "Requirements"
    assert projection.contract_path == "registry/artifacts/Requirements/artifact.json"
    assert (
        projection.schema_path == "registry/artifacts/Requirements/artifact.schema.json"
    )
    assert '"version": {' in projection.canonical_json
    assert '"const": "0.3.0"' in projection.canonical_json
    assert '"provenance": {' in projection.canonical_json
    assert '"revision": {' in projection.canonical_json
    assert '"const": "## Revision"' in projection.canonical_json
    assert '"const": "^[1-9][0-9]*$"' in projection.canonical_json
    assert '"statusInvariants": {' in projection.canonical_json
    assert '"passRequiresCompleteEvidence": {' in projection.canonical_json
    assert (
        '"blockedRequiresUnavailablePrerequisite": {'
        in projection.canonical_json
    )


@pytest.mark.parametrize(
    "obsolete_field",
    [
        "binding",
        "producedBy",
        "required",
    ],
)
def test_obsolete_artifact_fields_are_rejected(
    obsolete_field: str,
) -> None:
    result = validate(
        source(extra=(obsolete_field, True)),
        snapshots=(),
    )

    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == OBSOLETE_FIELD_DIAGNOSTIC
    assert diagnostic.location == obsolete_field
    assert (
        diagnostic.message == f"obsolete artifact field {obsolete_field!r} is not allowed"
    )


@pytest.mark.parametrize(
    ("mutator", "expected_message"),
    [
        (
            lambda data: data.pop("type"),
            "type must be a non-empty string",
        ),
        (
            lambda data: data.pop("version"),
            "version must be a non-empty string",
        ),
        (
            lambda data: data.__setitem__("version", "v1"),
            "version must be a semantic version",
        ),
        (
            lambda data: data.__setitem__("description", ""),
            "description must be a non-empty string",
        ),
        (
            lambda data: data.__setitem__(
                "pathPattern",
                "/tmp/report.md",
            ),
            "pathPattern must be a safe relative path",
        ),
        (
            lambda data: data.__setitem__(
                "requiredHeadings",
                [],
            ),
            "requiredHeadings must be a non-empty list",
        ),
        (
            lambda data: data.__setitem__(
                "allowedStatuses",
                ["PASS", "PASS"],
            ),
            "allowedStatuses[1] is duplicated",
        ),
        (
            lambda data: data.__setitem__(
                "status",
                "invalid",
            ),
            "status must be an object",
        ),
        (
            lambda data: data.__setitem__(
                "statusInvariants",
                "invalid",
            ),
            "statusInvariants must be an object",
        ),
        (
            lambda data: data.__setitem__(
                "status",
                {"heading": "## Status"},
            ),
            "status.pattern must be a non-empty string",
        ),
        (
            lambda data: data.__setitem__(
                "status",
                {
                    "heading": "### Status",
                    "pattern": "PASS",
                },
            ),
            "status.heading must be exactly '## Status'",
        ),
    ],
)
def test_schema_errors_preserve_public_messages(
    mutator: Callable[[JsonObject], object],
    expected_message: str,
) -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    mutator(data)
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(
        invalid_source,
        snapshots=(),
    )

    assert result.contracts == ()
    assert result.schema_projections == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC
    assert result.diagnostics[0].message == expected_message


def test_type_must_match_containing_folder() -> None:
    result = validate(
        source(
            artifact_type="DifferentType",
            folder="Requirements",
        )
    )

    diagnostic = next(
        item for item in result.diagnostics if item.code == FOLDER_TYPE_DIAGNOSTIC
    )
    assert (
        diagnostic.message == "type 'DifferentType' does not match "
        "folder 'Requirements'"
    )


def test_artifact_types_must_be_unique() -> None:
    first = source()
    second = source(folder="Duplicate")

    result = validate(first, second)

    diagnostic = next(
        item for item in result.diagnostics if item.code == DUPLICATE_TYPE_DIAGNOSTIC
    )
    assert diagnostic.source_path == "registry/artifacts/Duplicate/artifact.json"
    assert diagnostic.related_identities == ("Requirements",)


def test_status_heading_must_be_required() -> None:
    result = validate(
        source(
            required_headings=[
                "# Requirements",
                "## Summary",
            ]
        )
    )

    assert any(item.code == STATUS_HEADING_DIAGNOSTIC for item in result.diagnostics)


def test_status_pattern_must_be_valid_regex() -> None:
    result = validate(
        source(
            status={
                "heading": "## Status",
                "pattern": "[",
            }
        )
    )

    assert any(
        item.code == INVALID_STATUS_PATTERN_DIAGNOSTIC for item in result.diagnostics
    )


def test_status_pattern_must_match_every_allowed_status() -> None:
    result = validate(
        source(
            status={
                "heading": "## Status",
                "pattern": "PASS|FAIL",
            }
        )
    )

    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == STATUS_PATTERN_MISMATCH_DIAGNOSTIC
    )
    assert diagnostic.related_identities == (
        "Requirements",
        "BLOCKED",
    )


def test_missing_generated_schema_is_rejected() -> None:
    result = validate(
        source(),
        snapshots=(),
    )

    assert any(
        item.code == MISSING_GENERATED_SCHEMA_DIAGNOSTIC for item in result.diagnostics
    )


def test_generated_schema_drift_is_rejected() -> None:
    artifact_source = source()
    projection = validate_artifact_registry(
        (artifact_source,),
        SCHEMA,
        (),
    ).schema_projections[0]
    snapshot = ArtifactSchemaSnapshot(
        source_path=projection.schema_path,
        canonical_json='{"drift": true}\n',
    )

    result = validate(
        artifact_source,
        snapshots=(snapshot,),
    )

    assert any(
        item.code == GENERATED_SCHEMA_DRIFT_DIAGNOSTIC for item in result.diagnostics
    )


def test_orphan_generated_schema_is_rejected() -> None:
    artifact_source = source()
    snapshots = (
        *matching_snapshots(artifact_source),
        ArtifactSchemaSnapshot(
            source_path=("registry/artifacts/Orphan/artifact.schema.json"),
            canonical_json="{}\n",
        ),
    )

    result = validate(
        artifact_source,
        snapshots=snapshots,
    )

    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == ORPHAN_GENERATED_SCHEMA_DIAGNOSTIC
    )
    assert diagnostic.source_path == "registry/artifacts/Orphan/artifact.schema.json"


def test_array_type_error_preserves_public_message() -> None:
    result = validate(
        source(allowed_statuses="PASS"),
        snapshots=(),
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == ("allowedStatuses must be a non-empty list")


def test_string_type_error_preserves_public_message() -> None:
    result = validate(
        source(artifact_type=42),
        snapshots=(),
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == ("type must be a non-empty string")


@pytest.mark.parametrize(
    ("missing_field", "expected_message"),
    [
        (
            "allowedStatuses",
            "allowedStatuses must be a non-empty list",
        ),
        (
            "status",
            "status must be an object",
        ),
        (
            "statusInvariants",
            "statusInvariants must be an object",
        ),
    ],
)
def test_missing_structured_fields_preserve_public_messages(
    missing_field: str,
    expected_message: str,
) -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    data.pop(missing_field)
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(
        invalid_source,
        snapshots=(),
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == expected_message


def test_unmapped_schema_error_uses_generic_message() -> None:
    result = validate(
        source(extra=("unexpected", True)),
        snapshots=(),
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message.startswith("schema violation: ")
    assert "unexpected" in diagnostic.message


def test_array_item_error_uses_indexed_location() -> None:
    result = validate(
        source(required_headings=[1]),
        snapshots=(),
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.location == "$.requiredHeadings[0]"
    assert diagnostic.message == ("requiredHeadings.0 must be a non-empty string")


def test_artifact_schema_wrapper_helpers_delegate() -> None:
    error = ValidationError(
        "invalid heading",
        path=["requiredHeadings", 0],
    )

    assert artifacts_module._schema_error_sort_key(
        error
    ) == (
        (
            "requiredHeadings",
            "0",
        ),
        "invalid heading",
    )
    assert artifacts_module._schema_error_location(
        error
    ) == "$.requiredHeadings[0]"


def test_missing_provenance_is_rejected() -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    data.pop("provenance")
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(invalid_source, snapshots=())

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == "provenance must be an object"


def test_provenance_heading_is_canonical() -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    provenance = data["provenance"]
    assert isinstance(provenance, dict)
    provenance["heading"] = "### Provenance"
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(invalid_source, snapshots=())

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == (
        "provenance.heading must be exactly '## Provenance'"
    )


def test_provenance_identity_set_is_canonical() -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    provenance = data["provenance"]
    assert isinstance(provenance, dict)
    provenance["requiredIdentities"] = [
        "artifactType",
        "artifactVersion",
    ]
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(invalid_source, snapshots=())

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == (
        "provenance.requiredIdentities must match the canonical "
        "identity set"
    )


def test_provenance_heading_must_be_required() -> None:
    result = validate(
        source(
            required_headings=[
                "# Requirements",
                "## Status",
                "## Summary",
            ]
        )
    )

    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == PROVENANCE_HEADING_DIAGNOSTIC
    )
    assert diagnostic.location == "provenance.heading"
    assert diagnostic.related_identities == (
        "Requirements",
        "## Provenance",
    )


def test_missing_revision_is_rejected() -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    data.pop("revision")
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(invalid_source, snapshots=())

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == "revision must be an object"


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        (
            "heading",
            "### Revision",
            "revision.heading must be exactly '## Revision'",
        ),
        (
            "pattern",
            ".*",
            "revision.pattern must be exactly '^[1-9][0-9]*$'",
        ),
    ],
)
def test_revision_contract_is_canonical(
    field: str,
    value: str,
    expected_message: str,
) -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    revision = data["revision"]
    assert isinstance(revision, dict)
    revision[field] = value
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(invalid_source, snapshots=())

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == expected_message


def test_revision_heading_must_be_required() -> None:
    result = validate(
        source(
            required_headings=[
                "# Requirements",
                "## Status",
                "## Provenance",
                "## Summary",
            ]
        )
    )

    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == REVISION_HEADING_DIAGNOSTIC
    )
    assert diagnostic.location == "revision.heading"
    assert diagnostic.related_identities == (
        "Requirements",
        "## Revision",
    )


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        ("1", True),
        ("9", True),
        ("10", True),
        ("0", False),
        ("-1", False),
        ("+1", False),
        ("01", False),
        ("1.0", False),
        ("draft-2", False),
    ],
)
def test_revision_pattern_has_canonical_lexical_semantics(
    value: str,
    valid: bool,
) -> None:
    result = validate(source())
    assert result.is_valid
    pattern = result.contracts[0].revision.pattern
    assert (re.fullmatch(pattern, value) is not None) is valid


@pytest.mark.parametrize(
    "field",
    [
        "passRequiresCompleteEvidence",
        "passForbidsDemonstratedNonconformance",
        "failRequiresDemonstratedNonconformance",
        "blockedRequiresUnavailablePrerequisite",
    ],
)
def test_status_invariant_members_must_be_true(
    field: str,
) -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    invariants = data["statusInvariants"]
    assert isinstance(invariants, dict)
    invariants[field] = False
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(invalid_source, snapshots=())

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.message == f"statusInvariants.{field} must be true"


def test_status_invariant_members_cannot_be_renamed() -> None:
    artifact_source = source()
    data = artifact_source.to_json_object()
    invariants = data["statusInvariants"]
    assert isinstance(invariants, dict)
    invariants.pop("failRequiresDemonstratedNonconformance")
    invariants["failMayBeInferred"] = True
    invalid_source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=artifact_source.source_path,
        data=data,
    )

    result = validate(invalid_source, snapshots=())

    assert result.contracts == ()
    assert result.schema_projections == ()
    assert result.diagnostics
    assert all(
        diagnostic.code == SCHEMA_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )
