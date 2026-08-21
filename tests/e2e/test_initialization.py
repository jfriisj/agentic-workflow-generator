from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from agentic_workflow_generator.application import (
    InitializationPlan,
    InitializationService,
    load_initialization_service,
)
from agentic_workflow_generator.application.lockfile import (
    generate_lockfile,
    validate_lockfile,
)
from agentic_workflow_generator.application.target_materialization import (
    materialize_targets,
)
from agentic_workflow_generator.application.target_output_validation import (
    UNMANAGED_FILE_DIAGNOSTIC,
    validate_target_output,
)
from agentic_workflow_generator.cli.main import (
    main as cli_main,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
    write_json,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


ALL_TARGETS = ("opencode", "vscode-copilot")


@dataclass(frozen=True, slots=True)
class ConsumerSelection:
    mode: Literal["bundle", "setup"]
    name: str
    targets: tuple[str, ...] = ALL_TARGETS


CONSUMER_ACCEPTANCE_MATRIX = (
    ConsumerSelection("bundle", "agent-factory", ("opencode",)),
    ConsumerSelection("bundle", "ai-application"),
    ConsumerSelection("bundle", "lean-delivery"),
    ConsumerSelection("bundle", "orchestrated-delivery"),
    ConsumerSelection("bundle", "review-heavy-delivery"),
    ConsumerSelection("setup", "agent-factory-greenfield", ("opencode",)),
    ConsumerSelection("setup", "ai-application-greenfield"),
    ConsumerSelection("setup", "lean-delivery-greenfield"),
    ConsumerSelection("setup", "orchestrated-delivery-greenfield"),
    ConsumerSelection("setup", "review-heavy-delivery-greenfield"),
)


def copy_consumer_repository(
    consumer_root: Path,
) -> ProjectPaths:
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        consumer_root / "registry",
    )
    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        consumer_root / ".agentic" / "schemas",
    )
    return ProjectPaths(consumer_root)


def repository_files(
    paths: ProjectPaths,
) -> frozenset[Path]:
    return frozenset(
        path.relative_to(paths.root)
        for path in paths.root.rglob("*")
        if path.is_file()
    )


def plan_selection(
    service: InitializationService,
    selection: ConsumerSelection,
) -> InitializationPlan:
    if selection.mode == "bundle":
        return service.plan_bundle(selection.name)

    return service.plan_setup(selection.name)


def test_consumer_acceptance_matrix_matches_registered_selections(
    tmp_path: Path,
) -> None:
    paths = copy_consumer_repository(
        tmp_path / "consumer-project"
    )
    service = load_initialization_service(paths)

    assert tuple(
        selection.name
        for selection in CONSUMER_ACCEPTANCE_MATRIX
        if selection.mode == "bundle"
    ) == tuple(
        bundle.name
        for bundle in service.registry.bundles
    )
    assert tuple(
        selection.name
        for selection in CONSUMER_ACCEPTANCE_MATRIX
        if selection.mode == "setup"
    ) == tuple(
        setup.name
        for setup in service.guided_init.setups
    )


@pytest.mark.parametrize(
    "selection",
    CONSUMER_ACCEPTANCE_MATRIX,
    ids=lambda selection: f"{selection.mode}:{selection.name}",
)
def test_consumer_acceptance_matrix_initializes_clean_consumers(
    tmp_path: Path,
    selection: ConsumerSelection,
) -> None:
    paths = copy_consumer_repository(
        tmp_path / "consumer-project"
    )
    initial_files = repository_files(paths)

    assert initial_files
    assert all(
        relative_path.parts[0] == "registry"
        or relative_path.parts[:2] == (".agentic", "schemas")
        for relative_path in initial_files
    )
    assert not paths.active_config.exists()
    assert not paths.setup_profile.exists()
    assert not paths.lockfile.exists()
    assert not paths.generated_root.exists()

    service = load_initialization_service(paths)
    first_plan = plan_selection(service, selection)

    assert first_plan.targets == selection.targets

    first_result = service.commit(first_plan)
    expected_written_paths = frozenset(
        (
            paths.active_config,
            paths.setup_profile,
        )
        if selection.mode == "setup"
        else (paths.active_config,)
    )

    assert first_result.changed is True
    assert frozenset(first_result.written_paths) == expected_written_paths

    active_config = read_json_object(paths.active_config)

    assert "agents" not in active_config
    assert "gates" not in active_config

    if selection.mode == "setup":
        setup_profile = read_json_object(paths.setup_profile)
        assert setup_profile["selected"] == {
            "bundle": first_plan.bundle,
            "targets": list(first_plan.targets),
        }
    else:
        assert not paths.setup_profile.exists()

    expected_new_files = frozenset(
        path.relative_to(paths.root)
        for path in expected_written_paths
    )
    assert repository_files(paths) - initial_files == expected_new_files
    assert not paths.lockfile.exists()
    assert not paths.generated_root.exists()

    first_outputs = {
        path: path.read_bytes()
        for path in expected_written_paths
    }

    second_plan = plan_selection(service, selection)
    second_result = service.commit(second_plan)

    assert second_plan.active_config == first_plan.active_config
    assert second_plan.setup_profile_json == first_plan.setup_profile_json
    assert second_result.changed is False
    assert second_result.written_paths == ()
    assert {
        path: path.read_bytes()
        for path in expected_written_paths
    } == first_outputs


