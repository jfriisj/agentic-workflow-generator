#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path.cwd()

REQUIRED_COMMANDS = [
    ("bash", ["bash", "--version"]),
    ("git", ["git", "--version"]),
    ("python", ["python", "--version"]),
    ("node", ["node", "--version"]),
    ("npx", ["npx", "--version"]),
]


def run_command(name: str, command: list[str]) -> tuple[bool, str]:
    executable = shutil.which(command[0])

    if executable is None:
        return False, f"FAIL: {name} is required but was not found in PATH."

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    output = result.stdout.strip()

    if result.returncode != 0:
        details = [
            f"FAIL: {name} is required but failed to run.",
            f"Command path: {executable}",
            f"Command: {' '.join(command)}",
            f"Exit code: {result.returncode}",
        ]

        if output:
            details.extend(["Output:", output])

        return False, "\n".join(details)

    version = output.splitlines()[0] if output else "<no version output>"
    return True, f"PASS: {name} available at {executable} ({version})"


def main() -> int:
    print("== Agentic environment validation ==")
    print(f"Working directory: {ROOT}")
    print(f"PATH: {os.environ.get('PATH', '')}")

    errors: list[str] = []

    for name, command in REQUIRED_COMMANDS:
        ok, message = run_command(name, command)
        print(message)
        if not ok:
            errors.append(name)

    if errors:
        print()
        print(f"FAIL: Environment validation failed for {len(errors)} required command(s): {', '.join(errors)}")
        return 1

    print()
    print(f"PASS: Environment validation passed. Checked {len(REQUIRED_COMMANDS)} required command(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
