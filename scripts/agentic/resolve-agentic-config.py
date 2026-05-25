#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
REGISTRY_PATH = ROOT / "registry"
OUTPUT_PATH = ROOT / ".agentic" / "generated" / "resolution.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: File not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: Invalid JSON in {path}: {exc}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def load_registry_skills() -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}

    for skill_file in sorted((REGISTRY_PATH / "skills").glob("*/skill.json")):
        skill = load_json(skill_file)
        name = skill.get("name")

        if not name:
            raise SystemExit(f"ERROR: Skill has no name: {skill_file}")

        if name in skills:
            raise SystemExit(f"ERROR: Duplicate skill name: {name}")

        skill["_registryPath"] = str(skill_file.relative_to(ROOT))
        skills[name] = skill

    return skills


def load_target_adapters() -> dict[str, dict[str, Any]]:
    adapters: dict[str, dict[str, Any]] = {}

    for adapter_file in sorted((REGISTRY_PATH / "targets").glob("*/adapter.json")):
        adapter = load_json(adapter_file)
        name = adapter.get("name")

        if not name:
            raise SystemExit(f"ERROR: Target adapter has no name: {adapter_file}")

        if name in adapters:
            raise SystemExit(f"ERROR: Duplicate target adapter name: {name}")

        adapter["_registryPath"] = str(adapter_file.relative_to(ROOT))
        adapters[name] = adapter

    return adapters


def build_capability_index(skills: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}

    for skill_name, skill in skills.items():
        for capability in skill.get("provides", []):
            index.setdefault(capability, []).append(
                {
                    "skill": skill_name,
                    "version": skill.get("version"),
                    "path": skill.get("_registryPath"),
                    "contentPath": skill.get("contentPath"),
                    "allowedAgents": skill.get("allowedAgents", []),
                    "contextBudget": skill.get("contextBudget", {})
                }
            )

    return index


def resolve_agent_capabilities(
    config: dict[str, Any],
    capability_index: dict[str, list[dict[str, Any]]]
) -> tuple[list[dict[str, Any]], list[str]]:
    resolved_agents: list[dict[str, Any]] = []
    errors: list[str] = []

    for agent in config.get("agents", []):
        agent_name = agent.get("name")
        requested_capabilities = agent.get("capabilities", [])
        resolved_capabilities: list[dict[str, Any]] = []

        for capability in requested_capabilities:
            candidates = capability_index.get(capability, [])

            allowed_candidates = [
                candidate
                for candidate in candidates
                if not candidate.get("allowedAgents")
                or agent_name in candidate.get("allowedAgents", [])
            ]

            if not candidates:
                errors.append(
                    f"Agent '{agent_name}' requires capability '{capability}', "
                    f"but no skill provides it."
                )
                continue

            if not allowed_candidates:
                errors.append(
                    f"Agent '{agent_name}' requires capability '{capability}', "
                    f"but no providing skill allows this agent."
                )
                continue

            if len(allowed_candidates) > 1:
                errors.append(
                    f"Agent '{agent_name}' capability '{capability}' resolved to multiple skills: "
                    + ", ".join(candidate["skill"] for candidate in allowed_candidates)
                )
                continue

            resolved = allowed_candidates[0]
            resolved_capabilities.append(
                {
                    "capability": capability,
                    "skill": resolved["skill"],
                    "version": resolved["version"],
                    "skillPath": resolved["path"],
                    "contentPath": resolved["contentPath"],
                    "contextBudget": resolved["contextBudget"]
                }
            )

        resolved_agents.append(
            {
                "name": agent_name,
                "role": agent.get("role"),
                "permissionProfile": agent.get("permissionProfile"),
                "resolvedCapabilities": resolved_capabilities,
                "unresolvedCapabilities": [
                    capability
                    for capability in requested_capabilities
                    if capability not in [
                        item["capability"] for item in resolved_capabilities
                    ]
                ]
            }
        )

    return resolved_agents, errors


def validate_targets(
    config: dict[str, Any],
    adapters: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    resolved_targets: list[dict[str, Any]] = []
    errors: list[str] = []

    for target in config.get("targets", []):
        target_name = target.get("name")
        enabled = target.get("enabled", False)

        adapter = adapters.get(target_name)

        if enabled and adapter is None:
            errors.append(
                f"Target '{target_name}' is enabled, but no adapter exists in registry."
            )
            continue

        resolved_targets.append(
            {
                "name": target_name,
                "enabled": enabled,
                "priority": target.get("priority"),
                "adapterPath": adapter.get("_registryPath") if adapter else None,
                "supportedFeatures": adapter.get("supportedFeatures", {}) if adapter else {}
            }
        )

    return resolved_targets, errors


def main() -> int:
    config = load_json(CONFIG_PATH)
    skills = load_registry_skills()
    adapters = load_target_adapters()
    capability_index = build_capability_index(skills)

    resolved_agents, capability_errors = resolve_agent_capabilities(config, capability_index)
    resolved_targets, target_errors = validate_targets(config, adapters)

    errors = capability_errors + target_errors

    resolution = {
        "project": config.get("project", {}),
        "generator": config.get("generator", {}),
        "workflow": config.get("workflow", {}),
        "summary": {
            "agentCount": len(config.get("agents", [])),
            "skillCount": len(skills),
            "targetAdapterCount": len(adapters),
            "enabledTargetCount": len(
                [target for target in config.get("targets", []) if target.get("enabled")]
            ),
            "errorCount": len(errors)
        },
        "targets": resolved_targets,
        "agents": resolved_agents,
        "capabilityIndex": capability_index,
        "errors": errors
    }

    write_json(OUTPUT_PATH, resolution)

    if errors:
        print(f"FAIL: Resolution completed with {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        print(f"Wrote partial resolution to: {OUTPUT_PATH}")
        return 1

    print("PASS: Agentic config resolved successfully.")
    print(f"Wrote resolution to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
