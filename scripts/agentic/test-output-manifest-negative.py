#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path.cwd()

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
}


def ignore(_dir_path: str, names: list[str]) -> list[str]:
    return [name for name in names if name in EXCLUDE_DIRS or name.endswith(".pyc")]


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agentic-output-manifest-negative-") as temp_dir:
        work = Path(temp_dir) / "repo"
        shutil.copytree(ROOT, work, ignore=ignore)

        generated_file = work / ".github" / "copilot-instructions.md"
        if not generated_file.is_file():
            print(f"FAIL: Expected generated file not found: {generated_file.relative_to(work)}")
            return 1

        generated_file.write_text(
            generated_file.read_text(encoding="utf-8") + "\n<!-- manifest drift test -->\n",
            encoding="utf-8",
        )

        result = run(
            ["bash", "scripts/agentic/agentic-gen.sh", "validate-manifest"],
            work,
        )

        if result.returncode == 0:
            print("FAIL: validate-manifest passed after generated file drift.")
            print(result.stdout)
            return 1

        print("PASS: output manifest validation fails when generated file content drifts")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
