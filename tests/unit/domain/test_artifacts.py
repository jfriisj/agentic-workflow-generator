from dataclasses import FrozenInstanceError

import pytest

from agentic_workflow_generator.domain import (
    ArtifactContract,
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
        allowed_statuses=("PASS", "FAIL", "BLOCKED"),
        required_headings=(
            "# Requirements",
            "## Status",
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
