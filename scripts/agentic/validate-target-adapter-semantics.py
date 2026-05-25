#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
TARGET_REGISTRY = ROOT / "registry" / "targets"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def is_safe_relative_path(path_value: str) -> bool:
    path = Path(path_value)
    return bool(path_value.strip()) and not path.is_absolute() and ".." not in path.parts


def normalize_path(path_value: str) -> str:
    return Path(path_value).as_posix().rstrip("/")


def paths_overlap(left: str, right: str) -> bool:
    left_path = Path(left)
    right_path = Path(right)

    return (
        left == right
        or left_path in right_path.parents
        or right_path in left_path.parents
    )


def main() -> int:
    errors: list[str] = []

    adapter_paths = sorted(TARGET_REGISTRY.glob("*/adapter.json"))
    if not adapter_paths:
        print(f"FAIL: No target adapters found under {TARGET_REGISTRY}")
        return 1

    seen_names: dict[str, Path] = {}
    ownership: list[tuple[str, str, Path]] = []

    for adapter_path in adapter_paths:
        try:
            data = load_json(adapter_path)
        except Exception as exc:
            errors.append(f"{adapter_path}: failed to load JSON: {exc}")
            continue

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{adapter_path}: missing non-empty name")
            continue

        if name in seen_names:
            errors.append(
                f"{adapter_path}: duplicate target name {name!r}; "
                f"already used by {seen_names[name]}"
            )
        else:
            seen_names[name] = adapter_path

        owned_paths = data.get("ownedPaths")
        if not isinstance(owned_paths, list) or not owned_paths:
            errors.append(f"{adapter_path}: ownedPaths must be a non-empty list")
            continue

        normalized_seen: set[str] = set()

        for index, owned_path in enumerate(owned_paths):
            if not isinstance(owned_path, str):
                errors.append(f"{adapter_path}: ownedPaths[{index}] must be a string")
                continue

            if not is_safe_relative_path(owned_path):
                errors.append(f"{adapter_path}: ownedPaths[{index}] is unsafe: {owned_path!r}")
                continue

            normalized = normalize_path(owned_path)

            if normalized in normalized_seen:
                errors.append(f"{adapter_path}: duplicate ownedPath {normalized!r}")
                continue

            normalized_seen.add(normalized)
            ownership.append((name, normalized, adapter_path))

    for left_index, (left_name, left_path, left_adapter) in enumerate(ownership):
        for right_name, right_path, right_adapter in ownership[left_index + 1:]:
            if left_name == right_name:
                continue

            if paths_overlap(left_path, right_path):
                errors.append(
                    "ownedPaths overlap between targets: "
                    f"{left_name} owns {left_path!r} in {left_adapter}; "
                    f"{right_name} owns {right_path!r} in {right_adapter}"
                )

    if errors:
        print(f"FAIL: Target adapter semantic validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Target adapter semantics are valid.")
    print(f"Targets: {', '.join(sorted(seen_names))}")
    print(f"Owned paths: {len(ownership)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
