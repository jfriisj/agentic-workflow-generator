#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Required config file is missing: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise RuntimeError(f"{path}: expected a JSON object")

    return data


def main() -> int:
    errors: list[str] = []

    try:
        config = load_json(CONFIG_PATH)
    except Exception as exc:
        print(f"FAIL: Agentic config semantic validation: {exc}")
        return 1

    runtime_context = config.get("runtimeContext")

    if not isinstance(runtime_context, dict):
        errors.append(
            "runtimeContext must be an object"
        )
    else:
        enabled = runtime_context.get("enabled")
        fail_if_missing = runtime_context.get("failIfMissing")

        if enabled is not False:
            errors.append(
                "runtimeContext.enabled must be false before Milestone 4; "
                "runtime-context generation is not implemented"
            )

        if fail_if_missing is not False:
            errors.append(
                "runtimeContext.failIfMissing must be false before Milestone 4; "
                "generated runtime context cannot be required"
            )

    if errors:
        print(
            "FAIL: Agentic config semantic validation found "
            f"{len(errors)} error(s)."
        )
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Agentic config semantics are valid.")
    print("PASS: Runtime context remains disabled until Milestone 4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
