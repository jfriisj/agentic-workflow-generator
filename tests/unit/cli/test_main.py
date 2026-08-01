from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from agentic_workflow_generator.cli import main as command
from agentic_workflow_generator.infrastructure import ProcessResult


def test_help_uses_installed_public_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = command.main(["--help"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    assert captured.out.startswith(
        "Usage:\n"
        "  agentic-workflow-generator validate-environment\n"
    )
    assert "scripts/agentic" not in captured.out


def test_unknown_command_fails_closed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = command.main(["unknown"])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.err == "ERROR: Unknown command: unknown\n"
    assert captured.out.startswith("Usage:\n")


def test_route_forwards_arguments_only_to_argument_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, ...]] = []

    def routed(argv: Sequence[str]) -> int:
        observed.append(tuple(argv))
        return 7

    monkeypatch.setitem(
        command.COMMANDS,
        "init",
        routed,
    )

    result = command.main(
        [
            "init",
            "--bundle",
            "orchestrated-delivery",
        ]
    )

    assert result == 7
    assert observed == [
        (
            "--bundle",
            "orchestrated-delivery",
        )
    ]


def test_argumentless_route_rejects_extra_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = command.main(
        [
            "validate",
            "unexpected",
        ]
    )

    captured = capsys.readouterr()
    assert result == 2
    assert (
        "Command 'validate' does not accept arguments"
        in captured.err
    )


def test_pipeline_is_fail_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []

    def first(argv: Sequence[str]) -> int:
        assert not argv
        observed.append("first")
        return 0

    def failing(argv: Sequence[str]) -> int:
        assert not argv
        observed.append("failing")
        return 9

    def unreachable(argv: Sequence[str]) -> int:
        assert not argv
        observed.append("unreachable")
        return 0

    monkeypatch.setattr(
        command,
        "PIPELINE_STEPS",
        (
            ("first", first),
            ("failing", failing),
            ("unreachable", unreachable),
        ),
    )

    result = command._run_pipeline([])

    assert result == 9
    assert observed == [
        "first",
        "failing",
    ]


def test_generate_runs_canonical_generation_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []

    def step(name: str) -> command.Command:
        def run(argv: Sequence[str]) -> int:
            assert not argv
            observed.append(name)
            return 0

        return run

    monkeypatch.setattr(
        command,
        "GENERATION_STEPS",
        (
            ("lock", step("lock")),
            (
                "validate-lockfile",
                step("validate-lockfile"),
            ),
            (
                "materialize-targets",
                step("materialize-targets"),
            ),
            (
                "validate-generated",
                step("validate-generated"),
            ),
        ),
    )

    result = command._run_generate([])

    assert result == 0
    assert observed == [
        "lock",
        "validate-lockfile",
        "materialize-targets",
        "validate-generated",
    ]


def test_verify_stops_before_drift_check_on_pipeline_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drift_checked = False

    monkeypatch.setattr(
        command,
        "_run_pipeline",
        lambda argv: 6,
    )

    def verify_no_drift() -> int:
        nonlocal drift_checked
        drift_checked = True
        return 0

    monkeypatch.setattr(
        command,
        "_verify_no_drift",
        verify_no_drift,
    )

    result = command._run_verify([])

    assert result == 6
    assert drift_checked is False


def test_verify_rejects_unstaged_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = iter(
        (
            ProcessResult(
                executable="/usr/bin/git",
                arguments=("diff", "--quiet"),
                exit_code=1,
                output="",
            ),
            ProcessResult(
                executable="/usr/bin/git",
                arguments=(
                    "diff",
                    "--cached",
                    "--quiet",
                ),
                exit_code=0,
                output="",
            ),
        )
    )

    monkeypatch.setattr(
        command,
        "_run_external",
        lambda name, arguments: next(calls),
    )
    monkeypatch.setattr(
        command,
        "_git_status",
        lambda: " M generated.txt",
    )

    result = command._verify_no_drift()

    captured = capsys.readouterr()
    assert result == 1
    assert "Generated output drift detected" in captured.err
    assert (
        "uv run agentic-workflow-generator all"
        in captured.err
    )
    assert " M generated.txt" in captured.err


def test_doctor_is_fail_fast_before_pytest(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest_ran = False

    monkeypatch.setattr(
        command,
        "_run_quiet_verify",
        lambda argv: 4,
    )

    def run_pytest() -> int:
        nonlocal pytest_ran
        pytest_ran = True
        return 0

    monkeypatch.setattr(
        command,
        "_run_pytest",
        run_pytest,
    )

    result = command._run_doctor([])

    assert result == 4
    assert pytest_ran is False
    assert (
        "== Happy path verification =="
        in capsys.readouterr().out
    )


def test_doctor_strict_rejects_dirty_tree_after_doctor(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        command,
        "_run_doctor",
        lambda argv: 0,
    )
    monkeypatch.setattr(
        command,
        "_git_status",
        lambda: " M project-status.md",
    )

    result = command._run_doctor_strict([])

    captured = capsys.readouterr()
    assert result == 1
    assert "Working tree is not clean" in captured.err


def test_status_reports_missing_lockfile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        command,
        "_git_status",
        lambda: "",
    )

    result = command._show_status([])

    captured = capsys.readouterr()
    assert result == 0
    assert "Lockfile:\nmissing\n" in captured.out
    assert captured.out.endswith("Git status:\n")
