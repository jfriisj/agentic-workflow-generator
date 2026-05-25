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
        return json.load(file)


def artifact_contract_exists(artifact_type: str) -> bool:
    return (ARTIFACTS_DIR / artifact_type / "artifact.json").is_file()


def main() -> int:
    agent_files = sorted(AGENTS_DIR.glob("*/agent.json"))

    if not agent_files:
        print("WARN: No agent registry files found.")
        return 0

    errors: list[str] = []
    checked_bindings = 0

    for agent_file in agent_files:
        try:
            agent = load_json(agent_file)
        except Exception as exc:
            errors.append(f"{agent_file}: {exc}")
            continue

        agent_name = agent.get("name", agent_file.parent.name)
        produces = agent.get("produces", [])

        if produces is None:
            produces = []

        if not isinstance(produces, list):
            errors.append(f"{agent_file}: produces must be a list when present")
            continue

        for artifact_type in produces:
            checked_bindings += 1

            if not isinstance(artifact_type, str) or not artifact_type.strip():
                errors.append(f"{agent_file}: produces entries must be non-empty strings")
                continue

            if not artifact_contract_exists(artifact_type):
                errors.append(
                    f"{agent_file}: agent {agent_name} produces missing artifact contract: "
                    f"registry/artifacts/{artifact_type}/artifact.json"
                )

    if errors:
        print(f"FAIL: Agent artifact binding validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Agent artifact bindings are valid. Checked {checked_bindings} binding(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