@pytest.mark.parametrize(
    "selection",
    CONSUMER_ACCEPTANCE_MATRIX,
    ids=lambda selection: f"{selection.mode}:{selection.name}",
)
def test_consumer_acceptance_matrix_generates_canonical_lock_state(
    tmp_path: Path,
    selection: ConsumerSelection,
) -> None:
    paths = copy_consumer_repository(
        tmp_path / "consumer-project"
    )
    service = load_initialization_service(paths)
    plan = plan_selection(service, selection)
    initialization_result = service.commit(plan)

    assert initialization_result.changed is True
    assert paths.active_config.exists()
    assert not paths.lockfile.exists()
    assert not paths.generated_root.exists()
    assert not paths.manifest.exists()

    active_config_before_lock = paths.active_config.read_bytes()

    first_generation = generate_lockfile(paths)
    first_lockfile = paths.lockfile.read_bytes()

    assert first_generation.input_file_count > 0
    assert first_generation.content_hash.startswith("sha256:")
    assert validate_lockfile(paths) == ()

    lockfile = read_json_object(paths.lockfile)
    inputs = lockfile["inputs"]

    assert isinstance(inputs, dict)
    files = inputs["files"]
    assert isinstance(files, list)

    locked_paths = {
        entry["path"]
        for entry in files
        if isinstance(entry, dict)
        and isinstance(entry.get("path"), str)
    }

    assert ".agentic/agentic.json" in locked_paths
    assert paths.active_config.read_bytes() == active_config_before_lock
    assert not paths.generated_root.exists()
    assert not paths.manifest.exists()

    second_generation = generate_lockfile(paths)

    assert second_generation == first_generation
    assert paths.lockfile.read_bytes() == first_lockfile
    assert validate_lockfile(paths) == ()
    assert paths.active_config.read_bytes() == active_config_before_lock
    assert not paths.generated_root.exists()
    assert not paths.manifest.exists()


@pytest.mark.parametrize(
    "selection",
    CONSUMER_ACCEPTANCE_MATRIX,
    ids=lambda selection: f"{selection.mode}:{selection.name}",
)
def test_consumer_acceptance_matrix_materializes_canonical_target_state(
    tmp_path: Path,
    selection: ConsumerSelection,
) -> None:
    paths = copy_consumer_repository(
        tmp_path / "consumer-project"
    )
    service = load_initialization_service(paths)
    plan = plan_selection(service, selection)
    initialization_result = service.commit(plan)

    assert initialization_result.changed is True
    assert paths.active_config.exists()
    assert not paths.lockfile.exists()
    assert not paths.generated_root.exists()

    generate_lockfile(paths)

    assert validate_lockfile(paths) == ()
    assert paths.lockfile.exists()
    assert not paths.generated_root.exists()
    assert not paths.manifest.exists()

    active_config_before_materialization = paths.active_config.read_bytes()
    lockfile_before_materialization = paths.lockfile.read_bytes()

    result = materialize_targets(paths)

    assert result.target_count == len(plan.targets)
    assert result.generated_file_count > 0
    assert paths.manifest.exists()
    assert validate_target_output(paths) == ()

    manifest = read_json_object(paths.manifest)
    targets = manifest["targets"]
    summary = manifest["summary"]

    assert isinstance(targets, list)
    assert isinstance(summary, dict)

    manifest_target_names: list[str] = []
    manifest_generated_paths: list[str] = []

    for target in targets:
        assert isinstance(target, dict)
        target_name = target.get("name")
        generated_files = target.get("generatedFiles")

        assert isinstance(target_name, str)
        assert isinstance(generated_files, list)
        assert target.get("generatedFileCount") == len(generated_files)

        manifest_target_names.append(target_name)

        for generated_file in generated_files:
            assert isinstance(generated_file, dict)
            generated_path = generated_file.get("path")
            assert isinstance(generated_path, str)
            manifest_generated_paths.append(generated_path)

    assert tuple(manifest_target_names) == plan.targets
    assert summary["targetCount"] == result.target_count
    assert summary["generatedFileCount"] == result.generated_file_count
    assert len(manifest_generated_paths) == result.generated_file_count
    assert all(
        paths.repository_path(generated_path).is_file()
        for generated_path in manifest_generated_paths
    )
    assert (
        paths.active_config.read_bytes()
        == active_config_before_materialization
    )
    assert paths.lockfile.read_bytes() == lockfile_before_materialization


