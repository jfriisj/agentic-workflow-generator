"""Skill registry validation command."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.cli.rendering import render_failure
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryError,
    RegistryKind,
    RegistryLoader,
)
from agentic_workflow_generator.validation.skills import (
    SkillDependencyProjectionError,
    SkillReferenceData,
    project_agent_names,
    validate_skill_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-SKILL-900"


def main() -> int:
    """Validate the reusable skill registry."""

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        loader = RegistryLoader(paths)
        skill_sources = loader.load(RegistryKind.SKILL)
        agent_sources = loader.load(RegistryKind.AGENT)
        schema = read_json_object(paths.schema_root / "registry" / "skill.schema.json")

        existing_content_paths = frozenset(
            (
                source.source_path.parent / str(source.data.get("contentPath", ""))
            ).as_posix()
            for source in skill_sources
            if (
                isinstance(source.data.get("contentPath"), str)
                and (
                    source.source_path.parent / str(source.data["contentPath"])
                ).is_file()
            )
        )

        references = SkillReferenceData(
            agent_names=project_agent_names(agent_sources),
            existing_content_paths=existing_content_paths,
        )
    except (
        InfrastructureError,
        RegistryError,
        SkillDependencyProjectionError,
    ) as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    result = validate_skill_registry(
        skill_sources,
        schema,
        references,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    print(
        "PASS: Skill registry is valid. "
        f"Checked {len(result.skills)} skill directorie(s), "
        f"{len(result.capability_providers)} capability "
        "provider(s), and "
        f"{len(references.agent_names)} agent profile(s)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Skill registry', diagnostics)
