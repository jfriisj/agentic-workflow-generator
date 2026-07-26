from pathlib import Path

import pytest

from agentic_workflow_generator.cli.workflows import main
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
    workflow_name: str = "lean-delivery",
    capability: str = "requirements.elicit",
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
        "name": workflow_name,
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
                        capability,
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


def test_main_preserves_success_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main()

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Workflow registry is valid. "
        "Checked 1 workflow file(s), "
        "1 gate(s), "
        "1 skill capability reference(s), and "
        "1 artifact contract(s).\n"
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
    assert ("FAIL: Workflow registry validation found 1 error(s).") in output
    assert "[AWG-WORKFLOW-011]" in output
    assert (
        "gate requires capability 'does.not.exist' not provided by a registered skill"
    ) in output


def test_main_renders_file_name_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        workflow_name="different",
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-WORKFLOW-003]" in output
    assert ("name 'different' does not match file name 'lean-delivery'") in output


def test_main_renders_registry_boundary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-WORKFLOW-900]" in output
    assert "required registry root not found" in output


def test_main_renders_dependency_projection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(tmp_path)
    skill_path = tmp_path / "registry" / "skills" / "requirements" / "skill.json"
    write_json(
        skill_path,
        {
            "name": "requirements",
            "provides": [],
        },
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-WORKFLOW-900]" in output
    assert "provides must be a non-empty list" in output
