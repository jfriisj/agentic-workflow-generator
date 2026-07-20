#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
SETUP_PROFILE_PATH = ROOT / ".agentic" / "setup-profile.json"
SETUP_PROFILE_VALIDATOR = ROOT / "scripts" / "agentic" / "validate-setup-profile.py"
SETUP_REGISTRY_VALIDATOR = ROOT / "scripts" / "agentic" / "validate-setup-registry.py"
CONFIG_VALIDATOR = ROOT / "scripts" / "agentic" / "validate-agentic-config.sh"
CONFIG_SCHEMA_PATH = ROOT / ".agentic" / "schemas" / "agentic.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def require_string(data: dict[str, Any], field: str, path: Path) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {field} must be a non-empty string")
    return value


def require_string_list(
    data: dict[str, Any],
    field: str,
    path: Path,
) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path}: {field} must be a non-empty list")

    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{path}: {field}[{index}] must be a non-empty string"
            )
        result.append(item)

    return result


def load_setup(setup_name: str) -> tuple[Path, dict[str, Any]]:
    path = ROOT / "registry" / "setups" / f"{setup_name}.setup.json"
    if not path.is_file():
        raise ValueError(f"Unknown setup '{setup_name}'")

    setup = load_json(path)
    actual_name = require_string(setup, "name", path)
    if actual_name != setup_name:
        raise ValueError(
            f"{path}: setup name '{actual_name}' "
            f"does not match requested setup '{setup_name}'"
        )

    return path, setup
