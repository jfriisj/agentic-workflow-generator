from pathlib import Path

import pytest

from agentic_workflow_generator.registry import ProjectPaths


def test_project_paths_require_absolute_root() -> None:
    with pytest.raises(
        ValueError,
        match="Repository root must be an absolute path",
    ):
        ProjectPaths(Path("relative-repository"))


def test_project_paths_require_existing_root(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        ProjectPaths(missing)


def test_project_paths_expose_canonical_locations(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths(tmp_path)

    assert paths.registry_root == tmp_path / "registry"
    assert paths.schema_root == (tmp_path / ".agentic" / "schemas")
    assert paths.active_config == (tmp_path / ".agentic" / "agentic.json")
    assert paths.setup_profile == (
        tmp_path / ".agentic" / "setup-profile.json"
    )
    assert paths.generated_root == (tmp_path / ".agentic" / "generated")
    assert paths.lockfile == (tmp_path / ".agentic" / "agentic-lock.json")
    assert paths.manifest == (
        tmp_path / ".agentic" / "generated" / "output-manifest.json"
    )


@pytest.mark.parametrize(
    "unsafe_path",
    [
        Path("/tmp/outside.json"),
        Path("../outside.json"),
        Path("registry/../../outside.json"),
    ],
)
def test_repository_path_rejects_unsafe_paths(
    tmp_path: Path,
    unsafe_path: Path,
) -> None:
    paths = ProjectPaths(tmp_path)

    with pytest.raises(ValueError):
        paths.repository_path(unsafe_path)


def test_repository_path_resolves_safe_path(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths(tmp_path)

    result = paths.repository_path("registry/bundles/example.bundle.json")

    assert result == (tmp_path / "registry" / "bundles" / "example.bundle.json")


def test_owned_path_rejects_path_outside_owned_root(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths(tmp_path)

    with pytest.raises(
        ValueError,
        match="escapes the owned root",
    ):
        paths.owned_path(
            ".opencode",
            ".github/agents/example.md",
        )


def test_owned_path_accepts_path_inside_owned_root(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths(tmp_path)

    result = paths.owned_path(
        ".opencode",
        ".opencode/agents/example.md",
    )

    assert result == (tmp_path / ".opencode" / "agents" / "example.md")


def test_project_paths_require_directory_root(
    tmp_path: Path,
) -> None:
    file_root = tmp_path / "repository-file"
    file_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Repository root must be a directory",
    ):
        ProjectPaths(file_root)


def test_repository_path_rejects_empty_path(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths(tmp_path)

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        paths.repository_path(Path())


def test_repository_path_rejects_symlink_escape(
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository"
    repository_root.mkdir()

    outside_root = tmp_path / "outside"
    outside_root.mkdir()

    escape = repository_root / "escape"
    escape.symlink_to(outside_root, target_is_directory=True)

    paths = ProjectPaths(repository_root)

    with pytest.raises(
        ValueError,
        match="escapes the repository root",
    ):
        paths.repository_path("escape/generated.json")
