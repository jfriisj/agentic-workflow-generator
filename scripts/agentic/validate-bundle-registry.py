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


def registry_items(pattern: str, preferred_key: str = "name") -> dict[str, tuple[Path, dict[str, Any]]]:
    items: dict[str, tuple[Path, dict[str, Any]]] = {}

    for path in sorted(ROOT.glob(pattern)):
        data = load_json(path)
        value = data.get(preferred_key) or data.get("id") or path.stem.split(".")[0]

        if isinstance(value, str) and value.strip():
            items[value] = (path, data)

    return items


def registry_items_by_parent_folder(pattern: str) -> dict[str, tuple[Path, dict[str, Any]]]:
    items: dict[str, tuple[Path, dict[str, Any]]] = {}

    for path in sorted(ROOT.glob(pattern)):
        data = load_json(path)
        items[path.parent.name] = (path, data)

    return items


def registry_names(pattern: str, preferred_key: str = "name") -> set[str]:
    return set(registry_items(pattern, preferred_key))


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


def optional_string_list(data: dict[str, Any], field: str) -> list[str]:
    value = data.get(field)

    if not isinstance(value, list):
        return []

    return [item for item in value if isinstance(item, str) and item.strip()]


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


def validate_workflow_is_covered_by_bundle_agents(
    path: Path,
    workflow: str,
    workflow_data: dict[str, Any],
    bundle_agents: set[str],
    errors: list[str],
) -> None:
    states = workflow_data.get("states")
    if not isinstance(states, list):
        return

    for index, state in enumerate(states):
        if not isinstance(state, dict):
            continue

        if state.get("terminal") is True:
            continue

        state_name = state.get("name")
        agent = state.get("agent")

        if isinstance(agent, str) and agent.strip() and agent not in bundle_agents:
            errors.append(
                f"{path}: bundle workflow '{workflow}' state '{state_name or index}' "
                f"uses agent '{agent}' not included in bundle agents"
            )


def validate_workflow_transitions_are_inside_workflow(
    path: Path,
    workflow: str,
    workflow_data: dict[str, Any],
    errors: list[str],
) -> None:
    states = workflow_data.get("states")
    transitions = workflow_data.get("transitions")

    if not isinstance(states, list) or not isinstance(transitions, list):
        return

    state_names = {
        state.get("name")
        for state in states
        if isinstance(state, dict) and isinstance(state.get("name"), str) and state.get("name").strip()
    }

    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            continue

        from_state = transition.get("from")
        to_state = transition.get("to")

        if isinstance(from_state, str) and from_state not in state_names:
            errors.append(
                f"{path}: workflow transition[{index}] from state '{from_state}' "
                f"is not defined in bundle workflow '{workflow}'"
            )

        if isinstance(to_state, str) and to_state not in state_names:
            errors.append(
                f"{path}: workflow transition[{index}] to state '{to_state}' "
                f"is not defined in bundle workflow '{workflow}'"
            )


def validate_agent_capabilities_are_covered_by_bundle_skills(
    path: Path,
    agents: list[str],
    skills: list[str],
    agent_registry: dict[str, tuple[Path, dict[str, Any]]],
    skill_registry: dict[str, tuple[Path, dict[str, Any]]],
    errors: list[str],
) -> None:
    provided_capabilities: set[str] = set()

    for skill in skills:
        item = skill_registry.get(skill)
        if item is None:
            continue

        _, skill_data = item
        provided_capabilities.update(optional_string_list(skill_data, "provides"))

    for agent in agents:
        item = agent_registry.get(agent)
        if item is None:
            continue

        _, agent_data = item
        for capability in optional_string_list(agent_data, "capabilities"):
            if capability not in provided_capabilities:
                errors.append(
                    f"{path}: bundle agent '{agent}' capability '{capability}' "
                    "is not provided by bundle skills"
                )


def validate_agent_artifacts_are_included_in_bundle_artifacts(
    path: Path,
    agents: list[str],
    artifacts: set[str],
    agent_registry: dict[str, tuple[Path, dict[str, Any]]],
    errors: list[str],
) -> None:
    for agent in agents:
        item = agent_registry.get(agent)
        if item is None:
            continue

        _, agent_data = item
        for artifact in optional_string_list(agent_data, "produces"):
            if artifact not in artifacts:
                errors.append(
                    f"{path}: bundle agent '{agent}' produces artifact '{artifact}' "
                    "not included in bundle artifacts"
                )


