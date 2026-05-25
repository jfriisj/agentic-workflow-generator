#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
MANIFEST_PATH = ROOT / ".agentic" / "generated" / "output-manifest.json"

BASELINE_FILES = [
    ".agentic/agentic-lock.json",
    ".agentic/generated/resolution.json",
    ".agentic/generated/output-manifest.json",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def safe_relative_path(value: str) -> Path:
    path = Path(value)

    if path.is_absolute() or ".." in path.parts or not value.strip():
        raise ValueError(f"unsafe relative path: {value}")

    return path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_declared_generated_files() -> list[str]:
    manifest = load_json(MANIFEST_PATH)
    targets = manifest.get("targets")

    if not isinstance(targets, list):
        raise ValueError(f"{MANIFEST_PATH}: targets must be a list")

    files: set[str] = set()

    for target in targets:
        if not isinstance(target, dict):
            raise ValueError(f"{MANIFEST_PATH}: targets entries must be objects")

        generated_files = target.get("generatedFiles")
        if not isinstance(generated_files, list):
            raise ValueError(f"{MANIFEST_PATH}: target.generatedFiles must be a list")

        for generated_file in generated_files:
            if not isinstance(generated_file, dict):
                raise ValueError(f"{MANIFEST_PATH}: generatedFiles entries must be objects")

            raw_path = generated_file.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError(f"{MANIFEST_PATH}: generated file path must be a non-empty string")

            safe_relative_path(raw_path)
            files.add(raw_path)

    return sorted(files)


def collect_snapshot() -> dict[str, str]:
    paths = set(BASELINE_FILES)
    paths.update(collect_declared_generated_files())

    snapshot: dict[str, str] = {}

    for raw_path in sorted(paths):
        relative_path = safe_relative_path(raw_path)
        absolute_path = ROOT / relative_path

        if not absolute_path.is_file():
            raise FileNotFoundError(f"Snapshot file does not exist: {raw_path}")

        snapshot[raw_path] = sha256_file(absolute_path)

    return snapshot


def run_generation() -> int:
    result = subprocess.run(
        ["scripts/agentic/agentic-gen.sh", "all"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if result.returncode != 0:
        print("FAIL: idempotency generation run failed.")
        print(result.stdout)
        return result.returncode

    return 0


def main() -> int:
    try:
        before = collect_snapshot()
    except Exception as exc:
        print(f"FAIL: Could not collect baseline idempotency snapshot: {exc}")
        return 1

    generation_status = run_generation()
    if generation_status != 0:
        return generation_status

    try:
        after = collect_snapshot()
    except Exception as exc:
        print(f"FAIL: Could not collect post-generation idempotency snapshot: {exc}")
        return 1

    before_paths = set(before)
    after_paths = set(after)

    missing_after = sorted(before_paths - after_paths)
    added_after = sorted(after_paths - before_paths)
    changed = sorted(path for path in before_paths & after_paths if before[path] != after[path])

    if missing_after or added_after or changed:
        print("FAIL: Generation is not idempotent.")

        for path in missing_after:
            print(f"  - missing after generation: {path}")

        for path in added_after:
            print(f"  - added after generation: {path}")

        for path in changed:
            print(f"  - changed after generation: {path}")

        return 1

    print(f"PASS: Generation is idempotent. Checked {len(after)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
