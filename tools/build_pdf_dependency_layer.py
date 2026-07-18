from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


FIXED_MTIME = 946684800
IGNORED_NAMES = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def normalize_tree(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file() and path.suffix in IGNORED_SUFFIXES:
            path.unlink()
            continue

    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir() and path.name in IGNORED_NAMES:
            shutil.rmtree(path)
            continue

    for path in sorted(root.rglob("*")):
        if path.is_file():
            path.chmod(0o644)
            os.utime(path, (FIXED_MTIME, FIXED_MTIME))
        elif path.is_dir():
            path.chmod(0o755)
            os.utime(path, (FIXED_MTIME, FIXED_MTIME))


def build_pdf_dependency_layer(
    *,
    repository_root: Path,
    output_root: Path | None = None,
) -> Path:
    requirements = repository_root / "lambda_layer" / "requirements.txt"
    if not requirements.is_file():
        raise FileNotFoundError(
            f"Required layer requirements file does not exist: {requirements}"
        )

    layer_root = (
        output_root
        if output_root is not None
        else repository_root / "build" / "lambda_layer" / "pdf_dependencies"
    )

    if layer_root.exists():
        shutil.rmtree(layer_root)

    python_root = layer_root / "python"
    python_root.mkdir(parents=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-compile",
            "--platform",
            "manylinux2014_aarch64",
            "--implementation",
            "cp",
            "--python-version",
            "3.13",
            "--abi",
            "cp313",
            "--only-binary=:all:",
            "--target",
            str(python_root),
            "-r",
            str(requirements),
        ],
        check=True,
    )

    normalize_tree(layer_root)

    if not (python_root / "pypdf").is_dir():
        raise RuntimeError("PDF dependency layer does not contain python/pypdf")

    return layer_root


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Lambda PDF dependency layer."
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--output-root", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    layer_root = build_pdf_dependency_layer(
        repository_root=args.repository_root.resolve(),
        output_root=(
            args.output_root.resolve()
            if args.output_root is not None
            else None
        ),
    )

    files = sorted(
        path.relative_to(layer_root).as_posix()
        for path in layer_root.rglob("*")
        if path.is_file()
    )

    print(f"pdf_dependencies: {len(files)} files")
    print("  python/pypdf/")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
