#!/usr/bin/env python3
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path.cwd()

SCHEMA_TARGETS = [
    (
        ".agentic/schemas/registry/agent.schema.json",
        "registry/agents/*/agent.json",
        "agent",
    ),
    (
        ".agentic/schemas/registry/skill.schema.json",
        "registry/skills/*/skill.json",
        "skill",
    ),
    (
        ".agentic/schemas/registry/workflow.schema.json",
        "registry/workflows/*.workflow.json",
        "workflow",
    ),
    (
        ".agentic/schemas/registry/target-adapter.schema.json",
        "registry/targets/*/adapter.json",
        "target adapter",
    ),
    (
        ".agentic/schemas/registry/profile.schema.json",
        "registry/profiles/*.profile.json",
        "profile",
    ),
    (
        ".agentic/schemas/registry/bundle.schema.json",
        "registry/bundles/*.bundle.json",
        "bundle",
    ),
    (
        ".agentic/schemas/registry/setup.schema.json",
        "registry/setups/*.setup.json",
        "setup",
    ),
    (
        ".agentic/schemas/registry/artifact.schema.json",
        "registry/artifacts/*/artifact.json",
        "artifact",
    ),
    (
        ".agentic/schemas/registry/permission-profile.schema.json",
        "registry/permission-profiles/*/permission-profile.json",
        "permission profile",
    ),
]


class ValidationError(Exception):
    pass


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise ValidationError(f"Required file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"{path}: invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc


def format_instance_path(
    document_path: Path,
    segments: Iterable[Any],
) -> str:
    result = str(document_path)

    for segment in segments:
        if isinstance(segment, int):
            result += f"[{segment}]"
        else:
            result += f".{segment}"

    return result


def validate_document(
    schema_path: Path,
    document_path: Path,
) -> list[str]:
    try:
        schema = load_json(schema_path)
        document = load_json(document_path)
    except ValidationError as exc:
        return [str(exc)]

    if not isinstance(schema, dict):
        return [f"{schema_path}: schema root must be an object"]

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        schema_location = format_instance_path(
            schema_path,
            exc.absolute_schema_path,
        )
        return [
            f"{schema_location}: invalid Draft 2020-12 schema: "
            f"{exc.message}"
        ]

    validator = Draft202012Validator(schema)

    validation_errors = sorted(
        validator.iter_errors(document),
        key=lambda error: (
            tuple(str(item) for item in error.absolute_path),
            tuple(str(item) for item in error.absolute_schema_path),
            error.message,
        ),
    )

    errors: list[str] = []

    for error in validation_errors:
        location = format_instance_path(
            document_path,
            error.absolute_path,
        )
        errors.append(f"{location}: {error.message}")

    return errors


def main() -> int:
    all_errors: list[str] = []
    checked = 0

    for schema_rel, glob_pattern, label in SCHEMA_TARGETS:
        schema_path = ROOT / schema_rel

        if not schema_path.is_file():
            all_errors.append(
                f"Missing {label} schema: {schema_path}"
            )
            continue

        documents = sorted(ROOT.glob(glob_pattern))

        if not documents:
            all_errors.append(
                f"No {label} registry files found for pattern: "
                f"{glob_pattern}"
            )
            continue

        for document_path in documents:
            checked += 1
            all_errors.extend(
                validate_document(
                    schema_path,
                    document_path,
                )
            )

    if all_errors:
        print("ERROR: Registry schema validation failed.")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print(
        "PASS: Registry JSON schemas are valid. "
        f"Checked {checked} registry file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
