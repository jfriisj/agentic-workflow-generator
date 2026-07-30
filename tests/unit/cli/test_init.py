from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

import agentic_workflow_generator.cli.init as init_module
from agentic_workflow_generator.application import (
    GuidedInitValidationError,
    InitializationValidationError,
    load_initialization_service,
)
from agentic_workflow_generator.cli.init import (
    InitCommandError,
    Terminal,
    main,
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
    JsonValue,
    read_json_object,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
    tmp_path: Path,
) -> ProjectPaths:
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        tmp_path / "registry",
    )
    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        tmp_path / ".agentic" / "schemas",
    )
    return ProjectPaths(tmp_path)


def copy_existing_outputs(
    paths: ProjectPaths,
) -> dict[Path, tuple[bytes, int]]:
    paths.active_config.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    shutil.copy2(
        REPOSITORY_ROOT / ".agentic" / "agentic.json",
        paths.active_config,
    )
    shutil.copy2(
        REPOSITORY_ROOT / ".agentic" / "setup-profile.json",
        paths.setup_profile,
    )

    return {
        output: (
            output.read_bytes(),
            output.stat().st_mtime_ns,
        )
        for output in (
            paths.active_config,
            paths.setup_profile,
        )
    }


def assert_outputs_unchanged(
    before: dict[Path, tuple[bytes, int]],
) -> None:
    for output, (
        expected_bytes,
        expected_mtime_ns,
    ) in before.items():
        assert output.is_file()
        assert output.read_bytes() == expected_bytes
        assert output.stat().st_mtime_ns == expected_mtime_ns


def terminal_for(
    values: list[str],
    *,
    attached: bool = True,
) -> Terminal:
    iterator: Iterator[str] = iter(values)

    def read_value(_prompt: str) -> str:
        return next(iterator)

    return Terminal(
        input_reader=read_value,
        stdin_isatty=attached,
        stdout_isatty=attached,
    )


def default_interactive_values(
    paths: ProjectPaths,
    setup_name: str,
    *,
    confirmation: str,
) -> list[str]:
    service = load_initialization_service(paths)
    setup = service.guided_init.setup_by_name(setup_name)

    return [
        setup_name,
        *("" for _question in setup.questions),
        confirmation,
    ]


def test_direct_bundle_init_writes_typed_active_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--bundle",
            "lean-delivery",
        )
    )

    assert result == 0
    assert paths.active_config.is_file()
    assert not paths.setup_profile.exists()

    config = read_json_object(paths.active_config)

    assert config["selection"] == {
        "bundle": {
            "name": "lean-delivery",
            "version": "0.2.0",
        },
        "profile": {
            "name": "lean-delivery",
            "version": "0.2.0",
        },
        "workflow": {
            "name": "lean-delivery",
            "version": "0.2.0",
        },
    }
    assert "agentInstances" in config
    assert "roleBindings" in config
    assert "agents" not in config
    assert capsys.readouterr().out == (
        "PASS: Initialized .agentic/agentic.json from bundle 'lean-delivery'.\n"
    )


def test_noninteractive_guided_init_writes_both_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--guided",
            "--setup",
            "orchestrated-delivery-greenfield",
            "--answer",
            "target-platforms=opencode-only",
        )
    )

    assert result == 0
    assert paths.active_config.is_file()
    assert paths.setup_profile.is_file()

    config = read_json_object(paths.active_config)
    profile = read_json_object(paths.setup_profile)

    assert config["targets"] == [
        {
            "name": "opencode",
            "enabled": True,
            "priority": 1,
        }
    ]
    assert profile["selected"] == {
        "bundle": "orchestrated-delivery",
        "targets": [
            "opencode",
        ],
    }


