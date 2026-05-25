#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ARTIFACT_REGISTRY = ROOT / "registry" / "artifacts"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)



def is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def validate_string_list_entries(
    contract_path: Path,
    contract: dict[str, Any],
    key: str,
) -> list[str]:
    errors: list[str] = []
    values = contract.get(key)

    if not isinstance(values, list) or not values:
        return errors

    seen_values: set[str] = set()

    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{contract_path}: {key}[{index}] must be a non-empty string")
            continue

        if value in seen_values:
            errors.append(f"{contract_path}: {key}[{index}] is duplicated")

        seen_values.add(value)

    return errors


def validate_status_pattern(
    contract_path: Path,
    status_pattern: str,
    allowed_statuses: list[Any],
) -> list[str]:
    errors: list[str] = []

    if not all(isinstance(status, str) and status.strip() for status in allowed_statuses):
        return errors

    pattern_values = [part.strip() for part in status_pattern.split("|") if part.strip()]
    if not pattern_values:
        errors.append(f"{contract_path}: status.pattern must define at least one status value")
        return errors

    allowed_set = set(allowed_statuses)
    pattern_set = set(pattern_values)

    if pattern_set != allowed_set:
        errors.append(f"{contract_path}: status.pattern must match allowedStatuses")

    return errors

def validate_contract_shape(contract_path: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    errors: list[str] = []

    required_keys = {"type", "status", "allowedStatuses", "requiredHeadings"}
    missing = sorted(required_keys - set(contract.keys()))

    if missing:
        raise ValueError(f"{contract_path}: missing required keys: {', '.join(missing)}")

    artifact_type = contract.get("type")
    expected_type = contract_path.parent.name
    if not isinstance(artifact_type, str) or not artifact_type.strip():
        errors.append(f"{contract_path}: type must be a non-empty string")
    elif artifact_type != expected_type:
        errors.append(f"{contract_path}: type '{artifact_type}' does not match folder '{expected_type}'")

    description = contract.get("description")
    if description is not None and not isinstance(description, str):
        errors.append(f"{contract_path}: description must be a string when present")

    path_pattern = contract.get("pathPattern")
    if path_pattern is not None:
        if not isinstance(path_pattern, str) or not path_pattern.strip():
            errors.append(f"{contract_path}: pathPattern must be a non-empty string when present")
        elif not is_safe_relative_path(path_pattern):
            errors.append(f"{contract_path}: pathPattern must be a safe relative path")

    required_headings = contract["requiredHeadings"]
    if not isinstance(required_headings, list) or not required_headings:
        errors.append(f"{contract_path}: requiredHeadings must be a non-empty list")
    else:
        errors.extend(validate_string_list_entries(contract_path, contract, "requiredHeadings"))

    allowed_statuses = contract["allowedStatuses"]
    if not isinstance(allowed_statuses, list) or not allowed_statuses:
        errors.append(f"{contract_path}: allowedStatuses must be a non-empty list")
    else:
        errors.extend(validate_string_list_entries(contract_path, contract, "allowedStatuses"))

    status = contract["status"]
    if not isinstance(status, dict):
        errors.append(f"{contract_path}: status must be an object")
    else:
        status_heading = status.get("heading")
        if status_heading != "## Status":
            errors.append(f"{contract_path}: status.heading must be '## Status'")
        elif isinstance(required_headings, list) and status_heading not in required_headings:
            errors.append(f"{contract_path}: status.heading must be included in requiredHeadings")

        status_pattern = status.get("pattern")
        if not isinstance(status_pattern, str) or not status_pattern.strip():
            errors.append(f"{contract_path}: status.pattern must be a non-empty string")
        elif isinstance(allowed_statuses, list):
            errors.extend(validate_status_pattern(contract_path, status_pattern, allowed_statuses))

    if errors:
        raise ValueError("\n".join(errors))

    return contract


def extract_status(markdown: str) -> str | None:
    status_section = re.search(
        r"^## Status\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL,
    )

    if not status_section:
        return None

    body = status_section.group("body").strip()
    match = re.search(r"\b(PASS|FAIL|BLOCKED)\b", body)

    if not match:
        return None

    return match.group(1)


def validate_markdown_artifact(path: Path, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    markdown = path.read_text(encoding="utf-8")

    for heading in contract["requiredHeadings"]:
        if heading not in markdown:
            errors.append(f"{path}: missing required heading: {heading}")

    status = extract_status(markdown)

    if status is None:
        errors.append(f"{path}: missing valid status value PASS, FAIL, or BLOCKED under ## Status")
    elif status not in contract["allowedStatuses"]:
        errors.append(f"{path}: unsupported status: {status}")

    return errors


def contract_artifact_paths(contract: dict[str, Any]) -> list[Path]:
    path_pattern = contract.get("pathPattern")

    if not path_pattern:
        return []

    return sorted(ROOT.glob(path_pattern))


def main() -> int:
    contract_files = sorted(ARTIFACT_REGISTRY.glob("*/artifact.json"))

    if not contract_files:
        print("WARN: No artifact contracts found under registry/artifacts.")
        return 0

    errors: list[str] = []
    checked_artifacts = 0

    for contract_path in contract_files:
        try:
            contract = validate_contract_shape(contract_path)
        except Exception as exc:
            errors.append(str(exc))
            continue

        artifact_paths = contract_artifact_paths(contract)
        checked_artifacts += len(artifact_paths)

        for artifact_path in artifact_paths:
            errors.extend(validate_markdown_artifact(artifact_path, contract))

    if errors:
        print(f"FAIL: Artifact validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Artifact contracts are valid. Checked {checked_artifacts} artifact file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
