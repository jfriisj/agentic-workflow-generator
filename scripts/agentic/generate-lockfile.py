#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
LOCKFILE_PATH = ROOT / ".agentic" / "agentic-lock.json"

LOCK_PATTERNS = [
    ".agentic/agentic.json",
    ".agentic/schemas/*.json",
    "registry/**/*.json",
    "registry/**/SKILL.md",
    "scripts/agentic/*.py",
    "scripts/agentic/*.sh",
]

EXCLUDED_PARTS = {
    "__pycache__",
    ".git",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    if path == LOCKFILE_PATH:
        return False
    return path.is_file()


def collect_files() -> list[Path]:
    files: set[Path] = set()

    for pattern in LOCK_PATTERNS:
        for path in ROOT.glob(pattern):
            if should_include(path):
                files.add(path)

    return sorted(files, key=lambda item: str(item.relative_to(ROOT)))


def file_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "sizeBytes": stat.st_size,
    }


def main() -> int:
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

    lockfile = {
        "lockfileVersion": 1,
        "generator": {
            "name": "agentic-gen",
            "mode": "local-mvp-lockfile"
        },
        "inputs": {
            "patterns": LOCK_PATTERNS,
            "fileCount": len(records),
            "contentHash": "sha256:" + aggregate_digest.hexdigest(),
            "files": records
        }
    }

    LOCKFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCKFILE_PATH.open("w", encoding="utf-8") as file:
        json.dump(lockfile, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"PASS: Generated deterministic lockfile with {len(records)} input file(s).")
    print(f"Lockfile: {LOCKFILE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
