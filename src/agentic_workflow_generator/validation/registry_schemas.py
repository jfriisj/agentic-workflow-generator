"""Mechanical Draft 2020-12 validation of registry schemas and documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    read_json,
    read_json_object,
)
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryError,
    RegistryKind,
    RegistryLoader,
)
from agentic_workflow_generator.validation.schema_support import (
    json_value_schema_diagnostics,
)

SCHEMA_INPUT_DIAGNOSTIC = "AWG-REGISTRY-SCHEMA-001"
SCHEMA_DEFINITION_DIAGNOSTIC = "AWG-REGISTRY-SCHEMA-002"
REGISTRY_DISCOVERY_DIAGNOSTIC = "AWG-REGISTRY-SCHEMA-003"
DOCUMENT_SCHEMA_DIAGNOSTIC = "AWG-REGISTRY-SCHEMA-004"
DOCUMENT_INPUT_DIAGNOSTIC = "AWG-REGISTRY-SCHEMA-005"


@dataclass(frozen=True, slots=True)
class RegistrySchemaContract:
    """One schema-to-registry-kind validation contract."""

    kind: RegistryKind
    schema_filename: str


@dataclass(frozen=True, slots=True)
class RegistrySchemaValidationResult:
    """Deterministic mechanical registry-schema validation result."""

    checked_document_count: int
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


REGISTRY_SCHEMA_CONTRACTS = (
    RegistrySchemaContract(
        RegistryKind.AGENT,
        "agent.schema.json",
    ),
    RegistrySchemaContract(
        RegistryKind.SKILL,
        "skill.schema.json",
    ),
    RegistrySchemaContract(
        RegistryKind.WORKFLOW,
        "workflow.schema.json",
    ),
    RegistrySchemaContract(
        RegistryKind.TARGET,
        "target-adapter.schema.json",
    ),
    RegistrySchemaContract(
        RegistryKind.PROFILE,
        "profile.schema.json",
    ),
    RegistrySchemaContract(
        RegistryKind.BUNDLE,
        "bundle.schema.json",
    ),
    RegistrySchemaContract(
        RegistryKind.SETUP,
        "setup.schema.json",
    ),
    RegistrySchemaContract(
        RegistryKind.ARTIFACT,
        "artifact.schema.json",
    ),
    RegistrySchemaContract(
        RegistryKind.PERMISSION_PROFILE,
        "permission-profile.schema.json",
    ),
)


def validate_registry_schemas(
    paths: ProjectPaths,
) -> RegistrySchemaValidationResult:
    """Validate every registry schema and matching document."""

    loader = RegistryLoader(paths)
    diagnostics: list[Diagnostic] = []
    checked_document_count = 0

    for contract in REGISTRY_SCHEMA_CONTRACTS:
        schema_path = (
            paths.schema_root
            / "registry"
            / contract.schema_filename
        )

        try:
            schema = read_json_object(schema_path)
        except InfrastructureError as exc:
            diagnostics.append(
                Diagnostic(
                    code=SCHEMA_INPUT_DIAGNOSTIC,
                    message=str(exc),
                    source_path=_relative_path(
                        paths,
                        schema_path,
                    ),
                )
            )
            continue

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            diagnostics.append(
                Diagnostic(
                    code=SCHEMA_DEFINITION_DIAGNOSTIC,
                    message=(
                        "invalid Draft 2020-12 schema: "
                        f"{exc.message}"
                    ),
                    source_path=_relative_path(
                        paths,
                        schema_path,
                    ),
                    location=_schema_error_location(exc),
                )
            )
            continue

        try:
            document_paths = loader.discover(contract.kind)
        except RegistryError as exc:
            diagnostics.append(
                Diagnostic(
                    code=REGISTRY_DISCOVERY_DIAGNOSTIC,
                    message=str(exc),
                    source_path=(
                        paths.registry_root
                        / contract.kind.directory_name
                    )
                    .relative_to(paths.root)
                    .as_posix(),
                )
            )
            continue

        validator = Draft202012Validator(schema)
        checked_document_count += len(document_paths)

        for document_path in document_paths:
            relative_document_path = document_path.relative_to(
                paths.root
            )

            try:
                document = read_json(document_path)
            except InfrastructureError as exc:
                diagnostics.append(
                    Diagnostic(
                        code=DOCUMENT_INPUT_DIAGNOSTIC,
                        message=str(exc),
                        source_path=(
                            relative_document_path.as_posix()
                        ),
                    )
                )
                continue

            diagnostics.extend(
                json_value_schema_diagnostics(
                    document,
                    relative_document_path,
                    validator,
                    DOCUMENT_SCHEMA_DIAGNOSTIC,
                )
            )

    return RegistrySchemaValidationResult(
        checked_document_count=checked_document_count,
        diagnostics=tuple(diagnostics),
    )


def _relative_path(
    paths: ProjectPaths,
    path: Path,
) -> str:
    return path.relative_to(paths.root).as_posix()


def _schema_error_location(
    error: SchemaError,
) -> str:
    location = "$"

    for component in error.absolute_schema_path:
        if isinstance(component, int):
            location += f"[{component}]"
        else:
            location += f".{component}"

    return location
