#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


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
        ".agentic/schemas/registry/artifact.schema.json",
        "registry/artifacts/*/artifact.json",
        "artifact",
    ),
]


class ValidationError(Exception):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc}") from exc


def json_type_name(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__


def matches_type(value: Any, expected: str) -> bool:
    actual = json_type_name(value)

    if expected == "number":
        return actual in {"integer", "number"}

    return actual == expected


def validate_value(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []

    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not matches_type(value, expected_type):
        errors.append(f"{path}: expected {expected_type}, got {json_type_name(value)}")
        return errors

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        errors.append(f"{path}: expected one of {enum!r}, got {value!r}")

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            errors.append(f"{path}: string length must be >= {min_length}")

    if isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_value(item, item_schema, f"{path}[{index}]"))

        if schema.get("uniqueItems") is True:
            seen: set[str] = set()
            for index, item in enumerate(value):
                key = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if key in seen:
                    errors.append(f"{path}[{index}]: duplicate array item {item!r}")
                seen.add(key)

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for field in required:
                if isinstance(field, str) and field not in value:
                    errors.append(f"{path}: missing required field {field!r}")

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for field, field_schema in properties.items():
                if field in value and isinstance(field_schema, dict):
                    errors.extend(validate_value(value[field], field_schema, f"{path}.{field}"))

        additional = schema.get("additionalProperties")
        if additional is False and isinstance(properties, dict):
            allowed = set(properties)
            for field in value:
                if field not in allowed:
                    errors.append(f"{path}: unknown field {field!r}")

    return errors


def validate_document(schema_path: Path, document_path: Path) -> list[str]:
    schema = load_json(schema_path)
    document = load_json(document_path)

    if not isinstance(schema, dict):
        return [f"{schema_path}: schema root must be an object"]

    return validate_value(document, schema, str(document_path))


def main() -> int:
    all_errors: list[str] = []
    checked = 0

    for schema_rel, glob_pattern, label in SCHEMA_TARGETS:
        schema_path = ROOT / schema_rel
        if not schema_path.is_file():
            all_errors.append(f"Missing {label} schema: {schema_path}")
            continue

        documents = sorted(ROOT.glob(glob_pattern))
        if not documents:
            all_errors.append(f"No {label} registry files found for pattern: {glob_pattern}")
            continue

        for document_path in documents:
            checked += 1
            all_errors.extend(validate_document(schema_path, document_path))

    if all_errors:
        print("ERROR: Registry schema validation failed.")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Registry JSON schemas are valid. Checked {checked} registry file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
