#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
AGENTS_DIR = ROOT / "registry" / "agents"
ARTIFACTS_DIR = ROOT / "registry" / "artifacts"
SKILLS_DIR = ROOT / "registry" / "skills"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data



def collect_skill_capabilities() -> set[str]:
    capabilities: set[str] = set()

    for path in sorted(SKILLS_DIR.glob("*/skill.json")):
        try:
            skill = load_json(path)
        except Exception:
            continue

        provides = skill.get("provides")
        if not isinstance(provides, list):
            continue

        for capability in provides:
            if isinstance(capability, str) and capability.strip():
                capabilities.add(capability)

    return capabilities


def validate_artifact_reference_list(
    path: Path,
    agent: dict[str, Any],
    key: str,
) -> list[str]:
    errors: list[str] = []
    values = agent.get(key)

    if values is None:
        return errors

    if not isinstance(values, list):
        return [f"{path}: {key} must be a list when present"]

    seen_values: set[str] = set()

    for artifact_type in values:
        if not isinstance(artifact_type, str) or not artifact_type.strip():
            errors.append(f"{path}: {key} entries must be non-empty strings")
            continue

        if artifact_type in seen_values:
            errors.append(f"{path}: {key} entry '{artifact_type}' is duplicated")

        seen_values.add(artifact_type)

        if not artifact_exists(artifact_type):
            errors.append(
                f"{path}: {key} missing artifact contract: "
                f"registry/artifacts/{artifact_type}/artifact.json"
            )

    return errors

def artifact_exists(artifact_type: str) -> bool:
    return (ARTIFACTS_DIR / artifact_type / "artifact.json").is_file()


def validate_agent_file(path: Path, skill_capabilities: set[str]) -> list[str]:
    errors: list[str] = []
    folder_name = path.parent.name

    try:
        agent = load_json(path)
    except Exception as exc:
        return [f"{path}: {exc}"]

    name = agent.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{path}: name must be a non-empty string")
    elif name != folder_name:
        errors.append(f"{path}: name '{name}' does not match folder '{folder_name}'")

    role = agent.get("role")
    if not isinstance(role, str) or not role.strip():
        errors.append(f"{path}: role must be a non-empty string")

    description = agent.get("description")
    if description is not None and not isinstance(description, str):
        errors.append(f"{path}: description must be a string when present")

    default_permission_profile = agent.get("defaultPermissionProfile")
    if not isinstance(default_permission_profile, str) or not default_permission_profile.strip():
        errors.append(f"{path}: defaultPermissionProfile must be a non-empty string")

    permission_profile = agent.get("permissionProfile")
    if permission_profile is not None and not isinstance(permission_profile, str):
        errors.append(f"{path}: permissionProfile must be a string when present")

    version = agent.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append(f"{path}: version must be a non-empty string")

    capabilities = agent.get("capabilities")
    if capabilities is not None:
        if not isinstance(capabilities, list):
            errors.append(f"{path}: capabilities must be a list when present")
        else:
            seen_capabilities: set[str] = set()

            for capability in capabilities:
                if not isinstance(capability, str) or not capability.strip():
                    errors.append(f"{path}: capabilities entries must be non-empty strings")
                    continue

                if capability in seen_capabilities:
                    errors.append(f"{path}: capabilities entry '{capability}' is duplicated")

                seen_capabilities.add(capability)

                if capability not in skill_capabilities:
                    errors.append(
                        f"{path}: capabilities entry '{capability}' must be provided by a registered skill"
                    )

    errors.extend(validate_artifact_reference_list(path, agent, "produces"))
    errors.extend(validate_artifact_reference_list(path, agent, "requiredArtifacts"))

    return errors


def main() -> int:
    agent_files = sorted(AGENTS_DIR.glob("*/agent.json"))

    if not agent_files:
        print("WARN: No agent registry files found.")
        return 0

    errors: list[str] = []
    skill_capabilities = collect_skill_capabilities()

    for agent_file in agent_files:
        errors.extend(validate_agent_file(agent_file, skill_capabilities))

    if errors:
        print(f"FAIL: Agent registry validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Agent registry is valid. Checked {len(agent_files)} agent file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
