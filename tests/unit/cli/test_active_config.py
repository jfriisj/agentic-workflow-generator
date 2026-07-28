from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from agentic_workflow_generator.cli.active_config import (
    main,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
CONFIG_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "agentic.json"
)
SCHEMA_SOURCE = (
    REPOSITORY_ROOT
    / ".agentic"
    / "schemas"
    / "agentic.schema.json"
)


def test_active_config_cli_accepts_valid_config(
    capsys,
) -> None:
    result = main(
        (
            str(CONFIG_SOURCE),
            str(SCHEMA_SOURCE),
        )
    )

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Active configuration is valid: "
        f"{CONFIG_SOURCE}\n"
    )


def test_active_config_cli_rejects_duplicate_target(
    tmp_path: Path,
    capsys,
) -> None:
    config = _read_json(CONFIG_SOURCE)
    targets = cast(list[Any], config["targets"])
    targets.append(dict(cast(dict[str, Any], targets[0])))
    config_path = tmp_path / "agentic.json"
    _write_json(config_path, config)

    result = main(
        (
            str(config_path),
            str(SCHEMA_SOURCE),
        )
    )

    assert result == 1
    output = capsys.readouterr().out
    assert "AWG-ACTIVE-CONFIG-001" in output
    assert "non-unique elements" in output


def test_active_config_cli_rejects_invalid_target_enabled(
    tmp_path: Path,
    capsys,
) -> None:
    config = _read_json(CONFIG_SOURCE)
    targets = cast(list[Any], config["targets"])
    first_target = cast(dict[str, Any], targets[0])
    first_target["enabled"] = "true"
    config_path = tmp_path / "agentic.json"
    _write_json(config_path, config)

    result = main(
        (
            str(config_path),
            str(SCHEMA_SOURCE),
        )
    )

    assert result == 1
    output = capsys.readouterr().out
    assert "AWG-ACTIVE-CONFIG-001" in output
    assert "enabled" in output


def test_active_config_cli_reports_missing_config(
    tmp_path: Path,
    capsys,
) -> None:
    missing = tmp_path / "missing.json"

    result = main(
        (
            str(missing),
            str(SCHEMA_SOURCE),
        )
    )

    assert result == 1
    output = capsys.readouterr().out
    assert "AWG-ACTIVE-CONFIG-900" in output
    assert str(missing) in output


def _read_json(path: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
