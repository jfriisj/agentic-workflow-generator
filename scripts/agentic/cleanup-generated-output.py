#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
MANIFEST_PATH = ROOT / ".agentic" / "generated" / "output-manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected top-level object")

    return data


def is_safe_relative_path(path_value: str) -> bool:
    path = Path(path_value)
    return bool(path_value.strip()) and not path.is_absolute() and ".." not in path.parts


def collect_files_under_owned_path(path_value: str) -> set[str]:
    if not is_safe_relative_path(path_value):
        raise ValueError(f"Unsafe ownedPath: {path_value!r}")

    path = ROOT / path_value

    if not path.exists():
        return set()

    if path.is_file():
        return {path.relative_to(ROOT).as_posix()}

    if path.is_dir():
        return {
            file_path.relative_to(ROOT).as_posix()
            for file_path in path.rglob("*")
            if file_path.is_file()
        }

    return set()


def remove_empty_parent_dirs(start_path: Path) -> None:
    current = start_path.parent

    while current != ROOT and current.exists():
        try:
            current.rmdir()
        except OSError:
            return

        current = current.parent


def find_unmanaged_files(manifest: dict[str, Any]) -> list[str]:
    unmanaged: set[str] = set()

    targets = manifest.get("targets")
    if not isinstance(targets, list):
        raise ValueError("manifest.targets must be a list")

    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("manifest.targets entries must be objects")

        target_name = target.get("name", "<unknown>")

        owned_paths = target.get("ownedPaths")
        if not isinstance(owned_paths, list):
            raise ValueError(f"target {target_name}: ownedPaths must be a list")

        generated_files = target.get("generatedFiles")
        if not isinstance(generated_files, list):
            raise ValueError(f"target {target_name}: generatedFiles must be a list")

        declared_files: set[str] = set()
        for entry in generated_files:
            if not isinstance(entry, dict):
                continue

            path_value = entry.get("path")
            if isinstance(path_value, str) and is_safe_relative_path(path_value):
                declared_files.add(path_value)

        actual_owned_files: set[str] = set()
        for owned_path in owned_paths:
            if not isinstance(owned_path, str):
                raise ValueError(f"target {target_name}: ownedPaths must contain strings")

            actual_owned_files.update(collect_files_under_owned_path(owned_path))

        unmanaged.update(actual_owned_files - declared_files)

    return sorted(unmanaged)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find or remove unmanaged generated files under manifest ownedPaths."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Only print unmanaged files.")
    mode.add_argument("--apply", action="store_true", help="Delete unmanaged files.")

    args = parser.parse_args()

    try:
        manifest = load_json(MANIFEST_PATH)
        unmanaged_files = find_unmanaged_files(manifest)
    except Exception as exc:
        print(f"FAIL: Cleanup failed before execution: {exc}")
        return 1

    if not unmanaged_files:
        print("PASS: No unmanaged generated files found.")
        return 0

    if args.dry_run:
        print(f"INFO: Found {len(unmanaged_files)} unmanaged generated file(s).")
        for path in unmanaged_files:
            print(f"Would remove unmanaged generated file: {path}")
        return 0

    deleted = 0
    for path_value in unmanaged_files:
        path = ROOT / path_value

        if not path.is_file():
            print(f"SKIP: File no longer exists: {path_value}")
            continue

        path.unlink()
        remove_empty_parent_dirs(path)
        deleted += 1
        print(f"Removed unmanaged generated file: {path_value}")

    print(f"PASS: Removed {deleted} unmanaged generated file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
