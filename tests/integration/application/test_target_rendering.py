from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agentic_workflow_generator.application import (
    load_validated_registry_snapshot,
)
from agentic_workflow_generator.application.target_materialization import (
    load_active_composition,
)
from agentic_workflow_generator.application.target_rendering import (
    TargetRenderingError,
    render_enabled_targets,
)
from agentic_workflow_generator.compiler import (
    CompiledComposition,
    ProjectMetadata,
    compile_bundle_composition,
)
from agentic_workflow_generator.domain import BashPermission
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def compiled_bundle(bundle_name: str) -> CompiledComposition:
    paths = ProjectPaths(REPOSITORY_ROOT)
    snapshot = load_validated_registry_snapshot(paths)
    project = ProjectMetadata(
        name="consumer-project",
        project_type="agentic-project",
        description="Generated target-rendering test configuration.",
        language_profiles=("python",),
        runtime_profiles=("python",),
        architecture_profile="typed-composition",
    )
    return compile_bundle_composition(
        snapshot,
        project,
        bundle_name,
    )


def rendered_bundle_files(
    bundle_name: str,
    target_name: str,
) -> dict[Path, bytes]:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle(bundle_name)
    targets = render_enabled_targets(paths, composition)
    target = next(
        item
        for item in targets
        if item.name == target_name
    )
    return {
        file.path: file.content
        for file in target.files
    }


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
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
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

    state_owner_instances = {
        ownership.agent_instance
        for ownership in active.composition.state_ownership
    }

    for instance in state_owner_instances:
        state_owner = files[
            Path(f".github/agents/{instance}.agent.md")
        ].decode("utf-8")
        assert "handoffs:" not in state_owner


def test_vscode_controller_owns_every_non_terminal_route_handoff() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    files = rendered_files("vscode-copilot")
    controller = files[
        Path(".github/agents/workflow-controller.agent.md")
    ].decode("utf-8")
    owners = {
        ownership.workflow_state: ownership.agent_instance
        for ownership in active.composition.state_ownership
    }
    non_terminal_routes = tuple(
        sorted(
            (
                transition.source,
                transition.result.name,
                transition.result.value,
                transition.target,
                owners[transition.target],
            )
            for transition in active.composition.workflow.transitions
            if transition.target in owners
        )
    )

    labels: list[str] = []

    for source, result_name, result_value, target, owner in non_terminal_routes:
        label = (
            f"Route {source} + {result_name} ({result_value}) -> {target}"
        )
        prompt = (
            f"Current state: {source}. Canonical result: {result_name} "
            f"({result_value}). Dispatch the owner of selected target state "
            f"{target}; do not infer, prioritize, or reclassify the route."
        )
        handoff = (
            f'  - label: "{label}"\n'
            f'    agent: "{owner}"\n'
            f'    prompt: "{prompt}"\n'
            "    send: false"
        )

        assert handoff in controller
        labels.append(label)

    assert controller.count("  - label:") == len(non_terminal_routes) + 1
    assert [controller.index(f'label: "{label}"') for label in labels] == sorted(
        controller.index(f'label: "{label}"') for label in labels
    )

    for transition in active.composition.workflow.transitions:
        if transition.target not in active.composition.workflow.terminal_states:
            continue

        terminal_label = (
            f"Route {transition.source} + {transition.result.name} "
            f"({transition.result.value}) -> {transition.target}"
        )
        assert terminal_label not in controller


