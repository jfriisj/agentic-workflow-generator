#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
RESOLUTION_PATH = ROOT / ".agentic" / "generated" / "resolution.json"
SKILLS_DIR = ROOT / "registry" / "skills"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def kebab_case(value: str) -> str:
    value = value.strip()
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-").lower()


def required_file(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing generated file: {path.relative_to(ROOT)}")
        return

    if path.stat().st_size == 0:
        errors.append(f"generated file is empty: {path.relative_to(ROOT)}")


def enabled_targets(resolution: dict[str, Any]) -> set[str]:
    targets = resolution.get("targets", [])
    enabled: set[str] = set()

    if not isinstance(targets, list):
        return enabled

    for target in targets:
        if not isinstance(target, dict):
            continue

        name = target.get("name")
        is_enabled = bool(target.get("enabled", False))
        missing = bool(target.get("missing", False))

        if isinstance(name, str) and is_enabled and not missing:
            enabled.add(name)

    return enabled


def agent_names(resolution: dict[str, Any]) -> list[str]:
    agents = resolution.get("agents", [])
    names: list[str] = []

    if not isinstance(agents, list):
        return names

    for agent in agents:
        if not isinstance(agent, dict):
            continue

        name = agent.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())

    return names


def skill_names_from_registry() -> list[str]:
    return sorted(
        path.parent.name
        for path in SKILLS_DIR.glob("*/skill.json")
        if path.is_file()
    )


def validate_vscode_output(agents: list[str], skills: list[str]) -> list[str]:
    errors: list[str] = []

    required_file(ROOT / ".github" / "copilot-instructions.md", errors)

    for agent_name in agents:
        required_file(
            ROOT / ".github" / "agents" / f"{kebab_case(agent_name)}.agent.md",
            errors,
        )

    for skill_name in skills:
        required_file(
            ROOT / ".github" / "skills" / skill_name / "SKILL.md",
            errors,
        )

    return errors


def validate_opencode_output(agents: list[str], skills: list[str]) -> list[str]:
    errors: list[str] = []

    required_file(ROOT / "AGENTS.md", errors)
    required_file(ROOT / "opencode.json", errors)

    for agent_name in agents:
        required_file(
            ROOT / ".opencode" / "agents" / f"{kebab_case(agent_name)}.md",
            errors,
        )

    for skill_name in skills:
        required_file(
            ROOT / ".opencode" / "skills" / skill_name / "SKILL.md",
            errors,
        )

    return errors


def main() -> int:
    errors: list[str] = []

    try:
        resolution = load_json(RESOLUTION_PATH)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    targets = enabled_targets(resolution)
    agents = agent_names(resolution)
    skills = skill_names_from_registry()

    if not targets:
        errors.append(f"{RESOLUTION_PATH}: expected at least one enabled generated target")

    if not agents:
        errors.append(f"{RESOLUTION_PATH}: expected at least one resolved agent")

    if not skills:
        errors.append(f"{SKILLS_DIR}: expected at least one registered skill")

    if "vscode-copilot" in targets:
        errors.extend(validate_vscode_output(agents, skills))

    if "opencode" in targets:
        errors.extend(validate_opencode_output(agents, skills))

    if errors:
        print(f"FAIL: Generated output validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Generated output is valid.")
    print(f"Targets: {', '.join(sorted(targets))}")
    print(f"Agents: {len(agents)}")
    print(f"Skills: {len(skills)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
