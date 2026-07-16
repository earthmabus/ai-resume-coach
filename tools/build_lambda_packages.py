from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


FIXED_MTIME = 946684800  # 2000-01-01T00:00:00Z
IGNORED_NAMES = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class LambdaPackage:
    name: str
    handler_source: str
    shared_directories: tuple[str, ...] = ()


PACKAGES = (
    LambdaPackage(
        name="api",
        handler_source="src/lambdas/api/handler.py",
        shared_directories=(
            "src/core",
            "src/features",
            "src/providers",
        ),
    ),
    LambdaPackage(
        name="worker",
        handler_source="src/lambdas/worker/handler.py",
        shared_directories=(
            "src/providers",
        ),
    ),
    LambdaPackage(
        name="outbox_publisher",
        handler_source=(
            "src/lambdas/outbox_publisher/handler.py"
        ),
        shared_directories=(
            "src/core",
        ),
    ),
    LambdaPackage(
        name="registration_notification",
        handler_source=(
            "src/lambdas/registration_notification/handler.py"
        ),
    ),
)


def should_ignore(path: Path) -> bool:
    return (
        any(part in IGNORED_NAMES for part in path.parts)
        or path.suffix in IGNORED_SUFFIXES
    )


def normalize_file(path: Path) -> None:
    path.chmod(0o644)
    os.utime(path, (FIXED_MTIME, FIXED_MTIME))


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(
            f"Required package source file does not exist: {source}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    normalize_file(destination)


def copy_directory(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(
            f"Required package source directory does not exist: {source}"
        )

    for source_file in sorted(source.rglob("*")):
        if not source_file.is_file() or should_ignore(source_file):
            continue

        relative_path = source_file.relative_to(source)
        copy_file(source_file, destination / relative_path)


def build_package(
    *,
    repository_root: Path,
    output_root: Path,
    package: LambdaPackage,
) -> list[Path]:
    package_root = output_root / package.name

    if package_root.exists():
        shutil.rmtree(package_root)

    package_root.mkdir(parents=True)

    copy_file(
        repository_root / package.handler_source,
        package_root / "handler.py",
    )

    for shared_directory in package.shared_directories:
        source = repository_root / shared_directory
        copy_directory(source, package_root / source.name)

    files = sorted(
        path.relative_to(package_root)
        for path in package_root.rglob("*")
        if path.is_file()
    )

    if not files or files[0] != Path("handler.py"):
        if Path("handler.py") not in files:
            raise RuntimeError(
                f"Package {package.name} does not contain handler.py"
            )

    return files


def build_all_packages(
    *,
    repository_root: Path,
    output_root: Path | None = None,
    packages: Iterable[LambdaPackage] = PACKAGES,
) -> dict[str, list[Path]]:
    resolved_output_root = (
        output_root
        if output_root is not None
        else repository_root / "build" / "lambda"
    )

    if resolved_output_root.exists():
        shutil.rmtree(resolved_output_root)

    resolved_output_root.mkdir(parents=True)

    built: dict[str, list[Path]] = {}

    for package in packages:
        built[package.name] = build_package(
            repository_root=repository_root,
            output_root=resolved_output_root,
            package=package,
        )

    return built


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build isolated AWS Lambda deployment directories."
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repository_root = args.repository_root.resolve()
    output_root = (
        args.output_root.resolve()
        if args.output_root is not None
        else repository_root / "build" / "lambda"
    )

    built = build_all_packages(
        repository_root=repository_root,
        output_root=output_root,
    )

    for package_name, files in built.items():
        print(f"{package_name}: {len(files)} files")
        for file_path in files:
            print(f"  {file_path.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
