"""Active configuration validation command."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

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
from agentic_workflow_generator.validation.schema_support import (
    object_schema_diagnostics,
)

SCHEMA_DIAGNOSTIC = "AWG-ACTIVE-CONFIG-001"
COMMAND_FAILURE_DIAGNOSTIC = "AWG-ACTIVE-CONFIG-900"
DEFAULT_CONFIG_PATH = Path(".agentic/agentic.json")
DEFAULT_SCHEMA_PATH = Path(
    ".agentic/schemas/agentic.schema.json"
)


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Validate one serialized active configuration."""

    args = _parse_args(argv)
    config_path = Path(args.config_path)
    schema_path = Path(args.schema_path)

    try:
        schema = read_json_object(schema_path)
        Draft202012Validator.check_schema(schema)
        config = read_json_object(config_path)
    except (
        InfrastructureError,
        SchemaError,
    ) as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    diagnostics = object_schema_diagnostics(
        config,
        config_path,
        Draft202012Validator(schema),
        SCHEMA_DIAGNOSTIC,
    )

    if diagnostics:
        return _render_failure(diagnostics)

    print(
        "PASS: Active configuration is valid: "
        f"{config_path}"
    )
    return 0


def _parse_args(
    argv: Sequence[str] | None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one serialized Agentic active "
            "configuration."
        )
    )
    parser.add_argument(
        "config_path",
        nargs="?",
        default=str(DEFAULT_CONFIG_PATH),
        help=(
            "Active configuration path. Defaults to "
            ".agentic/agentic.json."
        ),
    )
    parser.add_argument(
        "schema_path",
        nargs="?",
        default=str(DEFAULT_SCHEMA_PATH),
        help=(
            "Active configuration schema path. Defaults to "
            ".agentic/schemas/agentic.schema.json."
        ),
    )
    return parser.parse_args(argv)


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure(
        "Active configuration",
        diagnostics,
    )


if __name__ == "__main__":
    raise SystemExit(main())
