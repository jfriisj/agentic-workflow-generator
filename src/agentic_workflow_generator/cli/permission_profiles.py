"""Permission profile validation command."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.cli.rendering import render_failure
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
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
from agentic_workflow_generator.validation import (
    validate_permission_profile_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-PERMISSION-900"


def main() -> int:
    """Validate the permission-profile registry."""

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        sources = RegistryLoader(paths).load(RegistryKind.PERMISSION_PROFILE)
        schema = read_json_object(
            paths.schema_root / "registry" / "permission-profile.schema.json"
        )
    except (InfrastructureError, RegistryError) as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    result = validate_permission_profile_registry(
        sources,
        schema,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    print(
        "PASS: Permission profile registry is valid. "
        f"Checked {len(result.profiles)} permission "
        "profile file(s)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Permission profile registry', diagnostics)
