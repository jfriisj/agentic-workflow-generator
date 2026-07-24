#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from target_generation_support import (
    WorkflowTopology,
    deduplicated_resolved_skills,
    derive_workflow_topology,
    handoffs_for_agent,
    require_permission_mapping,
    yaml_string,
)

ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
RESOLUTION_PATH = ROOT / ".agentic" / "generated" / "resolution.json"
REGISTRY_PATH = ROOT / "registry"

AGENTS_OUTPUT_DIR = ROOT / ".github" / "agents"
SKILLS_OUTPUT_DIR = ROOT / ".github" / "skills"
INSTRUCTIONS_OUTPUT_PATH = ROOT / ".github" / "copilot-instructions.md"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def reset_owned_directory(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"Refusing to reset owned output through symlink: {path}")

    if path.exists():
        if not path.is_dir():
            raise RuntimeError(f"Owned output path is not a directory: {path}")
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=False)


def slugify(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = value.replace("_", "-").replace(" ", "-")
    value = re.sub(r"[^a-zA-Z0-9-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-").lower()


def markdown_list(values: list[str]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {value}" for value in values)


def find_config_agent(config: dict[str, Any], agent_name: str) -> dict[str, Any]:
    for agent in config.get("agents", []):
        if agent.get("name") == agent_name:
            return agent
    raise RuntimeError(f"Agent not found in config: {agent_name}")


def require_supported_runtime_context(config: dict[str, Any]) -> None:
    runtime_context = config.get("runtimeContext")
    if not isinstance(runtime_context, dict):
        raise RuntimeError("runtimeContext must be an object.")

    enabled = runtime_context.get("enabled")
    fail_if_missing = runtime_context.get("failIfMissing")

    if enabled is not False or fail_if_missing is not False:
        raise RuntimeError(
            "Runtime context generation is not implemented until Milestone 4; "
            "runtimeContext.enabled and runtimeContext.failIfMissing must both be false."
        )


def render_produced_artifacts(produces: list[dict[str, Any]]) -> str:
    if not produces:
        return """## Produced Artifacts

This agent does not declare a produced artifact contract.
"""

    blocks: list[str] = [
        "## Produced Artifacts",
        "",
        "When this agent completes work, it must produce output that matches the declared artifact contract.",
    ]

    for artifact in produces:
        artifact_type = artifact["type"]
        contract_path = artifact.get("contractPath", "missing")
        path_pattern = artifact.get("pathPattern", "missing")
        allowed_statuses = artifact.get("allowedStatuses", [])
        required_headings = artifact.get("requiredHeadings", [])

        blocks.extend(
            [
                "",
                f"### {artifact_type}",
                "",
                f"- contract: `{contract_path}`",
                f"- output path pattern: `{path_pattern}`",
                f"- allowed statuses: {', '.join(allowed_statuses)}",
                "",
                "Required headings:",
                "",
                markdown_list(required_headings),
            ]
        )

    return "\n".join(blocks) + "\n"


def render_handoffs(
    topology: WorkflowTopology,
    agent_name: str,
) -> str:
    handoffs = handoffs_for_agent(topology, agent_name)
    if not handoffs:
        return ""

    lines = ["handoffs:"]
    for handoff in handoffs:
        lines.extend(
            [
                f"  - label: {yaml_string(handoff['label'])}",
                f"    agent: {yaml_string(slugify(handoff['agent']))}",
                f"    prompt: {yaml_string(handoff['prompt'])}",
                "    send: false",
            ]
        )

    return "\n".join(lines) + "\n"


def generate_agent_file(
    config_agent: dict[str, Any],
    resolved_agent: dict[str, Any],
    adapter: dict[str, Any],
    topology: WorkflowTopology,
) -> str:
    name = config_agent["name"]
    role = config_agent["role"]
    description = config_agent["description"]
    permission_profile = config_agent["permissionProfile"]
    capabilities = config_agent.get("capabilities", [])
    must_not = config_agent.get("mustNot", [])
    resolved_skills = deduplicated_resolved_skills(resolved_agent)
    produces = resolved_agent.get("produces", [])
    permission = require_permission_mapping(adapter, permission_profile)
    tools = permission.get("tools")

    if (
        not isinstance(tools, list)
        or not tools
        or not all(isinstance(tool, str) and tool.strip() for tool in tools)
    ):
        raise RuntimeError(
            f"VS Code permission mapping for {permission_profile} "
            "must declare a non-empty tools list."
        )

    tools_frontmatter = json.dumps(tools, ensure_ascii=False)
    handoffs_frontmatter = render_handoffs(topology, name)

    return f"""---
name: {yaml_string(name)}
description: {yaml_string(description)}
tools: {tools_frontmatter}
{handoffs_frontmatter}---

# {name}

## Role

{role}

## Description

{description}

## Operating Rules

1. Stay inside your assigned role.
2. Do not invent missing workflow state.
3. If required evidence is missing, stop and report `BLOCKED: Missing required evidence`.
4. Do not override fail-closed gates.

## Permission Profile

~~~text
{permission_profile}
~~~

## VS Code Tools

{markdown_list(tools)}

## Capabilities

{markdown_list(capabilities)}

## Resolved Skills

{markdown_list(resolved_skills)}

## Must Not

{markdown_list(must_not)}

{render_produced_artifacts(produces)}
## Output Expectations

When producing an artifact, include:

- status: PASS, FAIL, or BLOCKED
- summary
- evidence reviewed
- findings
- required fixes
- handoff target
"""


def generate_instructions(config: dict[str, Any]) -> str:
    project = config.get("project", {})
    workflow = config.get("workflow", {})
    agents = [agent["name"] for agent in config.get("agents", [])]
    gates = [gate["name"] for gate in config.get("gates", [])]

    return f"""# Copilot Instructions

This repository uses generated agentic workflow infrastructure.

## Project

- name: {project.get("name")}
- type: {project.get("type")}
- architecture profile: {project.get("architectureProfile")}

## Workflow

- profile: {workflow.get("profile")}
- start state: {workflow.get("startState")}
- terminal states: {", ".join(workflow.get("terminalStates", []))}
- fail closed: {workflow.get("failClosed")}

## Agents

{markdown_list(agents)}

## Gates

{markdown_list(gates)}

## Core Rules

1. The workflow is fail-closed.
2. Artifacts are workflow memory.
3. The orchestrator owns routing and state transitions.
4. Agents must stay within their role.
5. Missing evidence must result in BLOCKED, not PASS.
6. Generated files should not be manually edited unless the project explicitly allows overrides.

## Generated Metadata

Resolution metadata is generated under:

~~~text
.agentic/generated/
~~~
"""


def copy_resolved_skills(resolution: dict[str, Any]) -> None:
    copied: set[str] = set()

    for agent in resolution.get("agents", []):
        for resolved in agent.get("resolvedCapabilities", []):
            skill_name = resolved["skill"]

            if skill_name in copied:
                continue

            skill_path = REGISTRY_PATH / "skills" / skill_name
            output_path = SKILLS_OUTPUT_DIR / skill_name

            if not skill_path.is_dir():
                raise RuntimeError(f"Resolved skill directory does not exist: {skill_path}")

            if output_path.exists():
                shutil.rmtree(output_path)

            shutil.copytree(skill_path, output_path)
            copied.add(skill_name)


def main() -> int:
    config = load_json(CONFIG_PATH)
    resolution = load_json(RESOLUTION_PATH)
    require_supported_runtime_context(config)

    if resolution.get("summary", {}).get("errorCount", 0) != 0:
        raise RuntimeError("Resolution contains errors. Run resolver first and fix all reported errors.")

    enabled_targets = {
        target["name"]: target
        for target in resolution.get("targets", [])
        if target.get("enabled")
    }

    if "vscode-copilot" not in enabled_targets:
        raise RuntimeError("vscode-copilot target is not enabled or not resolved.")

    adapter_path_raw = enabled_targets["vscode-copilot"].get("adapterPath")
    if not adapter_path_raw:
        raise RuntimeError(
            "vscode-copilot adapter path is missing from resolution."
        )

    adapter = load_json(ROOT / adapter_path_raw)
    topology = derive_workflow_topology(resolution)

    reset_owned_directory(AGENTS_OUTPUT_DIR)
    reset_owned_directory(SKILLS_OUTPUT_DIR)

    for resolved_agent in resolution.get("agents", []):
        agent_name = resolved_agent["name"]
        config_agent = find_config_agent(config, agent_name)
        output_path = AGENTS_OUTPUT_DIR / f"{slugify(agent_name)}.agent.md"
        write_text(
            output_path,
            generate_agent_file(
                config_agent,
                resolved_agent,
                adapter,
                topology,
            ),
        )

    copy_resolved_skills(resolution)
    write_text(INSTRUCTIONS_OUTPUT_PATH, generate_instructions(config))

    print("PASS: Generated VS Code Copilot output.")
    print(f"Agents: {AGENTS_OUTPUT_DIR}")
    print(f"Skills: {SKILLS_OUTPUT_DIR}")
    print(f"Instructions: {INSTRUCTIONS_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
