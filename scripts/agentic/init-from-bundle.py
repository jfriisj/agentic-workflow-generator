#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
SETUP_PROFILE_PATH = ROOT / ".agentic" / "setup-profile.json"
SETUP_PROFILE_VALIDATOR = ROOT / "scripts" / "agentic" / "validate-setup-profile.py"


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


def load_setup(setup_name: str) -> tuple[Path, dict[str, Any]]:
    path = ROOT / "registry" / "setups" / f"{setup_name}.setup.json"
    if not path.is_file():
        raise ValueError(f"Unknown setup '{setup_name}'")

    setup = load_json(path)
    actual_name = require_string(setup, "name", path)
    if actual_name != setup_name:
        raise ValueError(f"{path}: setup name '{actual_name}' does not match requested setup '{setup_name}'")

    return path, setup


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


def parse_answer_overrides(raw_answers: list[str] | None) -> dict[str, str]:
    overrides: dict[str, str] = {}

    for raw_answer in raw_answers or []:
        if "=" not in raw_answer:
            raise ValueError(f"Invalid --answer '{raw_answer}'. Expected format: question=value")

        question, selected = raw_answer.split("=", 1)
        question = question.strip()
        selected = selected.strip()

        if not question:
            raise ValueError(f"Invalid --answer '{raw_answer}'. Question id must be non-empty")

        if not selected:
            raise ValueError(f"Invalid --answer '{raw_answer}'. Selected value must be non-empty")

        if question in overrides:
            raise ValueError(f"Duplicate --answer for question '{question}'")

        overrides[question] = selected

    return overrides


def materialize_answer(
    setup_path: Path,
    question: dict[str, Any],
    index: int,
    answer_overrides: dict[str, str],
    used_overrides: set[str],
) -> dict[str, str]:
    question_id = require_string(question, "id", setup_path)
    recommended = require_string_list(question, "recommended", setup_path)

    if question_id in answer_overrides:
        selected = answer_overrides[question_id]
        used_overrides.add(question_id)
    else:
        selected = recommended[0]

    options = question.get("options")
    if not isinstance(options, list) or not options:
        raise ValueError(f"{setup_path}: question '{question_id}' options must be a non-empty list")

    options_by_value: dict[str, dict[str, Any]] = {}
    for option_index, option in enumerate(options):
        if not isinstance(option, dict):
            raise ValueError(f"{setup_path}: question '{question_id}' options[{option_index}] must be an object")

        option_value = option.get("value")
        if not isinstance(option_value, str) or not option_value.strip():
            raise ValueError(f"{setup_path}: question '{question_id}' options[{option_index}].value must be a non-empty string")

        options_by_value[option_value] = option

    selected_option = options_by_value.get(selected)
    if selected_option is None:
        raise ValueError(f"{setup_path}: question '{question_id}' selected option '{selected}' does not exist")

    blocked = question.get("blocked")
    if isinstance(blocked, list) and selected in blocked:
        raise ValueError(f"{setup_path}: question '{question_id}' selected option '{selected}' is blocked")

    compatible = question.get("compatible")
    if selected in recommended:
        classification = "recommended"
    elif isinstance(compatible, list) and selected in compatible:
        classification = "compatible"
    else:
        raise ValueError(
            f"{setup_path}: question '{question_id}' selected option '{selected}' is neither recommended nor compatible"
        )

    reason = selected_option.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(f"{setup_path}: question '{question_id}' option '{selected}' reason must be a non-empty string")

    return {
        "question": question_id,
        "selected": selected,
        "classification": classification,
        "reason": reason,
    }


