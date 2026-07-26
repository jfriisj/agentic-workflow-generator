from dataclasses import FrozenInstanceError

import pytest

from agentic_workflow_generator.domain import (
    Diagnostic,
    Severity,
)


def test_diagnostic_accepts_structured_values() -> None:
    diagnostic = Diagnostic(
        code="AWG-BUNDLE-014",
        message="Artifact contract does not exist",
        source_path=("registry/bundles/example.bundle.json"),
        location="roleBindings[2].produces",
        related_identities=("ExampleBinding", "MissingArtifact"),
    )

    assert diagnostic.code == "AWG-BUNDLE-014"
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.related_identities == (
        "ExampleBinding",
        "MissingArtifact",
    )


@pytest.mark.parametrize(
    "code",
    [
        "",
        "BUNDLE-014",
        "AWG-bundle-014",
        "AWG-BUNDLE",
        "AWG-BUNDLE-14",
        "AWG-BUNDLE-0014",
    ],
)
def test_diagnostic_rejects_invalid_codes(code: str) -> None:
    with pytest.raises(
        ValueError,
        match="Diagnostic code must match",
    ):
        Diagnostic(code=code, message="Invalid input")


@pytest.mark.parametrize(
    "message",
    [
        "",
        " ",
        " leading",
        "trailing ",
    ],
)
def test_diagnostic_rejects_invalid_messages(
    message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Diagnostic message",
    ):
        Diagnostic(
            code="AWG-TEST-001",
            message=message,
        )


def test_diagnostic_rejects_duplicate_identities() -> None:
    with pytest.raises(
        ValueError,
        match="Related identities must be unique",
    ):
        Diagnostic(
            code="AWG-TEST-002",
            message="Duplicate identities",
            related_identities=("Agent", "Agent"),
        )


def test_diagnostic_is_immutable() -> None:
    diagnostic = Diagnostic(
        code="AWG-TEST-003",
        message="Immutable diagnostic",
    )

    with pytest.raises(FrozenInstanceError):
        diagnostic.message = "Changed"  # type: ignore[misc]


def test_diagnostic_rejects_invalid_source_path() -> None:
    with pytest.raises(
        ValueError,
        match="Diagnostic source_path",
    ):
        Diagnostic(
            code="AWG-TEST-004",
            message="Invalid source path",
            source_path=" registry/agents/example.json",
        )


def test_diagnostic_rejects_invalid_location() -> None:
    with pytest.raises(
        ValueError,
        match="Diagnostic location",
    ):
        Diagnostic(
            code="AWG-TEST-005",
            message="Invalid location",
            location="roleBindings[0] ",
        )


@pytest.mark.parametrize(
    "identity",
    [
        "",
        " ",
        " Agent",
        "Agent ",
    ],
)
def test_diagnostic_rejects_invalid_related_identity(
    identity: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Related identities must be non-empty and trimmed",
    ):
        Diagnostic(
            code="AWG-TEST-005",
            message="Invalid identity",
            related_identities=(identity,),
        )
