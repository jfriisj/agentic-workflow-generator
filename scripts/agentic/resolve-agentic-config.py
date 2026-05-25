#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
REGISTRY_PATH = ROOT / "registry"
OUTPUT_PATH = ROOT / ".agentic" / "generated" / "resolution.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def registry_agent_path(agent_name: str) -> Path:
    return REGISTRY_PATH / "agents" / agent_name / "agent.json"


def registry_target_path(target_name: str) -> Path:
    return REGISTRY_PATH / "targets" / target_name / "adapter.json"


def registry_artifact_path(artifact_type: str) -> Path:
    return REGISTRY_PATH / "artifacts" / artifact_type / "artifact.json"


def load_artifact_metadata(artifact_type: str) -> dict[str, Any]:
    artifact_path = registry_artifact_path(artifact_type)
    contract = load_json(artifact_path)

    return {
        "type": artifact_type,
        "contractPath": str(artifact_path.relative_to(ROOT)),
        "pathPattern": contract.get("pathPattern"),
        "allowedStatuses": contract.get("allowedStatuses", []),
        "requiredHeadings": contract.get("requiredHeadings", []),
    }


def load_available_skills() -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}

    for skill_file in sorted((REGISTRY_PATH / "skills").glob("*/skill.json")):
        skill = load_json(skill_file)
        name = skill.get("name") or skill_file.parent.name
        skill["_path"] = str(skill_file.relative_to(ROOT))
        skills[name] = skill

    return skills


def capabilities_for_skill(skill: dict[str, Any]) -> list[str]:
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
    seen: set[str] = set()

    for capability in candidates:
        if isinstance(capability, str):
            value = capability.strip()
        elif isinstance(capability, dict):
            raw_value = capability.get("name") or capability.get("id") or capability.get("capability")
            value = str(raw_value).strip() if raw_value is not None else ""
        else:
            value = ""

        if value and value not in seen:
            normalized.append(value)
            seen.add(value)

    return normalized


def resolve_capability(
    capability: str,
    available_skills: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for skill_name in sorted(available_skills):
        skill = available_skills[skill_name]
        if capability in capabilities_for_skill(skill):
            return {
                "capability": capability,
                "skill": skill_name,
                "skillPath": skill["_path"],
            }
    return None


def resolve_agent(
    config_agent: dict[str, Any],
    available_skills: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    agent_name = config_agent["name"]
    agent_file = registry_agent_path(agent_name)

    registry_agent: dict[str, Any] | None = None
    if not agent_file.is_file():
        errors.append(f"Missing registry agent definition: {agent_file.relative_to(ROOT)}")
    else:
        registry_agent = load_json(agent_file)

    resolved_capabilities: list[dict[str, Any]] = []
    missing_capabilities: list[str] = []

    for capability in config_agent.get("capabilities", []):
        resolved = resolve_capability(capability, available_skills)
        if resolved is None:
            missing_capabilities.append(capability)
            errors.append(f"Agent {agent_name} has unresolved capability: {capability}")
        else:
            resolved_capabilities.append(resolved)

    produces: list[dict[str, Any]] = []

    if registry_agent is not None:
        raw_produces = registry_agent.get("produces", [])

        if raw_produces is None:
            raw_produces = []

        if not isinstance(raw_produces, list):
            errors.append(f"{agent_file.relative_to(ROOT)}: produces must be a list")
        else:
            for artifact_type in raw_produces:
                if not isinstance(artifact_type, str) or not artifact_type.strip():
                    errors.append(f"{agent_file.relative_to(ROOT)}: produces entries must be non-empty strings")
                    continue

                artifact_file = registry_artifact_path(artifact_type)
                if not artifact_file.is_file():
                    errors.append(
                        f"Agent {agent_name} produces missing artifact contract: "
                        f"{artifact_file.relative_to(ROOT)}"
                    )
                    continue

                produces.append(load_artifact_metadata(artifact_type))

    return {
        "name": agent_name,
        "role": config_agent.get("role"),
        "registryPath": str(agent_file.relative_to(ROOT)),
        "capabilities": config_agent.get("capabilities", []),
        "resolvedCapabilities": resolved_capabilities,
        "missingCapabilities": missing_capabilities,
        "produces": produces,
    }


def resolve_target(target: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    target_name = target["name"]
    enabled = bool(target.get("enabled", False))
    adapter_file = registry_target_path(target_name)

    if not adapter_file.is_file():
        if enabled:
            errors.append(f"Missing enabled target adapter: {adapter_file.relative_to(ROOT)}")

        return {
            "name": target_name,
            "enabled": enabled,
            "adapterPath": None,
            "missing": True,
        }

    return {
        "name": target_name,
        "enabled": enabled,
        "adapterPath": str(adapter_file.relative_to(ROOT)),
        "missing": False,
    }


def main() -> int:
    config = load_json(CONFIG_PATH)
    available_skills = load_available_skills()
    errors: list[str] = []

    resolved_agents = [
        resolve_agent(config_agent, available_skills, errors)
        for config_agent in config.get("agents", [])
    ]

    resolved_targets = [
        resolve_target(target, errors)
        for target in config.get("targets", [])
    ]

    produced_binding_count = sum(len(agent.get("produces", [])) for agent in resolved_agents)

    resolution = {
        "project": config.get("project", {}),
        "workflow": config.get("workflow", {}),
        "agents": resolved_agents,
        "targets": resolved_targets,
        "summary": {
            "agentCount": len(resolved_agents),
            "targetCount": len(resolved_targets),
            "availableSkillCount": len(available_skills),
            "producedArtifactBindingCount": produced_binding_count,
            "errorCount": len(errors),
            "errors": errors,
        },
    }

    write_json(OUTPUT_PATH, resolution)

    if errors:
        print(f"FAIL: Agentic config resolved with {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        print(f"Wrote resolution to: {OUTPUT_PATH}")
        return 1

    print("PASS: Agentic config resolved successfully.")
    print(f"PASS: Resolved {produced_binding_count} produced artifact binding(s).")
    print(f"Wrote resolution to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
