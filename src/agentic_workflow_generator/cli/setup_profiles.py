"""Materialized guided setup-profile validation command."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from agentic_workflow_generator.cli.rendering import render_failure
from agentic_workflow_generator.cli.setup_context import (
    SetupContextError,
    load_setup_validation_context,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.validation.setup_profiles import (
    validate_setup_profile,
)
from agentic_workflow_generator.validation.setups import (
    validate_setup_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-SETUP-PROFILE-900"
DEFAULT_PROFILE_PATH = Path(".agentic/setup-profile.json")


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Validate one materialized guided setup profile."""

    args = _parse_args(argv)
    profile_path = Path(args.profile_path)

    try:
        context = load_setup_validation_context(
            Path.cwd().resolve()
        )
        profile_schema = read_json_object(
            context.paths.schema_root
            / "setup-profile.schema.json"
        )
        profile_data = read_json_object(profile_path)
    except (
        InfrastructureError,
        SetupContextError,
    ) as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    setup_result = validate_setup_registry(
        context.setup_sources,
        context.setup_schema,
        context.references,
    )

    if not setup_result.is_valid:
        return _render_failure(setup_result.diagnostics)

    result = validate_setup_profile(
        profile_data,
        profile_path,
        profile_schema,
        setup_result.setups,
        context.references,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    print(f"PASS: Setup profile is valid: {profile_path}")
    return 0


def _parse_args(
    argv: Sequence[str] | None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Validate a materialized Agentic guided setup profile.")
    )
    parser.add_argument(
        "profile_path",
        nargs="?",
        default=str(DEFAULT_PROFILE_PATH),
        help=("Setup profile path. Defaults to .agentic/setup-profile.json."),
    )
    return parser.parse_args(argv)


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Setup profile', diagnostics)

if __name__ == "__main__":
    raise SystemExit(main())
