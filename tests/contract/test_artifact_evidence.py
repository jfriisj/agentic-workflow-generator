from pathlib import Path
from typing import Any, cast

from agentic_workflow_generator.infrastructure import read_json_object

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ARTIFACT_TYPES = {
    "AIEvaluationReport",
    "ArchitectureDecision",
    "CodeReview",
    "ImplementationReport",
    "QAReport",
    "Requirements",
    "TestReport",
}
EXPECTED_EVIDENCE = {
    "heading": "## Evidence",
    "requiredFields": [
        "claim",
        "source",
        "reproduction",
        "result",
    ],
}


def test_all_governed_artifacts_match_adr_0007_evidence_contract() -> None:
    artifact_root = REPOSITORY_ROOT / "registry" / "artifacts"
    artifact_paths = tuple(sorted(artifact_root.glob("*/artifact.json")))

    assert {path.parent.name for path in artifact_paths} == EXPECTED_ARTIFACT_TYPES

    for path in artifact_paths:
        artifact = cast(dict[str, Any], read_json_object(path))

        assert artifact["version"] == "0.7.0"
        assert artifact["evidence"] == EXPECTED_EVIDENCE
        assert "## Evidence" in cast(list[str], artifact["requiredHeadings"])
