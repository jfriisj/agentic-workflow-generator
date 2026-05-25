#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
SKILLS_DIR = ROOT / "registry" / "skills"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def extract_capabilities(skill: dict[str, Any]) -> list[str]:
    candidates: list[Any] = []

    for key in [
        "capabilities",
        "provides",
        "providedCapabilities",
        "provided_capabilities",
    ]:
        value = skill.get(key)

        if isinstance(value, list):
            candidates.extend(value)

        if isinstance(value, dict):
            nested = value.get("capabilities")
            if isinstance(nested, list):
                candidates.extend(nested)

    single_capability = skill.get("capability")
    if isinstance(single_capability, str):
        candidates.append(single_capability)

    normalized: list[str] = []

    for capability in candidates:
        if isinstance(capability, str) and capability.strip():
            normalized.append(capability.strip())
        elif isinstance(capability, dict):
            raw_value = capability.get("name") or capability.get("id") or capability.get("capability")
            if raw_value is not None and str(raw_value).strip():
                normalized.append(str(raw_value).strip())

    return normalized


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_json = skill_dir / "skill.json"
    skill_md = skill_dir / "SKILL.md"
    folder_name = skill_dir.name

    if not skill_json.is_file():
        errors.append(f"{skill_dir}: missing skill.json")
        return errors

    if not skill_md.is_file():
        errors.append(f"{skill_dir}: missing SKILL.md")

    try:
        skill = load_json(skill_json)
    except Exception as exc:
        return [f"{skill_json}: {exc}"]

    name = skill.get("name")
    if name is not None:
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{skill_json}: name must be a non-empty string when present")
        elif name != folder_name:
            errors.append(f"{skill_json}: name '{name}' does not match folder '{folder_name}'")

    capabilities = extract_capabilities(skill)
    if not capabilities:
        errors.append(
            f"{skill_json}: must declare at least one capability using capabilities, provides, "
            "providedCapabilities, provided_capabilities, or capability"
        )

    duplicate_capabilities = sorted(
        capability for capability in set(capabilities) if capabilities.count(capability) > 1
    )

    if duplicate_capabilities:
        errors.append(
            f"{skill_json}: duplicate capabilities: {', '.join(duplicate_capabilities)}"
        )

    return errors


def main() -> int:
    skill_dirs = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())

    if not skill_dirs:
        print("WARN: No skill directories found.")
        return 0

    errors: list[str] = []

    for skill_dir in skill_dirs:
        errors.extend(validate_skill_dir(skill_dir))

    if errors:
        print(f"FAIL: Skill registry validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Skill registry is valid. Checked {len(skill_dirs)} skill directorie(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
