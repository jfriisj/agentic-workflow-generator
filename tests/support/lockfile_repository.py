"""Repository fixture for lockfile tests."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.registry import ProjectPaths


def build_lockfile_repository(
    root: Path,
) -> ProjectPaths:
    """Create a minimal repository covering every lock pattern."""

    files = {
        ".agentic/agentic.json": "{}\n",
        ".agentic/schemas/agentic.schema.json": "{}\n",
        ".agentic/schemas/registry/agent.schema.json": "{}\n",
        "pyproject.toml": "[project]\n",
        "registry/bundles/example.bundle.json": "{}\n",
        "registry/skills/example/SKILL.md": "# Example\n",
        "src/agentic_workflow_generator/example.py": (
            "VALUE = 2\n"
        ),
        "uv.lock": "version = 1\n",
    }

    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return ProjectPaths(root.resolve())
