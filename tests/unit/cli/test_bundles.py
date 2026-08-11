from pathlib import Path

import pytest

from agentic_workflow_generator.cli.bundles import main
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "bundle.schema.json"
)


def _write_registry_object(
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


def bundle_data(
    *,
    name: str = "lean-delivery",
) -> JsonObject:
    return {
        "name": name,
        "description": "Lean delivery bundle.",
        "version": "0.2.0",
        "profile": "lean-delivery",
        "workflow": "lean-delivery",
        "agentInstances": [
            {
                "id": "requirements-worker",
                "profile": "Requirements",
                "displayName": "Requirements",
                "permissionProfile": "read-only",
                "sharedContextPolicy": ("shared-with-assigned-bindings"),
            },
            {
                "id": "workflow-controller",
                "profile": "Orchestrator",
                "displayName": "Orchestrator",
                "permissionProfile": "read-only",
                "sharedContextPolicy": ("shared-with-assigned-bindings"),
            },
        ],
        "roleBindings": [
            {
                "roleName": "requirements",
                "bindingType": "state-owner",
                "agentInstance": "requirements-worker",
                "workflowState": "Requirements",
                "workflowGate": "requirements-review",
                "requiredCapabilities": [
                    "requirements.elicit",
                ],
                "selectedSkills": [
                    "requirements-analysis",
                ],
                "produces": [
                    "Requirements",
                ],
                "inputArtifacts": [],
                "responsibilities": [
                    "Clarify requirements",
                ],
                "guardrails": [
                    "Do not implement",
                ],
            },
            {
                "roleName": "workflow-controller",
                "bindingType": "workflow-controller",
                "agentInstance": "workflow-controller",
                "requiredCapabilities": [
                    "workflow.route",
                ],
                "selectedSkills": [
                    "workflow-routing",
                ],
                "produces": [],
                "inputArtifacts": [],
                "responsibilities": [
                    "Route work",
                ],
                "guardrails": [
                    "Do not override gates",
                ],
            },
        ],
        "separationPolicies": [
            {
                "id": "role-independence",
                "mode": "required",
                "roleBindings": [
                    "requirements",
                    "workflow-controller",
                ],
                "requireDistinctInstances": True,
                "reason": ("Routing authority must remain independent."),
            }
        ],
        "skills": [
            "requirements-analysis",
            "workflow-routing",
        ],
        "artifacts": [
            "Requirements",
        ],
        "targets": [
            "opencode",
        ],
    }


def create_repository(
    root: Path,
    *,
    bundle_name: str = "lean-delivery",
    skill_provides: list[JsonValue] | None = None,
) -> None:
    schema_target = root / ".agentic" / "schemas" / "registry" / "bundle.schema.json"
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    _write_registry_object(
        root,
        ("registry/bundles/lean-delivery.bundle.json"),
        bundle_data(name=bundle_name),
    )
    _write_registry_object(
        root,
        ("registry/profiles/lean-delivery.profile.json"),
        {
            "name": "lean-delivery",
        },
    )
    _write_registry_object(
        root,
        ("registry/workflows/lean-delivery.workflow.json"),
        {
            "name": "lean-delivery",
            "states": [
                {
                    "name": "Requirements",
                    "gate": {
                        "name": ("requirements-review"),
                        "requiredCapabilities": [
                            "requirements.elicit",
                        ],
                        "requiredArtifacts": [
                            "Requirements",
                        ],
                    },
                },
                {
                    "name": "Done",
                    "terminal": True,
                },
            ],
        },
    )
    _write_registry_object(
        root,
        ("registry/agents/Requirements/agent.json"),
        {
            "name": "Requirements",
        },
    )
    _write_registry_object(
        root,
        ("registry/agents/Orchestrator/agent.json"),
        {
            "name": "Orchestrator",
        },
    )
    _write_registry_object(
        root,
        ("registry/skills/requirements-analysis/skill.json"),
        {
            "name": "requirements-analysis",
            "provides": (
                [
                    "requirements.elicit",
                ]
                if skill_provides is None
                else skill_provides
            ),
            "requiresCapabilities": [],
        },
    )
    _write_registry_object(
        root,
        ("registry/skills/workflow-routing/skill.json"),
        {
            "name": "workflow-routing",
            "provides": [
                "workflow.route",
            ],
            "requiresCapabilities": [],
        },
    )
    _write_registry_object(
        root,
        ("registry/artifacts/Requirements/artifact.json"),
        {
            "type": "Requirements",
        },
    )
    _write_registry_object(
        root,
        ("registry/permission-profiles/read-only/permission-profile.json"),
        {
            "name": "read-only",
        },
    )
    _write_registry_object(
        root,
        ("registry/targets/opencode/adapter.json"),
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
        "PASS: Bundle registry is valid. "
        "Checked 1 bundle file(s), "
        "2 agent instance(s), "
        "2 role binding(s), and "
        "1 separation policy file entry(ies).\n"
    )


def test_main_renders_semantic_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        bundle_name="different",
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out

    assert result == 1
    assert "FAIL: Bundle registry validation found 1 error(s)." in output
    assert "[AWG-BUNDLE-003]" in output
    assert "name 'different' does not match file name 'lean-delivery'" in output


def test_main_renders_registry_boundary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out

    assert result == 1
    assert "[AWG-BUNDLE-900]" in output
    assert "required registry root not found" in output


def test_main_renders_projection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        skill_provides=[],
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out

    assert result == 1
    assert "[AWG-BUNDLE-900]" in output
    assert "provides must be a non-empty list" in output