@pytest.mark.parametrize(
    "selection",
    CONSUMER_ACCEPTANCE_MATRIX,
    ids=lambda selection: f"{selection.mode}:{selection.name}",
)
def test_consumer_acceptance_matrix_repeats_canonical_target_state(
    tmp_path: Path,
    selection: ConsumerSelection,
) -> None:
    paths = copy_consumer_repository(
        tmp_path / "consumer-project"
    )
    service = load_initialization_service(paths)
    plan = plan_selection(service, selection)
    initialization_result = service.commit(plan)

    assert initialization_result.changed is True
    assert paths.active_config.exists()

    generate_lockfile(paths)

    assert validate_lockfile(paths) == ()

    first_result = materialize_targets(paths)

    assert first_result.target_count == len(plan.targets)
    assert first_result.generated_file_count > 0
    assert first_result.removed_file_count == 0
    assert validate_target_output(paths) == ()

    manifest = read_json_object(paths.manifest)
    targets = manifest["targets"]

    assert isinstance(targets, list)

    generated_paths: list[Path] = []
    owned_paths: list[Path] = []

    for target in targets:
        assert isinstance(target, dict)
        generated_files = target.get("generatedFiles")
        raw_owned_paths = target.get("ownedPaths")

        assert isinstance(generated_files, list)
        assert isinstance(raw_owned_paths, list)

        for generated_file in generated_files:
            assert isinstance(generated_file, dict)
            generated_path = generated_file.get("path")
            assert isinstance(generated_path, str)
            generated_paths.append(Path(generated_path))

        for owned_path in raw_owned_paths:
            assert isinstance(owned_path, str)
            owned_paths.append(Path(owned_path))

    canonical_generated_paths = frozenset(generated_paths)

    def owned_regular_files() -> frozenset[Path]:
        files: set[Path] = set()

        for owned_path in owned_paths:
            owned_root = paths.repository_path(owned_path)

            if owned_root.is_file():
                files.add(owned_path)
            elif owned_root.is_dir():
                files.update(
                    candidate.relative_to(paths.root)
                    for candidate in owned_root.rglob("*")
                    if candidate.is_file()
                )

        return frozenset(files)

    assert owned_regular_files() == canonical_generated_paths

    active_config_before_repeat = paths.active_config.read_bytes()
    lockfile_before_repeat = paths.lockfile.read_bytes()
    manifest_before_repeat = paths.manifest.read_bytes()
    generated_before_repeat = {
        generated_path: paths.repository_path(
            generated_path
        ).read_bytes()
        for generated_path in canonical_generated_paths
    }

    second_result = materialize_targets(paths)

    assert second_result.target_count == first_result.target_count
    assert (
        second_result.generated_file_count
        == first_result.generated_file_count
    )
    assert second_result.removed_file_count == 0
    assert paths.active_config.read_bytes() == active_config_before_repeat
    assert paths.lockfile.read_bytes() == lockfile_before_repeat
    assert paths.manifest.read_bytes() == manifest_before_repeat
    assert {
        generated_path: paths.repository_path(
            generated_path
        ).read_bytes()
        for generated_path in canonical_generated_paths
    } == generated_before_repeat
    assert owned_regular_files() == canonical_generated_paths
    assert validate_target_output(paths) == ()

    owned_directories = tuple(
        paths.repository_path(owned_path)
        for owned_path in owned_paths
        if paths.repository_path(owned_path).is_dir()
    )

    assert owned_directories

    unmanaged = owned_directories[0] / "consumer-unmanaged.txt"
    assert not unmanaged.exists()
    unmanaged.write_bytes(b"unmanaged\n")

    diagnostics = validate_target_output(paths)

    assert UNMANAGED_FILE_DIAGNOSTIC in {
        diagnostic.code
        for diagnostic in diagnostics
    }

    cleanup_result = materialize_targets(paths)

    assert cleanup_result.target_count == first_result.target_count
    assert (
        cleanup_result.generated_file_count
        == first_result.generated_file_count
    )
    assert cleanup_result.removed_file_count == 1
    assert not unmanaged.exists()
    assert paths.active_config.read_bytes() == active_config_before_repeat
    assert paths.lockfile.read_bytes() == lockfile_before_repeat
    assert paths.manifest.read_bytes() == manifest_before_repeat
    assert {
        generated_path: paths.repository_path(
            generated_path
        ).read_bytes()
        for generated_path in canonical_generated_paths
    } == generated_before_repeat
    assert owned_regular_files() == canonical_generated_paths
    assert validate_target_output(paths) == ()


