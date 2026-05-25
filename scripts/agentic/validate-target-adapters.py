#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
TARGETS_DIR = ROOT / "registry" / "targets"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def validate_adapter_file(adapter_path: Path) -> list[str]:
    errors: list[str] = []
    target_name = adapter_path.parent.name

    try:
        adapter = load_json(adapter_path)
    except Exception as exc:
        return [f"{adapter_path}: {exc}"]

    declared_name = adapter.get("name")
    if declared_name is not None and declared_name != target_name:
        errors.append(
            f"{adapter_path}: declared name '{declared_name}' does not match target folder '{target_name}'"
        )

    permission_mapping = adapter.get("permissionMapping")
    if permission_mapping is not None and not isinstance(permission_mapping, dict):
        errors.append(f"{adapter_path}: permissionMapping must be an object when present")

    output = adapter.get("output")
    if output is not None and not isinstance(output, dict):
        errors.append(f"{adapter_path}: output must be an object when present")

    return errors


def validate_config_targets(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for target in config.get("targets", []):
        if not isinstance(target, dict):
            errors.append(".agentic/agentic.json: target entries must be objects")
            continue

        target_name = target.get("name")
        enabled = bool(target.get("enabled", False))

        if not isinstance(target_name, str) or not target_name.strip():
            errors.append(".agentic/agentic.json: target.name must be a non-empty string")
            continue

        adapter_path = TARGETS_DIR / target_name / "adapter.json"

        if enabled and not adapter_path.is_file():
            errors.append(
                f".agentic/agentic.json: enabled target '{target_name}' is missing adapter: "
                f"{adapter_path.relative_to(ROOT)}"
            )

    return errors


def main() -> int:
    errors: list[str] = []

    config = load_json(CONFIG_PATH)
    errors.extend(validate_config_targets(config))

    adapter_files = sorted(TARGETS_DIR.glob("*/adapter.json"))

    for adapter_path in adapter_files:
        errors.extend(validate_adapter_file(adapter_path))

    if errors:
        print(f"FAIL: Target adapter validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Target adapters are valid. Checked {len(adapter_files)} adapter file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
