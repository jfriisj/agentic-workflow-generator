#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
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

        expected_text = "interactive guided init was cancelled; no files were written"
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
    setup_profile = load_json(
        worktree / ".agentic" / "setup-profile.json"
    )
    config = load_json(
        worktree / ".agentic" / "agentic.json"
    )

    expected_selected = {
        "bundle": "ai-application",
        "targets": [
            "opencode",
            "vscode-copilot",
        ],
    }
    actual_selected = setup_profile.get("selected")

    if actual_selected != expected_selected:
        return (
            False,
            f"setup-profile selected was {actual_selected!r}, "
            f"expected {expected_selected!r}",
        )

    selection = config.get("selection")

    if not isinstance(selection, dict):
        return False, "agentic config selection must be an object"

    expected_selection = {
        "bundle": "ai-application",
        "profile": "ai-application",
        "workflow": "ai-application-delivery",
    }

    for key, expected_name in expected_selection.items():
        value = selection.get(key)

        if not isinstance(value, dict):
            return (
                False,
                f"agentic config selection.{key} must be an object",
            )

        actual_name = value.get("name")

        if actual_name != expected_name:
            return (
                False,
                f"agentic config selection.{key}.name was "
                f"{actual_name!r}, expected {expected_name!r}",
            )

    workflow = config.get("workflow")

    if not isinstance(workflow, dict):
        return False, "agentic config workflow must be an object"

    if workflow.get("name") != "ai-application-delivery":
        return (
            False,
            "agentic config workflow.name was "
            f"{workflow.get('name')!r}, expected "
            "'ai-application-delivery'",
        )

    agent_instances = config.get("agentInstances")

    if not isinstance(agent_instances, list):
        return False, "agentic config agentInstances must be a list"

    actual_instances: list[tuple[object, object]] = []

    for instance in agent_instances:
        if not isinstance(instance, dict):
            continue

        profile = instance.get("profile")
        profile_name = (
            profile.get("name")
            if isinstance(profile, dict)
            else None
        )
        actual_instances.append(
            (
                instance.get("id"),
                profile_name,
            )
        )

    expected_instances = [
        ("requirements-worker", "Requirements"),
        ("architecture-worker", "Architect"),
        ("implementation-worker", "Implementer"),
        ("ai-evaluation-worker", "AIEvaluator"),
        ("test-runner", "TestRunner"),
        ("code-review-worker", "CodeReviewer"),
        ("qa-worker", "QA"),
        ("workflow-controller", "Orchestrator"),
    ]

    if actual_instances != expected_instances:
        return (
            False,
            f"agentic config agent instances were "
            f"{actual_instances!r}, expected "
            f"{expected_instances!r}",
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


def break_target_output_missing_file(
    worktree: Path,
) -> None:
    path = (
        worktree
        / ".github"
        / "agents"
        / "workflow-controller.agent.md"
    )

    if not path.is_file():
        raise RuntimeError(
            "Expected generated file not found before "
            f"mutation: {path}"
        )

    path.unlink()


def break_target_output_content_drift(
    worktree: Path,
) -> None:
    path = (
        worktree
        / ".github"
        / "copilot-instructions.md"
    )

    if not path.is_file():
        raise RuntimeError(
            "Expected generated file not found before "
            f"mutation: {path}"
        )

    path.write_bytes(
        path.read_bytes()
        + b"\n<!-- negative target output drift -->\n"
    )


def break_target_output_unmanaged_file(
    worktree: Path,
) -> None:
    path = (
        worktree
        / ".github"
        / "agents"
        / "unmanaged.agent.md"
    )
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_bytes(b"# Unmanaged generated output\n")


def break_target_output_manifest_drift(
    worktree: Path,
) -> None:
    path = (
        worktree
        / ".agentic"
        / "generated"
        / "output-manifest.json"
    )

    if not path.is_file():
        raise RuntimeError(
            "Expected output manifest not found before "
            f"mutation: {path}"
        )

    path.write_bytes(
        path.read_bytes() + b"\n"
    )


def break_target_output_obsolete_resolution(
    worktree: Path,
) -> None:
    path = (
        worktree
        / ".agentic"
        / "generated"
        / "resolution.json"
    )
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_bytes(b"{}\n")






























def no_mutation(worktree: Path) -> None:
    _ = worktree


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


def break_generation_idempotency_by_changing_renderer(
    worktree: Path,
) -> None:
    subprocess.run(
        ["scripts/agentic/agentic-gen.sh", "all"],
        cwd=worktree,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )

    renderer_path = (
        worktree
        / "src"
        / "agentic_workflow_generator"
        / "application"
        / "target_rendering.py"
    )

    if not renderer_path.is_file():
        raise RuntimeError(
            "Expected typed target renderer not found before "
            f"mutation: {renderer_path}"
        )

    renderer_path.write_text(
        renderer_path.read_text(encoding="utf-8")
        + "\n# negative idempotency drift marker\n",
        encoding="utf-8",
    )










































































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


def break_target_adapter_supported_features(worktree: Path) -> None:
    path = (
        worktree
        / "registry"
        / "targets"
        / "opencode"
        / "adapter.json"
    )
    data = load_json(path)
    data["supportedFeatures"] = {
        "agents": True,
    }
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


def break_target_registry_adapter_name_mismatch(
    worktree: Path,
) -> None:
    path = awg_bundle_target_adapter_file(
        worktree,
        "opencode",
    )
    data = load_json(path)
    data["name"] = "wrong-opencode"
    write_json(path, data)


def break_target_registry_permission_mapping_missing(
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


def break_setup_registry_missing_default_bundle(
    worktree: Path,
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        default_selection = data.get("defaultSelection")

        if not isinstance(default_selection, dict):
            raise RuntimeError(
                "setup defaultSelection must be an object "
                "before mutation"
            )

        default_selection["bundle"] = "missing-bundle"

    awg_mutate_first_setup(worktree, mutate)


def break_setup_registry_recommended_missing_option(
    worktree: Path,
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        questions = data.get("questions")

        if not isinstance(questions, list) or not questions:
            raise RuntimeError(
                "setup questions must be a non-empty list "
                "before mutation"
            )

        first_question = questions[0]

        if not isinstance(first_question, dict):
            raise RuntimeError(
                "setup questions[0] must be an object "
                "before mutation"
            )

        first_question["defaultOption"] = "missing-option"

    awg_mutate_first_setup(worktree, mutate)


def break_setup_registry_recommended_overlaps_blocked(
    worktree: Path,
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        questions = data.get("questions")

        if not isinstance(questions, list) or not questions:
            raise RuntimeError(
                "setup questions must be a non-empty list "
                "before mutation"
            )

        first_question = questions[0]

        if not isinstance(first_question, dict):
            raise RuntimeError(
                "setup questions[0] must be an object "
                "before mutation"
            )

        options = first_question.get("options")

        if not isinstance(options, list):
            raise RuntimeError(
                "setup questions[0].options must be a list "
                "before mutation"
            )

        blocked_option = next(
            (
                option
                for option in options
                if isinstance(option, dict)
                and option.get("classification") == "blocked"
                and isinstance(option.get("value"), str)
            ),
            None,
        )

        if not isinstance(blocked_option, dict):
            raise RuntimeError(
                "setup question must contain a blocked option "
                "before mutation"
            )

        first_question["defaultOption"] = blocked_option["value"]

    awg_mutate_first_setup(worktree, mutate)


def break_setup_registry_option_recommends_obsolete_agents(
    worktree: Path,
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        questions = data.get("questions")

        if not isinstance(questions, list) or not questions:
            raise RuntimeError(
                "setup questions must be a non-empty list "
                "before mutation"
            )

        first_question = questions[0]

        if not isinstance(first_question, dict):
            raise RuntimeError(
                "setup questions[0] must be an object "
                "before mutation"
            )

        options = first_question.get("options")

        if not isinstance(options, list) or not options:
            raise RuntimeError(
                "setup question options must be a non-empty "
                "list before mutation"
            )

        first_option = options[0]

        if not isinstance(first_option, dict):
            raise RuntimeError(
                "setup question options[0] must be an object "
                "before mutation"
            )

        selection = first_option.get("selection")

        if selection is None:
            selection = {}
            first_option["selection"] = selection

        if not isinstance(selection, dict):
            raise RuntimeError(
                "setup option selection must be an object "
                "before mutation"
            )

        selection["agents"] = ["Requirements"]

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


def break_setup_profile_selected_obsolete_skill(
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
        setup_name = data.get("setup")

        if not isinstance(setup_name, str) or not setup_name.strip():
            raise RuntimeError(
                "setup profile setup must be a non-empty "
                "string before mutation"
            )

        setup = load_json(
            worktree
            / "registry"
            / "setups"
            / f"{setup_name}.setup.json"
        )
        questions = setup.get("questions")

        if not isinstance(questions, list):
            raise RuntimeError(
                "setup questions must be a list before mutation"
            )

        target_question = next(
            (
                question
                for question in questions
                if isinstance(question, dict)
                and question.get("id") == "target-platforms"
            ),
            None,
        )

        if not isinstance(target_question, dict):
            raise RuntimeError(
                "target-platforms setup question must exist "
                "before mutation"
            )

        options = target_question.get("options")

        if not isinstance(options, list):
            raise RuntimeError(
                "target-platforms options must be a list "
                "before mutation"
            )

        selected_option = next(
            (
                option
                for option in options
                if isinstance(option, dict)
                and option.get("value") == "opencode-only"
            ),
            None,
        )

        if not isinstance(selected_option, dict):
            raise RuntimeError(
                "opencode-only setup option must exist "
                "before mutation"
            )

        classification = selected_option.get("classification")
        reason = selected_option.get("reason")

        if not isinstance(classification, str):
            raise RuntimeError(
                "opencode-only classification must be a string "
                "before mutation"
            )

        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeError(
                "opencode-only reason must be a non-empty "
                "string before mutation"
            )

        answers = data.get("answers")

        if not isinstance(answers, list):
            raise RuntimeError(
                "setup profile answers must be a list "
                "before mutation"
            )

        answer = next(
            (
                item
                for item in answers
                if isinstance(item, dict)
                and item.get("question") == "target-platforms"
            ),
            None,
        )

        if not isinstance(answer, dict):
            raise RuntimeError(
                "setup profile target-platforms answer must "
                "exist before mutation"
            )

        answer["selected"] = "opencode-only"
        answer["classification"] = classification
        answer["reason"] = reason

        selected = data.get("selected")

        if not isinstance(selected, dict):
            raise RuntimeError(
                "setup profile selected must be an object "
                "before mutation"
            )

        selected["targets"] = [
            "opencode",
            "vscode-copilot",
        ]

    awg_mutate_setup_profile(worktree, mutate)


def break_setup_profile_answer_classification_drift(
    worktree: Path,
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        setup_name = data.get("setup")

        if not isinstance(setup_name, str) or not setup_name.strip():
            raise RuntimeError(
                "setup profile setup must be a non-empty "
                "string before mutation"
            )

        setup = load_json(
            worktree
            / "registry"
            / "setups"
            / f"{setup_name}.setup.json"
        )
        questions = setup.get("questions")

        if not isinstance(questions, list) or not questions:
            raise RuntimeError(
                "setup questions must be a non-empty list "
                "before mutation"
            )

        first_question = questions[0]

        if not isinstance(first_question, dict):
            raise RuntimeError(
                "setup questions[0] must be an object "
                "before mutation"
            )

        question_id = first_question.get("id")
        selected = first_question.get("defaultOption")
        options = first_question.get("options")

        if not isinstance(question_id, str) or not question_id.strip():
            raise RuntimeError(
                "setup questions[0].id must be a non-empty "
                "string before mutation"
            )

        if not isinstance(selected, str) or not selected.strip():
            raise RuntimeError(
                "setup questions[0].defaultOption must be a "
                "non-empty string before mutation"
            )

        if not isinstance(options, list) or not options:
            raise RuntimeError(
                "setup questions[0].options must be a "
                "non-empty list before mutation"
            )

        selected_option = next(
            (
                option
                for option in options
                if isinstance(option, dict)
                and option.get("value") == selected
            ),
            None,
        )

        if not isinstance(selected_option, dict):
            raise RuntimeError(
                "setup default option must exist before mutation"
            )

        reason = selected_option.get("reason")

        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeError(
                "setup default option reason must be a "
                "non-empty string before mutation"
            )

        answers = data.get("answers")

        if not isinstance(answers, list) or not answers:
            raise RuntimeError(
                "setup profile answers must be a non-empty "
                "list before mutation"
            )

        answer = next(
            (
                item
                for item in answers
                if isinstance(item, dict)
                and item.get("question") == question_id
            ),
            None,
        )

        if not isinstance(answer, dict):
            raise RuntimeError(
                "setup profile answer must exist before mutation"
            )

        answer["selected"] = selected
        answer["classification"] = "compatible"
        answer["reason"] = reason

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


def break_agent_registry_obsolete_field(
    worktree: Path,
) -> None:
    path = first_agent_registry_file(worktree)
    data = load_json(path)
    data["produces"] = ["ObsoleteArtifact"]
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
            "target output validation fails when a generated file is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_target_output_missing_file,
            "AWG-TARGET-OUTPUT-001",
        ),
        (
            "failure",
            "target output validation fails when generated content drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_target_output_content_drift,
            "AWG-TARGET-OUTPUT-003",
        ),
        (
            "failure",
            "target output validation fails when an unmanaged file exists",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_target_output_unmanaged_file,
            "AWG-TARGET-OUTPUT-004",
        ),
        (
            "failure",
            "target output validation fails when the manifest drifts",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_target_output_manifest_drift,
            "AWG-TARGET-OUTPUT-005",
        ),
        (
            "failure",
            "target output validation rejects obsolete resolution output",
            ["scripts/agentic/agentic-gen.sh", "validate-generated"],
            break_target_output_obsolete_resolution,
            "AWG-TARGET-OUTPUT-006",
        ),
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
            "generation idempotency validation fails when a compiler input changes between runs",
            ["scripts/agentic/agentic-gen.sh", "validate-idempotency"],
            break_generation_idempotency_by_changing_renderer,
            "Generation is not idempotent",
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
            "target adapter validation fails when ownedPaths overlap across targets",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_owned_path_overlap,
            "AWG-TARGET-009",
        ),
        (
            "failure",
            "target adapter validation fails when target name is duplicate",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_duplicate_name,
            "AWG-TARGET-004",
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
            "agent registry validation rejects obsolete agent fields",
            ["scripts/agentic/agentic-gen.sh", "validate-agents"],
            break_agent_registry_obsolete_field,
            "obsolete agent field 'produces' is not allowed",
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
            "unknown bundle 'missing-bundle'",
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
            "unknown guided setup 'missing-setup'",
        ),
        (
            "failure",
            "interactive guided init fails without an attached terminal",
            ["scripts/agentic/agentic-gen.sh", "init", "--guided"],
            break_init_from_bundle_unknown_bundle,
            "interactive --guided requires an attached terminal",
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
            "interactive --guided requires an attached terminal",
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
            "invalid answer override 'project-type'; expected question=value",
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
            "answer overrides reference unknown setup question(s): ['missing-question']",
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
            "question 'project-type' selected blocked option 'documentation-only'",
        ),
        (
            "failure",
            "target registry validation fails when adapter name does not match folder",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_registry_adapter_name_mismatch,
            "AWG-TARGET-003",
        ),
        (
            "failure",
            "target registry validation fails when permission mapping is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_registry_permission_mapping_missing,
            "AWG-TARGET-011",
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
            "selection references missing bundle 'missing-bundle'",
        ),
        (
            "failure",
            "setup registry validation fails when default option is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-setups"],
            break_setup_registry_recommended_missing_option,
            "does not reference an option",
        ),
        (
            "failure",
            "setup registry validation fails when default option is blocked",
            ["scripts/agentic/agentic-gen.sh", "validate-setups"],
            break_setup_registry_recommended_overlaps_blocked,
            "must be classified as recommended",
        ),
        (
            "failure",
            "setup registry validation rejects obsolete agent selection",
            ["scripts/agentic/agentic-gen.sh", "validate-setups"],
            break_setup_registry_option_recommends_obsolete_agents,
            "obsolete setup field 'agents' is not allowed",
        ),
        (
            "failure",
            "setup profile validation fails when schemaVersion is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_missing_schema_version,
            "'schemaVersion' is a required property",
        ),
        (
            "failure",
            "setup profile validation fails when setup reference is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_missing_setup_reference,
            "setup profile references missing setup 'missing-setup'",
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
            "setup profile validation rejects obsolete selected skills",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_selected_obsolete_skill,
            "obsolete selected field 'skills' is not allowed",
        ),
        (
            "failure",
            "setup profile validation fails when selected targets drift from answer recommends",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_selected_targets_drift_from_answer_recommends,
            "selected targets must match the materialized setup answers",
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
            "reason for question 'project-type' does not match the setup option reason",
        ),
        (
            "failure",
            "setup profile validation fails when fallback is allowed",
            ["scripts/agentic/agentic-gen.sh", "validate-setup-profile"],
            break_setup_profile_fallback_allowed,
            "False was expected",
        ),
        (
            "failure",
            "target adapter validation fails when name is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_missing_name,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when name is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_empty_name,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when name does not match folder",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_name_folder_mismatch,
            "AWG-TARGET-003",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPaths is missing",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_missing_owned_paths,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPaths has invalid type",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_invalid_owned_paths_type,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPaths is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_empty_owned_paths,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPath entry is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_empty_owned_path_entry,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPath is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_duplicate_owned_path,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPath contains parent reference",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_parent_owned_path,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when ownedPath is absolute",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_absolute_owned_path,
            "AWG-TARGET-001",
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
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "target adapter validation fails when version is empty",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_empty_version,
            "AWG-TARGET-001",
        ),
        (
            "failure",
            "active config validation fails when target entry is duplicated",
            ["scripts/agentic/agentic-gen.sh", "validate"],
            break_agentic_config_duplicate_target_name,
            "AWG-ACTIVE-CONFIG-001",
        ),
        (
            "failure",
            "active config validation fails when target enabled is not true",
            ["scripts/agentic/agentic-gen.sh", "validate"],
            break_agentic_config_target_enabled_invalid_type,
            "AWG-ACTIVE-CONFIG-001",
        ),
        (
            "failure",
            "target adapter validation rejects obsolete supported features",
            ["scripts/agentic/agentic-gen.sh", "validate-targets"],
            break_target_adapter_supported_features,
            "supportedFeatures is obsolete and must not be declared",
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