def validate_profile_matches_bundle_workflow(
    path: Path,
    profile: str | None,
    workflow: str | None,
    profile_registry: dict[str, tuple[Path, dict[str, Any]]],
    errors: list[str],
) -> None:
    if profile is None or workflow is None:
        return

    item = profile_registry.get(profile)
    if item is None:
        return

    _, profile_data = item
    profile_workflow = profile_data.get("workflow")

    if not isinstance(profile_workflow, str) or not profile_workflow.strip():
        errors.append(f"{path}: bundle profile '{profile}' workflow must be a non-empty string")
        return

    if profile_workflow != workflow:
        errors.append(
            f"{path}: bundle profile '{profile}' workflow '{profile_workflow}' "
            f"does not match bundle workflow '{workflow}'"
        )


def validate_targets_match_adapters(
    path: Path,
    targets: list[str],
    target_registry: dict[str, tuple[Path, dict[str, Any]]],
    errors: list[str],
) -> None:
    for target in targets:
        item = target_registry.get(target)
        if item is None:
            continue

        target_path, target_data = item
        adapter_name = target_data.get("name")

        if not isinstance(adapter_name, str) or not adapter_name.strip():
            errors.append(f"{path}: bundle target '{target}' adapter {target_path} name must be a non-empty string")
            continue

        if adapter_name != target:
            errors.append(
                f"{path}: bundle target '{target}' resolves to adapter named '{adapter_name}'"
            )


def validate_bundle_composition(
    path: Path,
    profile: str | None,
    workflow: str | None,
    agents: list[str],
    skills: list[str],
    artifacts: list[str],
    targets: list[str],
    profile_registry: dict[str, tuple[Path, dict[str, Any]]],
    workflow_registry: dict[str, tuple[Path, dict[str, Any]]],
    agent_registry: dict[str, tuple[Path, dict[str, Any]]],
    skill_registry: dict[str, tuple[Path, dict[str, Any]]],
    target_registry: dict[str, tuple[Path, dict[str, Any]]],
    errors: list[str],
) -> None:
    if workflow is not None:
        workflow_item = workflow_registry.get(workflow)
        if workflow_item is not None:
            _, workflow_data = workflow_item
            validate_workflow_is_covered_by_bundle_agents(path, workflow, workflow_data, set(agents), errors)
            validate_workflow_transitions_are_inside_workflow(path, workflow, workflow_data, errors)

    validate_agent_capabilities_are_covered_by_bundle_skills(
        path,
        agents,
        skills,
        agent_registry,
        skill_registry,
        errors,
    )
    validate_agent_artifacts_are_included_in_bundle_artifacts(
        path,
        agents,
        set(artifacts),
        agent_registry,
        errors,
    )
    validate_profile_matches_bundle_workflow(path, profile, workflow, profile_registry, errors)
    validate_targets_match_adapters(path, targets, target_registry, errors)


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

    profile_registry = registry_items("registry/profiles/*.profile.json")
    workflow_registry = registry_items("registry/workflows/*.workflow.json")
    agent_registry = registry_items("registry/agents/*/agent.json")
    skill_registry = registry_items("registry/skills/*/skill.json")
    target_registry = registry_items_by_parent_folder("registry/targets/*/adapter.json")

    available_profiles = set(profile_registry)
    available_workflows = set(workflow_registry)
    available_agents = set(agent_registry)
    available_skills = set(skill_registry)
    available_artifacts = registry_names("registry/artifacts/*/artifact.json", "type")
    available_targets = set(target_registry)

    if profile is not None and profile not in available_profiles:
        errors.append(f"{path}: bundle profile references missing profile '{profile}'")

    if workflow is not None and workflow not in available_workflows:
        errors.append(f"{path}: bundle workflow references missing workflow '{workflow}'")

    validate_references(path, "agents", agents, available_agents, "agent", errors)
    validate_references(path, "skills", skills, available_skills, "skill", errors)
    validate_references(path, "artifacts", artifacts, available_artifacts, "artifact", errors)
    validate_references(path, "targets", targets, available_targets, "target", errors)

    validate_bundle_composition(
        path,
        profile,
        workflow,
        agents,
        skills,
        artifacts,
        targets,
        profile_registry,
        workflow_registry,
        agent_registry,
        skill_registry,
        target_registry,
        errors,
    )

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
