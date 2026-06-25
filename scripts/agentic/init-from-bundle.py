#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def require_string(data: dict[str, Any], field: str, path: Path) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {field} must be a non-empty string")
    return value


def require_string_list(data: dict[str, Any], field: str, path: Path) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path}: {field} must be a non-empty list")

    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{path}: {field}[{index}] must be a non-empty string")
        result.append(item)

    return result


def load_bundle(bundle_name: str) -> tuple[Path, dict[str, Any]]:
    path = ROOT / "registry" / "bundles" / f"{bundle_name}.bundle.json"
    if not path.is_file():
        raise ValueError(f"Unknown bundle '{bundle_name}'")

    bundle = load_json(path)
    actual_name = require_string(bundle, "name", path)
    if actual_name != bundle_name:
        raise ValueError(f"{path}: bundle name '{actual_name}' does not match requested bundle '{bundle_name}'")

    return path, bundle


def load_registry_object(path: Path, expected_name: str, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"Bundle references missing {label} '{expected_name}'")

    data = load_json(path)
    actual_name = data.get("name") or data.get("type") or data.get("id")
    if actual_name != expected_name:
        raise ValueError(f"{path}: {label} name '{actual_name}' does not match expected '{expected_name}'")

    return data


def load_agent(agent_name: str) -> dict[str, Any]:
    return load_registry_object(ROOT / "registry" / "agents" / agent_name / "agent.json", agent_name, "agent")


def load_artifact(artifact_type: str) -> dict[str, Any]:
    return load_registry_object(ROOT / "registry" / "artifacts" / artifact_type / "artifact.json", artifact_type, "artifact")


def load_workflow(workflow_name: str) -> dict[str, Any]:
    return load_registry_object(ROOT / "registry" / "workflows" / f"{workflow_name}.workflow.json", workflow_name, "workflow")


def existing_config_or_default() -> dict[str, Any]:
    if CONFIG_PATH.is_file():
        return load_json(CONFIG_PATH)

    return {
        "$schema": "./schemas/agentic.schema.json",
        "project": {
            "name": ROOT.name,
            "type": "agentic-project",
            "description": f"Generated agentic configuration for {ROOT.name}.",
            "languageProfiles": [],
            "runtimeProfiles": [],
            "architectureProfile": "generated-from-bundle",
        },
        "generator": {
            "name": "agentic-gen",
            "version": "0.1.0",
            "mode": "compiler",
            "runtimeExecution": False,
        },
        "permissionProfiles": [
            {"name": "read-only", "read": True, "write": False, "edit": False, "bash": "deny"},
            {"name": "implementation", "read": True, "write": True, "edit": True, "bash": "allow"},
            {"name": "test-runner", "read": True, "write": True, "edit": True, "bash": "limited"},
        ],
        "runtimeContext": {
            "enabled": True,
            "outputDirectory": ".runtime/context",
            "resolutionDirectory": ".runtime/resolution",
            "failIfMissing": True,
        },
        "validation": {
            "failClosed": True,
            "requireLockfile": True,
            "requireArtifacts": True,
            "requireEvidence": True,
        },
    }


def materialize_targets(existing_targets: list[Any], bundle_targets: list[str]) -> list[dict[str, Any]]:
    existing_by_name: dict[str, dict[str, Any]] = {}

    for item in existing_targets:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            existing_by_name[item["name"]] = dict(item)

    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    ordered_names = list(existing_by_name)
    for target in bundle_targets:
        if target not in ordered_names:
            ordered_names.append(target)

    for index, target in enumerate(ordered_names, start=1):
        item = existing_by_name.get(target, {"name": target, "enabled": False, "priority": index})
        item["enabled"] = target in bundle_targets
        if not isinstance(item.get("priority"), int):
            item["priority"] = index
        result.append(item)
        seen.add(target)

    return result


def materialize_agents(agent_names: list[str]) -> list[dict[str, Any]]:
    agents: list[dict[str, Any]] = []

    for agent_name in agent_names:
        agent = load_agent(agent_name)
        permission_profile = agent.get("defaultPermissionProfile")
        if not isinstance(permission_profile, str) or not permission_profile.strip():
            permission_profile = "read-only"

        capabilities = agent.get("capabilities")
        must_not = agent.get("mustNot")

        agents.append(
            {
                "name": require_string(agent, "name", ROOT / "registry" / "agents" / agent_name / "agent.json"),
                "role": require_string(agent, "role", ROOT / "registry" / "agents" / agent_name / "agent.json"),
                "description": require_string(agent, "description", ROOT / "registry" / "agents" / agent_name / "agent.json"),
                "permissionProfile": permission_profile,
                "capabilities": capabilities if isinstance(capabilities, list) else [],
                "mustNot": must_not if isinstance(must_not, list) else [],
            }
        )

    return agents


