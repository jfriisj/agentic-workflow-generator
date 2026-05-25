#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path.cwd()


def copy_repo_to_temp() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="agentic-negative-gates-"))
    worktree = temp_root / "repo"

    def ignore(_: str, names: list[str]) -> set[str]:
        ignored = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "node_modules",
        }
        return {name for name in names if name in ignored}

    shutil.copytree(ROOT, worktree, ignore=ignore)
    return worktree


def run(worktree: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=worktree,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def remove_string_from_nested_lists(value: Any, needle: str) -> bool:
    changed = False

    if isinstance(value, list):
        original_len = len(value)
        value[:] = [entry for entry in value if entry != needle]
        changed = changed or len(value) != original_len

        for entry in value:
            changed = remove_string_from_nested_lists(entry, needle) or changed

    elif isinstance(value, dict):
        for entry in value.values():
            changed = remove_string_from_nested_lists(entry, needle) or changed

    return changed


def expect_failure(
    name: str,
    command: list[str],
    mutate,
    expected_text: str,
) -> tuple[bool, str]:
    worktree = copy_repo_to_temp()

    try:
        mutate(worktree)
        result = run(worktree, command)

        if result.returncode == 0:
            return (
                False,
                f"{name}: expected failure, but command passed.\n\nOutput:\n{result.stdout}",
            )

        if expected_text not in result.stdout:
            return (
                False,
                f"{name}: command failed, but expected text was not found: {expected_text!r}\n\n"
                f"Output:\n{result.stdout}",
            )

        return True, f"PASS: {name}"

    finally:
        shutil.rmtree(worktree.parent, ignore_errors=True)


def break_capability_coverage(worktree: Path) -> None:
    path = worktree / "registry" / "skills" / "workflow-routing" / "skill.json"
    data = load_json(path)

    changed = remove_string_from_nested_lists(data, "workflow.route")
    if not changed:
        raise RuntimeError("Could not remove workflow.route from workflow-routing skill")

    write_json(path, data)


def break_workflow_terminal_state(worktree: Path) -> None:
    path = worktree / "registry" / "workflows" / "orchestrated-delivery.workflow.json"
    data = load_json(path)

    terminal_states = data.setdefault("terminalStates", [])
    if not isinstance(terminal_states, list):
        raise RuntimeError("terminalStates must be a list for this test")

    terminal_states.append("DefinitelyMissingTerminalState")
    write_json(path, data)


def break_generated_output(worktree: Path) -> None:
    path = worktree / ".github" / "agents" / "orchestrator.agent.md"
    if not path.is_file():
        raise RuntimeError(f"Expected generated file not found before mutation: {path}")

    path.unlink()


def break_output_manifest_hash(worktree: Path) -> None:
    path = worktree / ".github" / "copilot-instructions.md"
    if not path.is_file():
        raise RuntimeError(f"Expected generated file not found before mutation: {path}")

    path.write_text(
        path.read_text(encoding="utf-8") + "\n<!-- negative manifest drift test -->\n",
        encoding="utf-8",
    )


def break_output_manifest_ownership(worktree: Path) -> None:
    path = worktree / ".github" / "agents" / "extra.agent.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Extra generated file drift test\n", encoding="utf-8")


def break_target_adapter_owned_paths(worktree: Path) -> None:
    path = worktree / "registry" / "targets" / "opencode" / "adapter.json"
    data = load_json(path)

    if "ownedPaths" not in data:
        raise RuntimeError("ownedPaths already missing before mutation")

    del data["ownedPaths"]
    write_json(path, data)



def break_resolution_output(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list for this test")

    first_agent = agents[0]
    if not isinstance(first_agent, dict):
        raise RuntimeError("first resolution agent must be an object")

    missing = first_agent.setdefault("missingCapabilities", [])
    if not isinstance(missing, list):
        raise RuntimeError("missingCapabilities must be a list for this test")

    missing.append("negative.test.missing-capability")
    write_json(path, data)


def break_lockfile(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic-lock.json"
    data = load_json(path)

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("lockfile inputs must be an object for this test")

    inputs["files"] = []
    write_json(path, data)


def main() -> int:
    tests = [
        (
            "coverage fails when a skill capability is removed",
            ["scripts/agentic/agentic-gen.sh", "coverage"],
            break_capability_coverage,
            "Missing skill coverage",
        ),
        (
            "workflow validation fails for unknown terminal state",
            ["scripts/agentic/agentic-gen.sh", "validate-workflows"],
            break_workflow_terminal_state,
            "terminalState",
        ),
        (
            "generated output validation fails when generated agent file is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_generated_output,
            "missing generated file",
        ),
        (
            "output manifest validation fails when generated file content drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_hash,
            "sha256 mismatch",
        ),
        (
            "output manifest validation fails when unmanaged generated file exists",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_ownership,
            "unmanaged generated file under owned path",
        ),
        (
            "target adapter validation fails when ownedPaths is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-registry-schemas"],
            break_target_adapter_owned_paths,
            "ownedPaths",
        ),
        (
            "resolution validation fails when missingCapabilities is non-empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_output,
            "missingCapabilities must be empty",
        ),
        (
            "lockfile validation fails when tracked files are empty",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile,
            "must not be empty",
        ),
    ]

    failures: list[str] = []

    for name, command, mutate, expected_text in tests:
        passed, message = expect_failure(name, command, mutate, expected_text)
        print(message)

        if not passed:
            failures.append(message)

    if failures:
        print()
        print(f"FAIL: {len(failures)} negative gate test(s) failed.")
        return 1

    print()
    print(f"PASS: All {len(tests)} negative gate tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
