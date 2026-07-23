from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEGACY_FILES = (
    "tools/acquire_auth_token.sh",
    "tools/check_environment.sh",
    "tools/create-context-zip.sh",
    "tools/build_lambda_packages.py",
    "tools/build_pdf_dependency_layer.py",
    "tools/validate_lambda_artifacts.py",
    "tools/validate_platform_v2_foundation.sh",
    "tools/replay_outbox.py",
)


def test_legacy_tooling_entrypoints_are_removed() -> None:
    assert not (ROOT / "tools/multi_site").exists()
    for relative_path in LEGACY_FILES:
        assert not (ROOT / relative_path).exists(), relative_path


def test_canonical_tooling_directories_exist() -> None:
    for directory in ("build", "prepare", "inspect", "validate", "operations", "lib"):
        assert (ROOT / "tools" / directory).is_dir(), directory


def test_gitignore_uses_canonical_runtime_environment_path() -> None:
    contents = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "tools/validate/*.env" in contents
    assert "tools/multi_site/*.env" not in contents
