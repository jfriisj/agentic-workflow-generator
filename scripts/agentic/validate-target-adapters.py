#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
TARGETS_DIR = ROOT / "registry" / "targets"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data



def is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def normalized_path_parts(value: str) -> tuple[str, ...]:
    return tuple(part for part in Path(value).parts if part not in {"."})


def owned_paths_overlap(left: str, right: str) -> bool:
    left_parts = normalized_path_parts(left)
    right_parts = normalized_path_parts(right)

    if not left_parts or not right_parts:
        return False

    min_len = min(len(left_parts), len(right_parts))
    return left_parts[:min_len] == right_parts[:min_len]


def validate_owned_paths(adapter_path: Path, adapter: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    owned_paths = adapter.get("ownedPaths")

    if not isinstance(owned_paths, list) or not owned_paths:
        return [f"{adapter_path}: ownedPaths must be a non-empty list"]

    seen_paths: set[str] = set()
    valid_paths: list[str] = []

    for index, owned_path in enumerate(owned_paths):
        if not isinstance(owned_path, str) or not owned_path.strip():
            errors.append(f"{adapter_path}: ownedPaths[{index}] must be a non-empty string")
            continue

        if not is_safe_relative_path(owned_path):
            errors.append(f"{adapter_path}: ownedPaths[{index}] must be a safe relative path")
            continue

        if owned_path in seen_paths:
            errors.append(f"{adapter_path}: ownedPaths[{index}] is duplicated")
            continue

        seen_paths.add(owned_path)
        valid_paths.append(owned_path)

    for left_index, left in enumerate(valid_paths):
        for right_index, right in enumerate(valid_paths[left_index + 1 :], start=left_index + 1):
            if owned_paths_overlap(left, right):
                errors.append(
                    f"{adapter_path}: ownedPaths[{left_index}] overlaps ownedPaths[{right_index}]"
                )

    return errors

def validate_adapter_file(adapter_path: Path) -> list[str]:
    errors: list[str] = []
    target_name = adapter_path.parent.name

    try:
        adapter = load_json(adapter_path)
    except Exception as exc:
        return [f"{adapter_path}: {exc}"]

    declared_name = adapter.get("name")
    if not isinstance(declared_name, str) or not declared_name.strip():
        errors.append(f"{adapter_path}: name must be a non-empty string")
    elif declared_name != target_name:
        errors.append(
            f"{adapter_path}: declared name '{declared_name}' does not match target folder '{target_name}'"
        )

    description = adapter.get("description")
    if description is not None and not isinstance(description, str):
        errors.append(f"{adapter_path}: description must be a string when present")

    version = adapter.get("version")
    if version is not None and (not isinstance(version, str) or not version.strip()):
        errors.append(f"{adapter_path}: version must be a non-empty string when present")

    errors.extend(validate_owned_paths(adapter_path, adapter))

    permission_mapping = adapter.get("permissionMapping")
    if permission_mapping is not None and not isinstance(permission_mapping, dict):
        errors.append(f"{adapter_path}: permissionMapping must be an object when present")

    output = adapter.get("output")
    if output is not None and not isinstance(output, dict):
        errors.append(f"{adapter_path}: output must be an object when present")

    return errors


def validate_config_targets(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    targets = config.get("targets", [])
    if not isinstance(targets, list):
        return [".agentic/agentic.json: targets must be a list"]

    seen_target_names: set[str] = set()

    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(".agentic/agentic.json: target entries must be objects")
            continue

        target_name = target.get("name")
        enabled = target.get("enabled", False)

        if not isinstance(target_name, str) or not target_name.strip():
            errors.append(".agentic/agentic.json: target.name must be a non-empty string")
            continue

        if target_name in seen_target_names:
            errors.append(f".agentic/agentic.json: target name '{target_name}' is duplicated")

        seen_target_names.add(target_name)

        if not isinstance(enabled, bool):
            errors.append(f".agentic/agentic.json: target '{target_name}' enabled must be a boolean")
            continue

        adapter_path = TARGETS_DIR / target_name / "adapter.json"

        if enabled and not adapter_path.is_file():
            errors.append(
                f".agentic/agentic.json: enabled target '{target_name}' is missing adapter: "
                f"{adapter_path.relative_to(ROOT)}"
            )

    return errors


def main() -> int:
    errors: list[str] = []

    config = load_json(CONFIG_PATH)
    errors.extend(validate_config_targets(config))

    adapter_files = sorted(TARGETS_DIR.glob("*/adapter.json"))

    for adapter_path in adapter_files:
        errors.extend(validate_adapter_file(adapter_path))

    if errors:
        print(f"FAIL: Target adapter validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Target adapters are valid. Checked {len(adapter_files)} adapter file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
