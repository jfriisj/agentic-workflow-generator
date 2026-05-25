#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
TARGET_REGISTRY = ROOT / "registry" / "targets"
OUTPUT_PATH = ROOT / ".agentic" / "generated" / "output-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def is_safe_relative_path(path_value: str) -> bool:
    path = Path(path_value)
    return bool(path_value.strip()) and not path.is_absolute() and ".." not in path.parts


def load_target_adapters() -> list[dict[str, Any]]:
    adapters: list[dict[str, Any]] = []

    for path in sorted(TARGET_REGISTRY.glob("*/adapter.json")):
        data = load_json(path)

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{path}: missing non-empty name")

        owned_paths = data.get("ownedPaths")
        if not isinstance(owned_paths, list) or not owned_paths:
            raise ValueError(f"{path}: missing non-empty ownedPaths")

        for owned_path in owned_paths:
            if not isinstance(owned_path, str) or not is_safe_relative_path(owned_path):
                raise ValueError(f"{path}: unsafe ownedPath {owned_path!r}")

        adapters.append(
            {
                "name": name,
                "registryPath": relative(path),
                "ownedPaths": owned_paths,
            }
        )

    if not adapters:
        raise ValueError(f"No target adapters found under {TARGET_REGISTRY}")

    return adapters


def collect_files_from_owned_paths(owned_paths: list[str]) -> list[Path]:
    files: set[Path] = set()

    for owned_path_value in owned_paths:
        owned_path = ROOT / owned_path_value

        if not owned_path.exists():
            continue

        if owned_path.is_file():
            files.add(owned_path)
            continue

        if owned_path.is_dir():
            for file_path in owned_path.rglob("*"):
                if file_path.is_file():
                    files.add(file_path)

    return sorted(files)


def file_entry(path: Path) -> dict[str, Any]:
    return {
        "path": relative(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def target_entry(adapter: dict[str, Any]) -> dict[str, Any]:
    files = collect_files_from_owned_paths(adapter["ownedPaths"])

    return {
        "name": adapter["name"],
        "registryPath": adapter["registryPath"],
        "ownedPaths": adapter["ownedPaths"],
        "generatedFiles": [file_entry(path) for path in files],
        "generatedFileCount": len(files),
    }


def main() -> int:
    errors: list[str] = []

    try:
        adapters = load_target_adapters()
    except Exception as exc:
        print(f"FAIL: Could not load target adapters: {exc}")
        return 1

    targets = [target_entry(adapter) for adapter in adapters]

    for target in targets:
        if target["generatedFileCount"] == 0:
            errors.append(f"{target['name']} target produced no manifest files")

    manifest = {
        "schemaVersion": "0.1.0",
        "description": "Deterministic manifest of generated target output files.",
        "targets": targets,
        "summary": {
            "targetCount": len(targets),
            "generatedFileCount": sum(target["generatedFileCount"] for target in targets),
            "errorCount": len(errors),
            "errors": errors,
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if errors:
        print(f"FAIL: Generated output manifest has {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        print(f"Wrote manifest to: {OUTPUT_PATH}")
        return 1

    print("PASS: Generated output manifest created.")
    print(f"Targets: {', '.join(target['name'] for target in manifest['targets'])}")
    print(f"Generated files: {manifest['summary']['generatedFileCount']}")
    print(f"Manifest: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
