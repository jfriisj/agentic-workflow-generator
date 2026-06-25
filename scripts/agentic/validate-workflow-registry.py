#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
WORKFLOWS_DIR = ROOT / "registry" / "workflows"
AGENTS_DIR = ROOT / "registry" / "agents"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data



def expected_workflow_name(path: Path) -> str:
    suffix = ".workflow.json"
    name = path.name

    if not name.endswith(suffix):
        return path.stem

    return name[: -len(suffix)]


def collect_agent_names() -> set[str]:
    agent_names: set[str] = set()

    for path in sorted(AGENTS_DIR.glob("*/agent.json")):
        try:
            agent = load_json(path)
        except Exception:
            continue

        name = agent.get("name")
        if isinstance(name, str) and name.strip():
            agent_names.add(name)

    return agent_names


def workflow_state_objects(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    states = workflow.get("states")

    if not isinstance(states, list):
        return []

    return [state for state in states if isinstance(state, dict)]


def state_name(state: dict[str, Any]) -> str | None:
    raw_name = state.get("name") or state.get("id")
    if isinstance(raw_name, str) and raw_name.strip():
        return raw_name.strip()

    return None


def terminal_state_names_from_objects(states: list[dict[str, Any]]) -> set[str]:
    terminal_names: set[str] = set()

    for state in states:
        name = state_name(state)
        if name is None:
            continue

        if state.get("terminal") is True:
            terminal_names.add(name)

    return terminal_names

def state_names_from_workflow(workflow: dict[str, Any]) -> set[str]:
    states = workflow.get("states", [])

    if isinstance(states, list):
        names: set[str] = set()

        for state in states:
            if isinstance(state, str):
                names.add(state)
            elif isinstance(state, dict):
                name = state.get("name") or state.get("id")
                if isinstance(name, str) and name.strip():
                    names.add(name.strip())

        return names

    if isinstance(states, dict):
        return {str(name) for name in states.keys()}

    return set()


def transition_pairs(workflow: dict[str, Any]) -> list[tuple[str, str]]:
    transitions = workflow.get("transitions", [])
    pairs: list[tuple[str, str]] = []

    if isinstance(transitions, list):
        for transition in transitions:
            if not isinstance(transition, dict):
                continue

            source = (
                transition.get("from")
                or transition.get("source")
                or transition.get("fromState")
            )
            target = (
                transition.get("to")
                or transition.get("target")
                or transition.get("toState")
            )

            if isinstance(source, str) and isinstance(target, str):
                pairs.append((source, target))

    if isinstance(transitions, dict):
        for source, targets in transitions.items():
            if isinstance(targets, str):
                pairs.append((str(source), targets))
            elif isinstance(targets, list):
                for target in targets:
                    if isinstance(target, str):
                        pairs.append((str(source), target))
                    elif isinstance(target, dict):
                        target_name = (
                            target.get("to")
                            or target.get("target")
                            or target.get("toState")
                        )
                        if isinstance(target_name, str):
                            pairs.append((str(source), target_name))

    return pairs

def reachable_states(start_state: str, pairs: list[tuple[str, str]]) -> set[str]:
    outgoing: dict[str, set[str]] = {}

    for source, target in pairs:
        outgoing.setdefault(source, set()).add(target)

    reachable: set[str] = set()
    stack = [start_state]

    while stack:
        current = stack.pop()

        if current in reachable:
            continue

        reachable.add(current)

        for target in sorted(outgoing.get(current, set()), reverse=True):
            if target not in reachable:
                stack.append(target)

    return reachable



def validate_workflow_file(path: Path, agent_names: set[str]) -> list[str]:
    errors: list[str] = []

    try:
        workflow = load_json(path)
    except Exception as exc:
        return [f"{path}: {exc}"]

    workflow_name = workflow.get("name") or workflow.get("id")
    expected_name = expected_workflow_name(path)

    if not isinstance(workflow_name, str) or not workflow_name.strip():
        errors.append(f"{path}: workflow must declare name or id as a non-empty string")
    elif workflow_name != expected_name:
        errors.append(f"{path}: workflow name '{workflow_name}' does not match file name '{expected_name}'")

    version = workflow.get("version")
    if version is not None and (not isinstance(version, str) or not version.strip()):
        errors.append(f"{path}: version must be a non-empty string when declared")

    description = workflow.get("description")
    if description is not None and not isinstance(description, str):
        errors.append(f"{path}: description must be a string when declared")

    fail_closed = workflow.get("failClosed")
    if not isinstance(fail_closed, bool):
        errors.append(f"{path}: failClosed must be a boolean")

    raw_states = workflow.get("states")
    if not isinstance(raw_states, list) or not raw_states:
        errors.append(f"{path}: states must be a non-empty list")
        return errors

    state_objects = workflow_state_objects(workflow)

    if len(state_objects) != len(raw_states):
        errors.append(f"{path}: states entries must be objects")

    state_names: list[str] = []
    terminal_names_from_states = terminal_state_names_from_objects(state_objects)

    for index, state in enumerate(raw_states):
        if not isinstance(state, dict):
            continue

        name = state_name(state)
        if name is None:
            errors.append(f"{path}: states[{index}].name must be a non-empty string")
            continue

        if name in state_names:
            errors.append(f"{path}: states[{index}].name '{name}' is duplicated")

        state_names.append(name)

        is_terminal = state.get("terminal") is True

        if is_terminal:
            if "agent" in state:
                errors.append(f"{path}: terminal state '{name}' must not declare agent")
            if "gate" in state:
                errors.append(f"{path}: terminal state '{name}' must not declare gate")
            continue

        agent = state.get("agent")
        if not isinstance(agent, str) or not agent.strip():
            errors.append(f"{path}: non-terminal state '{name}' must declare agent")
        elif agent not in agent_names:
            errors.append(f"{path}: state '{name}' references unknown agent '{agent}'")

        gate = state.get("gate")
        if not isinstance(gate, str) or not gate.strip():
            errors.append(f"{path}: non-terminal state '{name}' must declare gate")

    states = set(state_names)
    if not states:
        errors.append(f"{path}: workflow must declare at least one state")
        return errors

    start_state = workflow.get("startState") or workflow.get("initialState")
    valid_start_state: str | None = None

    if start_state is None:
        errors.append(f"{path}: startState must be declared")
    elif not isinstance(start_state, str) or not start_state.strip():
        errors.append(f"{path}: startState must be a non-empty string")
    elif start_state not in states:
        errors.append(f"{path}: startState '{start_state}' is not declared in states")
    elif start_state in terminal_names_from_states:
        errors.append(f"{path}: startState '{start_state}' must not be terminal")
    else:
        valid_start_state = start_state

    terminal_states = workflow.get("terminalStates")
    declared_terminal_states: set[str] = set()

    if not isinstance(terminal_states, list) or not terminal_states:
        errors.append(f"{path}: terminalStates must be a non-empty list")
    else:
        seen_terminal_states: set[str] = set()

        for index, terminal_state in enumerate(terminal_states):
            if not isinstance(terminal_state, str) or not terminal_state.strip():
                errors.append(f"{path}: terminalStates[{index}] must be a non-empty string")
                continue

            if terminal_state in seen_terminal_states:
                errors.append(f"{path}: terminalStates[{index}] '{terminal_state}' is duplicated")

            seen_terminal_states.add(terminal_state)

            if terminal_state not in states:
                errors.append(f"{path}: terminalState '{terminal_state}' is not declared in states")
            elif terminal_state not in terminal_names_from_states:
                errors.append(f"{path}: terminalState '{terminal_state}' must reference a terminal state")
            else:
                declared_terminal_states.add(terminal_state)

        undeclared_terminal_names = sorted(terminal_names_from_states - seen_terminal_states)
        for terminal_name in undeclared_terminal_names:
            errors.append(f"{path}: terminal state '{terminal_name}' must be listed in terminalStates")

    raw_transitions = workflow.get("transitions")
    valid_transition_pairs: list[tuple[str, str]] = []
    outgoing_sources: set[str] = set()
    seen_transition_events: set[tuple[str, str]] = set()

    if not isinstance(raw_transitions, list) or not raw_transitions:
        errors.append(f"{path}: transitions must be a non-empty list")
    else:
        for index, transition in enumerate(raw_transitions):
            label = f"transitions[{index}]"

            if not isinstance(transition, dict):
                errors.append(f"{path}: {label} must be an object")
                continue

            source = transition.get("from")
            target = transition.get("to")
            event = transition.get("on")

            if not isinstance(source, str) or not source.strip():
                errors.append(f"{path}: {label}.from must be a non-empty string")
                continue

            if not isinstance(target, str) or not target.strip():
                errors.append(f"{path}: {label}.to must be a non-empty string")
                continue

            if not isinstance(event, str) or not event.strip():
                errors.append(f"{path}: {label}.on must be a non-empty string")
                continue

            source_valid = source in states
            target_valid = target in states

            if not source_valid:
                errors.append(f"{path}: transition source '{source}' is not declared in states")
            elif source in terminal_names_from_states:
                errors.append(f"{path}: terminal state '{source}' must not have outgoing transition")
            else:
                outgoing_sources.add(source)

            if not target_valid:
                errors.append(f"{path}: transition target '{target}' is not declared in states")

            key = (source, event)
            if key in seen_transition_events:
                errors.append(f"{path}: transition event '{event}' from state '{source}' is duplicated")

            seen_transition_events.add(key)

            if source_valid and target_valid and source not in terminal_names_from_states:
                valid_transition_pairs.append((source, target))

    non_terminal_names = states - terminal_names_from_states
    for non_terminal_name in sorted(non_terminal_names):
        if non_terminal_name not in outgoing_sources:
            errors.append(f"{path}: non-terminal state '{non_terminal_name}' has no outgoing transition")

    if valid_start_state is not None:
        reachable = reachable_states(valid_start_state, valid_transition_pairs)

        for name in sorted(states - reachable):
            errors.append(f"{path}: state '{name}' is unreachable from startState '{valid_start_state}'")

        for terminal_name in sorted(declared_terminal_states):
            if terminal_name not in reachable:
                errors.append(
                    f"{path}: terminalState '{terminal_name}' is unreachable from startState '{valid_start_state}'"
                )

    return errors


def main() -> int:
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.workflow.json"))

    if not workflow_files:
        print("WARN: No workflow registry files found.")
        return 0

    errors: list[str] = []
    agent_names = collect_agent_names()

    for workflow_file in workflow_files:
        errors.extend(validate_workflow_file(workflow_file, agent_names))

    if errors:
        print(f"FAIL: Workflow registry validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Workflow registry is valid. Checked {len(workflow_files)} workflow file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
