#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
AGENTS_DIR = ROOT / "registry" / "agents"
SKILLS_DIR = ROOT / "registry" / "skills"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def extract_skill_capabilities(skill: dict[str, Any]) -> list[str]:
    capabilities: list[str] = []

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
                    capabilities.append(entry.strip())
                elif isinstance(entry, dict):
                    raw = entry.get("name") or entry.get("id") or entry.get("capability")
                    if raw is not None and str(raw).strip():
                        capabilities.append(str(raw).strip())

        elif isinstance(value, dict):
            nested = value.get("capabilities")
            if isinstance(nested, list):
                for entry in nested:
                    if isinstance(entry, str) and entry.strip():
                        capabilities.append(entry.strip())

    single = skill.get("capability")
    if isinstance(single, str) and single.strip():
        capabilities.append(single.strip())

    return capabilities


def main() -> int:
    agent_capabilities: dict[str, list[str]] = {}
    skill_capabilities: dict[str, list[str]] = {}

    for path in sorted(AGENTS_DIR.glob("*/agent.json")):
        agent = load_json(path)

        for capability in agent.get("capabilities", []):
            if isinstance(capability, str) and capability.strip():
                agent_capabilities.setdefault(capability.strip(), []).append(path.parent.name)

    for path in sorted(SKILLS_DIR.glob("*/skill.json")):
        skill = load_json(path)

        for capability in extract_skill_capabilities(skill):
            skill_capabilities.setdefault(capability, []).append(path.parent.name)

    agent_caps = set(agent_capabilities)
    skill_caps = set(skill_capabilities)

    missing_skill_coverage = sorted(agent_caps - skill_caps)
    unused_skill_capabilities = sorted(skill_caps - agent_caps)
    duplicate_skill_capabilities = {
        capability: providers
        for capability, providers in skill_capabilities.items()
        if len(providers) > 1
    }

    print(f"Agent capabilities: {len(agent_caps)}")
    print(f"Skill capabilities: {len(skill_caps)}")
    print()

    print("Missing skill coverage:")
    if missing_skill_coverage:
        for capability in missing_skill_coverage:
            providers = ", ".join(agent_capabilities[capability])
            print(f"  - {capability} required by agents: {providers}")
    else:
        print("  none")

    print()
    print("Unused skill capabilities:")
    if unused_skill_capabilities:
        for capability in unused_skill_capabilities:
            providers = ", ".join(skill_capabilities[capability])
            print(f"  - {capability} provided by skills: {providers}")
    else:
        print("  none")

    print()
    print("Duplicate skill capabilities:")
    if duplicate_skill_capabilities:
        for capability, providers in sorted(duplicate_skill_capabilities.items()):
            print(f"  - {capability}: {', '.join(providers)}")
    else:
        print("  none")

    if missing_skill_coverage or unused_skill_capabilities or duplicate_skill_capabilities:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
