#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
RESOLUTION_PATH = ROOT / ".agentic" / "generated" / "resolution.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def walk_for_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []

    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"

            if key in {"errors", "unresolved", "missing", "missingCapabilities"}:
                if isinstance(nested, list) and nested:
                    errors.append(f"{nested_path}: expected empty list, found {len(nested)} item(s)")
                elif isinstance(nested, dict) and nested:
                    errors.append(f"{nested_path}: expected empty object, found {len(nested)} item(s)")

            errors.extend(walk_for_errors(nested, nested_path))

    elif isinstance(value, list):
        for index, nested in enumerate(value):
            errors.extend(walk_for_errors(nested, f"{path}[{index}]"))

    return errors


def has_non_empty_collection(resolution: dict[str, Any], key: str) -> bool:
    value = resolution.get(key)

    if isinstance(value, list):
        return bool(value)

    if isinstance(value, dict):
        return bool(value)

    return False


def main() -> int:
    errors: list[str] = []

    try:
        resolution = load_json(RESOLUTION_PATH)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    for required_key in ["agents", "targets", "skills"]:
        if not has_non_empty_collection(resolution, required_key):
            errors.append(f"{RESOLUTION_PATH}: expected non-empty '{required_key}' collection")

    errors.extend(walk_for_errors(resolution))

    if errors:
        print(f"FAIL: Resolution output validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Resolution output is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
