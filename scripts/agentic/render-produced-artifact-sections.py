#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
RESOLUTION_PATH = ROOT / ".agentic" / "generated" / "resolution.json"

BEGIN_MARKER = "<!-- BEGIN GENERATED PRODUCED ARTIFACTS -->"
END_MARKER = "<!-- END GENERATED PRODUCED ARTIFACTS -->"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def slugify(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = value.replace("_", "-").replace(" ", "-")
    value = re.sub(r"[^a-zA-Z0-9-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-").lower()


def markdown_list(values: list[str]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {value}" for value in values)


def render_section(produces: list[dict[str, Any]]) -> str:
    if not produces:
        body = """## Produced Artifacts

This agent does not declare a produced artifact contract.
"""
    else:
        blocks: list[str] = [
            "## Produced Artifacts",
            "",
            "When this agent completes work, it must produce output that matches the declared artifact contract.",
        ]

        for artifact in produces:
            artifact_type = artifact["type"]
            contract_path = artifact.get("contractPath", "missing")
            path_pattern = artifact.get("pathPattern", "missing")
            allowed_statuses = artifact.get("allowedStatuses", [])
            required_headings = artifact.get("requiredHeadings", [])

            blocks.extend(
                [
                    "",
                    f"### {artifact_type}",
                    "",
                    f"- contract: `{contract_path}`",
                    f"- output path pattern: `{path_pattern}`",
                    f"- allowed statuses: {', '.join(allowed_statuses)}",
                    "",
                    "Required headings:",
                    "",
                    markdown_list(required_headings),
                ]
            )

        body = "\n".join(blocks) + "\n"

    return f"{BEGIN_MARKER}\n{body}{END_MARKER}\n"


def upsert_section(markdown: str, section: str) -> str:
    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER) + r"\n?",
        flags=re.DOTALL,
    )

    if pattern.search(markdown):
        return pattern.sub(section, markdown)

    insertion_points = [
        "\n## Output Expectations\n",
        "\n## Runtime Context Requirement\n",
    ]

    for marker in insertion_points:
        if marker in markdown:
            return markdown.replace(marker, "\n" + section + marker, 1)

    if markdown.endswith("\n"):
        return markdown + "\n" + section

    return markdown + "\n\n" + section


def update_file(path: Path, section: str) -> bool:
    if not path.is_file():
        return False

    original = path.read_text(encoding="utf-8")
    updated = upsert_section(original, section)

    if updated != original:
        path.write_text(updated, encoding="utf-8")

    return True


def main() -> int:
    resolution = load_json(RESOLUTION_PATH)
    updated_files = 0
    missing_files: list[str] = []

    for agent in resolution.get("agents", []):
        agent_name = agent["name"]
        produces = agent.get("produces", [])
        section = render_section(produces)
        slug = slugify(agent_name)

        target_paths = [
            ROOT / ".github" / "agents" / f"{slug}.agent.md",
            ROOT / ".opencode" / "agents" / f"{slug}.md",
        ]

        found_any = False

        for path in target_paths:
            if update_file(path, section):
                found_any = True
                updated_files += 1

        if not found_any:
            missing_files.append(agent_name)

    if missing_files:
        raise RuntimeError(
            "No generated agent files found for: " + ", ".join(sorted(missing_files))
        )

    print(f"PASS: Rendered produced artifact sections into {updated_files} generated agent file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
