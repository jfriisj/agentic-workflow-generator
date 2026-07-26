#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import pty
import select
import shutil
import signal
import subprocess
import tempfile
import time
from collections.abc import Callable
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


def run_with_pty(
    worktree: Path,
    command: list[str],
    scripted_input: str,
    timeout_seconds: float = 15.0,
) -> subprocess.CompletedProcess[str]:
    master_fd, slave_fd = pty.openpty()
    process: subprocess.Popen[bytes] | None = None
    output = bytearray()

    try:
        process = subprocess.Popen(
            command,
            cwd=worktree,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            start_new_session=True,
        )
    finally:
        os.close(slave_fd)

    try:
        os.write(master_fd, scripted_input.encode("utf-8"))
        deadline = time.monotonic() + timeout_seconds

        while True:
            if time.monotonic() >= deadline:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise RuntimeError(
                    f"PTY command timed out after {timeout_seconds:.1f} seconds: "
                    + " ".join(command)
                )

            readable, _, _ = select.select([master_fd], [], [], 0.1)

            if readable:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise

                if not chunk:
                    break

                output.extend(chunk)

            if process.poll() is not None:
                while True:
                    readable, _, _ = select.select([master_fd], [], [], 0)

                    if not readable:
                        break

                    try:
                        chunk = os.read(master_fd, 4096)
                    except OSError as exc:
                        if exc.errno == errno.EIO:
                            break
                        raise

                    if not chunk:
                        break

                    output.extend(chunk)

                break

        returncode = process.wait(timeout=1)
        stdout = output.decode("utf-8", errors="replace")

        return subprocess.CompletedProcess(
            args=command,
            returncode=returncode,
            stdout=stdout,
            stderr=None,
        )
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()

        os.close(master_fd)


def expect_interactive_guided_defaults() -> tuple[bool, str]:
    name = "interactive guided init accepts default recommendations"
    worktree = copy_repo_to_temp()

    try:
        result = run_with_pty(
            worktree,
            ["scripts/agentic/agentic-gen.sh", "init", "--guided"],
            "orchestrated-delivery-greenfield\n\n\n\ny\n",
        )

        if result.returncode != 0:
            return (
                False,
                f"{name}: expected success, but command failed.\n\n"
                f"Output:\n{result.stdout}",
            )

        required_output = (
            "== Guided Agentic Initialization ==",
            "== Generated Setup Plan ==",
            "project-type: microservice-platform [recommended]",
            "delivery-style: orchestrated-delivery [recommended]",
            "target-platforms: opencode-and-vscode-copilot [recommended]",
            "PASS: Initialized .agentic/setup-profile.json "
            "from guided setup 'orchestrated-delivery-greenfield'.",
        )

        for expected_text in required_output:
            if expected_text not in result.stdout:
                return (
                    False,
                    f"{name}: expected text was not found: {expected_text!r}\n\n"
                    f"Output:\n{result.stdout}",
                )

        post_passed, post_message = assert_guided_default_targets(worktree)
        if not post_passed:
            return False, f"{name}: {post_message}\n\nOutput:\n{result.stdout}"

        return True, f"PASS: {name}"
    finally:
        shutil.rmtree(worktree.parent, ignore_errors=True)


def expect_interactive_guided_first_question_back_returns_to_setup() -> tuple[
    bool, str
]:
    name = "interactive guided init returns to setup selection from first question"
    worktree = copy_repo_to_temp()

    try:
        result = run_with_pty(
            worktree,
            ["scripts/agentic/agentic-gen.sh", "init", "--guided"],
            "orchestrated-delivery-greenfield\nb\n"
            "orchestrated-delivery-greenfield\n\n\n\ny\n",
        )

        if result.returncode != 0:
            return (
                False,
                f"{name}: expected success, but command failed.\n\n"
                f"Output:\n{result.stdout}",
            )

        setup_heading = "== Guided Agentic Initialization =="
        if result.stdout.count(setup_heading) != 2:
            return (
                False,
                f"{name}: expected setup selection to be displayed exactly twice, "
                f"but found {result.stdout.count(setup_heading)} occurrence(s).\n\n"
                f"Output:\n{result.stdout}",
            )

        first_question = "Question 1/3:"
        if result.stdout.count(first_question) != 2:
            return (
                False,
                f"{name}: expected the first question to be displayed exactly twice, "
                f"but found {result.stdout.count(first_question)} occurrence(s).\n\n"
                f"Output:\n{result.stdout}",
            )

        expected_text = (
            "PASS: Initialized .agentic/setup-profile.json "
            "from guided setup 'orchestrated-delivery-greenfield'."
        )
        if expected_text not in result.stdout:
            return (
                False,
                f"{name}: expected completion text was not found: "
                f"{expected_text!r}\n\nOutput:\n{result.stdout}",
            )

        post_passed, post_message = assert_guided_default_targets(worktree)
        if not post_passed:
            return False, f"{name}: {post_message}\n\nOutput:\n{result.stdout}"

        return True, f"PASS: {name}"
    finally:
        shutil.rmtree(worktree.parent, ignore_errors=True)


def expect_interactive_guided_cancel_preserves_files() -> tuple[bool, str]:
    name = "interactive guided init cancellation preserves existing files"
    worktree = copy_repo_to_temp()

    profile_path = worktree / ".agentic" / "setup-profile.json"
    config_path = worktree / ".agentic" / "agentic.json"

    try:
        tracked_paths = (profile_path, config_path)
        before: dict[Path, tuple[bytes, int]] = {}

        for tracked_path in tracked_paths:
            if not tracked_path.is_file():
                return (
                    False,
                    f"{name}: required file was missing before test: {tracked_path}",
                )

            before[tracked_path] = (
                tracked_path.read_bytes(),
                tracked_path.stat().st_mtime_ns,
            )

        result = run_with_pty(
            worktree,
            ["scripts/agentic/agentic-gen.sh", "init", "--guided"],
            "q\n",
        )

        if result.returncode == 0:
            return (
                False,
                f"{name}: expected cancellation failure, but command passed.\n\n"
                f"Output:\n{result.stdout}",
            )

        expected_text = "Interactive guided init was cancelled; no files were written"
        if expected_text not in result.stdout:
            return (
                False,
                f"{name}: expected cancellation text was not found: "
                f"{expected_text!r}\n\nOutput:\n{result.stdout}",
            )

        for tracked_path, (expected_bytes, expected_mtime_ns) in before.items():
            if not tracked_path.is_file():
                return False, f"{name}: cancellation removed file: {tracked_path}"

            actual_bytes = tracked_path.read_bytes()
            actual_mtime_ns = tracked_path.stat().st_mtime_ns

            if actual_bytes != expected_bytes:
                return (
                    False,
                    f"{name}: cancellation changed file contents: {tracked_path}",
                )

            if actual_mtime_ns != expected_mtime_ns:
                return False, f"{name}: cancellation rewrote file: {tracked_path}"

        return True, f"PASS: {name}"
    finally:
        shutil.rmtree(worktree.parent, ignore_errors=True)


def expect_guided_dry_run(
    name: str,
    extra_args: list[str],
    expected_answer_line: str,
    expected_targets_line: str,
) -> tuple[bool, str]:
    worktree = copy_repo_to_temp()

    profile_path = worktree / ".agentic" / "setup-profile.json"
    config_path = worktree / ".agentic" / "agentic.json"

    try:
        tracked_paths = (profile_path, config_path)
        before: dict[Path, tuple[bytes, int]] = {}

        for tracked_path in tracked_paths:
            if not tracked_path.is_file():
                return (
                    False,
                    f"{name}: required file was missing before test: {tracked_path}",
                )

            before[tracked_path] = (
                tracked_path.read_bytes(),
                tracked_path.stat().st_mtime_ns,
            )

        command = [
            "scripts/agentic/agentic-gen.sh",
            "init",
            "--guided",
            "--setup",
            "orchestrated-delivery-greenfield",
            "--dry-run",
            *extra_args,
        ]
        result = run(worktree, command)

        if result.returncode != 0:
            return (
                False,
                f"{name}: expected success, but command failed.\n\n"
                f"Output:\n{result.stdout}",
            )

        required_output = (
            "== Generated Setup Plan ==",
            expected_answer_line,
            expected_targets_line,
            "PASS: Guided dry-run validated setup "
            "'orchestrated-delivery-greenfield'; no files were written.",
        )

        for expected_text in required_output:
            if expected_text not in result.stdout:
                return (
                    False,
                    f"{name}: expected text was not found: "
                    f"{expected_text!r}\n\n"
                    f"Output:\n{result.stdout}",
                )

        forbidden_output = (
            "PASS: Initialized .agentic/setup-profile.json",
            "PASS: Initialized .agentic/agentic.json",
        )

        for forbidden_text in forbidden_output:
            if forbidden_text in result.stdout:
                return (
                    False,
                    f"{name}: dry-run emitted write-success text: "
                    f"{forbidden_text!r}\n\n"
                    f"Output:\n{result.stdout}",
                )

        for tracked_path, (
            expected_bytes,
            expected_mtime_ns,
        ) in before.items():
            if not tracked_path.is_file():
                return (
                    False,
                    f"{name}: dry-run removed file: {tracked_path}",
                )

            actual_bytes = tracked_path.read_bytes()
            actual_mtime_ns = tracked_path.stat().st_mtime_ns

            if actual_bytes != expected_bytes:
                return (
                    False,
                    f"{name}: dry-run changed file contents: {tracked_path}",
                )

            if actual_mtime_ns != expected_mtime_ns:
                return (
                    False,
                    f"{name}: dry-run rewrote file: {tracked_path}",
                )

        return True, f"PASS: {name}"
    finally:
        shutil.rmtree(worktree.parent, ignore_errors=True)


def expect_guided_dry_run_defaults() -> tuple[bool, str]:
    return expect_guided_dry_run(
        "guided dry-run preserves files with default recommendations",
        [],
        "target-platforms: opencode-and-vscode-copilot [recommended]",
        "targets: opencode, vscode-copilot",
    )


def expect_guided_dry_run_opencode_override() -> tuple[bool, str]:
    return expect_guided_dry_run(
        "guided dry-run preserves files with target override",
        [
            "--answer",
            "target-platforms=opencode-only",
        ],
        "target-platforms: opencode-only [compatible]",
        "targets: opencode",
    )


def assert_cleanup_apply_removed_file(worktree: Path) -> tuple[bool, str]:
    path = worktree / ".github" / "agents" / "cleanup-apply-test.agent.md"
    if path.exists():
        return (
            False,
            f"cleanup apply did not remove expected file: {path.relative_to(worktree)}",
        )
    return True, "cleanup apply removed expected unmanaged file"


def assert_guided_target_selection(
    worktree: Path,
    expected_answer: str,
    expected_classification: str,
    expected_targets: list[str],
) -> tuple[bool, str]:
    setup_profile = load_json(worktree / ".agentic" / "setup-profile.json")
    config = load_json(worktree / ".agentic" / "agentic.json")

    selected = setup_profile.get("selected")
    if not isinstance(selected, dict):
        return False, "setup-profile selected must be an object"

    actual_selected_targets = selected.get("targets")
    if actual_selected_targets != expected_targets:
        return (
            False,
            f"setup-profile selected.targets was {actual_selected_targets!r}, expected {expected_targets!r}",
        )

    answers = setup_profile.get("answers")
    if not isinstance(answers, list):
        return False, "setup-profile answers must be a list"

    target_answer = next(
        (
            answer
            for answer in answers
            if isinstance(answer, dict) and answer.get("question") == "target-platforms"
        ),
        None,
    )
    if not isinstance(target_answer, dict):
        return False, "setup-profile target-platforms answer must exist"

    if target_answer.get("selected") != expected_answer:
        return (
            False,
            f"target-platforms selected was {target_answer.get('selected')!r}, expected {expected_answer!r}",
        )

    if target_answer.get("classification") != expected_classification:
        return False, (
            f"target-platforms classification was {target_answer.get('classification')!r}, "
            f"expected {expected_classification!r}"
        )

    config_targets = config.get("targets")
    if not isinstance(config_targets, list):
        return False, "agentic config targets must be a list"

    actual_config_targets = [
        target.get("name") for target in config_targets if isinstance(target, dict)
    ]
    if actual_config_targets != expected_targets:
        return (
            False,
            f"agentic config targets were {actual_config_targets!r}, expected {expected_targets!r}",
        )

    return True, "guided target selection matched setup-profile and agentic config"


def assert_guided_default_targets(worktree: Path) -> tuple[bool, str]:
    return assert_guided_target_selection(
        worktree,
        "opencode-and-vscode-copilot",
        "recommended",
        ["opencode", "vscode-copilot"],
    )


def assert_guided_opencode_only_targets(worktree: Path) -> tuple[bool, str]:
    return assert_guided_target_selection(
        worktree,
        "opencode-only",
        "compatible",
        ["opencode"],
    )


def assert_guided_vscode_copilot_only_targets(worktree: Path) -> tuple[bool, str]:
    return assert_guided_target_selection(
        worktree,
        "vscode-copilot-only",
        "compatible",
        ["vscode-copilot"],
    )


def assert_ai_application_composition(
    worktree: Path,
) -> tuple[bool, str]:
    setup_profile = load_json(worktree / ".agentic" / "setup-profile.json")
    config = load_json(worktree / ".agentic" / "agentic.json")

    selected = setup_profile.get("selected")
    if not isinstance(selected, dict):
        return False, "setup-profile selected must be an object"

    expected = {
        "bundle": "ai-application",
        "profile": "ai-application",
        "workflow": "ai-application-delivery",
        "agents": [
            "AIEvaluator",
            "Architect",
            "CodeReviewer",
            "Implementer",
            "Orchestrator",
            "QA",
            "Requirements",
            "TestRunner",
        ],
        "skills": [
            "ai-evaluation",
            "architecture-design",
            "code-review-clean-code",
            "code-review-tests",
            "implementation-engineering",
            "qa-acceptance-validation",
            "requirements-analysis",
            "security-review",
            "test-execution",
            "workflow-routing",
        ],
        "artifacts": [
            "AIEvaluationReport",
            "ArchitectureDecision",
            "CodeReview",
            "ImplementationReport",
            "QAReport",
            "Requirements",
            "TestReport",
        ],
        "targets": [
            "opencode",
            "vscode-copilot",
        ],
    }

    for key, expected_value in expected.items():
        actual_value = selected.get(key)
        if actual_value != expected_value:
            return (
                False,
                f"setup-profile selected.{key} was "
                f"{actual_value!r}, expected {expected_value!r}",
            )

    workflow = config.get("workflow")
    if not isinstance(workflow, dict):
        return False, "agentic config workflow must be an object"

    if workflow.get("profile") != "ai-application-delivery":
        return (
            False,
            "agentic config workflow.profile was "
            f"{workflow.get('profile')!r}, expected "
            "'ai-application-delivery'",
        )

    agents = config.get("agents")
    if not isinstance(agents, list):
        return False, "agentic config agents must be a list"

    actual_agents = [agent.get("name") for agent in agents if isinstance(agent, dict)]

    if actual_agents != expected["agents"]:
        return (
            False,
            f"agentic config agents were {actual_agents!r}, "
            f"expected {expected['agents']!r}",
        )

    return True, "AI application composition matched the dedicated setup"


