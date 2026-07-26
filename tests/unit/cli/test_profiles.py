import json
from pathlib import Path
from typing import Any

from agentic_workflow_generator.cli import profiles
from agentic_workflow_generator.cli.rendering import render_diagnostic
from agentic_workflow_generator.domain import Diagnostic


def write_json(
    path: Path,
    data: object,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )


def valid_profile() -> dict[str, object]:
    return {
        "name": "lean-delivery",
        "version": "0.2.0",
        "description": "Advisory delivery defaults.",
        "recommendedWorkflow": "lean-delivery",
        "recommendedAgents": [
            "Implementer",
        ],
        "recommendedCapabilities": [
            "implementation.code",
        ],
        "recommendedLanguageProfiles": [
            "language-agnostic",
        ],
        "recommendedRuntimeProfiles": [
            "local",
        ],
    }


def prepare_registry(
    root: Path,
) -> None:
    write_json(
        root / ".agentic/schemas/registry/profile.schema.json",
        json.loads(
            Path(".agentic/schemas/registry/profile.schema.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    write_json(
        root / "registry/profiles/lean-delivery.profile.json",
        valid_profile(),
    )
    write_json(
        root / "registry/workflows/lean-delivery.workflow.json",
        {
            "name": "lean-delivery",
        },
    )
    write_json(
        root / "registry/agents/Implementer/agent.json",
        {
            "name": "Implementer",
        },
    )
    write_json(
        root / "registry/skills/implementation/skill.json",
        {
            "name": "implementation",
            "provides": [
                "implementation.code",
            ],
        },
    )


def test_profile_cli_reports_success(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    prepare_registry(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert profiles.main() == 0

    output = capsys.readouterr().out

    assert (
        "PASS: Profile registry is valid. "
        "Checked 1 profile file(s), "
        "1 recommended agent reference(s), and "
        "1 recommended capability reference(s)."
    ) in output


def test_profile_cli_renders_semantic_diagnostic(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    prepare_registry(tmp_path)
    path = tmp_path / "registry/profiles/lean-delivery.profile.json"
    data = valid_profile()
    data["recommendedWorkflow"] = "missing"
    write_json(path, data)
    monkeypatch.chdir(tmp_path)

    assert profiles.main() == 1

    output = capsys.readouterr().out

    assert "[AWG-PROFILE-005]" in output
    assert "recommendedWorkflow" in output


def test_profile_cli_renders_dependency_failure(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    prepare_registry(tmp_path)
    write_json(
        tmp_path / "registry/skills/implementation/skill.json",
        {
            "name": "implementation",
            "provides": [],
        },
    )
    monkeypatch.chdir(tmp_path)

    assert profiles.main() == 1

    output = capsys.readouterr().out

    assert "[AWG-PROFILE-900]" in output
    assert "provides must be a non-empty list" in output


def test_render_diagnostic_omits_missing_context() -> None:
    rendered = render_diagnostic(
        Diagnostic(
            code="AWG-PROFILE-900",
            message="failure",
        )
    )

    assert rendered == "[AWG-PROFILE-900] failure"
