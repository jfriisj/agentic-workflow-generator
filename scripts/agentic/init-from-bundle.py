#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from guided_init import (
    choose_interactive_setup,
    collect_interactive_answers,
    confirm_guided_plan,
    print_guided_plan,
    require_interactive_terminal,
    validate_setup_registry,
)
from init_support import (
    CONFIG_PATH,
    CONFIG_SCHEMA_PATH,
    CONFIG_VALIDATOR,
    ROOT,
    SETUP_PROFILE_PATH,
    SETUP_PROFILE_VALIDATOR,
    load_json,
    require_string,
    require_string_list,
    write_json,
)
from setup_materializer import (
    materialize_setup_profile,
    parse_answer_overrides,
)


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


def materialize_targets(existing_targets: list[Any], target_names: list[str]) -> list[dict[str, Any]]:
    existing_by_name: dict[str, dict[str, Any]] = {}

    for item in existing_targets:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            existing_by_name[item["name"]] = dict(item)

    result: list[dict[str, Any]] = []

    for index, target in enumerate(target_names, start=1):
        item = existing_by_name.get(target, {"name": target, "enabled": True, "priority": index})
        item["name"] = target
        item["enabled"] = True
        item["priority"] = index
        result.append(item)

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


def validate_setup_profile(
    profile_path: Path = SETUP_PROFILE_PATH,
) -> None:
    if not SETUP_PROFILE_VALIDATOR.is_file():
        raise ValueError(f"Required setup profile validator not found: {SETUP_PROFILE_VALIDATOR}")

    result = subprocess.run(
        [sys.executable, str(SETUP_PROFILE_VALIDATOR), str(profile_path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if result.returncode != 0:
        raise ValueError("setup profile validation failed:\n" + result.stdout.rstrip())


def validate_agentic_config(config_path: Path) -> None:
    if not CONFIG_VALIDATOR.is_file():
        raise ValueError(
            f"Required Agentic config validator not found: {CONFIG_VALIDATOR}"
        )

    if not CONFIG_SCHEMA_PATH.is_file():
        raise ValueError(
            f"Required Agentic config schema not found: {CONFIG_SCHEMA_PATH}"
        )

    result = subprocess.run(
        [
            "bash",
            str(CONFIG_VALIDATOR),
            str(config_path),
            str(CONFIG_SCHEMA_PATH),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if result.returncode != 0:
        raise ValueError(
            "Agentic config validation failed:\n"
            + result.stdout.rstrip()
        )


def validate_guided_dry_run(
    setup_profile: dict[str, Any],
    config: dict[str, Any],
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="agentic-guided-dry-run-"
    ) as temp_directory:
        candidate_directory = Path(temp_directory)
        candidate_profile_path = (
            candidate_directory / "setup-profile.json"
        )
        candidate_config_path = (
            candidate_directory / "agentic.json"
        )

        write_json(candidate_profile_path, setup_profile)
        write_json(candidate_config_path, config)

        validate_setup_profile(candidate_profile_path)
        validate_agentic_config(candidate_config_path)


def restore_file(path: Path, previous_content: bytes | None) -> None:
    if previous_content is None:
        path.unlink(missing_ok=True)
        return

    path.write_bytes(previous_content)


def commit_guided_outputs(
    setup_profile: dict[str, Any],
    config: dict[str, Any],
) -> None:
    previous_profile = (
        SETUP_PROFILE_PATH.read_bytes() if SETUP_PROFILE_PATH.is_file() else None
    )
    previous_config = CONFIG_PATH.read_bytes() if CONFIG_PATH.is_file() else None

    try:
        write_json(SETUP_PROFILE_PATH, setup_profile)
        write_json(CONFIG_PATH, config)
        validate_setup_profile()
    except Exception as exc:
        restoration_errors: list[str] = []

        for path, previous_content in (
            (SETUP_PROFILE_PATH, previous_profile),
            (CONFIG_PATH, previous_config),
        ):
            try:
                restore_file(path, previous_content)
            except Exception as restoration_exc:
                restoration_errors.append(f"{path}: {restoration_exc}")

        if restoration_errors:
            raise RuntimeError(
                f"{exc}; additionally failed to restore previous files: "
                + "; ".join(restoration_errors)
            ) from exc

        raise


def materialize_config(
    bundle_name: str,
    selected_workflow: str | None = None,
    selected_agents: list[str] | None = None,
    selected_targets: list[str] | None = None,
) -> dict[str, Any]:
    bundle_path, bundle = load_bundle(bundle_name)

    bundle_workflow = require_string(bundle, "workflow", bundle_path)
    bundle_targets = require_string_list(bundle, "targets", bundle_path)
    bundle_agents = require_string_list(bundle, "agents", bundle_path)

    workflow_name = selected_workflow or bundle_workflow
    target_names = selected_targets or bundle_targets
    agent_names = selected_agents or bundle_agents

    if workflow_name != bundle_workflow:
        raise ValueError(f"{bundle_path}: selected workflow '{workflow_name}' must match bundle workflow '{bundle_workflow}'")

    extra_targets = sorted(set(target_names) - set(bundle_targets))
    if extra_targets:
        raise ValueError(f"{bundle_path}: selected targets are not included in bundle targets: {extra_targets}")

    extra_agents = sorted(set(agent_names) - set(bundle_agents))
    if extra_agents:
        raise ValueError(f"{bundle_path}: selected agents are not included in bundle agents: {extra_agents}")

    workflow = load_workflow(workflow_name)

    existing = existing_config_or_default()

    generated = {
        "$schema": existing.get("$schema", "./schemas/agentic.schema.json"),
        "project": existing["project"],
        "generator": existing["generator"],
        "targets": materialize_targets(existing.get("targets", []), target_names),
        "workflow": {
            "profile": workflow_name,
            "startState": require_string(workflow, "startState", ROOT / "registry" / "workflows" / f"{workflow_name}.workflow.json"),
            "terminalStates": require_string_list(workflow, "terminalStates", ROOT / "registry" / "workflows" / f"{workflow_name}.workflow.json"),
            "failClosed": bool(workflow.get("failClosed", True)),
        },
        "permissionProfiles": existing["permissionProfiles"],
        "agents": materialize_agents(agent_names),
        "gates": materialize_gates(workflow),
        "runtimeContext": existing["runtimeContext"],
        "validation": existing["validation"],
    }

    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize Agentic configuration from a registered bundle or guided setup."
    )
    parser.add_argument("--bundle", help="Bundle name, for example: orchestrated-delivery")
    parser.add_argument(
        "--guided",
        action="store_true",
        help=(
            "Run interactive guided initialization, or initialize non-interactively "
            "when combined with --setup."
        ),
    )
    parser.add_argument(
        "--setup",
        help="Guided setup name, for example: orchestrated-delivery-greenfield",
    )
    parser.add_argument(
        "--answer",
        action="append",
        default=[],
        help="Guided setup answer override in question=value format. May be repeated.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Materialize, validate, and print a guided setup plan "
            "without writing files."
        ),
    )
    args = parser.parse_args()

    if args.guided:
        if args.bundle:
            parser.error("--guided cannot be combined with --bundle")
        if args.answer and not args.setup:
            parser.error("--answer requires --setup when used with --guided")
    else:
        if args.setup:
            parser.error("--setup requires --guided")
        if args.answer:
            parser.error("--answer requires --guided")
        if args.dry_run:
            parser.error("--dry-run requires --guided")
        if not args.bundle:
            parser.error("one of --bundle or --guided is required")

    return args


def main() -> int:
    args = parse_args()

    try:
        if args.guided:
            interactive = args.setup is None

            if interactive:
                require_interactive_terminal()
                validate_setup_registry()

                while True:
                    setup_name = choose_interactive_setup()
                    answer_overrides = collect_interactive_answers(setup_name)
                    if answer_overrides is not None:
                        break
            else:
                setup_name = args.setup
                answer_overrides = parse_answer_overrides(args.answer)

            setup_profile = materialize_setup_profile(setup_name, answer_overrides)

            selected = setup_profile.get("selected")
            if not isinstance(selected, dict):
                raise ValueError(f"{SETUP_PROFILE_PATH}: selected must be an object")

            bundle = require_string(selected, "bundle", SETUP_PROFILE_PATH)
            workflow = require_string(selected, "workflow", SETUP_PROFILE_PATH)
            agents = require_string_list(selected, "agents", SETUP_PROFILE_PATH)
            targets = require_string_list(selected, "targets", SETUP_PROFILE_PATH)
            config = materialize_config(
                bundle,
                selected_workflow=workflow,
                selected_agents=agents,
                selected_targets=targets,
            )

            if args.dry_run:
                validate_guided_dry_run(setup_profile, config)
                print_guided_plan(setup_profile)
                print(
                    "PASS: Guided dry-run validated setup "
                    f"'{setup_name}'; no files were written."
                )
                return 0

            if interactive:
                print_guided_plan(setup_profile)
                confirm_guided_plan()

            commit_guided_outputs(setup_profile, config)

            print(
                "PASS: Initialized .agentic/setup-profile.json "
                f"from guided setup '{setup_name}'."
            )
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
