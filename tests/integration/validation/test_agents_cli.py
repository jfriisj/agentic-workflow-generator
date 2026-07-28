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
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "agent.schema.json"
)


def create_repository(
    root: Path,
    *,
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
        "name": "Implementer",
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


def run_launcher(
    root: Path,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_workflow_generator.cli.agents",
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
        "PASS: Agent registry is valid. "
        "Checked 1 agent file(s), "
        "1 skill capability reference(s), "
        "and 1 permission profile(s).\n"
    )


def test_launcher_renders_structured_failure(
    tmp_path: Path,
) -> None:
    create_repository(
        tmp_path,
        capability="does.not.exist",
    )

    result = run_launcher(tmp_path)

    assert result.returncode == 1
    assert "[AWG-AGENT-005]" in result.stdout
    assert (
        "recommendedCapabilities entry "
        "'does.not.exist' must be provided "
        "by a registered skill"
    ) in result.stdout
