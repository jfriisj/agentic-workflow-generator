from dataclasses import replace
from pathlib import Path

import pytest

import agentic_workflow_generator.application.guided_init as guided_init_module
from agentic_workflow_generator.application import (
    GuidedInitError,
    GuidedInitService,
    GuidedInitValidationError,
    load_guided_init_service,
    materialize_setup_profile,
    parse_answer_overrides,
)
from agentic_workflow_generator.domain import (
    Diagnostic,
    Setup,
    SetupMode,
    SetupOption,
    SetupOptionClassification,
    SetupQuestion,
    SetupSelection,
    SetupSelectionPatch,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
)
from agentic_workflow_generator.registry import ProjectPaths
from agentic_workflow_generator.validation.setup_profiles import (
    SetupProfileValidationResult,
)
from agentic_workflow_generator.validation.setups import (
    ProjectedSetupBundle,
    SetupReferenceData,
    SetupValidationResult,
)


def setup() -> Setup:
    return Setup(
        name="lean-delivery-greenfield",
        description="Focused setup.",
        version="0.2.0",
        mode=SetupMode.GREENFIELD,
        default_selection=SetupSelection(
            bundle="lean-delivery",
            targets=("opencode",),
        ),
        questions=(
            SetupQuestion(
                id="target-platforms",
                prompt="Which target?",
                default_option="opencode-only",
                options=(
                    SetupOption(
                        value="opencode-only",
                        label="OpenCode",
                        classification=(
                            SetupOptionClassification.RECOMMENDED
                        ),
                        reason="OpenCode is supported.",
                        selection=SetupSelectionPatch(
                            bundle=None,
                            targets=("opencode",),
                        ),
                    ),
                ),
            ),
        ),
    )


def references(
    *,
    targets: frozenset[str] = frozenset(
        {
            "opencode",
        }
    ),
) -> SetupReferenceData:
    return SetupReferenceData(
        bundles=(
            ProjectedSetupBundle(
                name="lean-delivery",
                targets=targets,
            ),
        ),
        targets=targets,
    )


def profile_schema() -> JsonObject:
    return read_json_object(
        Path(".agentic/schemas/setup-profile.schema.json")
    )


def service(
    *,
    projected_references: SetupReferenceData | None = None,
    schema: JsonObject | None = None,
) -> GuidedInitService:
    return GuidedInitService(
        setups=(setup(),),
        references=(
            references()
            if projected_references is None
            else projected_references
        ),
        profile_schema=(
            profile_schema()
            if schema is None
            else schema
        ),
    )


def test_parse_answer_overrides_accepts_none_and_values() -> None:
    assert parse_answer_overrides(None) == {}
    assert parse_answer_overrides(
        (
            " target-platforms = opencode-only ",
            "delivery-style=lean",
        )
    ) == {
        "target-platforms": "opencode-only",
        "delivery-style": "lean",
    }


@pytest.mark.parametrize(
    ("raw_answers", "message"),
    [
        (
            ("missing-separator",),
            "expected question=value",
        ),
        (
            ("=value",),
            "question id must be non-empty",
        ),
        (
            ("question=",),
            "selected value must be non-empty",
        ),
        (
            (
                "question=one",
                "question=two",
            ),
            "duplicate answer override",
        ),
    ],
)
def test_parse_answer_overrides_fails_closed(
    raw_answers: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(
        GuidedInitError,
        match=message,
    ):
        parse_answer_overrides(raw_answers)


def test_setup_lookup_and_materialization_are_typed() -> None:
    guided = service()

    assert guided.setup_by_name(
        "lean-delivery-greenfield"
    ) == setup()

    profile = guided.materialize(
        "lean-delivery-greenfield",
        {
            "target-platforms": "opencode-only",
        },
    )

    assert profile.setup == "lean-delivery-greenfield"
    assert profile.selected == SetupSelection(
        bundle="lean-delivery",
        targets=("opencode",),
    )


def test_unknown_setup_fails_closed() -> None:
    with pytest.raises(
        GuidedInitError,
        match="unknown guided setup",
    ):
        service().setup_by_name("missing")


def test_profile_validation_failure_preserves_diagnostics() -> None:
    guided = service(
        projected_references=references(
            targets=frozenset(
                {
                    "vscode-copilot",
                }
            )
        )
    )

    with pytest.raises(
        GuidedInitValidationError,
        match="setup profile validation failed",
    ) as captured:
        guided.materialize(
            "lean-delivery-greenfield"
        )

    assert captured.value.boundary == "setup profile"
    assert captured.value.diagnostics


def test_profile_round_trip_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materialized = materialize_setup_profile(
        setup()
    )

    def fake_validate_setup_profile(
        *_args: object,
        **_kwargs: object,
    ) -> SetupProfileValidationResult:
        return SetupProfileValidationResult(
            profile=replace(
                materialized,
                setup="different-setup",
            ),
            diagnostics=(),
        )

    monkeypatch.setattr(
        guided_init_module,
        "validate_setup_profile",
        fake_validate_setup_profile,
    )

    with pytest.raises(
        GuidedInitError,
        match="validated setup profile does not match",
    ):
        service().materialize(
            "lean-delivery-greenfield"
        )


def test_setup_registry_validation_failure_preserves_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostic = Diagnostic(
        code="AWG-SETUP-999",
        message="invalid setup registry",
    )

    def fake_validate_setup_registry(
        *_args: object,
        **_kwargs: object,
    ) -> SetupValidationResult:
        return SetupValidationResult(
            setups=(),
            diagnostics=(diagnostic,),
        )

    monkeypatch.setattr(
        guided_init_module,
        "validate_setup_registry",
        fake_validate_setup_registry,
    )

    with pytest.raises(
        GuidedInitValidationError,
        match="setup registry validation failed",
    ) as captured:
        load_guided_init_service(
            ProjectPaths(Path.cwd().resolve())
        )

    assert captured.value.boundary == "setup registry"
    assert captured.value.diagnostics == (diagnostic,)