@pytest.mark.parametrize(
    (
        "answer",
        "expected_selected",
        "expected_classification",
        "expected_targets",
    ),
    [
        (
            None,
            "opencode-and-vscode-copilot",
            "recommended",
            ["opencode", "vscode-copilot"],
        ),
        (
            "target-platforms=opencode-only",
            "opencode-only",
            "compatible",
            ["opencode"],
        ),
        (
            "target-platforms=vscode-copilot-only",
            "vscode-copilot-only",
            "compatible",
            ["vscode-copilot"],
        ),
    ],
)
def test_guided_target_selection_preserves_materialized_contract(
    answer: str | None,
    expected_selected: str,
    expected_classification: str,
    expected_targets: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    arguments = [
        "--guided",
        "--setup",
        "orchestrated-delivery-greenfield",
    ]

    if answer is not None:
        arguments.extend(
            (
                "--answer",
                answer,
            )
        )

    result = main(tuple(arguments))

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Initialized .agentic/setup-profile.json "
        "from guided setup "
        "'orchestrated-delivery-greenfield'.\n"
        "PASS: Initialized .agentic/agentic.json "
        "from bundle 'orchestrated-delivery'.\n"
    )

    profile = read_json_object(paths.setup_profile)
    config = read_json_object(paths.active_config)
    answers = profile["answers"]
    assert isinstance(answers, list)
    target_answer = next(
        answer_value
        for answer_value in answers
        if isinstance(answer_value, dict)
        and answer_value.get("question") == "target-platforms"
    )

    selected = cast(JsonObject, profile["selected"])
    targets = cast(list[JsonValue], config["targets"])
    target_objects = [cast(JsonObject, target) for target in targets]

    assert target_answer["selected"] == expected_selected
    assert target_answer["classification"] == expected_classification
    assert selected["targets"] == expected_targets
    assert [target["name"] for target in target_objects] == expected_targets


def test_ai_guided_init_preserves_complete_composition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--guided",
            "--setup",
            "ai-application-greenfield",
        )
    )

    assert result == 0
    profile = read_json_object(paths.setup_profile)
    config = read_json_object(paths.active_config)

    assert profile["selected"] == {
        "bundle": "ai-application",
        "targets": [
            "opencode",
            "vscode-copilot",
        ],
    }
    selection = cast(JsonObject, config["selection"])
    bundle_selection = cast(JsonObject, selection["bundle"])
    profile_selection = cast(JsonObject, selection["profile"])
    workflow_selection = cast(JsonObject, selection["workflow"])
    workflow = cast(JsonObject, config["workflow"])
    agent_instances = [
        cast(JsonObject, instance)
        for instance in cast(list[JsonValue], config["agentInstances"])
    ]

    assert bundle_selection["name"] == "ai-application"
    assert profile_selection["name"] == "ai-application"
    assert workflow_selection["name"] == "ai-application-delivery"
    assert workflow["name"] == "ai-application-delivery"
    assert [
        (
            instance["id"],
            cast(JsonObject, instance["profile"])["name"],
        )
        for instance in agent_instances
    ] == [
        ("requirements-worker", "Requirements"),
        ("architecture-worker", "Architect"),
        ("implementation-worker", "Implementer"),
        ("ai-evaluation-worker", "AIEvaluator"),
        ("test-runner", "TestRunner"),
        ("code-review-worker", "CodeReviewer"),
        ("qa-worker", "QA"),
        ("workflow-controller", "Orchestrator"),
    ]


@pytest.mark.parametrize(
    (
        "answer_arguments",
        "expected_answer_line",
        "expected_targets_line",
    ),
    [
        (
            (),
            ("target-platforms: opencode-and-vscode-copilot [recommended]"),
            "targets: opencode, vscode-copilot",
        ),
        (
            (
                "--answer",
                "target-platforms=opencode-only",
            ),
            "target-platforms: opencode-only [compatible]",
            "targets: opencode",
        ),
    ],
)
def test_guided_dry_run_preserves_existing_outputs(
    answer_arguments: tuple[str, ...],
    expected_answer_line: str,
    expected_targets_line: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    before = copy_existing_outputs(paths)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--guided",
            "--setup",
            "orchestrated-delivery-greenfield",
            "--dry-run",
            *answer_arguments,
        )
    )
    output = capsys.readouterr().out

    assert result == 0
    assert expected_answer_line in output
    assert expected_targets_line in output
    assert (
        "PASS: Guided dry-run validated setup "
        "'orchestrated-delivery-greenfield'; "
        "no files were written."
    ) in output
    assert "PASS: Initialized .agentic/setup-profile.json" not in output
    assert "PASS: Initialized .agentic/agentic.json" not in output
    assert_outputs_unchanged(before)