def test_agent_factory_reference_fixture_preserves_models(
    tmp_path: Path,
) -> None:
    paths = copy_consumer_repository(tmp_path / "consumer-project")
    service = load_initialization_service(paths)
    plan = service.plan_setup("agent-factory-greenfield")
    service.commit(plan)

    active_config = read_json_object(paths.active_config)
    instances = active_config["agentInstances"]
    assert isinstance(instances, list)
    assert {
        instance["id"]
        for instance in instances
        if isinstance(instance, dict)
    } == {
        "requirements-researcher",
        "software-architect",
        "minimal-change-engineer",
        "test-engineer",
        "code-reviewer",
        "reality-checker",
        "workflow-controller",
    }
    assert all(
        isinstance(instance, dict)
        and instance.get("modelAssignment")
        == {"provider": "openai", "model": "gpt-5.6-sol"}
        for instance in instances
    )

    generate_lockfile(paths)
    materialize_targets(paths)
    assert validate_target_output(paths) == ()
    for instance in instances:
        assert isinstance(instance, dict)
        agent_path = paths.root / ".opencode" / "agents" / f"{instance['id']}.md"
        assert agent_path.is_file()
        assert 'model: "openai/gpt-5.6-sol"' in agent_path.read_text(encoding="utf-8")


def test_agent_factory_distinct_assignments_preserve_per_agent(
    tmp_path: Path,
) -> None:
    paths = copy_consumer_repository(tmp_path / "consumer-project")
    bundle_path = paths.registry_root / "bundles" / "agent-factory.bundle.json"
    bundle = read_json_object(bundle_path)
    instances = bundle["agentInstances"]
    assert isinstance(instances, list)
    first = instances[0]
    assert isinstance(first, dict)
    first["modelAssignment"] = {"provider": "openai", "model": "gpt-5.6-luna"}
    write_json(bundle_path, bundle)

    service = load_initialization_service(paths)
    plan = service.plan_bundle("agent-factory")
    service.commit(plan)
    active_config = read_json_object(paths.active_config)
    active_instances = active_config["agentInstances"]
    assert isinstance(active_instances, list)
    by_id = {
        instance["id"]: instance
        for instance in active_instances
        if isinstance(instance, dict) and isinstance(instance.get("id"), str)
    }
    assert by_id["requirements-researcher"]["modelAssignment"] == {
        "provider": "openai",
        "model": "gpt-5.6-luna",
    }
    assert by_id["software-architect"]["modelAssignment"] == {
        "provider": "openai",
        "model": "gpt-5.6-sol",
    }

    generate_lockfile(paths)
    materialize_targets(paths)
    assert validate_target_output(paths) == ()
    assert 'model: "openai/gpt-5.6-luna"' in (
        paths.root / ".opencode" / "agents" / "requirements-researcher.md"
    ).read_text(encoding="utf-8")
    assert 'model: "openai/gpt-5.6-sol"' in (
        paths.root / ".opencode" / "agents" / "software-architect.md"
    ).read_text(encoding="utf-8")


def test_consumer_incomplete_active_composition_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_consumer_repository(
        tmp_path / "consumer-project"
    )
    service = load_initialization_service(paths)
    plan = service.plan_bundle("orchestrated-delivery")
    initialization_result = service.commit(plan)

    assert initialization_result.changed is True
    assert paths.active_config.exists()
    assert not paths.lockfile.exists()
    assert not paths.generated_root.exists()
    assert not paths.manifest.exists()

    active_config = read_json_object(paths.active_config)

    assert "workflow" in active_config
    del active_config["workflow"]
    write_json(paths.active_config, active_config)

    invalid_active_config = paths.active_config.read_bytes()

    monkeypatch.chdir(paths.root)
    result = cli_main(("validate",))

    assert result == 1
    output = capsys.readouterr().out
    assert "AWG-ACTIVE-CONFIG-001" in output
    assert "workflow" in output

    assert (
        paths.active_config.read_bytes()
        == invalid_active_config
    )
    assert "workflow" not in read_json_object(
        paths.active_config
    )
    assert not paths.lockfile.exists()
