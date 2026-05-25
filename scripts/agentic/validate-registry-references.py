#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
REGISTRY_DIR = ROOT / "registry"
AGENTS_DIR = REGISTRY_DIR / "agents"
SKILLS_DIR = REGISTRY_DIR / "skills"
TARGETS_DIR = REGISTRY_DIR / "targets"
WORKFLOWS_DIR = REGISTRY_DIR / "workflows"
PROFILES_DIR = REGISTRY_DIR / "profiles"
ARTIFACTS_DIR = REGISTRY_DIR / "artifacts"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def collect_agent_names() -> set[str]:
    return {
        path.parent.name
        for path in AGENTS_DIR.glob("*/agent.json")
        if path.is_file()
    }


def collect_target_names() -> set[str]:
    return {
        path.parent.name
        for path in TARGETS_DIR.glob("*/adapter.json")
        if path.is_file()
    }


def collect_workflow_names() -> set[str]:
    names: set[str] = set()

    for path in WORKFLOWS_DIR.glob("*.workflow.json"):
        names.add(path.name.removesuffix(".workflow.json"))

        try:
            workflow = load_json(path)
        except Exception:
            continue

        declared = workflow.get("name") or workflow.get("id")
        if isinstance(declared, str) and declared.strip():
            names.add(declared.strip())

    return names


def collect_profile_names() -> set[str]:
    names: set[str] = set()

    for path in PROFILES_DIR.glob("*.profile.json"):
        names.add(path.name.removesuffix(".profile.json"))

        try:
            profile = load_json(path)
        except Exception:
            continue

        declared = profile.get("name") or profile.get("id")
        if isinstance(declared, str) and declared.strip():
            names.add(declared.strip())

    return names


def collect_artifact_names() -> set[str]:
    return {
        path.parent.name
        for path in ARTIFACTS_DIR.glob("*/artifact.json")
        if path.is_file()
    }


def extract_skill_capabilities(skill: dict[str, Any]) -> set[str]:
    capabilities: set[str] = set()

    for key in [
        "capabilities",
        "provides",
        "providedCapabilities",
        "provided_capabilities",
    ]:
        value = skill.get(key)

        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, str) and entry.strip():
                    capabilities.add(entry.strip())
                elif isinstance(entry, dict):
                    raw = entry.get("name") or entry.get("id") or entry.get("capability")
                    if raw is not None and str(raw).strip():
                        capabilities.add(str(raw).strip())

        elif isinstance(value, dict):
            nested = value.get("capabilities")
            if isinstance(nested, list):
                for entry in nested:
                    if isinstance(entry, str) and entry.strip():
                        capabilities.add(entry.strip())

    single = skill.get("capability")
    if isinstance(single, str) and single.strip():
        capabilities.add(single.strip())

    return capabilities


def collect_skill_capabilities() -> set[str]:
    capabilities: set[str] = set()

    for path in SKILLS_DIR.glob("*/skill.json"):
        try:
            skill = load_json(path)
        except Exception:
            continue

        capabilities.update(extract_skill_capabilities(skill))

    return capabilities


def validate_config_references(
    config: dict[str, Any],
    agents: set[str],
    targets: set[str],
    workflows: set[str],
    profiles: set[str],
) -> list[str]:
    errors: list[str] = []

    selected_profile = config.get("profile")
    if selected_profile is not None:
        if not isinstance(selected_profile, str) or not selected_profile.strip():
            errors.append(".agentic/agentic.json: profile must be a non-empty string when present")
        elif selected_profile not in profiles:
            errors.append(f".agentic/agentic.json: unknown profile '{selected_profile}'")

    for agent in config.get("agents", []):
        if isinstance(agent, str):
            agent_name = agent
            enabled = True
        elif isinstance(agent, dict):
            agent_name = agent.get("name")
            enabled = bool(agent.get("enabled", True))
        else:
            errors.append(".agentic/agentic.json: agents entries must be strings or objects")
            continue

        if enabled and agent_name not in agents:
            errors.append(f".agentic/agentic.json: enabled agent '{agent_name}' is not registered")

    for target in config.get("targets", []):
        if isinstance(target, str):
            target_name = target
            enabled = True
        elif isinstance(target, dict):
            target_name = target.get("name")
            enabled = bool(target.get("enabled", False))
        else:
            errors.append(".agentic/agentic.json: targets entries must be strings or objects")
            continue

        if enabled and target_name not in targets:
            errors.append(f".agentic/agentic.json: enabled target '{target_name}' is not registered")

    for workflow in config.get("workflows", []):
        if isinstance(workflow, str):
            workflow_name = workflow
            enabled = True
        elif isinstance(workflow, dict):
            workflow_name = workflow.get("name") or workflow.get("id")
            enabled = bool(workflow.get("enabled", True))
        else:
            errors.append(".agentic/agentic.json: workflows entries must be strings or objects")
            continue

        if enabled and workflow_name not in workflows:
            errors.append(f".agentic/agentic.json: enabled workflow '{workflow_name}' is not registered")

    return errors


def validate_agent_references(
    artifacts: set[str],
    skill_capabilities: set[str],
) -> list[str]:
    errors: list[str] = []

    for path in sorted(AGENTS_DIR.glob("*/agent.json")):
        try:
            agent = load_json(path)
        except Exception as exc:
            errors.append(f"{relative(path)}: {exc}")
            continue

        for artifact_type in agent.get("produces", []):
            if not isinstance(artifact_type, str):
                continue

            if artifact_type not in artifacts:
                errors.append(
                    f"{relative(path)}: produces unknown artifact '{artifact_type}'"
                )

        for capability in agent.get("capabilities", []):
            if not isinstance(capability, str):
                continue

            if capability not in skill_capabilities:
                errors.append(
                    f"{relative(path)}: capability '{capability}' has no skill coverage"
                )

    return errors


def main() -> int:
    errors: list[str] = []

    try:
        config = load_json(CONFIG_PATH)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    agents = collect_agent_names()
    targets = collect_target_names()
    workflows = collect_workflow_names()
    profiles = collect_profile_names()
    artifacts = collect_artifact_names()
    skill_capabilities = collect_skill_capabilities()

    errors.extend(
        validate_config_references(
            config=config,
            agents=agents,
            targets=targets,
            workflows=workflows,
            profiles=profiles,
        )
    )

    errors.extend(
        validate_agent_references(
            artifacts=artifacts,
            skill_capabilities=skill_capabilities,
        )
    )

    if errors:
        print(f"FAIL: Registry reference validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Registry references are valid.")
    print(f"Agents: {len(agents)}")
    print(f"Targets: {len(targets)}")
    print(f"Workflows: {len(workflows)}")
    print(f"Profiles: {len(profiles)}")
    print(f"Artifacts: {len(artifacts)}")
    print(f"Skill capabilities: {len(skill_capabilities)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
