#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
WORKFLOWS_DIR = ROOT / "registry" / "workflows"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


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


def validate_workflow_file(path: Path) -> list[str]:
    errors: list[str] = []

    try:
        workflow = load_json(path)
    except Exception as exc:
        return [f"{path}: {exc}"]

    workflow_name = workflow.get("name") or workflow.get("id")
    if not isinstance(workflow_name, str) or not workflow_name.strip():
        errors.append(f"{path}: workflow must declare name or id as a non-empty string")

    states = state_names_from_workflow(workflow)
    if not states:
        errors.append(f"{path}: workflow must declare at least one state")
        return errors

    start_state = workflow.get("startState") or workflow.get("initialState")
    if start_state is not None:
        if not isinstance(start_state, str) or not start_state.strip():
            errors.append(f"{path}: startState must be a non-empty string when present")
        elif start_state not in states:
            errors.append(f"{path}: startState '{start_state}' is not declared in states")

    terminal_states = workflow.get("terminalStates", [])
    if terminal_states is None:
        terminal_states = []

    if not isinstance(terminal_states, list):
        errors.append(f"{path}: terminalStates must be a list when present")
    else:
        for terminal_state in terminal_states:
            if not isinstance(terminal_state, str) or not terminal_state.strip():
                errors.append(f"{path}: terminalStates entries must be non-empty strings")
                continue

            if terminal_state not in states:
                errors.append(f"{path}: terminalState '{terminal_state}' is not declared in states")

    for source, target in transition_pairs(workflow):
        if source not in states:
            errors.append(f"{path}: transition source '{source}' is not declared in states")

        if target not in states:
            errors.append(f"{path}: transition target '{target}' is not declared in states")

    return errors


def main() -> int:
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.workflow.json"))

    if not workflow_files:
        print("WARN: No workflow registry files found.")
        return 0

    errors: list[str] = []

    for workflow_file in workflow_files:
        errors.extend(validate_workflow_file(workflow_file))

    if errors:
        print(f"FAIL: Workflow registry validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Workflow registry is valid. Checked {len(workflow_files)} workflow file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
