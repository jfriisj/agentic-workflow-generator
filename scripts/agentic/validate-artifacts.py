#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ARTIFACT_REGISTRY = ROOT / "registry" / "artifacts"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_contract_shape(contract_path: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    required_keys = {"type", "status", "allowedStatuses", "requiredHeadings"}
    missing = sorted(required_keys - set(contract.keys()))

    if missing:
        raise ValueError(f"{contract_path}: missing required keys: {', '.join(missing)}")

    if not isinstance(contract["requiredHeadings"], list) or not contract["requiredHeadings"]:
        raise ValueError(f"{contract_path}: requiredHeadings must be a non-empty list")

    if not isinstance(contract["allowedStatuses"], list) or not contract["allowedStatuses"]:
        raise ValueError(f"{contract_path}: allowedStatuses must be a non-empty list")

    status = contract["status"]
    if not isinstance(status, dict) or status.get("heading") != "## Status":
        raise ValueError(f"{contract_path}: status.heading must be '## Status'")

    return contract


def extract_status(markdown: str) -> str | None:
    status_section = re.search(
        r"^## Status\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL,
    )

    if not status_section:
        return None

    body = status_section.group("body").strip()
    match = re.search(r"\b(PASS|FAIL|BLOCKED)\b", body)

    if not match:
        return None

    return match.group(1)


def validate_markdown_artifact(path: Path, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    markdown = path.read_text(encoding="utf-8")

    for heading in contract["requiredHeadings"]:
        if heading not in markdown:
            errors.append(f"{path}: missing required heading: {heading}")

    status = extract_status(markdown)

    if status is None:
        errors.append(f"{path}: missing valid status value PASS, FAIL, or BLOCKED under ## Status")
    elif status not in contract["allowedStatuses"]:
        errors.append(f"{path}: unsupported status: {status}")

    return errors


def contract_artifact_paths(contract: dict[str, Any]) -> list[Path]:
    path_pattern = contract.get("pathPattern")

    if not path_pattern:
        return []

    return sorted(ROOT.glob(path_pattern))


def main() -> int:
    contract_files = sorted(ARTIFACT_REGISTRY.glob("*/artifact.json"))

    if not contract_files:
        print("WARN: No artifact contracts found under registry/artifacts.")
        return 0

    errors: list[str] = []
    checked_artifacts = 0

    for contract_path in contract_files:
        try:
            contract = validate_contract_shape(contract_path)
        except Exception as exc:
            errors.append(str(exc))
            continue

        artifact_paths = contract_artifact_paths(contract)
        checked_artifacts += len(artifact_paths)

        for artifact_path in artifact_paths:
            errors.extend(validate_markdown_artifact(artifact_path, contract))

    if errors:
        print(f"FAIL: Artifact validation found {len(errors)} error(s).")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Artifact contracts are valid. Checked {checked_artifacts} artifact file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
