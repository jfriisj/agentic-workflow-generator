"""Target adapter registry validation command."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.cli.rendering import (
    render_failure,
)
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
    TargetReferenceData,
    validate_permission_profile_registry,
    validate_target_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-TARGET-900"


def main() -> int:
    """Validate the target adapter registry."""

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        loader = RegistryLoader(paths)

        permission_result = (
            validate_permission_profile_registry(
                loader.load(
                    RegistryKind.PERMISSION_PROFILE
                ),
                read_json_object(
                    paths.schema_root
                    / "registry"
                    / "permission-profile.schema.json"
                ),
            )
        )

        if not permission_result.is_valid:
            return render_failure(
                "Target adapter registry dependency",
                permission_result.diagnostics,
            )

        result = validate_target_registry(
            loader.load(RegistryKind.TARGET),
            read_json_object(
                paths.schema_root
                / "registry"
                / "target-adapter.schema.json"
            ),
            TargetReferenceData(
                permission_profiles=frozenset(
                    profile.name
                    for profile
                    in permission_result.profiles
                ),
            ),
        )
    except (InfrastructureError, RegistryError) as exc:
        return render_failure(
            "Target adapter registry",
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            ),
        )

    if not result.is_valid:
        return render_failure(
            "Target adapter registry",
            result.diagnostics,
        )

    print(
        "PASS: Target adapter registry is valid. "
        f"Checked {len(result.adapters)} target adapter "
        "file(s) against "
        f"{len(permission_result.profiles)} permission "
        "profile(s)."
    )
    return 0
