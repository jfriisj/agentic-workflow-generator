from pathlib import Path

import pytest

from agentic_workflow_generator.cli.setups import main
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "setup.schema.json"
)


def write_registry_object(
    root: Path,
    relative_path: str,
    data: JsonObject,
) -> None:
    path = root / relative_path
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(
        path,
        data,
    )


def setup_data(
    *,
    name: str = "lean-delivery-greenfield",
    bundle: str = "lean-delivery",
) -> JsonObject:
    return {
        "name": name,
        "description": "Focused guided setup.",
        "version": "0.2.0",
        "mode": "greenfield",
        "defaultSelection": {
            "bundle": bundle,
            "targets": [
                "opencode",
            ],
        },
        "questions": [
            {
                "id": "target-platforms",
                "prompt": "Which targets should be generated?",
                "defaultOption": "opencode-only",
                "options": [
                    {
                        "value": "opencode-only",
                        "label": "OpenCode only",
                        "classification": "recommended",
                        "reason": "OpenCode is supported.",
                        "selection": {
                            "targets": [
                                "opencode",
                            ],
                        },
                    },
                    {
                        "value": "unsupported",
                        "label": "Unsupported target",
                        "classification": "blocked",
                        "reason": "The target is unavailable.",
                    },
                ],
            },
        ],
    }


def create_repository(
    root: Path,
    *,
    setup_name: str = "lean-delivery-greenfield",
    setup_bundle: str = "lean-delivery",
    bundle_targets: list[JsonValue] | None = None,
) -> None:
    schema_target = root / ".agentic" / "schemas" / "registry" / "setup.schema.json"
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    write_registry_object(
        root,
        "registry/setups/lean-delivery-greenfield.setup.json",
        setup_data(
            name=setup_name,
            bundle=setup_bundle,
        ),
    )
    write_registry_object(
        root,
        "registry/bundles/lean-delivery.bundle.json",
        {
            "name": "lean-delivery",
            "targets": (
                [
                    "opencode",
                ]
                if bundle_targets is None
                else bundle_targets
            ),
        },
    )
    write_registry_object(
        root,
        "registry/targets/opencode/adapter.json",
        {
            "name": "opencode",
        },
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
        "PASS: Setup registry is valid. Checked 1 setup file(s) and 1 question(s).\n"
    )


def test_main_renders_semantic_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        setup_name="different",
    )
    monkeypatch.chdir(tmp_path)

    result = main()
    output = capsys.readouterr().out

    assert result == 1
    assert "FAIL: Setup registry validation found 1 error(s)." in output
    assert "[AWG-SETUP-003]" in output
    assert (
        "setup name 'different' must match file name "
        "'lean-delivery-greenfield'" in output
    )


def test_main_renders_registry_boundary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main()
    output = capsys.readouterr().out

    assert result == 1
    assert "[AWG-SETUP-900]" in output
    assert "required registry root not found" in output


def test_main_renders_projection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        bundle_targets=[],
    )
    monkeypatch.chdir(tmp_path)

    result = main()
    output = capsys.readouterr().out

    assert result == 1
    assert "[AWG-SETUP-900]" in output
    assert "targets must be a non-empty list" in output