def test_guided_dry_run_prints_typed_plan_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--guided",
            "--setup",
            "lean-delivery-greenfield",
            "--dry-run",
        )
    )
    output = capsys.readouterr().out

    assert result == 0
    assert "== Generated Setup Plan ==" in output
    assert "agentInstances:" in output
    assert "roleBindings:" in output
    assert "fallbackAllowed: false" in output
    assert "no files were written" in output
    assert not paths.active_config.exists()
    assert not paths.setup_profile.exists()


def test_interactive_init_accepts_defaults_and_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    setup_name = "lean-delivery-greenfield"
    terminal = terminal_for(
        default_interactive_values(
            paths,
            setup_name,
            confirmation="y",
        )
    )

    result = main(
        ("--guided",),
        terminal=terminal,
    )

    assert result == 0
    assert paths.active_config.is_file()
    assert paths.setup_profile.is_file()


def test_interactive_back_from_first_question_reselects_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    setup_name = "lean-delivery-greenfield"
    setup = load_initialization_service(paths).guided_init.setup_by_name(setup_name)
    terminal = terminal_for(
        [
            setup_name,
            "b",
            setup_name,
            *("" for _question in setup.questions),
            "y",
        ]
    )

    result = main(
        ("--guided",),
        terminal=terminal,
    )

    assert result == 0
    assert paths.active_config.is_file()
    assert paths.setup_profile.is_file()


def test_interactive_cancellation_preserves_existing_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    before = copy_existing_outputs(paths)
    monkeypatch.chdir(tmp_path)

    result = main(
        ("--guided",),
        terminal=terminal_for(["q"]),
    )

    assert result == 1
    output = capsys.readouterr().out

    assert "== Guided Agentic Initialization ==" in output
    assert "Select a registered guided setup:" in output

    for setup_name in (
        "ai-application-greenfield",
        "lean-delivery-greenfield",
        "orchestrated-delivery-greenfield",
        "review-heavy-delivery-greenfield",
    ):
        assert setup_name in output

    assert output.endswith(
        "FAIL: interactive guided init was cancelled; no files were written\n"
    )
    assert_outputs_unchanged(before)


@pytest.mark.parametrize(
    "arguments",
    [
        ("--guided",),
        (
            "--guided",
            "--dry-run",
        ),
    ],
)
def test_interactive_mode_requires_attached_terminal(
    arguments: tuple[str, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        arguments,
        terminal=terminal_for(
            [],
            attached=False,
        ),
    )

    assert result == 1
    assert capsys.readouterr().out == (
        "FAIL: interactive --guided requires an attached terminal; "
        "use --guided --setup <setup-name> for "
        "non-interactive execution\n"
    )
    assert not paths.active_config.exists()
    assert not paths.setup_profile.exists()


def test_invalid_answer_override_fails_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--guided",
            "--setup",
            "lean-delivery-greenfield",
            "--answer",
            "unknown=value",
        )
    )

    assert result == 1
    assert "unknown setup question" in (capsys.readouterr().out)
    assert not paths.active_config.exists()
    assert not paths.setup_profile.exists()


def setup_option(
    value: str,
    classification: SetupOptionClassification = (SetupOptionClassification.RECOMMENDED),
) -> SetupOption:
    return SetupOption(
        value=value,
        label=value.title(),
        classification=classification,
        reason=f"Use {value}.",
        selection=SetupSelectionPatch(
            bundle=None,
            targets=None,
        ),
    )


def setup_question(
    question_id: str,
) -> SetupQuestion:
    return SetupQuestion(
        id=question_id,
        prompt=f"Choose {question_id}.",
        default_option="recommended",
        options=(
            setup_option("recommended"),
            setup_option("compatible"),
            setup_option(
                "blocked",
                SetupOptionClassification.BLOCKED,
            ),
        ),
    )


