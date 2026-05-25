#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
MANIFEST_PATH = ROOT / ".agentic" / "generated" / "output-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected top-level object")

    return data


def validate_file_entry(target_name: str, index: int, entry: Any, errors: list[str]) -> None:
    if not isinstance(entry, dict):
        errors.append(f"target {target_name} generatedFiles[{index}]: expected object")
        return

    path_value = entry.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        errors.append(f"target {target_name} generatedFiles[{index}]: missing non-empty path")
        return

    if path_value.startswith("/") or ".." in Path(path_value).parts:
        errors.append(f"target {target_name} generatedFiles[{index}]: unsafe path {path_value!r}")
        return

    file_path = ROOT / path_value
    if not file_path.is_file():
        errors.append(f"target {target_name} generatedFiles[{index}]: file does not exist: {path_value}")
        return

    expected_sha = entry.get("sha256")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        errors.append(f"target {target_name} generatedFiles[{index}]: invalid sha256 for {path_value}")
        return

    actual_sha = sha256_file(file_path)
    if actual_sha != expected_sha:
        errors.append(
            f"target {target_name} generatedFiles[{index}]: sha256 mismatch for {path_value}"
        )

    expected_bytes = entry.get("bytes")
    if not isinstance(expected_bytes, int) or expected_bytes < 0:
        errors.append(f"target {target_name} generatedFiles[{index}]: invalid bytes for {path_value}")
        return

    actual_bytes = file_path.stat().st_size
    if actual_bytes != expected_bytes:
        errors.append(
            f"target {target_name} generatedFiles[{index}]: byte size mismatch for {path_value}"
        )


def main() -> int:
    errors: list[str] = []

    try:
        manifest = load_json(MANIFEST_PATH)
    except Exception as exc:
        print(f"FAIL: Output manifest validation failed: {exc}")
        return 1

    schema_version = manifest.get("schemaVersion")
    if not isinstance(schema_version, str) or not schema_version.strip():
        errors.append(f"{MANIFEST_PATH}: missing non-empty schemaVersion")

    targets = manifest.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append(f"{MANIFEST_PATH}: expected non-empty targets list")
        targets = []

    seen_targets: set[str] = set()
    total_files = 0

    for target_index, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(f"targets[{target_index}]: expected object")
            continue

        name = target.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"targets[{target_index}]: missing non-empty name")
            name = f"<unknown:{target_index}>"

        if name in seen_targets:
            errors.append(f"targets[{target_index}]: duplicate target name {name!r}")
        seen_targets.add(name)

        owned_paths = target.get("ownedPaths")
        if not isinstance(owned_paths, list) or not owned_paths:
            errors.append(f"target {name}: expected non-empty ownedPaths list")
        elif not all(isinstance(path, str) and path.strip() for path in owned_paths):
            errors.append(f"target {name}: ownedPaths must contain non-empty strings")

        generated_files = target.get("generatedFiles")
        if not isinstance(generated_files, list) or not generated_files:
            errors.append(f"target {name}: expected non-empty generatedFiles list")
            continue

        declared_count = target.get("generatedFileCount")
        if declared_count != len(generated_files):
            errors.append(
                f"target {name}: generatedFileCount {declared_count!r} does not match "
                f"actual count {len(generated_files)}"
            )

        total_files += len(generated_files)

        seen_paths: set[str] = set()
        for file_index, file_entry in enumerate(generated_files):
            if isinstance(file_entry, dict) and isinstance(file_entry.get("path"), str):
                path = file_entry["path"]
                if path in seen_paths:
                    errors.append(f"target {name}: duplicate generated file path {path!r}")
                seen_paths.add(path)

            validate_file_entry(name, file_index, file_entry, errors)

    summary = manifest.get("summary")
    if not isinstance(summary, dict):
        errors.append(f"{MANIFEST_PATH}: expected summary object")
    else:
        declared_target_count = summary.get("targetCount")
        if declared_target_count != len(targets):
            errors.append(
                f"summary.targetCount {declared_target_count!r} does not match actual count {len(targets)}"
            )

        declared_file_count = summary.get("generatedFileCount")
        if declared_file_count != total_files:
            errors.append(
                f"summary.generatedFileCount {declared_file_count!r} does not match actual count {total_files}"
            )

        error_count = summary.get("errorCount")
        summary_errors = summary.get("errors")
        if error_count != 0:
            errors.append(f"summary.errorCount must be 0, got {error_count!r}")
        if summary_errors not in ([], None):
            errors.append("summary.errors must be empty")

    if errors:
        print(f"FAIL: Output manifest validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Output manifest is valid.")
    print(f"Targets: {', '.join(sorted(seen_targets))}")
    print(f"Generated files: {total_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
