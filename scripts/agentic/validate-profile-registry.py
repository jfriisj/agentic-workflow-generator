#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
PROFILES_DIR = ROOT / "registry" / "profiles"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def expected_profile_name(path: Path) -> str:
    name = path.name

    if name.endswith(".profile.json"):
        return name.removesuffix(".profile.json")

    return path.stem


def validate_string_list(path: Path, profile: dict[str, Any], key: str) -> list[str]:
    errors: list[str] = []
    value = profile.get(key)

    if value is None:
        return errors

    if not isinstance(value, list):
        return [f"{path}: {key} must be a list when present"]

    for item in value:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}: {key} entries must be non-empty strings")

    return errors


def validate_profile_file(path: Path) -> list[str]:
    errors: list[str] = []

    try:
        profile = load_json(path)
    except Exception as exc:
        return [f"{path}: {exc}"]

    declared_name = profile.get("name") or profile.get("id")
    expected_name = expected_profile_name(path)

    if not isinstance(declared_name, str) or not declared_name.strip():
        errors.append(f"{path}: profile must declare name or id as a non-empty string")
    elif declared_name != expected_name:
        errors.append(
            f"{path}: declared profile name '{declared_name}' does not match file name '{expected_name}'"
        )

    description = profile.get("description")
    if description is not None and not isinstance(description, str):
        errors.append(f"{path}: description must be a string when present")

    for key in [
        "agents",
        "skills",
        "workflows",
        "targets",
        "capabilities",
        "recommendedAgents",
        "recommendedSkills",
        "recommendedWorkflows",
        "recommendedTargets",
    ]:
        errors.extend(validate_string_list(path, profile, key))

    defaults = profile.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        errors.append(f"{path}: defaults must be an object when present")

    return errors


def main() -> int:
    profile_files = sorted(PROFILES_DIR.glob("*.profile.json"))

    if not profile_files:
        print("WARN: No profile registry files found.")
        return 0

    errors: list[str] = []

    for profile_file in profile_files:
        errors.extend(validate_profile_file(profile_file))

    if errors:
        print(f"FAIL: Profile registry validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Profile registry is valid. Checked {len(profile_files)} profile file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
