from pathlib import Path

import pytest

from agentic_workflow_generator.cli.skills import main
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "skill.schema.json"
)


def create_repository(
    root: Path,
    *,
    recommended_agent: str = "Implementer",
    create_content: bool = True,
    agent_name: JsonValue = "Implementer",
) -> None:
    schema_target = root / ".agentic" / "schemas" / "registry" / "skill.schema.json"
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    skill: JsonObject = {
        "name": "implementation",
        "version": "1.0.0",
        "description": "Implements approved work.",
        "provides": ["implementation.code"],
        "contentPath": "SKILL.md",
        "contextBudget": {"maxTokens": 4000},
        "requiresCapabilities": [],
        "recommendedAgents": [recommended_agent],
    }
    skill_path = root / "registry" / "skills" / "implementation" / "skill.json"
    skill_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(skill_path, skill)

    if create_content:
        skill_path.with_name("SKILL.md").write_text(
            "# Implementation\n",
            encoding="utf-8",
        )

    agent_path = root / "registry" / "agents" / "Implementer" / "agent.json"
    agent_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(
        agent_path,
        {"name": agent_name},
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
        "PASS: Skill registry is valid. "
        "Checked 1 skill directorie(s), "
        "1 capability provider(s), and "
        "1 agent profile(s).\n"
    )


def test_main_renders_semantic_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        recommended_agent="DoesNotExist",
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert ("FAIL: Skill registry validation found 1 error(s).") in output
    assert "[AWG-SKILL-007]" in output
    assert "recommendedAgents" in output


def test_main_renders_missing_content_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        create_content=False,
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-SKILL-003]" in output
    assert "must reference an existing file" in output


def test_main_renders_projection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        agent_name="",
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-SKILL-900]" in output
    assert "name must be a non-empty string" in output


def test_main_renders_registry_boundary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-SKILL-900]" in output
    assert "required registry root not found" in output
