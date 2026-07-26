#!/usr/bin/env bash
set -euo pipefail

repository_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repository_root" || "$PWD" != "$repository_root" ]]; then
  echo "Run this script from the repository root." >&2
  exit 1
fi

bash -n tools/docs/archive_documentation.sh
bash -n tools/docs/validate_documentation.sh

python - "$repository_root" <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

root = Path(sys.argv[1]).resolve()
listed = subprocess.run(
    [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "*.md",
    ],
    cwd=root,
    check=True,
    capture_output=True,
    text=True,
).stdout.splitlines()
markdown_files = [root / relative for relative in sorted(set(listed))]
failures: list[str] = []

link_pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
for document in markdown_files:
    text = document.read_text(encoding="utf-8")
    for raw_target in link_pattern.findall(text):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        if (
            not target
            or target.startswith(("#", "http://", "https://", "mailto:", "app://"))
        ):
            continue
        local_target = unquote(target.split("#", 1)[0])
        resolved = (document.parent / local_target).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            failures.append(
                f"{document.relative_to(root)}: link escapes repository: {target}"
            )
            continue
        if not resolved.exists():
            failures.append(
                f"{document.relative_to(root)}: missing link target: {target}"
            )

canonical = [
    root / "docs" / "README.md",
    root / "docs" / "executive" / "README.md",
    root / "docs" / "executive" / "EXECUTIVE_SUMMARY.md",
    root / "docs" / "executive" / "PLATFORM_OVERVIEW.md",
    root / "docs" / "executive" / "SYSTEM_CAPABILITIES.md",
    root / "docs" / "executive" / "OPERATIONAL_READINESS.md",
    root / "docs" / "executive" / "PRODUCT_ROADMAP.md",
    root / "docs" / "executive" / "GLOSSARY.md",
    root / "docs" / "architecture" / "README.md",
    *[
        root / "docs" / "architecture" / f"{number:02d}_{name}.md"
        for number, name in [
            (1, "EXECUTIVE_OVERVIEW"),
            (2, "PLATFORM_OVERVIEW"),
            (3, "LOGICAL_ARCHITECTURE"),
            (4, "PHYSICAL_ARCHITECTURE"),
            (5, "SECURITY_ARCHITECTURE"),
            (6, "REQUEST_LIFECYCLE"),
            (7, "DATA_ARCHITECTURE"),
            (8, "PROCESSING_ARCHITECTURE"),
            (9, "DISASTER_RECOVERY"),
            (10, "OBSERVABILITY"),
            (11, "DEPLOYMENT_ARCHITECTURE"),
            (12, "VALIDATION_AND_CERTIFICATION"),
            (13, "OPERATIONAL_RUNBOOK"),
            (14, "ARCHITECTURAL_DECISIONS"),
        ]
    ],
    root / "docs" / "operations" / "README.md",
    root / "docs" / "certification" / "README.md",
    root / "docs" / "reference" / "README.md",
]
required_metadata = ("Status", "Audience", "Purpose", "Owner", "Related documents")
for document in canonical:
    if not document.exists():
        failures.append(f"missing canonical publication: {document.relative_to(root)}")
        continue
    text = document.read_text(encoding="utf-8")
    for field in required_metadata:
        if not re.search(rf"^> \*\*{re.escape(field)}:\*\*", text, re.MULTILINE):
            failures.append(
                f"{document.relative_to(root)}: missing metadata field {field}"
            )

titles: dict[str, list[Path]] = defaultdict(list)
for document in canonical:
    if not document.exists():
        continue
    match = re.search(r"^#\s+(.+)$", document.read_text(encoding="utf-8"), re.MULTILINE)
    if match:
        titles[match.group(1).strip().casefold()].append(document)
for title, documents in titles.items():
    if len(documents) > 1 and title not in {"platform overview"}:
        joined = ", ".join(str(path.relative_to(root)) for path in documents)
        failures.append(f"duplicate canonical title '{title}': {joined}")

mapping = root / "docs" / "DOCUMENT_MAPPING.md"
if not mapping.exists():
    failures.append("missing docs/DOCUMENT_MAPPING.md")
else:
    mapping_text = mapping.read_text(encoding="utf-8")
    for document in markdown_files:
        relative = document.relative_to(root).as_posix()
        if f"`{relative}`" not in mapping_text:
            failures.append(f"DOCUMENT_MAPPING.md missing Markdown file: {relative}")

for document in canonical:
    if not document.exists():
        continue
    text = document.read_text(encoding="utf-8")
    if re.search(r"\]\([^)]*docs/archive/|\]\([^)]*\.\./archive/", text):
        failures.append(
            f"{document.relative_to(root)}: canonical document uses archive as primary link"
        )

if failures:
    print("Documentation validation failed:")
    for failure in failures:
        print(f"  - {failure}")
    raise SystemExit(1)

print(f"Documentation validation passed: {len(markdown_files)} Markdown files checked.")
print(f"Canonical metadata passed: {len(canonical)} publications checked.")
PY
