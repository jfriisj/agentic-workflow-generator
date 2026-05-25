#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

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


def generate_agent_file(config_agent: dict[str, Any], resolved_agent: dict[str, Any]) -> str:
    name = config_agent["name"]
    role = config_agent["role"]
    description = config_agent["description"]
    permission_profile = config_agent["permissionProfile"]
    capabilities = config_agent.get("capabilities", [])
    must_not = config_agent.get("mustNot", [])
    resolved_capabilities = resolved_agent.get("resolvedCapabilities", [])
    resolved_skills = [item["skill"] for item in resolved_capabilities]
    produces = resolved_agent.get("produces", [])
    runtime_context_path = f".runtime/context/{{{{WORKFLOW_ID}}}}-{name}.context.md"

    return f"""---
name: {name}
description: {description}
---

# {name}

## Role

{role}

## Description

{description}

## Operating Rules

1. Stay inside your assigned role.
2. Use only the generated runtime context for workflow-specific knowledge.
3. Do not invent missing workflow state.
4. If required runtime context is missing, stop and report `BLOCKED: Missing generated runtime context`.
5. If required evidence is missing, stop and report `BLOCKED: Missing required evidence`.
6. Do not override fail-closed gates.

## Runtime Context Requirement

Before doing any work, load this generated runtime context:

~~~text
{runtime_context_path}
~~~

If the file is missing, do not continue.

## Permission Profile

~~~text
{permission_profile}
~~~

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
5. Agents must use generated runtime context when available.
6. Missing evidence must result in BLOCKED, not PASS.
7. Generated files should not be manually edited unless the project explicitly allows overrides.

## Generated Context

Runtime context is generated under:

~~~text
.runtime/context/
~~~

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

    if resolution.get("summary", {}).get("errorCount", 0) != 0:
        raise RuntimeError("Resolution contains errors. Run resolver first and fix all reported errors.")

    AGENTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for resolved_agent in resolution.get("agents", []):
        agent_name = resolved_agent["name"]
        config_agent = find_config_agent(config, agent_name)
        output_path = AGENTS_OUTPUT_DIR / f"{slugify(agent_name)}.agent.md"
        write_text(output_path, generate_agent_file(config_agent, resolved_agent))

    copy_resolved_skills(resolution)
    write_text(INSTRUCTIONS_OUTPUT_PATH, generate_instructions(config))

    print("PASS: Generated VS Code Copilot output.")
    print(f"Agents: {AGENTS_OUTPUT_DIR}")
    print(f"Skills: {SKILLS_OUTPUT_DIR}")
    print(f"Instructions: {INSTRUCTIONS_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
