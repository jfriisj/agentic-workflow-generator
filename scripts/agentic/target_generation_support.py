#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowTopology:
    controller_agent: str
    start_state: str
    state_to_agent: dict[str, str]
    terminal_states: frozenset[str]
    transitions: tuple[dict[str, str], ...]


def require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{label} must be a non-empty string.")
    return value


def derive_workflow_topology(resolution: dict[str, Any]) -> WorkflowTopology:
    workflow = resolution.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("Resolution workflow must be an object.")

    states = workflow.get("states")
    if not isinstance(states, list) or not states:
        raise RuntimeError("Resolution workflow.states must be a non-empty list.")

    configured_agents: list[str] = []
    for index, agent in enumerate(resolution.get("agents", [])):
        if not isinstance(agent, dict):
            raise RuntimeError(f"Resolution agents[{index}] must be an object.")
        configured_agents.append(
            require_non_empty_string(
                agent.get("name"),
                f"Resolution agents[{index}].name",
            )
        )

    if not configured_agents:
        raise RuntimeError("Resolution must contain configured agents.")

    state_to_agent: dict[str, str] = {}
    terminal_states: set[str] = set()
    all_state_names: set[str] = set()

    for index, state in enumerate(states):
        if not isinstance(state, dict):
            raise RuntimeError(f"Resolution workflow.states[{index}] must be an object.")

        state_name = require_non_empty_string(
            state.get("name"),
            f"Resolution workflow.states[{index}].name",
        )

        if state_name in all_state_names:
            raise RuntimeError(f"Resolution workflow state is duplicated: {state_name}")
        all_state_names.add(state_name)

        if state.get("terminal") is True:
            if "agent" in state or "gate" in state:
                raise RuntimeError(
                    f"Terminal workflow state must not declare agent or gate: {state_name}"
                )
            terminal_states.add(state_name)
            continue

        agent_name = require_non_empty_string(
            state.get("agent"),
            f"Resolution workflow state {state_name}.agent",
        )
        require_non_empty_string(
            state.get("gate"),
            f"Resolution workflow state {state_name}.gate",
        )

        if agent_name not in configured_agents:
            raise RuntimeError(
                f"Workflow state {state_name} references unconfigured agent {agent_name}."
            )

        state_to_agent[state_name] = agent_name

    if not state_to_agent:
        raise RuntimeError("Resolution workflow must contain non-terminal state agents.")

    state_agents = set(state_to_agent.values())
    controller_agents = [
        agent_name
        for agent_name in configured_agents
        if agent_name not in state_agents
    ]

    if len(controller_agents) != 1:
        raise RuntimeError(
            "Exactly one configured controller agent must exist outside workflow states; "
            f"found {controller_agents}."
        )

    controller_agent = controller_agents[0]
    default_failure_route = require_non_empty_string(
        workflow.get("defaultFailureRoute"),
        "Resolution workflow.defaultFailureRoute",
    )

    if default_failure_route != controller_agent:
        raise RuntimeError(
            "Resolution workflow.defaultFailureRoute must equal the controller agent "
            f"{controller_agent}, got {default_failure_route}."
        )

    start_state = require_non_empty_string(
        workflow.get("startState"),
        "Resolution workflow.startState",
    )
    if start_state not in state_to_agent:
        raise RuntimeError(
            f"Resolution workflow.startState must be non-terminal: {start_state}"
        )

    raw_transitions = workflow.get("transitions")
    if not isinstance(raw_transitions, list) or not raw_transitions:
        raise RuntimeError("Resolution workflow.transitions must be a non-empty list.")

    transitions: list[dict[str, str]] = []
    for index, transition in enumerate(raw_transitions):
        if not isinstance(transition, dict):
            raise RuntimeError(
                f"Resolution workflow.transitions[{index}] must be an object."
            )

        source = require_non_empty_string(
            transition.get("from"),
            f"Resolution workflow.transitions[{index}].from",
        )
        target = require_non_empty_string(
            transition.get("to"),
            f"Resolution workflow.transitions[{index}].to",
        )
        event = require_non_empty_string(
            transition.get("on"),
            f"Resolution workflow.transitions[{index}].on",
        )

        if source not in state_to_agent:
            raise RuntimeError(
                f"Workflow transition source must be non-terminal: {source}"
            )
        if target not in all_state_names:
            raise RuntimeError(f"Workflow transition target is unknown: {target}")

        transitions.append({"from": source, "to": target, "on": event})

    return WorkflowTopology(
        controller_agent=controller_agent,
        start_state=start_state,
        state_to_agent=state_to_agent,
        terminal_states=frozenset(terminal_states),
        transitions=tuple(transitions),
    )


