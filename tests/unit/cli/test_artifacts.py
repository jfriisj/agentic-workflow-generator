from pathlib import Path

import pytest

from agentic_workflow_generator.cli.artifacts import main
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
    write_json,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.artifacts import (
    validate_artifact_registry,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "artifact.schema.json"
)
SCHEMA = read_json_object(SCHEMA_SOURCE)


def create_repository(
    root: Path,
    *,
    artifact_type: str = "Requirements",
    drift_schema: bool = False,
) -> None:
    schema_target = root / ".agentic" / "schemas" / "registry" / "artifact.schema.json"
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    artifact: JsonObject = {
        "type": artifact_type,
        "version": "0.3.0",
        "description": "Requirements contract.",
        "pathPattern": "agent-output/requirements/*.md",
        "status": {
            "heading": "## Status",
            "pattern": "PASS|FAIL|BLOCKED",
        },
        "provenance": {
            "heading": "## Provenance",
            "requiredIdentities": [
                "artifactType",
                "artifactVersion",
                "workflow",
                "workflowVersion",
                "roleBinding",
                "agentInstance",
            ],
        },
        "allowedStatuses": [
            "PASS",
            "FAIL",
            "BLOCKED",
        ],
        "requiredHeadings": [
            "# Requirements",
            "## Status",
            "## Provenance",
            "## Summary",
        ],
    }
    artifact_path = root / "registry" / "artifacts" / "Requirements" / "artifact.json"
    artifact_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(artifact_path, artifact)

    source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=Path("registry/artifacts/Requirements/artifact.json"),
        data=artifact,
    )
    projection = validate_artifact_registry(
        (source,),
        SCHEMA,
        (),
    ).schema_projections[0]
    generated_schema_path = artifact_path.with_name("artifact.schema.json")
    generated_schema_path.write_text(
        "{}\n" if drift_schema else projection.canonical_json,
        encoding="utf-8",
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
        "PASS: Artifact contracts are valid. Checked 1 artifact file(s).\n"
    )


def test_main_renders_structured_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        drift_schema=True,
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-ARTIFACT-010]" in output
    assert (
        "artifact.schema.json does not match expected "
        "schema generated from artifact.json"
    ) in output


def test_main_renders_registry_boundary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-ARTIFACT-900]" in output
    assert "required registry root not found" in output
