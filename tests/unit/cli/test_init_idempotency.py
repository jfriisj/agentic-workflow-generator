from __future__ import annotations

import argparse
import runpy
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

import agentic_workflow_generator.cli.init_idempotency as idempotency_module
from agentic_workflow_generator.application import (
    load_initialization_service,
)
from agentic_workflow_generator.cli.init_idempotency import (
    InitIdempotencyError,
    main,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
    tmp_path: Path,
) -> ProjectPaths:
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        tmp_path / "registry",
    )
    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        tmp_path / ".agentic" / "schemas",
    )
    return ProjectPaths(tmp_path)


def test_direct_bundle_idempotency_uses_typed_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--bundle",
            "lean-delivery",
        )
    )

    assert result == 0
    assert paths.active_config.is_file()
    assert not paths.setup_profile.exists()
    assert capsys.readouterr().out == (
        "PASS: Init from bundle is idempotent for bundle "
        "'lean-delivery'. Checked .agentic/agentic.json.\n"
    )


def test_guided_idempotency_checks_both_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--guided",
            "--setup",
            "lean-delivery-greenfield",
        )
    )

    assert result == 0
    assert paths.active_config.is_file()
    assert paths.setup_profile.is_file()
    assert capsys.readouterr().out == (
        "PASS: Guided init is idempotent for setup "
        "'lean-delivery-greenfield'. Checked "
        ".agentic/setup-profile.json and "
        ".agentic/agentic.json.\n"
    )


def test_review_heavy_guided_idempotency_preserves_success_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--guided",
            "--setup",
            "review-heavy-delivery-greenfield",
        )
    )

    assert result == 0
    assert paths.active_config.is_file()
    assert paths.setup_profile.is_file()
    assert capsys.readouterr().out == (
        "PASS: Guided init is idempotent for setup "
        "'review-heavy-delivery-greenfield'. Checked "
        ".agentic/setup-profile.json and "
        ".agentic/agentic.json.\n"
    )


def test_orchestrated_bundle_idempotency_preserves_success_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--bundle",
            "orchestrated-delivery",
        )
    )

    assert result == 0
    assert paths.active_config.is_file()
    assert not paths.setup_profile.exists()
    assert capsys.readouterr().out == (
        "PASS: Init from bundle is idempotent for bundle "
        "'orchestrated-delivery'. Checked "
        ".agentic/agentic.json.\n"
    )


@pytest.mark.parametrize(
    ("arguments", "expected_message"),
    [
        (
            (
                "--guided",
                "--bundle",
                "lean-delivery",
            ),
            "--guided cannot be combined with --bundle",
        ),
        (
            ("--guided",),
            "--guided requires --setup",
        ),
        (
            (
                "--setup",
                "lean-delivery-greenfield",
            ),
            "--setup requires --guided",
        ),
        (
            (),
            "one of --bundle or --guided --setup is required",
        ),
    ],
)
def test_idempotency_cli_rejects_invalid_argument_combinations(
    arguments: tuple[str, ...],
    expected_message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as captured:
        main(arguments)

    assert captured.value.code == 2
    assert expected_message in capsys.readouterr().err


def test_idempotency_cli_reports_application_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--bundle",
            "missing",
        )
    )

    assert result == 1
    assert "unknown bundle" in capsys.readouterr().out


def test_plan_helper_rejects_missing_runtime_arguments(
    tmp_path: Path,
) -> None:
    service = load_initialization_service(copy_repository(tmp_path))

    with pytest.raises(
        InitIdempotencyError,
        match="requires a setup name",
    ):
        idempotency_module._plan(
            service,
            argparse.Namespace(
                guided=True,
                setup=None,
                bundle=None,
            ),
        )

    with pytest.raises(
        InitIdempotencyError,
        match="requires a bundle name",
    ):
        idempotency_module._plan(
            service,
            argparse.Namespace(
                guided=False,
                setup=None,
                bundle=None,
            ),
        )


def test_snapshot_helper_requires_materialized_output(
    tmp_path: Path,
) -> None:
    service = load_initialization_service(copy_repository(tmp_path))
    plan = service.plan_bundle("lean-delivery")

    with pytest.raises(
        InitIdempotencyError,
        match="output is missing",
    ):
        idempotency_module._snapshot_outputs(
            service,
            plan,
        )


@dataclass(frozen=True)
class FakePlan:
    setup_profile_json: object | None = None


@dataclass(frozen=True)
class FakeCommitResult:
    changed: bool
    written_paths: tuple[Path, ...]


class DriftingInitializationService:
    def __init__(
        self,
        paths: ProjectPaths,
    ) -> None:
        self.paths = paths
        self.calls = 0
        self.plan = FakePlan()

    def plan_bundle(
        self,
        _bundle_name: str,
    ) -> FakePlan:
        return self.plan

    def commit(
        self,
        _plan: FakePlan,
    ) -> FakeCommitResult:
        self.calls += 1
        self.paths.active_config.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.paths.active_config.write_bytes(f"run-{self.calls}".encode())
        changed = self.calls == 2

        return FakeCommitResult(
            changed=changed,
            written_paths=((self.paths.active_config,) if changed else ()),
        )


def test_idempotency_cli_detects_repeated_write_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = ProjectPaths(tmp_path)
    service = DriftingInitializationService(paths)
    monkeypatch.setattr(
        idempotency_module,
        "load_initialization_service",
        lambda _paths: service,
    )

    result = main(
        (
            "--bundle",
            "lean-delivery",
        )
    )

    assert result == 1
    assert "repeated initialization changed output" in (capsys.readouterr().out)


def test_init_idempotency_module_entrypoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "init_idempotency.py",
            "--bundle",
            "lean-delivery",
        ],
    )

    with pytest.raises(SystemExit) as captured:
        runpy.run_path(
            str(
                REPOSITORY_ROOT
                / "src"
                / "agentic_workflow_generator"
                / "cli"
                / "init_idempotency.py"
            ),
            run_name="__main__",
        )

    assert captured.value.code == 0
