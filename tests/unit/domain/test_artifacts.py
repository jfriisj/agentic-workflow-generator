from dataclasses import FrozenInstanceError

import pytest

from agentic_workflow_generator.domain import (
    ArtifactContract,
    ArtifactProvenanceContract,
    ArtifactRevisionContract,
    ArtifactStatus,
)


def test_artifact_contract_is_immutable() -> None:
    contract = ArtifactContract(
        type="Requirements",
        version="0.2.0",
        description="Requirements contract.",
        path_pattern="agent-output/requirements/*.md",
        status=ArtifactStatus(
            heading="## Status",
            pattern="PASS|FAIL|BLOCKED",
        ),
        provenance=ArtifactProvenanceContract(
            heading="## Provenance",
            required_identities=(
                "artifactType",
                "artifactVersion",
                "workflow",
                "workflowVersion",
                "roleBinding",
                "agentInstance",
            ),
        ),
        revision=ArtifactRevisionContract(
            heading="## Revision",
            pattern=r"^[1-9][0-9]*$",
        ),
        allowed_statuses=("PASS", "FAIL", "BLOCKED"),
        required_headings=(
            "# Requirements",
            "## Status",
            "## Provenance",
            "## Revision",
        ),
    )

    assert contract.status.heading == "## Status"

    with pytest.raises(FrozenInstanceError):
        contract.type = "Changed"  # type: ignore[misc]


def test_artifact_status_is_immutable() -> None:
    status = ArtifactStatus(
        heading="## Status",
        pattern="PASS|FAIL|BLOCKED",
    )

    with pytest.raises(FrozenInstanceError):
        status.pattern = "PASS"  # type: ignore[misc]


def test_artifact_provenance_contract_is_immutable() -> None:
    provenance = ArtifactProvenanceContract(
        heading="## Provenance",
        required_identities=(
            "artifactType",
            "artifactVersion",
            "workflow",
            "workflowVersion",
            "roleBinding",
            "agentInstance",
        ),
    )

    with pytest.raises(FrozenInstanceError):
        provenance.heading = "Changed"  # type: ignore[misc]


def test_artifact_revision_contract_is_immutable() -> None:
    revision = ArtifactRevisionContract(
        heading="## Revision",
        pattern=r"^[1-9][0-9]*$",
    )

    with pytest.raises(FrozenInstanceError):
        revision.pattern = ".*"  # type: ignore[misc]
