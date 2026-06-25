#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
BUNDLES_DIR = ROOT / "registry" / "bundles"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be an object")

    return data


def expected_bundle_name(path: Path) -> str:
    return path.name.removesuffix(".bundle.json")


def registry_names(pattern: str, preferred_key: str = "name") -> set[str]:
    names: set[str] = set()

    for path in sorted(ROOT.glob(pattern)):
        data = load_json(path)
        value = data.get(preferred_key) or data.get("id") or path.stem.split(".")[0]

        if isinstance(value, str) and value.strip():
            names.add(value)

    return names


def require_string(value: object, path: Path, field: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}: {field} must be a non-empty string")
        return None

    return value


def require_unique_string_list(value: object, path: Path, field: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{path}: {field} must be a non-empty list")
        return []

    result: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}: {field}[{index}] must be a non-empty string")
            continue

        if item in seen:
            errors.append(f"{path}: {field}[{index}] '{item}' is duplicated")

        seen.add(item)
        result.append(item)

    return result


def validate_references(
    path: Path,
    field: str,
    values: list[str],
    available: set[str],
    label: str,
    errors: list[str],
) -> None:
    for value in values:
        if value not in available:
            errors.append(f"{path}: bundle {field} references missing {label} '{value}'")


def validate_bundle_file(path: Path) -> list[str]:
    errors: list[str] = []

    try:
        bundle = load_json(path)
    except Exception as exc:
        return [f"{path}: {exc}"]

    name = require_string(bundle.get("name"), path, "name", errors)
    if name is not None and name != expected_bundle_name(path):
        errors.append(
            f"{path}: bundle name '{name}' does not match file name '{expected_bundle_name(path)}'"
        )

    require_string(bundle.get("description"), path, "description", errors)
    require_string(bundle.get("version"), path, "version", errors)

    profile = require_string(bundle.get("profile"), path, "profile", errors)
    workflow = require_string(bundle.get("workflow"), path, "workflow", errors)

    agents = require_unique_string_list(bundle.get("agents"), path, "agents", errors)
    skills = require_unique_string_list(bundle.get("skills"), path, "skills", errors)
    artifacts = require_unique_string_list(bundle.get("artifacts"), path, "artifacts", errors)
    targets = require_unique_string_list(bundle.get("targets"), path, "targets", errors)

    available_profiles = registry_names("registry/profiles/*.profile.json")
    available_workflows = registry_names("registry/workflows/*.workflow.json")
    available_agents = registry_names("registry/agents/*/agent.json")
    available_skills = registry_names("registry/skills/*/skill.json")
    available_artifacts = registry_names("registry/artifacts/*/artifact.json", "type")
    available_targets = registry_names("registry/targets/*/adapter.json")

    if profile is not None and profile not in available_profiles:
        errors.append(f"{path}: bundle profile references missing profile '{profile}'")

    if workflow is not None and workflow not in available_workflows:
        errors.append(f"{path}: bundle workflow references missing workflow '{workflow}'")

    validate_references(path, "agents", agents, available_agents, "agent", errors)
    validate_references(path, "skills", skills, available_skills, "skill", errors)
    validate_references(path, "artifacts", artifacts, available_artifacts, "artifact", errors)
    validate_references(path, "targets", targets, available_targets, "target", errors)

    return errors


def main() -> int:
    bundle_paths = sorted(BUNDLES_DIR.glob("*.bundle.json"))

    if not bundle_paths:
        print(f"FAIL: No bundle registry files found in {BUNDLES_DIR}")
        return 1

    errors: list[str] = []

    for path in bundle_paths:
        errors.extend(validate_bundle_file(path))

    if errors:
        print(f"FAIL: Bundle registry validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Bundle registry is valid. Checked {len(bundle_paths)} bundle file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
