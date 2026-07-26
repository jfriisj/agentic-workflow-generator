from pathlib import Path

import pytest

from agentic_workflow_generator.cli.agents import main
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "agent.schema.json"
)


def create_repository(
    root: Path,
    *,
    agent_name: str = "Implementer",
    capability: str = "implementation.code",
) -> None:
    schema_target = root / ".agentic" / "schemas" / "registry" / "agent.schema.json"
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    agent: JsonObject = {
        "name": agent_name,
        "version": "0.2.0",
        "role": "implementation",
        "description": "Implements approved work.",
        "recommendedResponsibilities": [
            "Modify product code",
        ],
        "defaultGuardrails": [
            "Do not self-approve",
        ],
        "recommendedCapabilities": [
            capability,
        ],
        "defaultPermissionProfile": ("implementation"),
    }
    agent_path = root / "registry" / "agents" / "Implementer" / "agent.json"
    agent_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(agent_path, agent)

    skill_path = root / "registry" / "skills" / "implementation" / "skill.json"
    skill_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(
        skill_path,
        {
            "name": "implementation",
            "provides": [
                "implementation.code",
            ],
        },
    )

    permission_path = (
        root
        / "registry"
        / "permission-profiles"
        / "implementation"
        / "permission-profile.json"
    )
    permission_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(
        permission_path,
        {"name": "implementation"},
    )


def test_main_returns_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main()

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Agent registry is valid. "
        "Checked 1 agent file(s), "
        "1 skill capability reference(s), "
        "and 1 permission profile(s).\n"
    )


def test_main_renders_semantic_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        capability="does.not.exist",
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert ("FAIL: Agent registry validation found 1 error(s).") in output
    assert "[AWG-AGENT-005]" in output
    assert ("registry/agents/Implementer/agent.json recommendedCapabilities") in output


def test_main_renders_folder_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        agent_name="Wrong",
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-AGENT-003]" in output
    assert "name 'Wrong' does not match folder" in output


def test_main_renders_registry_boundary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-AGENT-900]" in output
    assert "required registry root not found" in output
