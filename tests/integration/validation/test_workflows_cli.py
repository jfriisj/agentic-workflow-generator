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
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "workflow.schema.json"
)


def create_repository(
    root: Path,
    *,
    artifact_type: str = "Requirements",
) -> None:
    schema_target = root / ".agentic" / "schemas" / "registry" / "workflow.schema.json"
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    workflow: JsonObject = {
        "name": "lean-delivery",
        "version": "0.2.0",
        "description": "Lean workflow.",
        "startState": "Requirements",
        "terminalStates": [
            "Done",
            "Blocked",
        ],
        "defaultFailureState": "Blocked",
        "failClosed": True,
        "states": [
            {
                "name": "Requirements",
                "gate": {
                    "name": "requirements-review",
                    "blocking": True,
                    "requiredCapabilities": [
                        "requirements.elicit",
                    ],
                    "requiredArtifacts": [
                        artifact_type,
                    ],
                },
            },
            {
                "name": "Done",
                "terminal": True,
            },
            {
                "name": "Blocked",
                "terminal": True,
            },
        ],
        "transitions": [
            {
                "from": "Requirements",
                "to": "Done",
                "on": "pass",
            },
            {
                "from": "Requirements",
                "to": "Blocked",
                "on": "fail",
            },
        ],
    }
    workflow_path = root / "registry" / "workflows" / "lean-delivery.workflow.json"
    workflow_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(workflow_path, workflow)

    skill_path = root / "registry" / "skills" / "requirements" / "skill.json"
    skill_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(
        skill_path,
        {
            "name": "requirements",
            "provides": [
                "requirements.elicit",
            ],
        },
    )

    artifact_path = root / "registry" / "artifacts" / "Requirements" / "artifact.json"
    artifact_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(
        artifact_path,
        {
            "type": "Requirements",
            "allowedStatuses": [
                "PASS",
                "FAIL",
                "BLOCKED",
            ],
        },
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
            "agentic_workflow_generator.cli.workflows",
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
        "PASS: Workflow registry is valid. "
        "Checked 1 workflow file(s), "
        "1 gate(s), "
        "1 skill capability reference(s), and "
        "1 artifact contract(s).\n"
    )


def test_launcher_renders_structured_failure(
    tmp_path: Path,
) -> None:
    create_repository(
        tmp_path,
        artifact_type="MissingArtifact",
    )

    result = run_launcher(tmp_path)

    assert result.returncode == 1
    assert "[AWG-WORKFLOW-012]" in result.stdout
    assert (
        "gate requires missing artifact contract 'MissingArtifact'"
    ) in result.stdout
