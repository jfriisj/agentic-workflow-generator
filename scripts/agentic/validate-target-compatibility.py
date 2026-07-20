#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from target_generation_support import (
    deduplicated_resolved_skills,
    derive_workflow_topology,
    handoffs_for_agent,
    opencode_mode_for_agent,
    require_permission_mapping,
)


ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
RESOLUTION_PATH = ROOT / ".agentic" / "generated" / "resolution.json"
TARGETS_DIRECTORY = ROOT / "registry" / "targets"

FORBIDDEN_RUNTIME_TEXT = (
    "{{WORKFLOW_ID}}",
    "Missing generated runtime context",
    "Runtime Context Requirement",
    ".runtime/context/",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Required JSON file is missing: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise RuntimeError(f"{path}: expected a JSON object")

    return data


def kebab_case(value: str) -> str:
    value = value.strip()
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-").lower()


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{label} must be a non-empty string")
    return value


def parse_scalar(value: str) -> Any:
    stripped = value.strip()

    if not stripped:
        return ""

    if stripped in {"true", "false"}:
        return stripped == "true"

    if stripped.startswith(('"', "[", "{")):
        return json.loads(stripped)

    return stripped


def read_frontmatter(path: Path) -> tuple[list[str], str]:
    if not path.is_file():
        raise RuntimeError(f"Required generated file is missing: {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not lines or lines[0] != "---":
        raise RuntimeError(f"{path}: missing opening YAML frontmatter delimiter")

    try:
        end_index = lines.index("---", 1)
    except ValueError as error:
        raise RuntimeError(
            f"{path}: missing closing YAML frontmatter delimiter"
        ) from error

    return lines[1:end_index], "\n".join(lines[end_index + 1 :])


def top_level_frontmatter(lines: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}

    for line in lines:
        if not line or line.startswith(" "):
            continue

        if ":" not in line:
            raise RuntimeError(f"Invalid top-level frontmatter line: {line!r}")

        key, raw_value = line.split(":", 1)

        if key in values:
            raise RuntimeError(f"Duplicated frontmatter key: {key}")

        values[key] = parse_scalar(raw_value)

    return values


def assert_no_runtime_contract(path: Path, text: str) -> None:
    for forbidden in FORBIDDEN_RUNTIME_TEXT:
        if forbidden in text:
            raise RuntimeError(
                f"{path}: contains unsupported runtime-context text {forbidden!r}"
            )


def configured_agents(
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    raw_agents = config.get("agents")

    if not isinstance(raw_agents, list) or not raw_agents:
        raise RuntimeError("agentic config agents must be a non-empty list")

    agents: dict[str, dict[str, Any]] = {}

    for index, agent in enumerate(raw_agents):
        if not isinstance(agent, dict):
            raise RuntimeError(f"agentic config agents[{index}] must be an object")

        name = require_string(
            agent.get("name"),
            f"agentic config agents[{index}].name",
        )

        if name in agents:
            raise RuntimeError(f"agentic config agent is duplicated: {name}")

        agents[name] = agent

    return agents


def resolved_agents(
    resolution: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    raw_agents = resolution.get("agents")

    if not isinstance(raw_agents, list) or not raw_agents:
        raise RuntimeError("resolution agents must be a non-empty list")

    agents: dict[str, dict[str, Any]] = {}

    for index, agent in enumerate(raw_agents):
        if not isinstance(agent, dict):
            raise RuntimeError(f"resolution agents[{index}] must be an object")

        name = require_string(
            agent.get("name"),
            f"resolution agents[{index}].name",
        )

        if name in agents:
            raise RuntimeError(f"resolution agent is duplicated: {name}")

        agents[name] = agent

    return agents


def enabled_targets(resolution: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_targets = resolution.get("targets")

    if not isinstance(raw_targets, list) or not raw_targets:
        raise RuntimeError("resolution targets must be a non-empty list")

    targets: dict[str, dict[str, Any]] = {}

    for index, target in enumerate(raw_targets):
        if not isinstance(target, dict):
            raise RuntimeError(f"resolution targets[{index}] must be an object")

        name = require_string(
            target.get("name"),
            f"resolution targets[{index}].name",
        )

        if target.get("enabled") is True and target.get("missing") is not True:
            targets[name] = target

    if not targets:
        raise RuntimeError("resolution contains no enabled available targets")

    return targets


def selected_skills(
    agents: dict[str, dict[str, Any]],
) -> set[str]:
    skills: set[str] = set()

    for agent in agents.values():
        skills.update(deduplicated_resolved_skills(agent))

    if not skills:
        raise RuntimeError("resolution contains no selected skills")

    return skills


def validate_skill_files(
    target_name: str,
    skills_directory: Path,
    expected_skills: set[str],
) -> None:
    actual_skill_paths = sorted(skills_directory.glob("*/SKILL.md"))
    actual_skills = {path.parent.name for path in actual_skill_paths}

    if actual_skills != expected_skills:
        raise RuntimeError(
            f"{target_name}: generated skills were {sorted(actual_skills)}, "
            f"expected {sorted(expected_skills)}"
        )

    for skill_path in actual_skill_paths:
        frontmatter_lines, body = read_frontmatter(skill_path)
        frontmatter = top_level_frontmatter(frontmatter_lines)

        expected_name = skill_path.parent.name
        if frontmatter.get("name") != expected_name:
            raise RuntimeError(
                f"{skill_path}: name was {frontmatter.get('name')!r}, "
                f"expected {expected_name!r}"
            )

        require_string(
            frontmatter.get("description"),
            f"{skill_path}: description",
        )

        if not body.strip():
            raise RuntimeError(f"{skill_path}: skill body is empty")

        assert_no_runtime_contract(
            skill_path,
            skill_path.read_text(encoding="utf-8"),
        )


def parse_opencode_permission(
    path: Path,
    lines: list[str],
) -> dict[str, str]:
    try:
        permission_index = lines.index("permission:")
    except ValueError as error:
        raise RuntimeError(
            f"{path}: missing permission frontmatter block"
        ) from error

    permission: dict[str, str] = {}

    for line in lines[permission_index + 1 :]:
        if line and not line.startswith(" "):
            break

        if not line.strip():
            continue

        if not line.startswith("  ") or ":" not in line:
            raise RuntimeError(
                f"{path}: invalid permission frontmatter line {line!r}"
            )

        key, raw_value = line.strip().split(":", 1)
        value = parse_scalar(raw_value)

        if not isinstance(value, str):
            raise RuntimeError(
                f"{path}: permission {key} must be a string"
            )

        permission[key] = value

    return permission


def validate_opencode(
    config_agents: dict[str, dict[str, Any]],
    resolution_agents: dict[str, dict[str, Any]],
    adapter: dict[str, Any],
    topology: Any,
    skills: set[str],
) -> None:
    generated_config = load_json(ROOT / "opencode.json")
    expected_default = kebab_case(topology.controller_agent)

    if generated_config.get("$schema") != "https://opencode.ai/config.json":
        raise RuntimeError("opencode.json contains an unexpected schema URL")

    if generated_config.get("default_agent") != expected_default:
        raise RuntimeError(
            "opencode.json default_agent was "
            f"{generated_config.get('default_agent')!r}, "
            f"expected {expected_default!r}"
        )

    expected_slugs = {
        kebab_case(name): name
        for name in resolution_agents
    }
    actual_paths = sorted((ROOT / ".opencode" / "agents").glob("*.md"))
    actual_slugs = {path.stem for path in actual_paths}

    if actual_slugs != set(expected_slugs):
        raise RuntimeError(
            "OpenCode generated agents were "
            f"{sorted(actual_slugs)}, expected {sorted(expected_slugs)}"
        )

    for agent_path in actual_paths:
        agent_name = expected_slugs[agent_path.stem]
        config_agent = config_agents[agent_name]
        frontmatter_lines, body = read_frontmatter(agent_path)
        frontmatter = top_level_frontmatter(frontmatter_lines)

        expected_mode = opencode_mode_for_agent(topology, agent_name)
        if frontmatter.get("mode") != expected_mode:
            raise RuntimeError(
                f"{agent_path}: mode was {frontmatter.get('mode')!r}, "
                f"expected {expected_mode!r}"
            )

        require_string(
            frontmatter.get("description"),
            f"{agent_path}: description",
        )

        permission_profile = require_string(
            config_agent.get("permissionProfile"),
            f"agent {agent_name}.permissionProfile",
        )
        expected_permission = require_permission_mapping(
            adapter,
            permission_profile,
        )
        actual_permission = parse_opencode_permission(
            agent_path,
            frontmatter_lines,
        )

        for permission_name in ("edit", "bash"):
            if (
                actual_permission.get(permission_name)
                != expected_permission.get(permission_name)
            ):
                raise RuntimeError(
                    f"{agent_path}: permission {permission_name} was "
                    f"{actual_permission.get(permission_name)!r}, expected "
                    f"{expected_permission.get(permission_name)!r}"
                )

        if not body.strip():
            raise RuntimeError(f"{agent_path}: agent body is empty")

        assert_no_runtime_contract(
            agent_path,
            agent_path.read_text(encoding="utf-8"),
        )

    validate_skill_files(
        "opencode",
        ROOT / ".opencode" / "skills",
        skills,
    )

    instructions_path = ROOT / "AGENTS.md"
    if not instructions_path.is_file() or not instructions_path.read_text(
        encoding="utf-8"
    ).strip():
        raise RuntimeError("AGENTS.md is missing or empty")

    assert_no_runtime_contract(
        instructions_path,
        instructions_path.read_text(encoding="utf-8"),
    )


def parse_vscode_handoffs(
    path: Path,
    lines: list[str],
) -> list[dict[str, Any]]:
    try:
        handoffs_index = lines.index("handoffs:")
    except ValueError:
        return []

    handoffs: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in lines[handoffs_index + 1 :]:
        if line and not line.startswith(" "):
            break

        if not line.strip():
            continue

        stripped = line.strip()

        if stripped.startswith("- label:"):
            if current is not None:
                handoffs.append(current)

            current = {
                "label": parse_scalar(stripped.split(":", 1)[1]),
            }
            continue

        if current is None or ":" not in stripped:
            raise RuntimeError(
                f"{path}: invalid handoff frontmatter line {line!r}"
            )

        key, raw_value = stripped.split(":", 1)
        current[key] = parse_scalar(raw_value)

    if current is not None:
        handoffs.append(current)

    return handoffs


def expected_vscode_handoffs(
    topology: Any,
    agent_name: str,
) -> list[dict[str, Any]]:
    expected: list[dict[str, Any]] = []

    for handoff in handoffs_for_agent(topology, agent_name):
        expected.append(
            {
                "label": handoff["label"],
                "agent": kebab_case(handoff["agent"]),
                "prompt": handoff["prompt"],
                "send": False,
            }
        )

    return expected


def validate_vscode(
    config_agents: dict[str, dict[str, Any]],
    resolution_agents: dict[str, dict[str, Any]],
    adapter: dict[str, Any],
    topology: Any,
    skills: set[str],
) -> None:
    expected_slugs = {
        kebab_case(name): name
        for name in resolution_agents
    }
    actual_paths = sorted((ROOT / ".github" / "agents").glob("*.agent.md"))
    actual_slugs = {
        path.name.removesuffix(".agent.md")
        for path in actual_paths
    }

    if actual_slugs != set(expected_slugs):
        raise RuntimeError(
            "VS Code generated agents were "
            f"{sorted(actual_slugs)}, expected {sorted(expected_slugs)}"
        )

    for agent_path in actual_paths:
        agent_slug = agent_path.name.removesuffix(".agent.md")
        agent_name = expected_slugs[agent_slug]
        config_agent = config_agents[agent_name]
        frontmatter_lines, body = read_frontmatter(agent_path)
        frontmatter = top_level_frontmatter(frontmatter_lines)

        if frontmatter.get("name") != agent_name:
            raise RuntimeError(
                f"{agent_path}: name was {frontmatter.get('name')!r}, "
                f"expected {agent_name!r}"
            )

        require_string(
            frontmatter.get("description"),
            f"{agent_path}: description",
        )

        permission_profile = require_string(
            config_agent.get("permissionProfile"),
            f"agent {agent_name}.permissionProfile",
        )
        permission_mapping = require_permission_mapping(
            adapter,
            permission_profile,
        )
        expected_tools = permission_mapping.get("tools")
        actual_tools = frontmatter.get("tools")

        if actual_tools != expected_tools:
            raise RuntimeError(
                f"{agent_path}: tools were {actual_tools!r}, "
                f"expected {expected_tools!r}"
            )

        actual_handoffs = parse_vscode_handoffs(
            agent_path,
            frontmatter_lines,
        )
        expected_handoffs = expected_vscode_handoffs(
            topology,
            agent_name,
        )

        if actual_handoffs != expected_handoffs:
            raise RuntimeError(
                f"{agent_path}: handoffs were {actual_handoffs!r}, "
                f"expected {expected_handoffs!r}"
            )

        unknown_handoffs = sorted(
            {
                handoff["agent"]
                for handoff in actual_handoffs
                if handoff.get("agent") not in expected_slugs
            }
        )
        if unknown_handoffs:
            raise RuntimeError(
                f"{agent_path}: references unknown handoff agents "
                f"{unknown_handoffs}"
            )

        if not body.strip():
            raise RuntimeError(f"{agent_path}: agent body is empty")

        assert_no_runtime_contract(
            agent_path,
            agent_path.read_text(encoding="utf-8"),
        )

    validate_skill_files(
        "vscode-copilot",
        ROOT / ".github" / "skills",
        skills,
    )

    instructions_path = ROOT / ".github" / "copilot-instructions.md"
    if not instructions_path.is_file() or not instructions_path.read_text(
        encoding="utf-8"
    ).strip():
        raise RuntimeError(
            ".github/copilot-instructions.md is missing or empty"
        )

    assert_no_runtime_contract(
        instructions_path,
        instructions_path.read_text(encoding="utf-8"),
    )


def validate_adapter_truth(
    target_name: str,
    adapter: dict[str, Any],
) -> None:
    if "templates" in adapter:
        raise RuntimeError(
            f"{target_name}: adapter must not declare unused templates"
        )

    output_paths = adapter.get("outputPaths")
    if not isinstance(output_paths, dict):
        raise RuntimeError(
            f"{target_name}: adapter outputPaths must be an object"
        )

    unsupported_output_keys = {
        "runtimeContext",
        "resolution",
    } & set(output_paths)

    if unsupported_output_keys:
        raise RuntimeError(
            f"{target_name}: adapter declares unsupported output paths "
            f"{sorted(unsupported_output_keys)}"
        )

    supported_features = adapter.get("supportedFeatures")
    if not isinstance(supported_features, dict):
        raise RuntimeError(
            f"{target_name}: adapter supportedFeatures must be an object"
        )

    if supported_features.get("runtimeContext") is not False:
        raise RuntimeError(
            f"{target_name}: runtimeContext must be false before Milestone 4"
        )


def opencode_skill_names(data: Any) -> set[str]:
    if isinstance(data, list):
        return {
            item["name"]
            for item in data
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
        }

    if isinstance(data, dict):
        candidates = data.get("skills", data)

        if isinstance(candidates, list):
            return {
                item["name"]
                for item in candidates
                if isinstance(item, dict)
                and isinstance(item.get("name"), str)
            }

        if isinstance(candidates, dict):
            return set(candidates)

    raise RuntimeError("Unsupported OpenCode debug skill JSON shape")


def run_opencode_runtime_validation(
    topology: Any,
    resolution_agents: dict[str, dict[str, Any]],
    skills: set[str],
) -> None:
    executable = shutil.which("opencode")

    if executable is None:
        raise RuntimeError(
            "OpenCode executable is required for runtime compatibility validation"
        )

    config_result = subprocess.run(
        [executable, "debug", "config"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if config_result.returncode != 0:
        raise RuntimeError(
            "OpenCode rejected generated configuration:\n"
            + config_result.stdout
        )

    try:
        effective_config = json.loads(config_result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "OpenCode debug config did not return valid JSON:\n"
            + config_result.stdout
        ) from error

    expected_default = kebab_case(topology.controller_agent)
    if effective_config.get("default_agent") != expected_default:
        raise RuntimeError(
            "OpenCode effective default_agent was "
            f"{effective_config.get('default_agent')!r}, "
            f"expected {expected_default!r}"
        )

    effective_agents = effective_config.get("agent")
    if not isinstance(effective_agents, dict):
        raise RuntimeError(
            "OpenCode effective configuration lacks an agent object"
        )

    for agent_name in resolution_agents:
        slug = kebab_case(agent_name)
        agent = effective_agents.get(slug)

        if not isinstance(agent, dict):
            raise RuntimeError(
                f"OpenCode did not discover generated agent {slug}"
            )

        expected_mode = opencode_mode_for_agent(topology, agent_name)
        if agent.get("mode") != expected_mode:
            raise RuntimeError(
                f"OpenCode effective mode for {slug} was "
                f"{agent.get('mode')!r}, expected {expected_mode!r}"
            )

    skill_result = subprocess.run(
        [executable, "debug", "skill"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if skill_result.returncode != 0:
        raise RuntimeError(
            "OpenCode rejected generated skills:\n"
            + skill_result.stdout
        )

    try:
        effective_skills = opencode_skill_names(
            json.loads(skill_result.stdout)
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "OpenCode debug skill did not return valid JSON:\n"
            + skill_result.stdout
        ) from error

    missing_skills = sorted(skills - effective_skills)
    if missing_skills:
        raise RuntimeError(
            f"OpenCode did not discover generated skills: {missing_skills}"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate generated OpenCode and VS Code Copilot output "
            "against resolved workflow, adapter, and permission contracts."
        )
    )
    parser.add_argument(
        "--require-opencode-runtime",
        action="store_true",
        help=(
            "Require the installed OpenCode CLI to parse the generated "
            "configuration, agents, and skills."
        ),
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        config = load_json(CONFIG_PATH)
        resolution = load_json(RESOLUTION_PATH)

        runtime_context = config.get("runtimeContext")
        if not isinstance(runtime_context, dict):
            raise RuntimeError(
                "agentic config runtimeContext must be an object"
            )

        if (
            runtime_context.get("enabled") is not False
            or runtime_context.get("failIfMissing") is not False
        ):
            raise RuntimeError(
                "Runtime context generation is unsupported before "
                "Milestone 4; enabled and failIfMissing must both be false."
            )

        config_agents = configured_agents(config)
        resolution_agents = resolved_agents(resolution)

        if set(config_agents) != set(resolution_agents):
            raise RuntimeError(
                "Configured and resolved agent sets differ: "
                f"configured={sorted(config_agents)}, "
                f"resolved={sorted(resolution_agents)}"
            )

        targets = enabled_targets(resolution)
        skills = selected_skills(resolution_agents)
        topology = derive_workflow_topology(resolution)

        checked_targets = 0

        for target_name in sorted(targets):
            adapter = load_json(
                TARGETS_DIRECTORY / target_name / "adapter.json"
            )
            validate_adapter_truth(target_name, adapter)

            if target_name == "opencode":
                validate_opencode(
                    config_agents,
                    resolution_agents,
                    adapter,
                    topology,
                    skills,
                )
            elif target_name == "vscode-copilot":
                validate_vscode(
                    config_agents,
                    resolution_agents,
                    adapter,
                    topology,
                    skills,
                )
            else:
                raise RuntimeError(
                    f"No compatibility validator exists for target {target_name}"
                )

            checked_targets += 1

        if (
            arguments.require_opencode_runtime
            and "opencode" in targets
        ):
            run_opencode_runtime_validation(
                topology,
                resolution_agents,
                skills,
            )

        print(
            "PASS: Target compatibility validation succeeded for "
            f"{checked_targets} enabled target(s)."
        )
        print(
            f"PASS: Validated {len(resolution_agents)} agent(s), "
            f"{len(skills)} selected skill(s), workflow modes, "
            "permissions, tools, and handoffs."
        )

        if arguments.require_opencode_runtime and "opencode" in targets:
            print(
                "PASS: OpenCode runtime parsed generated config, "
                "agents, and skills."
            )

        return 0
    except Exception as exc:
        print(f"FAIL: Target compatibility validation: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
