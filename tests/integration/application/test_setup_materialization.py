from pathlib import Path

import pytest

from agentic_workflow_generator.application import (
    materialize_setup_profile,
    setup_profile_to_json,
)
from agentic_workflow_generator.domain import Setup
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
    serialize_json,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryKind,
    RegistryLoader,
)
from agentic_workflow_generator.validation.setup_profiles import (
    validate_setup_profile,
)
from agentic_workflow_generator.validation.setups import (
    SetupReferenceData,
    project_setup_bundles,
    project_target_names,
    validate_setup_registry,
)

REPOSITORY_ROOT = Path(__file__).parents[3]


def load_validated_setups() -> tuple[
    tuple[Setup, ...],
    SetupReferenceData,
    JsonObject,
]:
    paths = ProjectPaths(REPOSITORY_ROOT.resolve())
    loader = RegistryLoader(paths)

    references = SetupReferenceData(
        bundles=project_setup_bundles(
            loader.load(RegistryKind.BUNDLE)
        ),
        targets=project_target_names(
            loader.load(RegistryKind.TARGET)
        ),
    )
    result = validate_setup_registry(
        loader.load(RegistryKind.SETUP),
        read_json_object(
            paths.schema_root
            / "registry"
            / "setup.schema.json"
        ),
        references,
    )

    assert result.is_valid
    assert not result.diagnostics

    return (
        result.setups,
        references,
        read_json_object(
            paths.schema_root
            / "setup-profile.schema.json"
        ),
    )


def validate_materialized_profile(
    setup: Setup,
    references: SetupReferenceData,
    profile_schema: JsonObject,
    *,
    target_option: str | None = None,
) -> JsonObject:
    overrides = (
        {
            "target-platforms": target_option,
        }
        if target_option is not None
        else None
    )
    profile = materialize_setup_profile(
        setup,
        overrides,
    )
    data = setup_profile_to_json(profile)
    result = validate_setup_profile(
        data,
        Path(
            ".agentic"
            / Path("generated")
            / "integration"
            / f"{setup.name}.setup-profile.json"
        ),
        profile_schema,
        (setup,),
        references,
    )

    assert result.is_valid
    assert not result.diagnostics
    assert result.profile == profile
    return data


def test_all_registered_setups_materialize_valid_default_profiles() -> None:
    setups, references, profile_schema = load_validated_setups()

    assert tuple(setup.name for setup in setups) == (
        "ai-application-greenfield",
        "lean-delivery-greenfield",
        "orchestrated-delivery-greenfield",
        "review-heavy-delivery-greenfield",
    )

    for setup in setups:
        data = validate_materialized_profile(
            setup,
            references,
            profile_schema,
        )

        assert serialize_json(data) == serialize_json(data)
        assert data["selected"] == {
            "bundle": setup.default_selection.bundle,
            "targets": list(setup.default_selection.targets),
        }


@pytest.mark.parametrize(
    ("target_option", "expected_targets"),
    [
        (
            "opencode-only",
            [
                "opencode",
            ],
        ),
        (
            "vscode-copilot-only",
            [
                "vscode-copilot",
            ],
        ),
    ],
)
def test_all_registered_setups_materialize_valid_target_overrides(
    target_option: str,
    expected_targets: list[str],
) -> None:
    setups, references, profile_schema = load_validated_setups()

    for setup in setups:
        data = validate_materialized_profile(
            setup,
            references,
            profile_schema,
            target_option=target_option,
        )
        selected = data["selected"]

        assert isinstance(selected, dict)
        assert selected["targets"] == expected_targets


def test_repository_setup_profile_matches_default_materialization() -> None:
    setups, references, profile_schema = load_validated_setups()
    existing = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "setup-profile.json"
    )
    setup_name = existing["setup"]

    assert isinstance(setup_name, str)

    setup = next(
        setup
        for setup in setups
        if setup.name == setup_name
    )
    materialized = validate_materialized_profile(
        setup,
        references,
        profile_schema,
    )

    assert existing == materialized
