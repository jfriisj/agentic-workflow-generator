from __future__ import annotations

import hashlib
import subprocess
import zipfile
from pathlib import Path

import pytest

from agentic_workflow_generator.tooling import domain_diagrams


def test_verify_sha256_accepts_expected_hash(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "asset.zip"
    archive.write_bytes(b"verified archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    domain_diagrams._verify_sha256(
        archive,
        expected=digest,
        label="Test asset",
    )


def test_verify_sha256_rejects_hash_mismatch(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "asset.zip"
    archive.write_bytes(b"tampered archive")

    with pytest.raises(
        domain_diagrams.DiagramRenderingError,
        match="SHA-256 mismatch",
    ):
        domain_diagrams._verify_sha256(
            archive,
            expected="0" * 64,
            label="Test asset",
        )


def test_extract_renderer_requires_complete_native_distribution(
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


def test_extract_fonts_requires_canonical_dejavu_family(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "dejavu.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name in (
            "DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf",
            "DejaVuSans-Oblique.ttf",
            "DejaVuSans-BoldOblique.ttf",
        ):
            archive.writestr(f"dejavu/ttf/{name}", b"font")

    font_directory = domain_diagrams._extract_fonts(
        archive_path,
        tmp_path / "extract",
    )

    assert font_directory.name == "ttf"
    assert (font_directory / "DejaVuSans.ttf").is_file()


def test_write_fontconfig_isolates_font_directory(
    tmp_path: Path,
) -> None:
    font_directory = tmp_path / "fonts"
    font_directory.mkdir()

    config = domain_diagrams._write_fontconfig(
        font_directory=font_directory,
        destination=tmp_path / "fontconfig",
    )

    content = config.read_text(encoding="utf-8")
    assert f"<dir>{font_directory.resolve()}</dir>" in content
    assert "<cachedir>" in content
    assert "/usr/share/fonts" not in content


def test_run_renderer_pins_fontconfig_and_font_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renderer = tmp_path / "plantuml"
    renderer.write_bytes(b"binary")
    source = tmp_path / "domain.puml"
    source.write_text("@startuml\n@enduml\n", encoding="utf-8")
    fontconfig = tmp_path / "fonts.conf"
    fontconfig.write_text("<fontconfig/>\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    domain_diagrams._run_renderer(
        renderer,
        (source,),
        cwd=tmp_path,
        fontconfig=fontconfig,
    )

    command = captured["command"]
    assert isinstance(command, list)
    assert "-SdefaultFontName=DejaVu Sans" in command

    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["GRAPHVIZ_DOT"] == "/definitely/missing/dot"
    assert environment["FONTCONFIG_FILE"] == str(fontconfig.resolve())
    assert environment["FONTCONFIG_PATH"] == str(
        fontconfig.parent.resolve()
    )


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