def transitions_by_state_and_event(workflow: dict[str, Any]) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}

    transitions = workflow.get("transitions")
    if not isinstance(transitions, list):
        return result

    for transition in transitions:
        if not isinstance(transition, dict):
            continue

        from_state = transition.get("from")
        to_state = transition.get("to")
        event = transition.get("on")

        if isinstance(from_state, str) and isinstance(to_state, str) and isinstance(event, str):
            result[(from_state, event)] = to_state

    return result


def first_produced_artifact(agent: dict[str, Any], agent_name: str) -> str:
    produces = agent.get("produces")
    if isinstance(produces, list) and len(produces) == 1 and isinstance(produces[0], str) and produces[0].strip():
        return produces[0]

    raise ValueError(f"Agent '{agent_name}' must produce exactly one artifact to generate a gate")


def materialize_gates(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    states = workflow.get("states")
    if not isinstance(states, list):
        raise ValueError("workflow states must be a list")

    route_by_state_event = transitions_by_state_and_event(workflow)
    blocked_route = workflow.get("defaultFailureRoute")
    if not isinstance(blocked_route, str) or not blocked_route.strip():
        blocked_route = "Orchestrator"

    gates: list[dict[str, Any]] = []

    for state in states:
        if not isinstance(state, dict) or state.get("terminal") is True:
            continue

        state_name = state.get("name")
        agent_name = state.get("agent")
        gate_name = state.get("gate")

        if not isinstance(state_name, str) or not isinstance(agent_name, str) or not isinstance(gate_name, str):
            continue

        agent = load_agent(agent_name)
        artifact_type = first_produced_artifact(agent, agent_name)
        artifact = load_artifact(artifact_type)

        path_pattern = artifact.get("pathPattern")
        if not isinstance(path_pattern, str) or not path_pattern.strip():
            path_pattern = f"agent-output/{artifact_type}/*.md"

        capabilities = agent.get("capabilities")
        required_capabilities = capabilities if isinstance(capabilities, list) else []

        gates.append(
            {
                "name": gate_name,
                "owner": agent_name,
                "requiredCapabilities": required_capabilities,
                "requiredArtifacts": [
                    {
                        "type": artifact_type,
                        "pathPattern": path_pattern,
                    }
                ],
                "passRoute": route_by_state_event.get((state_name, "pass"), blocked_route),
                "failRoute": route_by_state_event.get((state_name, "fail"), blocked_route),
                "blockedRoute": blocked_route,
                "blocking": True,
            }
        )

    if not gates:
        raise ValueError("Bundle workflow produced no gates")

    return gates


def materialize_config(bundle_name: str) -> dict[str, Any]:
    bundle_path, bundle = load_bundle(bundle_name)

    workflow_name = require_string(bundle, "workflow", bundle_path)
    bundle_targets = require_string_list(bundle, "targets", bundle_path)
    bundle_agents = require_string_list(bundle, "agents", bundle_path)

    workflow = load_workflow(workflow_name)

    existing = existing_config_or_default()

    generated = {
        "$schema": existing.get("$schema", "./schemas/agentic.schema.json"),
        "project": existing["project"],
        "generator": existing["generator"],
        "targets": materialize_targets(existing.get("targets", []), bundle_targets),
        "workflow": {
            "profile": workflow_name,
            "startState": require_string(workflow, "startState", ROOT / "registry" / "workflows" / f"{workflow_name}.workflow.json"),
            "terminalStates": require_string_list(workflow, "terminalStates", ROOT / "registry" / "workflows" / f"{workflow_name}.workflow.json"),
            "failClosed": bool(workflow.get("failClosed", True)),
        },
        "permissionProfiles": existing["permissionProfiles"],
        "agents": materialize_agents(bundle_agents),
        "gates": materialize_gates(workflow),
        "runtimeContext": existing["runtimeContext"],
        "validation": existing["validation"],
    }

    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize .agentic/agentic.json from a registered bundle.")
    parser.add_argument("--bundle", required=True, help="Bundle name, for example: orchestrated-delivery")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        config = materialize_config(args.bundle)
        write_json(CONFIG_PATH, config)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"PASS: Initialized .agentic/agentic.json from bundle '{args.bundle}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
