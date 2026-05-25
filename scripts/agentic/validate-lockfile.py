#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
LOCKFILE_PATH = ROOT / ".agentic" / "agentic-lock.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def find_input_collection(lockfile: dict[str, Any]) -> tuple[str, Any] | None:
    inputs = lockfile.get("inputs")

    if isinstance(inputs, dict):
        nested_files = inputs.get("files")
        if isinstance(nested_files, (list, dict)):
            return "inputs.files", nested_files

    for key in ["files", "inputFiles", "trackedFiles"]:
        value = lockfile.get(key)
        if isinstance(value, (list, dict)):
            return key, value

    return None


def validate_file_entry(entry: Any, path_label: str) -> list[str]:
    errors: list[str] = []

    if not isinstance(entry, dict):
        return [f"{path_label}: expected object"]

    path_value = entry.get("path") or entry.get("file") or entry.get("name")
    hash_value = (
        entry.get("hash")
        or entry.get("sha256")
        or entry.get("checksum")
        or entry.get("digest")
    )

    if not isinstance(path_value, str) or not path_value.strip():
        errors.append(f"{path_label}: expected non-empty path/file/name")

    if not isinstance(hash_value, str) or not hash_value.strip():
        errors.append(f"{path_label}: expected non-empty hash/sha256/checksum/digest")

    return errors


def validate_inputs(collection_name: str, collection: Any) -> list[str]:
    errors: list[str] = []

    if isinstance(collection, list):
        if not collection:
            return [f"{LOCKFILE_PATH}: {collection_name} must not be empty"]

        for index, entry in enumerate(collection):
            errors.extend(validate_file_entry(entry, f"{collection_name}[{index}]"))

        return errors

    if isinstance(collection, dict):
        if not collection:
            return [f"{LOCKFILE_PATH}: {collection_name} must not be empty"]

        for key, value in collection.items():
            if isinstance(value, str) and value.strip():
                continue

            if isinstance(value, dict):
                entry = {"path": key, **value}
                errors.extend(validate_file_entry(entry, f"{collection_name}.{key}"))
                continue

            errors.append(
                f"{collection_name}.{key}: expected checksum string or object with checksum"
            )

        return errors

    return [f"{LOCKFILE_PATH}: {collection_name} must be list or object"]


def main() -> int:
    errors: list[str] = []

    try:
        lockfile = load_json(LOCKFILE_PATH)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    input_collection = find_input_collection(lockfile)

    if input_collection is None:
        errors.append(
            f"{LOCKFILE_PATH}: expected one of inputs, files, inputFiles, or trackedFiles"
        )
    else:
        collection_name, collection = input_collection
        errors.extend(validate_inputs(collection_name, collection))

    if errors:
        print(f"FAIL: Lockfile validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Lockfile is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