def opencode_mode_for_agent(
    topology: WorkflowTopology,
    agent_name: str,
) -> str:
    if agent_name == topology.controller_agent:
        return "primary"
    if agent_name in topology.state_to_agent.values():
        return "subagent"
    raise RuntimeError(f"Agent is not part of workflow topology: {agent_name}")


def handoffs_for_agent(
    topology: WorkflowTopology,
    agent_name: str,
) -> list[dict[str, Any]]:
    handoffs: list[dict[str, Any]] = []

    if agent_name == topology.controller_agent:
        target_agent = topology.state_to_agent[topology.start_state]
        handoffs.append(
            {
                "label": f"Start {topology.start_state}",
                "agent": target_agent,
                "prompt": (
                    f"Begin the workflow at state {topology.start_state}. "
                    "Follow the generated gate and artifact requirements."
                ),
                "send": False,
            }
        )
        return handoffs

    owned_states = [
        state_name
        for state_name, owner in topology.state_to_agent.items()
        if owner == agent_name
    ]

    seen: set[tuple[str, str, str]] = set()

    for state_name in owned_states:
        for transition in topology.transitions:
            if transition["from"] != state_name:
                continue

            target_state = transition["to"]
            event = transition["on"]

            if target_state in topology.state_to_agent:
                target_agent = topology.state_to_agent[target_state]
                prompt = (
                    f"Continue the workflow after state {state_name} returned "
                    f"{event}. Enter state {target_state} and follow its gate "
                    "and artifact requirements."
                )
            elif target_state in topology.terminal_states:
                if event.lower() == "pass":
                    continue
                target_agent = topology.controller_agent
                prompt = (
                    f"State {state_name} returned {event} and routed to terminal "
                    f"state {target_state}. Review the blocked outcome and decide "
                    "the next fail-closed action."
                )
            else:
                raise RuntimeError(
                    f"Workflow transition target is unavailable: {target_state}"
                )

            key = (event, target_state, target_agent)
            if key in seen:
                continue
            seen.add(key)

            handoffs.append(
                {
                    "label": f"{event.upper()} to {target_agent}",
                    "agent": target_agent,
                    "prompt": prompt,
                    "send": False,
                }
            )

    return handoffs


def require_permission_mapping(
    adapter: dict[str, Any],
    permission_profile: str,
) -> dict[str, Any]:
    mappings = adapter.get("permissionMapping")
    if not isinstance(mappings, dict):
        raise RuntimeError("Target adapter permissionMapping must be an object.")

    mapping = mappings.get(permission_profile)
    if not isinstance(mapping, dict):
        raise RuntimeError(
            f"Target adapter lacks permission mapping for {permission_profile}."
        )

    return mapping


def deduplicated_resolved_skills(
    resolved_agent: dict[str, Any],
) -> list[str]:
    resolved_capabilities = resolved_agent.get("resolvedCapabilities")
    if not isinstance(resolved_capabilities, list):
        raise RuntimeError("Resolved agent capabilities must be a list.")

    skills: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(resolved_capabilities):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"Resolved capability {index} must be an object."
            )

        skill_name = require_non_empty_string(
            item.get("skill"),
            f"Resolved capability {index}.skill",
        )

        if skill_name not in seen:
            skills.append(skill_name)
            seen.add(skill_name)

    return skills


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
