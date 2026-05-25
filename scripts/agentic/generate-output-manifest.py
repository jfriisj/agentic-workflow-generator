#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
OUTPUT_PATH = ROOT / ".agentic" / "generated" / "output-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def existing_files(paths: list[Path]) -> list[Path]:
    return sorted(path for path in paths if path.is_file())


def collect_vscode_copilot_files() -> list[Path]:
    files: list[Path] = []

    files.extend(sorted((ROOT / ".github" / "agents").glob("*.agent.md")))
    files.extend(sorted((ROOT / ".github" / "skills").glob("*/SKILL.md")))
    files.extend(sorted((ROOT / ".github" / "skills").glob("*/skill.json")))
    files.append(ROOT / ".github" / "copilot-instructions.md")

    return existing_files(files)


def collect_opencode_files() -> list[Path]:
    files: list[Path] = []

    files.extend(sorted((ROOT / ".opencode" / "agents").glob("*.md")))
    files.extend(sorted((ROOT / ".opencode" / "skills").glob("*/SKILL.md")))
    files.extend(sorted((ROOT / ".opencode" / "skills").glob("*/skill.json")))
    files.append(ROOT / "AGENTS.md")
    files.append(ROOT / "opencode.json")

    return existing_files(files)


def file_entry(path: Path) -> dict[str, Any]:
    return {
        "path": relative(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def target_entry(name: str, owned_paths: list[str], files: list[Path]) -> dict[str, Any]:
    return {
        "name": name,
        "ownedPaths": owned_paths,
        "generatedFiles": [file_entry(path) for path in files],
        "generatedFileCount": len(files),
    }


def main() -> int:
    vscode_files = collect_vscode_copilot_files()
    opencode_files = collect_opencode_files()

    errors: list[str] = []

    if not vscode_files:
        errors.append("vscode-copilot target produced no manifest files")

    if not opencode_files:
        errors.append("opencode target produced no manifest files")

    manifest = {
        "schemaVersion": "0.1.0",
        "description": "Deterministic manifest of generated target output files.",
        "targets": [
            target_entry(
                "vscode-copilot",
                [
                    ".github/agents",
                    ".github/skills",
                    ".github/copilot-instructions.md"
                ],
                vscode_files,
            ),
            target_entry(
                "opencode",
                [
                    ".opencode/agents",
                    ".opencode/skills",
                    "AGENTS.md",
                    "opencode.json"
                ],
                opencode_files,
            ),
        ],
        "summary": {
            "targetCount": 2,
            "generatedFileCount": len(vscode_files) + len(opencode_files),
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
