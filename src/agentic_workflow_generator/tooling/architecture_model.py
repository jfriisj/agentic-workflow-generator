"""Validate and export the canonical Structurizr architecture model."""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from agentic_workflow_generator.tooling import domain_diagrams

STRUCTURIZR_RELEASE = "2026.06.28"
STRUCTURIZR_TAG = "2026.06.28-noble"
STRUCTURIZR_REPOSITORY = "structurizr/structurizr"
STRUCTURIZR_DIGEST = (
    "sha256:b5140a2a783b0cc780fe4b54dcfeecb565ddd5fce5a578e7ff600b78ad0cc03a"
)
STRUCTURIZR_IMAGE = f"{STRUCTURIZR_REPOSITORY}@{STRUCTURIZR_DIGEST}"
STRUCTURIZR_TAGGED_IMAGE = f"{STRUCTURIZR_REPOSITORY}:{STRUCTURIZR_TAG}"

WORKSPACE_PATH = Path("docs/architecture/workspace.dsl")
WORKSPACE_DIRECTORY = WORKSPACE_PATH.parent
EXPECTED_VIEW_KEYS = frozenset(
    {
        "SystemContext",
        "CompilerResponsibilities",
    }
)
EXPECTED_EXPORT_FILENAMES = frozenset(
    {
        "structurizr-SystemContext.puml",
        "structurizr-SystemContext-key.puml",
        "structurizr-CompilerResponsibilities.puml",
        "structurizr-CompilerResponsibilities-key.puml",
    }
)
VIEW_EXPORTS = {
    "SystemContext": "structurizr-SystemContext.puml",
    "CompilerResponsibilities": "structurizr-CompilerResponsibilities.puml",
}
COMMITTED_SVGS = {
    "SystemContext": Path("docs/architecture/diagrams/system-context.svg"),
    "CompilerResponsibilities": Path(
        "docs/architecture/diagrams/compiler-responsibilities.svg"
    ),
}

_REMOTE_URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)
_WORKSPACE_EXTENDS_PATTERN = re.compile(
    r"^\s*workspace\s+extends\b",
    re.IGNORECASE | re.MULTILINE,
)
_DISALLOWED_DIRECTIVE_PATTERN = re.compile(
    r"^\s*!(?:plugin|script)\b",
    re.IGNORECASE | re.MULTILINE,
)


class ArchitectureModelError(RuntimeError):
    """Raised when the canonical architecture-model contract is not met."""


def _run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _validate_platform() -> None:
    machine = platform.machine().lower()
    if platform.system().lower() != "linux" or machine not in {
        "amd64",
        "x86_64",
    }:
        raise ArchitectureModelError(
            "Canonical architecture-model validation currently requires "
            "Linux amd64."
        )


def _require_docker() -> None:
    if shutil.which("docker") is None:
        raise ArchitectureModelError(
            "Docker is required for architecture-model validation tooling."
        )


def _verify_image_metadata(image: Mapping[str, object]) -> None:
    image_id = image.get("Id")
    os_name = image.get("Os")
    architecture = image.get("Architecture")
    repo_digests = image.get("RepoDigests")

    expected_repo_digest = (
        f"{STRUCTURIZR_REPOSITORY}@{STRUCTURIZR_DIGEST}"
    )

    if image_id != STRUCTURIZR_DIGEST:
        raise ArchitectureModelError(
            "Pinned Structurizr image ID mismatch: "
            f"expected {STRUCTURIZR_DIGEST}, got {image_id!r}."
        )
    if os_name != "linux":
        raise ArchitectureModelError(
            "Pinned Structurizr image OS mismatch: "
            f"expected 'linux', got {os_name!r}."
        )
    if architecture != "amd64":
        raise ArchitectureModelError(
            "Pinned Structurizr image architecture mismatch: "
            f"expected 'amd64', got {architecture!r}."
        )
    if not isinstance(repo_digests, list) or expected_repo_digest not in (
        item for item in repo_digests if isinstance(item, str)
    ):
        raise ArchitectureModelError(
            "Pinned Structurizr repository digest is unavailable or "
            "does not match the accepted artifact."
        )


