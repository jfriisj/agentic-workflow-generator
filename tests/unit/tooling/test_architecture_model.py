from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agentic_workflow_generator.tooling import architecture_model


def _workspace(root: Path, text: str) -> Path:
    path = root / architecture_model.WORKSPACE_PATH
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_verify_image_metadata_accepts_pinned_artifact() -> None:
    architecture_model._verify_image_metadata(
        {
            "Id": architecture_model.STRUCTURIZR_DIGEST,
            "Os": "linux",
            "Architecture": "amd64",
            "RepoDigests": [
                architecture_model.STRUCTURIZR_IMAGE,
            ],
        }
    )


def test_verify_image_metadata_rejects_wrong_digest() -> None:
    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match="image ID mismatch",
    ):
        architecture_model._verify_image_metadata(
            {
                "Id": "sha256:" + ("0" * 64),
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [
                    architecture_model.STRUCTURIZR_IMAGE,
                ],
            }
        )


def test_structurizr_command_is_offline_and_digest_pinned(
    tmp_path: Path,
) -> None:
    command = architecture_model._structurizr_command(
        ["validate", "-workspace", "workspace.dsl"],
        workdir=tmp_path,
    )

    assert "--network" in command
    assert command[command.index("--network") + 1] == "none"
    assert architecture_model.STRUCTURIZR_IMAGE in command
    assert architecture_model.STRUCTURIZR_TAGGED_IMAGE not in command


def test_source_policy_rejects_remote_url(tmp_path: Path) -> None:
    _workspace(
        tmp_path,
        """workspace {
    !include https://example.com/model.dsl
}
""",
    )

    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match="Remote URL dependency",
    ):
        architecture_model._validate_source_policy(tmp_path)


def test_source_policy_rejects_workspace_extension(
    tmp_path: Path,
) -> None:
    _workspace(
        tmp_path,
        """workspace extends base.dsl {
}
""",
    )

    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match="Workspace extension",
    ):
        architecture_model._validate_source_policy(tmp_path)


def test_source_policy_rejects_manual_workspace_json(
    tmp_path: Path,
) -> None:
    _workspace(
        tmp_path,
        """workspace {
    model {
    }
}
""",
    )
    workspace_json = (
        tmp_path
        / architecture_model.WORKSPACE_DIRECTORY
        / "workspace.json"
    )
    workspace_json.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match=r"workspace\.json",
    ):
        architecture_model._validate_source_policy(tmp_path)


def test_expected_view_keys_are_enforced() -> None:
    payload = {
        "views": {
            "systemContextViews": [
                {"key": "SystemContext"},
            ],
            "containerViews": [],
        }
    }

    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match="CompilerResponsibilities",
    ):
        architecture_model._verify_expected_views(payload)


def test_deterministic_export_requires_identical_paths_and_bytes() -> None:
    architecture_model._verify_deterministic_export(
        {
            "structurizr-SystemContext.puml": b"same",
            "structurizr-CompilerResponsibilities.puml": b"same",
        },
        {
            "structurizr-SystemContext.puml": b"same",
            "structurizr-CompilerResponsibilities.puml": b"same",
        },
    )

    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match="not byte-identical",
    ):
        architecture_model._verify_deterministic_export(
            {"structurizr-SystemContext.puml": b"first"},
            {"structurizr-SystemContext.puml": b"second"},
        )


def test_plantuml_export_shape_requires_expected_views_and_keys() -> None:
    exports = {
        name: b"content"
        for name in architecture_model.EXPECTED_EXPORT_FILENAMES
    }
    architecture_model._verify_plantuml_export_shape(exports)

    exports["unexpected.puml"] = b"content"
    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match="export shape changed",
    ):
        architecture_model._verify_plantuml_export_shape(exports)


def test_committed_svg_check_detects_missing_output(tmp_path: Path) -> None:
    rendered = {
        key: f"{key}-svg".encode()
        for key in architecture_model.COMMITTED_SVGS
    }
    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match="SVG drift",
    ):
        architecture_model._verify_committed_svgs(
            root=tmp_path,
            rendered=rendered,
        )


def test_committed_svg_check_accepts_exact_bytes(tmp_path: Path) -> None:
    rendered = {
        key: f"{key}-svg".encode()
        for key in architecture_model.COMMITTED_SVGS
    }
    architecture_model._write_committed_svgs(
        root=tmp_path,
        rendered=rendered,
    )
    architecture_model._verify_committed_svgs(
        root=tmp_path,
        rendered=rendered,
    )



def test_unresolved_reference_probe_requires_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def accepted(
        arguments: list[str],
        *,
        workdir: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout="unexpectedly accepted",
        )

    monkeypatch.setattr(
        architecture_model,
        "_run_structurizr",
        accepted,
    )

    with pytest.raises(
        architecture_model.ArchitectureModelError,
        match="unexpectedly accepted",
    ):
        architecture_model._verify_unresolved_reference_fails(tmp_path)


def test_unresolved_reference_probe_accepts_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def rejected(
        arguments: list[str],
        *,
        workdir: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        captured["arguments"] = arguments
        captured["workdir"] = workdir
        return subprocess.CompletedProcess(
            arguments,
            1,
            stdout="unresolved destination",
        )

    monkeypatch.setattr(
        architecture_model,
        "_run_structurizr",
        rejected,
    )

    architecture_model._verify_unresolved_reference_fails(tmp_path)

    assert captured["workdir"] == tmp_path
    assert captured["arguments"] == [
        "validate",
        "-workspace",
        "unresolved-reference.dsl",
    ]