def test_both_targets_preserve_controller_owned_routing() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    expected_routes = tuple(
        sorted(
            (
                transition.source,
                transition.result.name,
                transition.result.value,
                transition.target,
            )
            for transition in active.composition.workflow.transitions
        )
    )

    for target_name, controller_path, owner_path in (
        (
            "opencode",
            Path(".opencode/agents/workflow-controller.md"),
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/workflow-controller.agent.md"),
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        files = rendered_files(target_name)
        controller = files[controller_path].decode("utf-8")
        owner = files[owner_path].decode("utf-8")

        assert "This controller is the sole routing authority." in controller
        assert "- start state: `Requirements`" in controller
        assert "- terminal states: `Done`, `Blocked`" in controller
        assert "- default failure state: `Blocked`" in controller
        assert "`PASS` (`pass`), `FAIL` (`fail`), `BLOCKED` (`blocked`)" in controller

        for source, result_name, result_value, target in expected_routes:
            assert (
                f"- `{source}` + `{result_name}` (`{result_value}`) -> `{target}`"
                in controller
            )

        assert "Return that result and control to the workflow controller." in owner
        assert "Do not select or execute a workflow route." in owner
        assert "Canonical routing table:" not in owner


def test_rendering_rejects_incomplete_canonical_routing() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    workflow = active.composition.workflow
    incomplete = replace(
        active.composition,
        workflow=replace(
            workflow,
            transitions=tuple(
                transition
                for transition in workflow.transitions
                if not (
                    transition.source == "Requirements"
                    and transition.result.value == "pass"
                )
            ),
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="must have exactly one 'pass' route",
    ):
        render_enabled_targets(paths, incomplete)


def test_rendering_rejects_missing_state_ownership() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    missing_owner = replace(
        active.composition,
        state_ownership=tuple(
            ownership
            for ownership in active.composition.state_ownership
            if ownership.workflow_state != "Requirements"
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="must have exactly one compiled owner",
    ):
        render_enabled_targets(paths, missing_owner)


def test_rendering_rejects_missing_controller_instance() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    missing_controller = replace(
        active.composition,
        role_bindings=tuple(
            replace(binding, agent_instance="missing-controller")
            if binding.role_name == active.composition.controller_binding
            else binding
            for binding in active.composition.role_bindings
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="is not a rendered agent instance",
    ):
        render_enabled_targets(paths, missing_controller)




def test_rendered_required_inputs_use_compiled_production_identity() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    implementation = next(
        binding
        for binding in active.composition.role_bindings
        if binding.role_name == "implementation"
    )

    assert tuple(
        (
            production.artifact.type,
            production.role_binding,
            production.agent_instance,
        )
        for production in implementation.input_artifacts
    ) == (
        (
            "ArchitectureDecision",
            "architecture",
            "architecture-worker",
        ),
        (
            "Requirements",
            "requirements",
            "requirements-worker",
        ),
    )

    expected_lines = tuple(
        (
            f"`artifactType`: `{production.artifact.type}`; "
            f"producer `roleBinding`: `{production.role_binding}`; "
            f"resolved `agentInstance`: `{production.agent_instance}`"
        )
        for production in implementation.input_artifacts
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/implementation-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(
                ".github/agents/"
                "implementation-worker.agent.md"
            ),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        assert "## Required Input Artifacts" in content
        assert "### implementation" in content
        for expected in expected_lines:
            assert expected in content


def test_rendered_controller_has_no_governed_inputs() -> None:
    expected = (
        "### workflow-controller\n\n"
        "This role binding has no required static input artifacts."
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/workflow-controller.md"),
        ),
        (
            "vscode-copilot",
            Path(
                ".github/agents/"
                "workflow-controller.agent.md"
            ),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        assert "## Required Input Artifacts" in content
        assert expected in content


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
        "  - ## Evidence\n"
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



def test_rendered_evidence_uses_compiled_artifact_contract() -> None:
    expected_lines = (
        "- evidence heading: `## Evidence`",
        "- evidence required fields:",
        "  - claim",
        "  - source",
        "  - reproduction",
        "  - result",
        "- evidence semantics:",
        (
            "  - record one or more reproducible evidence records "
            "for status-determining conditions"
        ),
        (
            "  - cover every status-determining condition used to "
            "classify the artifact"
        ),
        (
            "  - keep materially independent conditions "
            "independently reproducible"
        ),
        (
            "  - evidence records supply observations; they do not "
            "define artifact status policy"
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
def test_both_targets_preserve_compiled_test_evidence_semantics() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    gate = next(
        gate
        for gate in active.composition.workflow_gates
        if any(
            artifact.type == "TestReport"
            for artifact in gate.required_artifacts
        )
    )

    expected_categories = (
        "changed-behavior-tests",
        "project-validation-suite",
    )
    assert tuple(
        requirement.value
        for requirement in gate.required_test_evidence
    ) == expected_categories

    expected_meanings = (
        (
            "`changed-behavior-tests`: repository-authoritative validation "
            "directly exercises the approved changed behavior"
        ),
        (
            "`project-validation-suite`: repository-authoritative broader "
            "regression/validation suite applicable to the project"
        ),
    )
    expected_common = (
        f"### {gate.name}",
        f"- workflow state: `{gate.workflow_state}`",
        (
            "- gate owner: role binding "
            f"`{gate.owner_role_binding}`; agent instance "
            f"`{gate.owner_agent_instance}`"
        ),
        (
            "- required test evidence: every category below is "
            "independently required"
        ),
        *expected_meanings,
        (
            "- static/runtime boundary: required categories come only "
            "from this compiled gate"
        ),
        (
            "- do not infer required categories from skill or project "
            "prose"
        ),
        "- do not invent required observations",
        (
            "- routing boundary: the state owner returns the "
            "already-classified canonical result"
        ),
    )

    for target_name, owner_path, instructions_path in (
        (
            "opencode",
            Path(
                ".opencode/agents/"
                f"{gate.owner_agent_instance}.md"
            ),
            Path("AGENTS.md"),
        ),
        (
            "vscode-copilot",
            Path(
                ".github/agents/"
                f"{gate.owner_agent_instance}.agent.md"
            ),
            Path(".github/copilot-instructions.md"),
        ),
    ):
        files = rendered_files(target_name)
        owner = files[owner_path].decode("utf-8")
        instructions = files[instructions_path].decode("utf-8")

        for expected in expected_common:
            assert expected in owner

        for category, meaning in zip(
            expected_categories,
            expected_meanings,
            strict=True,
        ):
            assert (
                f"{meaning}; provide independently reproducible "
                "`TestReport` evidence"
            ) in owner
            assert f"`{category}`" in instructions

        assert (
            "`claim`, `source`, `reproduction`, and `result` fields"
        ) in owner
        assert (
            "the compiler and target adapter do not discover or execute tests"
        ) in owner
        assert (
            "classify `TestReport` only under its compiled `PASS`, `FAIL`, "
            "and `BLOCKED` evidence/status contract"
        ) in owner


def test_rendering_rejects_lost_required_test_evidence() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    gate = next(
        gate
        for gate in active.composition.workflow_gates
        if any(
            artifact.type == "TestReport"
            for artifact in gate.required_artifacts
        )
    )
    broken_gate = replace(
        gate,
        required_test_evidence=(),
    )
    broken = replace(
        active.composition,
        workflow_gates=tuple(
            broken_gate if item is gate else item
            for item in active.composition.workflow_gates
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="must preserve non-empty required test evidence",
    ):
        render_enabled_targets(paths, broken)


def test_non_test_report_gate_renders_no_test_evidence() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    gate = next(
        gate
        for gate in active.composition.workflow_gates
        if all(
            artifact.type != "TestReport"
            for artifact in gate.required_artifacts
        )
    )

    for target_name, owner_path in (
        (
            "opencode",
            Path(
                ".opencode/agents/"
                f"{gate.owner_agent_instance}.md"
            ),
        ),
        (
            "vscode-copilot",
            Path(
                ".github/agents/"
                f"{gate.owner_agent_instance}.agent.md"
            ),
        ),
    ):
        owner = rendered_files(target_name)[owner_path].decode("utf-8")
        section_start = owner.index(f"### {gate.name}")
        next_heading = owner.find("\n### ", section_start + 1)
        section_end = next_heading if next_heading != -1 else len(owner)
        section = owner[section_start:section_end]

        assert "- required test evidence: none" in section
        assert "`changed-behavior-tests`" not in section
        assert "`project-validation-suite`" not in section


def test_both_targets_preserve_compiled_ai_evaluation_semantics() -> None:
    composition = compiled_bundle("ai-application")
    gate = next(
        gate
        for gate in composition.workflow_gates
        if any(
            artifact.type == "AIEvaluationReport"
            for artifact in gate.required_artifacts
        )
    )
    binding = next(
        binding
        for binding in composition.role_bindings
        if binding.role_name == gate.owner_role_binding
    )
    instance = next(
        instance
        for instance in composition.agent_instances
        if instance.id == gate.owner_agent_instance
    )

    assert gate.required_capabilities == (
        "ai.evaluate-quality",
        "ai.evaluate-safety",
        "ai.evaluate-operational-risks",
    )
    assert tuple(
        production.artifact.type
        for production in binding.input_artifacts
    ) == (
        "ImplementationReport",
        "Requirements",
    )
    assert instance.permission_profile.read is True
    assert instance.permission_profile.write is False
    assert instance.permission_profile.edit is False
    assert instance.permission_profile.bash is BashPermission.DENY

    expected_common = (
        "required AI-evaluation dimensions",
        "governed runtime inputs",
        "`ImplementationReport`",
        "`Requirements`",
        "AIEvaluationReport` is the sole evidence and status authority",
        "`claim`, `source`, `reproduction`, `result`",
        "map every status-determining required criterion reproducibly",
        "relevant compiled AI-evaluation capability dimension",
        "complete reproducible evidence satisfying all applicable required criteria",
        "may support `PASS`",
        "read=`true`; write=`false`; edit=`false`; bash=`deny`",
        "do not run shell commands",
        "execute external evaluation jobs",
        "invoke a model-under-test merely to generate missing evidence",
        "prevents `PASS` and yields `BLOCKED`",
        "demonstrated nonconformance yields `FAIL`",
        "outside the effective permission profile",
        "the evaluation cannot be `PASS`",
        "`FAIL_ON_DEMONSTRATED_NONCONFORMANCE`",
        "do not parse produced artifact Markdown or project files",
        "only the controller selects the route",
        "## Evaluation Scope",
        "## Safety and Failure Analysis",
        "## Operational Evidence",
    )

    for target_name, owner_path in (
        (
            "opencode",
            Path(".opencode/agents/ai-evaluation-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(
                ".github/agents/"
                "ai-evaluation-worker.agent.md"
            ),
        ),
    ):
        content = rendered_bundle_files(
            "ai-application",
            target_name,
        )[owner_path].decode("utf-8")

        assert f"### {gate.name}" in content
        for capability in gate.required_capabilities:
            assert f"  - `{capability}`" in content
        for expected in expected_common:
            assert expected in content


def test_ai_evaluation_semantics_do_not_infer_from_responsibility_prose() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle("ai-application")
    gate = next(
        gate
        for gate in composition.workflow_gates
        if any(
            artifact.type == "AIEvaluationReport"
            for artifact in gate.required_artifacts
        )
    )
    instance = next(
        instance
        for instance in composition.agent_instances
        if instance.id == gate.owner_agent_instance
    )

    def ai_gate_section(candidate: CompiledComposition) -> str:
        target = next(
            item
            for item in render_enabled_targets(paths, candidate)
            if item.name == "opencode"
        )
        owner = next(
            file.content.decode("utf-8")
            for file in target.files
            if file.path
            == Path(".opencode/agents/ai-evaluation-worker.md")
        )
        section_start = owner.index(f"### {gate.name}")
        section_end = owner.index(
            "\n## Workflow Authority",
            section_start,
        )
        return owner[section_start:section_end]

    baseline_section = ai_gate_section(composition)
    prose_only_instance = replace(
        instance,
        responsibilities=(
            *instance.responsibilities,
            "Prose-only text mentioning ai.evaluate-made-up must not "
            "become a required evaluation dimension",
        ),
    )
    prose_only = replace(
        composition,
        agent_instances=tuple(
            prose_only_instance if item is instance else item
            for item in composition.agent_instances
        ),
    )

    assert ai_gate_section(prose_only) == baseline_section
    assert "ai.evaluate-made-up" not in baseline_section


def test_rendering_rejects_lost_ai_evaluation_dimensions() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle("ai-application")
    gate = next(
        gate
        for gate in composition.workflow_gates
        if any(
            artifact.type == "AIEvaluationReport"
            for artifact in gate.required_artifacts
        )
    )
    broken_gate = replace(
        gate,
        required_capabilities=(),
    )
    broken = replace(
        composition,
        workflow_gates=tuple(
            broken_gate if item is gate else item
            for item in composition.workflow_gates
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match=(
            "must preserve non-empty required "
            "AI-evaluation capabilities"
        ),
    ):
        render_enabled_targets(paths, broken)


def test_rendering_rejects_missing_ai_evaluation_governed_input() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle("ai-application")
    gate = next(
        gate
        for gate in composition.workflow_gates
        if any(
            artifact.type == "AIEvaluationReport"
            for artifact in gate.required_artifacts
        )
    )
    binding = next(
        binding
        for binding in composition.role_bindings
        if binding.role_name == gate.owner_role_binding
    )
    broken_binding = replace(
        binding,
        input_artifacts=tuple(
            production
            for production in binding.input_artifacts
            if production.artifact.type != "Requirements"
        ),
    )
    broken = replace(
        composition,
        role_bindings=tuple(
            broken_binding if item is binding else item
            for item in composition.role_bindings
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="must preserve governed AI-evaluation inputs",
    ):
        render_enabled_targets(paths, broken)


def test_rendering_rejects_broadened_ai_evaluation_permission() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle("ai-application")
    gate = next(
        gate
        for gate in composition.workflow_gates
        if any(
            artifact.type == "AIEvaluationReport"
            for artifact in gate.required_artifacts
        )
    )
    instance = next(
        instance
        for instance in composition.agent_instances
        if instance.id == gate.owner_agent_instance
    )
    broken_instance = replace(
        instance,
        permission_profile=replace(
            instance.permission_profile,
            bash=BashPermission.LIMITED,
        ),
    )
    broken = replace(
        composition,
        agent_instances=tuple(
            broken_instance if item is instance else item
            for item in composition.agent_instances
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match=(
            "must preserve the accepted read-only/no-shell "
            "AI-evaluation permission boundary"
        ),
    ):
        render_enabled_targets(paths, broken)

_DEFAULT_BUNDLES_FOR_MATERIALIZATION = (
    "ai-application",
    "lean-delivery",
    "orchestrated-delivery",
    "review-heavy-delivery",
)


@pytest.mark.parametrize(
    "bundle_name",
    _DEFAULT_BUNDLES_FOR_MATERIALIZATION,
)
@pytest.mark.parametrize(
    ("target_name", "agent_path_template"),
    (
        ("opencode", ".opencode/agents/{agent}.md"),
        ("vscode-copilot", ".github/agents/{agent}.agent.md"),
    ),
)
def test_current_targets_preserve_adr_0014_materialization_boundary(
    bundle_name: str,
    target_name: str,
    agent_path_template: str,
) -> None:
    composition = compiled_bundle(bundle_name)
    files = rendered_bundle_files(bundle_name, target_name)
    instances = {
        instance.id: instance
        for instance in composition.agent_instances
    }
    mediated_producers = 0

    assert composition.artifact_production

    for production in composition.artifact_production:
        instance = instances[production.agent_instance]
        path = Path(
            agent_path_template.format(agent=production.agent_instance)
        )
        content = files[path].decode("utf-8")
        permission = instance.permission_profile
        direct_mutation = (
            permission.write
            or permission.edit
            or permission.bash is not BashPermission.DENY
        )

        assert "### Materialization Boundary" in content
        assert (
            "`produces` does not grant repository write, edit, or shell "
            "authority"
        ) in content
        assert "conversation-only content is not sufficient" in content
        assert (
            "unavailable or unreadable materialization forbids `PASS`"
        ) in content
        assert (
            "the workflow controller selects routes only and does not own "
            "artifact persistence or materialization"
        ) in content
        assert (
            f"- output path pattern: `{production.artifact.path_pattern}`"
        ) in content

        if direct_mutation:
            assert "- writable-producer boundary:" in content
            continue

        mediated_producers += 1
        assert "- mediated handoff:" in content
        assert (
            "caller-owned materialization outside this agent instance's "
            "permission profile"
        ) in content
        assert "do not attempt a forbidden write" in content

        if target_name == "opencode":
            assert "  edit: deny" in content
            assert "  bash: deny" in content
        else:
            assert 'tools: ["search", "read/readFile"]' in content

    assert mediated_producers > 0


def test_rendering_rejects_artifact_production_without_rendered_producer() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle("lean-delivery")
    production = composition.artifact_production[0]
    invalid = replace(
        composition,
        artifact_production=(
            replace(
                production,
                agent_instance="missing-artifact-producer",
            ),
            *composition.artifact_production[1:],
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="not a rendered agent instance",
    ):
        render_enabled_targets(paths, invalid)


def _composition_with_target_permission_setting(
    composition: CompiledComposition,
    target_name: str,
    permission_profile: str,
    setting_name: str,
    value: str | tuple[str, ...],
) -> CompiledComposition:
    target = next(
        item
        for item in composition.targets
        if item.adapter.name == target_name
    )
    mapping = next(
        item
        for item in target.adapter.permission_mappings
        if item.permission_profile == permission_profile
    )
    setting = next(
        item
        for item in mapping.settings
        if item.name == setting_name
    )
    updated_setting = replace(setting, value=value)
    updated_mapping = replace(
        mapping,
        settings=tuple(
            updated_setting if item is setting else item
            for item in mapping.settings
        ),
    )
    updated_adapter = replace(
        target.adapter,
        permission_mappings=tuple(
            updated_mapping if item is mapping else item
            for item in target.adapter.permission_mappings
        ),
    )
    updated_target = replace(target, adapter=updated_adapter)
    return replace(
        composition,
        targets=tuple(
            updated_target if item is target else item
            for item in composition.targets
        ),
    )


def test_both_targets_preserve_every_current_effective_permission_profile() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    seen_profiles: set[str] = set()

    for bundle_name in _DEFAULT_BUNDLES_FOR_MATERIALIZATION:
        composition = compiled_bundle(bundle_name)
        targets = {
            target.name: target
            for target in render_enabled_targets(paths, composition)
        }
        opencode_files = {
            file.path: file.content
            for file in targets["opencode"].files
        }
        vscode_files = {
            file.path: file.content
            for file in targets["vscode-copilot"].files
        }

        for instance in composition.agent_instances:
            permission = instance.permission_profile
            seen_profiles.add(permission.name)
            assert permission.read is True
            assert permission.write == permission.edit

            opencode = opencode_files[
                Path(f".opencode/agents/{instance.id}.md")
            ].decode("utf-8")
            expected_edit = "allow" if permission.edit else "deny"
            expected_bash = {
                BashPermission.DENY: "deny",
                BashPermission.LIMITED: "ask",
                BashPermission.ALLOW: "allow",
            }[permission.bash]
            assert f"  edit: {expected_edit}" in opencode
            assert f"  bash: {expected_bash}" in opencode

            vscode = vscode_files[
                Path(f".github/agents/{instance.id}.agent.md")
            ].decode("utf-8")
            tools_line = next(
                line
                for line in vscode.splitlines()
                if line.startswith("tools: ")
            )
            tools = set(json.loads(tools_line.removeprefix("tools: ")))

            assert {"search", "read/readFile"} <= tools
            assert ("edit/editFiles" in tools) == permission.edit
            assert (
                "execute/runInTerminal" in tools
            ) == (permission.bash is not BashPermission.DENY)

            if permission.bash is BashPermission.LIMITED:
                assert (
                    "canonical `bash=limited` permission is preserved only "
                    "under VS Code"
                ) in vscode
                assert "`Default Approvals`" in vscode
                assert "`Bypass Approvals` and `Autopilot`" in vscode
            else:
                assert "## Target Permission Prerequisite" not in vscode

    assert seen_profiles == {
        "read-only",
        "implementation",
        "test-runner",
    }


def test_rendering_rejects_broadened_opencode_limited_shell() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle("orchestrated-delivery")
    broken = _composition_with_target_permission_setting(
        composition,
        "opencode",
        "test-runner",
        "bash",
        "allow",
    )

    with pytest.raises(
        TargetRenderingError,
        match="does not preserve canonical bash='limited'",
    ):
        render_enabled_targets(paths, broken)


def test_rendering_rejects_vscode_missing_required_edit_tool() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle("orchestrated-delivery")
    target = next(
        item
        for item in composition.targets
        if item.adapter.name == "vscode-copilot"
    )
    mapping = next(
        item
        for item in target.adapter.permission_mappings
        if item.permission_profile == "test-runner"
    )
    tools = next(
        item.value
        for item in mapping.settings
        if item.name == "tools"
    )
    assert isinstance(tools, tuple)
    broken_tools = tuple(
        tool
        for tool in tools
        if tool != "edit/editFiles"
    )
    broken = _composition_with_target_permission_setting(
        composition,
        "vscode-copilot",
        "test-runner",
        "tools",
        broken_tools,
    )

    with pytest.raises(
        TargetRenderingError,
        match="does not preserve canonical write/edit authority",
    ):
        render_enabled_targets(paths, broken)


def test_rendering_rejects_unrepresentable_write_edit_split() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle("orchestrated-delivery")
    instance = next(
        item
        for item in composition.agent_instances
        if item.permission_profile.name == "test-runner"
    )
    broken_instance = replace(
        instance,
        permission_profile=replace(
            instance.permission_profile,
            edit=False,
        ),
    )
    broken = replace(
        composition,
        agent_instances=tuple(
            broken_instance if item is instance else item
            for item in composition.agent_instances
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="cannot preserve divergent canonical write/edit authority",
    ):
        render_enabled_targets(paths, broken)
def _markdown_list_section(
    content: str,
    heading: str,
) -> tuple[str, ...]:
    marker = f"## {heading}\n\n"
    assert content.count(marker) == 1
    section = content.split(marker, 1)[1].split("\n\n## ", 1)[0]
    return tuple(
        line.removeprefix("- ")
        for line in section.splitlines()
        if line.startswith("- ")
    )


def _expected_markdown_list(values: tuple[str, ...]) -> tuple[str, ...]:
    return values or ("None",)


@pytest.mark.parametrize(
    "bundle_name",
    _DEFAULT_BUNDLES_FOR_MATERIALIZATION,
)
@pytest.mark.parametrize(
    ("target_name", "agent_suffix"),
    (
        ("opencode", ".md"),
        ("vscode-copilot", ".agent.md"),
    ),
)
def test_current_targets_preserve_general_compiled_semantics(
    bundle_name: str,
    target_name: str,
    agent_suffix: str,
) -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    composition = compiled_bundle(bundle_name)
    target = next(
        item
        for item in composition.targets
        if item.adapter.name == target_name
    )
    output_paths = {
        output.name: output.path
        for output in target.adapter.output_paths
    }
    files = rendered_bundle_files(bundle_name, target_name)

    for instance in composition.agent_instances:
        agent_path = (
            Path(output_paths["agents"])
            / f"{instance.id}{agent_suffix}"
        )
        assert agent_path in files
        content = files[agent_path].decode("utf-8")

        assert f"- agent instance: `{instance.id}`" in content
        assert f"- profile: `{instance.profile.name}`" in content
        assert (
            f"- role bindings: {', '.join(instance.role_bindings)}"
            in content
        )
        assert _markdown_list_section(
            content,
            "Required Capabilities",
        ) == _expected_markdown_list(instance.required_capabilities)
        assert _markdown_list_section(
            content,
            "Selected Skills",
        ) == _expected_markdown_list(
            tuple(skill.name for skill in instance.selected_skills)
        )
        assert _markdown_list_section(
            content,
            "Responsibilities",
        ) == _expected_markdown_list(instance.responsibilities)
        assert _markdown_list_section(
            content,
            "Guardrails",
        ) == _expected_markdown_list(instance.guardrails)

    instructions_path = Path(output_paths["instructions"])
    assert instructions_path in files
    instructions = files[instructions_path].decode("utf-8")
    assert f"- bundle: {composition.bundle}" in instructions
    assert f"- profile: {composition.profile.name}" in instructions
    assert f"- workflow: {composition.workflow.name}" in instructions

    skill_output_root = Path(output_paths["skills"])
    expected_skill_files: dict[Path, bytes] = {}

    for skill in composition.skills:
        source_root = paths.registry_root / "skills" / skill.name
        for source_path in sorted(
            source_root.rglob("*"),
            key=lambda path: path.relative_to(source_root).as_posix(),
        ):
            if not source_path.is_file():
                continue
            expected_skill_files[
                skill_output_root
                / skill.name
                / source_path.relative_to(source_root)
            ] = source_path.read_bytes()

    rendered_skill_files = {
        path: content
        for path, content in files.items()
        if path.is_relative_to(skill_output_root)
    }
    assert rendered_skill_files == expected_skill_files
