from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LEGACY_FILES = (
    "INSTALL.md",
    "README.txt",
    "tools/prepare/mr014_certification.sh",
    "tools/prepare/mr014_tfvars.py",
    "tools/validate/mr009d3b_runtime.sh",
    "tools/validate/mr009d4_runtime.sh",
)


def test_legacy_tooling_and_document_entrypoints_are_removed() -> None:
    assert not (ROOT / "tools/multi_site").exists()
    assert not (ROOT / "scripts").exists()
    for relative_path in LEGACY_FILES:
        assert not (ROOT / relative_path).exists(), relative_path


def test_canonical_tooling_directories_and_dispatchers_exist() -> None:
    for directory in ("build", "prepare", "inspect", "validate", "operations", "lib"):
        path = ROOT / "tools" / directory
        assert path.is_dir(), directory
        if directory != "lib":
            assert (path / "run.sh").is_file(), directory


def test_repository_architecture_document_exists() -> None:
    assert (ROOT / "docs/architecture/REPOSITORY_STRUCTURE.md").is_file()


def test_gitignore_uses_canonical_runtime_environment_path() -> None:
    contents = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "tools/validate/*.env" in contents
    assert "tools/multi_site/*.env" not in contents
