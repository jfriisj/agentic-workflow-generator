#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
SKILLS_DIR = ROOT / "registry" / "skills"
AGENTS_DIR = ROOT / "registry" / "agents"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def extract_capabilities(skill: dict[str, Any]) -> list[str]:
    candidates: list[Any] = []

    for key in [
        "capabilities",
        "provides",
        "providedCapabilities",
        "provided_capabilities",
    ]:
        value = skill.get(key)

        if isinstance(value, list):
            candidates.extend(value)

        if isinstance(value, dict):
            nested = value.get("capabilities")
            if isinstance(nested, list):
                candidates.extend(nested)

    single_capability = skill.get("capability")
    if isinstance(single_capability, str):
        candidates.append(single_capability)

    normalized: list[str] = []

    for capability in candidates:
        if isinstance(capability, str) and capability.strip():
            normalized.append(capability.strip())
        elif isinstance(capability, dict):
            raw_value = (
                capability.get("name")
                or capability.get("id")
                or capability.get("capability")
            )
            if raw_value is not None and str(raw_value).strip():
                normalized.append(str(raw_value).strip())

    return normalized


def validate_provides_field(
    skill_json: Path,
    skill: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    provides = skill.get("provides")

    if not isinstance(provides, list) or not provides:
        return [f"{skill_json}: provides must be a non-empty list"]

    seen_capabilities: set[str] = set()

    for index, capability in enumerate(provides):
        if not isinstance(capability, str) or not capability.strip():
            errors.append(
                f"{skill_json}: provides[{index}] must be a non-empty string"
            )
            continue

        normalized = capability.strip()

        if normalized in seen_capabilities:
            errors.append(f"{skill_json}: provides[{index}] is duplicated")

        seen_capabilities.add(normalized)

    return errors


def validate_reference_list(
    skill_json: Path,
    skill: dict[str, Any],
    field: str,
    available_values: set[str],
    reference_kind: str,
) -> list[str]:
    errors: list[str] = []
    values = skill.get(field)

    if values is None:
        return errors

    if not isinstance(values, list):
        return [f"{skill_json}: {field} must be a list when present"]

    seen: set[str] = set()

    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"{skill_json}: {field}[{index}] must be a non-empty string"
            )
            continue

        normalized = value.strip()

        if normalized in seen:
            errors.append(
                f"{skill_json}: {field}[{index}] is duplicated"
            )
            continue

        seen.add(normalized)

        if normalized not in available_values:
            errors.append(
                f"{skill_json}: {field} entry '{normalized}' must reference "
                f"an existing {reference_kind}"
            )

    return errors


def load_agent_names() -> tuple[set[str], list[str]]:
    errors: list[str] = []
    agent_names: set[str] = set()

    if not AGENTS_DIR.is_dir():
        return set(), [f"Required directory not found: {AGENTS_DIR}"]

    for agent_json in sorted(AGENTS_DIR.glob("*/agent.json")):
        try:
            agent = load_json(agent_json)
        except Exception as exc:
            errors.append(f"{agent_json}: {exc}")
            continue

        name = agent.get("name")

        if not isinstance(name, str) or not name.strip():
            errors.append(
                f"{agent_json}: name must be a non-empty string"
            )
            continue

        normalized = name.strip()

        if normalized in agent_names:
            errors.append(
                f"{agent_json}: duplicate agent name '{normalized}'"
            )
            continue

        agent_names.add(normalized)

    if not agent_names and not errors:
        errors.append(f"No registered agents found under {AGENTS_DIR}")

    return agent_names, errors


def collect_capability_sources(
    skill_dirs: list[Path],
) -> tuple[dict[str, Path], list[str]]:
    errors: list[str] = []
    capability_sources: dict[str, Path] = {}

    for skill_dir in skill_dirs:
        skill_json = skill_dir / "skill.json"

        if not skill_json.is_file():
            continue

        try:
            skill = load_json(skill_json)
        except Exception:
            continue

        local_capabilities = sorted(set(extract_capabilities(skill)))

        for capability in local_capabilities:
            existing_source = capability_sources.get(capability)

            if existing_source is not None and existing_source != skill_json:
                errors.append(
                    f"{skill_json}: capability '{capability}' is already "
                    f"provided by {existing_source}"
                )
                continue

            capability_sources[capability] = skill_json

    return capability_sources, errors


