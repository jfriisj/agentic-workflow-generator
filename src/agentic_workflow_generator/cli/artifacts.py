"""Artifact-contract registry validation command."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.cli.rendering import render_failure
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    read_json_object,
    serialize_json,
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
from agentic_workflow_generator.validation.artifacts import (
    ArtifactSchemaSnapshot,
    validate_artifact_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-ARTIFACT-900"


def main() -> int:
    """Validate the reusable artifact-contract registry."""

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        loader = RegistryLoader(paths)
        artifact_sources = loader.load(RegistryKind.ARTIFACT)
        schema = read_json_object(
            paths.schema_root / "registry" / "artifact.schema.json"
        )
        schema_snapshots = tuple(
            ArtifactSchemaSnapshot(
                source_path=path.relative_to(paths.root).as_posix(),
                canonical_json=serialize_json(read_json_object(path)),
            )
            for path in sorted(
                (paths.registry_root / RegistryKind.ARTIFACT.directory_name).glob(
                    "*/artifact.schema.json"
                ),
                key=lambda item: item.relative_to(paths.registry_root).as_posix(),
            )
        )
    except (
        InfrastructureError,
        RegistryError,
    ) as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    result = validate_artifact_registry(
        artifact_sources,
        schema,
        schema_snapshots,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    print(
        "PASS: Artifact contracts are valid. "
        f"Checked {len(result.contracts)} artifact file(s)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Artifact contract', diagnostics)

if __name__ == "__main__":
    raise SystemExit(main())
