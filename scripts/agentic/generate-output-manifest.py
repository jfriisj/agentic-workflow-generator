#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
TARGET_REGISTRY = ROOT / "registry" / "targets"
BUNDLE_REGISTRY = ROOT / "registry" / "bundles"
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
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



def require_string(data: dict[str, Any], field: str, source: Path) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source}: {field} must be a non-empty string")
    return value


def require_string_list(data: dict[str, Any], field: str, source: Path) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source}: {field} must be a non-empty list")

    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{source}: {field}[{index}] must be a non-empty string")
        result.append(item)

    return result


def is_safe_relative_path(path_value: str) -> bool:
    path = Path(path_value)
    return bool(path_value.strip()) and not path.is_absolute() and ".." not in path.parts



def active_workflow_name() -> str:
    config = load_json(CONFIG_PATH)
    workflow = config.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError(f"{CONFIG_PATH}: workflow must be an object")

    profile = workflow.get("profile")
    if not isinstance(profile, str) or not profile.strip():
        raise ValueError(f"{CONFIG_PATH}: workflow.profile must be a non-empty string")

    return profile


def active_bundle_entry() -> dict[str, Any]:
    workflow_name = active_workflow_name()
    candidates: list[tuple[Path, dict[str, Any]]] = []

    for path in sorted(BUNDLE_REGISTRY.glob("*.bundle.json")):
        bundle = load_json(path)
        if bundle.get("workflow") == workflow_name:
            candidates.append((path, bundle))

    if not candidates:
        raise ValueError(f"No bundle found for active workflow '{workflow_name}'")

    if len(candidates) > 1:
        names = ", ".join(require_string(bundle, "name", path) for path, bundle in candidates)
        raise ValueError(f"Multiple bundles found for active workflow '{workflow_name}': {names}")

    path, bundle = candidates[0]

    return {
        "name": require_string(bundle, "name", path),
        "registryPath": relative(path),
        "profile": require_string(bundle, "profile", path),
        "workflow": require_string(bundle, "workflow", path),
        "agents": require_string_list(bundle, "agents", path),
        "skills": require_string_list(bundle, "skills", path),
        "artifacts": require_string_list(bundle, "artifacts", path),
        "targets": require_string_list(bundle, "targets", path),
    }


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

    try:
        bundle = active_bundle_entry()
    except Exception as exc:
        print(f"FAIL: Could not resolve active bundle metadata: {exc}")
        return 1

    bundle_target_names = set(bundle["targets"])
    generated_target_names = {target["name"] for target in targets}

    for missing_target in sorted(bundle_target_names - generated_target_names):
        errors.append(f"bundle target has no generated output target: {missing_target}")

    for extra_target in sorted(generated_target_names - bundle_target_names):
        errors.append(f"generated target is not included in active bundle: {extra_target}")

    for target in targets:
        if target["generatedFileCount"] == 0:
            errors.append(f"{target['name']} target produced no manifest files")

    manifest = {
        "schemaVersion": "0.2.0",
        "description": "Deterministic manifest of active bundle and generated target output files.",
        "bundle": bundle,
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
    print(f"Bundle: {manifest['bundle']['name']}")
    print(f"Targets: {', '.join(target['name'] for target in manifest['targets'])}")
    print(f"Generated files: {manifest['summary']['generatedFileCount']}")
    print(f"Manifest: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
