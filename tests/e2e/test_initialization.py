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
    validate_target_output,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class ConsumerSelection:
    mode: Literal["bundle", "setup"]
    name: str


CONSUMER_ACCEPTANCE_MATRIX = (
    ConsumerSelection("bundle", "ai-application"),
    ConsumerSelection("bundle", "lean-delivery"),
    ConsumerSelection("bundle", "orchestrated-delivery"),
    ConsumerSelection("bundle", "review-heavy-delivery"),
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
    registered_targets = tuple(
        target.name
        for target in service.registry.targets
    )
    first_plan = plan_selection(service, selection)

    assert first_plan.targets == registered_targets

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
