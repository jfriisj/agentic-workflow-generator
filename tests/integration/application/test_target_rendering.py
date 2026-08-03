from __future__ import annotations

import json
from pathlib import Path

from agentic_workflow_generator.application.target_materialization import (
    load_active_composition,
)
from agentic_workflow_generator.application.target_rendering import (
    render_enabled_targets,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def rendered_files(
    target_name: str,
) -> dict[Path, bytes]:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    targets = render_enabled_targets(
        paths,
        active.composition,
    )
    target = next(
        item
        for item in targets
        if item.name == target_name
    )
    return {
        file.path: file.content
        for file in target.files
    }


def test_opencode_uses_agent_instance_identity() -> None:
    files = rendered_files("opencode")

    assert (
        Path(".opencode/agents/workflow-controller.md")
        in files
    )
    assert (
        Path(".opencode/agents/requirements-worker.md")
        in files
    )
    assert Path(".opencode/agents/orchestrator.md") not in files

    config = json.loads(
        files[Path("opencode.json")].decode("utf-8")
    )
    assert config["default_agent"] == "workflow-controller"

    controller = files[
        Path(".opencode/agents/workflow-controller.md")
    ].decode("utf-8")
    assert "# Orchestrator" in controller
    assert "agent instance: `workflow-controller`" in controller
    assert ".agentic/agentic.json" in controller
    assert "resolution.json" not in controller


def test_vscode_handoffs_use_agent_instance_identity() -> None:
    files = rendered_files("vscode-copilot")
    controller_path = Path(
        ".github/agents/workflow-controller.agent.md"
    )

    assert controller_path in files
    assert (
        Path(".github/agents/orchestrator.agent.md")
        not in files
    )

    controller = files[controller_path].decode("utf-8")
    assert 'name: "workflow-controller"' in controller
    assert 'agent: "requirements-worker"' in controller
    assert "resolution.json" not in controller


def test_rendered_artifact_headings_are_nested() -> None:
    files = rendered_files("opencode")
    requirements = files[
        Path(".opencode/agents/requirements-worker.md")
    ].decode("utf-8")

    assert (
        "- required headings:\n"
        "  - # Requirements\n"
        "  - ## Status\n"
        "  - ## Provenance\n"
        "  - ## Revision\n"
        "  - ## Summary\n"
    ) in requirements
    assert (
        "- required headings:\n\n- # Requirements"
        not in requirements
    )


def test_rendered_targets_copy_compiled_skills() -> None:
    for target_name, skill_root in (
        ("opencode", Path(".opencode/skills")),
        (
            "vscode-copilot",
            Path(".github/skills"),
        ),
    ):
        files = rendered_files(target_name)

        assert (
            skill_root
            / "workflow-routing"
            / "SKILL.md"
        ) in files
        assert (
            skill_root
            / "workflow-routing"
            / "skill.json"
        ) in files


def test_every_rendered_file_is_target_owned() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)

    for target in render_enabled_targets(
        paths,
        active.composition,
    ):
        owned = tuple(
            Path(path)
            for path in target.owned_paths
        )

        assert target.files

        for file in target.files:
            assert any(
                file.path == root
                or file.path.is_relative_to(root)
                for root in owned
            )


def test_rendered_provenance_uses_compiled_production_identity() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    production = next(
        item
        for item in active.composition.artifact_production
        if item.artifact.type == "Requirements"
    )

    expected_lines = (
        "- provenance heading: `## Provenance`",
        "  - `artifactType`: `Requirements`",
        f"  - `artifactVersion`: `{production.artifact.version}`",
        f"  - `workflow`: `{active.composition.workflow.name}`",
        (
            "  - `workflowVersion`: "
            f"`{active.composition.workflow.version}`"
        ),
        f"  - `roleBinding`: `{production.role_binding}`",
        f"  - `agentInstance`: `{production.agent_instance}`",
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        for expected in expected_lines:
            assert expected in content


def test_rendered_revision_uses_compiled_artifact_contract() -> None:
    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        assert "- revision heading: `## Revision`" in content
        assert (
            "- revision entry: `revision: <N>` where `<N>` matches "
            "`^[1-9][0-9]*$`"
        ) in content



def test_rendered_status_invariants_use_compiled_artifact_contract() -> None:
    expected_lines = (
        "- status invariants:",
        "  - `passRequiresCompleteEvidence`: `true`",
        "  - `passForbidsDemonstratedNonconformance`: `true`",
        "  - `failRequiresDemonstratedNonconformance`: `true`",
        "  - `blockedRequiresUnavailablePrerequisite`: `true`",
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        for expected in expected_lines:
            assert expected in content

def test_rendered_status_semantics_use_compiled_artifact_contract() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    production = next(
        item
        for item in active.composition.artifact_production
        if item.artifact.type == "Requirements"
    )
    semantics = production.artifact.status_semantics
    expected_lines = (
        "- status semantics:",
        f"  - `PASS`: {semantics.pass_definition}",
        f"  - `FAIL`: {semantics.fail_definition}",
        f"  - `BLOCKED`: {semantics.blocked_definition}",
        (
            "  - `mixedConditionRule`: "
            f"`{semantics.mixed_condition_rule}`"
        ),
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        for expected in expected_lines:
            assert expected in content

        assert (
            "Missing required evidence alone must result in `BLOCKED`; "
            "demonstrated nonconformance remains governed by the artifact contract."
        ) in content
