#!/usr/bin/env python3
from __future__ import annotations

import hashlib
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


def expect_success(
    name: str,
    command: list[str],
    mutate,
    expected_text: str,
    post_check=None,
) -> tuple[bool, str]:
    worktree = copy_repo_to_temp()

    try:
        mutate(worktree)
        result = run(worktree, command)

        if result.returncode != 0:
            return (
                False,
                f"{name}: expected success, but command failed.\n\nOutput:\n{result.stdout}",
            )

        if expected_text not in result.stdout:
            return (
                False,
                f"{name}: command succeeded, but expected text was not found: {expected_text!r}\n\n"
                f"Output:\n{result.stdout}",
            )

        if post_check is not None:
            post_passed, post_message = post_check(worktree)
            if not post_passed:
                return False, f"{name}: {post_message}\n\nOutput:\n{result.stdout}"

        return True, f"PASS: {name}"

    finally:
        shutil.rmtree(worktree.parent, ignore_errors=True)



def assert_cleanup_apply_removed_file(worktree: Path) -> tuple[bool, str]:
    path = worktree / ".github" / "agents" / "cleanup-apply-test.agent.md"
    if path.exists():
        return False, f"cleanup apply did not remove expected file: {path.relative_to(worktree)}"
    return True, "cleanup apply removed expected unmanaged file"



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


def break_cleanup_generated_apply(worktree: Path) -> None:
    path = worktree / ".github" / "agents" / "cleanup-apply-test.agent.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Cleanup apply test\n", encoding="utf-8")



def break_cleanup_generated_dry_run(worktree: Path) -> None:
    path = worktree / ".github" / "agents" / "cleanup-dry-run-test.agent.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Cleanup dry-run test\n", encoding="utf-8")



def break_cleanup_manifest_absolute_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("first manifest target must be an object before mutation")

    owned_paths = first_target.get("ownedPaths")
    if not isinstance(owned_paths, list):
        raise RuntimeError("first manifest target ownedPaths must be a list before mutation")

    owned_paths.append("/tmp/agentic-danger-test")
    write_json(path, data)



def break_cleanup_manifest_parent_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("first manifest target must be an object before mutation")

    owned_paths = first_target.get("ownedPaths")
    if not isinstance(owned_paths, list):
        raise RuntimeError("first manifest target ownedPaths must be a list before mutation")

    owned_paths.append("../outside-repo")
    write_json(path, data)



def break_output_manifest_unsupported_schema_version(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)
    data["schemaVersion"] = "999.0.0"
    write_json(path, data)



