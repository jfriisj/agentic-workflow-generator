"""Reproducible rendering of authoritative domain diagrams."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Sequence
from pathlib import Path

PLANTUML_VERSION = "1.2026.6"
PLANTUML_ARCHIVE_SHA256 = (
    "835c238634ed1b8638c3fdcfe4f94d005fc9664df3da2c88f80d0aaf4471b04b"
)
PLANTUML_ARCHIVE_NAME = (
    f"native-plantuml-linux-amd64-{PLANTUML_VERSION}.zip"
)
PLANTUML_ARCHIVE_URL = (
    "https://github.com/plantuml/plantuml/releases/download/"
    f"v{PLANTUML_VERSION}/{PLANTUML_ARCHIVE_NAME}"
)
DIAGRAM_DIRECTORY = Path("docs/diagrams/domain")
DOWNLOAD_TIMEOUT_SECONDS = 60
RENDER_TIMEOUT_SECONDS = 120


class DiagramRenderingError(RuntimeError):
    """Raised when the canonical diagram-rendering contract cannot be met."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_archive(path: Path) -> None:
    actual = _sha256(path)
    if actual != PLANTUML_ARCHIVE_SHA256:
        raise DiagramRenderingError(
            "PlantUML archive SHA-256 mismatch: "
            f"expected {PLANTUML_ARCHIVE_SHA256}, got {actual}"
        )


def _cache_directory() -> Path:
    configured = os.environ.get("XDG_CACHE_HOME")
    base = (
        Path(configured).expanduser()
        if configured
        else Path.home() / ".cache"
    )
    return (
        base
        / "agentic-workflow-generator"
        / "plantuml"
        / PLANTUML_VERSION
    )


def _download_archive(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.unlink(missing_ok=True)

    request = urllib.request.Request(
        PLANTUML_ARCHIVE_URL,
        headers={"User-Agent": "agentic-workflow-generator"},
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        ) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        _verify_archive(temporary)
        temporary.replace(destination)
    except (
        OSError,
        urllib.error.URLError,
        DiagramRenderingError,
    ):
        temporary.unlink(missing_ok=True)
        raise


def _ensure_archive() -> Path:
    archive = _cache_directory() / PLANTUML_ARCHIVE_NAME
    if archive.is_file():
        _verify_archive(archive)
        return archive

    _download_archive(archive)
    return archive


def _extract_renderer(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()

    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = (destination / member.filename).resolve()
            if (
                member_path != destination_root
                and destination_root not in member_path.parents
            ):
                raise DiagramRenderingError(
                    "PlantUML archive contains an unsafe member path: "
                    f"{member.filename}"
                )

        archive.extractall(destination)

    candidates = tuple(
        path
        for path in destination.rglob("plantuml")
        if path.is_file()
    )
    if len(candidates) != 1:
        raise DiagramRenderingError(
            "Expected exactly one PlantUML native executable in archive; "
            f"found {len(candidates)}"
        )

    executable = candidates[0]
    mode = executable.stat().st_mode
    executable.chmod(
        mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )
    return executable


def _validate_platform() -> None:
    machine = platform.machine().lower()
    if sys.platform != "linux" or machine not in {"amd64", "x86_64"}:
        raise DiagramRenderingError(
            "Canonical domain-diagram rendering currently requires "
            "Linux amd64."
        )


def _diagram_sources(root: Path) -> tuple[Path, ...]:
    directory = root / DIAGRAM_DIRECTORY
    sources = tuple(sorted(directory.glob("*.puml")))
    if not sources:
        raise DiagramRenderingError(
            f"No authoritative PlantUML sources found under {directory}."
        )
    return sources


def _run_renderer(
    renderer: Path,
    sources: tuple[Path, ...],
    *,
    cwd: Path,
) -> None:
    environment = dict(os.environ)
    environment["GRAPHVIZ_DOT"] = "/definitely/missing/dot"

    completed = subprocess.run(
        [
            str(renderer),
            "-Playout=smetana",
            "-tsvg",
            *(str(source) for source in sources),
        ],
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=RENDER_TIMEOUT_SECONDS,
    )

    if completed.returncode != 0:
        raise DiagramRenderingError(
            "PlantUML rendering failed with exit code "
            f"{completed.returncode}: {completed.stdout.strip()}"
        )


def _copy_sources(
    sources: tuple[Path, ...],
    destination: Path,
) -> tuple[Path, ...]:
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for source in sources:
        target = destination / source.name
        shutil.copyfile(source, target)
        copied.append(target)
    return tuple(copied)


def _mismatched_svgs(
    sources: tuple[Path, ...],
    rendered_directory: Path,
) -> tuple[str, ...]:
    mismatches: list[str] = []
    for source in sources:
        committed = source.with_suffix(".svg")
        rendered = rendered_directory / committed.name
        if not committed.is_file() or not rendered.is_file():
            mismatches.append(committed.name)
            continue
        if committed.read_bytes() != rendered.read_bytes():
            mismatches.append(committed.name)
    return tuple(mismatches)


def _render(
    *,
    root: Path,
    check: bool,
) -> int:
    _validate_platform()
    sources = _diagram_sources(root)
    archive = _ensure_archive()

    with tempfile.TemporaryDirectory(
        prefix="agentic-domain-diagrams-"
    ) as temporary_name:
        temporary = Path(temporary_name)
        renderer = _extract_renderer(
            archive,
            temporary / "renderer",
        )

        if check:
            rendered_directory = temporary / "check"
            copied_sources = _copy_sources(
                sources,
                rendered_directory,
            )
            _run_renderer(
                renderer,
                copied_sources,
                cwd=root,
            )
            mismatches = _mismatched_svgs(
                sources,
                rendered_directory,
            )
            if mismatches:
                print(
                    "ERROR: Canonical domain-diagram SVG drift detected:",
                    file=sys.stderr,
                )
                for mismatch in mismatches:
                    print(f"- {mismatch}", file=sys.stderr)
                return 1

            print(
                "PASS: Domain-diagram SVGs match canonical rendering. "
                f"Checked {len(sources)} diagram(s)."
            )
            return 0

        _run_renderer(
            renderer,
            sources,
            cwd=root,
        )

    print(
        "PASS: Rendered canonical domain-diagram SVGs. "
        f"Updated {len(sources)} diagram(s)."
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Render or verify authoritative domain diagrams."""
    parser = argparse.ArgumentParser(
        prog="render-domain-diagrams",
        description=(
            "Render authoritative PlantUML domain diagrams with the "
            "repository-pinned renderer."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed SVG files without modifying the repository",
    )
    arguments = parser.parse_args(argv)

    try:
        return _render(
            root=Path.cwd().resolve(),
            check=bool(arguments.check),
        )
    except (
        DiagramRenderingError,
        OSError,
        subprocess.SubprocessError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
