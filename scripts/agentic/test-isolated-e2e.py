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
SETUP_NAME = "orchestrated-delivery-greenfield"

SOURCE_DIRECTORIES = (
    Path("registry"),
    Path("scripts/agentic"),
    Path(".agentic/schemas"),
)

SNAPSHOT_PATHS = (
    Path(".agentic/setup-profile.json"),
    Path(".agentic/agentic.json"),
    Path(".agentic/generated/resolution.json"),
    Path(".agentic/agentic-lock.json"),
    Path(".github"),
    Path(".opencode"),
    Path("AGENTS.md"),
    Path("opencode.json"),
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Required JSON file was not generated: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise RuntimeError(f"{path}: expected a JSON object")

    return data


def copy_source_tree(fixture_root: Path) -> None:
    fixture_root.mkdir(parents=True)

    for relative_path in SOURCE_DIRECTORIES:
        source = ROOT / relative_path
        destination = fixture_root / relative_path

        if not source.is_dir():
            raise RuntimeError(f"Required source directory is missing: {source}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
            ),
        )


def run_command(
    fixture_root: Path,
    command: list[str],
    expected_text: str,
) -> str:
    result = subprocess.run(
        command,
        cwd=fixture_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed with exit code "
            f"{result.returncode}: {' '.join(command)}\n\n"
            f"Output:\n{result.stdout}"
        )

    if expected_text not in result.stdout:
        raise RuntimeError(
            f"Command succeeded but expected text was missing: {expected_text!r}\n\n"
            f"Command: {' '.join(command)}\n\n"
            f"Output:\n{result.stdout}"
        )

    return result.stdout


def assert_clean_start(fixture_root: Path) -> None:
    forbidden_paths = (
        fixture_root / ".agentic" / "agentic.json",
        fixture_root / ".agentic" / "setup-profile.json",
        fixture_root / ".agentic" / "agentic-lock.json",
        fixture_root / ".agentic" / "generated",
        fixture_root / ".github",
        fixture_root / ".opencode",
        fixture_root / "AGENTS.md",
        fixture_root / "opencode.json",
    )

    existing = [
        str(path.relative_to(fixture_root))
        for path in forbidden_paths
        if path.exists()
    ]

    if existing:
        raise RuntimeError(
            "Isolated fixture inherited generated or configured state: "
            + ", ".join(existing)
        )


def assert_materialized_configuration(fixture_root: Path) -> None:
    setup_profile = load_json(
        fixture_root / ".agentic" / "setup-profile.json"
    )
    config = load_json(
        fixture_root / ".agentic" / "agentic.json"
    )

    if setup_profile.get("setup") != SETUP_NAME:
        raise RuntimeError(
            "setup-profile setup was "
            f"{setup_profile.get('setup')!r}, expected {SETUP_NAME!r}"
        )

    selected = setup_profile.get("selected")
    if not isinstance(selected, dict):
        raise RuntimeError("setup-profile selected must be an object")

    if selected.get("bundle") != "orchestrated-delivery":
        raise RuntimeError(
            "setup-profile selected.bundle was "
            f"{selected.get('bundle')!r}"
        )

    if selected.get("targets") != ["opencode", "vscode-copilot"]:
        raise RuntimeError(
            "setup-profile selected.targets was "
            f"{selected.get('targets')!r}"
        )

    project = config.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("agentic config project must be an object")

    if project.get("name") != fixture_root.name:
        raise RuntimeError(
            f"project.name was {project.get('name')!r}, "
            f"expected {fixture_root.name!r}"
        )

    targets = config.get("targets")
    if not isinstance(targets, list):
        raise RuntimeError("agentic config targets must be a list")

    enabled_targets = sorted(
        target.get("name")
        for target in targets
        if isinstance(target, dict) and target.get("enabled") is True
    )

    if enabled_targets != ["opencode", "vscode-copilot"]:
        raise RuntimeError(
            f"enabled targets were {enabled_targets!r}"
        )


def assert_generated_outputs(fixture_root: Path) -> None:
    resolution = load_json(
        fixture_root / ".agentic" / "generated" / "resolution.json"
    )
    lockfile = load_json(
        fixture_root / ".agentic" / "agentic-lock.json"
    )

    summary = resolution.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("resolution summary must be an object")

    if summary.get("errorCount") != 0:
        raise RuntimeError(
            "resolution errorCount was "
            f"{summary.get('errorCount')!r}"
        )

    agents = resolution.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("resolution agents must be a non-empty list")

    required_files = [
        fixture_root / ".github" / "copilot-instructions.md",
        fixture_root / "AGENTS.md",
        fixture_root / "opencode.json",
    ]

    for agent in agents:
        if not isinstance(agent, dict):
            raise RuntimeError("resolution agent entries must be objects")

        name = agent.get("name")
        if not isinstance(name, str) or not name.strip():
            raise RuntimeError("resolved agent name must be non-empty")

        slug = []
        previous_lower_or_digit = False

        for character in name:
            if (
                character.isupper()
                and previous_lower_or_digit
            ):
                slug.append("-")

            if character.isalnum():
                slug.append(character.lower())
                previous_lower_or_digit = (
                    character.islower() or character.isdigit()
                )
            else:
                if slug and slug[-1] != "-":
                    slug.append("-")
                previous_lower_or_digit = False

        agent_slug = "".join(slug).strip("-")

        required_files.extend(
            [
                fixture_root
                / ".github"
                / "agents"
                / f"{agent_slug}.agent.md",
                fixture_root
                / ".opencode"
                / "agents"
                / f"{agent_slug}.md",
            ]
        )

    for path in required_files:
        if not path.is_file():
            raise RuntimeError(
                "Required generated output is missing: "
                f"{path.relative_to(fixture_root)}"
            )

        if path.stat().st_size == 0:
            raise RuntimeError(
                "Generated output is empty: "
                f"{path.relative_to(fixture_root)}"
            )

    inputs = lockfile.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("lockfile inputs must be an object")

    file_count = inputs.get("fileCount")
    if not isinstance(file_count, int) or file_count <= 0:
        raise RuntimeError(
            f"lockfile inputs.fileCount was {file_count!r}"
        )

    content_hash = inputs.get("contentHash")
    if (
        not isinstance(content_hash, str)
        or not content_hash.startswith("sha256:")
    ):
        raise RuntimeError(
            f"lockfile contentHash was {content_hash!r}"
        )


