from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workflow_generator.application.target_materialization import (
    build_target_materialization_plan,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
    sha256_bytes,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_plan_builds_schema_valid_reduced_manifest() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    plan = build_target_materialization_plan(paths)
    schema = read_json_object(
        paths.schema_root
        / "generated"
        / "output-manifest.schema.json"
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(
        plan.manifest
    )

    assert plan.manifest["schemaVersion"] == "0.3.0"
    assert set(plan.manifest) == {
        "schemaVersion",
        "description",
        "composition",
        "targets",
        "summary",
    }
    assert "bundle" not in plan.manifest

    summary = plan.manifest["summary"]
    assert isinstance(summary, dict)
    assert "errorCount" not in summary
    assert "errors" not in summary


def test_plan_manifest_hashes_planned_output() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    plan = build_target_materialization_plan(paths)
    manifest_targets = plan.manifest["targets"]

    assert isinstance(manifest_targets, list)

    expected = {
        file.path.as_posix(): (
            sha256_bytes(file.content),
            len(file.content),
        )
        for target in plan.rendered_targets
        for file in target.files
    }
    actual: dict[str, tuple[str, int]] = {}

    for target in manifest_targets:
        assert isinstance(target, dict)
        assert "registryPath" not in target
        generated_files = target["generatedFiles"]
        assert isinstance(generated_files, list)

        for generated_file in generated_files:
            assert isinstance(generated_file, dict)
            path = generated_file["path"]
            digest = generated_file["sha256"]
            size = generated_file["bytes"]
            assert isinstance(path, str)
            assert isinstance(digest, str)
            assert isinstance(size, int)
            actual[path] = (digest, size)

    assert actual == expected


def test_plan_uses_agent_instance_output_paths() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    plan = build_target_materialization_plan(paths)
    planned_paths = {
        file.path
        for target in plan.rendered_targets
        for file in target.files
    }

    assert Path(
        ".opencode/agents/workflow-controller.md"
    ) in planned_paths
    assert Path(
        ".github/agents/workflow-controller.agent.md"
    ) in planned_paths
    assert Path(
        ".opencode/agents/orchestrator.md"
    ) not in planned_paths
    assert Path(
        ".github/agents/orchestrator.agent.md"
    ) not in planned_paths


def test_plan_marks_unplanned_owned_files_as_stale(
    tmp_path: Path,
) -> None:
    from agentic_workflow_generator.application.target_materialization import (
        _collect_stale_files,
    )
    from agentic_workflow_generator.application.target_rendering import (
        RenderedFile,
        RenderedTarget,
    )

    paths = ProjectPaths(tmp_path)
    owned = tmp_path / "owned"
    owned.mkdir()
    (owned / "keep.txt").write_bytes(b"old")
    (owned / "stale.txt").write_bytes(b"stale")

    rendered = (
        RenderedTarget(
            name="test",
            owned_paths=("owned",),
            files=(
                RenderedFile(
                    path=Path("owned/keep.txt"),
                    content=b"new",
                ),
            ),
        ),
    )

    assert _collect_stale_files(
        paths,
        rendered,
    ) == (Path("owned/stale.txt"),)

def test_plan_marks_obsolete_resolution_as_stale(
    tmp_path: Path,
) -> None:
    from agentic_workflow_generator.application.target_materialization import (
        _collect_stale_files,
    )

    paths = ProjectPaths(tmp_path)
    resolution = (
        paths.generated_root / "resolution.json"
    )
    resolution.parent.mkdir(parents=True)
    resolution.write_bytes(b"{}")

    assert _collect_stale_files(
        paths,
        (),
    ) == (
        Path(".agentic/generated/resolution.json"),
    )