def _verify_local_image() -> None:
    completed = _run(
        [
            "docker",
            "image",
            "inspect",
            STRUCTURIZR_IMAGE,
        ]
    )
    if completed.returncode != 0:
        raise ArchitectureModelError(
            "Pinned Structurizr image is not available locally. "
            "Run `uv run architecture-model prepare` explicitly before "
            "normal validation."
        )

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ArchitectureModelError(
            "Docker returned invalid JSON while inspecting the pinned "
            "Structurizr image."
        ) from exc

    if not isinstance(payload, list) or len(payload) != 1:
        raise ArchitectureModelError(
            "Expected exactly one Docker image inspection result."
        )
    image = payload[0]
    if not isinstance(image, dict):
        raise ArchitectureModelError(
            "Docker image inspection result has an invalid shape."
        )

    _verify_image_metadata(image)


def _structurizr_command(
    arguments: Sequence[str],
    *,
    workdir: Path | None = None,
) -> list[str]:
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
    ]
    if workdir is not None:
        mount = f"{workdir.resolve()}:/usr/local/structurizr"
        command.extend(
            [
                "--volume",
                mount,
                "--workdir",
                "/usr/local/structurizr",
            ]
        )
    command.extend(
        [
            STRUCTURIZR_IMAGE,
            *arguments,
        ]
    )
    return command


