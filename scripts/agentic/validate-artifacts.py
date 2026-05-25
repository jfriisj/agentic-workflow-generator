#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ARTIFACTS_DIR = ROOT / "registry" / "artifacts"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def slugify_artifact_type(artifact_type: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", artifact_type).lower()


def expected_schema_for_contract(contract: dict[str, Any]) -> dict[str, Any]:
    artifact_type = str(contract["type"])
    allowed_statuses = list(contract["allowedStatuses"])
    required_headings = list(contract["requiredHeadings"])

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://example.local/agentic/artifacts/{slugify_artifact_type(artifact_type)}.schema.json",
        "title": f"{artifact_type} Artifact Contract",
        "type": "object",
        "required": [
            "type",
            "description",
            "pathPattern",
            "status",
            "allowedStatuses",
            "requiredHeadings",
        ],
        "additionalProperties": False,
        "properties": {
            "type": {
                "type": "string",
                "const": artifact_type,
            },
            "description": {
                "type": "string",
                "const": contract["description"],
            },
            "pathPattern": {
                "type": "string",
                "const": contract["pathPattern"],
            },
            "status": {
                "type": "object",
                "required": ["heading", "pattern"],
                "additionalProperties": False,
                "properties": {
                    "heading": {
                        "type": "string",
                        "const": contract["status"]["heading"],
                    },
                    "pattern": {
                        "type": "string",
                        "const": contract["status"]["pattern"],
                    },
                },
            },
            "allowedStatuses": {
                "type": "array",
                "prefixItems": [
                    {
                        "type": "string",
                        "const": status,
                    }
                    for status in allowed_statuses
                ],
                "items": False,
                "minItems": len(allowed_statuses),
                "maxItems": len(allowed_statuses),
                "uniqueItems": True,
            },
            "requiredHeadings": {
                "type": "array",
                "prefixItems": [
                    {
                        "type": "string",
                        "const": heading,
                    }
                    for heading in required_headings
                ],
                "items": False,
                "minItems": len(required_headings),
                "maxItems": len(required_headings),
                "uniqueItems": True,
            },
        },
    }


def validate_string_list(path: Path, data: dict[str, Any], key: str) -> list[str]:
    errors: list[str] = []
    value = data.get(key)

    if not isinstance(value, list) or not value:
        return [f"{path}: {key} must be a non-empty list"]

    seen: set[str] = set()

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}: {key} entries must be non-empty strings")
            continue

        if item in seen:
            errors.append(f"{path}: {key} contains duplicate entry")
            continue

        seen.add(item)

    return errors


def validate_artifact_contract(path: Path) -> list[str]:
    errors: list[str] = []
    expected_type = path.parent.name

    try:
        artifact = load_json(path)
    except Exception as exc:
        return [f"{path}: {exc}"]

    artifact_type = artifact.get("type")
    if artifact_type != expected_type:
        errors.append(f"{path}: type must match containing directory '{expected_type}'")

    description = artifact.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{path}: description must be a non-empty string")

    path_pattern = artifact.get("pathPattern")
    if not isinstance(path_pattern, str) or not path_pattern.strip():
        errors.append(f"{path}: pathPattern must be a non-empty string")
    elif not is_safe_relative_path(path_pattern):
        errors.append(f"{path}: pathPattern must be a safe relative path")

    errors.extend(validate_string_list(path, artifact, "requiredHeadings"))
    errors.extend(validate_string_list(path, artifact, "allowedStatuses"))

    status = artifact.get("status")
    if not isinstance(status, dict):
        errors.append(f"{path}: status must be an object")
        return errors

    status_heading = status.get("heading")
    if status_heading != "## Status":
        errors.append(f"{path}: status.heading must be exactly '## Status'")

    required_headings = artifact.get("requiredHeadings")
    if isinstance(required_headings, list) and status_heading not in required_headings:
        errors.append(f"{path}: status.heading must be present in requiredHeadings")

    status_pattern = status.get("pattern")
    if not isinstance(status_pattern, str) or not status_pattern.strip():
        errors.append(f"{path}: status.pattern must be a non-empty string")
        return errors

    allowed_statuses = artifact.get("allowedStatuses")
    if isinstance(allowed_statuses, list):
        try:
            compiled_pattern = re.compile(status_pattern)
        except re.error as exc:
            errors.append(f"{path}: status.pattern is not a valid regex: {exc}")
            return errors

        for allowed_status in allowed_statuses:
            if isinstance(allowed_status, str) and not compiled_pattern.fullmatch(allowed_status):
                errors.append(f"{path}: status.pattern must match every allowed status")
                break

    return errors


def validate_artifact_schema_parity(path: Path) -> list[str]:
    schema_path = path.parent / "artifact.schema.json"

    if not schema_path.is_file():
        return [f"{path.parent}: missing artifact.schema.json"]

    try:
        artifact = load_json(path)
        schema = load_json(schema_path)
    except Exception as exc:
        return [f"{schema_path}: {exc}"]

    try:
        expected_schema = expected_schema_for_contract(artifact)
    except Exception as exc:
        return [f"{schema_path}: could not build expected artifact schema: {exc}"]

    if schema != expected_schema:
        return [f"{schema_path}: artifact.schema.json does not match expected schema generated from artifact.json"]

    return []


def validate_orphan_artifact_schemas() -> list[str]:
    errors: list[str] = []

    for schema_path in sorted(ARTIFACTS_DIR.glob("*/artifact.schema.json")):
        artifact_path = schema_path.parent / "artifact.json"
        if not artifact_path.is_file():
            errors.append(f"{schema_path}: orphan artifact.schema.json without artifact.json")

    return errors


def generate_missing_or_outdated_schemas() -> None:
    for artifact_path in sorted(ARTIFACTS_DIR.glob("*/artifact.json")):
        artifact = load_json(artifact_path)
        schema_path = artifact_path.parent / "artifact.schema.json"
        write_json(schema_path, expected_schema_for_contract(artifact))


def main() -> int:
    artifact_files = sorted(ARTIFACTS_DIR.glob("*/artifact.json"))

    if not artifact_files:
        print("WARN: No artifact contracts found.")
        return 0

    errors: list[str] = []

    for artifact_path in artifact_files:
        errors.extend(validate_artifact_contract(artifact_path))
        errors.extend(validate_artifact_schema_parity(artifact_path))

    errors.extend(validate_orphan_artifact_schemas())

    if errors:
        print(f"FAIL: Artifact contract validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Artifact contracts are valid. Checked {len(artifact_files)} artifact file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