def materialize_setup_profile(setup_name: str, answer_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    setup_path, setup = load_setup(setup_name)

    mode = require_string(setup, "mode", setup_path)
    default_bundle = require_string(setup, "defaultBundle", setup_path)

    questions = setup.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"{setup_path}: questions must be a non-empty list")

    overrides = answer_overrides or {}
    used_overrides: set[str] = set()

    answers: list[dict[str, str]] = []
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            raise ValueError(f"{setup_path}: questions[{index}] must be an object")
        answers.append(materialize_answer(setup_path, question, index, overrides, used_overrides))

    unused_overrides = sorted(set(overrides) - used_overrides)
    if unused_overrides:
        raise ValueError(f"{setup_path}: --answer references unknown setup question(s): {unused_overrides}")

    final_recommendation = setup.get("finalRecommendation")
    if not isinstance(final_recommendation, dict):
        raise ValueError(f"{setup_path}: finalRecommendation must be an object")

    selected_bundle = require_string(final_recommendation, "bundle", setup_path)
    if selected_bundle != default_bundle:
        raise ValueError(
            f"{setup_path}: finalRecommendation bundle '{selected_bundle}' must match defaultBundle '{default_bundle}'"
        )

    return {
        "$schema": "./schemas/setup-profile.schema.json",
        "schemaVersion": "0.1.0",
        "mode": mode,
        "setup": setup_name,
        "answers": answers,
        "selected": {
            "bundle": selected_bundle,
            "profile": require_string(final_recommendation, "profile", setup_path),
            "workflow": require_string(final_recommendation, "workflow", setup_path),
            "agents": require_string_list(final_recommendation, "agents", setup_path),
            "skills": require_string_list(final_recommendation, "skills", setup_path),
            "artifacts": require_string_list(final_recommendation, "artifacts", setup_path),
            "targets": require_string_list(final_recommendation, "targets", setup_path),
        },
        "policy": {
            "failFast": True,
            "fallbackAllowed": False,
        },
    }


def validate_setup_profile() -> None:
    if not SETUP_PROFILE_VALIDATOR.is_file():
        raise ValueError(f"Required setup profile validator not found: {SETUP_PROFILE_VALIDATOR}")

    result = subprocess.run(
        [sys.executable, str(SETUP_PROFILE_VALIDATOR)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if result.returncode != 0:
        raise ValueError("setup profile validation failed:\n" + result.stdout.rstrip())


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
    parser = argparse.ArgumentParser(description="Initialize Agentic configuration from a registered bundle or guided setup.")
    parser.add_argument("--bundle", help="Bundle name, for example: orchestrated-delivery")
    parser.add_argument("--guided", action="store_true", help="Initialize from a guided setup recommendation.")
    parser.add_argument("--setup", help="Guided setup name, for example: orchestrated-delivery-greenfield")
    parser.add_argument(
        "--answer",
        action="append",
        default=[],
        help="Guided setup answer override in question=value format. May be repeated.",
    )
    args = parser.parse_args()

    if args.guided:
        if args.bundle:
            parser.error("--guided cannot be combined with --bundle")
        if not args.setup:
            parser.error("--guided requires --setup")
    else:
        if args.setup:
            parser.error("--setup requires --guided")
        if args.answer:
            parser.error("--answer requires --guided")
        if not args.bundle:
            parser.error("one of --bundle or --guided --setup is required")

    return args


def main() -> int:
    args = parse_args()

    try:
        if args.guided:
            answer_overrides = parse_answer_overrides(args.answer)
            setup_profile = materialize_setup_profile(args.setup, answer_overrides)
            write_json(SETUP_PROFILE_PATH, setup_profile)
            validate_setup_profile()

            selected = setup_profile.get("selected")
            if not isinstance(selected, dict):
                raise ValueError(f"{SETUP_PROFILE_PATH}: selected must be an object")

            bundle = require_string(selected, "bundle", SETUP_PROFILE_PATH)
            config = materialize_config(bundle)
            write_json(CONFIG_PATH, config)

            print(f"PASS: Initialized .agentic/setup-profile.json from guided setup '{args.setup}'.")
            print(f"PASS: Initialized .agentic/agentic.json from bundle '{bundle}'.")
            return 0

        config = materialize_config(args.bundle)
        write_json(CONFIG_PATH, config)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"PASS: Initialized .agentic/agentic.json from bundle '{args.bundle}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
