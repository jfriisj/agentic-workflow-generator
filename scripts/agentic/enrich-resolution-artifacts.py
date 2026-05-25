#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
RESOLUTION_PATH = ROOT / ".agentic" / "generated" / "resolution.json"
AGENTS_DIR = ROOT / "registry" / "agents"
ARTIFACTS_DIR = ROOT / "registry" / "artifacts"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def load_agent_registry(agent_name: str) -> dict[str, Any]:
    return load_json(AGENTS_DIR / agent_name / "agent.json")


def load_artifact_contract(artifact_type: str) -> tuple[Path, dict[str, Any]]:
    contract_path = ARTIFACTS_DIR / artifact_type / "artifact.json"
    return contract_path, load_json(contract_path)


def artifact_metadata(artifact_type: str) -> dict[str, Any]:
    contract_path, contract = load_artifact_contract(artifact_type)

    return {
        "type": artifact_type,
        "contractPath": str(contract_path.relative_to(ROOT)),
        "pathPattern": contract.get("pathPattern"),
        "allowedStatuses": contract.get("allowedStatuses", []),
        "requiredHeadings": contract.get("requiredHeadings", []),
    }


def main() -> int:
    resolution = load_json(RESOLUTION_PATH)

    agents = resolution.get("agents", [])
    if not isinstance(agents, list):
        raise RuntimeError("resolution.agents must be a list")

    enriched_count = 0

    for resolved_agent in agents:
        agent_name = resolved_agent.get("name")
        if not agent_name:
            raise RuntimeError("Resolved agent is missing name")

        registry_agent = load_agent_registry(agent_name)
        produces = registry_agent.get("produces", [])

        if produces is None:
            produces = []

        if not isinstance(produces, list):
            raise RuntimeError(f"registry/agents/{agent_name}/agent.json: produces must be a list")

        resolved_agent["produces"] = [artifact_metadata(artifact_type) for artifact_type in produces]
        enriched_count += len(produces)

    write_json(RESOLUTION_PATH, resolution)

    print(f"PASS: Enriched resolution with {enriched_count} produced artifact binding(s).")
    print(f"Resolution: {RESOLUTION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
