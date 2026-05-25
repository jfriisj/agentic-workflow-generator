#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
RESOLUTION_PATH = ROOT / ".agentic" / "generated" / "resolution.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def walk_for_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []

    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"

            if key in {"errors", "unresolved", "missing", "missingCapabilities"}:
                if isinstance(nested, list) and nested:
                    errors.append(f"{nested_path}: expected empty list, found {len(nested)} item(s)")
                elif isinstance(nested, dict) and nested:
                    errors.append(f"{nested_path}: expected empty object, found {len(nested)} item(s)")

            errors.extend(walk_for_errors(nested, nested_path))

    elif isinstance(value, list):
        for index, nested in enumerate(value):
            errors.extend(walk_for_errors(nested, f"{path}[{index}]"))

    return errors


def has_non_empty_list(resolution: dict[str, Any], key: str) -> bool:
    value = resolution.get(key)
    return isinstance(value, list) and bool(value)


def validate_agent_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    agents = resolution.get("agents")

    if not isinstance(agents, list) or not agents:
        return [f"{RESOLUTION_PATH}: expected non-empty 'agents' collection"]

    for index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            errors.append(f"{RESOLUTION_PATH}: agents[{index}] must be an object")
            continue

        agent_name = agent.get("name", f"agents[{index}]")

        capabilities = agent.get("capabilities")
        if not isinstance(capabilities, list):
            errors.append(f"{RESOLUTION_PATH}: {agent_name}: capabilities must be a list")
            continue

        missing_capabilities = agent.get("missingCapabilities")
        if isinstance(missing_capabilities, list) and missing_capabilities:
            errors.append(
                f"{RESOLUTION_PATH}: {agent_name}: missingCapabilities must be empty, "
                f"found {len(missing_capabilities)} item(s)"
            )
        elif missing_capabilities is not None and not isinstance(missing_capabilities, list):
            errors.append(f"{RESOLUTION_PATH}: {agent_name}: missingCapabilities must be a list")

        resolved_capabilities = agent.get("resolvedCapabilities")
        if not isinstance(resolved_capabilities, list):
            errors.append(f"{RESOLUTION_PATH}: {agent_name}: resolvedCapabilities must be a list")
            continue

        capability_names = {
            capability
            for capability in capabilities
            if isinstance(capability, str) and capability.strip()
        }

        resolved_names: set[str] = set()

        for resolved_index, resolved in enumerate(resolved_capabilities):
            if not isinstance(resolved, dict):
                errors.append(
                    f"{RESOLUTION_PATH}: {agent_name}: "
                    f"resolvedCapabilities[{resolved_index}] must be an object"
                )
                continue

            capability = resolved.get("capability")
            skill = resolved.get("skill")
            skill_path = resolved.get("skillPath")

            if not isinstance(capability, str) or not capability.strip():
                errors.append(
                    f"{RESOLUTION_PATH}: {agent_name}: "
                    f"resolvedCapabilities[{resolved_index}].capability must be a non-empty string"
                )
                continue

            resolved_names.add(capability)

            if not isinstance(skill, str) or not skill.strip():
                errors.append(
                    f"{RESOLUTION_PATH}: {agent_name}: "
                    f"resolvedCapabilities[{resolved_index}].skill must be a non-empty string"
                )

            if not isinstance(skill_path, str) or not skill_path.strip():
                errors.append(
                    f"{RESOLUTION_PATH}: {agent_name}: "
                    f"resolvedCapabilities[{resolved_index}].skillPath must be a non-empty string"
                )

        unresolved = sorted(capability_names - resolved_names)
        if unresolved:
            errors.append(
                f"{RESOLUTION_PATH}: {agent_name}: unresolved capabilities: "
                f"{', '.join(unresolved)}"
            )

    return errors


def main() -> int:
    errors: list[str] = []

    try:
        resolution = load_json(RESOLUTION_PATH)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    for required_key in ["agents", "targets"]:
        if not has_non_empty_list(resolution, required_key):
            errors.append(f"{RESOLUTION_PATH}: expected non-empty '{required_key}' collection")

    errors.extend(validate_agent_resolution(resolution))

    errors.extend(walk_for_errors(resolution))

    if errors:
        print(f"FAIL: Resolution output validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Resolution output is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