def break_capability_coverage(worktree: Path) -> None:
    path = worktree / "registry" / "skills" / "workflow-routing" / "skill.json"
    data = load_json(path)

    changed = remove_string_from_nested_lists(data, "workflow.route")
    if not changed:
        raise RuntimeError(
            "Could not remove workflow.route from workflow-routing skill"
        )

    write_json(path, data)


def break_generated_output(worktree: Path) -> None:
    path = worktree / ".github" / "agents" / "orchestrator.agent.md"
    if not path.is_file():
        raise RuntimeError(f"Expected generated file not found before mutation: {path}")

    path.unlink()


def break_generated_selected_skill_output(worktree: Path) -> None:
    path = worktree / ".github" / "skills" / "code-review-clean-code" / "SKILL.md"
    if not path.is_file():
        raise RuntimeError(
            f"Expected generated selected skill not found before mutation: {path}"
        )

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
        raise RuntimeError(
            "first manifest target ownedPaths must be a list before mutation"
        )

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
        raise RuntimeError(
            "first manifest target ownedPaths must be a list before mutation"
        )

    owned_paths.append("../outside-repo")
    write_json(path, data)


def break_output_manifest_bundle_workflow_drift(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    bundle = data.get("bundle")
    if not isinstance(bundle, dict):
        raise RuntimeError("output manifest bundle must be an object before mutation")

    bundle["workflow"] = "wrong-workflow"
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
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    first_entry["path"] = 123
    write_json(path, data)


def break_output_manifest_generated_file_empty_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    first_entry["path"] = ""
    write_json(path, data)


def break_output_manifest_generated_file_missing_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    first_entry.pop("path", None)
    write_json(path, data)


def break_output_manifest_invalid_generated_file_entry_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    generated_files[0] = "not-an-object"
    write_json(path, data)


def break_output_manifest_empty_generated_files(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    first_target["generatedFiles"] = []
    first_target["generatedFileCount"] = 0

    summary = data.get("summary")
    if isinstance(summary, dict):
        total_files = 0
        for target in targets:
            if isinstance(target, dict) and isinstance(
                target.get("generatedFiles"), list
            ):
                total_files += len(target["generatedFiles"])
        summary["generatedFileCount"] = total_files

    write_json(path, data)


def no_mutation(worktree: Path) -> None:
    _ = worktree


def break_init_idempotency_by_changing_init_script(worktree: Path) -> None:
    path = worktree / "scripts" / "agentic" / "init-from-bundle.py"
    text = path.read_text(encoding="utf-8")

    marker = "    return generated\n"
    if marker not in text:
        raise RuntimeError("Could not find init generated return marker")

    injection = (
        '    generated["project"]["description"] = '
        'str(generated["project"].get("description", "")) + '
        '" negative init idempotency drift marker"\n'
    )

    path.write_text(text.replace(marker, injection + marker, 1), encoding="utf-8")


def break_environment_validation_node_command(worktree: Path) -> None:
    fake_bin = worktree / ".tmp-negative-node-bin"
    fake_bin.mkdir(parents=True, exist_ok=True)

    node_path = fake_bin / "node"
    node_path.write_text(
        "#!/usr/bin/env bash\necho 'negative gate broken node' >&2\nexit 42\n",
        encoding="utf-8",
    )
    node_path.chmod(0o755)

    npx_path = fake_bin / "npx"
    npx_path.write_text(
        "#!/usr/bin/env bash\necho 'negative gate fake npx'\n",
        encoding="utf-8",
    )
    npx_path.chmod(0o755)


def break_generation_idempotency_by_changing_generator(worktree: Path) -> None:
    subprocess.run(
        ["scripts/agentic/agentic-gen.sh", "all"],
        cwd=worktree,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )

    generator_path = worktree / "scripts" / "agentic" / "generate-vscode-copilot.py"
    if not generator_path.is_file():
        raise RuntimeError(
            f"Expected generator file not found before mutation: {generator_path}"
        )

    text = generator_path.read_text(encoding="utf-8")

    marker = "def main() -> int:"
    if marker not in text:
        raise RuntimeError("Could not find main() in VS Code Copilot generator")

    injection = 'print("negative idempotency drift marker")\\n    '

    text = text.replace(marker, marker + "\\n    " + injection, 1)
    generator_path.write_text(text, encoding="utf-8")


def break_output_manifest_missing_generated_files(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    first_target.pop("generatedFiles", None)
    write_json(path, data)


def break_output_manifest_owned_paths_absolute_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    first_target["ownedPaths"] = ["/tmp/agentic-owned-path-test"]
    write_json(path, data)


def break_output_manifest_owned_paths_parent_reference(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    first_target["ownedPaths"] = ["../outside"]
    write_json(path, data)


def break_output_manifest_invalid_owned_paths_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    first_target["ownedPaths"] = [123]
    write_json(path, data)


def break_output_manifest_empty_owned_paths(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

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
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    targets[0] = "not-an-object"
    write_json(path, data)


def break_output_manifest_missing_owned_paths(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    first_target.pop("ownedPaths", None)
    write_json(path, data)


def break_output_manifest_missing_target_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

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
        raise RuntimeError(
            "output manifest targets must contain at least two targets before mutation"
        )

    first_target = targets[0]
    second_target = targets[1]
    if not isinstance(first_target, dict) or not isinstance(second_target, dict):
        raise RuntimeError("output manifest targets must be objects before mutation")

    first_name = first_target.get("name")
    if not isinstance(first_name, str) or not first_name.strip():
        raise RuntimeError(
            "first output manifest target name must be a non-empty string before mutation"
        )

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
        raise RuntimeError(
            "summary.generatedFileCount must be an integer before mutation"
        )

    summary["generatedFileCount"] = current_total + 1
    write_json(path, data)


def break_output_manifest_generated_file_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list):
        raise RuntimeError(
            "output manifest generatedFiles must be a list before mutation"
        )

    first_target["generatedFileCount"] = len(generated_files) + 1
    write_json(path, data)


def break_output_manifest_duplicate_generated_file_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    generated_files.append(dict(first_entry))
    first_target["generatedFileCount"] = len(generated_files)

    summary = data.get("summary")
    if isinstance(summary, dict):
        total_files = 0
        for target in targets:
            if isinstance(target, dict) and isinstance(
                target.get("generatedFiles"), list
            ):
                total_files += len(target["generatedFiles"])
        summary["generatedFileCount"] = total_files

    write_json(path, data)


def break_output_manifest_declared_file_missing(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    generated_path = first_entry.get("path")
    if not isinstance(generated_path, str) or not generated_path.strip():
        raise RuntimeError(
            "output manifest generatedFiles[0].path must be a non-empty string before mutation"
        )

    file_path = worktree / generated_path
    if not file_path.is_file():
        raise RuntimeError(
            f"Expected generated file to exist before mutation: {generated_path}"
        )

    file_path.unlink()


def break_output_manifest_generated_file_absolute_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    first_entry["path"] = "/tmp/agentic-generated-file-test.md"
    write_json(path, data)


def break_output_manifest_generated_file_parent_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    first_entry["path"] = "../README.md"
    write_json(path, data)


def break_output_manifest_generated_file_missing_bytes(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    first_entry.pop("bytes", None)
    write_json(path, data)


def break_output_manifest_invalid_bytes(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    first_entry["bytes"] = "not-an-integer"
    write_json(path, data)


def break_output_manifest_byte_size(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    current_bytes = first_entry.get("bytes")
    if not isinstance(current_bytes, int):
        raise RuntimeError(
            "output manifest generatedFiles[0].bytes must be an integer before mutation"
        )

    first_entry["bytes"] = current_bytes + 1
    write_json(path, data)


def break_output_manifest_generated_file_missing_sha256(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    first_entry.pop("sha256", None)
    write_json(path, data)


def break_output_manifest_invalid_sha256(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "output-manifest.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

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
        raise RuntimeError(
            "output manifest targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError(
            "output manifest first target must be an object before mutation"
        )

    generated_files = first_target.get("generatedFiles")
    if not isinstance(generated_files, list) or not generated_files:
        raise RuntimeError(
            "output manifest generatedFiles must be a non-empty list before mutation"
        )

    first_entry = generated_files[0]
    if not isinstance(first_entry, dict):
        raise RuntimeError(
            "output manifest generatedFiles[0] must be an object before mutation"
        )

    outside_path = "README.md"
    absolute_outside_path = worktree / outside_path
    if not absolute_outside_path.is_file():
        raise RuntimeError(
            f"Expected outside file to exist before mutation: {outside_path}"
        )

    mutated_entry = dict(first_entry)
    mutated_entry["path"] = outside_path
    mutated_entry["sha256"] = hashlib.sha256(
        absolute_outside_path.read_bytes()
    ).hexdigest()
    mutated_entry["bytes"] = absolute_outside_path.stat().st_size

    generated_files.append(mutated_entry)
    first_target["generatedFileCount"] = len(generated_files)

    summary = data.get("summary")
    if isinstance(summary, dict):
        total_files = 0
        for target in targets:
            if isinstance(target, dict) and isinstance(
                target.get("generatedFiles"), list
            ):
                total_files += len(target["generatedFiles"])
        summary["generatedFileCount"] = total_files

    write_json(path, data)


def break_output_manifest_ownership(worktree: Path) -> None:
    path = worktree / ".github" / "agents" / "extra.agent.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Extra generated file drift test\n", encoding="utf-8")


def break_registry_schema_agent_version_pattern(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)
    data["version"] = "0.2"
    write_json(path, data)


def break_registry_schema_workflow_states_min_items(
    worktree: Path,
) -> None:
    path = awg_default_workflow_registry_file(worktree)
    data = load_json(path)
    data["states"] = []
    write_json(path, data)


def break_registry_schema_workflow_terminal_const(
    worktree: Path,
) -> None:
    path = awg_default_workflow_registry_file(worktree)
    data = load_json(path)

    states = data.get("states")
    if not isinstance(states, list):
        raise RuntimeError("workflow states must be a list before mutation")

    for state in states:
        if isinstance(state, dict) and state.get("terminal") is True:
            state["terminal"] = False
            write_json(path, data)
            return

    raise RuntimeError("expected a terminal workflow state before mutation")


def break_registry_schema_permission_bash_enum(
    worktree: Path,
) -> None:
    path = (
        worktree
        / "registry"
        / "permission-profiles"
        / "read-only"
        / "permission-profile.json"
    )

    if not path.is_file():
        raise RuntimeError(f"expected permission profile before mutation: {path}")

    data = load_json(path)
    data["bash"] = "root"
    write_json(path, data)


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


def break_target_adapter_owned_path_overlap(worktree: Path) -> None:
    path = worktree / "registry" / "targets" / "opencode" / "adapter.json"
    data = load_json(path)

    owned_paths = data.get("ownedPaths")
    if not isinstance(owned_paths, list):
        raise RuntimeError("ownedPaths must be a list before mutation")

    if ".github/agents" not in owned_paths:
        owned_paths.append(".github/agents")

    write_json(path, data)


def break_resolution_target_empty_adapter_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    if first_target.get("missing") is not False:
        raise RuntimeError("resolution targets[0] must be non-missing before mutation")

    first_target["adapterPath"] = ""
    write_json(path, data)


def break_resolution_target_invalid_adapter_path_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    if first_target.get("missing") is not False:
        raise RuntimeError("resolution targets[0] must be non-missing before mutation")

    first_target["adapterPath"] = {"not": "a-string"}
    write_json(path, data)


def break_resolution_target_missing_adapter_path(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    first_target.pop("adapterPath", None)
    write_json(path, data)


def break_resolution_target_invalid_enabled_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    first_target["enabled"] = "not-a-boolean"
    write_json(path, data)


def break_resolution_target_missing_enabled(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    first_target.pop("enabled", None)
    write_json(path, data)


def break_resolution_target_missing_missing_flag(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    first_target.pop("missing", None)
    write_json(path, data)


def break_resolution_target_invalid_missing_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    first_target["missing"] = "not-a-list"
    write_json(path, data)


def break_resolution_target_invalid_name_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    first_target["name"] = {"not": "a-string"}
    write_json(path, data)


def break_resolution_target_empty_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    first_target["name"] = ""
    write_json(path, data)


def break_resolution_target_missing_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    first_target.pop("name", None)
    write_json(path, data)


def break_resolution_target_entry_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    targets[0] = "not-an-object"
    write_json(path, data)


def break_resolution_invalid_targets_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data["targets"] = {"not": "a-list"}
    write_json(path, data)


def break_resolution_empty_targets(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data["targets"] = []
    write_json(path, data)


def break_resolution_missing_targets(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data.pop("targets", None)
    write_json(path, data)


def break_resolution_resolved_capability_invalid_skill_path_type(
    worktree: Path,
) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved["skillPath"] = {"not": "a-string"}
    write_json(path, data)


def break_resolution_resolved_capability_empty_skill_path(worktree: Path) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved["skillPath"] = ""
    write_json(path, data)


def break_resolution_resolved_capability_missing_skill_path(worktree: Path) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved.pop("skillPath", None)
    write_json(path, data)


def break_resolution_resolved_capability_invalid_skill_type(worktree: Path) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved["skill"] = {"not": "a-string"}
    write_json(path, data)


def break_resolution_resolved_capability_empty_skill(worktree: Path) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved["skill"] = ""
    write_json(path, data)


def break_resolution_resolved_capability_missing_skill(worktree: Path) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved.pop("skill", None)
    write_json(path, data)


def break_resolution_resolved_capability_invalid_capability_type(
    worktree: Path,
) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved["capability"] = {"not": "a-string"}
    write_json(path, data)


def break_resolution_resolved_capability_empty_capability(worktree: Path) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved["capability"] = ""
    write_json(path, data)


def break_resolution_resolved_capability_missing_capability(worktree: Path) -> None:
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

    first_resolved = resolved[0]
    if not isinstance(first_resolved, dict):
        raise RuntimeError("resolvedCapabilities[0] must be an object before mutation")

    first_resolved.pop("capability", None)
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
        raise RuntimeError(
            "resolvedCapabilities must be a non-empty list before mutation"
        )

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


def first_resolution_agent_with_produces(
    data: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    agents = data.get("agents")
    if not isinstance(agents, list):
        raise RuntimeError("resolution agents must be a list before mutation")

    for index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            continue

        produces = agent.get("produces")
        if isinstance(produces, list) and produces:
            return index, agent

    raise RuntimeError("expected at least one agent with produces before mutation")


def first_resolution_produce(
    data: dict[str, Any],
) -> tuple[int, dict[str, Any], int, dict[str, Any]]:
    agent_index, agent = first_resolution_agent_with_produces(data)

    produces = agent.get("produces")
    if not isinstance(produces, list) or not produces:
        raise RuntimeError("agent produces must be a non-empty list before mutation")

    produce = produces[0]
    if not isinstance(produce, dict):
        raise RuntimeError("first produce entry must be an object before mutation")

    return agent_index, agent, 0, produce


def mutate_resolution_agent_string_field(
    worktree: Path,
    field: str,
    action: str,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents or not isinstance(agents[0], dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    if action == "missing":
        agents[0].pop(field, None)
    elif action == "empty":
        agents[0][field] = ""
    elif action == "invalid-type":
        agents[0][field] = {"not": "a-string"}
    else:
        raise RuntimeError(f"Unknown agent string mutation action: {action}")

    write_json(path, data)


def semantic_resolution_targets(data: dict[str, Any]) -> list[Any]:
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )
    return targets


def semantic_first_present_resolution_target(data: dict[str, Any]) -> dict[str, Any]:
    for target in semantic_resolution_targets(data):
        if isinstance(target, dict) and target.get("missing") is False:
            return target
    raise RuntimeError("expected at least one non-missing target before mutation")


def semantic_first_missing_resolution_target(data: dict[str, Any]) -> dict[str, Any]:
    targets = semantic_resolution_targets(data)

    for target in targets:
        if isinstance(target, dict) and target.get("missing") is True:
            return target

    target = {
        "name": "missing-negative-gate-target",
        "enabled": False,
        "adapterPath": None,
        "missing": True,
    }
    targets.append(target)

    summary = data.get("summary")
    if isinstance(summary, dict):
        summary["targetCount"] = len(targets)

    return target


def break_resolution_agent_registry_path_missing_file(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents or not isinstance(agents[0], dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    agents[0]["registryPath"] = "registry/agents/does-not-exist/agent.json"
    write_json(path, data)


def break_resolution_produce_contract_path_missing_file(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    _, _, _, produce = first_resolution_produce(data)
    produce["contractPath"] = "registry/artifacts/DoesNotExist/artifact.json"

    write_json(path, data)


def break_resolution_target_adapter_path_missing_file(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    target = semantic_first_present_resolution_target(data)
    target["adapterPath"] = "registry/targets/does-not-exist/adapter.json"

    write_json(path, data)


def break_resolution_semantic_missing_target_enabled_true(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    target = semantic_first_missing_resolution_target(data)
    target["enabled"] = True

    write_json(path, data)


def break_resolution_semantic_missing_target_adapter_path_non_null(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    target = semantic_first_missing_resolution_target(data)
    target["adapterPath"] = "registry/targets/missing/adapter.json"

    write_json(path, data)


def break_resolution_semantic_present_target_enabled_false(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    target = semantic_first_present_resolution_target(data)
    target["enabled"] = False

    write_json(path, data)


def break_resolution_semantic_present_target_adapter_path_null(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    target = semantic_first_present_resolution_target(data)
    target["adapterPath"] = None

    write_json(path, data)


def break_resolution_semantic_duplicate_target_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = semantic_resolution_targets(data)
    if len(targets) < 2:
        raise RuntimeError(
            "resolution targets must contain at least two targets before mutation"
        )

    first = targets[0]
    second = targets[1]
    if not isinstance(first, dict) or not isinstance(second, dict):
        raise RuntimeError(
            "resolution targets[0] and targets[1] must be objects before mutation"
        )

    name = first.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError(
            "resolution targets[0].name must be a non-empty string before mutation"
        )

    second["name"] = name
    write_json(path, data)


def break_resolution_target_adapter_path_parent_reference(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    target = targets[0]
    if not isinstance(target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    if target.get("missing") is not False:
        raise RuntimeError("resolution targets[0] must be non-missing before mutation")

    target["adapterPath"] = "../registry/targets/unsafe/adapter.json"
    write_json(path, data)


def break_resolution_target_adapter_path_absolute(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError(
            "resolution targets must be a non-empty list before mutation"
        )

    target = targets[0]
    if not isinstance(target, dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    if target.get("missing") is not False:
        raise RuntimeError("resolution targets[0] must be non-missing before mutation")

    target["adapterPath"] = "/tmp/unsafe/adapter.json"
    write_json(path, data)


def break_resolution_agent_registry_path_parent_reference(worktree: Path) -> None:
    mutate_resolution_agent_string_field(worktree, "registryPath", "empty")

    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents or not isinstance(agents[0], dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    agents[0]["registryPath"] = "../registry/agents/unsafe/agent.json"
    write_json(path, data)


def break_resolution_agent_registry_path_absolute(worktree: Path) -> None:
    mutate_resolution_agent_string_field(worktree, "registryPath", "empty")

    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents or not isinstance(agents[0], dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    agents[0]["registryPath"] = "/tmp/unsafe/agent.json"
    write_json(path, data)


def break_resolution_produce_contract_path_parent_reference(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    _, _, _, produce = first_resolution_produce(data)
    produce["contractPath"] = "../registry/artifacts/unsafe/artifact.json"
    write_json(path, data)


def break_resolution_produce_contract_path_absolute(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    _, _, _, produce = first_resolution_produce(data)
    produce["contractPath"] = "/tmp/unsafe/artifact.json"
    write_json(path, data)


def break_resolution_produce_path_pattern_parent_reference(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    _, _, _, produce = first_resolution_produce(data)
    produce["pathPattern"] = "../agent-output/unsafe/*.md"
    write_json(path, data)


def break_resolution_produce_path_pattern_absolute(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    _, _, _, produce = first_resolution_produce(data)
    produce["pathPattern"] = "/tmp/agent-output/unsafe/*.md"
    write_json(path, data)


def break_resolution_agent_missing_role(worktree: Path) -> None:
    mutate_resolution_agent_string_field(worktree, "role", "missing")


def break_resolution_agent_empty_role(worktree: Path) -> None:
    mutate_resolution_agent_string_field(worktree, "role", "empty")


def break_resolution_agent_invalid_role_type(worktree: Path) -> None:
    mutate_resolution_agent_string_field(worktree, "role", "invalid-type")


def break_resolution_agent_missing_registry_path(worktree: Path) -> None:
    mutate_resolution_agent_string_field(worktree, "registryPath", "missing")


def break_resolution_agent_empty_registry_path(worktree: Path) -> None:
    mutate_resolution_agent_string_field(worktree, "registryPath", "empty")


def break_resolution_agent_invalid_registry_path_type(worktree: Path) -> None:
    mutate_resolution_agent_string_field(worktree, "registryPath", "invalid-type")


def break_resolution_duplicate_agent_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or len(agents) < 2:
        raise RuntimeError(
            "resolution agents must contain at least two agents before mutation"
        )

    first_agent = agents[0]
    second_agent = agents[1]
    if not isinstance(first_agent, dict) or not isinstance(second_agent, dict):
        raise RuntimeError(
            "resolution agents[0] and agents[1] must be objects before mutation"
        )

    first_name = first_agent.get("name")
    if not isinstance(first_name, str) or not first_name.strip():
        raise RuntimeError(
            "resolution agents[0].name must be a non-empty string before mutation"
        )

    second_agent["name"] = first_name
    write_json(path, data)


def break_resolution_agent_missing_produces(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents or not isinstance(agents[0], dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    agents[0].pop("produces", None)
    write_json(path, data)


def break_resolution_agent_invalid_produces_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents or not isinstance(agents[0], dict):
        raise RuntimeError("resolution agents[0] must be an object before mutation")

    agents[0]["produces"] = "not-a-list"
    write_json(path, data)


def break_resolution_agent_produces_entry_invalid_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    _, agent = first_resolution_agent_with_produces(data)
    produces = agent.get("produces")
    if not isinstance(produces, list) or not produces:
        raise RuntimeError("agent produces must be a non-empty list before mutation")

    produces[0] = "not-an-object"
    write_json(path, data)


def mutate_resolution_produce_string_field(
    worktree: Path,
    field: str,
    action: str,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    _, _, _, produce = first_resolution_produce(data)

    if action == "missing":
        produce.pop(field, None)
    elif action == "empty":
        produce[field] = ""
    elif action == "invalid-type":
        produce[field] = {"not": "a-string"}
    else:
        raise RuntimeError(f"Unknown produce string mutation action: {action}")

    write_json(path, data)


def mutate_resolution_produce_string_list_field(
    worktree: Path,
    field: str,
    action: str,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    _, _, _, produce = first_resolution_produce(data)

    if action == "missing":
        produce.pop(field, None)
    elif action == "invalid-type":
        produce[field] = {"not": "a-list"}
    elif action == "empty-list":
        produce[field] = []
    elif action == "invalid-entry-type":
        values = produce.get(field)
        if not isinstance(values, list) or not values:
            raise RuntimeError(
                f"produce.{field} must be a non-empty list before mutation"
            )
        values[0] = {"not": "a-string"}
    elif action == "empty-entry":
        values = produce.get(field)
        if not isinstance(values, list) or not values:
            raise RuntimeError(
                f"produce.{field} must be a non-empty list before mutation"
            )
        values[0] = ""
    elif action == "duplicate-entry":
        values = produce.get(field)
        if not isinstance(values, list) or not values:
            raise RuntimeError(
                f"produce.{field} must be a non-empty list before mutation"
            )
        values.append(values[0])
    else:
        raise RuntimeError(f"Unknown produce string-list mutation action: {action}")

    write_json(path, data)


def break_resolution_produce_missing_type(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "type", "missing")


def break_resolution_produce_empty_type(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "type", "empty")


def break_resolution_produce_invalid_type_type(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "type", "invalid-type")


def break_resolution_produce_missing_contract_path(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "contractPath", "missing")


def break_resolution_produce_empty_contract_path(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "contractPath", "empty")


def break_resolution_produce_invalid_contract_path_type(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "contractPath", "invalid-type")


def break_resolution_produce_missing_path_pattern(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "pathPattern", "missing")


def break_resolution_produce_empty_path_pattern(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "pathPattern", "empty")


def break_resolution_produce_invalid_path_pattern_type(worktree: Path) -> None:
    mutate_resolution_produce_string_field(worktree, "pathPattern", "invalid-type")


def break_resolution_produce_missing_allowed_statuses(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(worktree, "allowedStatuses", "missing")


def break_resolution_produce_invalid_allowed_statuses_type(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "allowedStatuses", "invalid-type"
    )


def break_resolution_produce_empty_allowed_statuses(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "allowedStatuses", "empty-list"
    )


def break_resolution_produce_invalid_allowed_status_entry_type(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "allowedStatuses", "invalid-entry-type"
    )


def break_resolution_produce_empty_allowed_status_entry(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "allowedStatuses", "empty-entry"
    )


def break_resolution_produce_duplicate_allowed_status(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "allowedStatuses", "duplicate-entry"
    )


def break_resolution_produce_missing_required_headings(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(worktree, "requiredHeadings", "missing")


def break_resolution_produce_invalid_required_headings_type(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "requiredHeadings", "invalid-type"
    )


def break_resolution_produce_empty_required_headings(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "requiredHeadings", "empty-list"
    )


def break_resolution_produce_invalid_required_heading_entry_type(
    worktree: Path,
) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "requiredHeadings", "invalid-entry-type"
    )


def break_resolution_produce_empty_required_heading_entry(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "requiredHeadings", "empty-entry"
    )


def break_resolution_produce_duplicate_required_heading(worktree: Path) -> None:
    mutate_resolution_produce_string_list_field(
        worktree, "requiredHeadings", "duplicate-entry"
    )


def break_resolution_summary_wrong_produced_artifact_binding_count(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    produced_count = summary.get("producedArtifactBindingCount")
    if not isinstance(produced_count, int) or isinstance(produced_count, bool):
        raise RuntimeError(
            "summary.producedArtifactBindingCount must be an integer before mutation"
        )

    summary["producedArtifactBindingCount"] = produced_count + 1
    write_json(path, data)


def break_resolution_missing_project(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data.pop("project", None)
    write_json(path, data)


def break_resolution_invalid_project_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data["project"] = "not-an-object"
    write_json(path, data)


def mutate_project_string_field(
    worktree: Path,
    field: str,
    action: str,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("resolution project must be an object before mutation")

    if action == "missing":
        project.pop(field, None)
    elif action == "empty":
        project[field] = ""
    elif action == "invalid-type":
        project[field] = {"not": "a-string"}
    else:
        raise RuntimeError(f"Unknown project string mutation action: {action}")

    write_json(path, data)


def mutate_project_list_field(
    worktree: Path,
    field: str,
    action: str,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("resolution project must be an object before mutation")

    if action == "missing":
        project.pop(field, None)
    elif action == "invalid-type":
        project[field] = {"not": "a-list"}
    elif action == "empty-list":
        project[field] = []
    elif action == "invalid-entry-type":
        values = project.get(field)
        if not isinstance(values, list) or not values:
            raise RuntimeError(
                f"project.{field} must be a non-empty list before mutation"
            )
        values[0] = {"not": "a-string"}
    elif action == "empty-entry":
        values = project.get(field)
        if not isinstance(values, list) or not values:
            raise RuntimeError(
                f"project.{field} must be a non-empty list before mutation"
            )
        values[0] = ""
    elif action == "duplicate-entry":
        values = project.get(field)
        if not isinstance(values, list) or not values:
            raise RuntimeError(
                f"project.{field} must be a non-empty list before mutation"
            )
        values.append(values[0])
    else:
        raise RuntimeError(f"Unknown project list mutation action: {action}")

    write_json(path, data)


def break_resolution_project_missing_name(worktree: Path) -> None:
    mutate_project_string_field(worktree, "name", "missing")


def break_resolution_project_empty_name(worktree: Path) -> None:
    mutate_project_string_field(worktree, "name", "empty")


def break_resolution_project_invalid_name_type(worktree: Path) -> None:
    mutate_project_string_field(worktree, "name", "invalid-type")


def break_resolution_project_missing_type(worktree: Path) -> None:
    mutate_project_string_field(worktree, "type", "missing")


def break_resolution_project_empty_type(worktree: Path) -> None:
    mutate_project_string_field(worktree, "type", "empty")


def break_resolution_project_invalid_type_type(worktree: Path) -> None:
    mutate_project_string_field(worktree, "type", "invalid-type")


def break_resolution_project_missing_description(worktree: Path) -> None:
    mutate_project_string_field(worktree, "description", "missing")


def break_resolution_project_empty_description(worktree: Path) -> None:
    mutate_project_string_field(worktree, "description", "empty")


def break_resolution_project_invalid_description_type(worktree: Path) -> None:
    mutate_project_string_field(worktree, "description", "invalid-type")


def break_resolution_project_missing_architecture_profile(worktree: Path) -> None:
    mutate_project_string_field(worktree, "architectureProfile", "missing")


def break_resolution_project_empty_architecture_profile(worktree: Path) -> None:
    mutate_project_string_field(worktree, "architectureProfile", "empty")


def break_resolution_project_invalid_architecture_profile_type(worktree: Path) -> None:
    mutate_project_string_field(worktree, "architectureProfile", "invalid-type")


def break_resolution_project_missing_language_profiles(worktree: Path) -> None:
    mutate_project_list_field(worktree, "languageProfiles", "missing")


def break_resolution_project_invalid_language_profiles_type(worktree: Path) -> None:
    mutate_project_list_field(worktree, "languageProfiles", "invalid-type")


def break_resolution_project_empty_language_profiles(worktree: Path) -> None:
    mutate_project_list_field(worktree, "languageProfiles", "empty-list")


def break_resolution_project_invalid_language_profile_entry_type(
    worktree: Path,
) -> None:
    mutate_project_list_field(worktree, "languageProfiles", "invalid-entry-type")


def break_resolution_project_empty_language_profile_entry(worktree: Path) -> None:
    mutate_project_list_field(worktree, "languageProfiles", "empty-entry")


def break_resolution_project_duplicate_language_profile(worktree: Path) -> None:
    mutate_project_list_field(worktree, "languageProfiles", "duplicate-entry")


def break_resolution_project_missing_runtime_profiles(worktree: Path) -> None:
    mutate_project_list_field(worktree, "runtimeProfiles", "missing")


def break_resolution_project_invalid_runtime_profiles_type(worktree: Path) -> None:
    mutate_project_list_field(worktree, "runtimeProfiles", "invalid-type")


def break_resolution_project_empty_runtime_profiles(worktree: Path) -> None:
    mutate_project_list_field(worktree, "runtimeProfiles", "empty-list")


def break_resolution_project_invalid_runtime_profile_entry_type(worktree: Path) -> None:
    mutate_project_list_field(worktree, "runtimeProfiles", "invalid-entry-type")


def break_resolution_project_empty_runtime_profile_entry(worktree: Path) -> None:
    mutate_project_list_field(worktree, "runtimeProfiles", "empty-entry")


def break_resolution_project_duplicate_runtime_profile(worktree: Path) -> None:
    mutate_project_list_field(worktree, "runtimeProfiles", "duplicate-entry")


def resolution_workflow(data: dict[str, Any]) -> dict[str, Any]:
    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")
    return workflow


def break_resolution_project_config_mismatch(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("resolution project must be an object before mutation")

    project["name"] = "different-project-name"
    write_json(path, data)


def break_resolution_workflow_config_mismatch(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow["startState"] = "Architect"
    write_json(path, data)


def break_resolution_target_config_name_mismatch(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets or not isinstance(targets[0], dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    targets[0]["name"] = "different-target-name"
    write_json(path, data)


def break_resolution_target_config_enabled_mismatch(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets or not isinstance(targets[0], dict):
        raise RuntimeError("resolution targets[0] must be an object before mutation")

    targets[0]["enabled"] = False
    write_json(path, data)


def break_resolution_workflow_profile_missing_registry_file(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = resolution_workflow(data)
    workflow["profile"] = "does-not-exist"

    write_json(path, data)


def break_resolution_workflow_profile_unsafe_registry_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = resolution_workflow(data)
    workflow["profile"] = "../orchestrated-delivery"

    write_json(path, data)


def break_resolution_workflow_start_state_unknown_registry_state(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = resolution_workflow(data)
    workflow["startState"] = "UnknownState"

    write_json(path, data)


def break_resolution_workflow_start_state_terminal_registry_state(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = resolution_workflow(data)
    workflow["startState"] = "Done"

    write_json(path, data)


def break_resolution_workflow_terminal_state_unknown_registry_state(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = resolution_workflow(data)
    terminal_states = workflow.get("terminalStates")
    if not isinstance(terminal_states, list) or not terminal_states:
        raise RuntimeError(
            "workflow.terminalStates must be a non-empty list before mutation"
        )

    terminal_states[0] = "UnknownTerminalState"

    write_json(path, data)


def break_resolution_workflow_terminal_state_non_terminal_registry_state(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = resolution_workflow(data)
    terminal_states = workflow.get("terminalStates")
    if not isinstance(terminal_states, list) or not terminal_states:
        raise RuntimeError(
            "workflow.terminalStates must be a non-empty list before mutation"
        )

    terminal_states[0] = "Requirements"

    write_json(path, data)


def break_resolution_workflow_fail_closed_registry_mismatch(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = resolution_workflow(data)
    workflow["failClosed"] = False

    write_json(path, data)


def break_resolution_workflow_missing_transitions(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow.pop("transitions", None)
    write_json(path, data)


def break_resolution_workflow_transition_target_mismatch(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    transitions = workflow.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        raise RuntimeError(
            "resolution workflow transitions must be a non-empty list before mutation"
        )

    first = transitions[0]
    if not isinstance(first, dict):
        raise RuntimeError(
            "resolution workflow transition must be an object before mutation"
        )

    first["to"] = "Blocked"
    write_json(path, data)


def break_resolution_workflow_transition_event_mismatch(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    transitions = workflow.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        raise RuntimeError(
            "resolution workflow transitions must be a non-empty list before mutation"
        )

    first = transitions[0]
    if not isinstance(first, dict):
        raise RuntimeError(
            "resolution workflow transition must be an object before mutation"
        )

    first["on"] = "changed"
    write_json(path, data)


def break_resolution_workflow_transition_count_mismatch(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    transitions = workflow.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        raise RuntimeError(
            "resolution workflow transitions must be a non-empty list before mutation"
        )

    transitions.pop()
    write_json(path, data)


def break_resolution_missing_workflow(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data.pop("workflow", None)
    write_json(path, data)


def break_resolution_invalid_workflow_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data["workflow"] = "not-an-object"
    write_json(path, data)


def break_resolution_workflow_missing_fail_closed(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow.pop("failClosed", None)
    write_json(path, data)


def break_resolution_workflow_invalid_fail_closed_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow["failClosed"] = "not-a-boolean"
    write_json(path, data)


def break_resolution_workflow_missing_profile(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow.pop("profile", None)
    write_json(path, data)


def break_resolution_workflow_empty_profile(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow["profile"] = ""
    write_json(path, data)


def break_resolution_workflow_invalid_profile_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow["profile"] = {"not": "a-string"}
    write_json(path, data)


def break_resolution_workflow_missing_start_state(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow.pop("startState", None)
    write_json(path, data)


def break_resolution_workflow_empty_start_state(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow["startState"] = ""
    write_json(path, data)


def break_resolution_workflow_invalid_start_state_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow["startState"] = {"not": "a-string"}
    write_json(path, data)


def break_resolution_workflow_missing_terminal_states(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow.pop("terminalStates", None)
    write_json(path, data)


def break_resolution_workflow_invalid_terminal_states_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow["terminalStates"] = {"not": "a-list"}
    write_json(path, data)


def break_resolution_workflow_empty_terminal_states(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    workflow["terminalStates"] = []
    write_json(path, data)


def break_resolution_workflow_invalid_terminal_state_entry_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    terminal_states = workflow.get("terminalStates")
    if not isinstance(terminal_states, list) or not terminal_states:
        raise RuntimeError(
            "workflow terminalStates must be a non-empty list before mutation"
        )

    terminal_states[0] = {"not": "a-string"}
    write_json(path, data)


def break_resolution_workflow_empty_terminal_state_entry(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    terminal_states = workflow.get("terminalStates")
    if not isinstance(terminal_states, list) or not terminal_states:
        raise RuntimeError(
            "workflow terminalStates must be a non-empty list before mutation"
        )

    terminal_states[0] = ""
    write_json(path, data)


def break_resolution_workflow_duplicate_terminal_state(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RuntimeError("resolution workflow must be an object before mutation")

    terminal_states = workflow.get("terminalStates")
    if not isinstance(terminal_states, list) or not terminal_states:
        raise RuntimeError(
            "workflow terminalStates must be a non-empty list before mutation"
        )

    terminal_states.append(terminal_states[0])
    write_json(path, data)


def break_resolution_missing_summary(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data.pop("summary", None)
    write_json(path, data)


def break_resolution_invalid_summary_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    data["summary"] = "not-an-object"
    write_json(path, data)


def break_resolution_summary_missing_agent_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary.pop("agentCount", None)
    write_json(path, data)


def break_resolution_summary_invalid_agent_count_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary["agentCount"] = "not-an-integer"
    write_json(path, data)


def break_resolution_summary_wrong_agent_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    agent_count = summary.get("agentCount")
    if not isinstance(agent_count, int) or isinstance(agent_count, bool):
        raise RuntimeError("summary.agentCount must be an integer before mutation")

    summary["agentCount"] = agent_count + 1
    write_json(path, data)


def break_resolution_summary_missing_target_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary.pop("targetCount", None)
    write_json(path, data)


def break_resolution_summary_invalid_target_count_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary["targetCount"] = "not-an-integer"
    write_json(path, data)


def break_resolution_summary_wrong_target_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    target_count = summary.get("targetCount")
    if not isinstance(target_count, int) or isinstance(target_count, bool):
        raise RuntimeError("summary.targetCount must be an integer before mutation")

    summary["targetCount"] = target_count + 1
    write_json(path, data)


def break_resolution_summary_missing_available_skill_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary.pop("availableSkillCount", None)
    write_json(path, data)


def break_resolution_summary_invalid_available_skill_count_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary["availableSkillCount"] = "not-an-integer"
    write_json(path, data)


def break_resolution_summary_missing_produced_artifact_binding_count(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary.pop("producedArtifactBindingCount", None)
    write_json(path, data)


def break_resolution_summary_invalid_produced_artifact_binding_count_type(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary["producedArtifactBindingCount"] = "not-an-integer"
    write_json(path, data)


def break_resolution_summary_missing_error_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary.pop("errorCount", None)
    write_json(path, data)


def break_resolution_summary_invalid_error_count_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary["errorCount"] = "not-an-integer"
    write_json(path, data)


def break_resolution_summary_nonzero_error_count(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary["errorCount"] = 1
    write_json(path, data)


def break_resolution_summary_missing_errors(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary.pop("errors", None)
    write_json(path, data)


def break_resolution_summary_invalid_errors_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary["errors"] = "not-a-list"
    write_json(path, data)


def break_resolution_summary_nonempty_errors(worktree: Path) -> None:
    path = worktree / ".agentic" / "generated" / "resolution.json"
    data = load_json(path)

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object before mutation")

    summary["errors"] = ["synthetic resolution summary error"]
    write_json(path, data)


def first_agent_registry_file(worktree: Path) -> Path:
    agent_files = sorted((worktree / "registry" / "agents").glob("*/agent.json"))
    if not agent_files:
        raise RuntimeError("expected at least one agent registry file")
    return agent_files[0]


def first_producing_agent_registry_file(worktree: Path) -> Path:
    agent_files = sorted((worktree / "registry" / "agents").glob("*/agent.json"))

    for path in agent_files:
        data = load_json(path)
        produces = data.get("produces")
        required_artifacts = data.get("requiredArtifacts")

        if isinstance(produces, list) and produces:
            return path

        if isinstance(required_artifacts, list) and required_artifacts:
            return path

    raise RuntimeError("expected at least one agent with artifact references")


def first_skill_json_file(worktree: Path) -> Path:
    skill_files = sorted((worktree / "registry" / "skills").glob("*/skill.json"))
    if not skill_files:
        raise RuntimeError("expected at least one skill registry file")
    return skill_files[0]


def first_two_skill_json_files(worktree: Path) -> tuple[Path, Path]:
    skill_files = sorted((worktree / "registry" / "skills").glob("*/skill.json"))
    if len(skill_files) < 2:
        raise RuntimeError("expected at least two skill registry files")
    return skill_files[0], skill_files[1]


def awg_default_workflow_registry_file(worktree: Path) -> Path:
    path = worktree / "registry" / "workflows" / "orchestrated-delivery.workflow.json"

    if not path.is_file():
        raise RuntimeError(
            "expected default workflow registry file: "
            "registry/workflows/orchestrated-delivery.workflow.json"
        )

    return path


def awg_mutate_default_workflow(worktree: Path, mutator) -> None:
    path = awg_default_workflow_registry_file(worktree)
    data = load_json(path)
    mutator(data)
    write_json(path, data)


def awg_first_target_adapter_file(worktree: Path) -> Path:
    adapter_files = sorted((worktree / "registry" / "targets").glob("*/adapter.json"))
    if not adapter_files:
        raise RuntimeError("expected at least one target adapter file")
    return adapter_files[0]


def awg_mutate_first_target_adapter(worktree: Path, mutator) -> None:
    path = awg_first_target_adapter_file(worktree)
    data = load_json(path)
    mutator(data)
    write_json(path, data)


def break_target_adapter_missing_name(worktree: Path) -> None:
    awg_mutate_first_target_adapter(worktree, lambda data: data.pop("name", None))


def break_target_adapter_empty_name(worktree: Path) -> None:
    awg_mutate_first_target_adapter(worktree, lambda data: data.__setitem__("name", ""))


def break_target_adapter_name_folder_mismatch(worktree: Path) -> None:
    awg_mutate_first_target_adapter(
        worktree, lambda data: data.__setitem__("name", "different-target")
    )


def break_target_adapter_missing_owned_paths(worktree: Path) -> None:
    awg_mutate_first_target_adapter(worktree, lambda data: data.pop("ownedPaths", None))


def break_target_adapter_invalid_owned_paths_type(worktree: Path) -> None:
    awg_mutate_first_target_adapter(
        worktree, lambda data: data.__setitem__("ownedPaths", "not-a-list")
    )


def break_target_adapter_empty_owned_paths(worktree: Path) -> None:
    awg_mutate_first_target_adapter(
        worktree, lambda data: data.__setitem__("ownedPaths", [])
    )


def break_target_adapter_empty_owned_path_entry(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        owned_paths = data.get("ownedPaths")
        if not isinstance(owned_paths, list) or not owned_paths:
            raise RuntimeError("ownedPaths must be a non-empty list before mutation")
        owned_paths[0] = ""

    awg_mutate_first_target_adapter(worktree, mutate)


def break_target_adapter_duplicate_owned_path(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        owned_paths = data.get("ownedPaths")
        if not isinstance(owned_paths, list) or not owned_paths:
            raise RuntimeError("ownedPaths must be a non-empty list before mutation")
        owned_paths.append(owned_paths[0])

    awg_mutate_first_target_adapter(worktree, mutate)


def break_target_adapter_parent_owned_path(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        owned_paths = data.get("ownedPaths")
        if not isinstance(owned_paths, list) or not owned_paths:
            raise RuntimeError("ownedPaths must be a non-empty list before mutation")
        owned_paths[0] = "../unsafe"

    awg_mutate_first_target_adapter(worktree, mutate)


def break_target_adapter_absolute_owned_path(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        owned_paths = data.get("ownedPaths")
        if not isinstance(owned_paths, list) or not owned_paths:
            raise RuntimeError("ownedPaths must be a non-empty list before mutation")
        owned_paths[0] = "/tmp/unsafe"

    awg_mutate_first_target_adapter(worktree, mutate)


def break_target_adapter_overlapping_owned_path(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        owned_paths = data.get("ownedPaths")
        if not isinstance(owned_paths, list) or not owned_paths:
            raise RuntimeError("ownedPaths must be a non-empty list before mutation")

        base = str(owned_paths[0]).rstrip("/")
        owned_paths.append(f"{base}/nested")

    awg_mutate_first_target_adapter(worktree, mutate)


def break_target_adapter_invalid_description_type(worktree: Path) -> None:
    awg_mutate_first_target_adapter(
        worktree, lambda data: data.__setitem__("description", {"not": "a-string"})
    )


def break_target_adapter_empty_version(worktree: Path) -> None:
    awg_mutate_first_target_adapter(
        worktree, lambda data: data.__setitem__("version", "")
    )


def break_agentic_config_duplicate_target_name(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("config targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("first config target must be an object before mutation")

    targets.append(dict(first_target))
    write_json(path, data)


def break_agentic_config_target_enabled_invalid_type(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic.json"
    data = load_json(path)

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise RuntimeError("config targets must be a non-empty list before mutation")

    first_target = targets[0]
    if not isinstance(first_target, dict):
        raise RuntimeError("first config target must be an object before mutation")

    first_target["enabled"] = "true"
    write_json(path, data)


def break_agentic_config_runtime_context_enabled(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic.json"
    data = load_json(path)

    runtime_context = data.get("runtimeContext")
    if not isinstance(runtime_context, dict):
        raise RuntimeError("config runtimeContext must be an object before mutation")

    runtime_context["enabled"] = True
    write_json(path, data)


def break_agentic_config_runtime_context_fail_if_missing(
    worktree: Path,
) -> None:
    path = worktree / ".agentic" / "agentic.json"
    data = load_json(path)

    runtime_context = data.get("runtimeContext")
    if not isinstance(runtime_context, dict):
        raise RuntimeError("config runtimeContext must be an object before mutation")

    runtime_context["failIfMissing"] = True
    write_json(path, data)


def break_init_from_bundle_unknown_bundle(worktree: Path) -> None:
    return


def awg_bundle_target_adapter_file(
    worktree: Path,
    target: str,
) -> Path:
    path = worktree / "registry" / "targets" / target / "adapter.json"

    if not path.is_file():
        raise RuntimeError(f"Expected target adapter file not found: {path}")

    return path


def break_bundle_registry_target_adapter_name_mismatch(
    worktree: Path,
) -> None:
    path = awg_bundle_target_adapter_file(
        worktree,
        "opencode",
    )
    data = load_json(path)
    data["name"] = "wrong-opencode"
    write_json(path, data)


def break_bundle_registry_target_permission_mapping_missing(
    worktree: Path,
) -> None:
    path = awg_bundle_target_adapter_file(
        worktree,
        "opencode",
    )
    data = load_json(path)
    mapping = data.get("permissionMapping")

    if not isinstance(mapping, dict):
        raise RuntimeError("target permissionMapping must be an object before mutation")

    mapping.pop("read-only", None)
    write_json(path, data)


def awg_default_setup_file(worktree: Path) -> Path:
    path = (
        worktree / "registry" / "setups" / "orchestrated-delivery-greenfield.setup.json"
    )

    if not path.is_file():
        raise RuntimeError(
            "expected default setup registry file: "
            "registry/setups/orchestrated-delivery-greenfield.setup.json"
        )

    return path


def awg_mutate_first_setup(
    worktree: Path, mutate: Callable[[dict[str, Any]], None]
) -> None:
    path = awg_default_setup_file(worktree)
    data = load_json(path)

    if not isinstance(data, dict):
        raise RuntimeError("setup registry file must be an object before mutation")

    mutate(data)
    write_json(path, data)


def break_setup_registry_name_mismatch(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["name"] = "wrong-setup"

    awg_mutate_first_setup(worktree, mutate)


def break_setup_registry_missing_default_bundle(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["defaultBundle"] = "missing-bundle"
        final_recommendation = data.get("finalRecommendation")
        if not isinstance(final_recommendation, dict):
            raise RuntimeError(
                "setup finalRecommendation must be an object before mutation"
            )
        final_recommendation["bundle"] = "missing-bundle"

    awg_mutate_first_setup(worktree, mutate)


def break_setup_registry_recommended_missing_option(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        questions = data.get("questions")
        if not isinstance(questions, list) or not questions:
            raise RuntimeError(
                "setup questions must be a non-empty list before mutation"
            )
        first_question = questions[0]
        if not isinstance(first_question, dict):
            raise RuntimeError("setup questions[0] must be an object before mutation")
        first_question["recommended"] = ["missing-option"]

    awg_mutate_first_setup(worktree, mutate)


def break_setup_registry_recommended_overlaps_blocked(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        questions = data.get("questions")
        if not isinstance(questions, list) or not questions:
            raise RuntimeError(
                "setup questions must be a non-empty list before mutation"
            )
        first_question = questions[0]
        if not isinstance(first_question, dict):
            raise RuntimeError("setup questions[0] must be an object before mutation")
        first_question["blocked"] = ["microservice-platform"]

    awg_mutate_first_setup(worktree, mutate)


def break_setup_registry_option_recommends_legacy_agents(
    worktree: Path,
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        questions = data.get("questions")

        if not isinstance(questions, list) or not questions:
            raise RuntimeError(
                "setup questions must be a non-empty list before mutation"
            )

        first_question = questions[0]

        if not isinstance(first_question, dict):
            raise RuntimeError("setup questions[0] must be an object before mutation")

        options = first_question.get("options")

        if not isinstance(options, list) or not options:
            raise RuntimeError(
                "setup question options must be a non-empty list before mutation"
            )

        first_option = options[0]

        if not isinstance(first_option, dict):
            raise RuntimeError(
                "setup question options[0] must be an object before mutation"
            )

        recommends = first_option.get("recommends")

        if not isinstance(recommends, dict):
            raise RuntimeError(
                "setup option recommends must be an object before mutation"
            )

        recommends["agents"] = ["Requirements"]

    awg_mutate_first_setup(worktree, mutate)


def awg_setup_profile_file(worktree: Path) -> Path:
    return worktree / ".agentic" / "setup-profile.json"


def awg_mutate_setup_profile(
    worktree: Path,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    init_result = run(
        worktree,
        [
            "scripts/agentic/agentic-gen.sh",
            "init",
            "--guided",
            "--setup",
            "orchestrated-delivery-greenfield",
        ],
    )

    if init_result.returncode != 0:
        raise RuntimeError(
            "failed to materialize orchestrated-delivery-greenfield "
            f"before setup-profile mutation:\n{init_result.stdout}"
        )

    path = awg_setup_profile_file(worktree)

    if not path.is_file():
        raise RuntimeError("expected .agentic/setup-profile.json to exist")

    data = load_json(path)

    if not isinstance(data, dict):
        raise RuntimeError("setup profile file must be an object before mutation")

    mutate(data)
    write_json(path, data)


def break_setup_profile_missing_schema_version(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data.pop("schemaVersion", None)

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_missing_setup_reference(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["setup"] = "missing-setup"

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_answer_missing_option(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        answers = data.get("answers")
        if not isinstance(answers, list) or not answers:
            raise RuntimeError(
                "setup profile answers must be a non-empty list before mutation"
            )
        first_answer = answers[0]
        if not isinstance(first_answer, dict):
            raise RuntimeError(
                "setup profile answers[0] must be an object before mutation"
            )
        first_answer["selected"] = "missing-option"

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_answer_blocked_option(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        answers = data.get("answers")
        if not isinstance(answers, list) or not answers:
            raise RuntimeError(
                "setup profile answers must be a non-empty list before mutation"
            )
        first_answer = answers[0]
        if not isinstance(first_answer, dict):
            raise RuntimeError(
                "setup profile answers[0] must be an object before mutation"
            )
        first_answer["selected"] = "documentation-only"

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_selected_legacy_skill(
    worktree: Path,
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        selected = data.get("selected")

        if not isinstance(selected, dict):
            raise RuntimeError(
                "setup profile selected must be an object before mutation"
            )

        selected["skills"] = ["workflow-routing"]

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_selected_targets_drift_from_answer_recommends(
    worktree: Path,
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        answers = data.get("answers")
        if not isinstance(answers, list):
            raise RuntimeError("setup profile answers must be a list before mutation")

        found = False
        for answer in answers:
            if (
                isinstance(answer, dict)
                and answer.get("question") == "target-platforms"
            ):
                answer["selected"] = "opencode-only"
                answer["classification"] = "compatible"
                answer["reason"] = (
                    "Compatible when the project only needs OpenCode generated output; "
                    "VS Code Copilot can be added later by selecting the combined target option."
                )
                found = True

        if not found:
            raise RuntimeError(
                "setup profile target-platforms answer must exist before mutation"
            )

        selected = data.get("selected")
        if not isinstance(selected, dict):
            raise RuntimeError(
                "setup profile selected must be an object before mutation"
            )

        selected["targets"] = ["opencode", "vscode-copilot"]

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_answer_classification_drift(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        setup_name = data.get("setup")
        if not isinstance(setup_name, str) or not setup_name.strip():
            raise RuntimeError(
                "setup profile setup must be a non-empty string before mutation"
            )

        setup = load_json(worktree / "registry" / "setups" / f"{setup_name}.setup.json")
        questions = setup.get("questions")
        if not isinstance(questions, list) or not questions:
            raise RuntimeError(
                "setup questions must be a non-empty list before mutation"
            )

        first_question = questions[0]
        if not isinstance(first_question, dict):
            raise RuntimeError("setup questions[0] must be an object before mutation")

        question_id = first_question.get("id")
        recommended = first_question.get("recommended")
        options = first_question.get("options")
        if not isinstance(question_id, str) or not question_id.strip():
            raise RuntimeError(
                "setup questions[0].id must be a non-empty string before mutation"
            )
        if (
            not isinstance(recommended, list)
            or not recommended
            or not isinstance(recommended[0], str)
        ):
            raise RuntimeError(
                "setup questions[0].recommended must contain a string before mutation"
            )
        if not isinstance(options, list) or not options:
            raise RuntimeError(
                "setup questions[0].options must be a non-empty list before mutation"
            )

        selected = recommended[0]
        selected_option = next(
            (
                option
                for option in options
                if isinstance(option, dict) and option.get("value") == selected
            ),
            None,
        )
        if not isinstance(selected_option, dict):
            raise RuntimeError("setup recommended option must exist before mutation")

        reason = selected_option.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeError(
                "setup recommended option reason must be a non-empty string before mutation"
            )

        answers = data.get("answers")
        if not isinstance(answers, list) or not answers:
            raise RuntimeError(
                "setup profile answers must be a non-empty list before mutation"
            )
        first_answer = answers[0]
        if not isinstance(first_answer, dict):
            raise RuntimeError(
                "setup profile answers[0] must be an object before mutation"
            )

        first_answer["question"] = question_id
        first_answer["selected"] = selected
        first_answer["classification"] = "compatible"
        first_answer["reason"] = reason

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_answer_reason_drift(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        answers = data.get("answers")
        if not isinstance(answers, list) or not answers:
            raise RuntimeError(
                "setup profile answers must be a non-empty list before mutation"
            )
        first_answer = answers[0]
        if not isinstance(first_answer, dict):
            raise RuntimeError(
                "setup profile answers[0] must be an object before mutation"
            )
        first_answer["reason"] = "Wrong reason."

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_fallback_allowed(worktree: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        policy = data.get("policy")
        if not isinstance(policy, dict):
            raise RuntimeError("setup profile policy must be an object before mutation")
        policy["fallbackAllowed"] = True

    awg_mutate_setup_profile(worktree, mutate)


def break_skill_registry_missing_name(worktree: Path) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data.pop("name", None)
    write_json(path, data)


def break_skill_registry_missing_provides(worktree: Path) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data.pop("provides", None)
    write_json(path, data)


def break_skill_registry_invalid_provides_type(worktree: Path) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data["provides"] = "not-a-list"
    write_json(path, data)


def break_skill_registry_empty_provides(worktree: Path) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data["provides"] = []
    write_json(path, data)


def break_skill_registry_empty_provides_entry(worktree: Path) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)

    provides = data.get("provides")
    if not isinstance(provides, list) or not provides:
        raise RuntimeError("skill provides must be a non-empty list before mutation")

    provides[0] = ""
    write_json(path, data)


def break_skill_registry_duplicate_provides_entry(worktree: Path) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)

    provides = data.get("provides")
    if not isinstance(provides, list) or not provides:
        raise RuntimeError("skill provides must be a non-empty list before mutation")

    provides.append(provides[0])
    write_json(path, data)


def break_skill_registry_duplicate_global_capability(worktree: Path) -> None:
    first_path, second_path = first_two_skill_json_files(worktree)

    first = load_json(first_path)
    second = load_json(second_path)

    first_provides = first.get("provides")
    if not isinstance(first_provides, list) or not first_provides:
        raise RuntimeError(
            "first skill provides must be a non-empty list before mutation"
        )

    second_provides = second.get("provides")
    if not isinstance(second_provides, list):
        second_provides = []
        second["provides"] = second_provides

    second_provides.append(first_provides[0])
    write_json(second_path, second)


def break_skill_registry_invalid_description_type(worktree: Path) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data["description"] = {"not": "a-string"}
    write_json(path, data)


def break_skill_registry_empty_version(worktree: Path) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data["version"] = ""
    write_json(path, data)


def break_skill_registry_recommended_agents_invalid_type(
    worktree: Path,
) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data["recommendedAgents"] = "not-a-list"
    write_json(path, data)


def break_skill_registry_recommended_agent_missing_reference(
    worktree: Path,
) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data["recommendedAgents"] = ["DoesNotExist"]
    write_json(path, data)


def break_skill_registry_duplicate_recommended_agent(
    worktree: Path,
) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    agents = data.get("recommendedAgents")

    if not isinstance(agents, list) or not agents:
        raise RuntimeError("recommendedAgents must be a non-empty list before mutation")

    agents.append(agents[0])
    write_json(path, data)


def break_skill_registry_requires_capabilities_invalid_type(
    worktree: Path,
) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data["requiresCapabilities"] = "not-a-list"
    write_json(path, data)


def break_skill_registry_required_capability_missing_reference(
    worktree: Path,
) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    data["requiresCapabilities"] = ["capability.does.not.exist"]
    write_json(path, data)


def break_skill_registry_duplicate_required_capability(
    worktree: Path,
) -> None:
    first_path, second_path = first_two_skill_json_files(worktree)
    first = load_json(first_path)
    second = load_json(second_path)
    second_provides = second.get("provides")

    if not isinstance(second_provides, list) or not second_provides:
        raise RuntimeError(
            "second skill provides must be a non-empty list before mutation"
        )

    capability = second_provides[0]
    first["requiresCapabilities"] = [capability, capability]
    write_json(first_path, first)


def break_skill_registry_requires_own_capability(
    worktree: Path,
) -> None:
    path = first_skill_json_file(worktree)
    data = load_json(path)
    provides = data.get("provides")

    if not isinstance(provides, list) or not provides:
        raise RuntimeError("skill provides must be a non-empty list before mutation")

    data["requiresCapabilities"] = [provides[0]]
    write_json(path, data)


def break_agent_registry_unknown_recommended_capability(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)

    capabilities = data.get("recommendedCapabilities")
    if not isinstance(capabilities, list):
        raise RuntimeError("recommendedCapabilities must be a list before mutation")

    capabilities.append("does.not.exist")
    write_json(path, data)


def break_agent_registry_duplicate_recommended_capability(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)

    capabilities = data.get("recommendedCapabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise RuntimeError("recommendedCapabilities must be non-empty before mutation")

    capabilities.append(capabilities[0])
    write_json(path, data)


def break_agent_registry_empty_recommended_responsibilities(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)
    data["recommendedResponsibilities"] = []
    write_json(path, data)


def break_agent_registry_empty_default_guardrails(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)
    data["defaultGuardrails"] = []
    write_json(path, data)


def break_agent_registry_empty_version(worktree: Path) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)
    data["version"] = ""
    write_json(path, data)


def permission_profile_path(
    worktree: Path,
    name: str = "read-only",
) -> Path:
    path = (
        worktree / "registry" / "permission-profiles" / name / "permission-profile.json"
    )

    if not path.is_file():
        raise RuntimeError(f"expected permission profile before mutation: {path}")

    return path


def break_permission_profile_name_folder_mismatch(
    worktree: Path,
) -> None:
    path = permission_profile_path(worktree)
    data = load_json(path)
    data["name"] = "wrong-name"
    write_json(path, data)


def break_permission_profile_write_without_read(
    worktree: Path,
) -> None:
    path = permission_profile_path(worktree)
    data = load_json(path)
    data["read"] = False
    data["write"] = True
    write_json(path, data)


def break_permission_profile_edit_without_write(
    worktree: Path,
) -> None:
    path = permission_profile_path(worktree)
    data = load_json(path)
    data["edit"] = True
    write_json(path, data)


def break_permission_profile_bash_without_read(
    worktree: Path,
) -> None:
    path = permission_profile_path(worktree)
    data = load_json(path)
    data["read"] = False
    data["bash"] = "limited"
    write_json(path, data)


def break_agent_registry_missing_default_permission_profile(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)
    data.pop("defaultPermissionProfile", None)
    write_json(path, data)


def break_agent_registry_unknown_default_permission_profile(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)
    data["defaultPermissionProfile"] = "does-not-exist"
    write_json(path, data)


def break_agent_registry_legacy_field(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)
    data["produces"] = ["LegacyArtifact"]
    write_json(path, data)


def break_lockfile_missing_input_file_entry(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic-lock.json"
    data = load_json(path)

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("lockfile inputs must be an object for this test")

    files = inputs.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError(
            "lockfile inputs.files must be a non-empty list for this test"
        )

    files.pop()
    inputs["fileCount"] = len(files)
    write_json(path, data)


def break_lockfile_input_hash_drift(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic-lock.json"
    data = load_json(path)

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("lockfile inputs must be an object for this test")

    files = inputs.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError(
            "lockfile inputs.files must be a non-empty list for this test"
        )

    first = files[0]
    if not isinstance(first, dict):
        raise RuntimeError("lockfile inputs.files[0] must be an object for this test")

    first["sha256"] = "sha256:" + "0" * 64
    write_json(path, data)


def break_lockfile_input_size_drift(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic-lock.json"
    data = load_json(path)

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("lockfile inputs must be an object for this test")

    files = inputs.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError(
            "lockfile inputs.files must be a non-empty list for this test"
        )

    first = files[0]
    if not isinstance(first, dict):
        raise RuntimeError("lockfile inputs.files[0] must be an object for this test")

    size_bytes = first.get("sizeBytes")
    if not isinstance(size_bytes, int):
        raise RuntimeError(
            "lockfile inputs.files[0].sizeBytes must be an integer for this test"
        )

    first["sizeBytes"] = size_bytes + 1
    write_json(path, data)


def break_lockfile_file_count_drift(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic-lock.json"
    data = load_json(path)

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("lockfile inputs must be an object for this test")

    file_count = inputs.get("fileCount")
    if not isinstance(file_count, int):
        raise RuntimeError("lockfile inputs.fileCount must be an integer for this test")

    inputs["fileCount"] = file_count + 1
    write_json(path, data)


def break_lockfile_content_hash_drift(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic-lock.json"
    data = load_json(path)

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("lockfile inputs must be an object for this test")

    inputs["contentHash"] = "sha256:" + "0" * 64
    write_json(path, data)


def break_lockfile_untracked_registry_input(worktree: Path) -> None:
    path = worktree / "registry" / "skills" / "SyntheticLockfileSkill" / "skill.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "name": "SyntheticLockfileSkill",
                "description": "Synthetic skill used to prove lockfile input coverage.",
                "version": "0.0.0",
                "provides": ["synthetic.lockfile.coverage"],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def break_lockfile(worktree: Path) -> None:
    path = worktree / ".agentic" / "agentic-lock.json"
    data = load_json(path)

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("lockfile inputs must be an object for this test")

    inputs["files"] = []
    write_json(path, data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run isolated negative gate tests.")
    parser.add_argument(
        "--name-contains",
        help=("Run only tests whose names contain this case-insensitive text."),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

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
            "environment validation fails when node cannot run",
            [
                "env",
                "PATH=.tmp-negative-node-bin:/usr/bin:/bin",
                "scripts/agentic/agentic-gen.sh",
                "validate-environment",
            ],
            break_environment_validation_node_command,
            "node is required but failed to run",
        ),
        (
            "failure",
            "generation idempotency validation fails when second generation changes output",
            ["scripts/agentic/agentic-gen.sh", "validate-idempotency"],
            break_generation_idempotency_by_changing_generator,
            "Generation is not idempotent",
        ),
        (
            "failure",
            "init idempotency validation fails when second init changes config",
            [
                "scripts/agentic/agentic-gen.sh",
                "validate-init-idempotency",
                "--bundle",
                "orchestrated-delivery",
            ],
            break_init_idempotency_by_changing_init_script,
            "Init from bundle is not idempotent",
        ),
        (
            "failure",
            "init idempotency validation fails when guided setup argument is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-init-idempotency", "--guided"],
            no_mutation,
            "error: --guided requires --setup",
        ),
        (
            "failure",
            "init idempotency validation fails when setup is used without guided",
            [
                "scripts/agentic/agentic-gen.sh",
                "validate-init-idempotency",
                "--setup",
                "orchestrated-delivery-greenfield",
            ],
            no_mutation,
            "error: --setup requires --guided",
        ),
        (
            "failure",
            "init idempotency validation fails when guided and bundle are combined",
            [
                "scripts/agentic/agentic-gen.sh",
                "validate-init-idempotency",
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--bundle",
                "orchestrated-delivery",
            ],
            no_mutation,
            "error: --guided cannot be combined with --bundle",
        ),
        (
            "failure",
            "init idempotency validation fails when no mode is selected",
            ["scripts/agentic/agentic-gen.sh", "validate-init-idempotency"],
            no_mutation,
            "error: one of --bundle or --guided --setup is required",
        ),
        (
            "success",
            "lean guided init is idempotent",
            [
                "scripts/agentic/agentic-gen.sh",
                "validate-init-idempotency",
                "--guided",
                "--setup",
                "lean-delivery-greenfield",
            ],
            no_mutation,
            "PASS: Guided init is idempotent for setup "
            "'lean-delivery-greenfield'. Checked "
            ".agentic/setup-profile.json and .agentic/agentic.json.",
        ),
        (
            "success",
            "review-heavy guided init is idempotent",
            [
                "scripts/agentic/agentic-gen.sh",
                "validate-init-idempotency",
                "--guided",
                "--setup",
                "review-heavy-delivery-greenfield",
            ],
            no_mutation,
            "PASS: Guided init is idempotent for setup "
            "'review-heavy-delivery-greenfield'. Checked "
            ".agentic/setup-profile.json and .agentic/agentic.json.",
        ),
        (
            "success",
            "direct orchestrated bundle initialization remains available",
            [
                "scripts/agentic/agentic-gen.sh",
                "validate-init-idempotency",
                "--bundle",
                "orchestrated-delivery",
            ],
            no_mutation,
            "PASS: Init from bundle is idempotent for bundle "
            "'orchestrated-delivery'. Checked .agentic/agentic.json.",
        ),
        (
            "success",
            "AI guided init selects the complete AI composition",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--setup",
                "ai-application-greenfield",
            ],
            no_mutation,
            "PASS: Initialized .agentic/setup-profile.json from guided setup "
            "'ai-application-greenfield'.",
            assert_ai_application_composition,
        ),
        (
            "success",
            "guided init selects default target recommendations",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
            ],
            no_mutation,
            "PASS: Initialized .agentic/setup-profile.json from guided setup 'orchestrated-delivery-greenfield'.",
            assert_guided_default_targets,
        ),
        (
            "success",
            "guided init selects opencode only target recommendation",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--answer",
                "target-platforms=opencode-only",
            ],
            no_mutation,
            "PASS: Initialized .agentic/setup-profile.json from guided setup 'orchestrated-delivery-greenfield'.",
            assert_guided_opencode_only_targets,
        ),
        (
            "success",
            "guided init selects vscode copilot only target recommendation",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--answer",
                "target-platforms=vscode-copilot-only",
            ],
            no_mutation,
            "PASS: Initialized .agentic/setup-profile.json from guided setup 'orchestrated-delivery-greenfield'.",
            assert_guided_vscode_copilot_only_targets,
        ),
        (
            "failure",
            "generated output validation fails when generated agent file is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_generated_output,
            "missing generated file",
        ),
        (
            "failure",
            "generated output validation fails when selected skill file is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_generated_selected_skill_output,
            "missing generated file: .github/skills/code-review-clean-code/SKILL.md",
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
            "output manifest validation fails when bundle metadata drifts from registry",
            ["scripts/agentic/agentic-gen.sh", "validate-manifest"],
            break_output_manifest_bundle_workflow_drift,
            "bundle metadata drift for workflow",
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
            "registry schema validation enforces semantic version pattern",
            ["scripts/agentic/agentic-gen.sh", "validate-registry-schemas"],
            break_registry_schema_agent_version_pattern,
            "does not match",
        ),
        (
            "failure",
            "registry schema validation enforces workflow states minItems",
            ["scripts/agentic/agentic-gen.sh", "validate-registry-schemas"],
            break_registry_schema_workflow_states_min_items,
            "should be non-empty",
        ),
        (
            "failure",
            "registry schema validation enforces workflow state oneOf and const",
            ["scripts/agentic/agentic-gen.sh", "validate-registry-schemas"],
            break_registry_schema_workflow_terminal_const,
            "is not valid under any of the given schemas",
        ),
        (
            "failure",
            "registry schema validation enforces permission bash enum",
            ["scripts/agentic/agentic-gen.sh", "validate-registry-schemas"],
            break_registry_schema_permission_bash_enum,
            "is not one of",
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
            "resolution validation fails when target adapterPath is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_empty_adapter_path,
            "targets[0].adapterPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when target adapterPath has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_invalid_adapter_path_type,
            "targets[0].adapterPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when target adapterPath is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_missing_adapter_path,
            "targets[0].adapterPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when target enabled has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_invalid_enabled_type,
            "targets[0].enabled must be a boolean",
        ),
        (
            "failure",
            "resolution validation fails when target enabled is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_missing_enabled,
            "targets[0].enabled must be a boolean",
        ),
        (
            "failure",
            "resolution validation fails when target missing flag is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_missing_missing_flag,
            "targets[0].missing must be a boolean",
        ),
        (
            "failure",
            "resolution validation fails when target missing has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_invalid_missing_type,
            "targets[0].missing must be a boolean",
        ),
        (
            "failure",
            "resolution validation fails when target name has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_invalid_name_type,
            "targets[0].name must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when target name is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_empty_name,
            "targets[0].name must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when target name is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_missing_name,
            "targets[0].name must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when target entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_entry_type,
            "targets[0] must be an object",
        ),
        (
            "failure",
            "resolution validation fails when targets has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_invalid_targets_type,
            "expected non-empty 'targets' collection",
        ),
        (
            "failure",
            "resolution validation fails when targets is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_empty_targets,
            "expected non-empty 'targets' collection",
        ),
        (
            "failure",
            "resolution validation fails when targets is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_missing_targets,
            "expected non-empty 'targets' collection",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability skillPath has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_invalid_skill_path_type,
            "resolvedCapabilities[0].skillPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability skillPath is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_empty_skill_path,
            "resolvedCapabilities[0].skillPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability skillPath is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_missing_skill_path,
            "resolvedCapabilities[0].skillPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability skill has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_invalid_skill_type,
            "resolvedCapabilities[0].skill must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability skill is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_empty_skill,
            "resolvedCapabilities[0].skill must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability skill is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_missing_skill,
            "resolvedCapabilities[0].skill must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability capability has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_invalid_capability_type,
            "resolvedCapabilities[0].capability must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability capability is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_empty_capability,
            "resolvedCapabilities[0].capability must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when resolvedCapability capability is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_resolved_capability_missing_capability,
            "resolvedCapabilities[0].capability must be a non-empty string",
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
            "resolution validation fails when summary is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_missing_summary,
            "summary must be an object",
        ),
        (
            "failure",
            "resolution validation fails when summary has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_invalid_summary_type,
            "summary must be an object",
        ),
        (
            "failure",
            "resolution validation fails when summary agentCount is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_missing_agent_count,
            "summary.agentCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary agentCount has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_invalid_agent_count_type,
            "summary.agentCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary agentCount is wrong",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_wrong_agent_count,
            "summary.agentCount must match agents length",
        ),
        (
            "failure",
            "resolution validation fails when summary targetCount is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_missing_target_count,
            "summary.targetCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary targetCount has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_invalid_target_count_type,
            "summary.targetCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary targetCount is wrong",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_wrong_target_count,
            "summary.targetCount must match targets length",
        ),
        (
            "failure",
            "resolution validation fails when summary availableSkillCount is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_missing_available_skill_count,
            "summary.availableSkillCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary availableSkillCount has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_invalid_available_skill_count_type,
            "summary.availableSkillCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary producedArtifactBindingCount is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_missing_produced_artifact_binding_count,
            "summary.producedArtifactBindingCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary producedArtifactBindingCount has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_invalid_produced_artifact_binding_count_type,
            "summary.producedArtifactBindingCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary errorCount is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_missing_error_count,
            "summary.errorCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary errorCount has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_invalid_error_count_type,
            "summary.errorCount must be an integer",
        ),
        (
            "failure",
            "resolution validation fails when summary errorCount is non-zero",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_nonzero_error_count,
            "summary.errorCount must be 0",
        ),
        (
            "failure",
            "resolution validation fails when summary errors is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_missing_errors,
            "summary.errors must be an empty list",
        ),
        (
            "failure",
            "resolution validation fails when summary errors has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_invalid_errors_type,
            "summary.errors must be an empty list",
        ),
        (
            "failure",
            "resolution validation fails when summary errors is non-empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_nonempty_errors,
            "summary.errors must be empty",
        ),
        (
            "failure",
            "resolution validation fails when workflow is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_missing_workflow,
            "workflow must be an object",
        ),
        (
            "failure",
            "resolution validation fails when workflow has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_invalid_workflow_type,
            "workflow must be an object",
        ),
        (
            "failure",
            "resolution validation fails when workflow failClosed is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_missing_fail_closed,
            "workflow.failClosed must be a boolean",
        ),
        (
            "failure",
            "resolution validation fails when workflow failClosed has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_invalid_fail_closed_type,
            "workflow.failClosed must be a boolean",
        ),
        (
            "failure",
            "resolution validation fails when workflow profile is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_missing_profile,
            "workflow.profile must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when workflow profile is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_empty_profile,
            "workflow.profile must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when workflow profile has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_invalid_profile_type,
            "workflow.profile must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when workflow startState is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_missing_start_state,
            "workflow.startState must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when workflow startState is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_empty_start_state,
            "workflow.startState must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when workflow startState has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_invalid_start_state_type,
            "workflow.startState must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when workflow terminalStates is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_missing_terminal_states,
            "workflow.terminalStates must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when workflow terminalStates has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_invalid_terminal_states_type,
            "workflow.terminalStates must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when workflow terminalStates is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_empty_terminal_states,
            "workflow.terminalStates must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when workflow terminalState entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_invalid_terminal_state_entry_type,
            "workflow.terminalStates[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when workflow terminalState entry is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_empty_terminal_state_entry,
            "workflow.terminalStates[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when workflow terminalState is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_duplicate_terminal_state,
            "workflow.terminalStates",
        ),
        (
            "failure",
            "resolution validation fails when project is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_missing_project,
            "project must be an object",
        ),
        (
            "failure",
            "resolution validation fails when project has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_invalid_project_type,
            "project must be an object",
        ),
        (
            "failure",
            "resolution validation fails when project name is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_missing_name,
            "project.name must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project name is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_empty_name,
            "project.name must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project name has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_invalid_name_type,
            "project.name must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project type is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_missing_type,
            "project.type must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project type is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_empty_type,
            "project.type must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project type has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_invalid_type_type,
            "project.type must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project description is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_missing_description,
            "project.description must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project description is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_empty_description,
            "project.description must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project description has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_invalid_description_type,
            "project.description must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project architectureProfile is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_missing_architecture_profile,
            "project.architectureProfile must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project architectureProfile is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_empty_architecture_profile,
            "project.architectureProfile must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project architectureProfile has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_invalid_architecture_profile_type,
            "project.architectureProfile must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project languageProfiles is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_missing_language_profiles,
            "project.languageProfiles must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when project languageProfiles has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_invalid_language_profiles_type,
            "project.languageProfiles must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when project languageProfiles is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_empty_language_profiles,
            "project.languageProfiles must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when project languageProfiles entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_invalid_language_profile_entry_type,
            "project.languageProfiles[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project languageProfiles entry is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_empty_language_profile_entry,
            "project.languageProfiles[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project languageProfiles has duplicate entry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_duplicate_language_profile,
            "project.languageProfiles",
        ),
        (
            "failure",
            "resolution validation fails when project runtimeProfiles is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_missing_runtime_profiles,
            "project.runtimeProfiles must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when project runtimeProfiles has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_invalid_runtime_profiles_type,
            "project.runtimeProfiles must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when project runtimeProfiles is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_empty_runtime_profiles,
            "project.runtimeProfiles must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when project runtimeProfiles entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_invalid_runtime_profile_entry_type,
            "project.runtimeProfiles[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project runtimeProfiles entry is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_empty_runtime_profile_entry,
            "project.runtimeProfiles[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when project runtimeProfiles has duplicate entry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_duplicate_runtime_profile,
            "project.runtimeProfiles",
        ),
        (
            "failure",
            "resolution validation fails when agent produces is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_missing_produces,
            "agents[0].produces must be a list",
        ),
        (
            "failure",
            "resolution validation fails when agent produces has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_invalid_produces_type,
            "agents[0].produces must be a list",
        ),
        (
            "failure",
            "resolution validation fails when agent produces entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_produces_entry_invalid_type,
            "produces[0] must be an object",
        ),
        (
            "failure",
            "resolution validation fails when produce type is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_missing_type,
            "produces[0].type must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce type is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_empty_type,
            "produces[0].type must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce type has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_invalid_type_type,
            "produces[0].type must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce contractPath is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_missing_contract_path,
            "produces[0].contractPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce contractPath is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_empty_contract_path,
            "produces[0].contractPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce contractPath has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_invalid_contract_path_type,
            "produces[0].contractPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce pathPattern is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_missing_path_pattern,
            "produces[0].pathPattern must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce pathPattern is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_empty_path_pattern,
            "produces[0].pathPattern must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce pathPattern has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_invalid_path_pattern_type,
            "produces[0].pathPattern must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce allowedStatuses is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_missing_allowed_statuses,
            "produces[0].allowedStatuses must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when produce allowedStatuses has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_invalid_allowed_statuses_type,
            "produces[0].allowedStatuses must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when produce allowedStatuses is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_empty_allowed_statuses,
            "produces[0].allowedStatuses must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when produce allowedStatuses entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_invalid_allowed_status_entry_type,
            "allowedStatuses[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce allowedStatuses entry is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_empty_allowed_status_entry,
            "allowedStatuses[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce allowedStatuses has duplicate entry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_duplicate_allowed_status,
            "allowedStatuses",
        ),
        (
            "failure",
            "resolution validation fails when produce requiredHeadings is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_missing_required_headings,
            "produces[0].requiredHeadings must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when produce requiredHeadings has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_invalid_required_headings_type,
            "produces[0].requiredHeadings must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when produce requiredHeadings is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_empty_required_headings,
            "produces[0].requiredHeadings must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when produce requiredHeadings entry has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_invalid_required_heading_entry_type,
            "requiredHeadings[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce requiredHeadings entry is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_empty_required_heading_entry,
            "requiredHeadings[0] must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when produce requiredHeadings has duplicate entry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_duplicate_required_heading,
            "requiredHeadings",
        ),
        (
            "failure",
            "resolution validation fails when produced artifact binding count is wrong",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_summary_wrong_produced_artifact_binding_count,
            "summary.producedArtifactBindingCount must match total agents produces length",
        ),
        (
            "failure",
            "resolution validation fails when agent role is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_missing_role,
            "agents[0].role must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when agent role is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_empty_role,
            "agents[0].role must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when agent role has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_invalid_role_type,
            "agents[0].role must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when agent registryPath is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_missing_registry_path,
            "agents[0].registryPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when agent registryPath is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_empty_registry_path,
            "agents[0].registryPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when agent registryPath has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_invalid_registry_path_type,
            "agents[0].registryPath must be a non-empty string",
        ),
        (
            "failure",
            "resolution validation fails when agent name is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_duplicate_agent_name,
            "agents[1].name is duplicated",
        ),
        (
            "failure",
            "resolution validation fails when agent registryPath contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_registry_path_parent_reference,
            "agents[0].registryPath must be a safe relative path",
        ),
        (
            "failure",
            "resolution validation fails when agent registryPath is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_registry_path_absolute,
            "agents[0].registryPath must be a safe relative path",
        ),
        (
            "failure",
            "resolution validation fails when produce contractPath contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_contract_path_parent_reference,
            "contractPath must be a safe relative path",
        ),
        (
            "failure",
            "resolution validation fails when produce contractPath is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_contract_path_absolute,
            "contractPath must be a safe relative path",
        ),
        (
            "failure",
            "resolution validation fails when produce pathPattern contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_path_pattern_parent_reference,
            "pathPattern must be a safe relative path",
        ),
        (
            "failure",
            "resolution validation fails when produce pathPattern is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_path_pattern_absolute,
            "pathPattern must be a safe relative path",
        ),
        (
            "failure",
            "resolution validation fails when target adapterPath contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_adapter_path_parent_reference,
            "targets[0].adapterPath must be a safe relative path",
        ),
        (
            "failure",
            "resolution validation fails when target adapterPath is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_adapter_path_absolute,
            "targets[0].adapterPath must be a safe relative path",
        ),
        (
            "failure",
            "resolution validation fails when missing target is enabled",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_semantic_missing_target_enabled_true,
            "must have enabled=false when missing=true",
        ),
        (
            "failure",
            "resolution validation fails when missing target has adapterPath",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_semantic_missing_target_adapter_path_non_null,
            "adapterPath must be null when missing=true",
        ),
        (
            "failure",
            "resolution validation fails when present target is disabled",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_semantic_present_target_enabled_false,
            "must have enabled=true when missing=false",
        ),
        (
            "failure",
            "resolution validation fails when present target adapterPath is null",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_semantic_present_target_adapter_path_null,
            "adapterPath must be a non-empty string when missing=false",
        ),
        (
            "failure",
            "resolution validation fails when resolution target name is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_semantic_duplicate_target_name,
            "targets[1].name is duplicated",
        ),
        (
            "failure",
            "resolution validation fails when agent registryPath points to missing file",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_agent_registry_path_missing_file,
            "agents[0].registryPath must point to an existing file",
        ),
        (
            "failure",
            "resolution validation fails when produce contractPath points to missing file",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_produce_contract_path_missing_file,
            "contractPath must point to an existing file",
        ),
        (
            "failure",
            "resolution validation fails when target adapterPath points to missing file",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_adapter_path_missing_file,
            "targets[0].adapterPath must point to an existing file",
        ),
        (
            "failure",
            "resolution validation fails when workflow transitions are missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_missing_transitions,
            "workflow.transitions must be a non-empty list",
        ),
        (
            "failure",
            "resolution validation fails when workflow transition target differs from registry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_transition_target_mismatch,
            "workflow.transitions must match workflow registry transitions",
        ),
        (
            "failure",
            "resolution validation fails when workflow transition event differs from registry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_transition_event_mismatch,
            "workflow.transitions must match workflow registry transitions",
        ),
        (
            "failure",
            "resolution validation fails when workflow transition count differs from registry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_transition_count_mismatch,
            "workflow.transitions must match workflow registry transitions",
        ),
        (
            "failure",
            "resolution validation fails when workflow profile registry file is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_profile_missing_registry_file,
            "workflow.profile must reference an existing workflow registry file",
        ),
        (
            "failure",
            "resolution validation fails when workflow profile is unsafe registry name",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_profile_unsafe_registry_name,
            "workflow.profile must be a safe registry name",
        ),
        (
            "failure",
            "resolution validation fails when workflow startState is unknown registry state",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_start_state_unknown_registry_state,
            "workflow.startState must exist in workflow registry states",
        ),
        (
            "failure",
            "resolution validation fails when workflow startState is terminal registry state",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_start_state_terminal_registry_state,
            "workflow.startState must reference a non-terminal registry state",
        ),
        (
            "failure",
            "resolution validation fails when workflow terminalState is unknown registry state",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_terminal_state_unknown_registry_state,
            "workflow.terminalStates[0] must exist in workflow registry states",
        ),
        (
            "failure",
            "resolution validation fails when workflow terminalState is non-terminal registry state",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_terminal_state_non_terminal_registry_state,
            "workflow.terminalStates[0] must reference a terminal registry state",
        ),
        (
            "failure",
            "resolution validation fails when workflow failClosed differs from registry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_fail_closed_registry_mismatch,
            "workflow.failClosed must match workflow registry failClosed",
        ),
        (
            "failure",
            "resolution validation fails when project differs from config",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_project_config_mismatch,
            "project must match .agentic/agentic.json: project",
        ),
        (
            "failure",
            "resolution validation fails when workflow startState differs from registry",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_workflow_config_mismatch,
            "workflow.startState must match workflow registry startState",
        ),
        (
            "failure",
            "resolution validation fails when target name differs from config",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_config_name_mismatch,
            "target name/enabled projection must match .agentic/agentic.json: targets",
        ),
        (
            "failure",
            "resolution validation fails when target enabled differs from config",
            ["scripts/agentic/agentic-gen.sh", "validate-resolution"],
            break_resolution_target_config_enabled_mismatch,
            "target name/enabled projection must match .agentic/agentic.json: targets",
        ),
        (
            "failure",
            "permission profile registry validation fails when name differs from folder",
            ["scripts/agentic/agentic-gen.sh", "validate-permission-profiles"],
            break_permission_profile_name_folder_mismatch,
            "name 'wrong-name' does not match folder 'read-only'",
        ),
        (
            "failure",
            "permission profile registry validation fails when write lacks read",
            ["scripts/agentic/agentic-gen.sh", "validate-permission-profiles"],
            break_permission_profile_write_without_read,
            "write=true requires read=true",
        ),
        (
            "failure",
            "permission profile registry validation fails when edit lacks write",
            ["scripts/agentic/agentic-gen.sh", "validate-permission-profiles"],
            break_permission_profile_edit_without_write,
            "edit=true requires write=true",
        ),
        (
            "failure",
            "permission profile registry validation fails when bash lacks read",
            ["scripts/agentic/agentic-gen.sh", "validate-permission-profiles"],
            break_permission_profile_bash_without_read,
            "bash=limited requires read=true",
        ),
        (
            "failure",
            "agent registry validation fails when recommended capability is unavailable",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_unknown_recommended_capability,
            "recommendedCapabilities entry 'does.not.exist' must be provided by a registered skill",
        ),
        (
            "failure",
            "agent registry validation fails when recommended capability is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_duplicate_recommended_capability,
            "recommendedCapabilities entry",
        ),
        (
            "failure",
            "agent registry validation fails when recommended responsibilities are empty",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_empty_recommended_responsibilities,
            "recommendedResponsibilities must be a non-empty list",
        ),
        (
            "failure",
            "agent registry validation fails when default guardrails are empty",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_empty_default_guardrails,
            "defaultGuardrails must be a non-empty list",
        ),
        (
            "failure",
            "agent registry validation fails when version is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_empty_version,
            "version must be a non-empty string",
        ),
        (
            "failure",
            "agent registry validation fails when defaultPermissionProfile is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_missing_default_permission_profile,
            "defaultPermissionProfile must be a non-empty string",
        ),
        (
            "failure",
            "agent registry validation fails when defaultPermissionProfile is unknown",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_unknown_default_permission_profile,
            "must reference an existing permission profile",
        ),
        (
            "failure",
            "agent registry validation rejects legacy agent fields",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_legacy_field,
            "legacy agent field 'produces' is not allowed",
        ),
        (
            "failure",
            "skill registry validation fails when name is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_missing_name,
            "name must be a non-empty string",
        ),
        (
            "failure",
            "skill registry validation fails when provides is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_missing_provides,
            "provides must be a non-empty list",
        ),
        (
            "failure",
            "skill registry validation fails when provides has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_invalid_provides_type,
            "provides must be a non-empty list",
        ),
        (
            "failure",
            "skill registry validation fails when provides is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_empty_provides,
            "provides must be a non-empty list",
        ),
        (
            "failure",
            "skill registry validation fails when provides entry is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_empty_provides_entry,
            "provides[0] must be a non-empty string",
        ),
        (
            "failure",
            "skill registry validation fails when provides entry is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_duplicate_provides_entry,
            "provides[",
        ),
        (
            "failure",
            "skill registry validation fails when capability is provided by multiple skills",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_duplicate_global_capability,
            "is already provided by",
        ),
        (
            "failure",
            "skill registry validation fails when description has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_invalid_description_type,
            "description must be a string when present",
        ),
        (
            "failure",
            "skill registry validation fails when version is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_empty_version,
            "version must be a non-empty string when present",
        ),
        (
            "failure",
            "skill registry validation fails when recommendedAgents has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_recommended_agents_invalid_type,
            "recommendedAgents must be a list when present",
        ),
        (
            "failure",
            "skill registry validation fails when recommended agent is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_recommended_agent_missing_reference,
            "recommendedAgents entry 'DoesNotExist' must reference an existing agent",
        ),
        (
            "failure",
            "skill registry validation fails when recommended agent is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_duplicate_recommended_agent,
            "recommendedAgents[1] is duplicated",
        ),
        (
            "failure",
            "skill registry validation fails when requiresCapabilities has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_requires_capabilities_invalid_type,
            "requiresCapabilities must be a list when present",
        ),
        (
            "failure",
            "skill registry validation fails when required capability is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_required_capability_missing_reference,
            "requiresCapabilities entry 'capability.does.not.exist' must reference an existing capability",
        ),
        (
            "failure",
            "skill registry validation fails when required capability is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_duplicate_required_capability,
            "requiresCapabilities[1] is duplicated",
        ),
        (
            "failure",
            "skill registry validation fails when skill requires its own capability",
            ["scripts/agentic/agentic-gen.sh", "validate-skills"],
            break_skill_registry_requires_own_capability,
            "is provided by the same skill",
        ),
        (
            "failure",
            "init from bundle fails when bundle is unknown",
            ["scripts/agentic/agentic-gen.sh", "init", "--bundle", "missing-bundle"],
            break_init_from_bundle_unknown_bundle,
            "Unknown bundle 'missing-bundle'",
        ),
        (
            "failure",
            "guided init fails when setup is unknown",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--setup",
                "missing-setup",
            ],
            break_init_from_bundle_unknown_bundle,
            "Unknown setup 'missing-setup'",
        ),
        (
            "failure",
            "interactive guided init fails without an attached terminal",
            ["scripts/agentic/agentic-gen.sh", "init", "--guided"],
            break_init_from_bundle_unknown_bundle,
            "Interactive --guided requires an attached terminal",
        ),
        (
            "failure",
            "guided dry-run fails without guided mode",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--bundle",
                "orchestrated-delivery",
                "--dry-run",
            ],
            no_mutation,
            "--dry-run requires --guided",
        ),
        (
            "failure",
            "interactive guided dry-run fails without an attached terminal",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--dry-run",
            ],
            no_mutation,
            "Interactive --guided requires an attached terminal",
        ),
        (
            "failure",
            "guided init fails when answer is used without an explicit setup",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--answer",
                "project-type=ai-application",
            ],
            break_init_from_bundle_unknown_bundle,
            "--answer requires --setup when used with --guided",
        ),
        (
            "failure",
            "guided init fails when setup is used without guided mode",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--setup",
                "orchestrated-delivery-greenfield",
            ],
            break_init_from_bundle_unknown_bundle,
            "--setup requires --guided",
        ),
        (
            "failure",
            "guided init fails when answer is used without guided mode",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--bundle",
                "orchestrated-delivery",
                "--answer",
                "project-type=ai-application",
            ],
            break_init_from_bundle_unknown_bundle,
            "--answer requires --guided",
        ),
        (
            "failure",
            "guided init fails when answer format is invalid",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--answer",
                "project-type",
            ],
            break_init_from_bundle_unknown_bundle,
            "Invalid --answer 'project-type'. Expected format: question=value",
        ),
        (
            "failure",
            "guided init fails when answer question is unknown",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--answer",
                "missing-question=value",
            ],
            break_init_from_bundle_unknown_bundle,
            "--answer references unknown setup question(s): ['missing-question']",
        ),
        (
            "failure",
            "guided init fails when answer selects blocked option",
            [
                "scripts/agentic/agentic-gen.sh",
                "init",
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--answer",
                "project-type=documentation-only",
            ],
            break_init_from_bundle_unknown_bundle,
            "question 'project-type' selected option 'documentation-only' is blocked",
        ),
        (
            "failure",
            "bundle registry validation fails when target adapter does not match bundle target",
            ["scripts/agentic/agentic-gen.sh", "validate-bundles"],
            break_bundle_registry_target_adapter_name_mismatch,
            "bundle target 'opencode' resolves to adapter named 'wrong-opencode'",
        ),
        (
            "failure",
            "bundle registry validation fails when target permission mapping is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-bundles"],
            break_bundle_registry_target_permission_mapping_missing,
            "target 'opencode' has no permission mapping for 'read-only'",
        ),
        (
            "failure",
            "setup registry validation fails when name does not match file",
            ["scripts/agentic/agentic-gen.sh", "validate-setups"],
            break_setup_registry_name_mismatch,
            "setup name 'wrong-setup' must match file name 'orchestrated-delivery-greenfield'",
        ),
        (
            "failure",
            "setup registry validation fails when default bundle is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-setups"],
            break_setup_registry_missing_default_bundle,
            "defaultBundle defaultBundle references missing bundle 'missing-bundle'",
        ),
        (
            "failure",
            "setup registry validation fails when recommended option is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-setups"],
            break_setup_registry_recommended_missing_option,
            "question 'project-type' recommended references missing option 'missing-option'",
        ),
        (
            "failure",
            "setup registry validation fails when recommended overlaps blocked",
            ["scripts/agentic/agentic-gen.sh", "validate-setups"],
            break_setup_registry_recommended_overlaps_blocked,
            "question 'project-type' has overlapping recommended/blocked values: ['microservice-platform']",
        ),
        (
            "failure",
            "setup registry validation rejects legacy agent recommendations",
            ["scripts/agentic/agentic-gen.sh", "validate-setups"],
            break_setup_registry_option_recommends_legacy_agents,
            "legacy recommendation field 'agents' is not allowed",
        ),
        (
            "failure",
            "setup profile validation fails when schemaVersion is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_missing_schema_version,
            "schemaVersion must be a non-empty string",
        ),
        (
            "failure",
            "setup profile validation fails when setup reference is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_missing_setup_reference,
            "setup references missing setup registry file 'missing-setup'",
        ),
        (
            "failure",
            "setup profile validation fails when answer option is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_answer_missing_option,
            "answer for question 'project-type' selects missing option 'missing-option'",
        ),
        (
            "failure",
            "setup profile validation fails when answer selects blocked option",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_answer_blocked_option,
            "answer for question 'project-type' selects blocked option 'documentation-only'",
        ),
        (
            "failure",
            "setup profile validation rejects legacy selected skills",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_selected_legacy_skill,
            "legacy selected field 'skills' is not allowed",
        ),
        (
            "failure",
            "setup profile validation fails when selected targets drift from answer recommends",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_selected_targets_drift_from_answer_recommends,
            "selected targets must match selected setup answer recommends",
        ),
        (
            "failure",
            "setup profile validation fails when answer classification drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_answer_classification_drift,
            "classification 'compatible' must be 'recommended'",
        ),
        (
            "failure",
            "setup profile validation fails when answer reason drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_answer_reason_drift,
            "reason does not match setup option reason",
        ),
        (
            "failure",
            "setup profile validation fails when fallback is allowed",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_fallback_allowed,
            "policy.fallbackAllowed must be false",
        ),
        (
            "failure",
            "target adapter validation fails when name is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_missing_name,
            "name must be a non-empty string",
        ),
        (
            "failure",
            "target adapter validation fails when name is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_empty_name,
            "name must be a non-empty string",
        ),
        (
            "failure",
            "target adapter validation fails when name does not match folder",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_name_folder_mismatch,
            "does not match target folder",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPaths is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_missing_owned_paths,
            "ownedPaths must be a non-empty list",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPaths has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_invalid_owned_paths_type,
            "ownedPaths must be a non-empty list",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPaths is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_empty_owned_paths,
            "ownedPaths must be a non-empty list",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPath entry is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_empty_owned_path_entry,
            "ownedPaths[0] must be a non-empty string",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPath is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_duplicate_owned_path,
            "is duplicated",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPath contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_parent_owned_path,
            "must be a safe relative path",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPath is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_absolute_owned_path,
            "must be a safe relative path",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPaths overlap",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_overlapping_owned_path,
            "overlaps",
        ),
        (
            "failure",
            "target adapter validation fails when description has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_invalid_description_type,
            "description must be a string when present",
        ),
        (
            "failure",
            "target adapter validation fails when version is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_empty_version,
            "version must be a non-empty string when present",
        ),
        (
            "failure",
            "target adapter validation fails when config target name is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_agentic_config_duplicate_target_name,
            "is duplicated",
        ),
        (
            "failure",
            "target adapter validation fails when config target enabled has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_agentic_config_target_enabled_invalid_type,
            "enabled must be a boolean",
        ),
        (
            "failure",
            "agentic config semantic validation fails when runtime context is enabled before Milestone 4",
            ["scripts/agentic/agentic-gen.sh", "validate"],
            break_agentic_config_runtime_context_enabled,
            "runtimeContext.enabled must be false before Milestone 4",
        ),
        (
            "failure",
            "agentic config semantic validation fails when missing runtime context is required before Milestone 4",
            ["scripts/agentic/agentic-gen.sh", "validate"],
            break_agentic_config_runtime_context_fail_if_missing,
            "runtimeContext.failIfMissing must be false before Milestone 4",
        ),
        (
            "failure",
            "lockfile validation fails when input file entry is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile_missing_input_file_entry,
            "missing input file in lockfile",
        ),
        (
            "failure",
            "lockfile validation fails when input file hash drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile_input_hash_drift,
            "sha256 drift for input file",
        ),
        (
            "failure",
            "lockfile validation fails when input file size drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile_input_size_drift,
            "sizeBytes drift for input file",
        ),
        (
            "failure",
            "lockfile validation fails when file count drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile_file_count_drift,
            "lockfile content drift detected",
        ),
        (
            "failure",
            "lockfile validation fails when content hash drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile_content_hash_drift,
            "lockfile content drift detected",
        ),
        (
            "failure",
            "lockfile validation fails when new registry input is not tracked",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile_untracked_registry_input,
            "missing input file in lockfile",
        ),
        (
            "failure",
            "lockfile validation fails when tracked files are empty",
            ["scripts/agentic/agentic-gen.sh", "validate-lockfile"],
            break_lockfile,
            "must not be empty",
        ),
    ]

    custom_tests = [
        expect_interactive_guided_defaults,
        expect_interactive_guided_first_question_back_returns_to_setup,
        expect_interactive_guided_cancel_preserves_files,
        expect_guided_dry_run_defaults,
        expect_guided_dry_run_opencode_override,
    ]

    if args.name_contains:
        needle = args.name_contains.casefold()
        tests = [test for test in tests if needle in test[1].casefold()]
        custom_tests = [
            test for test in custom_tests if needle in test.__name__.casefold()
        ]

        if not tests and not custom_tests:
            print(
                "FAIL: No negative gate tests matched "
                f"--name-contains {args.name_contains!r}."
            )
            return 1

    failures: list[str] = []

    for test in tests:
        expectation, name, command, mutate, expected_text, *rest = test
        post_check = rest[0] if rest else None

        if expectation == "success":
            passed, message = expect_success(
                name, command, mutate, expected_text, post_check
            )
        elif expectation == "failure":
            passed, message = expect_failure(name, command, mutate, expected_text)
        else:
            passed = False
            message = f"{name}: unknown expectation {expectation!r}"

        print(message)

        if not passed:
            failures.append(message)

    for custom_test in custom_tests:
        passed, message = custom_test()
        print(message)

        if not passed:
            failures.append(message)

    if failures:
        print()
        print(f"FAIL: {len(failures)} negative gate test(s) failed.")
        return 1

    total_tests = len(tests) + len(custom_tests)

    print()
    print(f"PASS: All {total_tests} negative gate tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
