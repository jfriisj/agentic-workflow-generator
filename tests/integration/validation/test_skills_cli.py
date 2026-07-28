import os
import subprocess
import sys
from pathlib import Path

from agentic_workflow_generator.infrastructure import (
    JsonObject,
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
        {"name": "Implementer"},
    )


def run_launcher(
    root: Path,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_workflow_generator.cli.skills",
        ],
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_launcher_preserves_success_contract(
    tmp_path: Path,
) -> None:
    create_repository(tmp_path)

    result = run_launcher(tmp_path)

    assert result.returncode == 0
    assert result.stdout == (
        "PASS: Skill registry is valid. "
        "Checked 1 skill directorie(s), "
        "1 capability provider(s), and "
        "1 agent profile(s).\n"
    )


def test_launcher_renders_structured_failure(
    tmp_path: Path,
) -> None:
    create_repository(
        tmp_path,
        recommended_agent="DoesNotExist",
    )

    result = run_launcher(tmp_path)

    assert result.returncode == 1
    assert "[AWG-SKILL-007]" in result.stdout
    assert (
        "recommendedAgents entry 'DoesNotExist' must reference an existing agent"
    ) in result.stdout