def snapshot_source_payload() -> dict[str, str]:
    snapshot: dict[str, str] = {}

    for relative_directory in SOURCE_DIRECTORIES:
        directory = ROOT / relative_directory

        if not directory.is_dir():
            raise RuntimeError(
                f"Required source directory is missing: {directory}"
            )

        for path in sorted(directory.rglob("*")):
            if (
                not path.is_file()
                or "__pycache__" in path.parts
                or path.suffix in {".pyc", ".pyo"}
            ):
                continue

            relative_path = path.relative_to(ROOT)
            snapshot[str(relative_path)] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

    if not snapshot:
        raise RuntimeError("Compiler source payload contains no files")

    return snapshot


def snapshot_files(fixture_root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}

    for relative_path in SNAPSHOT_PATHS:
        path = fixture_root / relative_path

        if path.is_file():
            snapshot[str(relative_path)] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            continue

        if path.is_dir():
            files = sorted(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and "__pycache__" not in candidate.parts
                and candidate.suffix not in {".pyc", ".pyo"}
            )

            if not files:
                raise RuntimeError(
                    f"Snapshot directory contains no files: {relative_path}"
                )

            for candidate in files:
                relative_candidate = candidate.relative_to(fixture_root)
                snapshot[str(relative_candidate)] = hashlib.sha256(
                    candidate.read_bytes()
                ).hexdigest()
            continue

        raise RuntimeError(
            f"Required snapshot path is missing: {relative_path}"
        )

    return snapshot


def main() -> int:
    print("== Isolated consumer end-to-end test ==")

    source_snapshot_before = snapshot_source_payload()

    temp_root = Path(
        tempfile.mkdtemp(prefix="agentic-isolated-e2e-")
    )
    fixture_root = temp_root / "consumer-project"

    exit_code = 0

    try:
        copy_source_tree(fixture_root)
        assert_clean_start(fixture_root)

        init_command = [
            "scripts/agentic/agentic-gen.sh",
            "init",
            "--guided",
            "--setup",
            SETUP_NAME,
        ]

        run_command(
            fixture_root,
            init_command,
            "PASS: Initialized .agentic/setup-profile.json "
            f"from guided setup '{SETUP_NAME}'.",
        )
        assert_materialized_configuration(fixture_root)

        run_command(
            fixture_root,
            ["scripts/agentic/agentic-gen.sh", "all"],
            "PASS: Generated output is valid.",
        )
        assert_generated_outputs(fixture_root)

        first_snapshot = snapshot_files(fixture_root)

        run_command(
            fixture_root,
            init_command,
            "PASS: Initialized .agentic/setup-profile.json "
            f"from guided setup '{SETUP_NAME}'.",
        )
        run_command(
            fixture_root,
            ["scripts/agentic/agentic-gen.sh", "all"],
            "PASS: Generated output is valid.",
        )

        second_snapshot = snapshot_files(fixture_root)

        if first_snapshot != second_snapshot:
            changed = sorted(
                path
                for path in set(first_snapshot) | set(second_snapshot)
                if first_snapshot.get(path) != second_snapshot.get(path)
            )
            raise RuntimeError(
                "Isolated end-to-end output was not deterministic. "
                "Changed paths: "
                + ", ".join(changed)
            )

        source_snapshot_after = snapshot_source_payload()
        if source_snapshot_before != source_snapshot_after:
            changed = sorted(
                path
                for path in set(source_snapshot_before)
                | set(source_snapshot_after)
                if source_snapshot_before.get(path)
                != source_snapshot_after.get(path)
            )
            raise RuntimeError(
                "Isolated end-to-end execution modified compiler sources. "
                "Changed paths: "
                + ", ".join(changed)
            )

        print(
            "PASS: Isolated consumer fixture initialized from a clean state."
        )
        print(
            "PASS: Both targets, resolution, and lockfile were generated "
            "and validated."
        )
        print(
            "PASS: Repeated guided init and generation were byte-identical "
            f"across {len(first_snapshot)} tracked file(s)."
        )
        print(
            "PASS: Compiler source payload remained byte-identical."
        )
    except Exception as exc:
        print(f"FAIL: {exc}")
        exit_code = 1
    finally:
        try:
            shutil.rmtree(temp_root)
        except Exception as cleanup_exc:
            print(
                f"FAIL: Could not remove isolated fixture {temp_root}: "
                f"{cleanup_exc}"
            )
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
