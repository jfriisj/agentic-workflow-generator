from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from agentic_workflow_generator.tooling import domain_diagrams


def test_verify_archive_accepts_expected_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "plantuml.zip"
    archive.write_bytes(b"verified archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    monkeypatch.setattr(
        domain_diagrams,
        "PLANTUML_ARCHIVE_SHA256",
        digest,
    )

    domain_diagrams._verify_archive(archive)


def test_verify_archive_rejects_hash_mismatch(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "plantuml.zip"
    archive.write_bytes(b"tampered archive")

    with pytest.raises(
        domain_diagrams.DiagramRenderingError,
        match="SHA-256 mismatch",
    ):
        domain_diagrams._verify_archive(archive)


def test_extract_renderer_requires_single_native_executable(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "plantuml.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("distribution/plantuml", b"binary")
        archive.writestr(
            "distribution/lib/libawt.so",
            b"native dependency",
        )

    extract_directory = tmp_path / "extract"
    renderer = domain_diagrams._extract_renderer(
        archive_path,
        extract_directory,
    )

    assert renderer.name == "plantuml"
    assert renderer.is_file()
    assert (
        extract_directory
        / "distribution"
        / "lib"
        / "libawt.so"
    ).is_file()


def test_mismatched_svgs_reports_changed_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "domain.puml"
    source.write_text("@startuml\n@enduml\n", encoding="utf-8")
    source.with_suffix(".svg").write_bytes(b"committed")

    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / "domain.svg").write_bytes(b"rendered")

    assert domain_diagrams._mismatched_svgs(
        (source,),
        rendered,
    ) == ("domain.svg",)


def test_mismatched_svgs_accepts_identical_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "domain.puml"
    source.write_text("@startuml\n@enduml\n", encoding="utf-8")
    source.with_suffix(".svg").write_bytes(b"same")

    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / "domain.svg").write_bytes(b"same")

    assert domain_diagrams._mismatched_svgs(
        (source,),
        rendered,
    ) == ()
