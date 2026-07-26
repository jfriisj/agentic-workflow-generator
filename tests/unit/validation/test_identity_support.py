from pathlib import Path

from agentic_workflow_generator.validation.identity_support import (
    duplicate_name_diagnostics,
    folder_name_mismatch_diagnostic,
)


def test_folder_name_mismatch_diagnostic() -> None:
    path = Path("registry/agents/Expected/agent.json")

    assert folder_name_mismatch_diagnostic(
        "Expected",
        path,
        "AWG-TEST-001",
    ) is None

    diagnostic = folder_name_mismatch_diagnostic(
        "Actual",
        path,
        "AWG-TEST-001",
    )

    assert diagnostic is not None
    assert diagnostic.code == "AWG-TEST-001"
    assert diagnostic.message == (
        "name 'Actual' does not match folder 'Expected'"
    )
    assert diagnostic.related_identities == (
        "Actual",
        "Expected",
    )


def test_duplicate_name_diagnostics_preserve_first_path() -> None:
    diagnostics = duplicate_name_diagnostics(
        (
            ("alpha", Path("first.json")),
            ("beta", Path("second.json")),
            ("alpha", Path("third.json")),
        ),
        "AWG-TEST-002",
        "agent",
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].message == (
        "agent name 'alpha' is duplicated; "
        "first declared at first.json"
    )
    assert diagnostics[0].source_path == "third.json"
    assert diagnostics[0].related_identities == ("alpha",)