def break_output_manifest_schema_version(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    if "schemaVersion" not in data:
        raise RuntimeError("schemaVersion already missing before mutation")

    del data["schemaVersion"]
    write_json(path, data)



def break_output_manifest_generated_file_invalid_path_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry["path"] = 123
    write_json(path, data)



def break_output_manifest_generated_file_empty_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry["path"] = ""
    write_json(path, data)



def break_output_manifest_generated_file_missing_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry.pop("path", None)
    write_json(path, data)



def break_output_manifest_invalid_generated_file_entry_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    generated_files[0] = "not-an-object"
    write_json(path, data)



def break_output_manifest_empty_generated_files(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    first_target["generatedFiles"] = []
    first_target["generatedFileCount"] = 0

    summary = data.get("summary")
    if isinstance(summary, dict):
        total_files = 0
        for target in targets:
            if isinstance(target, dict) and isinstance(target.get("generatedFiles"), list):
                total_files += len(target["generatedFiles"])
        summary["generatedFileCount"] = total_files

    write_json(path, data)



def break_output_manifest_missing_generated_files(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    first_target.pop("generatedFiles", None)
    write_json(path, data)



def break_output_manifest_owned_paths_absolute_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    first_target["ownedPaths"] = ["/tmp/agentic-owned-path-test"]
    write_json(path, data)



def break_output_manifest_owned_paths_parent_reference(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    first_target["ownedPaths"] = ["../outside"]
    write_json(path, data)



def break_output_manifest_invalid_owned_paths_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    first_target["ownedPaths"] = [123]
    write_json(path, data)



def break_output_manifest_empty_owned_paths(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    first_target["ownedPaths"] = []
    write_json(path, data)



def break_output_manifest_empty_targets(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    data["targets"] = []
    write_json(path, data)



def break_output_manifest_invalid_targets_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    data["targets"] = {"not": "a-list"}
    write_json(path, data)



def break_output_manifest_missing_targets(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    data.pop("targets", None)
    write_json(path, data)



def break_output_manifest_invalid_target_entry_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    targets[0] = "not-an-object"
    write_json(path, data)



def break_output_manifest_missing_owned_paths(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    first_target.pop("ownedPaths", None)
    write_json(path, data)



def break_output_manifest_missing_target_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    first_target["name"] = ""
    write_json(path, data)



def break_output_manifest_invalid_summary_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    data["summary"] = "not-an-object"
    write_json(path, data)



def break_output_manifest_missing_summary(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    data.pop("summary", None)
    write_json(path, data)



def break_output_manifest_duplicate_target_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or len(targets) < 2:
        raise RuntimeError("output manifest targets must contain at least two targets before mutation")

    first_target = targets[0]
    second_target = targets[1]
    if not isinstance(first_target, dict) or not isinstance(second_target, dict):
        raise RuntimeError("output manifest targets must be objects before mutation")

    first_name = first_target.get("name")
    if not isinstance(first_name, str) or not first_name.strip():
        raise RuntimeError("first output manifest target name must be a non-empty string before mutation")

    second_target["name"] = first_name
    write_json(path, data)



def break_output_manifest_summary_missing_error_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("output manifest summary must be an object before mutation")

    summary.pop("errorCount", None)
    write_json(path, data)



def break_output_manifest_summary_error_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("output manifest summary must be an object before mutation")

    summary["errorCount"] = 1
    write_json(path, data)


def break_output_manifest_summary_missing_errors(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("output manifest summary must be an object before mutation")

    summary.pop("errors", None)
    write_json(path, data)



def break_output_manifest_summary_errors(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("output manifest summary must be an object before mutation")

    summary["errors"] = ["synthetic manifest error"]
    write_json(path, data)



def break_output_manifest_summary_missing_target_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("output manifest summary must be an object before mutation")

    summary.pop("targetCount", None)
    write_json(path, data)



def break_output_manifest_summary_target_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("output manifest summary must be an object before mutation")

    current_count = summary.get("targetCount")
    if not isinstance(current_count, int):
        raise RuntimeError("summary.targetCount must be an integer before mutation")

    summary["targetCount"] = current_count + 1
    write_json(path, data)



def break_output_manifest_summary_missing_generated_file_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("output manifest summary must be an object before mutation")

    summary.pop("generatedFileCount", None)
    write_json(path, data)



def break_output_manifest_summary_generated_file_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("output manifest summary must be an object before mutation")

    current_total = summary.get("generatedFileCount")
    if not isinstance(current_total, int):
        raise RuntimeError("summary.generatedFileCount must be an integer before mutation")

    summary["generatedFileCount"] = current_total + 1
    write_json(path, data)



def break_output_manifest_generated_file_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list):
        raise RuntimeError("output manifest generatedFiles must be a list before mutation")

    first_target["generatedFileCount"] = len(generated_files) + 1
    write_json(path, data)



def break_output_manifest_duplicate_generated_file_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    generated_files.append(dict(first_entry))
    first_target["generatedFileCount"] = len(generated_files)

    summary = data.get("summary")
    if isinstance(summary, dict):
        total_files = 0
        for target in targets:
            if isinstance(target, dict) and isinstance(target.get("generatedFiles"), list):
                total_files += len(target["generatedFiles"])
        summary["generatedFileCount"] = total_files

    write_json(path, data)



def break_output_manifest_declared_file_missing(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    generated_path = first_entry.get("path")
    if not isinstance(generated_path, str) or not generated_path.strip():
        raise RuntimeError("output manifest generatedFiles[0].path must be a non-empty string before mutation")

    file_path = worktree / generated_path
    if not file_path.is_file():
        raise RuntimeError(f"Expected generated file to exist before mutation: {generated_path}")

    file_path.unlink()



def break_output_manifest_generated_file_absolute_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry["path"] = "/tmp/agentic-generated-file-test.md"
    write_json(path, data)



def break_output_manifest_generated_file_parent_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry["path"] = "../README.md"
    write_json(path, data)



def break_output_manifest_generated_file_missing_bytes(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry.pop("bytes", None)
    write_json(path, data)



def break_output_manifest_invalid_bytes(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry["bytes"] = "not-an-integer"
    write_json(path, data)



def break_output_manifest_byte_size(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    current_bytes = first_entry.get("bytes")
    if not isinstance(current_bytes, int):
        raise RuntimeError("output manifest generatedFiles[0].bytes must be an integer before mutation")

    first_entry["bytes"] = current_bytes + 1
    write_json(path, data)



def break_output_manifest_generated_file_missing_sha256(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry.pop("sha256", None)
    write_json(path, data)



def break_output_manifest_invalid_sha256(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    first_entry["sha256"] = "not-a-valid-sha256"
    write_json(path, data)



def break_output_manifest_hash(worktree: Path) -> None:
    path = worktree / ".github" / "copilot-instructions.md"
    if not path.is_file():
        raise RuntimeError(f"Expected generated file not found before mutation: {path}")

    path.write_text(
        path.read_text(encoding="utf-8") + "\n<!-- negative manifest drift test -->\n",
        encoding="utf-8",
    )


def break_output_manifest_declared_file_outside_owned_paths(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("output manifest targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("output manifest first target must be an object before mutation")

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError("output manifest generatedFiles must be a non-empty list before mutation")

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError("output manifest generatedFiles[0] must be an object before mutation")

    outside_path = "README.md"
    absolute_outside_path = worktree / outside_path
    if not absolute_outside_path.is_file():
        raise RuntimeError(f"Expected outside file to exist before mutation: {outside_path}")

    mutated_entry = dict(first_entry)
    mutated_entry["path"] = outside_path
    mutated_entry["sha256"] = hashlib.sha256(absolute_outside_path.read_bytes()).hexdigest()
    mutated_entry["bytes"] = absolute_outside_path.stat().st_size

    generated_files.append(mutated_entry)
    first_target["generatedFileCount"] = len(generated_files)

    summary = data.get("summary")
    if isinstance(summary, dict):
        total_files = 0
        for target in targets:
            if isinstance(target, dict) and isinstance(target.get("generatedFiles"), list):
                total_files += len(target["generatedFiles"])
        summary["generatedFileCount"] = total_files

    write_json(path, data)



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



def break_target_adapter_owned_path_parent_reference(worktree: Path) -> None:
    path = worktree / "registry" / "targets" / "opencode" / "adapter.json"
    data = load_json(path)

    owned_paths = data.get("ownedPaths")
    if not isinstance(owned_paths, list):
        raise RuntimeError("ownedPaths must be a list before mutation")

    owned_paths.append("../outside-repo")
    write_json(path, data)


def break_target_adapter_owned_path_absolute(worktree: Path) -> None:
    path = worktree / "registry" / "targets" / "opencode" / "adapter.json"
    data = load_json(path)

    owned_paths = data.get("ownedPaths")
    if not isinstance(owned_paths, list):
        raise RuntimeError("ownedPaths must be a list before mutation")

    owned_paths.append("/tmp/agentic-danger-test")
    write_json(path, data)



def break_target_adapter_duplicate_name(worktree: Path) -> None:
    path = worktree / "registry" / "targets" / "vscode-copilot" / "adapter.json"
    data = load_json(path)

    data["name"] = "opencode"
    write_json(path, data)



def break_target_adapter_duplicate_owned_path(worktree: Path) -> None:
    path = worktree / "registry" / "targets" / "opencode" / "adapter.json"
    data = load_json(path)

    owned_paths = data.get("ownedPaths")
    if not isinstance(owned_paths, list) or not owned_paths:
        raise RuntimeError("ownedPaths must be a non-empty list before mutation")

    owned_paths.append(owned_paths[0])
    write_json(path, data)



def break_target_adapter_owned_path_overlap(worktree: Path) -> None:
    path = worktree / "registry" / "targets" / "opencode" / "adapter.json"
    data = load_json(path)

    owned_paths = data.get("ownedPaths")
    if not isinstance(owned_paths, list):
        raise RuntimeError("ownedPaths must be a list before mutation")

    if ".github/agents" not in owned_paths:
        owned_paths.append(".github/agents")

    write_json(path, data)



def break_resolution_resolved_capability_entry_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list before mutation")

    first_agent = agents[0]
    if not isinstance(first_agent, dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    resolved = first_agent.get("resolvedCapabilities")
    if not isinstance(resolved, list) or not resolved:
        raise RuntimeError("resolvedCapabilities must be a non-empty list before mutation")

    resolved[0] = "not-an-object"
    write_json(path, data)



def break_resolution_agent_invalid_resolved_capabilities_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list before mutation")

    first_agent = agents[0]
    if not isinstance(first_agent, dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    first_agent["resolvedCapabilities"] = {"not": "a-list"}
    write_json(path, data)



def break_resolution_agent_missing_resolved_capabilities(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list before mutation")

    first_agent = agents[0]
    if not isinstance(first_agent, dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    first_agent.pop("resolvedCapabilities", None)
    write_json(path, data)



def break_resolution_agent_invalid_missing_capabilities_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list before mutation")

    first_agent = agents[0]
    if not isinstance(first_agent, dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    first_agent["missingCapabilities"] = "not-a-list"
    write_json(path, data)



def break_resolution_agent_invalid_capabilities_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list before mutation")

    first_agent = agents[0]
    if not isinstance(first_agent, dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    first_agent["capabilities"] = {"not": "a-list"}
    write_json(path, data)



def break_resolution_agent_missing_capabilities(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list before mutation")

    first_agent = agents[0]
    if not isinstance(first_agent, dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    first_agent.pop("capabilities", None)
    write_json(path, data)



def break_resolution_invalid_agent_entry_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list before mutation")

    agents[0] = "not-an-object"
    write_json(path, data)



def break_resolution_invalid_agents_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data["agents"] = {"not": "a-list"}
    write_json(path, data)



def break_resolution_empty_agents(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data["agents"] = []
    write_json(path, data)



def break_resolution_missing_agents(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data.pop("agents", None)
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
            "failure",
            "coverage fails when a skill capability is removed",
            ["scripts/agentic/agentic-gen.sh", "coverage"],
            break_capability_coverage,
            "Missing skill coverage",
        ),
        (
            "failure",
            "workflow validation fails for unknown terminal state",
            ["scripts/agentic/agentic-gen.sh", "validate-workflows"],
            break_workflow_terminal_state,
            "terminalState",
        ),
        (
            "failure",
            "generated output validation fails when generated agent file is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_generated_output,
            "missing generated file",
        ),
        (
            "success",
            "cleanup dry-run detects unmanaged generated file",
            ["scripts/agentic/agentic-gen.sh", "cleanup-generated", "--dry-run"],
            break_cleanup_generated_dry_run,
            "Would remove unmanaged generated file",
        ),
        (
            "success",
            "cleanup apply removes unmanaged generated file",
            ["scripts/agentic/agentic-gen.sh", "cleanup-generated", "--apply"],
            break_cleanup_generated_apply,
            "Removed unmanaged generated file",
            assert_cleanup_apply_removed_file,
        ),
        (
            "failure",
            "cleanup dry-run rejects parent-directory ownedPath",
            ["scripts/agentic/agentic-gen.sh", "cleanup-generated", "--dry-run"],
            break_cleanup_manifest_parent_path,
            "Unsafe ownedPath",
        ),
        (
            "failure",
            "cleanup dry-run rejects absolute ownedPath",
            ["scripts/agentic/agentic-gen.sh", "cleanup-generated", "--dry-run"],
            break_cleanup_manifest_absolute_path,
            "Unsafe ownedPath",
        ),
        (
            "failure",
            "output manifest validation fails when schemaVersion is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_schema_version,
            "schemaVersion",
        ),
        (
            "failure",
            "output manifest validation fails when schemaVersion is unsupported",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_unsupported_schema_version,
            "Unsupported output manifest schemaVersion",
        ),
        (
            "failure",
            "output manifest validation fails when generated file path has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_generated_file_invalid_path_type,
            "missing or unsafe path",
        ),
        (
            "failure",
            "output manifest validation fails when generated file path is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_generated_file_empty_path,
            "missing or unsafe path",
        ),
        (
            "failure",
            "output manifest validation fails when generated file path is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_generated_file_missing_path,
            "missing or unsafe path",
        ),
        (
            "failure",
            "output manifest validation fails when generated file entry is invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_invalid_generated_file_entry_type,
            "expected object",
        ),
        (
            "failure",
            "output manifest validation fails when target generatedFiles is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_empty_generated_files,
            "expected non-empty generatedFiles list",
        ),
        (
            "failure",
            "output manifest validation fails when target generatedFiles is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_missing_generated_files,
            "expected non-empty generatedFiles list",
        ),
        (
            "failure",
            "output manifest validation fails when target ownedPaths is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_owned_paths_absolute_path,
            "unsafe ownedPath",
        ),
        (
            "failure",
            "output manifest validation fails when target ownedPaths contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_owned_paths_parent_reference,
            "unsafe ownedPath",
        ),
        (
            "failure",
            "output manifest validation fails when target ownedPaths contains invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_invalid_owned_paths_type,
            "ownedPaths must contain non-empty strings",
        ),
        (
            "failure",
            "output manifest validation fails when target ownedPaths is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_empty_owned_paths,
            "expected non-empty ownedPaths list",
        ),
        (
            "failure",
            "output manifest validation fails when targets is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_empty_targets,
            "expected non-empty targets list",
        ),
        (
            "failure",
            "output manifest validation fails when targets has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_invalid_targets_type,
            "expected non-empty targets list",
        ),
        (
            "failure",
            "output manifest validation fails when targets is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_missing_targets,
            "expected non-empty targets list",
        ),
        (
            "failure",
            "output manifest validation fails when target entry is invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_invalid_target_entry_type,
            "expected object",
        ),
        (
            "failure",
            "output manifest validation fails when target ownedPaths is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_missing_owned_paths,
            "expected non-empty ownedPaths list",
        ),
        (
            "failure",
            "output manifest validation fails when target name is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_missing_target_name,
            "missing non-empty name",
        ),
        (
            "failure",
            "output manifest validation fails when summary has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_invalid_summary_type,
            "expected summary object",
        ),
        (
            "failure",
            "output manifest validation fails when summary is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_missing_summary,
            "expected summary object",
        ),
        (
            "failure",
            "output manifest validation fails when target name is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_duplicate_target_name,
            "duplicate target name",
        ),
        (
            "failure",
            "output manifest validation fails when summary errorCount is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_summary_missing_error_count,
            "summary.errorCount",
        ),
        (
            "failure",
            "output manifest validation fails when summary errorCount is non-zero",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_summary_error_count,
            "summary.errorCount",
        ),
        (
            "failure",
            "output manifest validation fails when summary errors is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_summary_missing_errors,
            "summary.errors",
        ),
        (
            "failure",
            "output manifest validation fails when summary errors is non-empty",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_summary_errors,
            "summary.errors",
        ),
        (
            "failure",
            "output manifest validation fails when summary targetCount is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_summary_missing_target_count,
            "summary.targetCount",
        ),
        (
            "failure",
            "output manifest validation fails when summary targetCount is wrong",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_summary_target_count,
            "summary.targetCount",
        ),
        (
            "failure",
            "output manifest validation fails when summary generatedFileCount is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_summary_missing_generated_file_count,
            "summary.generatedFileCount",
        ),
        (
            "failure",
            "output manifest validation fails when summary generatedFileCount is wrong",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_summary_generated_file_count,
            "summary.generatedFileCount",
        ),
        (
            "failure",
            "output manifest validation fails when generatedFileCount is wrong",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_generated_file_count,
            "generatedFileCount",
        ),
        (
            "failure",
            "output manifest validation fails when generated file path is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_duplicate_generated_file_path,
            "duplicate generated file path",
        ),
        (
            "failure",
            "output manifest validation fails when declared generated file is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_declared_file_missing,
            "file does not exist",
        ),
        (
            "failure",
            "output manifest validation fails when generated file path is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_generated_file_absolute_path,
            "missing or unsafe path",
        ),
        (
            "failure",
            "output manifest validation fails when generated file path contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_generated_file_parent_path,
            "missing or unsafe path",
        ),
        (
            "failure",
            "output manifest validation fails when generated file bytes is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_generated_file_missing_bytes,
            "invalid bytes",
        ),
        (
            "failure",
            "output manifest validation fails when generated file bytes is invalid",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_invalid_bytes,
            "invalid bytes",
        ),
        (
            "failure",
            "output manifest validation fails when generated file byte size drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_byte_size,
            "byte size mismatch",
        ),
        (
            "failure",
            "output manifest validation fails when generated file sha256 is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_generated_file_missing_sha256,
            "invalid sha256",
        ),
        (
            "failure",
            "output manifest validation fails when generated file sha256 is invalid",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_invalid_sha256,
            "invalid sha256",
        ),
        (
            "failure",
            "output manifest validation fails when generated file content drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_hash,
            "sha256 mismatch",
        ),
        (
            "failure",
            "output manifest validation fails when declared file is outside ownedPaths",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_declared_file_outside_owned_paths,
            "declared generated file is outside owned paths",
        ),
        (
            "failure",
            "output manifest validation fails when unmanaged generated file exists",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_ownership,
            "unmanaged generated file under owned path",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPaths is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-registry-schemas"],
            break_target_adapter_owned_paths,
            "ownedPaths",
        ),
        (
            "failure",
            "target adapter semantic validation fails when ownedPaths overlap",
            ["scripts/agentic/agentic-gen.sh", "validate-target-semantics"],
            break_target_adapter_owned_path_overlap,
            "ownedPaths overlap between targets",
        ),
        (
            "failure",
            "target adapter semantic validation fails when ownedPaths has duplicate",
            ["scripts/agentic/agentic-gen.sh", "validate-target-semantics"],
            break_target_adapter_duplicate_owned_path,
            "duplicate ownedPath",
        ),
        (
            "failure",
            "target adapter semantic validation fails when target name is duplicate",
            ["scripts/agentic/agentic-gen.sh", "validate-target-semantics"],
            break_target_adapter_duplicate_name,
            "duplicate target name",
        ),
        (
            "failure",
            "target adapter semantic validation fails when ownedPaths contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-target-semantics"],
            break_target_adapter_owned_path_parent_reference,
            "is unsafe",
        ),
        (
            "failure",
            "target adapter semantic validation fails when ownedPaths is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-target-semantics"],
            break_target_adapter_owned_path_absolute,
            "is unsafe",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_entry_type,
            "resolvedCapabilities[0] must be an object",
        ),
        (
            "failure",
            "resolution validation fails when agent resolvedCapabilities has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_invalid_resolved_capabilities_type,
            "resolvedCapabilities must be a list",
        ),
        (
            "failure",
            "resolution validation fails when agent resolvedCapabilities is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_missing_resolved_capabilities,
            "resolvedCapabilities must be a list",
        ),
        (
            "failure",
            "resolution validation fails when agent missingCapabilities has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_invalid_missing_capabilities_type,
            "missingCapabilities must be a list",
        ),
        (
            "failure",
            "resolution validation fails when agent capabilities has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_invalid_capabilities_type,
            "capabilities must be a list",
        ),
        (
            "failure",
            "resolution validation fails when agent capabilities is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_missing_capabilities,
            "capabilities must be a list",
        ),
        (
            "failure",
            "resolution validation fails when agent entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_invalid_agent_entry_type,
            "agents[0] must be an object",
        ),
        (
            "failure",
            "resolution validation fails when agents has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_invalid_agents_type,
            "expected non-empty 'agents' collection",
        ),
        (
            "failure",
            "resolution validation fails when agents is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_empty_agents,
            "expected non-empty 'agents' collection",
        ),
        (
            "failure",
            "resolution validation fails when agents is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_missing_agents,
            "expected non-empty 'agents' collection",
        ),
        (
            "failure",
            "resolution validation fails when missingCapabilities is non-empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_output,
            "missingCapabilities must be empty",
        ),
        (
            "failure",
            "lockfile validation fails when tracked files are empty",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile,
            "must not be empty",
        ),
    ]

    failures: list[str] = []

    for test in tests:
        expectation, name, command, mutate, expected_text, *rest = test
        post_check = rest[0] if rest else None

        if expectation == "success":
            passed, message = expect_success(name, command, mutate, expected_text, post_check)
        elif expectation == "failure":
            passed, message = expect_failure(name, command, mutate, expected_text)
        else:
            passed = False
            message = f"{name}: unknown expectation {expectation!r}"

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
