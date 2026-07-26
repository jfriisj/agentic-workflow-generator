"""Shared setup-validation dependency loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_workflow_generator.infrastructure import (
    JsonObject,
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
    RegistrySource,
)
from agentic_workflow_generator.validation.setups import (
    SetupDependencyProjectionError,
    SetupReferenceData,
    project_setup_bundles,
    project_target_names,
)


@dataclass(frozen=True, slots=True)
class SetupValidationContext:
    """Loaded inputs shared by setup validation commands."""

    paths: ProjectPaths
    setup_sources: tuple[RegistrySource, ...]
    setup_schema: JsonObject
    references: SetupReferenceData


class SetupContextError(RuntimeError):
    """Raised when setup validation inputs cannot be loaded."""


def load_setup_validation_context(
    root: Path,
) -> SetupValidationContext:
    """Load setup registry data and projected dependencies."""

    try:
        paths = ProjectPaths(root)
        loader = RegistryLoader(paths)

        setup_sources = loader.load(RegistryKind.SETUP)
        bundle_sources = loader.load(RegistryKind.BUNDLE)
        target_sources = loader.load(RegistryKind.TARGET)

        setup_schema = read_json_object(
            paths.schema_root
            / "registry"
            / "setup.schema.json"
        )
        references = SetupReferenceData(
            bundles=project_setup_bundles(bundle_sources),
            targets=project_target_names(target_sources),
        )
    except (
        InfrastructureError,
        RegistryError,
        SetupDependencyProjectionError,
    ) as exc:
        raise SetupContextError(str(exc)) from exc

    return SetupValidationContext(
        paths=paths,
        setup_sources=setup_sources,
        setup_schema=setup_schema,
        references=references,
    )
