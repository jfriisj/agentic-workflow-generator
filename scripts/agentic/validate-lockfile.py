#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
LOCKFILE_PATH = ROOT / ".agentic" / "agentic-lock.json"
GENERATOR_PATH = ROOT / "scripts" / "agentic" / "generate-lockfile.py"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")

    return data


def load_lock_generator() -> dict[str, Any]:
    if not GENERATOR_PATH.is_file():
        raise FileNotFoundError(f"Required file not found: {GENERATOR_PATH}")

    namespace = runpy.run_path(str(GENERATOR_PATH))

    for name in ["LOCK_PATTERNS", "collect_files", "file_record"]:
        if name not in namespace:
            raise ValueError(f"{GENERATOR_PATH}: missing {name}")

    if not isinstance(namespace["LOCK_PATTERNS"], list):
        raise ValueError(f"{GENERATOR_PATH}: LOCK_PATTERNS must be a list")

    if not callable(namespace["collect_files"]):
        raise ValueError(f"{GENERATOR_PATH}: collect_files must be callable")

    if not callable(namespace["file_record"]):
        raise ValueError(f"{GENERATOR_PATH}: file_record must be callable")

    return namespace


def expected_lockfile() -> dict[str, Any]:
    namespace = load_lock_generator()

    lock_patterns = namespace["LOCK_PATTERNS"]
    collect_files = namespace["collect_files"]
    file_record = namespace["file_record"]

    files = collect_files()

    if not files:
        raise RuntimeError("No files matched lockfile input patterns.")

    records = [file_record(path) for path in files]

    aggregate_digest = hashlib.sha256()
    for record in records:
        aggregate_digest.update(record["path"].encode("utf-8"))
        aggregate_digest.update(b"\0")
        aggregate_digest.update(record["sha256"].encode("utf-8"))
        aggregate_digest.update(b"\0")

    return {
        "lockfileVersion": 1,
        "generator": {
            "name": "agentic-gen",
            "mode": "local-mvp-lockfile",
        },
        "inputs": {
            "patterns": lock_patterns,
            "fileCount": len(records),
            "contentHash": "sha256:" + aggregate_digest.hexdigest(),
            "files": records,
        },
    }


def validate_shape(lockfile: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if lockfile.get("lockfileVersion") != 1:
        errors.append(f"{LOCKFILE_PATH}: lockfileVersion must be 1")

    generator = lockfile.get("generator")
    if not isinstance(generator, dict):
        errors.append(f"{LOCKFILE_PATH}: generator must be an object")
    else:
        if generator.get("name") != "agentic-gen":
            errors.append(f"{LOCKFILE_PATH}: generator.name must be agentic-gen")

        if generator.get("mode") != "local-mvp-lockfile":
            errors.append(f"{LOCKFILE_PATH}: generator.mode must be local-mvp-lockfile")

    inputs = lockfile.get("inputs")
    if not isinstance(inputs, dict):
        errors.append(f"{LOCKFILE_PATH}: inputs must be an object")
        return errors

    patterns = inputs.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        errors.append(f"{LOCKFILE_PATH}: inputs.patterns must be a non-empty list")
    elif not all(isinstance(pattern, str) and pattern.strip() for pattern in patterns):
        errors.append(f"{LOCKFILE_PATH}: inputs.patterns entries must be non-empty strings")

    file_count = inputs.get("fileCount")
    if not isinstance(file_count, int) or file_count <= 0:
        errors.append(f"{LOCKFILE_PATH}: inputs.fileCount must be a positive integer")

    content_hash = inputs.get("contentHash")
    if not isinstance(content_hash, str) or not content_hash.startswith("sha256:"):
        errors.append(f"{LOCKFILE_PATH}: inputs.contentHash must be a sha256 digest")

    files = inputs.get("files")
    if not isinstance(files, list) or not files:
        errors.append(f"{LOCKFILE_PATH}: inputs.files must not be empty")
        return errors

    seen_paths: set[str] = set()

    for index, entry in enumerate(files):
        label = f"inputs.files[{index}]"

        if not isinstance(entry, dict):
            errors.append(f"{label}: expected object")
            continue

        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            errors.append(f"{label}.path must be a non-empty string")
        elif Path(path_value).is_absolute() or ".." in Path(path_value).parts:
            errors.append(f"{label}.path must be a safe relative path")
        elif path_value in seen_paths:
            errors.append(f"{label}.path is duplicated")
        else:
            seen_paths.add(path_value)

        sha256_value = entry.get("sha256")
        if not isinstance(sha256_value, str) or not sha256_value.startswith("sha256:"):
            errors.append(f"{label}.sha256 must be a sha256 digest")

        size_bytes = entry.get("sizeBytes")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            errors.append(f"{label}.sizeBytes must be a non-negative integer")

    return errors


def main() -> int:
    try:
        lockfile = load_json(LOCKFILE_PATH)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    errors = validate_shape(lockfile)

    try:
        expected = expected_lockfile()
    except Exception as exc:
        errors.append(f"{LOCKFILE_PATH}: could not compute expected lockfile: {exc}")
        expected = None

    if expected is not None and lockfile != expected:
        errors.append(
            f"{LOCKFILE_PATH}: lockfile content drift detected; run scripts/agentic/agentic-gen.sh lock"
        )

        actual_inputs = lockfile.get("inputs") if isinstance(lockfile.get("inputs"), dict) else {}
        expected_inputs = expected.get("inputs", {})

        actual_files = actual_inputs.get("files") if isinstance(actual_inputs, dict) else []
        expected_files = expected_inputs.get("files", [])

        if isinstance(actual_files, list) and isinstance(expected_files, list):
            actual_by_path = {
                entry.get("path"): entry
                for entry in actual_files
                if isinstance(entry, dict) and isinstance(entry.get("path"), str)
            }
            expected_by_path = {
                entry.get("path"): entry
                for entry in expected_files
                if isinstance(entry, dict) and isinstance(entry.get("path"), str)
            }

            missing = sorted(set(expected_by_path) - set(actual_by_path))
            extra = sorted(set(actual_by_path) - set(expected_by_path))
            common = sorted(set(actual_by_path) & set(expected_by_path))

            for path in missing[:20]:
                errors.append(f"{LOCKFILE_PATH}: missing input file in lockfile: {path}")

            for path in extra[:20]:
                errors.append(f"{LOCKFILE_PATH}: unexpected input file in lockfile: {path}")

            for path in common:
                actual_entry = actual_by_path[path]
                expected_entry = expected_by_path[path]

                if actual_entry.get("sha256") != expected_entry.get("sha256"):
                    errors.append(f"{LOCKFILE_PATH}: sha256 drift for input file: {path}")

                if actual_entry.get("sizeBytes") != expected_entry.get("sizeBytes"):
                    errors.append(f"{LOCKFILE_PATH}: sizeBytes drift for input file: {path}")

    if errors:
        print(f"FAIL: Lockfile validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Lockfile is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
