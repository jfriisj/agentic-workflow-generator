from pathlib import Path

import pytest

from agentic_workflow_generator.cli.setup_profiles import main
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SETUP_SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "setup.schema.json"
)
PROFILE_SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "setup-profile.schema.json"
)


def write_object(
    root: Path,
    relative_path: str,
    data: JsonObject,
) -> None:
    path = root / relative_path
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(path, data)


def setup_data(
    *,
    name: str = "lean-delivery-greenfield",
) -> JsonObject:
    return {
        "name": name,
        "description": "Focused guided setup.",
        "version": "0.2.0",
        "mode": "greenfield",
        "defaultSelection": {
            "bundle": "lean-delivery",
            "targets": [
                "opencode",
            ],
        },
        "questions": [
            {
                "id": "delivery-style",
                "prompt": "How should delivery be controlled?",
                "defaultOption": "lean",
                "options": [
                    {
                        "value": "lean",
                        "label": "Lean",
                        "classification": "recommended",
                        "reason": ("Lean delivery is appropriate."),
                        "selection": {
                            "bundle": "lean-delivery",
                        },
                    },
                    {
                        "value": "unsafe",
                        "label": "Unsafe",
                        "classification": "blocked",
                        "reason": "Unsafe delivery is blocked.",
                    },
                ],
            },
        ],
    }


def profile_data(
    *,
    selected_option: str = "lean",
    classification: str = "recommended",
    reason: str = "Lean delivery is appropriate.",
) -> JsonObject:
    return {
        "$schema": "./schemas/setup-profile.schema.json",
        "schemaVersion": "0.2.0",
        "mode": "greenfield",
        "setup": "lean-delivery-greenfield",
        "answers": [
            {
                "question": "delivery-style",
                "selected": selected_option,
                "classification": classification,
                "reason": reason,
            },
        ],
        "selected": {
            "bundle": "lean-delivery",
            "targets": [
                "opencode",
            ],
        },
        "policy": {
            "failFast": True,
            "fallbackAllowed": False,
        },
    }


def create_repository(
    root: Path,
    *,
    setup_name: str = "lean-delivery-greenfield",
    bundle_targets: list[JsonValue] | None = None,
    profile: JsonObject | None = None,
) -> None:
    setup_schema_target = (
        root / ".agentic" / "schemas" / "registry" / "setup.schema.json"
    )
    setup_schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    setup_schema_target.write_text(
        SETUP_SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    profile_schema_target = root / ".agentic" / "schemas" / "setup-profile.schema.json"
    profile_schema_target.write_text(
        PROFILE_SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    write_object(
        root,
        "registry/setups/lean-delivery-greenfield.setup.json",
        setup_data(name=setup_name),
    )
    write_object(
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
    write_object(
        root,
        "registry/targets/opencode/adapter.json",
        {
            "name": "opencode",
        },
    )
    write_object(
        root,
        ".agentic/setup-profile.json",
        profile_data() if profile is None else profile,
    )


def test_main_preserves_success_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(())

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Setup profile is valid: .agentic/setup-profile.json\n"
    )


def test_main_accepts_explicit_profile_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(tmp_path)
    custom_path = tmp_path / "custom-profile.json"
    custom_path.write_text(
        (tmp_path / ".agentic/setup-profile.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = main((str(custom_path),))

    assert result == 0
    assert capsys.readouterr().out == (f"PASS: Setup profile is valid: {custom_path}\n")


def test_main_renders_profile_semantic_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        profile=profile_data(
            selected_option="unsafe",
            classification="recommended",
            reason="Unsafe delivery is blocked.",
        ),
    )
    monkeypatch.chdir(tmp_path)

    result = main(())
    output = capsys.readouterr().out

    assert result == 1
    assert "FAIL: Setup profile validation found 1 error(s)." in output
    assert "[AWG-SETUP-PROFILE-009]" in output
    assert "selects blocked option 'unsafe'" in output


def test_main_rejects_invalid_setup_registry_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        setup_name="different",
    )
    monkeypatch.chdir(tmp_path)

    result = main(())
    output = capsys.readouterr().out

    assert result == 1
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

    result = main(())
    output = capsys.readouterr().out

    assert result == 1
    assert "[AWG-SETUP-PROFILE-900]" in output
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

    result = main(())
    output = capsys.readouterr().out

    assert result == 1
    assert "[AWG-SETUP-PROFILE-900]" in output
    assert "targets must be a non-empty list" in output