def interactive_setup(
    name: str = "sample",
    question_count: int = 1,
) -> Setup:
    return Setup(
        name=name,
        description="Sample setup.",
        version="0.2.0",
        mode=SetupMode.GREENFIELD,
        default_selection=SetupSelection(
            bundle="lean-delivery",
            targets=("opencode",),
        ),
        questions=tuple(
            setup_question(f"question-{index}")
            for index in range(1, question_count + 1)
        ),
    )


@pytest.mark.parametrize(
    (
        "exception",
        "expected",
    ),
    [
        (
            EOFError(),
            "received EOF",
        ),
        (
            KeyboardInterrupt(),
            "was cancelled",
        ),
    ],
)
def test_terminal_wraps_eof_and_keyboard_interrupt(
    exception: BaseException,
    expected: str,
) -> None:
    def fail_reader(_prompt: str) -> str:
        raise exception

    terminal = Terminal(
        input_reader=fail_reader,
        stdin_isatty=True,
        stdout_isatty=True,
    )

    with pytest.raises(
        InitCommandError,
        match=expected,
    ):
        terminal.read("Prompt: ")


@pytest.mark.parametrize(
    (
        "arguments",
        "expected_message",
    ),
    [
        (
            (
                "--guided",
                "--bundle",
                "lean-delivery",
            ),
            "--guided cannot be combined with --bundle",
        ),
        (
            (
                "--guided",
                "--answer",
                "target-platforms=opencode-only",
            ),
            "--answer requires --setup when used with --guided",
        ),
        (
            (
                "--setup",
                "lean-delivery-greenfield",
            ),
            "--setup requires --guided",
        ),
        (
            (
                "--answer",
                "target-platforms=opencode-only",
            ),
            "--answer requires --guided",
        ),
        (
            ("--dry-run",),
            "--dry-run requires --guided",
        ),
        (
            (),
            "one of --bundle or --guided is required",
        ),
    ],
)
def test_invalid_cli_argument_combinations_fail_fast(
    arguments: tuple[str, ...],
    expected_message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as captured:
        main(arguments)

    assert captured.value.code == 2
    assert expected_message in capsys.readouterr().err


@pytest.mark.parametrize(
    (
        "arguments",
        "expected_message",
    ),
    [
        (
            (
                "--guided",
                "--setup",
                "missing-setup",
            ),
            "unknown guided setup 'missing-setup'",
        ),
        (
            (
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--answer",
                "project-type",
            ),
            "invalid answer override 'project-type'; expected question=value",
        ),
        (
            (
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--answer",
                "missing-question=value",
            ),
            "answer overrides reference unknown setup "
            "question(s): ['missing-question']",
        ),
        (
            (
                "--guided",
                "--setup",
                "orchestrated-delivery-greenfield",
                "--answer",
                "project-type=documentation-only",
            ),
            "question 'project-type' selected blocked option 'documentation-only'",
        ),
    ],
)
def test_noninteractive_guided_init_fails_closed(
    arguments: tuple[str, ...],
    expected_message: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(arguments)

    assert result == 1
    assert expected_message in capsys.readouterr().out
    assert not paths.active_config.exists()
    assert not paths.setup_profile.exists()


def test_setup_selection_rejects_empty_registry() -> None:
    with pytest.raises(
        InitCommandError,
        match="no guided setups",
    ):
        init_module._choose_interactive_setup(
            (),
            terminal_for([]),
        )


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            "q",
            "was cancelled",
        ),
        (
            "",
            "a setup selection is required",
        ),
        (
            "3",
            "invalid setup number",
        ),
        (
            "missing",
            "unknown guided setup",
        ),
    ],
)
def test_setup_selection_rejects_invalid_input(
    value: str,
    expected: str,
) -> None:
    setups = (
        interactive_setup("first"),
        interactive_setup("second"),
    )

    with pytest.raises(
        InitCommandError,
        match=expected,
    ):
        init_module._choose_interactive_setup(
            setups,
            terminal_for([value]),
        )


