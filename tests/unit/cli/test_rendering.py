import pytest

from agentic_workflow_generator.cli.rendering import (
    render_diagnostic,
    render_failure,
)
from agentic_workflow_generator.domain import Diagnostic


def test_render_diagnostic_with_all_optional_fields() -> None:
    diagnostic = Diagnostic(
        code="AWG-CLI-001",
        message="broken input",
        source_path="registry/example.json",
        location="field.value",
    )

    assert render_diagnostic(diagnostic) == (
        "[AWG-CLI-001] registry/example.json "
        "field.value broken input"
    )


def test_render_diagnostic_without_optional_fields() -> None:
    diagnostic = Diagnostic(
        code="AWG-CLI-002",
        message="unexpected failure",
    )

    assert render_diagnostic(diagnostic) == (
        "[AWG-CLI-002] unexpected failure"
    )


def test_render_failure_preserves_public_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="AWG-CLI-003",
        message="invalid registry",
    )

    result = render_failure(
        "Example registry",
        (diagnostic,),
    )

    assert result == 1
    assert capsys.readouterr().out == (
        "FAIL: Example registry validation found 1 error(s).\n"
        "  - [AWG-CLI-003] invalid registry\n"
    )
