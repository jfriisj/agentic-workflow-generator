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


def is_plain_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


CONFIG_PATH = Path(".agentic") / "agentic.json"


def target_identity_projection(targets: Any) -> Any:
    if not isinstance(targets, list):
        return targets

    projected_targets: list[Any] = []
    for target in targets:
        if not isinstance(target, dict):
            projected_targets.append(target)
            continue

        projected_targets.append(
            {
                "name": target.get("name"),
                "enabled": target.get("enabled"),
            }
        )

    return projected_targets


def validate_config_resolution_consistency(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    try:
        config = load_json(CONFIG_PATH)
    except Exception as exc:
        return [f"{CONFIG_PATH}: failed to load agentic config: {exc}"]

    config_project = config.get("project")
    resolution_project = resolution.get("project")
    if isinstance(config_project, dict) and isinstance(resolution_project, dict):
        if config_project != resolution_project:
            errors.append(f"{RESOLUTION_PATH}: project must match {CONFIG_PATH}: project")

    config_workflow = config.get("workflow")
    resolution_workflow = resolution.get("workflow")
    if isinstance(config_workflow, dict) and isinstance(resolution_workflow, dict):
        if config_workflow != resolution_workflow:
            errors.append(f"{RESOLUTION_PATH}: workflow must match {CONFIG_PATH}: workflow")

    config_targets = config.get("targets")
    resolution_targets = resolution.get("targets")
    if isinstance(config_targets, list) and isinstance(resolution_targets, list):
        if target_identity_projection(config_targets) != target_identity_projection(resolution_targets):
            errors.append(
                f"{RESOLUTION_PATH}: target name/enabled projection must match {CONFIG_PATH}: targets"
            )

    return errors


def validate_reference_paths_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    agents = resolution.get("agents")
    if isinstance(agents, list):
        for agent_index, agent in enumerate(agents):
            if not isinstance(agent, dict):
                continue

            registry_path = agent.get("registryPath")
            if (
                isinstance(registry_path, str)
                and registry_path.strip()
                and is_safe_relative_path(registry_path)
                and not Path(registry_path).is_file()
            ):
                errors.append(
                    f"{RESOLUTION_PATH}: agents[{agent_index}].registryPath "
                    "must point to an existing file"
                )

            produces = agent.get("produces")
            if not isinstance(produces, list):
                continue

            for produce_index, produce in enumerate(produces):
                if not isinstance(produce, dict):
                    continue

                contract_path = produce.get("contractPath")
                if (
                    isinstance(contract_path, str)
                    and contract_path.strip()
                    and is_safe_relative_path(contract_path)
                    and not Path(contract_path).is_file()
                ):
                    errors.append(
                        f"{RESOLUTION_PATH}: agents[{agent_index}].produces[{produce_index}]."
                        "contractPath must point to an existing file"
                    )

    targets = resolution.get("targets")
    if isinstance(targets, list):
        for target_index, target in enumerate(targets):
            if not isinstance(target, dict):
                continue

            missing = target.get("missing")
            adapter_path = target.get("adapterPath")

            if missing is False and (
                isinstance(adapter_path, str)
                and adapter_path.strip()
                and is_safe_relative_path(adapter_path)
                and not Path(adapter_path).is_file()
            ):
                errors.append(
                    f"{RESOLUTION_PATH}: targets[{target_index}].adapterPath "
                    "must point to an existing file"
                )

    return errors


def validate_target_semantics_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    targets = resolution.get("targets")

    if not isinstance(targets, list):
        return errors

    seen_target_names: set[str] = set()

    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            continue

        name = target.get("name")
        if isinstance(name, str) and name.strip():
            if name in seen_target_names:
                errors.append(f"{RESOLUTION_PATH}: targets[{index}].name is duplicated")
            seen_target_names.add(name)

        enabled = target.get("enabled")
        missing = target.get("missing")
        adapter_path = target.get("adapterPath")

        if not isinstance(enabled, bool):
            errors.append(f"{RESOLUTION_PATH}: targets[{index}].enabled must be a boolean")

        if not isinstance(missing, bool):
            errors.append(f"{RESOLUTION_PATH}: targets[{index}].missing must be a boolean")
            continue

        if missing:
            if enabled is not False:
                errors.append(
                    f"{RESOLUTION_PATH}: targets[{index}] must have enabled=false when missing=true"
                )

            if adapter_path is not None:
                errors.append(
                    f"{RESOLUTION_PATH}: targets[{index}].adapterPath must be null when missing=true"
                )
        else:
            if enabled is not True:
                errors.append(
                    f"{RESOLUTION_PATH}: targets[{index}] must have enabled=true when missing=false"
                )

            if not isinstance(adapter_path, str) or not adapter_path.strip():
                errors.append(
                    f"{RESOLUTION_PATH}: targets[{index}].adapterPath must be a non-empty string when missing=false"
                )
            elif not is_safe_relative_path(adapter_path):
                errors.append(
                    f"{RESOLUTION_PATH}: targets[{index}].adapterPath must be a safe relative path"
                )

    return errors


def validate_summary_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = resolution.get("summary")

    if not isinstance(summary, dict):
        return [f"{RESOLUTION_PATH}: summary must be an object"]

    integer_fields = [
        "agentCount",
        "targetCount",
        "availableSkillCount",
        "producedArtifactBindingCount",
        "errorCount",
    ]

    for field in integer_fields:
        value = summary.get(field)
        if not is_plain_int(value):
            errors.append(f"{RESOLUTION_PATH}: summary.{field} must be an integer")

    summary_errors = summary.get("errors")
    if not isinstance(summary_errors, list):
        errors.append(f"{RESOLUTION_PATH}: summary.errors must be an empty list")
    elif summary_errors:
        errors.append(f"{RESOLUTION_PATH}: summary.errors must be empty")

    error_count = summary.get("errorCount")
    if is_plain_int(error_count) and error_count != 0:
        errors.append(f"{RESOLUTION_PATH}: summary.errorCount must be 0")

    agents = resolution.get("agents")
    agent_count = summary.get("agentCount")
    if isinstance(agents, list) and is_plain_int(agent_count) and agent_count != len(agents):
        errors.append(f"{RESOLUTION_PATH}: summary.agentCount must match agents length")

    targets = resolution.get("targets")
    target_count = summary.get("targetCount")
    if isinstance(targets, list) and is_plain_int(target_count) and target_count != len(targets):
        errors.append(f"{RESOLUTION_PATH}: summary.targetCount must match targets length")

    return errors


def is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def validate_project_string_field(
    project: dict[str, Any],
    field: str,
    errors: list[str],
) -> None:
    value = project.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{RESOLUTION_PATH}: project.{field} must be a non-empty string")


def validate_project_string_list_field(
    project: dict[str, Any],
    field: str,
    errors: list[str],
) -> None:
    value = project.get(field)

    if not isinstance(value, list) or not value:
        errors.append(f"{RESOLUTION_PATH}: project.{field} must be a non-empty list")
        return

    seen_values: set[str] = set()

    for index, entry in enumerate(value):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(
                f"{RESOLUTION_PATH}: project.{field}[{index}] must be a non-empty string"
            )
            continue

        if entry in seen_values:
            errors.append(
                f"{RESOLUTION_PATH}: project.{field}[{index}] is duplicated"
            )

        seen_values.add(entry)


def validate_project_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project = resolution.get("project")

    if not isinstance(project, dict):
        return [f"{RESOLUTION_PATH}: project must be an object"]

    for field in [
        "name",
        "type",
        "description",
        "architectureProfile",
    ]:
        validate_project_string_field(project, field, errors)

    for field in [
        "languageProfiles",
        "runtimeProfiles",
    ]:
        validate_project_string_list_field(project, field, errors)

    return errors


def workflow_registry_path(profile: str) -> Path:
    return Path("registry") / "workflows" / f"{profile}.workflow.json"


def is_safe_registry_name(value: str) -> bool:
    return (
        bool(value.strip())
        and "/" not in value
        and "\\" not in value
        and ".." not in Path(value).parts
    )


def validate_workflow_semantics_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    workflow = resolution.get("workflow")

    if not isinstance(workflow, dict):
        return errors

    profile = workflow.get("profile")
    if not isinstance(profile, str) or not profile.strip():
        return errors

    if not is_safe_registry_name(profile):
        errors.append(f"{RESOLUTION_PATH}: workflow.profile must be a safe registry name")
        return errors

    registry_path = workflow_registry_path(profile)
    if not registry_path.is_file():
        errors.append(
            f"{RESOLUTION_PATH}: workflow.profile must reference an existing workflow registry file"
        )
        return errors

    try:
        registry_workflow = load_json(registry_path)
    except Exception as exc:
        errors.append(f"{registry_path}: failed to load workflow registry file: {exc}")
        return errors

    registry_states = registry_workflow.get("states")
    if not isinstance(registry_states, list):
        errors.append(f"{registry_path}: states must be a list")
        return errors

    state_names: set[str] = set()
    terminal_state_names: set[str] = set()

    for state_index, state in enumerate(registry_states):
        if not isinstance(state, dict):
            errors.append(f"{registry_path}: states[{state_index}] must be an object")
            continue

        state_name = state.get("name")
        if not isinstance(state_name, str) or not state_name.strip():
            errors.append(f"{registry_path}: states[{state_index}].name must be a non-empty string")
            continue

        state_names.add(state_name)

        if state.get("terminal") is True:
            terminal_state_names.add(state_name)

    start_state = workflow.get("startState")
    if isinstance(start_state, str) and start_state.strip():
        if start_state not in state_names:
            errors.append(
                f"{RESOLUTION_PATH}: workflow.startState must exist in workflow registry states"
            )
        elif start_state in terminal_state_names:
            errors.append(
                f"{RESOLUTION_PATH}: workflow.startState must reference a non-terminal registry state"
            )

    terminal_states = workflow.get("terminalStates")
    if isinstance(terminal_states, list):
        for terminal_index, terminal_state in enumerate(terminal_states):
            if not isinstance(terminal_state, str) or not terminal_state.strip():
                continue

            if terminal_state not in state_names:
                errors.append(
                    f"{RESOLUTION_PATH}: workflow.terminalStates[{terminal_index}] "
                    "must exist in workflow registry states"
                )
            elif terminal_state not in terminal_state_names:
                errors.append(
                    f"{RESOLUTION_PATH}: workflow.terminalStates[{terminal_index}] "
                    "must reference a terminal registry state"
                )

    registry_fail_closed = registry_workflow.get("failClosed")
    fail_closed = workflow.get("failClosed")
    if isinstance(registry_fail_closed, bool) and isinstance(fail_closed, bool):
        if fail_closed != registry_fail_closed:
            errors.append(
                f"{RESOLUTION_PATH}: workflow.failClosed must match workflow registry failClosed"
            )

    return errors


def validate_workflow_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    workflow = resolution.get("workflow")

    if not isinstance(workflow, dict):
        return [f"{RESOLUTION_PATH}: workflow must be an object"]

    fail_closed = workflow.get("failClosed")
    if not isinstance(fail_closed, bool):
        errors.append(f"{RESOLUTION_PATH}: workflow.failClosed must be a boolean")

    profile = workflow.get("profile")
    if not isinstance(profile, str) or not profile.strip():
        errors.append(f"{RESOLUTION_PATH}: workflow.profile must be a non-empty string")

    start_state = workflow.get("startState")
    if not isinstance(start_state, str) or not start_state.strip():
        errors.append(f"{RESOLUTION_PATH}: workflow.startState must be a non-empty string")

    terminal_states = workflow.get("terminalStates")
    if not isinstance(terminal_states, list) or not terminal_states:
        errors.append(f"{RESOLUTION_PATH}: workflow.terminalStates must be a non-empty list")
    else:
        seen_terminal_states: set[str] = set()

        for index, terminal_state in enumerate(terminal_states):
            if not isinstance(terminal_state, str) or not terminal_state.strip():
                errors.append(
                    f"{RESOLUTION_PATH}: workflow.terminalStates[{index}] must be a non-empty string"
                )
                continue

            if terminal_state in seen_terminal_states:
                errors.append(
                    f"{RESOLUTION_PATH}: workflow.terminalStates[{index}] is duplicated"
                )

            seen_terminal_states.add(terminal_state)

    return errors


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


def validate_agent_produces_string_field(
    produce: dict[str, Any],
    agent_index: int,
    produce_index: int,
    field: str,
    errors: list[str],
) -> None:
    value = produce.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(
            f"{RESOLUTION_PATH}: agents[{agent_index}].produces[{produce_index}].{field} "
            "must be a non-empty string"
        )
    elif field in {"contractPath", "pathPattern"} and not is_safe_relative_path(value):
        errors.append(
            f"{RESOLUTION_PATH}: agents[{agent_index}].produces[{produce_index}].{field} "
            "must be a safe relative path"
        )


def validate_agent_produces_string_list_field(
    produce: dict[str, Any],
    agent_index: int,
    produce_index: int,
    field: str,
    errors: list[str],
) -> None:
    value = produce.get(field)

    if not isinstance(value, list) or not value:
        errors.append(
            f"{RESOLUTION_PATH}: agents[{agent_index}].produces[{produce_index}].{field} "
            "must be a non-empty list"
        )
        return

    seen_values: set[str] = set()

    for entry_index, entry in enumerate(value):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(
                f"{RESOLUTION_PATH}: agents[{agent_index}].produces[{produce_index}]."
                f"{field}[{entry_index}] must be a non-empty string"
            )
            continue

        if entry in seen_values:
            errors.append(
                f"{RESOLUTION_PATH}: agents[{agent_index}].produces[{produce_index}]."
                f"{field}[{entry_index}] is duplicated"
            )

        seen_values.add(entry)


def validate_agent_identity_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    agents = resolution.get("agents")

    if not isinstance(agents, list):
        return errors

    seen_agent_names: set[str] = set()

    for agent_index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            continue

        name = agent.get("name")
        if isinstance(name, str) and name.strip():
            if name in seen_agent_names:
                errors.append(f"{RESOLUTION_PATH}: agents[{agent_index}].name is duplicated")
            seen_agent_names.add(name)

        role = agent.get("role")
        if not isinstance(role, str) or not role.strip():
            errors.append(f"{RESOLUTION_PATH}: agents[{agent_index}].role must be a non-empty string")

        registry_path = agent.get("registryPath")
        if not isinstance(registry_path, str) or not registry_path.strip():
            errors.append(
                f"{RESOLUTION_PATH}: agents[{agent_index}].registryPath must be a non-empty string"
            )
        elif not is_safe_relative_path(registry_path):
            errors.append(
                f"{RESOLUTION_PATH}: agents[{agent_index}].registryPath must be a safe relative path"
            )

    return errors


def validate_agent_produces_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    agents = resolution.get("agents")

    if not isinstance(agents, list):
        return errors

    total_produces = 0

    for agent_index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            continue

        produces = agent.get("produces")
        if not isinstance(produces, list):
            errors.append(f"{RESOLUTION_PATH}: agents[{agent_index}].produces must be a list")
            continue

        total_produces += len(produces)

        for produce_index, produce in enumerate(produces):
            if not isinstance(produce, dict):
                errors.append(
                    f"{RESOLUTION_PATH}: agents[{agent_index}].produces[{produce_index}] "
                    "must be an object"
                )
                continue

            for field in [
                "type",
                "contractPath",
                "pathPattern",
            ]:
                validate_agent_produces_string_field(
                    produce,
                    agent_index,
                    produce_index,
                    field,
                    errors,
                )

            for field in [
                "allowedStatuses",
                "requiredHeadings",
            ]:
                validate_agent_produces_string_list_field(
                    produce,
                    agent_index,
                    produce_index,
                    field,
                    errors,
                )

    summary = resolution.get("summary")
    if isinstance(summary, dict):
        expected_count = summary.get("producedArtifactBindingCount")
        if is_plain_int(expected_count) and expected_count != total_produces:
            errors.append(
                f"{RESOLUTION_PATH}: summary.producedArtifactBindingCount "
                "must match total agents produces length"
            )

    return errors


def validate_target_resolution(resolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    targets = resolution.get("targets")

    if not isinstance(targets, list) or not targets:
        return [f"{RESOLUTION_PATH}: expected non-empty 'targets' collection"]

    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(f"{RESOLUTION_PATH}: targets[{index}] must be an object")
            continue

        name = target.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{RESOLUTION_PATH}: targets[{index}].name must be a non-empty string")

        enabled = target.get("enabled")
        if not isinstance(enabled, bool):
            errors.append(f"{RESOLUTION_PATH}: targets[{index}].enabled must be a boolean")

        missing = target.get("missing")
        if not isinstance(missing, bool):
            errors.append(f"{RESOLUTION_PATH}: targets[{index}].missing must be a boolean")
        elif not missing:
            adapter_path = target.get("adapterPath")
            if not isinstance(adapter_path, str) or not adapter_path.strip():
                errors.append(f"{RESOLUTION_PATH}: targets[{index}].adapterPath must be a non-empty string")

            elif not is_safe_relative_path(adapter_path):
                errors.append(
                    f"{RESOLUTION_PATH}: targets[{index}].adapterPath must be a safe relative path"
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

    errors.extend(validate_summary_resolution(resolution))
    errors.extend(validate_project_resolution(resolution))
    errors.extend(validate_config_resolution_consistency(resolution))
    errors.extend(validate_workflow_resolution(resolution))
    errors.extend(validate_workflow_semantics_resolution(resolution))
    errors.extend(validate_agent_resolution(resolution))
    errors.extend(validate_agent_identity_resolution(resolution))
    errors.extend(validate_agent_produces_resolution(resolution))
    errors.extend(validate_target_resolution(resolution))
    errors.extend(validate_target_semantics_resolution(resolution))
    errors.extend(validate_reference_paths_resolution(resolution))

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