@pytest.mark.parametrize(
    (
        "value",
        "expected_name",
    ),
    [
        (
            "2",
            "second",
        ),
        (
            "first",
            "first",
        ),
    ],
)
def test_setup_selection_accepts_number_or_name(
    value: str,
    expected_name: str,
) -> None:
    selected = init_module._choose_interactive_setup(
        (
            interactive_setup("first"),
            interactive_setup("second"),
        ),
        terminal_for([value]),
    )

    assert selected.name == expected_name


def test_setup_selection_uses_default_for_single_setup() -> None:
    selected = init_module._choose_interactive_setup(
        (interactive_setup(),),
        terminal_for([""]),
    )

    assert selected.name == "sample"


def test_back_navigation_revisits_previous_question() -> None:
    setup = interactive_setup(
        question_count=2,
    )

    answers = init_module._collect_interactive_answers(
        setup,
        terminal_for(
            [
                "compatible",
                "b",
                "recommended",
                "compatible",
            ]
        ),
    )

    assert answers == {
        "question-1": "recommended",
        "question-2": "compatible",
    }


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            "q",
            "was cancelled",
        ),
        (
            "4",
            "invalid option number",
        ),
        (
            "missing",
            "does not exist",
        ),
        (
            "blocked",
            "selected blocked option",
        ),
    ],
)
def test_question_selection_rejects_invalid_input(
    value: str,
    expected: str,
) -> None:
    question = setup_question("question")

    with pytest.raises(
        InitCommandError,
        match=expected,
    ):
        init_module._interactive_question_selection(
            question,
            0,
            1,
            terminal_for([value]),
        )


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            "1",
            "recommended",
        ),
        (
            "compatible",
            "compatible",
        ),
    ],
)
def test_question_selection_accepts_number_or_value(
    value: str,
    expected: str,
) -> None:
    assert (
        init_module._interactive_question_selection(
            setup_question("question"),
            0,
            1,
            terminal_for([value]),
        )
        == expected
    )


def test_question_selection_returns_back_signal() -> None:
    assert (
        init_module._interactive_question_selection(
            setup_question("question"),
            0,
            1,
            terminal_for(["b"]),
        )
        is None
    )


def test_guided_plan_renderer_rejects_direct_plan(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    plan = load_initialization_service(paths).plan_bundle("lean-delivery")

    with pytest.raises(
        InitCommandError,
        match="has no setup profile",
    ):
        init_module._print_guided_plan(plan)


def test_invalid_confirmation_fails_closed() -> None:
    with pytest.raises(
        InitCommandError,
        match="invalid confirmation",
    ):
        init_module._confirm_guided_plan(terminal_for(["maybe"]))


def test_unknown_bundle_is_reported_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    copy_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        (
            "--bundle",
            "missing",
        )
    )

    assert result == 1
    assert capsys.readouterr().out == ("FAIL: unknown bundle 'missing'\n")


def test_init_cli_renders_initialization_validation_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="AWG-INIT-999",
        message="Injected active config failure.",
    )
    error = InitializationValidationError(
        "active configuration",
        (diagnostic,),
    )

    def fail_loader(_paths: ProjectPaths) -> None:
        raise error

    monkeypatch.setattr(
        init_module,
        "load_initialization_service",
        fail_loader,
    )

    result = main(
        (
            "--bundle",
            "lean-delivery",
        )
    )

    assert result == 1
    output = capsys.readouterr().out
    assert "FAIL: Initialization validation found 1 error(s)." in output
    assert "[AWG-INIT-999]" in output


def test_init_cli_renders_guided_validation_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="AWG-GUIDED-999",
        message="Injected guided setup failure.",
    )
    error = GuidedInitValidationError(
        "guided setup",
        (diagnostic,),
    )

    def fail_loader(_paths: ProjectPaths) -> None:
        raise error

    monkeypatch.setattr(
        init_module,
        "load_initialization_service",
        fail_loader,
    )

    result = main(
        (
            "--guided",
            "--setup",
            "lean-delivery-greenfield",
        )
    )

    assert result == 1
    output = capsys.readouterr().out
    assert ("FAIL: Guided initialization validation found 1 error(s).") in output
    assert "[AWG-GUIDED-999]" in output