def _run_structurizr(
    arguments: Sequence[str],
    *,
    workdir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return _run(
        _structurizr_command(arguments, workdir=workdir),
    )


def _verify_structurizr_version() -> None:
    completed = _run_structurizr(["version"])
    if completed.returncode != 0:
        raise ArchitectureModelError(
            "Pinned Structurizr image could not report its version: "
            f"{completed.stdout.strip()}"
        )

    expected = f"structurizr: {STRUCTURIZR_RELEASE}"
    if expected not in completed.stdout:
        raise ArchitectureModelError(
            "Pinned Structurizr release mismatch: expected "
            f"{expected!r} in version output."
        )


def _dsl_sources(root: Path) -> tuple[Path, ...]:
    architecture_directory = root / WORKSPACE_DIRECTORY
    workspace = root / WORKSPACE_PATH

    if not workspace.is_file():
        raise ArchitectureModelError(
            f"Canonical workspace is missing: {WORKSPACE_PATH}."
        )

    sources = tuple(sorted(architecture_directory.rglob("*.dsl")))
    if workspace not in sources:
        raise ArchitectureModelError(
            "Canonical workspace was not discovered as a DSL source."
        )
    return sources


def _validate_source_policy(root: Path) -> None:
    forbidden_workspace_json = root / WORKSPACE_DIRECTORY / "workspace.json"
    if forbidden_workspace_json.exists():
        raise ArchitectureModelError(
            "A committed/manual workspace.json is not permitted."
        )

    for source in _dsl_sources(root):
        text = source.read_text(encoding="utf-8")
        relative = source.relative_to(root)

        if _REMOTE_URL_PATTERN.search(text):
            raise ArchitectureModelError(
                f"Remote URL dependency is not permitted in {relative}."
            )
        if _WORKSPACE_EXTENDS_PATTERN.search(text):
            raise ArchitectureModelError(
                f"Workspace extension is not permitted in {relative}; "
                "the repository owns one canonical root workspace."
            )
        if _DISALLOWED_DIRECTIVE_PATTERN.search(text):
            raise ArchitectureModelError(
                f"Plugins/scripts are not admitted in {relative}."
            )


def _copy_workspace_sources(root: Path, destination: Path) -> None:
    source_root = root / WORKSPACE_DIRECTORY
    target_root = destination / WORKSPACE_DIRECTORY

    for source in _dsl_sources(root):
        relative = source.relative_to(source_root)
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _validate_workspace(workdir: Path) -> None:
    completed = _run_structurizr(
        [
            "validate",
            "-workspace",
            str(WORKSPACE_PATH),
        ],
        workdir=workdir,
    )
    if completed.returncode != 0:
        raise ArchitectureModelError(
            "Structurizr workspace validation failed: "
            f"{completed.stdout.strip()}"
        )


def _export_workspace_json(workdir: Path) -> Mapping[str, object]:
    output = workdir / "export-json"
    output.mkdir()

    completed = _run_structurizr(
        [
            "export",
            "-workspace",
            str(WORKSPACE_PATH),
            "-format",
            "json",
            "-output",
            "export-json",
        ],
        workdir=workdir,
    )
    if completed.returncode != 0:
        raise ArchitectureModelError(
            "Structurizr JSON export failed: "
            f"{completed.stdout.strip()}"
        )

    candidates = tuple(sorted(output.rglob("*.json")))
    if len(candidates) != 1:
        raise ArchitectureModelError(
            "Expected exactly one Structurizr JSON workspace export; "
            f"found {len(candidates)}."
        )

    try:
        payload = json.loads(candidates[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArchitectureModelError(
            "Structurizr JSON export is invalid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise ArchitectureModelError(
            "Structurizr JSON export has an invalid root shape."
        )
    return payload


def _view_keys(payload: Mapping[str, object]) -> frozenset[str]:
    views = payload.get("views")
    if not isinstance(views, dict):
        return frozenset()

    groups = (
        "systemLandscapeViews",
        "systemContextViews",
        "containerViews",
        "componentViews",
        "dynamicViews",
        "deploymentViews",
        "filteredViews",
        "customViews",
        "imageViews",
    )
    keys: set[str] = set()

    for group in groups:
        entries = views.get(group)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            key = entry.get("key")
            if isinstance(key, str):
                keys.add(key)

    return frozenset(keys)


def _verify_expected_views(payload: Mapping[str, object]) -> None:
    actual = _view_keys(payload)
    missing = EXPECTED_VIEW_KEYS - actual
    if missing:
        raise ArchitectureModelError(
            "Canonical architecture workspace is missing expected view "
            "key(s): "
            + ", ".join(sorted(missing))
        )


def _export_plantuml(workdir: Path, directory_name: str) -> dict[str, bytes]:
    output = workdir / directory_name
    output.mkdir()

    completed = _run_structurizr(
        [
            "export",
            "-workspace",
            str(WORKSPACE_PATH),
            "-format",
            "plantuml",
            "-output",
            directory_name,
        ],
        workdir=workdir,
    )
    if completed.returncode != 0:
        raise ArchitectureModelError(
            "Structurizr PlantUML export failed: "
            f"{completed.stdout.strip()}"
        )

    files = tuple(sorted(output.rglob("*.puml")))
    if not files:
        raise ArchitectureModelError(
            "Structurizr PlantUML export produced no diagram definitions."
        )

    return {
        str(path.relative_to(output)): path.read_bytes()
        for path in files
    }


def _verify_deterministic_export(
    first: Mapping[str, bytes],
    second: Mapping[str, bytes],
) -> None:
    if dict(first) != dict(second):
        raise ArchitectureModelError(
            "Repeated Structurizr PlantUML exports are not byte-identical."
        )


def _verify_plantuml_export_shape(exported: Mapping[str, bytes]) -> None:
    actual = frozenset(exported)
    if actual != EXPECTED_EXPORT_FILENAMES:
        missing = sorted(EXPECTED_EXPORT_FILENAMES - actual)
        unexpected = sorted(actual - EXPECTED_EXPORT_FILENAMES)
        details: list[str] = []
        if missing:
            details.append("missing=" + ", ".join(missing))
        if unexpected:
            details.append("unexpected=" + ", ".join(unexpected))
        raise ArchitectureModelError(
            "Structurizr PlantUML export shape changed: "
            + "; ".join(details)
        )


def _require_cached_renderer_archive(
    *,
    directory: Path,
    archive_name: str,
    expected_sha256: str,
    label: str,
) -> Path:
    archive = directory / archive_name
    if not archive.is_file():
        raise ArchitectureModelError(
            f"{label} is not available in the local tool cache. "
            "Run `uv run architecture-model prepare` explicitly before "
            "normal validation/rendering."
        )
    try:
        domain_diagrams._verify_sha256(
            archive,
            expected=expected_sha256,
            label=label,
        )
    except domain_diagrams.DiagramRenderingError as exc:
        raise ArchitectureModelError(str(exc)) from exc
    return archive


def _cached_renderer_inputs() -> tuple[Path, Path]:
    cache = domain_diagrams._cache_root()
    plantuml = _require_cached_renderer_archive(
        directory=cache / "plantuml" / domain_diagrams.PLANTUML_VERSION,
        archive_name=domain_diagrams.PLANTUML_ARCHIVE_NAME,
        expected_sha256=domain_diagrams.PLANTUML_ARCHIVE_SHA256,
        label="PlantUML archive",
    )
    dejavu = _require_cached_renderer_archive(
        directory=cache / "fonts" / "dejavu" / domain_diagrams.DEJAVU_VERSION,
        archive_name=domain_diagrams.DEJAVU_ARCHIVE_NAME,
        expected_sha256=domain_diagrams.DEJAVU_ARCHIVE_SHA256,
        label="DejaVu font archive",
    )
    return plantuml, dejavu


def _render_selected_views(
    *,
    workdir: Path,
    export_directory: Path,
) -> dict[str, bytes]:
    sources: list[Path] = []
    source_by_key: dict[str, Path] = {}
    for key, filename in VIEW_EXPORTS.items():
        source = export_directory / filename
        if not source.is_file():
            raise ArchitectureModelError(
                f"Expected Structurizr view export is missing: {filename}."
            )
        sources.append(source)
        source_by_key[key] = source

    plantuml_archive, dejavu_archive = _cached_renderer_inputs()
    renderer = domain_diagrams._extract_renderer(
        plantuml_archive,
        workdir / "renderer",
    )
    font_directory = domain_diagrams._extract_fonts(
        dejavu_archive,
        workdir / "fonts",
    )
    fontconfig = domain_diagrams._write_fontconfig(
        font_directory=font_directory,
        destination=workdir / "fontconfig",
    )
    domain_diagrams._run_renderer(
        renderer,
        tuple(sources),
        cwd=workdir,
        fontconfig=fontconfig,
    )

    rendered: dict[str, bytes] = {}
    for key, source in source_by_key.items():
        svg = source.with_suffix(".svg")
        if not svg.is_file():
            raise ArchitectureModelError(
                f"PlantUML did not produce the expected SVG for {key}."
            )
        rendered[key] = svg.read_bytes()
    return rendered


def _verify_committed_svgs(
    *,
    root: Path,
    rendered: Mapping[str, bytes],
) -> None:
    mismatches: list[str] = []
    for key, relative in COMMITTED_SVGS.items():
        committed = root / relative
        expected = rendered.get(key)
        if expected is None:
            mismatches.append(str(relative))
            continue
        if not committed.is_file() or committed.read_bytes() != expected:
            mismatches.append(str(relative))
    if mismatches:
        raise ArchitectureModelError(
            "Canonical architecture SVG drift detected: "
            + ", ".join(mismatches)
        )


def _write_committed_svgs(
    *,
    root: Path,
    rendered: Mapping[str, bytes],
) -> None:
    for key, relative in COMMITTED_SVGS.items():
        content = rendered.get(key)
        if content is None:
            raise ArchitectureModelError(
                f"No rendered SVG is available for expected view {key}."
            )
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def _validated_exports(
    *,
    root: Path,
    temporary: Path,
) -> tuple[dict[str, bytes], Path]:
    _copy_workspace_sources(root, temporary)
    _validate_workspace(temporary)
    payload = _export_workspace_json(temporary)
    _verify_expected_views(payload)

    first_directory = temporary / "plantuml-first"
    first = _export_plantuml(temporary, "plantuml-first")
    _verify_plantuml_export_shape(first)

    second = _export_plantuml(temporary, "plantuml-second")
    _verify_plantuml_export_shape(second)
    _verify_deterministic_export(first, second)
    return first, first_directory


def _verify_unresolved_reference_fails(workdir: Path) -> None:
    probe = workdir / "unresolved-reference.dsl"
    probe.write_text(
        "workspace {\n"
        "    model {\n"
        "        source = softwareSystem \"Source\"\n"
        "        source -> missing \"Must fail\"\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    completed = _run_structurizr(
        [
            "validate",
            "-workspace",
            probe.name,
        ],
        workdir=workdir,
    )
    if completed.returncode == 0:
        raise ArchitectureModelError(
            "Pinned Structurizr validation unexpectedly accepted an "
            "unresolved relationship destination."
        )


def _prepare() -> int:
    _validate_platform()
    _require_docker()

    completed = _run(
        [
            "docker",
            "pull",
            STRUCTURIZR_IMAGE,
        ]
    )
    if completed.returncode != 0:
        raise ArchitectureModelError(
            "Explicit Structurizr image acquisition failed: "
            f"{completed.stdout.strip()}"
        )

    _verify_local_image()
    _verify_structurizr_version()

    try:
        domain_diagrams._ensure_plantuml_archive()
        domain_diagrams._ensure_dejavu_archive()
    except domain_diagrams.DiagramRenderingError as exc:
        raise ArchitectureModelError(str(exc)) from exc

    print(
        "PASS: Prepared pinned architecture-model toolchain: "
        f"Structurizr {STRUCTURIZR_RELEASE} ({STRUCTURIZR_DIGEST}), "
        f"PlantUML {domain_diagrams.PLANTUML_VERSION}, and "
        f"DejaVu {domain_diagrams.DEJAVU_VERSION}."
    )
    return 0


def _render(root: Path) -> int:
    _validate_platform()
    _require_docker()
    _validate_source_policy(root)
    _verify_local_image()
    _verify_structurizr_version()

    with tempfile.TemporaryDirectory(
        prefix="agentic-architecture-model-"
    ) as temporary_name:
        temporary = Path(temporary_name)
        _exports, first_directory = _validated_exports(
            root=root,
            temporary=temporary,
        )
        rendered = _render_selected_views(
            workdir=temporary,
            export_directory=first_directory,
        )
        _write_committed_svgs(root=root, rendered=rendered)

    print(
        "PASS: Rendered canonical architecture SVGs. "
        f"Updated {len(rendered)} view(s)."
    )
    return 0


def _check(root: Path) -> int:
    _validate_platform()
    _require_docker()
    _validate_source_policy(root)
    _verify_local_image()
    _verify_structurizr_version()

    with tempfile.TemporaryDirectory(
        prefix="agentic-architecture-model-"
    ) as temporary_name:
        temporary = Path(temporary_name)
        _verify_unresolved_reference_fails(temporary)
        exports, first_directory = _validated_exports(
            root=root,
            temporary=temporary,
        )
        rendered = _render_selected_views(
            workdir=temporary,
            export_directory=first_directory,
        )
        _verify_committed_svgs(root=root, rendered=rendered)

    print(
        "PASS: Canonical Structurizr workspace validates with expected "
        "views, deterministic PlantUML export, and synchronized SVGs "
        f"({len(VIEW_EXPORTS)} view(s), {len(exports)} export file(s))."
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run architecture-model preparation or validation."""
    parser = argparse.ArgumentParser(
        prog="architecture-model",
        description=(
            "Prepare or validate the pinned canonical Structurizr "
            "architecture model."
        ),
    )
    parser.add_argument(
        "command",
        choices=("prepare", "render", "check"),
        help=(
            "prepare explicitly acquires the pinned toolchain; render "
            "regenerates committed SVGs; check performs offline fail-closed "
            "validation using the local pinned toolchain"
        ),
    )
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "prepare":
            return _prepare()
        root = Path.cwd().resolve()
        if arguments.command == "render":
            return _render(root)
        return _check(root)
    except (
        ArchitectureModelError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
