#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
AGENTS_DIR = ROOT / "registry" / "agents"
ARTIFACTS_DIR = ROOT / "registry" / "artifacts"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def artifact_contract_path(artifact_type: str) -> Path:
    return ARTIFACTS_DIR / artifact_type / "artifact.json"


def artifact_contract_exists(artifact_type: str) -> bool:
    return artifact_contract_path(artifact_type).is_file()


def collect_artifact_contracts() -> dict[str, Path]:
    contracts: dict[str, Path] = {}

    for artifact_path in sorted(ARTIFACTS_DIR.glob("*/artifact.json")):
        try:
            artifact = load_json(artifact_path)
        except Exception:
            continue

        artifact_type = artifact.get("type")
        if isinstance(artifact_type, str) and artifact_type.strip():
            contracts[artifact_type] = artifact_path

    return contracts


def validate_artifact_binding_policy(
    artifact_path: Path,
    artifact: dict[str, Any],
    produced_by: dict[str, list[str]],
) -> list[str]:
    errors: list[str] = []

    artifact_type = artifact.get("type")
    if not isinstance(artifact_type, str) or not artifact_type.strip():
        return [f"{artifact_path}: type must be a non-empty string"]

    binding = artifact.get("binding")
    producer_required = True

    if binding is not None:
        if not isinstance(binding, dict):
            return [f"{artifact_path}: binding must be an object when present"]

        raw_producer_required = binding.get("producerRequired")
        if not isinstance(raw_producer_required, bool):
            errors.append(f"{artifact_path}: binding.producerRequired must be a boolean")
        else:
            producer_required = raw_producer_required

        reason = binding.get("reason")
        if producer_required is False and (not isinstance(reason, str) or not reason.strip()):
            errors.append(f"{artifact_path}: binding.reason must be a non-empty string when producerRequired is false")

    producers = produced_by.get(artifact_type, [])

    if producer_required and not producers:
        errors.append(f"{artifact_path}: artifact contract is not produced by any agent")

    if not producer_required and producers:
        errors.append(f"{artifact_path}: binding.producerRequired is false but artifact is produced by agent(s): {', '.join(producers)}")

    return errors


def validate_reference_list(
    agent_file: Path,
    agent_name: str,
    agent: dict[str, Any],
    key: str,
) -> tuple[list[str], int, list[str]]:
    errors: list[str] = []
    checked_bindings = 0
    artifact_types: list[str] = []

    values = agent.get(key, [])

    if values is None:
        values = []

    if not isinstance(values, list):
        return [f"{agent_file}: {key} must be a list when present"], checked_bindings, artifact_types

    seen_values: set[str] = set()

    for index, artifact_type in enumerate(values):
        checked_bindings += 1

        if not isinstance(artifact_type, str) or not artifact_type.strip():
            errors.append(f"{agent_file}: {key}[{index}] must be a non-empty string")
            continue

        if artifact_type in seen_values:
            errors.append(f"{agent_file}: {key} entry '{artifact_type}' is duplicated")
            continue

        seen_values.add(artifact_type)
        artifact_types.append(artifact_type)

        if not artifact_contract_exists(artifact_type):
            errors.append(
                f"{agent_file}: agent {agent_name} {key} missing artifact contract: "
                f"registry/artifacts/{artifact_type}/artifact.json"
            )

    return errors, checked_bindings, artifact_types


def main() -> int:
    agent_files = sorted(AGENTS_DIR.glob("*/agent.json"))

    if not agent_files:
        print("WARN: No agent registry files found.")
        return 0

    errors: list[str] = []
    checked_bindings = 0
    produced_by: dict[str, list[str]] = {}

    for agent_file in agent_files:
        try:
            agent = load_json(agent_file)
        except Exception as exc:
            errors.append(f"{agent_file}: {exc}")
            continue

        raw_agent_name = agent.get("name", agent_file.parent.name)
        agent_name = raw_agent_name if isinstance(raw_agent_name, str) and raw_agent_name.strip() else agent_file.parent.name

        produces_errors, produces_count, produced_artifacts = validate_reference_list(
            agent_file,
            agent_name,
            agent,
            "produces",
        )
        errors.extend(produces_errors)
        checked_bindings += produces_count

        for artifact_type in produced_artifacts:
            produced_by.setdefault(artifact_type, []).append(agent_name)

        required_errors, required_count, _required_artifacts = validate_reference_list(
            agent_file,
            agent_name,
            agent,
            "requiredArtifacts",
        )
        errors.extend(required_errors)
        checked_bindings += required_count

    for artifact_type, artifact_path in collect_artifact_contracts().items():
        try:
            artifact = load_json(artifact_path)
        except Exception as exc:
            errors.append(f"{artifact_path}: {exc}")
            continue

        errors.extend(validate_artifact_binding_policy(artifact_path, artifact, produced_by))

    if errors:
        print(f"FAIL: Agent artifact binding validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Agent artifact bindings are valid. Checked {checked_bindings} binding(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
