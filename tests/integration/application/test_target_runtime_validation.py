from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agentic_workflow_generator.application.target_materialization import (
    materialize_targets,
)
from agentic_workflow_generator.application.target_runtime_validation import (
    EXECUTABLE_MISSING_DIAGNOSTIC,
    RUNTIME_CONTRACT_DIAGNOSTIC,
    validate_opencode_runtime,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
    tmp_path: Path,
) -> ProjectPaths:
    agentic_root = tmp_path / ".agentic"
    agentic_root.mkdir()

    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        agentic_root / "schemas",
    )
    shutil.copy2(
        REPOSITORY_ROOT / ".agentic" / "agentic.json",
        agentic_root / "agentic.json",
    )
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        tmp_path / "registry",
    )

    paths = ProjectPaths(tmp_path.resolve())
    materialize_targets(paths)
    return paths


def effective_runtime_data(
    paths: ProjectPaths,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    config = read_json_object(
        paths.repository_path("opencode.json")
    )
    agents: dict[str, object] = {}

    for path in sorted(
        paths.repository_path(
            ".opencode/agents"
        ).glob("*.md")
    ):
        mode = next(
            line.split(":", 1)[1].strip()
            for line in path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.startswith("mode:")
        )
        agents[path.stem] = {"mode": mode}

    effective_config: dict[str, object] = {
        "default_agent": config["default_agent"],
        "agent": agents,
    }
    skills = [
        {"name": path.name}
        for path in sorted(
            paths.repository_path(
                ".opencode/skills"
            ).iterdir()
        )
        if path.is_dir()
    ]
    return effective_config, skills


def test_runtime_accepts_canonical_opencode_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = copy_repository(tmp_path)
    effective_config, skills = effective_runtime_data(
        paths
    )

    monkeypatch.setattr(
        shutil,
        "which",
        lambda _name: "/usr/bin/opencode",
    )

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert kwargs["cwd"] == paths.root
        payload = (
            effective_config
            if command[-1] == "config"
            else skills
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(payload),
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    assert validate_opencode_runtime(paths) == ()


def test_runtime_requires_opencode_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.setattr(
        shutil,
        "which",
        lambda _name: None,
    )

    diagnostics = validate_opencode_runtime(paths)

    assert {
        diagnostic.code
        for diagnostic in diagnostics
    } == {EXECUTABLE_MISSING_DIAGNOSTIC}


def test_runtime_detects_missing_effective_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = copy_repository(tmp_path)
    effective_config, skills = effective_runtime_data(
        paths
    )
    agents = effective_config["agent"]
    assert isinstance(agents, dict)
    agents.pop("requirements-worker")

    monkeypatch.setattr(
        shutil,
        "which",
        lambda _name: "/usr/bin/opencode",
    )

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert kwargs["cwd"] == paths.root
        payload = (
            effective_config
            if command[-1] == "config"
            else skills
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(payload),
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    diagnostics = validate_opencode_runtime(paths)

    assert RUNTIME_CONTRACT_DIAGNOSTIC in {
        diagnostic.code
        for diagnostic in diagnostics
    }