def validate_skill_dir(
    skill_dir: Path,
    agent_names: set[str],
    capability_names: set[str],
) -> list[str]:
    errors: list[str] = []
    skill_json = skill_dir / "skill.json"
    skill_md = skill_dir / "SKILL.md"
    folder_name = skill_dir.name

    if not skill_json.is_file():
        errors.append(f"{skill_dir}: missing skill.json")
        return errors

    if not skill_md.is_file():
        errors.append(f"{skill_dir}: missing SKILL.md")

    try:
        skill = load_json(skill_json)
    except Exception as exc:
        return [f"{skill_json}: {exc}"]

    name = skill.get("name")

    if not isinstance(name, str) or not name.strip():
        errors.append(f"{skill_json}: name must be a non-empty string")
    elif name != folder_name:
        errors.append(
            f"{skill_json}: name '{name}' does not match folder "
            f"'{folder_name}'"
        )

    description = skill.get("description")
    if description is not None and not isinstance(description, str):
        errors.append(
            f"{skill_json}: description must be a string when present"
        )

    version = skill.get("version")
    if version is not None and (
        not isinstance(version, str) or not version.strip()
    ):
        errors.append(
            f"{skill_json}: version must be a non-empty string when present"
        )

    errors.extend(validate_provides_field(skill_json, skill))

    capabilities = extract_capabilities(skill)

    if not capabilities:
        errors.append(
            f"{skill_json}: must declare at least one capability using "
            "capabilities, provides, providedCapabilities, "
            "provided_capabilities, or capability"
        )

    duplicate_capabilities = sorted(
        capability
        for capability in set(capabilities)
        if capabilities.count(capability) > 1
    )

    if duplicate_capabilities:
        errors.append(
            f"{skill_json}: duplicate capabilities: "
            f"{', '.join(duplicate_capabilities)}"
        )

    errors.extend(
        validate_reference_list(
            skill_json,
            skill,
            "recommendedAgents",
            agent_names,
            "agent",
        )
    )

    errors.extend(
        validate_reference_list(
            skill_json,
            skill,
            "requiresCapabilities",
            capability_names,
            "capability",
        )
    )

    own_capabilities = set(capabilities)
    required_capabilities = skill.get("requiresCapabilities")

    if isinstance(required_capabilities, list):
        for capability in required_capabilities:
            if (
                isinstance(capability, str)
                and capability.strip() in own_capabilities
            ):
                errors.append(
                    f"{skill_json}: requiresCapabilities entry "
                    f"'{capability.strip()}' is provided by the same skill"
                )

    return errors


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"FAIL: Required directory not found: {SKILLS_DIR}")
        return 1

    skill_dirs = sorted(
        path for path in SKILLS_DIR.iterdir() if path.is_dir()
    )

    if not skill_dirs:
        print("FAIL: No skill directories found.")
        return 1

    agent_names, agent_errors = load_agent_names()
    capability_sources, capability_errors = collect_capability_sources(
        skill_dirs
    )
    capability_names = set(capability_sources)

    errors: list[str] = []
    errors.extend(agent_errors)
    errors.extend(capability_errors)

    for skill_dir in skill_dirs:
        errors.extend(
            validate_skill_dir(
                skill_dir,
                agent_names,
                capability_names,
            )
        )

    if errors:
        print(
            f"FAIL: Skill registry validation found "
            f"{len(errors)} error(s)."
        )
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"PASS: Skill registry is valid. Checked {len(skill_dirs)} "
        f"skill directorie(s), {len(capability_names)} capability "
        f"provider(s), and {len(agent_names)} agent profile(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
